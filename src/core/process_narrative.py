#!/usr/bin/env python3
"""
Process narrative texts into the Temporal-Spatial Memory database, with specific
support for PDF documents like The Hobbit.

Now enhanced with GraphRAG for better entity extraction and relationship modeling.
"""

# Ensure .env is loaded first!
try:
    from dotenv import load_dotenv
    if load_dotenv():
        print("Loaded environment variables from .env file.")
    else:
        print("Warning: .env file not found or empty.")
except ImportError:
    print("Warning: dotenv package not installed. Cannot load .env file.")

import os
import time
import argparse
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import datetime

# Core imports
from src.core.narrative_processor import NarrativeProcessor
from src.utils.config_loader import ConfigLoader
from src.models.narrative_atlas import NarrativeAtlas

# Add debugging
import inspect
import sys

from src.core.llm_operator import LLMOperator
from src.core.hybrid_extractor import HybridExtractor

def debug_function(func):
    """Print function signature for debugging"""
    print(f"Function: {func.__name__}")
    print(f"Signature: {inspect.signature(func)}")
    return func

# PDF processing imports
try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Warning: PyPDF2 not installed. PDF processing will not be available.")
    print("Install with: pip install PyPDF2")

# Optional: More advanced PDF processing
try:
    from unstructured.partition.pdf import partition_pdf
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    print("Note: 'unstructured' library not available. Using basic PDF extraction.")
    print("For better PDF extraction, install with: pip install unstructured[pdf]")

# Define a maximum chunk size in characters (adjust as needed)
# ~8000 chars is roughly 2000 tokens, well below typical limits
MAX_CHUNK_CHARS = 8000

class NarrativeProcessor:
    """
    Process narrative texts, with special handling for literary works.
    Converts documents, especially PDFs, into a temporal-spatial representation.
    """
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the narrative processor.
        
        Args:
            config_path: Path to the configuration file
            debug: Enable analytical breakpoints and snapshotting
        """
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()
        self.debug = debug
        
        # Get narrative metadata from config
        self.title = self.config.get("narrative", {}).get("title", "Unnamed Narrative")
        
        # Initialize atlas with configured storage path
        storage_path = self.config.get("storage", {}).get("path", "data")
        self.atlas = NarrativeAtlas(
            name=self._sanitize_name(self.title),
            storage_path=storage_path
        )
        
        # Track processing state
        self.processed_file = None
        self.output_dir = Path(self.config.get("output", {}).get("path", "Output"))
        self.output_dir.mkdir(exist_ok=True)
        # Create a timestamped run directory for this execution
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_output_dir = self.output_dir / timestamp
        self.run_output_dir.mkdir(exist_ok=True)
    
    def _sanitize_name(self, name: str) -> str:
        """Convert a name to a valid filename."""
        return re.sub(r'[^\w\s-]', '', name).lower().replace(' ', '_')
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from a PDF file, using the best available method.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as a string, or None if extraction failed
        """
        print(f"Reading PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file not found at {pdf_path}")
            return None
        
        # Try unstructured library first (if available) for better extraction
        if UNSTRUCTURED_AVAILABLE:
            try:
                print("Using unstructured library for advanced PDF parsing...")
                elements = partition_pdf(pdf_path)
                text = "\n\n".join(str(element) for element in elements)
                print(f"Extracted {len(text)} characters with unstructured library")
                return text
            except Exception as e:
                print(f"Error with unstructured PDF extraction: {str(e)}")
                print("Falling back to PyPDF2...")
        
        # Fall back to PyPDF2
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            
            print(f"PDF has {num_pages} pages")
            
            # Extract text from each page
            text = ""
            for i, page in enumerate(reader.pages):
                if i % 10 == 0:
                    print(f"Processing page {i+1}/{num_pages}...")
                text += page.extract_text() + "\n\n"
                
            print(f"Extracted {len(text)} characters with PyPDF2")
            # Analytical breakpoint
            if self.debug and text:
                print(f"[CHECKPOINT] Extracted text length: {len(text)}")
                print(f"[CHECKPOINT] Sample text (first 500 chars):\n{text[:500]}")
                with open("debug_extracted_text.txt", "w", encoding="utf-8") as f:
                    f.write(text)
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None
    
    def clean_literary_text(self, text: str) -> str:
        """
        Clean and preprocess literary text for better processing, preserving page numbers, headers, and footers.
        Extracts these elements as metadata for temporal/contextual use.
        Args:
            text: Raw text from the PDF
        Returns:
            Cleaned text (with all original content preserved)
        Side effects:
            Updates self.metadata with page numbers, chapters, headers, and footers
        """
        # Initialize metadata storage if not present
        if not hasattr(self, 'metadata'):
            self.metadata = {'pages': [], 'chapters': [], 'headers': [], 'footers': []}

        # Extract page numbers (simple heuristic: lines with only digits)
        page_number_pattern = re.compile(r'^\s*(\d+)\s*$', re.MULTILINE)
        for match in page_number_pattern.finditer(text):
            self.metadata['pages'].append({'page_number': int(match.group(1)), 'position': match.start()})

        # Extract chapter headings (common patterns)
        chapter_pattern = re.compile(r'(?im)^(chapter|CHAPTER|Chapter)\s+[IVXLCDM\d]+.*$', re.MULTILINE)
        for match in chapter_pattern.finditer(text):
            self.metadata['chapters'].append({'chapter': match.group(0).strip(), 'position': match.start()})

        # Optionally, extract headers/footers if patterns are provided in config
        header_pattern = self.config.get("text_processing", {}).get("header_pattern", "")
        footer_pattern = self.config.get("text_processing", {}).get("footer_pattern", "")
        if header_pattern:
            for match in re.finditer(header_pattern, text):
                self.metadata['headers'].append({'header': match.group(0), 'position': match.start()})
        if footer_pattern:
            for match in re.finditer(footer_pattern, text):
                self.metadata['footers'].append({'footer': match.group(0), 'position': match.start()})

        # Do NOT remove page numbers, headers, or footers from the text
        # Only normalize whitespace minimally
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Analytical breakpoint
        if self.debug:
            import json
            print(f"[CHECKPOINT] Pages found: {len(self.metadata['pages'])}")
            print(f"[CHECKPOINT] Chapters found: {len(self.metadata['chapters'])}")
            print(f"[CHECKPOINT] Sample cleaned text (first 500 chars):\n{text[:500]}")
            with open("debug_metadata.json", "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2)
            with open("debug_cleaned_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
        return text
    
    def preprocess_for_entity_extraction(self, text: str) -> str:
        """
        Add additional preprocessing to improve entity extraction for literature.
        
        Args:
            text: Cleaned text
            
        Returns:
            Text prepared for entity extraction
        """
        # Load entity extraction patterns from config
        entity_patterns = self.config.get("text_processing", {}).get("entity_patterns", {})
        
        # Add markers for dialogue to help with entity extraction
        text = re.sub(r'"([^"]+)" said (\w+)', r'"\1" said CHARACTER:\2', text)
        text = re.sub(r'"([^"]+)" (\w+) said', r'"\1" CHARACTER:\2 said', text)
        
        # Add location markers using configured patterns
        location_patterns = entity_patterns.get("locations", [])
        for pattern in location_patterns:
            text = re.sub(rf'\b{pattern}\b', f"LOCATION:{pattern}", text, flags=re.IGNORECASE)
        
        # Add character markers using configured patterns
        character_patterns = entity_patterns.get("characters", [])
        for pattern in character_patterns:
            text = re.sub(rf'\b{pattern}\b', f"CHARACTER:{pattern}", text, flags=re.IGNORECASE)
        
        # Analytical breakpoint
        if self.debug:
            print(f"[CHECKPOINT] Sample preprocessed text (first 500 chars):\n{text[:500]}")
            with open("debug_preprocessed_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
        return text
    
    def export_nodes_to_json(self, output_path: str = None) -> None:
        """
        Export all individual nodes (characters, events, locations, themes) to a structured JSON file.
        Args:
            output_path: Path to the output JSON file
        """
        nodes = []
        for node_dict in [self.atlas.characters, self.atlas.events, self.atlas.locations, self.atlas.themes]:
            for node_id, node in node_dict.items():
                if hasattr(node, 'to_dict'):
                    node_data = node.to_dict()
                else:
                    node_data = node.__dict__
                node_data['node_id'] = node_id
                nodes.append(node_data)
        import json
        # Always write to the run_output_dir as narrative_nodes.json
        output_path = self.run_output_dir / "narrative_nodes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(nodes, f, indent=2)
        print(f"Exported nodes to {output_path}")
    
    def process_narrative(self, text: Optional[str] = None, pdf_path: Optional[str] = None, segmentation_level: Optional[str] = None) -> "NarrativeAtlas":
        """
        Process a narrative text and build the narrative atlas.
        
        Args:
            text: The text to process. If None, will extract from PDF.
            pdf_path: Path to the PDF to extract text from (if text is None)
            segmentation_level: How to segment the text (paragraph, sentence, chapter)
                               If None, uses the value from config.
                               
        Returns:
            The populated NarrativeAtlas
        """
        start_time = time.time()
        
        # Get segmentation level from config if not specified
        if segmentation_level is None:
            segmentation_level = self.config.get("text_processing", {}).get("segmentation_level", "chapter")
        
        # If text is not provided, extract from PDF
        if text is None and pdf_path:
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                print("Failed to extract text from PDF.")
                return self.atlas
            self.processed_file = pdf_path
        
        if not text:
            print("No text to process.")
            return self.atlas
        
        print(f"Processing narrative: {self.title}")
        print(f"Segmentation level: {segmentation_level}")
        
        # Clean and preprocess the text
        clean_text = self.clean_literary_text(text)
        processed_text = self.preprocess_for_entity_extraction(clean_text)
        
        # Build the narrative atlas
        self.atlas.process_text(processed_text, self.title, segmentation_level)
        
        # Analytical breakpoint after segmentation and atlas creation
        if self.debug:
            print(f"[CHECKPOINT] NarrativeAtlas summary: {self.atlas.summary() if hasattr(self.atlas, 'summary') else str(self.atlas)}")
            # Optionally, save a serialized version of the atlas if supported
            if hasattr(self.atlas, 'to_json'):
                with open("debug_atlas.json", "w", encoding="utf-8") as f:
                    f.write(self.atlas.to_json())
        # Always export all nodes to a structured JSON file in the run-specific Output directory
        self.export_nodes_to_json()
        
        # Calculate processing time
        elapsed_time = time.time() - start_time
        print(f"Processing completed in {elapsed_time:.2f} seconds")
        
        return self.atlas

def main():
    """Main entry point for narrative processing."""
    parser = argparse.ArgumentParser(description="Process a narrative text (PDF or plain text) into a temporal-spatial database.")
    parser.add_argument("--config", type=str, help="Path to configuration file", default="config_examples/default_config.yaml")
    parser.add_argument("--pdf", type=str, help="Path to PDF file to process")
    parser.add_argument("--text", type=str, help="Path to text file to process")
    parser.add_argument("--use-graphrag", action="store_true", help="Use GraphRAG for enhanced entity extraction (currently implies LLM use)")
    args = parser.parse_args()
    
    if not args.pdf and not args.text:
        print("Error: Either a PDF or text file must be specified.")
        parser.print_help()
        return
    
    # Load config
    config_loader = ConfigLoader(args.config)
    config = config_loader.load_config()
    print(f"Loaded configuration from: {args.config}")

    # Update config with command line arguments (if any affect config directly)
    if args.use_graphrag:
        if "processing" not in config:
            config["processing"] = {}
        config["processing"]["use_graphrag"] = True
        print("GraphRAG processing enabled via command line.")

    # Save updated config if needed (optional)
    config_loader.config = config

    # Initialize processor (loads config, sets up output dirs)
    print(f"Initializing NarrativeProcessor with config: {args.config}")
    processor = NarrativeProcessor(config_path=args.config) # Pass config path again

    # Initialize LLM and hybrid extractor
    try:
        llm = LLMOperator() # Assumes API key is set via environment
        extractor = HybridExtractor(llm)
    except ValueError as e:
        print(f"Error initializing LLM components: {e}")
        print("Please ensure the OPENAI_API_KEY environment variable is set correctly.")
        return

    # Extract text if needed
    text = None
    if args.pdf:
        print(f"Extracting text from PDF: {args.pdf}")
        text = processor.extract_text_from_pdf(args.pdf)
        if not text:
            print("Failed to extract text from PDF. Exiting.")
            return
    elif args.text:
        try:
            print(f"Reading text from file: {args.text}")
            with open(args.text, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading text file: {str(e)}. Exiting.")
            return

    if not text:
        print("No text available to process. Exiting.")
        return

    # Clean text and extract metadata (like chapter positions)
    print("Cleaning text and extracting metadata...")
    clean_text = processor.clean_literary_text(text)

    # --- Process by Chunks --- 
    print("Processing text by chapter, sub-chunking if necessary...")
    all_segments_for_atlas = []
    all_entities_for_atlas = []

    if not processor.metadata or not processor.metadata.get('chapters'):
        print("Warning: No chapter metadata found. Processing the text with sub-chunking.")
        # Treat the whole text as one initial "chapter" to be sub-chunked
        initial_chunks = [(clean_text, 0, len(clean_text), {'chapter': 'Full Text'})]
    else:
        print(f"Found {len(processor.metadata['chapters'])} chapters.")
        chapters = sorted(processor.metadata['chapters'], key=lambda x: x['position'])
        initial_chunks = []
        for i, chapter_meta in enumerate(chapters):
            start_pos = chapter_meta['position']
            end_pos = chapters[i+1]['position'] if (i + 1) < len(chapters) else len(clean_text)
            chapter_text = clean_text[start_pos:end_pos]
            initial_chunks.append((chapter_text, start_pos, end_pos, chapter_meta))

    # Process initial chunks (chapters or full text), sub-chunking if needed
    total_initial_chunks = len(initial_chunks)
    for idx, (initial_text, initial_start, initial_end, initial_meta) in enumerate(initial_chunks):
        
        print(f"\nProcessing Initial Chunk {idx+1}/{total_initial_chunks} (Source: {initial_meta.get('chapter', 'Full Text')}, Chars: {len(initial_text)})..." )

        sub_chunks = []
        if len(initial_text) > MAX_CHUNK_CHARS:
            print(f"  Initial chunk exceeds {MAX_CHUNK_CHARS} chars. Sub-chunking...")
            # Simple fixed-size sub-chunking (can be improved, e.g., split by paragraph)
            current_pos = 0
            while current_pos < len(initial_text):
                sub_end = min(current_pos + MAX_CHUNK_CHARS, len(initial_text))
                sub_chunks.append(initial_text[current_pos:sub_end])
                current_pos = sub_end
            print(f"  Split into {len(sub_chunks)} sub-chunks.")
        else:
            sub_chunks.append(initial_text)

        # Process each sub-chunk (or the single chunk if not split)
        for sub_idx, chunk_text in enumerate(sub_chunks):
            if len(sub_chunks) > 1:
                print(f"  Processing Sub-chunk {sub_idx+1}/{len(sub_chunks)} (Chars: {len(chunk_text)})..." )
            
            # Calculate correct start/end indices relative to the *original* clean_text
            # This assumes fixed-size chunking for simplicity; paragraph splitting would need smarter index tracking
            chunk_start_in_doc = initial_start + sum(len(c) for c in sub_chunks[:sub_idx])
            chunk_end_in_doc = chunk_start_in_doc + len(chunk_text)

            # Create a segment corresponding to this specific chunk
            segment = {
                'text': chunk_text, 
                'start_index': chunk_start_in_doc, 
                'end_index': chunk_end_in_doc, 
                'metadata': initial_meta # Associate with original chapter/source
            }
            all_segments_for_atlas.append(segment)

            # Extract entities for this chunk
            print(f"    [Chunk {idx+1}-{sub_idx+1}] Calling LLM for entity extraction..." )
            entities = extractor.extract_entities(chunk_text)
            print(f"    [Chunk {idx+1}-{sub_idx+1}] LLM call complete.")

            if entities:
                print(f"      Extracted entities for Chunk {idx+1}-{sub_idx+1}.")
                all_entities_for_atlas.append(entities)
            else:
                print(f"      No entities extracted for Chunk {idx+1}-{sub_idx+1}.")
                all_entities_for_atlas.append({}) # Keep entity list aligned with segments
            
            # Add delay to respect rate limits
            print(f"    [Chunk {idx+1}-{sub_idx+1}] Waiting 1 second before next call..." )
            time.sleep(1)

    # --- Add all extracted nodes to the atlas --- 
    if all_segments_for_atlas and all_entities_for_atlas:
            print("\nAdding all extracted nodes to NarrativeAtlas...")
            processor.atlas.add_nodes_from_extraction(all_segments_for_atlas, all_entities_for_atlas)
    else:
            print("\nNo segments or entities were processed to add to the atlas.")

    # --- Save Atlas and Export Nodes --- 
    print("Saving NarrativeAtlas...")
    processor.atlas.save()

    print("Exporting nodes...")
    processor.export_nodes_to_json() # Uses run_output_dir by default now

    print(f"\nProcessing complete!")
    print(f"All outputs (like narrative_nodes.json) should be in: {processor.run_output_dir}")

if __name__ == "__main__":
    main() 
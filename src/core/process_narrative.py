#!/usr/bin/env python3
"""
Process narrative texts into the Temporal-Spatial Memory database, with specific
support for PDF documents like The Hobbit.

Now enhanced with GraphRAG for better entity extraction and relationship modeling.
"""

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
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)
from src.utils.config_loader import ConfigLoader
from src.models.narrative_atlas import NarrativeAtlas

# Add debugging
import inspect
import sys

from .llm_operator import LLMOperator
from .hybrid_extractor import HybridExtractor

def debug_function(func):
    """Print function signature for debugging"""
    print(f"Function: {func.__name__}")
    print(f"Signature: {inspect.signature(func)}")
    return func

# Assign debug wrappers
debug_create_character_arc_visualization = debug_function(create_character_arc_visualization)

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
        if output_path is None:
            output_path = self.run_output_dir / "narrative_nodes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(nodes, f, indent=2)
    
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
    
    def generate_visualizations(self) -> None:
        """Generate standard visualizations for the narrative."""
        if not self.atlas:
            print("No atlas to visualize.")
            return
        
        file_prefix = self._sanitize_name(self.title)
        
        # Create the visualization directory inside the run-specific output directory
        viz_dir = self.run_output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        print("Generating narrative visualizations...")
        
        try:
            # Create main narrative visualization
            create_narrative_visualization(
                self.atlas, 
                str(viz_dir / f"{file_prefix}_visualization.html")
            )
            
            # Create narrative timeline
            create_narrative_timeline(
                self.atlas,
                str(viz_dir / f"{file_prefix}_timeline.html")
            )
            
            # Print function signatures for debugging
            print("Debugging function signatures:")
            debug_create_character_arc_visualization
            
            # Create character arc visualizations for major characters
            top_characters = sorted(
                self.atlas.characters.items(),
                key=lambda x: x[1].content.get("mentions", 0),
                reverse=True
            )[:10]  # Top 10 characters
            
            for char_id, _ in top_characters:
                try:
                    print(f"Processing character: {char_id}")
                    character_data = self.atlas.analyze_character_arc(char_id)
                    character_name = character_data["name"]
                    char_filename = self._sanitize_name(character_name)
                    output_path = str(viz_dir / f"{file_prefix}_{char_filename}_arc.html")
                    
                    # Use a fallback approach with try/except
                    try:
                        create_character_arc_visualization(
                            self.atlas,
                            char_id,
                            output_path
                        )
                    except TypeError as e:
                        print(f"TypeError: {e}")
                        # Try alternative parameter combinations
                        try:
                            print("Trying alternative approach...")
                            create_character_arc_visualization(
                                character_data,
                                output_path
                            )
                        except Exception as e2:
                            print(f"Alternative approach failed: {e2}")
                except Exception as e:
                    print(f"Error processing character {char_id}: {str(e)}")
        except Exception as e:
            print(f"Error generating visualizations: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print(f"Visualizations saved to {viz_dir}")

def main():
    """Main entry point for narrative processing."""
    parser = argparse.ArgumentParser(description="Process a narrative text (PDF or plain text) into a temporal-spatial database.")
    parser.add_argument("--config", type=str, help="Path to configuration file", default="config_examples/default_config.yaml")
    parser.add_argument("--pdf", type=str, help="Path to PDF file to process")
    parser.add_argument("--text", type=str, help="Path to text file to process")
    parser.add_argument("--segmentation", type=str, choices=["paragraph", "sentence", "chapter"], 
                        help="Segmentation level (default is from config)")
    parser.add_argument("--use-graphrag", action="store_true", help="Use GraphRAG for enhanced entity extraction")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations after processing")
    
    args = parser.parse_args()
    
    if not args.pdf and not args.text:
        print("Error: Either a PDF or text file must be specified.")
        parser.print_help()
        return
    
    # Load config
    config_loader = ConfigLoader(args.config)
    config = config_loader.load_config()
    
    # Update config with command line arguments
    if args.use_graphrag:
        if "processing" not in config:
            config["processing"] = {}
        config["processing"]["use_graphrag"] = True
    
    # Save updated config if needed
    config_loader.config = config
    
    # Initialize processor
    print(f"Initializing with config: {args.config}")
    processor = NarrativeProcessor(args.config)
    
    # Initialize LLM and hybrid extractor
    llm = LLMOperator()
    extractor = HybridExtractor(llm)
    
    # Extract text if needed
    text = None
    if args.pdf:
        text = processor.extract_text_from_pdf(args.pdf)
        if not text:
            print("Failed to extract text from PDF.")
            return
    elif args.text:
        try:
            with open(args.text, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading text file: {str(e)}")
            return
    
    # Segment text using hybrid (LLM + deterministic) extractor
    print("Segmenting text using hybrid (LLM + deterministic) extractor...")
    segments = extractor.segment_text(text)
    
    # Extract entities for each segment
    print("Extracting entities for each segment...")
    all_entities = []
    for segment in segments:
        entities = extractor.extract_entities(segment['text'] if isinstance(segment, dict) and 'text' in segment else segment)
        all_entities.append(entities)
        # TODO: Pass entities and segment info to NarrativeAtlas for node creation and time hierarchy assignment
    
    # TODO: Integrate with NarrativeAtlas to build nodes using segments and extracted entities
    # atlas = processor.process_narrative(
    #     text=text,
    #     segmentation_level=args.segmentation
    # )
    
    print("Processing complete!")

if __name__ == "__main__":
    main() 
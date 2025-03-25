#!/usr/bin/env python3
"""
Process narrative texts into the Temporal-Spatial Memory database, with specific
support for PDF documents like The Hobbit.
"""

import os
import time
import argparse
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Core imports
from src.models.narrative_atlas import NarrativeAtlas
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)
from src.utils.config_loader import ConfigLoader

# Add debugging
import inspect
import sys

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
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the narrative processor.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()
        
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
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None
    
    def clean_literary_text(self, text: str) -> str:
        """
        Clean and preprocess literary text for better processing.
        
        Args:
            text: Raw text from the PDF
            
        Returns:
            Cleaned text
        """
        # Remove page numbers
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove headers and footers that repeat on pages
        header_pattern = self.config.get("text_processing", {}).get("header_pattern", "")
        footer_pattern = self.config.get("text_processing", {}).get("footer_pattern", "")
        
        if header_pattern:
            text = re.sub(header_pattern, '', text)
        if footer_pattern:
            text = re.sub(footer_pattern, '', text)
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Clean up spaces
        text = re.sub(r' +', ' ', text)
        
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
        
        return text
    
    def process_narrative(self, text: Optional[str] = None, pdf_path: Optional[str] = None, segmentation_level: Optional[str] = None) -> NarrativeAtlas:
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
        
        # Create the visualization directory
        viz_dir = self.output_dir / "visualizations"
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
    """Main entry point for the narrative processor CLI."""
    parser = argparse.ArgumentParser(description="Process narrative text into a temporal-spatial database")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--pdf", help="Path to PDF file to process")
    parser.add_argument("--segmentation", choices=["paragraph", "sentence", "chapter"], 
                       help="Segmentation level for text processing")
    parser.add_argument("--list-configs", action="store_true", help="List available configuration files")
    parser.add_argument("--select-config", type=int, help="Select a configuration by number")
    
    args = parser.parse_args()
    
    # Handle configuration selection
    if args.list_configs:
        config_dir = Path("config_examples")
        if config_dir.exists():
            configs = list(config_dir.glob("*.yaml"))
            print("\nAvailable configurations:")
            for i, config in enumerate(configs):
                print(f"{i+1}. {config.name}")
        else:
            print("No configuration directory found.")
        return
    
    if args.select_config is not None:
        config_dir = Path("config_examples")
        if config_dir.exists():
            configs = list(config_dir.glob("*.yaml"))
            if 1 <= args.select_config <= len(configs):
                args.config = str(configs[args.select_config - 1])
                print(f"Selected configuration: {configs[args.select_config - 1].name}")
            else:
                print(f"Invalid configuration number. Must be between 1 and {len(configs)}.")
                return
    
    # Initialize processor
    processor = NarrativeProcessor(args.config)
    
    # Process narrative
    processor.process_narrative(
        pdf_path=args.pdf,
        segmentation_level=args.segmentation
    )
    
    # Generate visualizations
    processor.generate_visualizations()
    
    print("Processing complete!")

if __name__ == "__main__":
    main() 
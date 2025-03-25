#!/usr/bin/env python3
"""
Generic narrative processor that processes any narrative text based on configuration.
"""

import os
import re
import time
import argparse
from typing import Dict, Any, Optional, List

from PyPDF2 import PdfReader
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.config_loader import ConfigLoader
from src.utils.text_processor import TextProcessor
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)

class NarrativeProcessor:
    """
    Generic processor for narrative text analysis.
    
    Uses configuration-driven approach to process any narrative text,
    eliminating content-specific code.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the narrative processor.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_loader = ConfigLoader(config_path)
        self.text_processor = TextProcessor(self.config_loader)
        
        # Get title from config
        self.title = self.config_loader.get_value("narrative.title", "narrative")
        self.db_name = self.config_loader.to_slug(self.title)
        
        # Initialize the atlas
        self.atlas = NarrativeAtlas(name=self.db_name, storage_path="data")
    
    def extract_text_from_pdf(self, pdf_path: Optional[str] = None) -> Optional[str]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file. If None, uses the path from config.
            
        Returns:
            Extracted text as a string
        """
        if not pdf_path:
            # Get the path from config using templates
            pdf_path = self.config_loader.get_template_value("paths.input_file")
            
        print(f"Reading PDF: {pdf_path}")
        
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
                
            print(f"Extracted {len(text)} characters")
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None
    
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
            segmentation_level = self.config_loader.get_value("text_processing.segmentation_level", "chapter")
        
        # If text is not provided, extract from PDF
        if text is None:
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                print("Failed to extract text from PDF.")
                return self.atlas
        
        print(f"Processing narrative: {self.title}")
        print(f"Segmentation level: {segmentation_level}")
        
        # Clean and preprocess the text
        clean_text = self.text_processor.clean_text(text)
        processed_text = self.text_processor.preprocess_for_entity_extraction(clean_text)
        
        # Build the narrative atlas
        self.atlas.process_text(processed_text, self.title, segmentation_level)
        
        # Calculate processing time
        elapsed_time = time.time() - start_time
        print(f"Processing completed in {elapsed_time:.2f} seconds")
        
        return self.atlas
    
    def create_narrative_launcher(self) -> None:
        """Create a launcher HTML file for the narrative visualizations."""
        # Filter out common words mistakenly identified as characters
        filtered_characters = {}
        common_words = self.config_loader.get_common_words()
        
        for char_id, character in self.atlas.characters.items():
            name = character.content.get("name", "Unknown")
            if name.lower() not in common_words and len(name) > 1:
                mentions = character.content.get("mentions", 0)
                filtered_characters[char_id] = (name, mentions)
        
        # Get the top characters by mentions
        top_characters = sorted(
            [(char_id, mentions) for char_id, (name, mentions) in filtered_characters.items()],
            key=lambda x: x[1],
            reverse=True
        )[:15]  # Get top 15 filtered characters
        
        # Create HTML content
        title = self.title
        file_prefix = self.db_name
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Narrative Atlas: %s</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f9fc;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        }
        .card h2 {
            color: #3498db;
            margin-top: 0;
        }
        .card p {
            color: #666;
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        footer {
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #7f8c8d;
        }
        .character-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }
        .character-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        .character-name {
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        .character-stat {
            color: #7f8c8d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>Narrative Atlas: %s</h1>
    
    <div class="container">
        <div class="card">
            <h2>Complete Narrative Visualization</h2>
            <p>View the 3D spatial-temporal representation of the narrative structure.</p>
            <a href="%s_visualization.html" class="btn">Open Visualization</a>
        </div>
        
        <div class="card">
            <h2>Narrative Timeline</h2>
            <p>Explore the chronological progression of events and character introductions.</p>
            <a href="%s_timeline.html" class="btn">Open Timeline</a>
        </div>
        
        <div class="card">
            <h2>Narrative Summary</h2>
            <p>Read a generated summary of the narrative based on our analysis.</p>
            <a href="%s_summary.html" class="btn">Read Summary</a>
        </div>
    """ % (title, title, file_prefix, file_prefix, file_prefix)
    
    # Add character analysis section
        if top_characters:
            html += """
        <div class="card">
            <h2>Top Characters</h2>
            <p>Analyze the narrative arcs of major characters in the story.</p>
            <div class="character-grid">
            """
            
            for char_id, mentions in top_characters:
                character = self.atlas.characters.get(char_id)
                name = character.content.get("name", "Unknown")
                
                html += """
                <div class="character-card">
                    <div class="character-name">%s</div>
                    <div class="character-stat">Mentions: %d</div>
                    <a href="%s_character_%s.html" class="btn" style="margin-top: 10px; font-size: 12px;">View Arc</a>
                </div>
                """ % (name, mentions, file_prefix, char_id)
            
            html += """
            </div>
        </div>
        """
    
        html += """
    </div>
    
    <footer>
        <p>Generated by Narrative Atlas Framework</p>
    </footer>
</body>
</html>
"""
        
        # Get output path from config
        output_path = self.config_loader.get_template_value("paths.launcher_file")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the HTML file
        with open(output_path, 'w') as f:
            f.write(html)
            
        print(f"Created narrative launcher: {output_path}")
    
    def generate_visualizations(self) -> None:
        """Generate all visualizations for the narrative."""
        # Ensure the atlas is loaded
        if not self.atlas.characters and not self.atlas.events:
            self.atlas.load()
            if not self.atlas.characters and not self.atlas.events:
                print("No narrative data available. Process a narrative first.")
                return
        
        # Get output paths from config
        vis_path = self.config_loader.get_template_value("paths.visualization_file")
        timeline_path = self.config_loader.get_template_value("paths.timeline_file")
        
        # Ensure output directories exist
        os.makedirs(os.path.dirname(vis_path), exist_ok=True)
        os.makedirs(os.path.dirname(timeline_path), exist_ok=True)
        
        # Create the main visualization
        create_narrative_visualization(self.atlas, vis_path)
        print(f"Created narrative visualization: {vis_path}")
        
        # Create the timeline visualization
        create_narrative_timeline(self.atlas, timeline_path)
        print(f"Created narrative timeline: {timeline_path}")
        
        # Create character arc visualizations for top characters
        self.generate_character_visualizations()
        
        # Create the launcher HTML
        self.create_narrative_launcher()
    
    def generate_character_visualizations(self) -> None:
        """Generate visualizations for top characters."""
        # Filter characters to exclude common words
        filtered_chars = {}
        common_words = self.config_loader.get_common_words()
        
        for char_id, character in self.atlas.characters.items():
            name = character.content.get("name", "Unknown")
            if name.lower() not in common_words and len(name) > 1:
                mentions = character.content.get("mentions", 0)
                filtered_chars[char_id] = mentions
        
        # Get top 15 characters by mention count
        top_chars = sorted(filtered_chars.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Create character arc visualizations
        output_dir = os.path.dirname(self.config_loader.get_template_value("paths.visualization_file"))
        file_prefix = self.db_name
        
        for char_id, _ in top_chars:
            output_path = f"{output_dir}/{file_prefix}_character_{char_id}.html"
            create_character_arc_visualization(self.atlas, char_id, output_path)
            print(f"Created character visualization for {char_id}: {output_path}")
    
    def run(self, pdf_path: Optional[str] = None, segmentation_level: Optional[str] = None) -> None:
        """
        Run the complete narrative processing pipeline.
        
        Args:
            pdf_path: Optional path to PDF file
            segmentation_level: Optional segmentation level
        """
        # Process the narrative
        self.process_narrative(pdf_path=pdf_path, segmentation_level=segmentation_level)
        
        # Generate visualizations
        self.generate_visualizations()
        
        print(f"Narrative processing complete for: {self.title}")

def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Process narrative text using the Narrative Atlas framework")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--pdf", help="Path to PDF file (overrides config)")
    parser.add_argument("--segmentation", choices=["paragraph", "sentence", "chapter"], 
                        help="Segmentation level (overrides config)")
    
    args = parser.parse_args()
    
    processor = NarrativeProcessor(args.config)
    processor.run(pdf_path=args.pdf, segmentation_level=args.segmentation)

if __name__ == "__main__":
    main() 
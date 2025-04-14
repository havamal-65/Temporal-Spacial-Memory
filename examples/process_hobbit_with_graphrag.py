#!/usr/bin/env python3
"""
Process The Hobbit with GraphRAG integration.

This script demonstrates how to use the enhanced temporal-spatial memory system
with GraphRAG to process The Hobbit and generate improved visualizations.
"""

import os
import sys
from pathlib import Path
from PyPDF2 import PdfReader

from src.core.narrative_processor import NarrativeProcessor
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
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

def main():
    """Process The Hobbit with GraphRAG integration."""
    print("Processing The Hobbit with GraphRAG Integration")
    print("==============================================\n")
    
    # Check for hobbit PDF
    pdf_path = "Input/the_hobbit_tolkien.pdf"
    config_path = "config_examples/hobbit_config.yaml"
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        print("Please place The Hobbit PDF in the Input directory as 'the_hobbit_tolkien.pdf'")
        return
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return
    
    # Extract text from PDF
    print(f"Extracting text from {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text from PDF.")
        return
    
    print(f"Successfully extracted {len(text)} characters from PDF")
    
    # Initialize processor with GraphRAG
    print(f"Initializing processor with config: {config_path}")
    processor = NarrativeProcessor(config_path)
    
    # Process the narrative with GraphRAG
    print("\nProcessing narrative with GraphRAG...")
    print("This may take several minutes as the knowledge graph is constructed.")
    atlas = processor.process_narrative(text=text)
    
    # Generate visualizations
    output_dir = "Output/hobbit_graphrag"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nGenerating visualizations in {output_dir}...")
    
    # Create main narrative visualization
    viz_path = os.path.join(output_dir, "hobbit_narrative.html")
    create_narrative_visualization(atlas, viz_path)
    print(f"Created narrative visualization: {viz_path}")
    
    # Create timeline visualization
    timeline_path = os.path.join(output_dir, "hobbit_timeline.html")
    create_narrative_timeline(atlas, timeline_path)
    print(f"Created timeline visualization: {timeline_path}")
    
    # Create character arc visualizations for top characters
    top_characters = sorted(atlas.characters.values(), 
                          key=lambda c: c.content.get("mention_count", 0), 
                          reverse=True)[:5]
    
    for char in top_characters:
        char_name = char.content.get("name", "character")
        char_slug = char_name.lower().replace(' ', '_')
        char_path = os.path.join(output_dir, f"hobbit_{char_slug}_arc.html")
        create_character_arc_visualization(atlas, char.node_id, char_path)
        print(f"Created character arc for {char_name}: {char_path}")
    
    # Create a launcher HTML file
    launcher_path = os.path.join(output_dir, "hobbit_launcher.html")
    with open(launcher_path, 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>The Hobbit - GraphRAG Enhanced Analysis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        h2 { color: #3498db; }
        .viz-link { 
            display: block; margin: 10px 0; padding: 10px;
            background-color: #3498db; color: white;
            text-decoration: none; border-radius: 5px;
            width: 300px; text-align: center;
        }
        .viz-link:hover { background-color: #2980b9; }
        .improvement { 
            background-color: #f1f8e9; 
            padding: 10px;
            border-left: 5px solid #8bc34a;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <h1>The Hobbit - GraphRAG Enhanced Analysis</h1>
    <p>This analysis uses GraphRAG for improved entity recognition and relationship extraction.</p>
    
    <div class="improvement">
        <h2>GraphRAG Improvements</h2>
        <ul>
            <li>Better character identification (no false positives on common words)</li>
            <li>Relationship extraction between characters, locations, and events</li>
            <li>Higher quality entity recognition with proper NLP techniques</li>
            <li>Semantic understanding of the narrative structure</li>
        </ul>
    </div>
    
    <h2>Visualizations</h2>
    <a href="hobbit_narrative.html" class="viz-link">Complete Narrative Structure</a>
    <a href="hobbit_timeline.html" class="viz-link">Narrative Timeline</a>
""")
        
        # Add character links
        for char in top_characters:
            char_name = char.content.get("name", "character")
            char_slug = char_name.lower().replace(' ', '_')
            f.write(f'    <a href="hobbit_{char_slug}_arc.html" class="viz-link">{char_name}\'s Character Arc</a>\n')
        
        f.write("""</body>
</html>""")
    
    print(f"\nCreated launcher HTML: {launcher_path}")
    print(f"Open {launcher_path} in a web browser to view all visualizations.")
    print("\nProcessing complete!")

if __name__ == "__main__":
    main() 
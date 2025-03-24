#!/usr/bin/env python3
"""
Process The Hobbit using the Apache OpenNLP integration for the Narrative Atlas framework.
"""

import os
import time
import re
import argparse
import logging
from PyPDF2 import PdfReader
from src.models.narrative_atlas import NarrativeAtlas
from src.nlp.opennlp.integration import OpenNLPIntegration
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    logger.info(f"Reading PDF: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        
        logger.info(f"PDF has {num_pages} pages")
        
        # Extract text from each page
        text = ""
        for i, page in enumerate(reader.pages):
            if i % 10 == 0:
                logger.info(f"Processing page {i+1}/{num_pages}...")
            text += page.extract_text() + "\n\n"
            
        logger.info(f"Extracted {len(text)} characters")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None

def clean_hobbit_text(text):
    """
    Clean and preprocess The Hobbit text for better processing.
    
    Args:
        text: Raw text from the PDF
        
    Returns:
        Cleaned text
    """
    # Remove header/footer content that might appear on multiple pages
    text = re.sub(r'The Hobbit, or There and Back Again\s*J.R.R. Tolkien\s*', '', text)
    
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove page numbers
    text = re.sub(r'\n\d+\n', '\n', text)
    
    # Clean up spaces
    text = re.sub(r' +', ' ', text)
    
    # Replace common pronoun references for better character tracking
    text = re.sub(r'\bThe hobbit\b', 'Bilbo Baggins', text, flags=re.IGNORECASE)
    text = re.sub(r'\bMr\. Baggins\b', 'Bilbo Baggins', text)
    
    # Handle known character names with consistent capitalization
    main_characters = [
        "Bilbo", "Thorin", "Gandalf", "Smaug", "Gollum", "Elrond", "Beorn", 
        "Bard", "Balin", "Dwalin", "Kili", "Fili", "Dori", "Nori", "Ori",
        "Oin", "Gloin", "Bifur", "Bofur", "Bombur"
    ]
    
    for character in main_characters:
        # Create a pattern that matches the character name case-insensitively with word boundaries
        pattern = r'\b' + re.escape(character) + r'\b'
        # Replace with properly capitalized name
        text = re.sub(pattern, character, text, flags=re.IGNORECASE)
    
    return text

def create_narrative_launcher(atlas, title, output_path="Output/the_hobbit_opennlp_launcher.html"):
    """Create a launcher HTML file for the narrative visualizations."""
    # Filter out common words mistakenly identified as characters
    filtered_characters = {}
    common_words = ["the", "and", "but", "he", "it", "they", "there", "in", "of", "to", "a", "was", "had", "you", "that", "this", "not", "for", "his"]
    
    for char_id, character in atlas.characters.items():
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
    file_prefix = title.lower().replace(" ", "_") + "_opennlp"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Narrative Atlas with OpenNLP: {title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f9fc;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        .container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        }}
        .card h2 {{
            color: #3498db;
            margin-top: 0;
        }}
        .card p {{
            color: #666;
            margin-bottom: 20px;
        }}
        .btn {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }}
        .btn:hover {{
            background-color: #2980b9;
        }}
        footer {{
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #7f8c8d;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }}
        .character-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }}
        .character-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        .character-name {{
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }}
        .character-stat {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            background-color: #3498db;
            color: white;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    <h1>Narrative Atlas with OpenNLP: {title} <span class="badge">Apache OpenNLP Enhanced</span></h1>
    
    <div class="container">
        <div class="card">
            <h2>Complete Narrative Visualization</h2>
            <p>View the 3D spatial-temporal representation of the narrative structure, enhanced with OpenNLP's improved entity and relationship extraction.</p>
            <a href="{file_prefix}_visualization.html" class="btn">Open Visualization</a>
        </div>
        
        <div class="card">
            <h2>Narrative Timeline</h2>
            <p>Explore the chronological progression of events and character introductions with enriched event detection using OpenNLP.</p>
            <a href="{file_prefix}_timeline.html" class="btn">Open Timeline</a>
        </div>
        
        <div class="card">
            <h2>Narrative Summary</h2>
            <p>Read a generated summary of the narrative based on our OpenNLP-enhanced analysis.</p>
            <a href="{file_prefix}_summary.html" class="btn">Read Summary</a>
        </div>
    </div>
    
    <h2>Top Characters</h2>
    <p>Characters identified and analyzed by Apache OpenNLP's entity recognition:</p>
    
    <div class="character-grid">
"""
    
    # Add character cards
    for i, (char_id, mentions) in enumerate(top_characters):
        character = atlas.characters.get(char_id)
        name = character.content.get("name", "Character")
        
        html += f"""        <div class="character-card">
            <div class="character-name">{name}</div>
            <div class="character-stat">Mentions: {mentions}</div>
            <div class="character-stat">Time: {character.time:.2f}</div>
            <div class="character-stat">Connections: {len(character.connections)}</div>
            <a href="{file_prefix}_{name.lower().replace(' ', '_')}_arc.html" class="btn">View Arc</a>
        </div>
"""
    
    html += f"""    </div>
    
    <footer>
        <p>Narrative Analysis with Temporal-Spatial Memory Database</p>
        <p>Narrative Statistics:</p>
        <ul>
            <li>Segments: {len(atlas.segments)}</li>
            <li>Characters: {len(atlas.characters)} (filtered to {len(filtered_characters)} major characters)</li>
            <li>Events: {len(atlas.events)}</li>
            <li>Locations: {len(atlas.locations)}</li>
            <li>Word count: {atlas.metrics.get('word_count', 0)}</li>
        </ul>
        <p>Enhanced with Apache OpenNLP for improved entity and relationship extraction</p>
        <p>Instructions: Click on a visualization to open it. In each visualization, you can:
        <br>• Rotate the 3D view by clicking and dragging
        <br>• Zoom with the scroll wheel
        <br>• Hover over nodes to see details</p>
    </footer>
</body>
</html>
"""
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the HTML file
    with open(output_path, "w") as f:
        f.write(html)
    
    logger.info(f"Launcher created at {output_path}")
    return output_path, filtered_characters

def process_hobbit_with_opennlp(input_file="Input/the_hobbit.pdf", segmentation_level="chapter"):
    """
    Process The Hobbit with OpenNLP integration.
    
    Args:
        input_file: Path to the input PDF file
        segmentation_level: Level at which to segment the text
        
    Returns:
        NarrativeAtlas instance with processed data
    """
    # Ensure directories exist
    os.makedirs("Input", exist_ok=True)
    os.makedirs("Output", exist_ok=True)
    os.makedirs("models/opennlp", exist_ok=True)
    
    # Set title and output paths
    title = "The Hobbit"
    file_prefix = title.lower().replace(" ", "_") + "_opennlp"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return None
    
    # Extract text from PDF
    text = extract_text_from_pdf(input_file)
    if not text:
        logger.error("Failed to extract text from PDF")
        return None
    
    # Clean and preprocess text
    cleaned_text = clean_hobbit_text(text)
    logger.info(f"Cleaned text: {len(cleaned_text)} characters")
    
    # Create NarrativeAtlas instance
    atlas = NarrativeAtlas(name=file_prefix, storage_path="data")
    
    # Create OpenNLP integration
    opennlp_integration = OpenNLPIntegration(atlas)
    
    # Process text with OpenNLP
    logger.info(f"Processing text with OpenNLP integration: {title}")
    logger.info(f"Segmentation level: {segmentation_level}")
    
    start_time = time.time()
    opennlp_integration.process_text(cleaned_text, title, segmentation_level=segmentation_level)
    end_time = time.time()
    
    logger.info(f"Processing completed in {end_time - start_time:.2f} seconds")
    
    # Print basic stats
    logger.info("\nNarrative Analysis Results:")
    logger.info(f"  Segments: {atlas.metrics.get('segment_count', 0)}")
    logger.info(f"  Characters: {len(atlas.characters)}")
    logger.info(f"  Events: {len(atlas.events)}")
    logger.info(f"  Locations: {len(atlas.locations)}")
    logger.info(f"  Word count: {atlas.metrics.get('word_count', 0)}")
    
    # Create visualizations
    logger.info("\nCreating visualizations...")
    
    # Main narrative visualization
    output_path = os.path.join("Output", f"{file_prefix}_visualization.html")
    create_narrative_visualization(atlas, output_path)
    logger.info(f"  Created main visualization: {output_path}")
    
    # Timeline visualization
    timeline_path = os.path.join("Output", f"{file_prefix}_timeline.html")
    create_narrative_timeline(atlas, timeline_path)
    logger.info(f"  Created timeline: {timeline_path}")
    
    # Create launcher HTML and get filtered characters
    launcher_path, filtered_characters = create_narrative_launcher(atlas, title)
    
    # Get top characters by mentions
    top_characters = sorted(
        [(char_id, mentions) for char_id, (name, mentions) in filtered_characters.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Get top 10 filtered characters
    
    # Character arc visualizations for main characters
    for char_id, mentions in top_characters:
        character = atlas.characters.get(char_id)
        name = character.content.get("name", "character")
        arc_path = os.path.join("Output", f"{file_prefix}_{name.lower().replace(' ', '_')}_arc.html")
        create_character_arc_visualization(atlas, char_id, arc_path)
        logger.info(f"  Created character arc for {name} ({mentions} mentions): {arc_path}")
    
    logger.info("\nAnalysis complete!")
    logger.info(f"Open '{launcher_path}' to explore the visualizations.")
    
    # Print top characters for easy reference
    logger.info("\nTop characters detected (filtered):")
    for i, (char_id, mentions) in enumerate(top_characters[:15], 1):
        character = atlas.characters.get(char_id)
        name = character.content.get("name", "character")
        logger.info(f"  {i}. {name} ({mentions} mentions)")
    
    # Save atlas to disk
    atlas.save()
    logger.info(f"Atlas saved to {os.path.join('data', file_prefix)}")
    
    return atlas

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Process The Hobbit with OpenNLP integration.')
    parser.add_argument('--input', '-i', type=str, default="Input/the_hobbit.pdf", 
                      help='Path to the input PDF file')
    parser.add_argument('--segmentation', '-s', type=str, default="chapter",
                      help='Level at which to segment the text (paragraph, sentence, chapter)')
    
    args = parser.parse_args()
    
    process_hobbit_with_opennlp(input_file=args.input, segmentation_level=args.segmentation)

if __name__ == "__main__":
    main() 
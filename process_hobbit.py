#!/usr/bin/env python3
"""
Process The Hobbit PDF and build a narrative analysis using the NarrativeAtlas framework.
"""

import os
import time
import re
import argparse
from PyPDF2 import PdfReader
from src.models.narrative_atlas import NarrativeAtlas
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

def preprocess_for_better_entity_extraction(text):
    """
    Add additional preprocessing to improve entity extraction.
    
    Args:
        text: Cleaned text
        
    Returns:
        Text with enhanced entity markers
    """
    # Add markers for dialogue to help with entity extraction
    text = re.sub(r'"([^"]+)" said (\w+)', r'"\1" said CHARACTER:\2', text)
    text = re.sub(r'"([^"]+)" (\w+) said', r'"\1" CHARACTER:\2 said', text)
    
    # Add location markers
    locations = [
        "Bag End", "Hobbiton", "The Shire", "Rivendell", "Misty Mountains", 
        "Mirkwood", "Lake-town", "Esgaroth", "Lonely Mountain", "Erebor",
        "Dale", "Laketown", "Goblin Town", "Forest", "Mountain", "Cave",
        "Beorn's House", "Mirkwood Forest", "The Great Hall"
    ]
    
    for location in locations:
        pattern = r'\b' + re.escape(location) + r'\b'
        replacement = f"LOCATION:{location}"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text

def create_narrative_launcher(atlas, title):
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
    file_prefix = title.lower().replace(" ", "_")
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
    
    # Add cards for top character arcs
    for char_id, mentions in top_characters[:3]:  # Limit to 3 main characters in main grid
        character = atlas.characters.get(char_id)
        if character:
            name = character.content.get("name", "Character")
            html += """
        <div class="card">
            <h2>%s's Character Arc</h2>
            <p>Analyze the development and journey of %s throughout the narrative.</p>
            <a href="%s_%s_arc.html" class="btn">View Character Arc</a>
        </div>
            """ % (name, name, file_prefix, name.lower())
    
    # Add a section for all major characters
    html += """
    </div>
    
    <h2>Major Characters</h2>
    <div class="character-grid">
    """
    
    # Add all top characters
    for char_id, mentions in top_characters:
        character = atlas.characters.get(char_id)
        if character:
            name = character.content.get("name", "Character")
            html += """
        <div class="character-card">
            <div class="character-name">%s</div>
            <div class="character-stat">Mentions: %d</div>
            <a href="%s_%s_arc.html" class="btn">View Arc</a>
        </div>
            """ % (name, mentions, file_prefix, name.lower())
    
    # Close HTML
    html += """
    </div>
    
    <footer>
        <p>Narrative Analysis with Temporal-Spatial Memory Database</p>
        <p>Narrative Statistics:</p>
        <ul>
            <li>Segments: %d</li>
            <li>Characters: %d (filtered to %d major characters)</li>
            <li>Events: %d</li>
            <li>Locations: %d</li>
            <li>Word count: %d</li>
        </ul>
        <p>Instructions: Click on a visualization to open it. In each visualization, you can:
        <br>• Rotate the 3D view by clicking and dragging
        <br>• Zoom with the scroll wheel
        <br>• Hover over nodes to see details</p>
    </footer>
</body>
</html>
    """ % (
        atlas.metrics["segment_count"],
        atlas.metrics["character_count"],
        len(filtered_characters),
        atlas.metrics["event_count"],
        atlas.metrics["location_count"],
        atlas.metrics["word_count"]
    )
    
    # Write the launcher file
    launcher_path = os.path.join("Output", f"{file_prefix}_launcher.html")
    with open(launcher_path, 'w') as f:
        f.write(html)
    
    return launcher_path, filtered_characters

def process_hobbit(segmentation_level="chapter"):
    """
    Process The Hobbit PDF and create narrative analysis.
    
    Args:
        segmentation_level: How to segment the text ("paragraph", "sentence", "chapter")
    """
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("Output", exist_ok=True)
    
    # Path to The Hobbit PDF
    pdf_path = "Input/the_hobbit_tolkien.pdf"
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text from PDF")
        return
    
    # Clean the text
    text = clean_hobbit_text(text)
    
    # Additional preprocessing to improve entity extraction
    text = preprocess_for_better_entity_extraction(text)
    
    # Create the Narrative Atlas
    title = "The Hobbit"
    atlas = NarrativeAtlas(name=title.lower().replace(" ", "_"), storage_path="data")
    
    # Process the text
    start_time = time.time()
    print(f"\nProcessing text: {title}")
    print(f"Segmentation level: {segmentation_level}")
    print(f"Text length: {len(text)} characters")
    
    # Process in chapters to better handle memory
    if segmentation_level == "chapter":
        # Try to split by chapter headings
        chapter_pattern = r'(?:Chapter \d+\s*(?:\n|\r\n)?(?:[A-Z][A-Za-z\s]+))'
        chapters = re.split(chapter_pattern, text)
        
        if len(chapters) <= 2:  # If not enough chapters found, try another approach
            print("Could not detect chapters automatically. Splitting into sections...")
            # Split into reasonable chunks
            chunk_size = 5000
            chapters = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        print(f"Split text into {len(chapters)} sections")
        
        # Process each chapter
        for i, chapter_text in enumerate(chapters):
            if not chapter_text.strip():
                continue
                
            print(f"Processing section {i+1}/{len(chapters)}...")
            # Process with a temporary timeline position offset to maintain sequence
            atlas.process_text(chapter_text, f"{title} - Part {i+1}", segmentation_level="paragraph")
            
    else:
        # Process the entire text at once (may be memory intensive for large books)
        atlas.process_text(text, title, segmentation_level=segmentation_level)
    
    processing_time = time.time() - start_time
    
    # Print basic stats
    print("\nNarrative Analysis Results:")
    print(f"  Segments: {atlas.metrics['segment_count']}")
    print(f"  Characters: {atlas.metrics['character_count']}")
    print(f"  Events: {atlas.metrics['event_count']}")
    print(f"  Locations: {atlas.metrics['location_count']}")
    print(f"  Word count: {atlas.metrics['word_count']}")
    print(f"  Processing time: {processing_time:.2f} seconds")
    
    # Create visualizations
    print("\nCreating visualizations...")
    
    # Main narrative visualization
    output_path = os.path.join("Output", f"{title.lower().replace(' ', '_')}_visualization.html")
    create_narrative_visualization(atlas, output_path)
    print(f"  Created main visualization: {output_path}")
    
    # Timeline visualization
    timeline_path = os.path.join("Output", f"{title.lower().replace(' ', '_')}_timeline.html")
    create_narrative_timeline(atlas, timeline_path)
    print(f"  Created timeline: {timeline_path}")
    
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
        arc_path = os.path.join("Output", f"{title.lower().replace(' ', '_')}_{name.lower()}_arc.html")
        create_character_arc_visualization(atlas, char_id, arc_path)
        print(f"  Created character arc for {name} ({mentions} mentions): {arc_path}")
    
    print("\nAnalysis complete!")
    print(f"Open '{launcher_path}' to explore the visualizations.")
    
    # Print top characters for easy reference
    print("\nTop characters detected (filtered):")
    for i, (char_id, mentions) in enumerate(top_characters[:15], 1):
        character = atlas.characters.get(char_id)
        name = character.content.get("name", "character")
        print(f"  {i}. {name} ({mentions} mentions)")
    
    return atlas

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Process The Hobbit PDF into the Narrative Atlas framework.')
    parser.add_argument('--segmentation', '-s', type=str, 
                        choices=['paragraph', 'sentence', 'chapter'], 
                        default='chapter', 
                        help='Text segmentation level')
    
    args = parser.parse_args()
    
    # Install PyPDF2 if not available
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 not found. Installing...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'PyPDF2'])
    
    process_hobbit(args.segmentation)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Test script for the Narrative Atlas framework.
Demonstrates text processing, analysis, and visualization capabilities.
"""

import os
import argparse
from src.models.narrative_atlas import NarrativeAtlas
from src.visualization.narrative_visualizer import (
    create_narrative_visualization,
    create_character_arc_visualization,
    create_narrative_timeline
)

def test_narrative_atlas(text_file: str, title: str, segmentation: str = "paragraph"):
    """
    Process a text file and create visualizations using the Narrative Atlas framework.
    
    Args:
        text_file: Path to the text file to process
        title: Title of the narrative
        segmentation: Segmentation level ('paragraph', 'sentence', 'chapter')
    """
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("Output", exist_ok=True)
    
    # Create the Narrative Atlas
    atlas = NarrativeAtlas(name=title.lower().replace(" ", "_"), storage_path="data")
    
    # Read the text file
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Process the text
    print(f"Processing text: {title}")
    print(f"Segmentation level: {segmentation}")
    print(f"Text length: {len(text)} characters")
    
    atlas.process_text(text, title, segmentation_level=segmentation)
    
    # Print basic stats
    print("\nNarrative Analysis Results:")
    print(f"  Segments: {atlas.metrics['segment_count']}")
    print(f"  Characters: {atlas.metrics['character_count']}")
    print(f"  Events: {atlas.metrics['event_count']}")
    print(f"  Locations: {atlas.metrics['location_count']}")
    print(f"  Word count: {atlas.metrics['word_count']}")
    
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
    
    # Character arc visualizations for main characters
    for char_id, character in list(atlas.characters.items())[:5]:  # Limit to top 5 characters
        name = character.content.get("name", "character")
        arc_path = os.path.join("Output", f"{title.lower().replace(' ', '_')}_{name.lower()}_arc.html")
        create_character_arc_visualization(atlas, char_id, arc_path)
        print(f"  Created character arc for {name}: {arc_path}")
    
    # Create launcher HTML
    create_narrative_launcher(atlas, title)
    
    print("\nAnalysis complete!")
    print(f"Open 'Output/{title.lower().replace(' ', '_')}_launcher.html' to explore the visualizations.")

def create_narrative_launcher(atlas, title):
    """Create a launcher HTML file for the narrative visualizations."""
    # Get the top characters
    top_characters = sorted(
        [(char_id, char.content.get("mentions", 0)) for char_id, char in atlas.characters.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
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
    """ % (title, title, file_prefix, file_prefix)
    
    # Add cards for character arcs
    for char_id, mentions in top_characters:
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
    
    # Close HTML
    html += """
    </div>
    
    <footer>
        <p>Narrative Analysis with Temporal-Spatial Memory Database</p>
        <p>Narrative Statistics:</p>
        <ul>
            <li>Segments: %d</li>
            <li>Characters: %d</li>
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
        atlas.metrics["event_count"],
        atlas.metrics["location_count"],
        atlas.metrics["word_count"]
    )
    
    # Write the launcher file
    launcher_path = os.path.join("Output", f"{file_prefix}_launcher.html")
    with open(launcher_path, 'w') as f:
        f.write(html)

def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description='Test the Narrative Atlas framework.')
    parser.add_argument('--file', '-f', type=str, required=True, help='Path to text file')
    parser.add_argument('--title', '-t', type=str, default="Narrative", help='Title of the narrative')
    parser.add_argument('--segmentation', '-s', type=str, 
                        choices=['paragraph', 'sentence', 'chapter'], 
                        default='paragraph', 
                        help='Text segmentation level')
    
    args = parser.parse_args()
    
    test_narrative_atlas(args.file, args.title, args.segmentation)

if __name__ == "__main__":
    main() 
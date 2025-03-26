#!/usr/bin/env python3
"""
Process The Hobbit with direct GraphRAG API integration.

A simpler version that uses only the basic visualization components that are known to work.
"""

import os
import sys
from pathlib import Path
from PyPDF2 import PdfReader
import shutil
import time
import asyncio

# GraphRAG imports
import graphrag.api as graphrag_api
from graphrag.config.load_config import load_config

# Visualization imports
from src.visualization.narrative_visualizer import (
    create_narrative_visualization, 
    create_character_arc_visualization,
    create_narrative_timeline
)

# Import the NarrativeAtlas for storing the processed data
from src.models.narrative_atlas import NarrativeAtlas
from src.models.narrative_nodes import CharacterNode, LocationNode, EventNode, ThemeNode

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

def clean_narrative_text(text):
    """
    Clean the extracted text for better processing.
    
    Args:
        text: Raw text from the PDF
        
    Returns:
        Cleaned text
    """
    import re
    
    # Remove page numbers
    text = re.sub(r'\n\d+\n', '\n', text)
    
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Clean up spaces
    text = re.sub(r' +', ' ', text)
    
    return text

def setup_graphrag_project(project_dir, input_text):
    """
    Set up a GraphRAG project.
    
    Args:
        project_dir: Path to the project directory
        input_text: Text to process
        
    Returns:
        GraphRAG config object
    """
    # Create project directory if it doesn't exist
    os.makedirs(project_dir, exist_ok=True)
    
    # Check if config already exists, otherwise create it
    config_path = os.path.join(project_dir, "settings.yaml")
    if not os.path.exists(config_path):
        print(f"Initializing GraphRAG project at {project_dir}")
        os.system(f"graphrag init --root {project_dir}")
    
    # Load the config
    config = load_config(Path(project_dir))
    
    # Write the input text to a file
    input_dir = os.path.join(project_dir, "input")
    os.makedirs(input_dir, exist_ok=True)
    
    input_file = os.path.join(input_dir, "the_hobbit.txt")
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(input_text)
    
    return config

def convert_graphrag_to_atlas(index_data, atlas_name="the_hobbit_graphrag"):
    """
    Convert GraphRAG index data to a NarrativeAtlas.
    
    Args:
        index_data: GraphRAG index data
        atlas_name: Name of the atlas
        
    Returns:
        NarrativeAtlas instance
    """
    # Create a new atlas
    atlas = NarrativeAtlas(name=atlas_name, storage_path="data")
    
    # Extract entities from the index data
    entities = index_data.get("entities", [])
    relationships = index_data.get("relationships", [])
    
    # Process entities
    entity_id_map = {}
    for entity in entities:
        entity_id = entity.get("id", "")
        entity_type = entity.get("type", "entity").lower()
        entity_name = entity.get("name", "")
        entity_desc = entity.get("description", "")
        
        # Determine node type and create appropriate node
        if entity_type in ("character", "person", "protagonist", "antagonist"):
            node = CharacterNode(
                node_id=entity_id,
                name=entity_name,
                time=entity.get("time", 0.5),
                distance=entity.get("centrality", 0.5),
                angle=float(hash(entity_name) % 100) / 100 * 6.28, 
                content={
                    "description": entity_desc,
                    "type": "character",
                    "mention_count": entity.get("mention_count", 1)
                }
            )
            atlas.characters[entity_id] = node
            entity_id_map[entity_id] = node
            
        elif entity_type in ("location", "place", "setting"):
            node = LocationNode(
                node_id=entity_id,
                name=entity_name,
                time=entity.get("time", 0.5),
                distance=entity.get("centrality", 0.5),
                angle=float(hash(entity_name) % 100) / 100 * 6.28 + 1.57,  # offset by 90 degrees
                content={
                    "description": entity_desc,
                    "type": "location"
                }
            )
            atlas.locations[entity_id] = node
            entity_id_map[entity_id] = node
            
        elif entity_type in ("event", "action", "happening"):
            node = EventNode(
                node_id=entity_id,
                name=entity_name,
                time=entity.get("time", 0.5),
                distance=entity.get("centrality", 0.5),
                angle=float(hash(entity_name) % 100) / 100 * 6.28 + 3.14,  # offset by 180 degrees
                content={
                    "description": entity_desc,
                    "type": "event"
                }
            )
            atlas.events[entity_id] = node
            entity_id_map[entity_id] = node
            
        elif entity_type in ("theme", "concept", "idea"):
            node = ThemeNode(
                node_id=entity_id,
                name=entity_name,
                time=entity.get("time", 0.5),
                distance=entity.get("centrality", 0.5),
                angle=float(hash(entity_name) % 100) / 100 * 6.28 + 4.71,  # offset by 270 degrees
                content={
                    "description": entity_desc,
                    "type": "theme"
                }
            )
            atlas.themes[entity_id] = node
            entity_id_map[entity_id] = node
    
    # Process relationships
    for rel in relationships:
        source_id = rel.get("source", "")
        target_id = rel.get("target", "")
        relationship_type = rel.get("type", "related_to")
        
        if source_id in entity_id_map and target_id in entity_id_map:
            source_node = entity_id_map[source_id]
            source_node.add_relationship(
                target_id=target_id,
                relationship_type=relationship_type,
                properties={
                    "description": rel.get("description", ""),
                    "weight": rel.get("weight", 1.0)
                }
            )
    
    # Save the atlas
    atlas.save()
    
    return atlas

def generate_visualizations(atlas, output_dir):
    """
    Generate visualizations from the atlas.
    
    Args:
        atlas: NarrativeAtlas instance
        output_dir: Output directory for visualizations
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create narrative visualization
    print("Creating narrative visualization...")
    viz_path = os.path.join(output_dir, "hobbit_narrative.html")
    create_narrative_visualization(atlas, viz_path)
    
    # Create timeline visualization
    print("Creating timeline visualization...")
    timeline_path = os.path.join(output_dir, "hobbit_timeline.html")
    create_narrative_timeline(atlas, timeline_path)
    
    # Create character arc visualizations for top characters
    print("Creating character arc visualizations...")
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
        body { font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        h2 { color: #3498db; }
        .viz-link { 
            display: block; margin: 10px 0; padding: 15px;
            background-color: #3498db; color: white;
            text-decoration: none; border-radius: 5px;
            width: 300px; text-align: center;
        }
        .viz-link:hover { background-color: #2980b9; }
        .improvement { 
            background-color: #f1f8e9; 
            padding: 15px;
            border-left: 5px solid #8bc34a;
            margin: 20px 0;
        }
        .viz-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>The Hobbit - GraphRAG Enhanced Analysis</h1>
    <p>This analysis uses GraphRAG for improved entity recognition and relationship extraction.</p>
    
    <div class="improvement">
        <h2>GraphRAG Improvements</h2>
        <ul>
            <li>Better character identification with relationship mapping</li>
            <li>More accurate location detection and temporal positioning</li>
            <li>Theme extraction and analysis</li>
            <li>Event sequence modeling and visualization</li>
            <li>Semantic understanding of the narrative structure</li>
        </ul>
    </div>
    
    <h2>Visualizations</h2>
    <div class="viz-container">
        <a href="hobbit_narrative.html" class="viz-link">Narrative Structure</a>
        <a href="hobbit_timeline.html" class="viz-link">Narrative Timeline</a>
""")
        
        # Add character links
        for char in top_characters:
            char_name = char.content.get("name", "character")
            char_slug = char_name.lower().replace(' ', '_')
            f.write(f'        <a href="hobbit_{char_slug}_arc.html" class="viz-link">{char_name}\'s Character Arc</a>\n')
        
        f.write("""    </div>
</body>
</html>""")
    
    print(f"\nCreated launcher HTML: {launcher_path}")
    print(f"Open {launcher_path} in a web browser to view all visualizations.")

def main():
    """Process The Hobbit with GraphRAG API."""
    print("Processing The Hobbit with GraphRAG API Integration")
    print("=================================================\n")
    
    # Set up paths
    pdf_path = "Input/the_hobbit_tolkien.pdf"
    project_dir = "data/hobbit_graphrag"
    output_dir = "Output/hobbit_graphrag"
    
    # Check for the PDF file
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        print("Please place The Hobbit PDF in the Input directory as 'the_hobbit_tolkien.pdf'")
        return
    
    # Extract text from PDF
    print(f"Extracting text from {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text from PDF.")
        return
    
    # Clean the text
    print("Cleaning extracted text...")
    clean_text = clean_narrative_text(text)
    
    # Set up GraphRAG project
    print(f"Setting up GraphRAG project at {project_dir}...")
    setup_graphrag_project(project_dir, clean_text)
    
    # Process the text with GraphRAG
    print("\nProcessing text with GraphRAG API...")
    print("This will take several minutes as the knowledge graph is constructed.")
    
    # Need to handle async call
    async def process_with_graphrag():
        # Load the config
        config = load_config(Path(project_dir))
        
        # Run the indexing
        results = await graphrag_api.build_index(config)
        return results[0] if results else {}
    
    # Run the async function
    index_data = asyncio.run(process_with_graphrag())
    
    # Convert GraphRAG index data to NarrativeAtlas
    print("\nConverting GraphRAG output to NarrativeAtlas...")
    atlas = convert_graphrag_to_atlas(index_data)
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    generate_visualizations(atlas, output_dir)
    
    print("\nProcessing complete!")
    print(f"Open {os.path.join(output_dir, 'hobbit_launcher.html')} to view all visualizations.")

if __name__ == "__main__":
    main() 
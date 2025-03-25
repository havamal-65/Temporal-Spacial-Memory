#!/usr/bin/env python3
"""
Script to generate an enhanced 3D visualization for The Hobbit.
"""

import os
import argparse
from src.models.narrative_atlas import NarrativeAtlas
from src.visualization.enhanced_3d_visualizer import create_enhanced_hobbit_visualization

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Generate an enhanced 3D visualization for The Hobbit.')
    parser.add_argument('--output', '-o', type=str, default="Output/the_hobbit_enhanced_visualization.html", 
                      help='Output path for the visualization file')
    
    args = parser.parse_args()
    
    # Ensure Output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Load the narrative analysis
    print("Loading narrative analysis for The Hobbit...")
    atlas = NarrativeAtlas(name="the_hobbit", storage_path="data")
    atlas.load()
    
    # Check if analysis exists
    if not atlas.characters:
        print("No analysis data found. Please run process_hobbit.py first.")
        return
    
    print(f"Found {len(atlas.characters)} characters and {len(atlas.events)} events in the analysis.")
    
    # Generate the enhanced visualization
    print("Generating enhanced 3D visualization...")
    create_enhanced_hobbit_visualization(atlas, args.output)
    
    print(f"Enhanced visualization saved to {args.output}")
    print(f"Open {args.output} in a browser to view the visualization.")

if __name__ == "__main__":
    main() 
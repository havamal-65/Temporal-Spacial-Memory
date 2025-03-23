#!/usr/bin/env python3
"""
Main runner script for the Temporal-Spatial Memory Database.

This script runs the full MeshTube implementation.
"""

import os
import sys
import time
from typing import Optional, Dict, Any, List, Tuple
from src.models.mesh_tube import MeshTube

def run_database(name: str = "MeshTubeDB", storage_path: Optional[str] = "data"):
    """
    Run the database.
    
    Args:
        name: Name for the database
        storage_path: Path to store database files
    """
    print("Starting Temporal-Spatial Memory Database...")
    
    print("Using MeshTube implementation with RTree spatial indexing")
    mesh = MeshTube(name=name, storage_path=storage_path)
    
    # Create example data
    create_example_data(mesh)
    
    # Run a few sample operations
    print("Running sample operations...")
    
    # Get a sample node
    sample_node_id = list(mesh.nodes.keys())[0]
    sample_node = mesh.get_node(sample_node_id)
    
    # Temporal slice
    start_time = time.time()
    slice_result = mesh.get_temporal_slice(time=1.0, tolerance=0.5)
    slice_time = time.time() - start_time
    print(f"Temporal slice found {len(slice_result)} nodes (took {slice_time*1000:.2f}ms)")
    
    # Nearest neighbors
    start_time = time.time()
    neighbors = mesh.get_nearest_nodes(sample_node, limit=3)
    neighbors_time = time.time() - start_time
    print(f"Found {len(neighbors)} nearest neighbors (took {neighbors_time*1000:.2f}ms)")
    
    # Cache stats
    cache_stats = {
        "hits": mesh.cache_hits,
        "misses": mesh.cache_misses,
        "hit_rate": mesh.cache_hits / (mesh.cache_hits + mesh.cache_misses) if (mesh.cache_hits + mesh.cache_misses) > 0 else 0
    }
    
    print(f"Cache performance: {cache_stats['hit_rate']:.1%} hit rate ({cache_stats['hits']} hits, {cache_stats['misses']} misses)")
    
    print("\nDatabase is running and ready for use!")
    return mesh

def create_example_data(mesh):
    """Create sample data in the mesh tube."""
    print("Creating example data...")
    
    # Add some core nodes
    ai_node = mesh.add_node(
        content={"topic": "Artificial Intelligence", "type": "core_concept"},
        time=0,
        distance=0,  # Central node
        angle=0
    )
    
    ml_node = mesh.add_node(
        content={"topic": "Machine Learning", "type": "technology"},
        time=1,
        distance=1,
        angle=45
    )
    
    nlp_node = mesh.add_node(
        content={"topic": "Natural Language Processing", "type": "application"},
        time=2,
        distance=2,
        angle=90
    )
    
    vision_node = mesh.add_node(
        content={"topic": "Computer Vision", "type": "application"},
        time=2,
        distance=2,
        angle=180
    )
    
    ethics_node = mesh.add_node(
        content={"topic": "AI Ethics", "type": "consideration"},
        time=3,
        distance=1.5,
        angle=270
    )
    
    # Connect related nodes
    mesh.connect_nodes(ai_node.node_id, ml_node.node_id)
    mesh.connect_nodes(ml_node.node_id, nlp_node.node_id)
    mesh.connect_nodes(ml_node.node_id, vision_node.node_id)
    mesh.connect_nodes(ai_node.node_id, ethics_node.node_id)
    
    # Create some delta updates
    mesh.apply_delta(
        original_node=ai_node,
        delta_content={"updated": True, "new_info": "AGI is emerging as a critical area"},
        time=4
    )
    
    mesh.apply_delta(
        original_node=ml_node,
        delta_content={"updated": True, "new_info": "Transformers have revolutionized the field"},
        time=5
    )
    
    print(f"Created {len(mesh.nodes)} nodes with connections and deltas")

def main():
    """Main entry point for the script."""
    # Ensure storage directory exists
    storage_path = "data"
    os.makedirs(storage_path, exist_ok=True)
    
    # Run with default parameters
    mesh = run_database(storage_path=storage_path)
    
    # Keep the script running to demonstrate it's working
    try:
        print("Press Ctrl+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
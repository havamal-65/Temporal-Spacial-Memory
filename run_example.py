#!/usr/bin/env python3
"""
Runner script for the Mesh Tube Knowledge Database example
"""

import os
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the example module from src
from src.models.mesh_tube import MeshTube
from src.utils.position_calculator import PositionCalculator
from src.visualization.mesh_visualizer import MeshVisualizer

def main():
    """
    Create a sample mesh tube database with AI-related topics
    """
    # Create a new mesh tube instance
    mesh = MeshTube(name="AI Conversation", storage_path="data")
    
    print(f"Created new Mesh Tube: {mesh.name}", flush=True)
    
    # Add some initial core topics (at time 0)
    ai_node = mesh.add_node(
        content={"topic": "Artificial Intelligence", "description": "The field of AI research"},
        time=0,
        distance=0.1,  # Close to center (core topic)
        angle=0
    )
    
    ml_node = mesh.add_node(
        content={"topic": "Machine Learning", "description": "A subfield of AI focused on learning from data"},
        time=0,
        distance=0.3,
        angle=45
    )
    
    dl_node = mesh.add_node(
        content={"topic": "Deep Learning", "description": "A subfield of ML using neural networks"},
        time=0,
        distance=0.5,
        angle=90
    )
    
    # Connect related topics
    mesh.connect_nodes(ai_node.node_id, ml_node.node_id)
    mesh.connect_nodes(ml_node.node_id, dl_node.node_id)
    
    # Add a specific AI model (at time 1)
    gpt_node = mesh.add_node(
        content={"topic": "GPT Models", "description": "Large language models by OpenAI"},
        time=1,
        distance=0.7,
        angle=30
    )
    
    # Connect to related topics
    mesh.connect_nodes(ml_node.node_id, gpt_node.node_id)
    
    # Create an update to GPT at time 2
    gpt_update = mesh.apply_delta(
        original_node=gpt_node,
        delta_content={"versions": ["GPT-3", "GPT-4"], "capabilities": "Advanced reasoning"},
        time=2
    )
    
    # Print statistics
    print("\nMesh Tube Statistics:", flush=True)
    print(MeshVisualizer.print_mesh_stats(mesh), flush=True)
    
    # Visualize a temporal slice
    print("\nTemporal Slice at time 0:", flush=True)
    print(MeshVisualizer.visualize_temporal_slice(mesh, time=0, tolerance=0.1), flush=True)
    
    print("\nTemporal Slice at time 1:", flush=True)
    print(MeshVisualizer.visualize_temporal_slice(mesh, time=1, tolerance=0.1), flush=True)
    
    # Display connections for GPT node
    print("\nConnections for GPT node:", flush=True)
    print(MeshVisualizer.visualize_connections(mesh, gpt_node.node_id), flush=True)
    
    # Show the full state of the GPT node after delta update
    print("\nFull state of GPT node after update:", flush=True)
    full_state = mesh.compute_node_state(gpt_update.node_id)
    for key, value in full_state.items():
        print(f"{key}: {value}", flush=True)
    
    # Save the database
    os.makedirs("data", exist_ok=True)
    mesh.save(filepath="data/ai_conversation_demo.json")
    print("\nDatabase saved to data/ai_conversation_demo.json", flush=True)

if __name__ == "__main__":
    print("Mesh Tube Knowledge Database Demo", flush=True)
    print("=================================", flush=True)
    main() 
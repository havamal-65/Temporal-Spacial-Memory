#!/usr/bin/env python3
"""
Example showing how to use the Temporal-Spatial Memory Database
"""

import os
import sys
from src.models.mesh_tube import MeshTube
from src.models.node import Node

def main():
    """
    Create and use a Temporal-Spatial Knowledge Database
    """
    # Create a new mesh tube database instance
    mesh = MeshTube(name="My Knowledge Database", storage_path="data")
    
    print(f"Created new Mesh Tube: {mesh.name}")
    
    # Add some core topics
    ai_node = mesh.add_node(
        content={"topic": "Machine Learning", "description": "Core concept of ML"},
        time=0,  # Time coordinate (0 = now, can be relative time)
        distance=0.1,  # Distance from center (smaller = more important)
        angle=0  # Angular position in the tube
    )
    
    tools_node = mesh.add_node(
        content={"topic": "ML Tools", "description": "Various ML tools and frameworks"},
        time=0,
        distance=0.3,
        angle=45
    )
    
    # Connect related topics
    mesh.connect_nodes(ai_node.node_id, tools_node.node_id)
    
    # Add a specific tool (at a later time)
    pytorch_node = mesh.add_node(
        content={"topic": "PyTorch", "description": "Deep learning framework"},
        time=1,  # Later point in time
        distance=0.5,
        angle=30
    )
    
    # Connect to related topics
    mesh.connect_nodes(tools_node.node_id, pytorch_node.node_id)
    
    # Update information about PyTorch
    pytorch_update = mesh.apply_delta(
        original_node=pytorch_node,
        delta_content={"version": "2.0", "features": "Dynamic computation graph"},
        time=2  # Even later point in time
    )
    
    # Query the database
    print("\nRetrieving nodes:")
    retrieved_node = mesh.get_node(ai_node.node_id)
    print(f"Retrieved node: {retrieved_node.content['topic']}")
    
    # Get temporal slice (all nodes at a specific time)
    print("\nTemporal slice at time 0:")
    nodes_at_time_0 = mesh.get_temporal_slice(time=0, tolerance=0.1)
    for node in nodes_at_time_0:
        print(f"- {node.content.get('topic', 'Unknown topic')}")
    
    # Find nearest nodes to a specific node
    print("\nNearest nodes to 'ML Tools':")
    nearest = mesh.get_nearest_nodes(tools_node, limit=2)
    for node, distance in nearest:
        print(f"- {node.content.get('topic', 'Unknown')} (distance: {distance:.2f})")
    
    # Get full state of PyTorch node after updates
    print("\nFull state of PyTorch node after update:")
    full_state = mesh.compute_node_state(pytorch_update.node_id)
    for key, value in full_state.items():
        print(f"- {key}: {value}")
    
    # Save the database
    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", "my_knowledge_db.json")
    mesh.save(save_path)
    print(f"\nDatabase saved to {save_path}")
    
    # Later, you can load it with:
    # loaded_mesh = MeshTube.load(save_path)

if __name__ == "__main__":
    print("Temporal-Spatial Memory Database Example")
    print("=======================================")
    main() 
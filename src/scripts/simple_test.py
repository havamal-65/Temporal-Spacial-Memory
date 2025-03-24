#!/usr/bin/env python3
"""
Simple test script for the Mesh Tube Knowledge Database
"""

import os
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.mesh_tube import MeshTube

def main():
    """Simple test of the MeshTube class"""
    # Print a header
    print("Simple Mesh Tube Test")
    print("====================")
    
    # Create a mesh tube instance
    mesh = MeshTube(name="Test Mesh", storage_path=None)
    
    print(f"Created mesh: {mesh.name}")
    
    # Add some test nodes
    node1 = mesh.add_node(
        content={"topic": "Test Topic 1"},
        time=0.0,
        distance=0.1,
        angle=0.0
    )
    
    print(f"Added node 1: {node1.node_id}")
    print(f"Content: {node1.content}")
    
    node2 = mesh.add_node(
        content={"topic": "Test Topic 2"},
        time=1.0,
        distance=0.5,
        angle=90.0
    )
    
    print(f"Added node 2: {node2.node_id}")
    print(f"Content: {node2.content}")
    
    # Connect the nodes
    mesh.connect_nodes(node1.node_id, node2.node_id)
    print(f"Connected node 1 and node 2")
    
    # Check connections
    print(f"Node 1 connections: {node1.connections}")
    print(f"Node 2 connections: {node2.connections}")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    main() 
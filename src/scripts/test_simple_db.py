#!/usr/bin/env python3
"""
Test script for the Mesh Tube Knowledge Database.

This script tests the basic functionality of the database to ensure it works.
"""

import os
import sys
from src.models.mesh_tube import MeshTube
from src.models.node import Node

def test_mesh_tube():
    """Test the functionality of the MeshTube class."""
    try:
        # Create a new mesh tube
        mesh = MeshTube(name="Test Database", storage_path="data")
        print("✓ Successfully created MeshTube instance")
        
        # Add some nodes
        node1 = mesh.add_node(
            content={"topic": "Test Topic 1", "description": "First test topic"},
            time=0,
            distance=0.1,
            angle=0
        )
        print(f"✓ Added node 1: {node1.node_id}")
        
        node2 = mesh.add_node(
            content={"topic": "Test Topic 2", "description": "Second test topic"},
            time=1,
            distance=0.3,
            angle=45
        )
        print(f"✓ Added node 2: {node2.node_id}")
        
        # Connect the nodes
        mesh.connect_nodes(node1.node_id, node2.node_id)
        print("✓ Connected nodes")
        
        # Retrieve a node
        retrieved_node = mesh.get_node(node1.node_id)
        if retrieved_node:
            print(f"✓ Retrieved node: {retrieved_node.content['topic']}")
        else:
            print("✗ Failed to retrieve node")
        
        # Test temporal slice
        nodes_at_time_0 = mesh.get_temporal_slice(time=0, tolerance=0.1)
        print(f"✓ Found {len(nodes_at_time_0)} nodes at time 0")
        
        # Test nearest nodes
        nearest = mesh.get_nearest_nodes(node1, limit=5)
        print(f"✓ Found {len(nearest)} nearest nodes")
        
        # Apply a delta update
        delta_node = mesh.apply_delta(
            original_node=node1,
            delta_content={"update": "Updated content for topic 1"},
            time=0.5
        )
        print(f"✓ Applied delta update, new node: {delta_node.node_id}")
        
        # Test computing node state
        state = mesh.compute_node_state(node1.node_id)
        print(f"✓ Computed node state: {state}")
        
        # Test saving and loading
        save_path = os.path.join("data", "test_db.json")
        mesh.save(save_path)
        print(f"✓ Saved database to {save_path}")
        
        # Test loading
        loaded_mesh = MeshTube.load(save_path)
        print(f"✓ Loaded database with {len(loaded_mesh.nodes)} nodes")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    print("==== Testing Mesh Tube Knowledge Database ====")
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Run the test
    success = test_mesh_tube()
    
    if success:
        print("\n==== All tests passed! ====")
    else:
        print("\n==== Test failed! ====")
        sys.exit(1)

if __name__ == "__main__":
    main() 
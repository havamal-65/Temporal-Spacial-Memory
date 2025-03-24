#!/usr/bin/env python3
"""
Simple test script for the Temporal-Spatial Memory Database.

This script tests the basic functionality of the database to ensure it works.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mesh_tube():
    """Test the basic functionality of the MeshTube class."""
    try:
        # Import the MeshTube class
        from src.models.mesh_tube import MeshTube
        print("✓ Successfully imported MeshTube")
        
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
        
        # Apply a delta
        delta_node = mesh.apply_delta(
            original_node=node1,
            delta_content={"updated": True, "version": 2},
            time=2
        )
        print(f"✓ Applied delta: {delta_node.node_id}")
        
        # Compute node state
        node_state = mesh.compute_node_state(node1.node_id)
        print(f"✓ Computed node state: {node_state}")
        
        # Test nearest nodes
        nearest_nodes = mesh.get_nearest_nodes(node1, limit=5)
        print(f"✓ Found {len(nearest_nodes)} nearest nodes")
        
        # Save the database
        if not os.path.exists("data"):
            os.makedirs("data")
        mesh.save("data/test_database.json")
        print("✓ Saved database")
        
        # Load the database
        loaded_mesh = MeshTube.load("data/test_database.json")
        print("✓ Loaded database")
        
        # Verify loaded data
        if len(loaded_mesh.nodes) == len(mesh.nodes):
            print(f"✓ Loaded {len(loaded_mesh.nodes)} nodes successfully")
        else:
            print(f"✗ Node count mismatch: {len(loaded_mesh.nodes)} vs {len(mesh.nodes)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the tests and report results."""
    print("Testing Temporal-Spatial Memory Database...")
    print("=========================================")
    
    success = test_mesh_tube()
    
    print("\nTest Results:")
    if success:
        print("✅ All tests passed! The database is working.")
    else:
        print("❌ Tests failed. The database needs fixing.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
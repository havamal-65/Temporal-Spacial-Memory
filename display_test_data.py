#!/usr/bin/env python3
"""
Script to generate and display sample test data for the Mesh Tube Knowledge Database.
"""

import random
import json
from src.models.mesh_tube import MeshTube
from src.models.node import Node
from typing import List, Dict, Any

def generate_sample_data(num_nodes=50, time_span=100):
    """Generate a smaller sample of test data and return it"""
    random.seed(42)  # For reproducible results
    mesh_tube = MeshTube("sample_data")
    
    # Create nodes with random content
    nodes = []
    for i in range(num_nodes):
        # Generate random position
        t = random.uniform(0, time_span)
        distance = random.uniform(0, 10)
        angle = random.uniform(0, 360)
        
        # Create content
        content = {
            f"key_{i}": f"value_{i}",
            "timestamp": t,
            "importance": random.uniform(0, 1)
        }
        
        # Add node
        node = mesh_tube.add_node(
            content=content,
            time=t,
            distance=distance,
            angle=angle
        )
        nodes.append(node)
        
        # Create some connections
        if i > 0:
            # Connect to some previous nodes
            for _ in range(min(3, i)):
                prev_idx = random.randint(0, i-1)
                mesh_tube.connect_nodes(node.node_id, nodes[prev_idx].node_id)
    
    # Create delta chains
    for i in range(1, num_nodes, 5):
        # Choose a random node to create deltas from
        base_idx = random.randint(0, num_nodes-1)
        base_node = nodes[base_idx]
        
        # Create a chain of delta nodes
        prev_node = base_node
        for j in range(3):  # Create chain of 3 deltas
            # Calculate new position (forward in time)
            new_time = prev_node.time + random.uniform(0.1, 1.0)
            if new_time > time_span:
                break
                
            # Create delta content (small changes)
            delta_content = {
                f"delta_key_{j}": f"delta_value_{j}",
                "modified_at": new_time
            }
            
            # Apply delta
            delta_node = mesh_tube.apply_delta(
                original_node=prev_node,
                delta_content=delta_content,
                time=new_time
            )
            
            prev_node = delta_node
            nodes.append(delta_node)
    
    return mesh_tube, nodes

def node_to_display_dict(node: Node) -> Dict[str, Any]:
    """Convert a node to a clean dictionary for display"""
    return {
        "id": node.node_id[:8] + "...",  # Truncate ID for readability
        "content": node.content,
        "time": node.time,
        "distance": node.distance,
        "angle": node.angle,
        "parent_id": node.parent_id[:8] + "..." if node.parent_id else None,
        "connections": len(node.connections),
        "delta_references": [ref_id[:8] + "..." for ref_id in node.delta_references]
    }

def display_sample_data(mesh_tube: MeshTube, nodes: List[Node]):
    """Display sample data in a readable format"""
    # Basic statistics
    print(f"Generated sample database with {len(mesh_tube.nodes)} nodes")
    print(f"Time range: {min(n.time for n in nodes):.2f} to {max(n.time for n in nodes):.2f}")
    
    # Display a few sample nodes
    print("\n== Sample Nodes ==")
    for i, node in enumerate(random.sample(nodes, min(5, len(nodes)))):
        node_dict = node_to_display_dict(node)
        print(f"\nNode {i+1}:")
        print(json.dumps(node_dict, indent=2))
    
    # Display a sample delta chain
    print("\n== Sample Delta Chain ==")
    # Find a node with delta references
    delta_nodes = [node for node in nodes if node.delta_references]
    if delta_nodes:
        chain_start = random.choice(delta_nodes)
        chain = mesh_tube._get_delta_chain(chain_start)
        print(f"Delta chain with {len(chain)} nodes:")
        for i, node in enumerate(sorted(chain, key=lambda n: n.time)):
            print(f"\nChain Node {i+1} (time={node.time:.2f}):")
            print(json.dumps(node_to_display_dict(node), indent=2))
            
        # Show computed state of the node
        print("\nComputed full state:")
        state = mesh_tube.compute_node_state(chain_start.node_id)
        print(json.dumps(state, indent=2))
    else:
        print("No delta chains found in sample data")
    
    # Display nearest neighbors example
    print("\n== Nearest Neighbors Example ==")
    sample_node = random.choice(nodes)
    nearest = mesh_tube.get_nearest_nodes(sample_node, limit=3)
    print(f"Nearest neighbors to node at position (time={sample_node.time:.2f}, distance={sample_node.distance:.2f}, angle={sample_node.angle:.2f}):")
    for i, (node, distance) in enumerate(nearest):
        print(f"\nNeighbor {i+1} (distance={distance:.2f}):")
        print(json.dumps(node_to_display_dict(node), indent=2))

def main():
    """Generate and display sample data"""
    print("Generating sample data...")
    mesh_tube, nodes = generate_sample_data(num_nodes=50)
    display_sample_data(mesh_tube, nodes)

if __name__ == "__main__":
    main() 
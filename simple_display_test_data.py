#!/usr/bin/env python3
"""
Simple script to generate and display sample test data for the Mesh Tube Knowledge Database.
This version doesn't use Rtree to avoid installation issues.
"""

import random
import json
import uuid
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set

# Simplified Node class for demonstration
class SimpleNode:
    def __init__(self, 
                content: Dict[str, Any],
                time: float,
                distance: float,
                angle: float,
                node_id: Optional[str] = None,
                parent_id: Optional[str] = None):
        self.node_id = node_id if node_id else str(uuid.uuid4())
        self.content = content
        self.time = time
        self.distance = distance
        self.angle = angle
        self.parent_id = parent_id
        self.created_at = datetime.now()
        self.connections: Set[str] = set()
        self.delta_references: List[str] = []
        
        if parent_id:
            self.delta_references.append(parent_id)
    
    def add_connection(self, node_id: str) -> None:
        self.connections.add(node_id)
    
    def add_delta_reference(self, node_id: str) -> None:
        if node_id not in self.delta_references:
            self.delta_references.append(node_id)
            
    def spatial_distance(self, other_node: 'SimpleNode') -> float:
        # Calculate distance in cylindrical coordinates
        r1, theta1, z1 = self.distance, self.angle, self.time
        r2, theta2, z2 = other_node.distance, other_node.angle, other_node.time
        
        # Convert angles from degrees to radians
        theta1_rad = math.radians(theta1)
        theta2_rad = math.radians(theta2)
        
        # Cylindrical coordinate distance formula
        distance = math.sqrt(
            r1**2 + r2**2 - 
            2 * r1 * r2 * math.cos(theta1_rad - theta2_rad) + 
            (z1 - z2)**2
        )
        
        return distance

# Simplified MeshTube class for demonstration
class SimpleMeshTube:
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, SimpleNode] = {}
        self.created_at = datetime.now()
        self.last_modified = self.created_at
    
    def add_node(self, 
                content: Dict[str, Any],
                time: float,
                distance: float,
                angle: float,
                parent_id: Optional[str] = None) -> SimpleNode:
        node = SimpleNode(
            content=content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=parent_id
        )
        
        self.nodes[node.node_id] = node
        self.last_modified = datetime.now()
        
        return node
    
    def get_node(self, node_id: str) -> Optional[SimpleNode]:
        return self.nodes.get(node_id)
    
    def connect_nodes(self, node_id1: str, node_id2: str) -> bool:
        node1 = self.get_node(node_id1)
        node2 = self.get_node(node_id2)
        
        if not node1 or not node2:
            return False
        
        node1.add_connection(node2.node_id)
        node2.add_connection(node1.node_id)
        self.last_modified = datetime.now()
        
        return True
    
    def apply_delta(self, 
                   original_node: SimpleNode, 
                   delta_content: Dict[str, Any],
                   time: float,
                   distance: Optional[float] = None,
                   angle: Optional[float] = None) -> SimpleNode:
        # Use original values for spatial coordinates if not provided
        if distance is None:
            distance = original_node.distance
            
        if angle is None:
            angle = original_node.angle
            
        # Create a new node with the delta content
        delta_node = self.add_node(
            content=delta_content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=original_node.node_id
        )
        
        # Make sure we have the reference
        delta_node.add_delta_reference(original_node.node_id)
        
        return delta_node
    
    def compute_node_state(self, node_id: str) -> Dict[str, Any]:
        node = self.get_node(node_id)
        if not node:
            return {}
            
        # If no delta references, return the node's content directly
        if not node.delta_references:
            return node.content
            
        # Start with an empty state
        computed_state = {}
        
        # Find all nodes in the reference chain
        chain = self._get_delta_chain(node)
        
        # Apply deltas in chronological order (oldest first)
        for delta_node in sorted(chain, key=lambda n: n.time):
            # Update the state with this node's content
            computed_state.update(delta_node.content)
            
        return computed_state
    
    def _get_delta_chain(self, node: SimpleNode) -> List[SimpleNode]:
        chain = [node]
        processed_ids = {node.node_id}
        
        # Process queue of nodes to check for references
        queue = list(node.delta_references)
        
        while queue:
            ref_id = queue.pop(0)
            if ref_id in processed_ids:
                continue
                
            ref_node = self.get_node(ref_id)
            if ref_node:
                chain.append(ref_node)
                processed_ids.add(ref_id)
                
                # Add any new references to the queue
                for new_ref in ref_node.delta_references:
                    if new_ref not in processed_ids:
                        queue.append(new_ref)
        
        return chain
    
    def get_nearest_nodes(self, 
                         reference_node: SimpleNode, 
                         limit: int = 10) -> List[Tuple[SimpleNode, float]]:
        distances = []
        
        for node in self.nodes.values():
            if node.node_id == reference_node.node_id:
                continue
                
            distance = reference_node.spatial_distance(node)
            distances.append((node, distance))
        
        # Sort by distance and return the closest ones
        distances.sort(key=lambda x: x[1])
        return distances[:limit]

def generate_sample_data(num_nodes=50, time_span=100):
    """Generate a smaller sample of test data and return it"""
    random.seed(42)  # For reproducible results
    mesh_tube = SimpleMeshTube("sample_data")
    
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

def node_to_display_dict(node: SimpleNode) -> Dict[str, Any]:
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

def display_sample_data(mesh_tube: SimpleMeshTube, nodes: List[SimpleNode]):
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
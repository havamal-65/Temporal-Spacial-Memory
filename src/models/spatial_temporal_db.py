#!/usr/bin/env python3
"""
SpatialTemporalDB - A cylindrical mesh database for storing temporal-spatial memory.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from .node import Node
# Assuming delta optimizer might still be relevant or refactored later
# If DeltaOptimizer is tightly coupled only to the old MeshTube name, this might need adjustment
from src.delta.delta_optimizer import DeltaOptimizer 

class SpatialTemporalDB:
    """
    A cylindrical mesh database for storing temporal-spatial memory.
    The database organizes nodes in a cylindrical coordinate system:
    - time: vertical axis (newer items higher)
    - distance: radial distance from center
    - angle: angular position around the center
    """
    
    def __init__(self, name: str = "memory", storage_path: str = "data"):
        """
        Initialize a new SpatialTemporalDB database.
        
        Args:
            name: Name of the database
            storage_path: Path to store database files
        """
        self.name = name
        self.storage_path = storage_path
        self.nodes: Dict[str, Node] = {}  # node_id -> Node
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
    
    def add_node(self, 
                content: Dict[str, Any],
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None) -> Node:
        """
        Add a new node to the database.
        
        Args:
            content: Node content (dictionary)
            time: Vertical position (0 = present)
            distance: Radial distance from center
            angle: Angular position (0-360 degrees)
            parent_id: Optional ID of parent node
            
        Returns:
            The created Node object
        """
        # Create new node
        node = Node(
            node_id=str(uuid.uuid4()),
            content=content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=parent_id,
            created_at=datetime.now().isoformat()
        )
        
        # Add to database
        self.nodes[node.node_id] = node
        
        return node
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID"""
        return self.nodes.get(node_id)
    
    def connect_nodes(self, source_id: str, target_id: str) -> bool:
        """
        Create a bidirectional connection between two nodes.
        
        Args:
            source_id: ID of source node
            target_id: ID of target node
            
        Returns:
            True if connection was created, False if either node not found
        """
        source = self.nodes.get(source_id)
        target = self.nodes.get(target_id)
        
        if not source or not target:
            return False
        
        # Add bidirectional connection
        source.connections.add(target_id)
        target.connections.add(source_id)
        
        return True
    
    def get_connected_nodes(self, node_id: str) -> List[Node]:
        """Get all nodes connected to the given node"""
        node = self.nodes.get(node_id)
        if not node:
            return []
            
        return [self.nodes[conn_id] for conn_id in node.connections 
                if conn_id in self.nodes]
    
    def get_temporal_slice(self, time: float, tolerance: float = 0.1) -> List[Node]:
        """
        Get all nodes at a specific time point (within tolerance).
        
        Args:
            time: Time point to query
            tolerance: How close to time point to include
            
        Returns:
            List of nodes at that time
        """
        return [node for node in self.nodes.values()
                if abs(node.time - time) <= tolerance]
    
    def get_spatial_region(self, 
                        min_distance: float,
                        max_distance: float,
                        min_angle: float,
                        max_angle: float) -> List[Node]:
        """
        Get nodes within a spatial region.
        
        Args:
            min_distance: Minimum radial distance
            max_distance: Maximum radial distance
            min_angle: Minimum angle (degrees)
            max_angle: Maximum angle (degrees)
            
        Returns:
            List of nodes in the region
        """
        return [node for node in self.nodes.values()
                if min_distance <= node.distance <= max_distance
                and min_angle <= node.angle <= max_angle]
    
    def search_by_content(self, query: str) -> List[Node]:
        """
        Search for nodes with content matching query.
        Simple string matching for now.
        
        Args:
            query: Search string
            
        Returns:
            List of matching nodes
        """
        query = query.lower()
        matches = []
        
        for node in self.nodes.values():
            # Convert content to string for searching
            content_str = str(node.content).lower()
            if query in content_str:
                matches.append(node)
                
        return matches
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node by ID."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            # Optionally, remove connections pointing to this node from others
            for other_node in self.nodes.values():
                if node_id in other_node.connections:
                    other_node.connections.remove(node_id)
            return True
        return False
    
    def save(self) -> None:
        """Save the database to disk"""
        # Convert to serializable format
        data = {
            "name": self.name,
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            }
        }
        
        # Save to file
        filepath = os.path.join(self.storage_path, f"{self.name}.json")
        print(f"Attempting to save DB to: {filepath}")
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Successfully saved DB to: {filepath}")
        except Exception as e:
            print(f"ERROR saving DB to {filepath}: {e}")
    
    def load(self) -> None:
        """Load the database from disk"""
        filepath = os.path.join(self.storage_path, f"{self.name}.json")
        
        if not os.path.exists(filepath):
            print(f"Database file not found: {filepath}")
            return
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            self.name = data.get("name", self.name)
            
            # Clear existing nodes
            self.nodes.clear()
            
            # Load nodes
            if "nodes" in data:
                for node_id, node_data in data["nodes"].items():
                    try:
                        # First try the standard Node.from_dict method
                        node = Node.from_dict(node_data)
                        
                        # If that failed, try creating a node directly
                        if not node and all(k in node_data for k in ["node_id", "content", "time", "distance", "angle"]):
                            node = Node(
                                node_id=node_data["node_id"],
                                content=node_data["content"],
                                time=node_data["time"],
                                distance=node_data["distance"],
                                angle=node_data["angle"],
                                parent_id=node_data.get("parent_id"),
                                created_at=node_data.get("created_at")
                            )
                            
                            # Manually add connections and delta_references
                            if "connections" in node_data and isinstance(node_data["connections"], list):
                                node.connections = set(node_data["connections"])
                                
                            if "delta_references" in node_data and isinstance(node_data["delta_references"], list):
                                node.delta_references = node_data["delta_references"]
                        
                        # Add the node to our database if valid
                        if node and node.content:
                            self.nodes[node_id] = node
                    except Exception as e:
                        print(f"Error loading node {node_id}: {str(e)}")
                        continue
                
                print(f"Loaded {len(self.nodes)} nodes from database.")
            else:
                print("No nodes found in database.")
                
        except Exception as e:
            print(f"Error loading database: {str(e)}")

    def apply_delta(self, original_node: Node, delta_content: dict, time: float = None) -> Node:
        """Apply a delta to a node and return the new node."""
        # Construct the delta with a changes dict for patching
        delta = {"changes": {"content": {"new": delta_content}}}
        # Pass original_node.content (dict) instead of Node
        new_content = DeltaOptimizer.apply_delta(original_node.content, delta)
        # Create a new Node with the merged content and other properties copied from original_node
        new_node = Node(
            node_id=original_node.node_id,
            content=new_content,
            time=original_node.time if time is None else time,
            distance=original_node.distance,
            angle=original_node.angle,
            parent_id=original_node.parent_id,
            created_at=datetime.now().isoformat(),
            connections=original_node.connections, # Copy connections
            delta_references=original_node.delta_references + [delta] # Append new delta
        )
        # Update the node in the database
        self.nodes[original_node.node_id] = new_node
        return new_node

    def compute_node_state(self, node_id: str) -> dict:
        """Compute the current state of a node by applying all its deltas."""
        # This might be complex if deltas are stored separately.
        # Assuming deltas are stored within the node object for now.
        node = self.get_node(node_id)
        if not node:
            return {}
        
        # The current node object already reflects the latest state
        # if apply_delta updates self.nodes[node_id]
        return node.content 
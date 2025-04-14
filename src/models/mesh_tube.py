#!/usr/bin/env python3
"""
MeshTube - A cylindrical mesh database for storing temporal-spatial memory.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from .node import Node

class MeshTube:
    """
    A cylindrical mesh database for storing temporal-spatial memory.
    The database organizes nodes in a cylindrical coordinate system:
    - time: vertical axis (newer items higher)
    - distance: radial distance from center
    - angle: angular position around the center
    """
    
    def __init__(self, name: str = "memory", storage_path: str = "data"):
        """
        Initialize a new MeshTube database.
        
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
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
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
#!/usr/bin/env python3
"""
Node class for the Temporal-Spatial Memory Database.
"""

import uuid
from typing import Dict, Any, Set, List, Optional

class Node:
    """
    A node in the cylindrical mesh database.
    Each node has:
    - A unique ID
    - Content (any JSON-serializable data)
    - Temporal-spatial coordinates (time, distance, angle)
    - Connections to other nodes
    """
    
    def __init__(self,
                node_id: Optional[str] = None,
                content: Dict[str, Any] = None,
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None,
                created_at: Optional[str] = None):
        """
        Initialize a new node.
        
        Args:
            node_id: Unique identifier (generated if not provided)
            content: Node content (dictionary)
            time: Vertical position (0 = present)
            distance: Radial distance from center
            angle: Angular position (0-360 degrees)
            parent_id: Optional ID of parent node
            created_at: Creation timestamp (ISO format)
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.content = content or {}
        self.time = time
        self.distance = distance
        self.angle = angle
        self.parent_id = parent_id
        self.created_at = created_at
        
        # Set of connected node IDs
        self.connections: Set[str] = set()
        
        # List of nodes this node references for delta updates
        self.delta_references: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "time": self.time,
            "distance": self.distance,
            "angle": self.angle,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "connections": list(self.connections),
            "delta_references": self.delta_references
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create a node from a dictionary"""
        try:
            # Check if the required keys are present
            required_keys = ["node_id", "content", "time", "distance", "angle"]
            for key in required_keys:
                if key not in data:
                    return None
            
            # Create the node
            node = cls(
                node_id=data["node_id"],
                content=data["content"],
                time=data["time"],
                distance=data["distance"],
                angle=data["angle"],
                parent_id=data.get("parent_id"),
                created_at=data.get("created_at")
            )
            
            # Restore connections
            if "connections" in data and isinstance(data["connections"], list):
                node.connections = set(data["connections"])
                
            if "delta_references" in data and isinstance(data["delta_references"], list):
                node.delta_references = data["delta_references"]
            
            # Validate the node
            if not node.content:
                return None
                
            return node
            
        except Exception as e:
            print(f"Error creating node from dictionary: {str(e)}")
            return None 
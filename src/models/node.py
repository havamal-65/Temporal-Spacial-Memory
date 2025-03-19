from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid
import math

class Node:
    """
    Represents a node in the Mesh Tube Knowledge Database.
    
    Each node has a unique 3D position in the mesh tube:
    - time: position along the longitudinal axis (temporal dimension)
    - distance: radial distance from the center (relevance to core topic)
    - angle: angular position (conceptual relationship)
    """
    
    def __init__(self, 
                 content: Dict[str, Any],
                 time: float,
                 distance: float,
                 angle: float,
                 node_id: Optional[str] = None,
                 parent_id: Optional[str] = None):
        """
        Initialize a new Node in the Mesh Tube.
        
        Args:
            content: The actual data stored in this node
            time: Temporal coordinate (longitudinal position)
            distance: Radial distance from tube center (relevance measure)
            angle: Angular position around the tube (topic relationship)
            node_id: Unique identifier for this node (generated if not provided)
            parent_id: ID of parent node (for delta references)
        """
        self.node_id = node_id if node_id else str(uuid.uuid4())
        self.content = content
        self.time = time
        self.distance = distance  # 0 = center (core topics), higher = less relevant
        self.angle = angle  # 0-360 degrees, represents conceptual relationships
        self.parent_id = parent_id
        self.created_at = datetime.now()
        self.connections: Set[str] = set()  # IDs of connected nodes
        self.delta_references: List[str] = []  # Temporal predecessors
        
        if parent_id:
            self.delta_references.append(parent_id)
    
    def add_connection(self, node_id: str) -> None:
        """Add a connection to another node"""
        self.connections.add(node_id)
    
    def remove_connection(self, node_id: str) -> None:
        """Remove a connection to another node"""
        if node_id in self.connections:
            self.connections.remove(node_id)
    
    def add_delta_reference(self, node_id: str) -> None:
        """Add a temporal predecessor reference"""
        if node_id not in self.delta_references:
            self.delta_references.append(node_id)
            
    def spatial_distance(self, other_node: 'Node') -> float:
        """
        Calculate the spatial distance between this node and another node in the mesh.
        Uses cylindrical coordinate system distance formula.
        """
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for storage"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "time": self.time,
            "distance": self.distance,
            "angle": self.angle,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "connections": list(self.connections),
            "delta_references": self.delta_references
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create a node from dictionary data"""
        node = cls(
            content=data["content"],
            time=data["time"],
            distance=data["distance"],
            angle=data["angle"],
            node_id=data["node_id"],
            parent_id=data.get("parent_id")
        )
        node.created_at = datetime.fromisoformat(data["created_at"])
        node.connections = set(data["connections"])
        node.delta_references = data["delta_references"]
        return node 
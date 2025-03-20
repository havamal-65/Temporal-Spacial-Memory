"""
Node structure implementation for the Temporal-Spatial Knowledge Database v2.

This module defines the primary data structures used to represent knowledge points
in three-dimensional cylindrical coordinates (time, radius, theta).
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple, Set, Union
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class NodeConnection:
    """
    Represents a connection between nodes in the knowledge graph.
    
    Attributes:
        target_id: UUID of the target node
        connection_type: Type of connection (e.g., "reference", "association", "causal")
        strength: Weight or strength of the connection (0.0 to 1.0)
        metadata: Additional metadata for the connection
    """
    target_id: UUID
    connection_type: str
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the connection after initialization."""
        # Ensure strength is between 0 and 1
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Connection strength must be between 0.0 and 1.0")
            
        # Ensure target_id is a UUID
        if isinstance(self.target_id, str):
            self.target_id = UUID(self.target_id)


@dataclass
class Node:
    """
    Node representing a knowledge point in the temporal-spatial database.
    
    Each node has a unique identifier, content data, and a position in 
    three-dimensional cylindrical coordinates (time, radius, theta).
    
    Attributes:
        id: Unique identifier for the node
        content: Dictionary containing the node's content data
        position: (time, radius, theta) coordinates
        connections: List of connections to other nodes
        origin_reference: Optional reference to originating node
        delta_information: Information about changes if this is a delta node
        metadata: Additional node metadata
    """
    id: UUID = field(default_factory=uuid.uuid4)
    content: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[float, float, float] = field(default=None)  # (t, r, θ)
    connections: List[NodeConnection] = field(default_factory=list)
    origin_reference: Optional[UUID] = None
    delta_information: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the node after initialization."""
        # Ensure position is a tuple of three floats
        if self.position is None:
            self.position = (0.0, 0.0, 0.0)  # Default position at origin
        elif not isinstance(self.position, tuple) or len(self.position) != 3:
            raise ValueError("Position must be a tuple of (time, radius, theta)")
        
        # Ensure id is a UUID
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        
        # Ensure origin_reference is a UUID if it exists
        if isinstance(self.origin_reference, str):
            self.origin_reference = UUID(self.origin_reference)
    
    def add_connection(self, target_id: Union[UUID, str], connection_type: str, 
                      strength: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a connection to another node.
        
        Args:
            target_id: UUID of the target node
            connection_type: Type of connection (e.g., "reference", "association")
            strength: Weight or strength of the connection (0.0 to 1.0)
            metadata: Additional metadata for the connection
        """
        connection = NodeConnection(
            target_id=UUID(target_id) if isinstance(target_id, str) else target_id,
            connection_type=connection_type,
            strength=strength,
            metadata=metadata or {}
        )
        self.connections.append(connection)
    
    def get_connections_by_type(self, connection_type: str) -> List[NodeConnection]:
        """Get all connections of a specific type."""
        return [conn for conn in self.connections if conn.connection_type == connection_type]
    
    def distance_to(self, other: Node) -> float:
        """
        Calculate distance to another node in cylindrical coordinates.
        
        Distance calculation in cylindrical coordinates (t, r, θ) requires
        special handling for the angular component.
        
        Args:
            other: The node to calculate distance to
            
        Returns:
            The Euclidean distance between the nodes
        """
        t1, r1, theta1 = self.position
        t2, r2, theta2 = other.position
        
        # Calculate Euclidean distance for time and radius
        dt = t2 - t1
        dr = r2 - r1
        
        # For the angular component, we need to handle the circular nature of θ
        # We use the smaller of the two possible angular distances
        dtheta = min(abs(theta2 - theta1), 2 * 3.14159 - abs(theta2 - theta1))
        
        # The arc length depends on the radius (r1 and r2)
        # We use the average radius to calculate the arc length
        avg_r = (r1 + r2) / 2
        arc_length = avg_r * dtheta
        
        # Calculate the total Euclidean distance
        return (dt**2 + dr**2 + arc_length**2)**0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        return {
            'id': str(self.id),
            'content': self.content,
            'position': self.position,
            'connections': [
                {
                    'target_id': str(conn.target_id),
                    'connection_type': conn.connection_type,
                    'strength': conn.strength,
                    'metadata': conn.metadata
                }
                for conn in self.connections
            ],
            'origin_reference': str(self.origin_reference) if self.origin_reference else None,
            'delta_information': self.delta_information,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        """Create a node from a dictionary representation."""
        # Convert connections from dict to NodeConnection objects
        connections = []
        for conn_data in data.get('connections', []):
            connections.append(NodeConnection(
                target_id=UUID(conn_data['target_id']),
                connection_type=conn_data['connection_type'],
                strength=conn_data['strength'],
                metadata=conn_data.get('metadata', {})
            ))
        
        # Convert UUID strings to UUID objects
        node_id = UUID(data['id']) if isinstance(data['id'], str) else data['id']
        origin_ref = None
        if data.get('origin_reference'):
            origin_ref = UUID(data['origin_reference']) if isinstance(data['origin_reference'], str) else data['origin_reference']
        
        return cls(
            id=node_id,
            content=data.get('content', {}),
            position=data.get('position', (0.0, 0.0, 0.0)),
            connections=connections,
            origin_reference=origin_ref,
            delta_information=data.get('delta_information', {}),
            metadata=data.get('metadata', {})
        ) 
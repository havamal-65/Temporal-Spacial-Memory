"""
Node data structure implementation for the Temporal-Spatial Knowledge Database.

This module defines the primary data structure used to represent knowledge points
in the multidimensional space-time continuum.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Set, Tuple
import uuid
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
from .exceptions import NodeError


@dataclass(frozen=True)
class Node:
    """
    Immutable node representing a knowledge point in the temporal-spatial database.
    
    Each node has a unique identifier, coordinates in both space and time,
    and arbitrary payload data. Nodes are immutable to ensure consistency
    when traversing historical states.
    
    Attributes:
        id: Unique identifier for the node
        coordinates: Spatial and temporal coordinates of the node
        data: Arbitrary payload data
        created_at: Creation timestamp
        references: IDs of other nodes this node references
        metadata: Additional node metadata
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    coordinates: Coordinates
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    references: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the node after initialization."""
        if not isinstance(self.coordinates, Coordinates):
            object.__setattr__(self, 'coordinates', Coordinates(
                spatial=self.coordinates.get('spatial') if isinstance(self.coordinates, dict) else None,
                temporal=self.coordinates.get('temporal') if isinstance(self.coordinates, dict) else None
            ))
    
    def with_data(self, new_data: Dict[str, Any]) -> Node:
        """Create a new node with updated data."""
        return Node(
            id=self.id,
            coordinates=self.coordinates,
            data={**self.data, **new_data},
            created_at=self.created_at,
            references=self.references.copy(),
            metadata=self.metadata.copy()
        )
    
    def with_coordinates(self, new_coordinates: Coordinates) -> Node:
        """Create a new node with updated coordinates."""
        return Node(
            id=self.id,
            coordinates=new_coordinates,
            data=self.data.copy(),
            created_at=self.created_at,
            references=self.references.copy(),
            metadata=self.metadata.copy()
        )
    
    def with_references(self, new_references: Set[str]) -> Node:
        """Create a new node with updated references."""
        return Node(
            id=self.id,
            coordinates=self.coordinates,
            data=self.data.copy(),
            created_at=self.created_at,
            references=new_references,
            metadata=self.metadata.copy()
        )
    
    def add_reference(self, reference_id: str) -> Node:
        """Create a new node with an additional reference."""
        new_references = self.references.copy()
        new_references.add(reference_id)
        return self.with_references(new_references)
    
    def remove_reference(self, reference_id: str) -> Node:
        """Create a new node with a reference removed."""
        if reference_id not in self.references:
            return self
        
        new_references = self.references.copy()
        new_references.remove(reference_id)
        return self.with_references(new_references)
    
    def distance_to(self, other: Node) -> float:
        """Calculate the distance to another node in the coordinate space."""
        return self.coordinates.distance_to(other.coordinates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        return {
            'id': self.id,
            'coordinates': self.coordinates.to_dict(),
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'references': list(self.references),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        """Create a node from a dictionary representation."""
        if 'id' not in data or 'coordinates' not in data:
            raise NodeError("Missing required fields for node creation")
        
        # Convert created_at from ISO format string to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Convert coordinates dictionary to Coordinates object
        if isinstance(data['coordinates'], dict):
            data['coordinates'] = Coordinates.from_dict(data['coordinates'])
        
        # Convert references list to set
        if 'references' in data and isinstance(data['references'], list):
            data['references'] = set(data['references'])
            
        return cls(**data) 
"""
Coordinate system implementation for the Temporal-Spatial Knowledge Database.

This module defines the coordinate system used to locate nodes in both
spatial and temporal dimensions.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import math

from .exceptions import CoordinateError, TemporalError, SpatialError


@dataclass(frozen=True)
class SpatialCoordinate:
    """
    Represents a point in n-dimensional space.
    
    Attributes:
        dimensions: A tuple containing the coordinates in each dimension
    """
    dimensions: Tuple[float, ...] = field(default_factory=tuple)
    
    def __post_init__(self):
        """Validate the dimensions."""
        if not isinstance(self.dimensions, tuple):
            dims = tuple(self.dimensions) if hasattr(self.dimensions, '__iter__') else (0.0,)
            object.__setattr__(self, 'dimensions', dims)
    
    @property
    def dimensionality(self) -> int:
        """Return the number of dimensions."""
        return len(self.dimensions)
    
    def distance_to(self, other: SpatialCoordinate) -> float:
        """Calculate Euclidean distance to another spatial coordinate."""
        if not isinstance(other, SpatialCoordinate):
            raise SpatialError("Can only calculate distance to another SpatialCoordinate")
        
        # Handle different dimensionality by padding with zeros
        max_dim = max(self.dimensionality, other.dimensionality)
        self_dims = self.dimensions + (0.0,) * (max_dim - self.dimensionality)
        other_dims = other.dimensions + (0.0,) * (max_dim - other.dimensionality)
        
        # Calculate Euclidean distance
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self_dims, other_dims)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {'dimensions': self.dimensions}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpatialCoordinate:
        """Create from dictionary representation."""
        if 'dimensions' not in data:
            raise SpatialError("Missing 'dimensions' field in spatial coordinate data")
        
        dims = data['dimensions']
        if isinstance(dims, list):
            dims = tuple(dims)
        
        return cls(dimensions=dims)


@dataclass(frozen=True)
class TemporalCoordinate:
    """
    Represents a point in time.
    
    Attributes:
        timestamp: The timestamp value
        precision: Optional precision level (e.g., 'year', 'month', 'day', 'hour', etc.)
    """
    timestamp: datetime
    precision: str = 'second'  # Default precision
    
    PRECISION_LEVELS = {
        'year': 0,
        'month': 1,
        'day': 2,
        'hour': 3,
        'minute': 4,
        'second': 5,
        'microsecond': 6
    }
    
    def __post_init__(self):
        """Validate the temporal coordinate."""
        if not isinstance(self.timestamp, datetime):
            raise TemporalError("Timestamp must be a datetime object")
        
        if self.precision not in self.PRECISION_LEVELS:
            raise TemporalError(f"Invalid precision: {self.precision}. Must be one of {list(self.PRECISION_LEVELS.keys())}")
    
    def distance_to(self, other: TemporalCoordinate) -> float:
        """Calculate temporal distance in seconds."""
        if not isinstance(other, TemporalCoordinate):
            raise TemporalError("Can only calculate distance to another TemporalCoordinate")
        
        # Calculate difference in seconds
        delta = abs((self.timestamp - other.timestamp).total_seconds())
        return delta
    
    def precedes(self, other: TemporalCoordinate) -> bool:
        """Check if this temporal coordinate precedes another."""
        return self.timestamp < other.timestamp
    
    def equals_at_precision(self, other: TemporalCoordinate) -> bool:
        """
        Check if two temporal coordinates are equal at the specified precision.
        
        For example, if precision is 'day', then only year, month, and day
        are considered for equality comparison.
        """
        if not isinstance(other, TemporalCoordinate):
            return False
        
        # Determine the lowest precision level
        min_precision = min(
            self.PRECISION_LEVELS[self.precision],
            self.PRECISION_LEVELS[other.precision]
        )
        
        # Compare based on the precision level
        attributes = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
        attributes = attributes[:min_precision + 1]  # +1 because we want to include the precision level
        
        return all(
            getattr(self.timestamp, attr) == getattr(other.timestamp, attr)
            for attr in attributes
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'precision': self.precision
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TemporalCoordinate:
        """Create from dictionary representation."""
        if 'timestamp' not in data:
            raise TemporalError("Missing 'timestamp' field in temporal coordinate data")
        
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        precision = data.get('precision', 'second')
        
        return cls(timestamp=timestamp, precision=precision)


@dataclass(frozen=True)
class SpatioTemporalCoordinate:
    """
    Represents a coordinate in the temporal-spatial system.
    
    Attributes:
        t: Temporal coordinate (time dimension)
        r: Radial distance from central axis (relevance)
        theta: Angular position (conceptual relationship)
    """
    t: float
    r: float
    theta: float
    
    def as_tuple(self) -> Tuple[float, float, float]:
        """Return coordinates as a tuple (t, r, theta)"""
        return (self.t, self.r, self.theta)
        
    def distance_to(self, other: "SpatioTemporalCoordinate") -> float:
        """
        Calculate distance to another coordinate.
        
        Uses a weighted Euclidean distance with special handling
        for the angular coordinate.
        """
        # Calculate differences for each dimension
        t_diff = self.t - other.t
        r_diff = self.r - other.r
        
        # Special handling for angular dimension (circular space)
        theta_diff = min(
            abs(self.theta - other.theta),
            2 * math.pi - abs(self.theta - other.theta)
        )
        
        # Calculate weighted Euclidean distance
        # We apply weights to each dimension based on their importance
        # Default weights are 1.0 for now but can be parameterized in the future
        t_weight = 1.0
        r_weight = 1.0
        theta_weight = 1.0
        
        distance = math.sqrt(
            (t_weight * t_diff) ** 2 +
            (r_weight * r_diff) ** 2 +
            (theta_weight * theta_diff * min(self.r, other.r)) ** 2  # Scale angular difference by radius
        )
        
        return distance
        
    def to_cartesian(self) -> Tuple[float, float, float]:
        """Convert to cartesian coordinates (x, y, z)"""
        # For 3D visualization or certain calculations, convert to cartesian
        # Using t as z-axis, and (r, theta) as polar coordinates on x-y plane
        x = self.r * math.cos(self.theta)
        y = self.r * math.sin(self.theta)
        z = self.t
        
        return (x, y, z)
        
    @classmethod
    def from_cartesian(cls, x: float, y: float, z: float) -> "SpatioTemporalCoordinate":
        """Create coordinate from cartesian position"""
        # Calculate cylindrical coordinates from cartesian
        t = z
        r = math.sqrt(x ** 2 + y ** 2)
        theta = math.atan2(y, x)  # Returns in range [-pi, pi]
        
        # Normalize theta to [0, 2*pi) range
        if theta < 0:
            theta += 2 * math.pi
            
        return cls(t=t, r=r, theta=theta)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            't': self.t,
            'r': self.r,
            'theta': self.theta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpatioTemporalCoordinate":
        """Create from dictionary representation."""
        if not all(key in data for key in ('t', 'r', 'theta')):
            raise CoordinateError("Missing required field(s) in SpatioTemporalCoordinate data")
        
        return cls(
            t=float(data['t']),
            r=float(data['r']),
            theta=float(data['theta'])
        )


@dataclass(frozen=True)
class Coordinates:
    """
    Combined spatial and temporal coordinates.
    
    Attributes:
        spatial: Spatial coordinates
        temporal: Temporal coordinates
    """
    spatial: Optional[SpatialCoordinate] = None
    temporal: Optional[TemporalCoordinate] = None
    
    def __post_init__(self):
        """Validate the coordinates."""
        # At least one of spatial or temporal must be provided
        if self.spatial is None and self.temporal is None:
            raise CoordinateError("At least one of spatial or temporal coordinates must be provided")
        
        # Convert spatial dictionary to SpatialCoordinate if needed
        if isinstance(self.spatial, dict):
            object.__setattr__(self, 'spatial', SpatialCoordinate.from_dict(self.spatial))
        
        # Convert temporal dictionary to TemporalCoordinate if needed
        if isinstance(self.temporal, dict):
            object.__setattr__(self, 'temporal', TemporalCoordinate.from_dict(self.temporal))
    
    def distance_to(self, other: Coordinates) -> float:
        """
        Calculate distance to another set of coordinates.
        
        This implementation uses a hybrid distance metric that combines
        spatial and temporal distances when both are available.
        """
        if not isinstance(other, Coordinates):
            raise CoordinateError("Can only calculate distance to another Coordinates object")
        
        spatial_dist = 0.0
        if self.spatial and other.spatial:
            spatial_dist = self.spatial.distance_to(other.spatial)
        
        temporal_dist = 0.0
        if self.temporal and other.temporal:
            # Normalize temporal distance
            temporal_dist = self.temporal.distance_to(other.temporal) / 86400.0  # Normalize to days
        
        # If only one dimension is available, return distance in that dimension
        if self.spatial is None or other.spatial is None:
            return temporal_dist
        if self.temporal is None or other.temporal is None:
            return spatial_dist
        
        # Otherwise return Euclidean combination of spatial and temporal distances
        return math.sqrt(spatial_dist**2 + temporal_dist**2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.spatial:
            result['spatial'] = self.spatial.to_dict()
        if self.temporal:
            result['temporal'] = self.temporal.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Coordinates:
        """Create from dictionary representation."""
        spatial = None
        if 'spatial' in data:
            spatial = SpatialCoordinate.from_dict(data['spatial'])
        
        temporal = None
        if 'temporal' in data:
            temporal = TemporalCoordinate.from_dict(data['temporal'])
        
        return cls(spatial=spatial, temporal=temporal) 
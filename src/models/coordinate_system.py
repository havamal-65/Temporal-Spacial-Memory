"""
Core Coordinate System for 4D Polar-Temporal Database

This module defines the fundamental 4D polar-temporal coordinate system:
- r: radial distance (relevance)
- θ: angular position (category/topic)
- t: temporal position (time)
- z: context layer
"""

import numpy as np
from typing import Tuple, List, Union, Dict, Optional


class PolarTemporalCoordinate:
    """
    Represents a point in the 4D polar-temporal space.
    """
    
    def __init__(self, r: float, theta: float, t: float, z: int):
        """
        Initialize a coordinate in 4D polar-temporal space.
        
        Args:
            r: Radial distance (relevance), where 0 is most relevant
            theta: Angular position in radians [0, 2π)
            t: Temporal position as timestamp or sequence number
            z: Context layer (discrete integer)
        """
        self.r = r
        self.theta = theta % (2 * np.pi)  # Normalize to [0, 2π)
        self.t = t
        self.z = z
    
    def __repr__(self) -> str:
        return f"PolarTemporalCoordinate(r={self.r:.2f}, θ={self.theta:.2f}, t={self.t:.2f}, z={self.z})"
    
    def to_cartesian(self) -> Tuple[float, float, float, float]:
        """
        Convert to 4D Cartesian coordinates for visualization or computation.
        
        Returns:
            Tuple containing (x, y, t, z) where x,y are derived from r,θ
        """
        x = self.r * np.cos(self.theta)
        y = self.r * np.sin(self.theta)
        return (x, y, self.t, self.z)
    
    @classmethod
    def from_cartesian(cls, x: float, y: float, t: float, z: int) -> 'PolarTemporalCoordinate':
        """
        Create a polar-temporal coordinate from Cartesian coordinates.
        
        Args:
            x, y: Cartesian coordinates in the polar plane
            t: Temporal position
            z: Context layer
            
        Returns:
            A new PolarTemporalCoordinate
        """
        r = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x) % (2 * np.pi)  # Ensure [0, 2π)
        return cls(r, theta, t, z)


class PolarTemporalSpace:
    """
    Manages the 4D polar-temporal coordinate space and operations within it.
    """
    
    def __init__(self, 
                 context_layers: int = 3, 
                 time_min: Optional[float] = None,
                 time_max: Optional[float] = None):
        """
        Initialize the 4D coordinate space.
        
        Args:
            context_layers: Number of discrete context layers
            time_min: Minimum time value (optional)
            time_max: Maximum time value (optional)
        """
        self.context_layers = context_layers
        self.time_min = time_min
        self.time_max = time_max
        
        # Weights for distance calculation
        self.w_r = 1.0       # Radial weight
        self.w_theta = 0.5   # Angular weight
        self.w_t = 1.0       # Temporal weight
        self.w_z = 0.7       # Context layer weight
    
    def distance(self, p1: PolarTemporalCoordinate, p2: PolarTemporalCoordinate) -> float:
        """
        Calculate the distance between two points in 4D space.
        
        Uses the weighted distance metric:
        d(P₁, P₂) = √[w_r(r₁ - r₂)² + w_θ·r_avg·(θ₁ - θ₂)² + w_t(t₁ - t₂)² + w_z(z₁ - z₂)²]
        
        Args:
            p1: First coordinate
            p2: Second coordinate
            
        Returns:
            Weighted distance between the points
        """
        # Angular distance needs special handling for circular wrapping
        theta_diff = min(abs(p1.theta - p2.theta), 
                         2 * np.pi - abs(p1.theta - p2.theta))
        
        # Calculate average radius for angular scaling
        r_avg = (p1.r + p2.r) / 2
        
        # Calculate weighted sum of squared differences
        r_term = self.w_r * (p1.r - p2.r)**2
        theta_term = self.w_theta * r_avg * theta_diff**2
        t_term = self.w_t * (p1.t - p2.t)**2
        z_term = self.w_z * (p1.z - p2.z)**2
        
        return np.sqrt(r_term + theta_term + t_term + z_term)
    
    def navigate(self, 
                p: PolarTemporalCoordinate, 
                delta_r: float = 0, 
                delta_theta: float = 0,
                delta_t: float = 0,
                delta_z: int = 0) -> PolarTemporalCoordinate:
        """
        Navigate from a point by specified deltas in each dimension.
        
        Args:
            p: Starting coordinate
            delta_r: Change in radial position
            delta_theta: Change in angular position
            delta_t: Change in temporal position
            delta_z: Change in context layer
            
        Returns:
            New coordinate after navigation
        """
        new_r = max(0, p.r + delta_r)  # r cannot be negative
        new_theta = (p.theta + delta_theta) % (2 * np.pi)
        new_t = p.t + delta_t
        new_z = max(1, min(self.context_layers, p.z + delta_z))  # Constrain z
        
        return PolarTemporalCoordinate(new_r, new_theta, new_t, new_z)
    
    def nearest_neighbors(self, 
                         p: PolarTemporalCoordinate, 
                         points: List[PolarTemporalCoordinate],
                         k: int = 5) -> List[Tuple[PolarTemporalCoordinate, float]]:
        """
        Find k nearest neighbors to a point in the 4D space.
        
        Args:
            p: Query point
            points: List of points to search
            k: Number of neighbors to return
            
        Returns:
            List of (point, distance) tuples, sorted by distance
        """
        distances = [(point, self.distance(p, point)) for point in points]
        return sorted(distances, key=lambda x: x[1])[:k] 
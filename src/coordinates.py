"""
Core Coordinate Representation for the Narrative Atlas

This module defines the PolarTemporalCoordinate class.
"""

import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class PolarTemporalCoordinate:
    """
    Represents a point in the 4D polar-temporal space.
    """
    
    r: float  # Radius (e.g., relevance, magnitude)
    theta: float  # Angle (e.g., category, aspect)
    t: float  # Time / Sequence

    def __init__(self, r: float, theta: float, t: float, z: int):
        """
        Initialize a coordinate in 4D polar-temporal space.
        
        Args:
            r: Radial distance (relevance), where 0 is most relevant
            theta: Angular position in radians [0, 2π)
            t: Temporal position as timestamp or sequence number
            z: Context layer (discrete integer)
        """
        if not (0 <= theta < 2 * np.pi):
            # Normalize theta to be within [0, 2*pi) range
            theta = theta % (2 * np.pi)
        self.r = r
        self.theta = theta 
        self.t = t
        self.z = z
    
    def __repr__(self) -> str:
        # Use f-string for cleaner formatting
        return f"PolarTemporalCoordinate(r={self.r:.4f}, theta={self.theta:.4f}, t={self.t}, z={self.z})"

    def __eq__(self, other) -> bool:
        """Check for equality based on coordinate values."""
        if not isinstance(other, PolarTemporalCoordinate):
            return NotImplemented
        # Consider using np.isclose for floating point comparisons if precision issues arise
        return (self.r == other.r and 
                self.theta == other.theta and 
                self.t == other.t and 
                self.z == other.z)
    
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
            A new PolarTemporalCoordinate instance
        """
        r = np.sqrt(x**2 + y**2)
        # Use np.arctan2(y, x) which handles quadrants correctly
        # Normalize to [0, 2*pi) after calculation
        theta_unnormalized = np.arctan2(y, x)
        theta = theta_unnormalized % (2 * np.pi)
        return cls(r, theta, t, z)

    # --- Methods below might be useful later but are not strictly needed for Phase 3 filtering --- 

    # @staticmethod
    # def angular_distance(theta1: float, theta2: float) -> float:
    #     """Calculate the shortest distance between two angles on a circle."""
    #     diff = abs(theta1 - theta2)
    #     return min(diff, 2 * np.pi - diff)

    # def distance(self, other: 'PolarTemporalCoordinate', weights: Dict[str, float] = None) -> float:
    #     """Calculate a weighted distance to another coordinate."""
    #     # Default weights (can be adjusted)
    #     default_weights = {'r': 1.0, 'theta': 0.5, 't': 1.0, 'z': 0.7}
    #     w = weights if weights else default_weights
        
    #     theta_diff = self.angular_distance(self.theta, other.theta)
    #     r_avg = (self.r + other.r) / 2 # Scale angular distance by average radius
        
    #     r_term = w['r'] * (self.r - other.r)**2
    #     theta_term = w['theta'] * r_avg * theta_diff**2 # Note the r_avg scaling
    #     t_term = w['t'] * (self.t - other.t)**2
    #     z_term = w['z'] * (self.z - other.z)**2
        
    #     return np.sqrt(r_term + theta_term + t_term + z_term) 
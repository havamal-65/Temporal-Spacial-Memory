"""
Minimum Bounding Rectangle implementation for the R-tree spatial index.

This module provides the Rectangle class, which represents a minimum
bounding rectangle (MBR) in the three-dimensional space of the
Temporal-Spatial Knowledge Database.
"""

from __future__ import annotations
from typing import Tuple
import math

from ..core.coordinates import SpatioTemporalCoordinate


class Rectangle:
    """
    Minimum Bounding Rectangle for R-tree indexing.
    
    This class represents a minimum bounding rectangle (MBR) in the
    three-dimensional space (t, r, θ) of the Temporal-Spatial Knowledge Database.
    It is used for efficient spatial indexing in the R-tree structure.
    """
    
    def __init__(self, 
                 min_t: float, max_t: float,
                 min_r: float, max_r: float,
                 min_theta: float, max_theta: float):
        """
        Initialize a new Rectangle.
        
        Args:
            min_t: Minimum temporal coordinate
            max_t: Maximum temporal coordinate
            min_r: Minimum radial coordinate
            max_r: Maximum radial coordinate
            min_theta: Minimum angular coordinate [0, 2π)
            max_theta: Maximum angular coordinate [0, 2π)
        """
        # Ensure min <= max for each dimension
        if min_t > max_t:
            min_t, max_t = max_t, min_t
        if min_r > max_r:
            min_r, max_r = max_r, min_r
            
        # Special handling for the angular dimension (wrap around)
        # Normalize to [0, 2π) range
        min_theta = min_theta % (2 * math.pi)
        max_theta = max_theta % (2 * math.pi)
        
        # Handle the case where the angular range crosses the 0 boundary
        if min_theta > max_theta:
            # We have a wrap-around situation (e.g., 350° to 10°)
            # In this case, we'll use the convention that min_theta > max_theta
            # indicates a wrap-around range
            pass
        
        self.min_t = min_t
        self.max_t = max_t
        self.min_r = min_r
        self.max_r = max_r
        self.min_theta = min_theta
        self.max_theta = max_theta
    
    def contains(self, coord: SpatioTemporalCoordinate) -> bool:
        """
        Check if this rectangle contains the given coordinate.
        
        Args:
            coord: The coordinate to check
            
        Returns:
            True if the coordinate is contained within this rectangle
        """
        # Check temporal and radial dimensions
        if coord.t < self.min_t or coord.t > self.max_t:
            return False
        if coord.r < self.min_r or coord.r > self.max_r:
            return False
        
        # Check angular dimension (handle wrap-around)
        if self.min_theta <= self.max_theta:
            # Normal case (no wrap-around)
            if coord.theta < self.min_theta or coord.theta > self.max_theta:
                return False
        else:
            # Wrap-around case (e.g., 350° to 10°)
            if coord.theta < self.min_theta and coord.theta > self.max_theta:
                return False
        
        return True
    
    def intersects(self, other: Rectangle) -> bool:
        """
        Check if this rectangle intersects with another.
        
        Args:
            other: The other rectangle to check
            
        Returns:
            True if the rectangles intersect
        """
        # Check temporal and radial dimensions
        if self.max_t < other.min_t or self.min_t > other.max_t:
            return False
        if self.max_r < other.min_r or self.min_r > other.max_r:
            return False
        
        # Check angular dimension (handle wrap-around)
        if self.min_theta <= self.max_theta and other.min_theta <= other.max_theta:
            # Both rectangles are normal (no wrap-around)
            if self.max_theta < other.min_theta or self.min_theta > other.max_theta:
                return False
        elif self.min_theta <= self.max_theta:
            # Self is normal, other is wrap-around
            if self.max_theta < other.min_theta and self.min_theta > other.max_theta:
                return False
        elif other.min_theta <= other.max_theta:
            # Self is wrap-around, other is normal
            if other.max_theta < self.min_theta and other.min_theta > self.max_theta:
                return False
        else:
            # Both are wrap-around - they must intersect in the angular dimension
            pass
        
        return True
    
    def area(self) -> float:
        """
        Calculate the volume/area of this rectangle.
        
        Returns:
            The volume of the rectangle
        """
        # Calculate the size in each dimension
        t_size = self.max_t - self.min_t
        r_size = self.max_r - self.min_r
        
        # Handle wrap-around for theta
        if self.min_theta <= self.max_theta:
            theta_size = self.max_theta - self.min_theta
        else:
            theta_size = (2 * math.pi) - (self.min_theta - self.max_theta)
        
        # Calculate volume, accounting for the fact that radial coordinate
        # affects the actual area in the angular dimension
        # This is a simplified approximation of the actual volume
        return t_size * (self.max_r**2 - self.min_r**2) * theta_size / 2
    
    def enlarge(self, coord: SpatioTemporalCoordinate) -> Rectangle:
        """
        Return a new rectangle enlarged to include the coordinate.
        
        Args:
            coord: The coordinate to include
            
        Returns:
            A new rectangle that contains both this rectangle and the coordinate
        """
        min_t = min(self.min_t, coord.t)
        max_t = max(self.max_t, coord.t)
        min_r = min(self.min_r, coord.r)
        max_r = max(self.max_r, coord.r)
        
        # Handle angular dimension
        if self.min_theta <= self.max_theta:
            # Normal case (no wrap-around)
            if coord.theta < self.min_theta or coord.theta > self.max_theta:
                # Check which direction requires less enlargement
                enlarge_min = (self.min_theta - coord.theta) % (2 * math.pi)
                enlarge_max = (coord.theta - self.max_theta) % (2 * math.pi)
                
                if enlarge_min <= enlarge_max:
                    min_theta = coord.theta
                    max_theta = self.max_theta
                else:
                    min_theta = self.min_theta
                    max_theta = coord.theta
            else:
                # Coordinate is already within the angular range
                min_theta = self.min_theta
                max_theta = self.max_theta
        else:
            # Wrap-around case
            if coord.theta > self.max_theta and coord.theta < self.min_theta:
                # Check which direction requires less enlargement
                enlarge_min = (coord.theta - self.max_theta) % (2 * math.pi)
                enlarge_max = (self.min_theta - coord.theta) % (2 * math.pi)
                
                if enlarge_min <= enlarge_max:
                    min_theta = self.min_theta
                    max_theta = coord.theta
                else:
                    min_theta = coord.theta
                    max_theta = self.max_theta
            else:
                # Coordinate is already within the angular range
                min_theta = self.min_theta
                max_theta = self.max_theta
        
        return Rectangle(min_t, max_t, min_r, max_r, min_theta, max_theta)
    
    def merge(self, other: Rectangle) -> Rectangle:
        """
        Return a new rectangle that contains both rectangles.
        
        Args:
            other: The other rectangle to merge with
            
        Returns:
            A new rectangle that contains both this rectangle and the other
        """
        min_t = min(self.min_t, other.min_t)
        max_t = max(self.max_t, other.max_t)
        min_r = min(self.min_r, other.min_r)
        max_r = max(self.max_r, other.max_r)
        
        # Handle angular dimension - this is complex due to wrap-around
        # We need to find the smallest angular range that contains both ranges
        if self.min_theta <= self.max_theta and other.min_theta <= other.max_theta:
            # Both are normal (no wrap-around)
            # Check if merging creates a wrap-around
            if self.max_theta < other.min_theta or other.max_theta < self.min_theta:
                # Disjoint ranges - check both ways of connecting them
                gap1 = (other.min_theta - self.max_theta) % (2 * math.pi)
                gap2 = (self.min_theta - other.max_theta) % (2 * math.pi)
                
                if gap1 <= gap2:
                    # Connect from self.max_theta to other.min_theta
                    min_theta = self.min_theta
                    max_theta = other.max_theta
                else:
                    # Connect from other.max_theta to self.min_theta
                    min_theta = other.min_theta
                    max_theta = self.max_theta
            else:
                # Overlapping or adjacent ranges
                min_theta = min(self.min_theta, other.min_theta)
                max_theta = max(self.max_theta, other.max_theta)
        elif self.min_theta > self.max_theta and other.min_theta > other.max_theta:
            # Both are wrap-around
            # Take the larger wrap-around range
            min_theta = max(self.min_theta, other.min_theta)
            max_theta = min(self.max_theta, other.max_theta)
        else:
            # One is wrap-around, one is normal
            if self.min_theta > self.max_theta:
                # Self is wrap-around
                wrap = self
                normal = other
            else:
                # Other is wrap-around
                wrap = other
                normal = self
                
            # Check if the normal range is contained within the wrap-around range
            if (normal.min_theta >= wrap.max_theta and normal.max_theta <= wrap.min_theta):
                # Normal range is inside the gap of the wrap-around range
                # Merge them
                min_theta = wrap.min_theta
                max_theta = wrap.max_theta
            else:
                # The ranges overlap or the normal range bridges the gap
                # Use a full circle or find the minimal containing range
                if (normal.min_theta <= wrap.max_theta and normal.max_theta >= wrap.min_theta):
                    # The normal range bridges the gap of the wrap-around range
                    # Use a full circle
                    min_theta = 0
                    max_theta = 2 * math.pi
                else:
                    # The ranges overlap at one end
                    if normal.max_theta >= wrap.min_theta:
                        # Overlap at the high end of the wrap-around range
                        min_theta = normal.min_theta
                        max_theta = wrap.max_theta
                    else:
                        # Overlap at the low end of the wrap-around range
                        min_theta = wrap.min_theta
                        max_theta = normal.max_theta
        
        return Rectangle(min_t, max_t, min_r, max_r, min_theta, max_theta)
    
    def margin(self) -> float:
        """
        Calculate the margin/perimeter of this rectangle.
        
        Returns:
            The perimeter of the rectangle
        """
        # Calculate the size in each dimension
        t_size = self.max_t - self.min_t
        r_size = self.max_r - self.min_r
        
        # Handle wrap-around for theta
        if self.min_theta <= self.max_theta:
            theta_size = self.max_theta - self.min_theta
        else:
            theta_size = (2 * math.pi) - (self.min_theta - self.max_theta)
        
        # For a cylindrical space, we approximate the perimeter as:
        # 2 * (areas of the circular faces) + (area of the curved surface)
        return 2 * math.pi * (self.min_r**2 + self.max_r**2) + 2 * math.pi * (self.min_r + self.max_r) * t_size
    
    def to_tuple(self) -> Tuple[float, float, float, float, float, float]:
        """
        Convert to a tuple representation.
        
        Returns:
            Tuple of (min_t, max_t, min_r, max_r, min_theta, max_theta)
        """
        return (self.min_t, self.max_t, self.min_r, self.max_r, self.min_theta, self.max_theta)
    
    @classmethod
    def from_coordinate(cls, coord: SpatioTemporalCoordinate, epsilon: float = 1e-10) -> Rectangle:
        """
        Create a rectangle from a single coordinate.
        
        This creates a small rectangle centered on the coordinate.
        
        Args:
            coord: The coordinate to create a rectangle for
            epsilon: Small value to create a non-zero area rectangle
            
        Returns:
            A small rectangle containing the coordinate
        """
        return cls(
            min_t=coord.t - epsilon,
            max_t=coord.t + epsilon,
            min_r=max(0, coord.r - epsilon),  # Ensure r stays non-negative
            max_r=coord.r + epsilon,
            min_theta=coord.theta - epsilon,
            max_theta=coord.theta + epsilon
        )
    
    @classmethod
    def from_coordinates(cls, coords: list[SpatioTemporalCoordinate]) -> Rectangle:
        """
        Create a rectangle that contains all the given coordinates.
        
        Args:
            coords: List of coordinates to contain
            
        Returns:
            A rectangle containing all the coordinates
            
        Raises:
            ValueError: If the list of coordinates is empty
        """
        if not coords:
            raise ValueError("Cannot create rectangle from empty list of coordinates")
        
        # Initialize with the first coordinate
        result = cls.from_coordinate(coords[0])
        
        # Enlarge to include the rest
        for coord in coords[1:]:
            result = result.enlarge(coord)
        
        return result
    
    def __repr__(self) -> str:
        """String representation of the rectangle."""
        return (f"Rectangle(t=[{self.min_t}, {self.max_t}], "
                f"r=[{self.min_r}, {self.max_r}], "
                f"θ=[{self.min_theta}, {self.max_theta}])") 
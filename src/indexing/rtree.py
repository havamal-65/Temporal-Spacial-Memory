"""
Spatial indexing implementation for the Temporal-Spatial Knowledge Database.

This module provides an R-tree based spatial index for efficient spatial queries.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator
import rtree
import numpy as np

from ..core.node import Node
from ..core.coordinates import Coordinates, SpatialCoordinate
from ..core.exceptions import SpatialIndexError


class SpatialIndex:
    """
    R-tree based spatial index for efficient spatial queries.
    
    This class provides a spatial index backed by the rtree library to
    efficiently perform spatial queries like nearest neighbors and
    range queries.
    """
    
    def __init__(self, dimension: int = 3, index_capacity: int = 100):
        """
        Initialize a new spatial index.
        
        Args:
            dimension: The dimensionality of the spatial index
            index_capacity: The maximum number of entries in an internal node
            
        Raises:
            SpatialIndexError: If the spatial index cannot be created
        """
        self.dimension = dimension
        
        # Set up the R-tree properties
        p = rtree.index.Property()
        p.dimension = dimension
        p.leaf_capacity = index_capacity
        p.index_capacity = index_capacity
        p.variant = rtree.index.RT_STAR  # Use R*-tree variant for better performance
        p.tight_mbr = True
        
        try:
            # Create the index
            self.index = rtree.index.Index(properties=p)
            
            # Keep a mapping from ids to nodes to avoid having to store
            # the actual nodes in the R-tree
            self.nodes: Dict[str, Node] = {}
        except Exception as e:
            raise SpatialIndexError(f"Failed to create spatial index: {e}") from e
    
    def insert(self, node: Node) -> None:
        """
        Insert a node into the spatial index.
        
        Args:
            node: The node to insert
            
        Raises:
            SpatialIndexError: If the node doesn't have spatial coordinates
                or if it cannot be inserted
        """
        if not node.coordinates.spatial:
            raise SpatialIndexError("Cannot insert node without spatial coordinates")
        
        # Extract the node's dimensions as a tuple
        dimensions = node.coordinates.spatial.dimensions
        
        # Pad with zeros if necessary
        if len(dimensions) < self.dimension:
            dimensions = dimensions + (0.0,) * (self.dimension - len(dimensions))
        # Truncate if necessary
        elif len(dimensions) > self.dimension:
            dimensions = dimensions[:self.dimension]
        
        # Convert to a bounding box for the R-tree (min_x, min_y, ..., max_x, max_y, ...)
        bounds = dimensions + dimensions
        
        try:
            # Insert into the R-tree with the node's ID as the object ID
            self.index.insert(id=hash(node.id), coordinates=bounds)
            
            # Store the node for later retrieval
            self.nodes[node.id] = node
        except Exception as e:
            raise SpatialIndexError(f"Failed to insert node {node.id}: {e}") from e
    
    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the spatial index.
        
        Args:
            node_id: The ID of the node to remove
            
        Returns:
            True if the node was removed, False if it wasn't in the index
            
        Raises:
            SpatialIndexError: If there's an error removing the node
        """
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        dimensions = node.coordinates.spatial.dimensions
        
        # Pad with zeros if necessary
        if len(dimensions) < self.dimension:
            dimensions = dimensions + (0.0,) * (self.dimension - len(dimensions))
        # Truncate if necessary
        elif len(dimensions) > self.dimension:
            dimensions = dimensions[:self.dimension]
        
        # Convert to a bounding box for the R-tree (min_x, min_y, ..., max_x, max_y, ...)
        bounds = dimensions + dimensions
        
        try:
            # Remove from the R-tree
            self.index.delete(id=hash(node_id), coordinates=bounds)
            
            # Remove from the node mapping
            del self.nodes[node_id]
            return True
        except Exception as e:
            raise SpatialIndexError(f"Failed to remove node {node_id}: {e}") from e
    
    def update(self, node: Node) -> None:
        """
        Update a node in the spatial index.
        
        This is equivalent to removing and re-inserting the node.
        
        Args:
            node: The node to update
            
        Raises:
            SpatialIndexError: If the node cannot be updated
        """
        try:
            self.remove(node.id)
            self.insert(node)
        except Exception as e:
            raise SpatialIndexError(f"Failed to update node {node.id}: {e}") from e
    
    def nearest(self, point: Tuple[float, ...], num_results: int = 10) -> List[Node]:
        """
        Find the nearest neighbors to a point.
        
        Args:
            point: The point to search near
            num_results: Maximum number of results to return
            
        Returns:
            List of nodes sorted by distance to the point
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        # Pad or truncate the point to match the index dimensionality
        if len(point) < self.dimension:
            point = point + (0.0,) * (self.dimension - len(point))
        elif len(point) > self.dimension:
            point = point[:self.dimension]
        
        try:
            # Use the R-tree nearest neighbor query
            nearest_ids = list(self.index.nearest(coordinates=point + point, num_results=num_results))
            
            # Map the hashed IDs back to nodes
            result = []
            for hashed_id in nearest_ids:
                for node_id, node in self.nodes.items():
                    if hash(node_id) == hashed_id:
                        result.append(node)
                        break
            
            return result
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform nearest neighbor query: {e}") from e
    
    def range_query(self, lower_bounds: Tuple[float, ...], upper_bounds: Tuple[float, ...]) -> List[Node]:
        """
        Find all nodes within a range.
        
        Args:
            lower_bounds: The lower bounds of the range
            upper_bounds: The upper bounds of the range
            
        Returns:
            List of nodes within the range
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        # Pad or truncate the bounds to match the index dimensionality
        if len(lower_bounds) < self.dimension:
            lower_bounds = lower_bounds + (0.0,) * (self.dimension - len(lower_bounds))
        elif len(lower_bounds) > self.dimension:
            lower_bounds = lower_bounds[:self.dimension]
        
        if len(upper_bounds) < self.dimension:
            upper_bounds = upper_bounds + (0.0,) * (self.dimension - len(upper_bounds))
        elif len(upper_bounds) > self.dimension:
            upper_bounds = upper_bounds[:self.dimension]
        
        # Combine the bounds into a single tuple for the R-tree
        bounds = lower_bounds + upper_bounds
        
        try:
            # Use the R-tree intersection query
            intersect_ids = list(self.index.intersection(coordinates=bounds))
            
            # Map the hashed IDs back to nodes
            result = []
            for hashed_id in intersect_ids:
                for node_id, node in self.nodes.items():
                    if hash(node_id) == hashed_id:
                        result.append(node)
                        break
            
            return result
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform range query: {e}") from e
    
    def count(self) -> int:
        """
        Count the number of nodes in the index.
        
        Returns:
            Number of nodes in the index
        """
        return len(self.nodes)
    
    def clear(self) -> None:
        """
        Remove all nodes from the index.
        
        Raises:
            SpatialIndexError: If there's an error clearing the index
        """
        try:
            # Re-create the index properties
            p = rtree.index.Property()
            p.dimension = self.dimension
            p.variant = rtree.index.RT_STAR
            p.tight_mbr = True
            
            # Create a new empty index
            self.index = rtree.index.Index(properties=p)
            
            # Clear the node mapping
            self.nodes.clear()
        except Exception as e:
            raise SpatialIndexError(f"Failed to clear spatial index: {e}") from e
    
    def get_all(self) -> List[Node]:
        """
        Get all nodes in the index.
        
        Returns:
            List of all nodes
        """
        return list(self.nodes.values()) 
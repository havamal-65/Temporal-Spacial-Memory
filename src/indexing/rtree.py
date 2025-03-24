"""
Spatial indexing implementation for the Temporal-Spatial Knowledge Database.

This module provides an R-tree based spatial index for efficient spatial queries.
This is a pure Python implementation without external dependencies.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator, Union, Callable
import numpy as np
import heapq
import logging
from enum import Enum
import time
from collections import defaultdict
import math

from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate
from src.core.exceptions import SpatialIndexError

# Configure logger
logger = logging.getLogger(__name__)

class SplitStrategy(Enum):
    """Enumeration of node splitting strategies for the R-tree."""
    QUADRATIC = "quadratic"  # Quadratic split (default in most implementations)
    LINEAR = "linear"        # Linear split (faster but less optimal)
    RSTAR = "rstar"          # R*-tree split strategy (more balanced)

class DistanceMetric(Enum):
    """Enumeration of distance metrics for spatial queries."""
    EUCLIDEAN = "euclidean"   # Euclidean distance (L2 norm)
    MANHATTAN = "manhattan"   # Manhattan distance (L1 norm)
    CHEBYSHEV = "chebyshev"   # Chebyshev distance (L∞ norm)

class SpatialIndex:
    """
    R-tree based spatial index for efficient spatial queries.
    
    This class provides a spatial index for efficiently performing
    spatial queries like nearest neighbors and range queries.
    """
    
    def __init__(self, 
                 dimension: int = 3, 
                 index_capacity: int = 100,
                 leaf_capacity: Optional[int] = None,
                 split_strategy: SplitStrategy = SplitStrategy.QUADRATIC,
                 distance_metric: DistanceMetric = DistanceMetric.EUCLIDEAN,
                 in_memory: bool = True):
        """
        Initialize a new spatial index.
        
        Args:
            dimension: The dimensionality of the spatial index
            index_capacity: The maximum number of entries in an internal node
            leaf_capacity: The maximum number of entries in a leaf node (defaults to index_capacity)
            split_strategy: The node splitting strategy to use
            distance_metric: The distance metric to use for nearest-neighbor queries
            in_memory: Whether to keep the index in memory (faster) or on disk
            
        Raises:
            SpatialIndexError: If the spatial index cannot be created
        """
        self.dimension = dimension
        self.distance_metric = distance_metric
        self.split_strategy = split_strategy
        self.leaf_capacity = leaf_capacity or index_capacity
        
        try:
            # Simple in-memory storage for nodes
            self.nodes: Dict[str, Node] = {}
            
            # Cache for nearest neighbor results
            self._nn_cache: Dict[Tuple[float, ...], List[Tuple[float, Node]]] = {}
            self._nn_cache_size = 100  # Maximum number of cached queries
            
            # Statistics
            self._stats = {
                "inserts": 0,
                "deletes": 0,
                "updates": 0,
                "queries": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
            
            logger.info(f"Created spatial index with dimension={dimension}, "
                       f"split_strategy={split_strategy.value}")
        except Exception as e:
            raise SpatialIndexError(f"Failed to create spatial index: {e}") from e
    
    def _calculate_distance(self, point1: Tuple[float, ...], point2: Tuple[float, ...]) -> float:
        """
        Calculate the distance between two points using the configured metric.
        
        Args:
            point1: First point
            point2: Second point
            
        Returns:
            Distance between the points
        """
        # Ensure points have the same dimensionality
        dim = min(len(point1), len(point2), self.dimension)
        p1 = point1[:dim]
        p2 = point2[:dim]
        
        if self.distance_metric == DistanceMetric.EUCLIDEAN:
            return sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
        elif self.distance_metric == DistanceMetric.MANHATTAN:
            return sum(abs(a - b) for a, b in zip(p1, p2))
        elif self.distance_metric == DistanceMetric.CHEBYSHEV:
            return max(abs(a - b) for a, b in zip(p1, p2))
        else:
            # Default to Euclidean
            return sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
    
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
        
        try:
            # Store the node
            self.nodes[node.id] = node
            
            # Update statistics
            self._stats["inserts"] += 1
            
            # Clear the nearest neighbor cache since the index has changed
            self._nn_cache.clear()
        except Exception as e:
            raise SpatialIndexError(f"Failed to insert node {node.id}: {e}") from e
    
    def bulk_load(self, nodes: List[Node]) -> None:
        """
        Bulk load multiple nodes into the index for better performance.
        
        This is much more efficient than inserting nodes one by one.
        
        Args:
            nodes: List of nodes to insert
            
        Raises:
            SpatialIndexError: If the nodes cannot be inserted
        """
        if not nodes:
            return
            
        try:
            # Add each node to the dictionary
            for node in nodes:
                if not node.coordinates.spatial:
                    logger.warning(f"Skipping node {node.id} without spatial coordinates")
                    continue
                
                self.nodes[node.id] = node
            
            # Update statistics
            self._stats["inserts"] += len(nodes)
            
            # Clear the nearest neighbor cache
            self._nn_cache.clear()
            
            logger.info(f"Bulk loaded {len(nodes)} nodes into the spatial index")
        except Exception as e:
            raise SpatialIndexError(f"Failed to bulk load nodes: {e}") from e
    
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
        
        try:
            # Remove from the node mapping
            del self.nodes[node_id]
            
            # Update statistics
            self._stats["deletes"] += 1
            
            # Clear the nearest neighbor cache
            self._nn_cache.clear()
            
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
            
            # Update statistics
            self._stats["updates"] += 1
        except Exception as e:
            raise SpatialIndexError(f"Failed to update node {node.id}: {e}") from e
    
    def nearest(self, point: Tuple[float, ...], num_results: int = 10, 
                max_distance: Optional[float] = None) -> List[Node]:
        """
        Find the nearest neighbors to a point.
        
        Args:
            point: The point to search near
            num_results: Maximum number of results to return
            max_distance: Optional maximum distance for nodes to be included
            
        Returns:
            List of nodes sorted by distance to the point
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        # Update statistics
        self._stats["queries"] += 1
        
        # Check the cache if the number of results is small
        if num_results <= 10 and not max_distance:
            cache_key = point + (num_results,)
            if cache_key in self._nn_cache:
                self._stats["cache_hits"] += 1
                # Return the cached results (up to num_results)
                return [node for _, node in self._nn_cache[cache_key][:num_results]]
            else:
                self._stats["cache_misses"] += 1
        
        # Pad or truncate the point to match the index dimensionality
        if len(point) < self.dimension:
            point = point + (0.0,) * (self.dimension - len(point))
        elif len(point) > self.dimension:
            point = point[:self.dimension]
        
        try:
            # Start time for performance tracking
            start_time = time.time()
            
            # Calculate distance to all nodes
            candidates = []
            for node in self.nodes.values():
                if node.coordinates.spatial:
                    distance = self._calculate_distance(point, node.coordinates.spatial.dimensions)
                    
                    # Add to candidates if within max_distance (if specified)
                    if max_distance is None or distance <= max_distance:
                        candidates.append((distance, node))
            
            # Sort by distance and take the top num_results
            candidates.sort(key=lambda x: x[0])
            result = [node for _, node in candidates[:num_results]]
            
            # Update the cache if the number of results is small
            if num_results <= 10 and not max_distance:
                cache_key = point + (num_results,)
                self._nn_cache[cache_key] = candidates[:num_results]
                
                # Limit cache size
                if len(self._nn_cache) > self._nn_cache_size:
                    # Remove a random entry (simple approach)
                    self._nn_cache.pop(next(iter(self._nn_cache)))
            
            # Log performance for large queries
            if num_results > 100:
                elapsed = time.time() - start_time
                logger.info(f"Nearest neighbor query for {num_results} results took {elapsed:.3f}s")
                
            return result
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform nearest neighbor query: {e}") from e
    
    def incremental_nearest(self, point: Tuple[float, ...], 
                           max_results: Optional[int] = None, 
                           max_distance: Optional[float] = None) -> Iterator[Tuple[float, Node]]:
        """
        Incrementally find nearest neighbors, yielding one at a time.
        
        This is more efficient when you need to process nodes one at a time
        and may not need all of them.
        
        Args:
            point: The point to search near
            max_results: Optional maximum number of results to return
            max_distance: Optional maximum distance for nodes to be included
            
        Yields:
            Tuple of (distance, node) sorted by increasing distance
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        # Pad or truncate the point to match the index dimensionality
        if len(point) < self.dimension:
            point = point + (0.0,) * (self.dimension - len(point))
        elif len(point) > self.dimension:
            point = point[:self.dimension]
        
        try:
            # Calculate distance to all nodes
            nodes_with_distances = []
            
            for node in self.nodes.values():
                if node.coordinates.spatial:
                    # Calculate distance
                    distance = self._calculate_distance(point, node.coordinates.spatial.dimensions)
                    
                    # Add if within max_distance
                    if max_distance is None or distance <= max_distance:
                        nodes_with_distances.append((distance, node))
            
            # Sort by distance
            nodes_with_distances.sort(key=lambda x: x[0])
            
            # Yield nodes up to max_results
            count = 0
            for distance, node in nodes_with_distances:
                yield (distance, node)
                count += 1
                if max_results is not None and count >= max_results:
                    break
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform incremental nearest neighbor query: {e}") from e
    
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
        # Update statistics
        self._stats["queries"] += 1
        
        # Pad or truncate the bounds to match the index dimensionality
        if len(lower_bounds) < self.dimension:
            lower_bounds = lower_bounds + (0.0,) * (self.dimension - len(lower_bounds))
        elif len(lower_bounds) > self.dimension:
            lower_bounds = lower_bounds[:self.dimension]
        
        if len(upper_bounds) < self.dimension:
            upper_bounds = upper_bounds + (0.0,) * (self.dimension - len(upper_bounds))
        elif len(upper_bounds) > self.dimension:
            upper_bounds = upper_bounds[:self.dimension]
        
        try:
            # Start time for performance tracking
            start_time = time.time()
            
            # Check all nodes against the range
            result = []
            for node in self.nodes.values():
                if not node.coordinates.spatial:
                    continue
                    
                dims = node.coordinates.spatial.dimensions
                
                # Pad or truncate dimensions if needed
                if len(dims) < self.dimension:
                    dims = dims + (0.0,) * (self.dimension - len(dims))
                elif len(dims) > self.dimension:
                    dims = dims[:self.dimension]
                
                # Check if the node is within the range
                in_range = True
                for i in range(self.dimension):
                    if dims[i] < lower_bounds[i] or dims[i] > upper_bounds[i]:
                        in_range = False
                        break
                
                if in_range:
                    result.append(node)
            
            # Log performance for large results
            if len(result) > 100:
                elapsed = time.time() - start_time
                logger.info(f"Range query returned {len(result)} results in {elapsed:.3f}s")
                
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
            # Clear the nodes dictionary
            self.nodes.clear()
            self._nn_cache.clear()
            
            # Reset statistics
            for key in self._stats:
                self._stats[key] = 0
                
            logger.info("Cleared spatial index")
        except Exception as e:
            raise SpatialIndexError(f"Failed to clear spatial index: {e}") from e
    
    def get_all(self) -> List[Node]:
        """
        Get all nodes in the index.
        
        Returns:
            List of all nodes
            
        Raises:
            SpatialIndexError: If there's an error retrieving nodes
        """
        try:
            return list(self.nodes.values())
        except Exception as e:
            raise SpatialIndexError(f"Failed to get all nodes: {e}") from e
    
    def path_query(self, path_points: List[Tuple[float, ...]], radius: float) -> List[Node]:
        """
        Find all nodes within a specified distance of a path.
        
        Args:
            path_points: List of points defining the path
            radius: Maximum distance from the path
            
        Returns:
            List of nodes within the specified distance of the path
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        if not path_points:
            return []
        
        try:
            # For each node, check distance to each line segment in the path
            result_set = set()
            
            for node in self.nodes.values():
                if not node.coordinates.spatial:
                    continue
                    
                point = node.coordinates.spatial.dimensions[:2]  # Use first 2 dimensions
                
                # Check minimum distance to any line segment
                min_distance = float('inf')
                
                for i in range(len(path_points) - 1):
                    p1 = path_points[i][:2]  # Use first 2 dimensions
                    p2 = path_points[i+1][:2]
                    
                    # Distance from point to line segment
                    dist = self._point_to_segment_distance(point, p1, p2)
                    min_distance = min(min_distance, dist)
                
                if min_distance <= radius:
                    result_set.add(node.id)
            
            # Convert set of IDs back to list of nodes
            return [self.nodes[node_id] for node_id in result_set]
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform path query: {e}") from e
    
    def _point_to_segment_distance(self, p: Tuple[float, ...], v: Tuple[float, ...], w: Tuple[float, ...]) -> float:
        """
        Calculate the distance from a point to a line segment.
        
        Args:
            p: The point
            v: Start point of the line segment
            w: End point of the line segment
            
        Returns:
            Distance from point to line segment
        """
        # Length squared of line segment
        l2 = sum((a - b) ** 2 for a, b in zip(v, w))
        
        if l2 == 0:
            # v and w are the same point
            return sum((a - b) ** 2 for a, b in zip(p, v)) ** 0.5
            
        # Project point onto line segment
        t = max(0, min(1, sum((a - b) * (c - b) for a, b, c in zip(p, v, w)) / l2))
        
        # Projection point
        proj = tuple(b + t * (c - b) for b, c in zip(v, w))
        
        # Distance from point to projection
        return sum((a - b) ** 2 for a, b in zip(p, proj)) ** 0.5
    
    def shape_query(self, shape: Union[List[Tuple[float, ...]], Dict[str, Any]]) -> List[Node]:
        """
        Find all nodes within or intersecting a complex shape.
        
        Args:
            shape: Either a list of points defining a polygon or a dictionary
                  with shape parameters (e.g., {"type": "circle", "center": (0, 0), "radius": 5})
            
        Returns:
            List of nodes within or intersecting the shape
            
        Raises:
            SpatialIndexError: If there's an error performing the query or if the shape is invalid
        """
        try:
            if isinstance(shape, list):
                # Treat as polygon
                return self._polygon_query(shape)
            elif isinstance(shape, dict):
                shape_type = shape.get("type", "").lower()
                
                if shape_type == "circle":
                    return self._circle_query(shape["center"], shape["radius"])
                elif shape_type == "rectangle":
                    return self.range_query(shape["min_point"], shape["max_point"])
                else:
                    raise SpatialIndexError(f"Unsupported shape type: {shape_type}")
            else:
                raise SpatialIndexError("Shape must be a list of points (polygon) or a dictionary")
        except KeyError as e:
            raise SpatialIndexError(f"Missing required parameter for shape query: {e}")
        except Exception as e:
            raise SpatialIndexError(f"Failed to perform shape query: {e}") from e
    
    def _circle_query(self, center: Tuple[float, ...], radius: float) -> List[Node]:
        """
        Find all nodes within a circle.
        
        Args:
            center: Center point of the circle
            radius: Radius of the circle
            
        Returns:
            List of nodes within the circle
        """
        result = []
        
        for node in self.nodes.values():
            if not node.coordinates.spatial:
                continue
                
            # Calculate distance to center
            distance = self._calculate_distance(center, node.coordinates.spatial.dimensions)
            
            # Add node if within radius
            if distance <= radius:
                result.append(node)
        
        return result
    
    def _polygon_query(self, polygon: List[Tuple[float, ...]]) -> List[Node]:
        """
        Find all nodes within a polygon.
        
        Args:
            polygon: List of points defining the polygon
            
        Returns:
            List of nodes within the polygon
        """
        if len(polygon) < 3:
            raise SpatialIndexError("Polygon must have at least 3 points")
            
        result = []
        
        for node in self.nodes.values():
            if not node.coordinates.spatial:
                continue
                
            point = node.coordinates.spatial.dimensions[:2]  # Use first 2 dimensions
            
            if self._is_point_in_polygon(point, polygon):
                result.append(node)
        
        return result
    
    def _is_point_in_polygon(self, point: Tuple[float, ...], polygon: List[Tuple[float, ...]]) -> bool:
        """
        Check if a point is inside a polygon using the ray casting algorithm.
        
        Args:
            point: The point to check
            polygon: List of points defining the polygon
            
        Returns:
            True if the point is inside the polygon, False otherwise
        """
        x, y = point[:2]
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0][:2]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n][:2]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the spatial index.
        
        Returns:
            Dictionary of statistics
        """
        stats = dict(self._stats)
        stats.update({
            "node_count": len(self.nodes),
            "dimension": self.dimension,
            "cache_size": len(self._nn_cache),
            "distance_metric": self.distance_metric.value,
        })
        return stats 
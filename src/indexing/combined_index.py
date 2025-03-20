"""
Combined spatio-temporal indexing for the Temporal-Spatial Knowledge Database.

This module provides a combined index that efficiently supports both spatial
and temporal queries, as well as queries that involve both dimensions.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator
from datetime import datetime, timedelta

from ..core.node import Node
from ..core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
from ..core.exceptions import IndexError, SpatialIndexError, TemporalIndexError
from .rtree import SpatialIndex
from .temporal_index import TemporalIndex


class CombinedIndex:
    """
    Combined spatial and temporal index.
    
    This class provides a combined index that efficiently supports both
    spatial and temporal queries, as well as combined queries that involve
    both dimensions.
    """
    
    def __init__(self, spatial_dimension: int = 3, spatial_index_capacity: int = 100):
        """
        Initialize a combined spatio-temporal index.
        
        Args:
            spatial_dimension: Dimensionality for the spatial index
            spatial_index_capacity: Capacity for the spatial index nodes
            
        Raises:
            IndexError: If the index cannot be created
        """
        try:
            self.spatial_index = SpatialIndex(dimension=spatial_dimension, index_capacity=spatial_index_capacity)
            self.temporal_index = TemporalIndex()
            
            # Keep track of which nodes are indexed in which sub-index
            self.spatial_nodes: Set[str] = set()
            self.temporal_nodes: Set[str] = set()
            
            # Keep a master list of all nodes
            self.all_nodes: Dict[str, Node] = {}
        except Exception as e:
            raise IndexError(f"Failed to create combined index: {e}") from e
    
    def insert(self, node: Node) -> None:
        """
        Insert a node into the combined index.
        
        The node will be inserted into the spatial index if it has spatial
        coordinates, and into the temporal index if it has temporal coordinates.
        
        Args:
            node: The node to insert
            
        Raises:
            IndexError: If the node cannot be inserted
        """
        try:
            # Insert into the appropriate sub-indices based on available coordinates
            if node.coordinates.spatial:
                self.spatial_index.insert(node)
                self.spatial_nodes.add(node.id)
            
            if node.coordinates.temporal:
                self.temporal_index.insert(node)
                self.temporal_nodes.add(node.id)
            
            # Always add to the master list
            self.all_nodes[node.id] = node
        except Exception as e:
            raise IndexError(f"Failed to insert node {node.id}: {e}") from e
    
    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the combined index.
        
        Args:
            node_id: The ID of the node to remove
            
        Returns:
            True if the node was removed, False if it wasn't in the index
            
        Raises:
            IndexError: If there's an error removing the node
        """
        if node_id not in self.all_nodes:
            return False
        
        try:
            # Remove from the appropriate sub-indices
            if node_id in self.spatial_nodes:
                self.spatial_index.remove(node_id)
                self.spatial_nodes.discard(node_id)
            
            if node_id in self.temporal_nodes:
                self.temporal_index.remove(node_id)
                self.temporal_nodes.discard(node_id)
            
            # Remove from the master list
            del self.all_nodes[node_id]
            
            return True
        except Exception as e:
            raise IndexError(f"Failed to remove node {node_id}: {e}") from e
    
    def update(self, node: Node) -> None:
        """
        Update a node in the combined index.
        
        Args:
            node: The node to update
            
        Raises:
            IndexError: If the node cannot be updated
        """
        try:
            self.remove(node.id)
            self.insert(node)
        except Exception as e:
            raise IndexError(f"Failed to update node {node.id}: {e}") from e
    
    def get(self, node_id: str) -> Optional[Node]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            The node if found, None otherwise
        """
        return self.all_nodes.get(node_id)
    
    def spatial_nearest(self, point: Tuple[float, ...], num_results: int = 10) -> List[Node]:
        """
        Find the nearest neighbors to a point in space.
        
        Args:
            point: The point to search near
            num_results: Maximum number of results to return
            
        Returns:
            List of nodes sorted by distance to the point
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        return self.spatial_index.nearest(point, num_results)
    
    def spatial_range(self, lower_bounds: Tuple[float, ...], upper_bounds: Tuple[float, ...]) -> List[Node]:
        """
        Find all nodes within a spatial range.
        
        Args:
            lower_bounds: The lower bounds of the range
            upper_bounds: The upper bounds of the range
            
        Returns:
            List of nodes within the range
            
        Raises:
            SpatialIndexError: If there's an error performing the query
        """
        return self.spatial_index.range_query(lower_bounds, upper_bounds)
    
    def temporal_range(self, start_time: datetime, end_time: datetime) -> List[Node]:
        """
        Find all nodes within a time range.
        
        Args:
            start_time: The start time of the range (inclusive)
            end_time: The end time of the range (inclusive)
            
        Returns:
            List of nodes within the time range
            
        Raises:
            TemporalIndexError: If there's an error performing the query
        """
        return self.temporal_index.range_query(start_time, end_time)
    
    def temporal_nearest(self, target_time: datetime, num_results: int = 10, max_distance: Optional[timedelta] = None) -> List[Node]:
        """
        Find the nearest nodes to a target time.
        
        Args:
            target_time: The target time to search near
            num_results: Maximum number of results to return
            max_distance: Maximum time distance to consider (optional)
            
        Returns:
            List of nodes sorted by temporal distance to the target time
            
        Raises:
            TemporalIndexError: If there's an error performing the query
        """
        return self.temporal_index.nearest(target_time, num_results, max_distance)
    
    def combined_query(self, 
                     spatial_point: Optional[Tuple[float, ...]] = None,
                     spatial_range: Optional[Tuple[Tuple[float, ...], Tuple[float, ...]]] = None,
                     temporal_point: Optional[datetime] = None,
                     temporal_range: Optional[Tuple[datetime, datetime]] = None,
                     num_results: int = 10,
                     max_spatial_distance: Optional[float] = None,
                     max_temporal_distance: Optional[timedelta] = None) -> List[Node]:
        """
        Perform a combined spatial and temporal query.
        
        This method combines results from spatial and temporal queries and
        returns the intersection of the results.
        
        Args:
            spatial_point: Point in space to search near (optional)
            spatial_range: Spatial range as (lower_bounds, upper_bounds) (optional)
            temporal_point: Point in time to search near (optional)
            temporal_range: Time range as (start_time, end_time) (optional)
            num_results: Maximum number of results to return
            max_spatial_distance: Maximum spatial distance to consider (optional)
            max_temporal_distance: Maximum temporal distance to consider (optional)
            
        Returns:
            List of nodes that satisfy both spatial and temporal constraints
            
        Raises:
            IndexError: If there's an error performing the query
        """
        try:
            spatial_results = set()
            temporal_results = set()
            
            # Perform spatial query if applicable
            if spatial_point is not None:
                nodes = self.spatial_nearest(spatial_point, num_results=num_results)
                spatial_results = {node.id for node in nodes}
            elif spatial_range is not None:
                lower_bounds, upper_bounds = spatial_range
                nodes = self.spatial_range(lower_bounds, upper_bounds)
                spatial_results = {node.id for node in nodes}
            
            # Perform temporal query if applicable
            if temporal_point is not None:
                nodes = self.temporal_nearest(temporal_point, num_results=num_results, 
                                              max_distance=max_temporal_distance)
                temporal_results = {node.id for node in nodes}
            elif temporal_range is not None:
                start_time, end_time = temporal_range
                nodes = self.temporal_range(start_time, end_time)
                temporal_results = {node.id for node in nodes}
            
            # Determine the final result set
            if spatial_results and temporal_results:
                # Intersection of spatial and temporal results
                result_ids = spatial_results.intersection(temporal_results)
            elif spatial_results:
                # Only spatial constraints were specified
                result_ids = spatial_results
            elif temporal_results:
                # Only temporal constraints were specified
                result_ids = temporal_results
            else:
                # No constraints were specified, return all nodes up to num_results
                result_ids = set(list(self.all_nodes.keys())[:num_results])
            
            # Convert IDs to nodes
            results = [self.all_nodes[node_id] for node_id in result_ids if node_id in self.all_nodes]
            
            # Sort by distance if a point was specified
            if spatial_point is not None and results:
                # Use the first node as an example to create a point object
                point_coords = SpatialCoordinate(dimensions=spatial_point)
                
                # Sort by spatial distance
                results.sort(key=lambda node: 
                             node.coordinates.spatial.distance_to(point_coords) 
                             if node.coordinates.spatial else float('inf'))
            
            if temporal_point is not None and results:
                # If already sorted by spatial distance, respect that
                if spatial_point is None:
                    # Sort by temporal distance
                    point_time = TemporalCoordinate(timestamp=temporal_point)
                    
                    results.sort(key=lambda node: 
                                node.coordinates.temporal.distance_to(point_time) 
                                if node.coordinates.temporal else float('inf'))
            
            return results[:num_results]
        except Exception as e:
            raise IndexError(f"Failed to perform combined query: {e}") from e
    
    def count(self) -> int:
        """
        Count the number of nodes in the index.
        
        Returns:
            Number of nodes in the index
        """
        return len(self.all_nodes)
    
    def clear(self) -> None:
        """
        Remove all nodes from the index.
        
        Raises:
            IndexError: If there's an error clearing the index
        """
        try:
            self.spatial_index.clear()
            self.temporal_index.clear()
            self.spatial_nodes.clear()
            self.temporal_nodes.clear()
            self.all_nodes.clear()
        except Exception as e:
            raise IndexError(f"Failed to clear combined index: {e}") from e
    
    def get_all(self) -> List[Node]:
        """
        Get all nodes in the index.
        
        Returns:
            List of all nodes
        """
        return list(self.all_nodes.values()) 
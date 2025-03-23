"""
Combined temporal-spatial index for efficient time and space queries.

This module provides a unified indexing structure that efficiently handles
both temporal and spatial aspects of data, allowing for combined queries.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import time
from collections import defaultdict
import logging
from datetime import datetime

from src.indexing.rtree import SpatialIndex
from src.core.node import Node
from src.core.coordinates import Coordinates
from src.core.exceptions import IndexingError

# Configure logger
logger = logging.getLogger(__name__)

class TemporalIndex:
    """
    Time-based index for efficient temporal queries.
    
    This index organizes nodes into time buckets for efficient
    time-range querying.
    """
    
    def __init__(self, bucket_size_minutes: int = 60):
        """
        Initialize a new temporal index.
        
        Args:
            bucket_size_minutes: The size of time buckets in minutes
        """
        self.bucket_size = bucket_size_minutes * 60  # Convert to seconds
        self.buckets = defaultdict(set)  # timestamp bucket -> node_ids
        self.node_timestamps = {}  # node_id -> timestamp
        
        # Statistics
        self.stats = {
            "inserts": 0,
            "removes": 0,
            "queries": 0,
            "total_query_time": 0.0,
            "avg_query_time": 0.0
        }
        
        logger.info(f"Created temporal index with bucket_size={bucket_size_minutes} minutes")
    
    def _get_bucket_key(self, timestamp: float) -> int:
        """
        Get the bucket key for a timestamp.
        
        Args:
            timestamp: The timestamp to get the bucket for
            
        Returns:
            The bucket key
        """
        return int(timestamp // self.bucket_size)
    
    def insert(self, node_id: str, timestamp: float) -> None:
        """
        Insert a node into the temporal index.
        
        Args:
            node_id: The ID of the node
            timestamp: The timestamp for the node
            
        Raises:
            IndexingError: If there's an error inserting the node
        """
        try:
            # Get the bucket key
            bucket_key = self._get_bucket_key(timestamp)
            
            # Remove from old bucket if exists
            if node_id in self.node_timestamps:
                old_timestamp = self.node_timestamps[node_id]
                old_bucket_key = self._get_bucket_key(old_timestamp)
                if node_id in self.buckets[old_bucket_key]:
                    self.buckets[old_bucket_key].remove(node_id)
            
            # Add to new bucket
            self.buckets[bucket_key].add(node_id)
            self.node_timestamps[node_id] = timestamp
            
            # Update statistics
            self.stats["inserts"] += 1
            
            logger.debug(f"Inserted node {node_id} into temporal bucket {bucket_key}")
        except Exception as e:
            raise IndexingError(f"Error inserting node {node_id} into temporal index: {e}") from e
    
    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the temporal index.
        
        Args:
            node_id: The ID of the node to remove
            
        Returns:
            True if the node was removed, False if it wasn't in the index
            
        Raises:
            IndexingError: If there's an error removing the node
        """
        if node_id not in self.node_timestamps:
            return False
        
        try:
            # Get the bucket key
            timestamp = self.node_timestamps[node_id]
            bucket_key = self._get_bucket_key(timestamp)
            
            # Remove from bucket
            if node_id in self.buckets[bucket_key]:
                self.buckets[bucket_key].remove(node_id)
            
            # Remove from timestamp mapping
            del self.node_timestamps[node_id]
            
            # Update statistics
            self.stats["removes"] += 1
            
            logger.debug(f"Removed node {node_id} from temporal bucket {bucket_key}")
            
            return True
        except Exception as e:
            raise IndexingError(f"Error removing node {node_id} from temporal index: {e}") from e
    
    def query_range(self, start_time: float, end_time: float) -> Set[str]:
        """
        Query nodes within a time range.
        
        Args:
            start_time: The start time of the range
            end_time: The end time of the range
            
        Returns:
            A set of node IDs within the time range
            
        Raises:
            IndexingError: If there's an error querying the index
        """
        try:
            # Record start time for statistics
            query_start_time = time.time()
            
            # Get bucket keys
            start_bucket = self._get_bucket_key(start_time)
            end_bucket = self._get_bucket_key(end_time)
            
            # Collect node IDs from all buckets in range
            result = set()
            for bucket_key in range(start_bucket, end_bucket + 1):
                # Add all nodes in the bucket
                result.update(self.buckets[bucket_key])
            
            # Filter out nodes that are outside the exact time range
            result = {
                node_id for node_id in result
                if start_time <= self.node_timestamps[node_id] <= end_time
            }
            
            # Update statistics
            query_duration = time.time() - query_start_time
            self.stats["queries"] += 1
            self.stats["total_query_time"] += query_duration
            self.stats["avg_query_time"] = (
                self.stats["total_query_time"] / self.stats["queries"]
            )
            
            logger.debug(
                f"Temporal range query [{start_time}-{end_time}] returned {len(result)} nodes"
            )
            
            return result
        except Exception as e:
            raise IndexingError(f"Error querying temporal index: {e}") from e
    
    def query_time_series(self, start_time: float, end_time: float, 
                          interval: float) -> Dict[int, Set[str]]:
        """
        Query time-series data at specified intervals within a range.
        
        Args:
            start_time: The start time of the range
            end_time: The end time of the range
            interval: The interval size in seconds
            
        Returns:
            A dictionary mapping time intervals to sets of node IDs
            
        Raises:
            IndexingError: If there's an error querying the index
        """
        try:
            # Record start time for statistics
            query_start_time = time.time()
            
            # Get all nodes in the range first
            all_nodes = self.query_range(start_time, end_time)
            
            # Group nodes by intervals
            result = defaultdict(set)
            for node_id in all_nodes:
                timestamp = self.node_timestamps[node_id]
                interval_key = int((timestamp - start_time) // interval)
                result[interval_key].add(node_id)
            
            # Update statistics
            query_duration = time.time() - query_start_time
            self.stats["queries"] += 1
            self.stats["total_query_time"] += query_duration
            self.stats["avg_query_time"] = (
                self.stats["total_query_time"] / self.stats["queries"]
            )
            
            logger.debug(
                f"Temporal time-series query [{start_time}-{end_time}] with interval {interval} "
                f"returned {len(result)} intervals and {len(all_nodes)} nodes"
            )
            
            return result
        except Exception as e:
            raise IndexingError(f"Error querying temporal index: {e}") from e
    
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the index.
        
        Returns:
            The number of nodes
        """
        return len(self.node_timestamps)
    
    def get_bucket_distribution(self) -> Dict[int, int]:
        """
        Get the distribution of nodes across buckets.
        
        Returns:
            A dictionary mapping bucket keys to node counts
        """
        return {
            bucket_key: len(nodes)
            for bucket_key, nodes in self.buckets.items()
            if nodes  # Only include non-empty buckets
        }

class TemporalSpatialIndex:
    """
    Combined temporal and spatial index for efficient queries.
    
    This class provides a unified indexing structure that efficiently handles
    both temporal and spatial aspects of data.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize a new temporal-spatial index.
        
        Args:
            config: Optional configuration options
        """
        self.config = config or {}
        
        # Get configuration options with defaults
        self.temporal_bucket_size = self.config.get("temporal_bucket_size", 60)  # minutes
        self.spatial_dimension = self.config.get("spatial_dimension", 3)
        self.auto_tuning = self.config.get("auto_tuning", False)
        
        # Initialize component indexes
        try:
            self.spatial_index = SpatialIndex(dimension=self.spatial_dimension)
            self.temporal_index = TemporalIndex(bucket_size_minutes=self.temporal_bucket_size)
            
            # Node storage for quick lookups
            self.nodes: Dict[str, Node] = {}
            
            # Statistics
            self.stats = {
                "inserts": 0,
                "removes": 0,
                "updates": 0,
                "queries": 0,
                "spatial_queries": 0,
                "temporal_queries": 0,
                "combined_queries": 0,
                "total_query_time": 0.0,
                "avg_query_time": 0.0
            }
            
            logger.info(
                f"Created combined temporal-spatial index with "
                f"temporal_bucket_size={self.temporal_bucket_size} minutes, "
                f"spatial_dimension={self.spatial_dimension}"
            )
        except Exception as e:
            raise IndexingError(f"Error initializing temporal-spatial index: {e}") from e
    
    def insert(self, node: Node) -> None:
        """
        Insert a node into the index.
        
        Args:
            node: The node to insert
            
        Raises:
            IndexingError: If the node cannot be inserted
        """
        if not node.coordinates:
            raise IndexingError("Cannot insert node without coordinates")
        
        try:
            # Insert into spatial index if it has spatial coordinates
            if node.coordinates.spatial:
                self.spatial_index.insert(node)
            
            # Insert into temporal index if it has a timestamp
            if node.coordinates.temporal:
                self.temporal_index.insert(node.id, node.coordinates.temporal)
            
            # Store the node for quick lookups
            self.nodes[node.id] = node
            
            # Update statistics
            self.stats["inserts"] += 1
            
            logger.debug(f"Inserted node {node.id} into combined index")
        except Exception as e:
            raise IndexingError(f"Error inserting node {node.id} into combined index: {e}") from e
    
    def bulk_load(self, nodes: List[Node]) -> None:
        """
        Bulk load multiple nodes into the index.
        
        Args:
            nodes: List of nodes to insert
            
        Raises:
            IndexingError: If the nodes cannot be inserted
        """
        if not nodes:
            return
        
        try:
            # Insert spatial nodes
            spatial_nodes = [node for node in nodes if node.coordinates.spatial]
            if spatial_nodes:
                self.spatial_index.bulk_load(spatial_nodes)
            
            # Insert temporal nodes
            for node in nodes:
                if node.coordinates.temporal:
                    self.temporal_index.insert(node.id, node.coordinates.temporal)
            
            # Store nodes for quick lookups
            for node in nodes:
                self.nodes[node.id] = node
            
            # Update statistics
            self.stats["inserts"] += len(nodes)
            
            logger.info(f"Bulk loaded {len(nodes)} nodes into combined index")
        except Exception as e:
            raise IndexingError(f"Error bulk loading nodes into combined index: {e}") from e
    
    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the index.
        
        Args:
            node_id: The ID of the node to remove
            
        Returns:
            True if the node was removed, False if it wasn't in the index
            
        Raises:
            IndexingError: If there's an error removing the node
        """
        if node_id not in self.nodes:
            return False
        
        try:
            # Remove from spatial index
            self.spatial_index.remove(node_id)
            
            # Remove from temporal index
            self.temporal_index.remove(node_id)
            
            # Remove from node storage
            del self.nodes[node_id]
            
            # Update statistics
            self.stats["removes"] += 1
            
            logger.debug(f"Removed node {node_id} from combined index")
            
            return True
        except Exception as e:
            raise IndexingError(f"Error removing node {node_id} from combined index: {e}") from e
    
    def update(self, node: Node) -> None:
        """
        Update a node in the index.
        
        Args:
            node: The node to update
            
        Raises:
            IndexingError: If the node cannot be updated
        """
        try:
            # Remove the old node
            self.remove(node.id)
            
            # Insert the new node
            self.insert(node)
            
            # Update statistics
            self.stats["updates"] += 1
            
            logger.debug(f"Updated node {node.id} in combined index")
        except Exception as e:
            raise IndexingError(f"Error updating node {node.id} in combined index: {e}") from e
    
    def query(self, spatial_criteria: Optional[Dict[str, Any]] = None, 
             temporal_criteria: Optional[Dict[str, Any]] = None,
             limit: Optional[int] = None) -> List[Node]:
        """
        Query the index with combined criteria.
        
        Args:
            spatial_criteria: Optional spatial criteria
            temporal_criteria: Optional temporal criteria
            limit: Optional maximum number of results
            
        Returns:
            A list of nodes matching the criteria
            
        Raises:
            IndexingError: If there's an error querying the index
        """
        try:
            # Record start time for statistics
            query_start_time = time.time()
            
            # Determine query type for statistics
            if spatial_criteria and temporal_criteria:
                self.stats["combined_queries"] += 1
            elif spatial_criteria:
                self.stats["spatial_queries"] += 1
            elif temporal_criteria:
                self.stats["temporal_queries"] += 1
            
            # Initialize result sets
            spatial_results: Optional[Set[str]] = None
            temporal_results: Optional[Set[str]] = None
            
            # Query spatial index if criteria provided
            if spatial_criteria:
                point = spatial_criteria.get("point")
                distance = spatial_criteria.get("distance")
                region = spatial_criteria.get("region")
                
                if point and distance:
                    # Nearest neighbor query
                    spatial_nodes = self.spatial_index.nearest(
                        point=point,
                        num_results=limit or 1000,
                        max_distance=distance
                    )
                    spatial_results = {node.id for node in spatial_nodes}
                elif region:
                    # Region query
                    spatial_nodes = self.spatial_index.query_region(region)
                    spatial_results = {node.id for node in spatial_nodes}
            
            # Query temporal index if criteria provided
            if temporal_criteria:
                start_time = temporal_criteria.get("start_time")
                end_time = temporal_criteria.get("end_time")
                
                if start_time is not None and end_time is not None:
                    temporal_results = self.temporal_index.query_range(start_time, end_time)
            
            # Combine results
            result_ids = self._combine_results(spatial_results, temporal_results)
            
            # Convert ID set to node list
            results = [self.nodes[node_id] for node_id in result_ids if node_id in self.nodes]
            
            # Apply limit if specified
            if limit is not None and len(results) > limit:
                results = results[:limit]
            
            # Update statistics
            query_duration = time.time() - query_start_time
            self.stats["queries"] += 1
            self.stats["total_query_time"] += query_duration
            self.stats["avg_query_time"] = (
                self.stats["total_query_time"] / self.stats["queries"]
            )
            
            logger.debug(
                f"Combined query returned {len(results)} results "
                f"(spatial: {spatial_results is not None}, "
                f"temporal: {temporal_results is not None})"
            )
            
            return results
        except Exception as e:
            raise IndexingError(f"Error querying combined index: {e}") from e
    
    def _combine_results(self, 
                         spatial_results: Optional[Set[str]], 
                         temporal_results: Optional[Set[str]]) -> Set[str]:
        """
        Combine spatial and temporal query results.
        
        Args:
            spatial_results: Optional set of node IDs from spatial query
            temporal_results: Optional set of node IDs from temporal query
            
        Returns:
            A set of node IDs that satisfy both criteria
        """
        if spatial_results is not None and temporal_results is not None:
            # Intersection of both result sets
            return spatial_results.intersection(temporal_results)
        elif spatial_results is not None:
            return spatial_results
        elif temporal_results is not None:
            return temporal_results
        else:
            return set()
    
    def query_time_series(self, 
                          start_time: float, 
                          end_time: float, 
                          interval: float, 
                          spatial_criteria: Optional[Dict[str, Any]] = None) -> Dict[int, List[Node]]:
        """
        Query time-series data with optional spatial filtering.
        
        Args:
            start_time: The start time
            end_time: The end time
            interval: The interval size in seconds
            spatial_criteria: Optional spatial criteria
            
        Returns:
            A dictionary mapping interval keys to lists of nodes
            
        Raises:
            IndexingError: If there's an error querying the index
        """
        try:
            # Record start time for statistics
            query_start_time = time.time()
            
            # Get time series intervals with node IDs
            interval_nodes = self.temporal_index.query_time_series(start_time, end_time, interval)
            
            # Apply spatial filtering if criteria provided
            if spatial_criteria:
                # Get spatial results
                spatial_query_result = self.query(spatial_criteria=spatial_criteria)
                spatial_ids = {node.id for node in spatial_query_result}
                
                # Filter each interval
                filtered_intervals = {}
                for interval_key, node_ids in interval_nodes.items():
                    filtered_node_ids = node_ids.intersection(spatial_ids)
                    if filtered_node_ids:
                        filtered_intervals[interval_key] = filtered_node_ids
                interval_nodes = filtered_intervals
            
            # Convert node IDs to node objects
            result = {}
            for interval_key, node_ids in interval_nodes.items():
                result[interval_key] = [
                    self.nodes[node_id] 
                    for node_id in node_ids 
                    if node_id in self.nodes
                ]
            
            # Update statistics
            query_duration = time.time() - query_start_time
            self.stats["queries"] += 1
            self.stats["total_query_time"] += query_duration
            self.stats["avg_query_time"] = (
                self.stats["total_query_time"] / self.stats["queries"]
            )
            
            logger.debug(
                f"Time-series query [{start_time}-{end_time}] with interval {interval} "
                f"returned {len(result)} intervals"
            )
            
            return result
        except Exception as e:
            raise IndexingError(f"Error querying time series: {e}") from e
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            A dictionary of statistics
        """
        stats = {
            **self.stats,
            "spatial_node_count": len(self.spatial_index.nodes),
            "temporal_node_count": self.temporal_index.get_node_count(),
            "total_node_count": len(self.nodes),
            "spatial_stats": self.spatial_index._stats,
            "temporal_stats": self.temporal_index.stats
        }
        
        return stats
    
    def tune_parameters(self) -> None:
        """
        Tune index parameters based on usage patterns.
        
        This method analyzes the current state of the index and adjusts
        parameters for optimal performance.
        
        Raises:
            IndexingError: If there's an error tuning the index
        """
        if not self.auto_tuning:
            logger.info("Auto-tuning is disabled")
            return
        
        try:
            # Analyze temporal query patterns
            temporal_queries = self.stats["temporal_queries"] + self.stats["combined_queries"]
            spatial_queries = self.stats["spatial_queries"] + self.stats["combined_queries"]
            
            if temporal_queries > 0:
                # Get bucket distribution
                bucket_distribution = self.temporal_index.get_bucket_distribution()
                bucket_counts = list(bucket_distribution.values())
                
                if bucket_counts:
                    avg_bucket_size = sum(bucket_counts) / len(bucket_counts)
                    max_bucket_size = max(bucket_counts)
                    
                    # If the buckets are very uneven or too large, adjust bucket size
                    if max_bucket_size > 5 * avg_bucket_size or avg_bucket_size > 500:
                        new_bucket_size = max(1, self.temporal_bucket_size // 2)
                        logger.info(
                            f"Tuning temporal bucket size from {self.temporal_bucket_size} "
                            f"to {new_bucket_size} minutes"
                        )
                        
                        # Create a new temporal index with the adjusted bucket size
                        new_temporal_index = TemporalIndex(bucket_size_minutes=new_bucket_size)
                        
                        # Transfer all nodes to the new index
                        for node_id, timestamp in self.temporal_index.node_timestamps.items():
                            new_temporal_index.insert(node_id, timestamp)
                        
                        # Replace the old index
                        self.temporal_index = new_temporal_index
                        self.temporal_bucket_size = new_bucket_size
            
            logger.info("Completed parameter tuning")
        except Exception as e:
            raise IndexingError(f"Error tuning index parameters: {e}") from e
    
    def rebuild(self) -> None:
        """
        Rebuild the index from scratch.
        
        This method rebuilds both spatial and temporal indexes, which can
        be useful after many updates or if the index is fragmented.
        
        Raises:
            IndexingError: If there's an error rebuilding the index
        """
        try:
            logger.info("Starting index rebuild")
            
            # Store nodes
            nodes_to_rebuild = list(self.nodes.values())
            
            # Create new indexes
            new_spatial_index = SpatialIndex(dimension=self.spatial_dimension)
            new_temporal_index = TemporalIndex(bucket_size_minutes=self.temporal_bucket_size)
            
            # Bulk load spatial nodes
            spatial_nodes = [node for node in nodes_to_rebuild if node.coordinates.spatial]
            if spatial_nodes:
                new_spatial_index.bulk_load(spatial_nodes)
            
            # Insert temporal nodes
            for node in nodes_to_rebuild:
                if node.coordinates.temporal:
                    new_temporal_index.insert(node.id, node.coordinates.temporal)
            
            # Replace indexes
            self.spatial_index = new_spatial_index
            self.temporal_index = new_temporal_index
            
            logger.info(f"Completed rebuild with {len(nodes_to_rebuild)} nodes")
        except Exception as e:
            raise IndexingError(f"Error rebuilding index: {e}") from e
    
    def visualize_distribution(self) -> Dict[str, Any]:
        """
        Generate visualization data for the index distribution.
        
        Returns:
            A dictionary with visualization data
        """
        # Temporal visualization data
        temporal_data = {
            "bucket_distribution": self.temporal_index.get_bucket_distribution(),
            "nodes_per_bucket": {
                bucket: len(nodes)
                for bucket, nodes in self.temporal_index.buckets.items()
                if nodes
            }
        }
        
        # Spatial visualization data (simplified)
        spatial_data = {
            "node_count": len(self.spatial_index.nodes)
        }
        
        return {
            "temporal": temporal_data,
            "spatial": spatial_data
        } 
"""
Temporal indexing implementation for the Temporal-Spatial Knowledge Database.

This module provides a temporal index for efficient time-based queries.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator
from datetime import datetime, timedelta
import bisect
from sortedcontainers import SortedDict

from ..core.node import Node
from ..core.coordinates import Coordinates, TemporalCoordinate
from ..core.exceptions import TemporalIndexError


class TemporalIndex:
    """
    Temporal index for efficient time-based queries.
    
    This class provides a temporal index to efficiently perform queries
    like "find all nodes within a time range" or "find nodes nearest to
    a specific point in time."
    """
    
    def __init__(self):
        """Initialize a new temporal index."""
        # Main index: dictionary mapping timestamps to sets of node IDs
        self.time_index = SortedDict()
        
        # Reverse mapping: dictionary mapping node IDs to their timestamps
        self.node_times: Dict[str, datetime] = {}
        
        # Store actual nodes
        self.nodes: Dict[str, Node] = {}
    
    def insert(self, node: Node) -> None:
        """
        Insert a node into the temporal index.
        
        Args:
            node: The node to insert
            
        Raises:
            TemporalIndexError: If the node doesn't have temporal coordinates
                or if it cannot be inserted
        """
        if not node.coordinates.temporal:
            raise TemporalIndexError("Cannot insert node without temporal coordinates")
        
        # Get the timestamp from the node
        timestamp = node.coordinates.temporal.timestamp
        
        try:
            # Add to the timestamp index
            if timestamp not in self.time_index:
                self.time_index[timestamp] = set()
            self.time_index[timestamp].add(node.id)
            
            # Add to the reverse mapping
            self.node_times[node.id] = timestamp
            
            # Store the node
            self.nodes[node.id] = node
        except Exception as e:
            raise TemporalIndexError(f"Failed to insert node {node.id}: {e}") from e
    
    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the temporal index.
        
        Args:
            node_id: The ID of the node to remove
            
        Returns:
            True if the node was removed, False if it wasn't in the index
            
        Raises:
            TemporalIndexError: If there's an error removing the node
        """
        if node_id not in self.node_times:
            return False
        
        try:
            # Get the timestamp for this node
            timestamp = self.node_times[node_id]
            
            # Remove from the timestamp index
            if timestamp in self.time_index:
                self.time_index[timestamp].discard(node_id)
                if not self.time_index[timestamp]:
                    del self.time_index[timestamp]
            
            # Remove from the reverse mapping
            del self.node_times[node_id]
            
            # Remove the node
            if node_id in self.nodes:
                del self.nodes[node_id]
            
            return True
        except Exception as e:
            raise TemporalIndexError(f"Failed to remove node {node_id}: {e}") from e
    
    def update(self, node: Node) -> None:
        """
        Update a node in the temporal index.
        
        This is equivalent to removing and re-inserting the node.
        
        Args:
            node: The node to update
            
        Raises:
            TemporalIndexError: If the node cannot be updated
        """
        try:
            self.remove(node.id)
            self.insert(node)
        except Exception as e:
            raise TemporalIndexError(f"Failed to update node {node.id}: {e}") from e
    
    def range_query(self, start_time: datetime, end_time: datetime) -> List[Node]:
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
        try:
            result = []
            
            # Find the first timestamp >= start_time
            start_index = bisect.bisect_left(list(self.time_index.keys()), start_time)
            
            # Iterate through all timestamps in the range
            for timestamp in list(self.time_index.keys())[start_index:]:
                if timestamp > end_time:
                    break
                
                # Add all nodes at this timestamp
                for node_id in self.time_index[timestamp]:
                    if node_id in self.nodes:
                        result.append(self.nodes[node_id])
            
            return result
        except Exception as e:
            raise TemporalIndexError(f"Failed to perform time range query: {e}") from e
    
    def nearest(self, target_time: datetime, num_results: int = 10, max_distance: Optional[timedelta] = None) -> List[Node]:
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
        try:
            # Convert all timestamps to a list for binary search
            timestamps = list(self.time_index.keys())
            
            # Find the index of the timestamp closest to the target
            index = bisect.bisect_left(timestamps, target_time)
            
            # Adjust index if we're at the end of the list
            if index == len(timestamps):
                index = len(timestamps) - 1
            
            # Initialize candidate nodes with their distances
            candidates = []
            
            # Look at timestamps around the target index
            left = index
            right = index
            
            while len(candidates) < num_results and (left >= 0 or right < len(timestamps)):
                # Try adding from the left
                if left >= 0:
                    timestamp = timestamps[left]
                    distance = abs((target_time - timestamp).total_seconds())
                    
                    # Check if we're within the max distance
                    if max_distance is None or distance <= max_distance.total_seconds():
                        for node_id in self.time_index[timestamp]:
                            if node_id in self.nodes:
                                candidates.append((distance, self.nodes[node_id]))
                    
                    left -= 1
                
                # Try adding from the right
                if right < len(timestamps) and right != left + 1:  # Avoid double-counting the target index
                    timestamp = timestamps[right]
                    distance = abs((target_time - timestamp).total_seconds())
                    
                    # Check if we're within the max distance
                    if max_distance is None or distance <= max_distance.total_seconds():
                        for node_id in self.time_index[timestamp]:
                            if node_id in self.nodes:
                                candidates.append((distance, self.nodes[node_id]))
                    
                    right += 1
            
            # Sort by distance and return the top results
            candidates.sort(key=lambda x: x[0])
            return [node for _, node in candidates[:num_results]]
        except Exception as e:
            raise TemporalIndexError(f"Failed to perform nearest time query: {e}") from e
    
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
            TemporalIndexError: If there's an error clearing the index
        """
        try:
            self.time_index.clear()
            self.node_times.clear()
            self.nodes.clear()
        except Exception as e:
            raise TemporalIndexError(f"Failed to clear temporal index: {e}") from e
    
    def get_all(self) -> List[Node]:
        """
        Get all nodes in the index.
        
        Returns:
            List of all nodes
        """
        return list(self.nodes.values()) 
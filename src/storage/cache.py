"""
Caching system for the Temporal-Spatial Knowledge Database.

This module provides caching mechanisms to improve performance by reducing
the number of database accesses required.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Union, Any, Tuple
from uuid import UUID
import threading
import time
from datetime import datetime, timedelta
from collections import OrderedDict

from ..core.node_v2 import Node


class NodeCache(ABC):
    """
    Abstract base class for node caching.
    
    This class defines the interface that all node cache implementations must
    follow to be compatible with the database.
    """
    
    @abstractmethod
    def get(self, node_id: UUID) -> Optional[Node]:
        """
        Get a node from cache if available.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            The node if found in cache, None otherwise
        """
        pass
    
    @abstractmethod
    def put(self, node: Node) -> None:
        """
        Add a node to the cache.
        
        Args:
            node: The node to cache
        """
        pass
    
    @abstractmethod
    def invalidate(self, node_id: UUID) -> None:
        """
        Remove a node from cache.
        
        Args:
            node_id: The ID of the node to remove
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Remove all nodes from the cache."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """
        Get the current size of the cache.
        
        Returns:
            Number of nodes in the cache
        """
        pass


class LRUCache(NodeCache):
    """
    Least Recently Used (LRU) cache implementation.
    
    This cache automatically evicts the least recently used nodes when the
    cache reaches its maximum size.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize an LRU cache.
        
        Args:
            max_size: Maximum number of nodes to cache
        """
        self.max_size = max_size
        self.cache = OrderedDict()  # OrderedDict maintains insertion order
        self.lock = threading.RLock()  # Reentrant lock for thread safety
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Get a node from cache if available."""
        with self.lock:
            if node_id in self.cache:
                # Move to end to mark as recently used
                node = self.cache.pop(node_id)
                self.cache[node_id] = node
                return node
            return None
    
    def put(self, node: Node) -> None:
        """Add a node to the cache."""
        with self.lock:
            # If node already exists, remove it first
            if node.id in self.cache:
                self.cache.pop(node.id)
            
            # Add the node to the cache
            self.cache[node.id] = node
            
            # Evict least recently used items if cache is full
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove first item (least recently used)
    
    def invalidate(self, node_id: UUID) -> None:
        """Remove a node from cache."""
        with self.lock:
            if node_id in self.cache:
                self.cache.pop(node_id)
    
    def clear(self) -> None:
        """Remove all nodes from the cache."""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Get the current size of the cache."""
        with self.lock:
            return len(self.cache)


class TemporalAwareCache(NodeCache):
    """
    Temporal-aware cache that prioritizes nodes in the current time slice.
    
    This cache is optimized for temporal queries by giving preference to
    nodes from the current time period of interest.
    """
    
    def __init__(self, 
                max_size: int = 1000, 
                current_time_window: Optional[Tuple[datetime, datetime]] = None,
                time_weight: float = 0.7):
        """
        Initialize a temporal-aware cache.
        
        Args:
            max_size: Maximum number of nodes to cache
            current_time_window: Current time window of interest (start, end)
            time_weight: Weight factor for temporal relevance scoring (0.0-1.0)
        """
        self.max_size = max_size
        self.current_time_window = current_time_window
        self.time_weight = max(0.0, min(1.0, time_weight))  # Clamp between 0 and 1
        
        # Main cache storage: node_id -> (node, last_access_time, score)
        self.cache: Dict[UUID, Tuple[Node, float, float]] = {}
        
        # Secondary indices
        self.temporal_index: Dict[datetime, Set[UUID]] = {}  # time -> set of node IDs
        
        self.lock = threading.RLock()
        self.access_count = 0  # Counter for tracking access frequency
    
    def _calculate_score(self, node: Node) -> float:
        """
        Calculate a cache priority score for a node.
        
        The score is based on the node's temporal coordinates and the
        current time window of interest.
        
        Args:
            node: The node to score
            
        Returns:
            A score value where higher values indicate higher priority
        """
        # Start with a base score
        score = 0.0
        
        # If we have a current time window, calculate temporal relevance
        if self.current_time_window and node.position:
            time_coord = node.position[0]  # Time coordinate is the first element
            
            # Convert time_coord to datetime for comparison
            # This is a simplification - in practice, you'd need proper conversion
            node_time = datetime.fromtimestamp(time_coord) if isinstance(time_coord, (int, float)) else None
            
            if node_time:
                window_start, window_end = self.current_time_window
                
                # If the node is in the current window, give it a high score
                if window_start <= node_time <= window_end:
                    temporal_score = 1.0
                else:
                    # Calculate how far the node is from the window
                    if node_time < window_start:
                        time_diff = (window_start - node_time).total_seconds()
                    else:
                        time_diff = (node_time - window_end).total_seconds()
                    
                    # Normalize the time difference (closer to 0 is better)
                    max_time_diff = 60 * 60 * 24 * 30  # 30 days in seconds
                    temporal_score = 1.0 - min(time_diff / max_time_diff, 1.0)
                
                # Apply the temporal weight
                score = self.time_weight * temporal_score
        
        # The remaining score is based on recency of access (LRU component)
        recency_score = 1.0 - (self.access_count - self.cache.get(node.id, (None, 0, 0))[1]) / max(self.access_count, 1)
        score += (1.0 - self.time_weight) * recency_score
        
        return score
    
    def _index_node(self, node: Node) -> None:
        """Add a node to the secondary indices."""
        # Extract the time coordinate and add to the temporal index
        if node.position:
            time_coord = node.position[0]
            
            # Create a datetime from the time coordinate (simplified)
            if isinstance(time_coord, (int, float)):
                node_time = datetime.fromtimestamp(time_coord)
                
                if node_time not in self.temporal_index:
                    self.temporal_index[node_time] = set()
                
                self.temporal_index[node_time].add(node.id)
    
    def _remove_from_indices(self, node_id: UUID) -> None:
        """Remove a node from the secondary indices."""
        # Get the node if it exists in the cache
        node_entry = self.cache.get(node_id)
        if not node_entry:
            return
        
        node = node_entry[0]
        
        # Remove from temporal index
        if node.position:
            time_coord = node.position[0]
            
            if isinstance(time_coord, (int, float)):
                node_time = datetime.fromtimestamp(time_coord)
                
                if node_time in self.temporal_index:
                    self.temporal_index[node_time].discard(node_id)
                    
                    # Remove empty sets
                    if not self.temporal_index[node_time]:
                        del self.temporal_index[node_time]
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Get a node from cache if available."""
        with self.lock:
            self.access_count += 1
            
            if node_id in self.cache:
                node, _, score = self.cache[node_id]
                
                # Update the last access time
                self.cache[node_id] = (node, self.access_count, score)
                
                return node
            
            return None
    
    def put(self, node: Node) -> None:
        """Add a node to the cache."""
        with self.lock:
            self.access_count += 1
            
            # Calculate the cache score for this node
            score = self._calculate_score(node)
            
            # Add to the main cache
            self.cache[node.id] = (node, self.access_count, score)
            
            # Add to the secondary indices
            self._index_node(node)
            
            # Evict items if cache is full
            if len(self.cache) > self.max_size:
                # Find the node with the lowest score
                lowest_score_id = min(self.cache.keys(), key=lambda k: self.cache[k][2])
                
                # Remove from indices first
                self._remove_from_indices(lowest_score_id)
                
                # Then remove from main cache
                del self.cache[lowest_score_id]
    
    def invalidate(self, node_id: UUID) -> None:
        """Remove a node from cache."""
        with self.lock:
            if node_id in self.cache:
                # Remove from indices first
                self._remove_from_indices(node_id)
                
                # Then remove from main cache
                del self.cache[node_id]
    
    def clear(self) -> None:
        """Remove all nodes from the cache."""
        with self.lock:
            self.cache.clear()
            self.temporal_index.clear()
            self.access_count = 0
    
    def size(self) -> int:
        """Get the current size of the cache."""
        with self.lock:
            return len(self.cache)
    
    def set_time_window(self, start: datetime, end: datetime) -> None:
        """
        Set the current time window of interest.
        
        This will trigger a recalculation of cache scores for all nodes.
        
        Args:
            start: Start time of the window
            end: End time of the window
        """
        with self.lock:
            self.current_time_window = (start, end)
            
            # Recalculate scores for all nodes
            for node_id, (node, last_access, _) in self.cache.items():
                score = self._calculate_score(node)
                self.cache[node_id] = (node, last_access, score)
    
    def prefetch_time_range(self, start: datetime, end: datetime, store: Any) -> int:
        """
        Prefetch nodes within a time range into the cache.
        
        Args:
            start: Start time of the range
            end: End time of the range
            store: The node store to fetch nodes from
            
        Returns:
            Number of nodes prefetched
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Query the store for nodes in the time range
        # 2. Add those nodes to the cache
        # 3. Return the number of nodes added
        
        # For now, we'll just set the time window
        self.set_time_window(start, end)
        return 0
    
    def invalidate_time_range(self, start: datetime, end: datetime) -> int:
        """
        Invalidate all nodes within a time range.
        
        Args:
            start: Start time of the range
            end: End time of the range
            
        Returns:
            Number of nodes invalidated
        """
        with self.lock:
            count = 0
            
            # Find times in the range
            times_in_range = [
                t for t in self.temporal_index.keys()
                if start <= t <= end
            ]
            
            # Get nodes from those times
            nodes_to_invalidate = set()
            for time in times_in_range:
                nodes_to_invalidate.update(self.temporal_index[time])
            
            # Invalidate those nodes
            for node_id in nodes_to_invalidate:
                self.invalidate(node_id)
                count += 1
            
            return count


class CacheChain(NodeCache):
    """
    Chain of caches that tries each cache in sequence.
    
    This allows for layered caching strategies, such as combining
    a small, fast L1 cache with a larger, slower L2 cache.
    """
    
    def __init__(self, caches: List[NodeCache]):
        """
        Initialize a cache chain.
        
        Args:
            caches: List of caches to chain, in order of preference
        """
        self.caches = caches
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Get a node from the first cache that has it."""
        # Try each cache in order
        for cache in self.caches:
            node = cache.get(node_id)
            if node:
                # If found, add to all earlier caches
                for earlier_cache in self.caches:
                    if earlier_cache is cache:
                        break
                    earlier_cache.put(node)
                return node
        
        return None
    
    def put(self, node: Node) -> None:
        """Add a node to all caches."""
        for cache in self.caches:
            cache.put(node)
    
    def invalidate(self, node_id: UUID) -> None:
        """Remove a node from all caches."""
        for cache in self.caches:
            cache.invalidate(node_id)
    
    def clear(self) -> None:
        """Clear all caches."""
        for cache in self.caches:
            cache.clear()
    
    def size(self) -> int:
        """Get the total size across all caches."""
        return sum(cache.size() for cache in self.caches) 
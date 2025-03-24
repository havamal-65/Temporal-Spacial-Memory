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


class PredictivePrefetchCache(NodeCache):
    """
    Cache that uses predictive prefetching to load nodes that are likely to be accessed soon.
    
    This cache analyzes access patterns and prefetches nodes that are spatially
    or temporally related to recently accessed nodes.
    """
    
    def __init__(self, 
                max_size: int = 1000,
                prefetch_count: int = 20,
                prefetch_threshold: float = 0.7,
                base_cache: Optional[NodeCache] = None):
        """
        Initialize a predictive prefetch cache.
        
        Args:
            max_size: Maximum number of nodes to cache
            prefetch_count: Maximum number of nodes to prefetch at once
            prefetch_threshold: Prediction score threshold to trigger prefetching (0.0-1.0)
            base_cache: Optional underlying cache to use
        """
        self.max_size = max_size
        self.prefetch_count = prefetch_count
        self.prefetch_threshold = max(0.0, min(1.0, prefetch_threshold))
        self.base_cache = base_cache or LRUCache(max_size)
        
        # Access pattern tracking
        self.access_sequence: List[UUID] = []  # Recent node access sequence
        self.max_sequence_length = 100  # Maximum length of access sequence to track
        
        # Transition probabilities: node_id -> {next_node_id -> count}
        self.transitions: Dict[UUID, Dict[UUID, int]] = {}
        
        # Connected nodes cache: node_id -> set of connected node IDs
        self.connections: Dict[UUID, Set[UUID]] = {}
        
        # Background prefetch thread
        self.prefetch_thread = None
        self.prefetch_queue: List[UUID] = []
        self.prefetch_lock = threading.RLock()
        self.prefetch_event = threading.Event()
        self.stop_event = threading.Event()
        
        # Node store for loading nodes (set later)
        self.node_store = None
        
        # Start the background thread
        self._start_prefetch_thread()
        
        # Thread-safe access
        self.lock = threading.RLock()
    
    def _start_prefetch_thread(self) -> None:
        """Start the background prefetching thread."""
        if self.prefetch_thread is None:
            self.stop_event.clear()
            self.prefetch_thread = threading.Thread(
                target=self._prefetch_loop,
                daemon=True,
                name="PrefetchCache"
            )
            self.prefetch_thread.start()
            logger.debug("Started prefetch thread")
    
    def _prefetch_loop(self) -> None:
        """Background prefetching loop."""
        while not self.stop_event.is_set():
            # Wait for prefetch event
            self.prefetch_event.wait(timeout=1.0)
            
            if self.stop_event.is_set():
                break
                
            if self.prefetch_event.is_set():
                try:
                    self._process_prefetch_queue()
                    self.prefetch_event.clear()
                except Exception as e:
                    logger.error(f"Error in prefetch thread: {e}")
    
    def set_node_store(self, store: Any) -> None:
        """
        Set the node store to use for loading nodes.
        
        Args:
            store: The node store
        """
        self.node_store = store
    
    def _process_prefetch_queue(self) -> None:
        """Process the prefetch queue."""
        if not self.node_store:
            return
            
        with self.prefetch_lock:
            # Get nodes to prefetch
            to_prefetch = list(self.prefetch_queue)
            self.prefetch_queue.clear()
        
        # Prefetch nodes
        for node_id in to_prefetch:
            try:
                # Skip if already in cache
                if self.base_cache.get(node_id) is not None:
                    continue
                
                # Load the node
                node = self.node_store.get(node_id)
                if node:
                    # Add to cache
                    self.base_cache.put(node)
                    logger.debug(f"Prefetched node {node_id}")
            except Exception as e:
                logger.error(f"Error prefetching node {node_id}: {e}")
    
    def _update_access_patterns(self, node_id: UUID) -> None:
        """
        Update access pattern tracking based on a node access.
        
        Args:
            node_id: ID of the node that was accessed
        """
        with self.lock:
            # If we have a previous access, record the transition
            if self.access_sequence:
                prev_id = self.access_sequence[-1]
                
                # Initialize transition dict if needed
                if prev_id not in self.transitions:
                    self.transitions[prev_id] = {}
                
                # Increment transition count
                self.transitions[prev_id][node_id] = self.transitions[prev_id].get(node_id, 0) + 1
            
            # Add to access sequence
            self.access_sequence.append(node_id)
            
            # Trim if too long
            if len(self.access_sequence) > self.max_sequence_length:
                self.access_sequence.pop(0)
    
    def _predict_next_nodes(self, node_id: UUID) -> List[Tuple[UUID, float]]:
        """
        Predict which nodes are likely to be accessed next.
        
        Args:
            node_id: ID of the currently accessed node
            
        Returns:
            List of (node_id, score) tuples sorted by score (descending)
        """
        candidates = {}
        
        with self.lock:
            # Add transitions from access patterns
            if node_id in self.transitions:
                total_transitions = sum(self.transitions[node_id].values())
                for next_id, count in self.transitions[node_id].items():
                    # Calculate transition probability
                    candidates[next_id] = candidates.get(next_id, 0) + (count / max(1, total_transitions))
            
            # Add connected nodes
            if node_id in self.connections:
                for connected_id in self.connections[node_id]:
                    candidates[connected_id] = candidates.get(connected_id, 0) + 0.5
        
        # Sort by score
        return sorted(
            [(nid, score) for nid, score in candidates.items()],
            key=lambda x: x[1],
            reverse=True
        )
    
    def _queue_prefetch(self, node_id: UUID) -> None:
        """
        Queue potential nodes for prefetching.
        
        Args:
            node_id: ID of the currently accessed node
        """
        # Skip if no node store set
        if not self.node_store:
            return
            
        # Get predicted next nodes
        predictions = self._predict_next_nodes(node_id)
        
        # Filter by threshold and limit
        to_prefetch = [
            nid for nid, score in predictions
            if score >= self.prefetch_threshold
        ][:self.prefetch_count]
        
        if to_prefetch:
            with self.prefetch_lock:
                # Add to prefetch queue
                self.prefetch_queue.extend(to_prefetch)
                
                # Signal prefetch thread
                self.prefetch_event.set()
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Get a node from cache if available."""
        node = self.base_cache.get(node_id)
        
        if node:
            # Update access patterns
            self._update_access_patterns(node_id)
            
            # Queue prefetch
            self._queue_prefetch(node_id)
            
            return node
            
        return None
    
    def put(self, node: Node) -> None:
        """Add a node to the cache."""
        # Add to base cache
        self.base_cache.put(node)
        
        # Update connection cache
        with self.lock:
            self.connections[node.id] = set(node.get_connected_nodes())
    
    def invalidate(self, node_id: UUID) -> None:
        """Remove a node from cache."""
        self.base_cache.invalidate(node_id)
        
        with self.lock:
            # Remove from connections
            if node_id in self.connections:
                del self.connections[node_id]
            
            # Remove from transitions
            if node_id in self.transitions:
                del self.transitions[node_id]
            
            # Remove from access sequence
            while node_id in self.access_sequence:
                self.access_sequence.remove(node_id)
    
    def clear(self) -> None:
        """Remove all nodes from the cache."""
        self.base_cache.clear()
        
        with self.lock:
            self.connections.clear()
            self.transitions.clear()
            self.access_sequence.clear()
    
    def size(self) -> int:
        """Get the current size of the cache."""
        return self.base_cache.size()
    
    def close(self) -> None:
        """
        Close the cache and stop background threads.
        """
        # Signal thread to stop
        self.stop_event.set()
        self.prefetch_event.set()  # Wake up thread
        
        # Wait for thread to finish
        if self.prefetch_thread and self.prefetch_thread.is_alive():
            self.prefetch_thread.join(timeout=5.0)
            self.prefetch_thread = None


class TemporalFrequencyCache(TemporalAwareCache):
    """
    Enhanced temporal-aware cache that uses access frequency in time windows.
    
    This cache tracks access frequency within temporal regions and prioritizes
    nodes that are frequently accessed in recent time windows.
    """
    
    def __init__(self, 
                max_size: int = 1000,
                time_weight: float = 0.6,
                frequency_weight: float = 0.3,
                recency_weight: float = 0.1):
        """
        Initialize a temporal frequency cache.
        
        Args:
            max_size: Maximum number of nodes to cache
            time_weight: Weight for temporal relevance (0.0-1.0)
            frequency_weight: Weight for access frequency (0.0-1.0)
            recency_weight: Weight for access recency (0.0-1.0)
        """
        # Normalize weights to sum to 1.0
        total_weight = time_weight + frequency_weight + recency_weight
        self.time_weight = time_weight / total_weight
        self.frequency_weight = frequency_weight / total_weight
        self.recency_weight = recency_weight / total_weight
        
        super().__init__(max_size=max_size, time_weight=self.time_weight)
        
        # Access frequency tracking by time window
        # window_start -> {node_id -> access_count}
        self.time_window_access: Dict[datetime, Dict[UUID, int]] = {}
        
        # Window size for frequency tracking (1 hour)
        self.window_size = timedelta(hours=1)
        
        # Maximum number of time windows to track
        self.max_time_windows = 24  # 24 hours
    
    def _calculate_score(self, node: Node) -> float:
        """
        Calculate a cache priority score for a node using frequency information.
        
        Args:
            node: The node to score
            
        Returns:
            A score value where higher values indicate higher priority
        """
        # Start with the base temporal score
        temporal_score = super()._calculate_score(node)
        
        # Calculate frequency score
        frequency_score = self._calculate_frequency_score(node)
        
        # Calculate recency score
        recency_score = self._calculate_recency_score(node)
        
        # Weighted combination of scores
        return (
            self.time_weight * temporal_score +
            self.frequency_weight * frequency_score +
            self.recency_weight * recency_score
        )
    
    def _calculate_frequency_score(self, node: Node) -> float:
        """
        Calculate a score based on access frequency.
        
        Args:
            node: The node to score
            
        Returns:
            A frequency score between 0.0 and 1.0
        """
        if not node.position:
            return 0.0
            
        # Get access counts across all windows
        total_count = 0
        window_counts = []
        
        # Get the node's time coordinate
        node_time = None
        if node.position:
            time_coord = node.position[0]
            if isinstance(time_coord, (int, float)):
                node_time = datetime.fromtimestamp(time_coord)
        
        with self.lock:
            # Look at each time window
            for window_start, access_dict in self.time_window_access.items():
                window_end = window_start + self.window_size
                count = access_dict.get(node.id, 0)
                
                # Weight the count by how close the window is to the node's time
                if node_time:
                    # Calculate temporal distance
                    if window_start <= node_time <= window_end:
                        # Node is in this window, use full count
                        weight = 1.0
                    else:
                        # Calculate distance in window sizes
                        if node_time < window_start:
                            distance = (window_start - node_time).total_seconds()
                        else:
                            distance = (node_time - window_end).total_seconds()
                        
                        # Normalize by window size and apply decay
                        normalized_distance = distance / self.window_size.total_seconds()
                        weight = max(0.0, 1.0 - (normalized_distance / 5.0))  # 5 window decay
                else:
                    # No time information, use full count
                    weight = 1.0
                
                weighted_count = count * weight
                window_counts.append(weighted_count)
                total_count += weighted_count
        
        # If we have access data, calculate score
        if window_counts:
            # Recent windows are more important, so take weighted average
            weighted_sum = 0
            total_weight = 0
            
            for i, count in enumerate(reversed(window_counts)):  # Reverse to give recent windows more weight
                weight = 1.0 / (i + 1)  # Harmonic weight
                weighted_sum += count * weight
                total_weight += weight
            
            avg_count = weighted_sum / total_weight if total_weight > 0 else 0
            
            # Normalize to 0.0-1.0 range with diminishing returns
            return 1.0 - (1.0 / (avg_count / 2.0 + 1.0))
        
        return 0.0
    
    def _calculate_recency_score(self, node: Node) -> float:
        """
        Calculate a score based on access recency.
        
        Args:
            node: The node to score
            
        Returns:
            A recency score between 0.0 and 1.0
        """
        # Use the access count from the base implementation
        with self.lock:
            if node.id in self.cache:
                _, last_access, _ = self.cache[node.id]
                
                # Normalize based on most recent access (higher is better)
                if self.access_count > 0:
                    return last_access / self.access_count
        
        return 0.0
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Get a node from cache if available."""
        with self.lock:
            # Update access frequency for current time window
            current_time = datetime.now()
            window_start = datetime(
                current_time.year, 
                current_time.month, 
                current_time.day, 
                current_time.hour
            )
            
            # Initialize window if needed
            if window_start not in self.time_window_access:
                self.time_window_access[window_start] = {}
                
                # Clean up old windows
                self._clean_old_windows()
            
            # Increment access count
            access_dict = self.time_window_access[window_start]
            access_dict[node_id] = access_dict.get(node_id, 0) + 1
            
            # Get from cache
            result = super().get(node_id)
            
            return result
    
    def _clean_old_windows(self) -> None:
        """Remove old time windows to prevent unbounded growth."""
        if len(self.time_window_access) <= self.max_time_windows:
            return
            
        # Sort windows by start time
        sorted_windows = sorted(self.time_window_access.keys())
        
        # Remove oldest windows
        to_remove = len(sorted_windows) - self.max_time_windows
        for i in range(to_remove):
            del self.time_window_access[sorted_windows[i]]
    
    def clear(self) -> None:
        """Remove all nodes from the cache."""
        super().clear()
        
        with self.lock:
            self.time_window_access.clear() 
"""
Partial loading system for managing large datasets in memory.

This module provides utilities for loading only parts of datasets into memory
based on query needs, reducing overall memory usage for large databases.
"""

import threading
from typing import Dict, List, Set, Any, Optional, Tuple, Callable, Iterator
from uuid import UUID
import time
from datetime import datetime, timedelta
import logging
import weakref
import gc
from collections import defaultdict

from ..core.node_v2 import Node
from .node_store import NodeStore


logger = logging.getLogger(__name__)


class PartialLoader:
    """
    Manages partial loading of datasets to optimize memory usage.
    
    This class provides a way to load only the parts of a dataset that are 
    actively needed, unloading others to save memory when working with large datasets.
    """
    
    def __init__(self, 
                 store: NodeStore, 
                 max_nodes_in_memory: int = 10000,
                 prefetch_size: int = 100,
                 gc_interval: float = 60.0):
        """
        Initialize the partial loader.
        
        Args:
            store: The underlying node store
            max_nodes_in_memory: Maximum number of nodes to keep in memory
            prefetch_size: Number of nodes to prefetch when loading a window
            gc_interval: Time between garbage collection runs in seconds
        """
        self.store = store
        self.max_nodes_in_memory = max_nodes_in_memory
        self.prefetch_size = prefetch_size
        self.gc_interval = gc_interval
        
        # Current nodes in memory
        self.loaded_nodes: Dict[UUID, Node] = {}
        
        # Track access times for eviction policy
        self.access_times: Dict[UUID, float] = {}
        
        # Recent time windows requested
        self.recent_time_windows: List[Tuple[datetime, datetime]] = []
        self.max_recent_windows = 5
        
        # Spatial regions recently accessed
        self.recent_spatial_regions: List[List[float]] = []  # [x_min, y_min, x_max, y_max]
        self.max_recent_regions = 5
        
        # Track pinned nodes that shouldn't be evicted
        self.pinned_nodes: Set[UUID] = set()
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Background thread for garbage collection
        self.gc_thread = None
        self.gc_stop_event = threading.Event()
        self._start_gc_thread()
        
        # Weak reference counting for node usage
        self.node_ref_count: Dict[UUID, int] = defaultdict(int)
        
        logger.info(f"Partial loader initialized with max_nodes={max_nodes_in_memory}")
    
    def _start_gc_thread(self) -> None:
        """Start the background garbage collection thread."""
        if self.gc_thread is None:
            self.gc_stop_event.clear()
            self.gc_thread = threading.Thread(
                target=self._gc_loop, 
                daemon=True,
                name="PartialLoader-GC"
            )
            self.gc_thread.start()
            logger.debug("Started garbage collection thread")
    
    def _gc_loop(self) -> None:
        """Background garbage collection loop."""
        while not self.gc_stop_event.is_set():
            # Sleep for the GC interval
            self.gc_stop_event.wait(self.gc_interval)
            
            if not self.gc_stop_event.is_set():
                try:
                    # Run garbage collection
                    self._run_gc()
                except Exception as e:
                    logger.error(f"Error in garbage collection: {e}")
    
    def _run_gc(self) -> None:
        """Run a garbage collection cycle."""
        with self.lock:
            # Skip if we're under the memory limit
            if len(self.loaded_nodes) <= self.max_nodes_in_memory:
                return
            
            # Calculate how many nodes to evict
            to_evict = len(self.loaded_nodes) - self.max_nodes_in_memory
            
            # Sort nodes by access time (oldest first)
            sorted_nodes = sorted(
                [(node_id, self.access_times.get(node_id, 0)) 
                 for node_id in self.loaded_nodes
                 if node_id not in self.pinned_nodes],
                key=lambda x: x[1]
            )
            
            # Evict oldest nodes
            evicted = 0
            for node_id, _ in sorted_nodes:
                if evicted >= to_evict:
                    break
                    
                # Check if node is in use (reference count > 0)
                if self.node_ref_count[node_id] > 0:
                    continue
                    
                # Evict the node
                if node_id in self.loaded_nodes:
                    del self.loaded_nodes[node_id]
                if node_id in self.access_times:
                    del self.access_times[node_id]
                if node_id in self.node_ref_count:
                    del self.node_ref_count[node_id]
                    
                evicted += 1
            
            # Force Python's garbage collector to run
            gc.collect()
            
            logger.debug(f"Garbage collected {evicted} nodes")
    
    def load_temporal_window(self, 
                            start_time: datetime, 
                            end_time: datetime, 
                            filter_func: Optional[Callable[[Node], bool]] = None) -> List[Node]:
        """
        Load all nodes within a specific time window.
        
        Args:
            start_time: Start of the time window
            end_time: End of the time window
            filter_func: Optional function to filter nodes
            
        Returns:
            List of nodes in the time window
        """
        with self.lock:
            # Add to recent windows for prefetching
            self._add_recent_time_window(start_time, end_time)
            
            # Get nodes from the store
            node_ids = self.store.get_nodes_in_time_range(start_time, end_time)
            
            # Load the nodes and track them
            nodes = []
            for node_id in node_ids:
                node = self.get_node(node_id)
                if node and (filter_func is None or filter_func(node)):
                    nodes.append(node)
            
            # Prefetch related nodes
            self._prefetch_related_nodes(nodes)
            
            return nodes
    
    def load_spatial_region(self, 
                           x_min: float, 
                           y_min: float, 
                           x_max: float, 
                           y_max: float,
                           filter_func: Optional[Callable[[Node], bool]] = None) -> List[Node]:
        """
        Load all nodes within a specific spatial region.
        
        Args:
            x_min: Minimum x coordinate
            y_min: Minimum y coordinate
            x_max: Maximum x coordinate
            y_max: Maximum y coordinate
            filter_func: Optional function to filter nodes
            
        Returns:
            List of nodes in the spatial region
        """
        with self.lock:
            # Add to recent regions for prefetching
            self._add_recent_spatial_region([x_min, y_min, x_max, y_max])
            
            # Get nodes from the store
            node_ids = self.store.get_nodes_in_spatial_region(x_min, y_min, x_max, y_max)
            
            # Load the nodes and track them
            nodes = []
            for node_id in node_ids:
                node = self.get_node(node_id)
                if node and (filter_func is None or filter_func(node)):
                    nodes.append(node)
            
            # Prefetch related nodes
            self._prefetch_related_nodes(nodes)
            
            return nodes
    
    def get_node(self, node_id: UUID) -> Optional[Node]:
        """
        Get a node by ID, loading it if necessary.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            The node if found, None otherwise
        """
        with self.lock:
            # Update access time
            current_time = time.time()
            self.access_times[node_id] = current_time
            
            # Check if already loaded
            if node_id in self.loaded_nodes:
                return self.loaded_nodes[node_id]
            
            # Load from store
            node = self.store.get(node_id)
            if node:
                # Store in memory
                self.loaded_nodes[node_id] = node
                
                # Check if we need to run garbage collection
                if len(self.loaded_nodes) > self.max_nodes_in_memory:
                    # Run GC in the current thread
                    self._run_gc()
                
                return node
            
            return None
    
    def pin_node(self, node_id: UUID) -> bool:
        """
        Pin a node to keep it in memory.
        
        Args:
            node_id: ID of the node to pin
            
        Returns:
            True if node was pinned, False if not found
        """
        with self.lock:
            node = self.get_node(node_id)
            if node:
                self.pinned_nodes.add(node_id)
                return True
            return False
    
    def unpin_node(self, node_id: UUID) -> None:
        """
        Unpin a node, allowing it to be evicted.
        
        Args:
            node_id: ID of the node to unpin
        """
        with self.lock:
            if node_id in self.pinned_nodes:
                self.pinned_nodes.remove(node_id)
    
    def pin_nodes(self, node_ids: List[UUID]) -> int:
        """
        Pin multiple nodes to keep them in memory.
        
        Args:
            node_ids: IDs of the nodes to pin
            
        Returns:
            Number of nodes successfully pinned
        """
        pinned = 0
        for node_id in node_ids:
            if self.pin_node(node_id):
                pinned += 1
        return pinned
    
    def unpin_all(self) -> int:
        """
        Unpin all currently pinned nodes.
        
        Returns:
            Number of nodes unpinned
        """
        with self.lock:
            count = len(self.pinned_nodes)
            self.pinned_nodes.clear()
            return count
    
    def _add_recent_time_window(self, start_time: datetime, end_time: datetime) -> None:
        """Add a time window to the recent windows list."""
        self.recent_time_windows.append((start_time, end_time))
        if len(self.recent_time_windows) > self.max_recent_windows:
            self.recent_time_windows.pop(0)
    
    def _add_recent_spatial_region(self, region: List[float]) -> None:
        """Add a spatial region to the recent regions list."""
        self.recent_spatial_regions.append(region)
        if len(self.recent_spatial_regions) > self.max_recent_regions:
            self.recent_spatial_regions.pop(0)
    
    def _prefetch_related_nodes(self, nodes: List[Node]) -> None:
        """Prefetch nodes that might be related to recently loaded nodes."""
        # Skip if we're already close to memory limit
        if len(self.loaded_nodes) >= self.max_nodes_in_memory * 0.9:
            return
            
        # Get connected node IDs from recent nodes
        to_prefetch = set()
        for node in nodes:
            # Add connected nodes
            for connected_id in node.get_connected_nodes():
                if connected_id not in self.loaded_nodes and len(to_prefetch) < self.prefetch_size:
                    to_prefetch.add(connected_id)
        
        # Prefetch the nodes
        for node_id in to_prefetch:
            self.get_node(node_id)
    
    def begin_node_usage(self, node: Node) -> None:
        """
        Signal that a node is being used and should not be garbage collected.
        
        Args:
            node: The node being used
        """
        with self.lock:
            self.node_ref_count[node.id] += 1
    
    def end_node_usage(self, node: Node) -> None:
        """
        Signal that a node is no longer being used.
        
        Args:
            node: The node no longer being used
        """
        with self.lock:
            if node.id in self.node_ref_count:
                self.node_ref_count[node.id] = max(0, self.node_ref_count[node.id] - 1)
    
    def get_streaming_iterator(self, 
                              node_ids: List[UUID], 
                              batch_size: int = 100) -> Iterator[Node]:
        """
        Get a streaming iterator for a list of nodes.
        
        This loads nodes in batches to avoid loading all nodes into memory at once.
        
        Args:
            node_ids: List of node IDs to iterate over
            batch_size: Number of nodes to load at once
            
        Returns:
            Iterator yielding nodes
        """
        # Copy the list to avoid modifying the original
        remaining_ids = list(node_ids)
        
        while remaining_ids:
            # Get the next batch
            batch_ids = remaining_ids[:batch_size]
            remaining_ids = remaining_ids[batch_size:]
            
            # Load and yield the batch
            for node_id in batch_ids:
                node = self.get_node(node_id)
                if node:
                    try:
                        # Mark node as in use
                        self.begin_node_usage(node)
                        yield node
                    finally:
                        # Mark node as no longer in use
                        self.end_node_usage(node)
    
    def close(self) -> None:
        """
        Close the partial loader and stop background threads.
        """
        if self.gc_thread and self.gc_thread.is_alive():
            self.gc_stop_event.set()
            self.gc_thread.join(timeout=5.0)
            self.gc_thread = None
        
        # Clear collections
        with self.lock:
            self.loaded_nodes.clear()
            self.access_times.clear()
            self.recent_time_windows.clear()
            self.recent_spatial_regions.clear()
            self.pinned_nodes.clear()
            self.node_ref_count.clear()
        
        logger.info("Partial loader closed")


class MemoryMonitor:
    """
    Monitors memory usage of the application.
    
    This class provides utilities to track memory usage and trigger actions
    when memory usage exceeds certain thresholds.
    """
    
    def __init__(self, 
                 warning_threshold_mb: float = 1000.0,
                 critical_threshold_mb: float = 1500.0,
                 check_interval: float = 30.0):
        """
        Initialize the memory monitor.
        
        Args:
            warning_threshold_mb: Memory usage warning threshold in MB
            critical_threshold_mb: Memory usage critical threshold in MB
            check_interval: Interval between memory checks in seconds
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # Convert to bytes
        self.critical_threshold = critical_threshold_mb * 1024 * 1024  # Convert to bytes
        self.check_interval = check_interval
        
        # Callbacks for different threshold events
        self.warning_callbacks: List[Callable[[], None]] = []
        self.critical_callbacks: List[Callable[[], None]] = []
        
        # Background monitoring thread
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # Current memory usage
        self.current_usage = 0
        self.peak_usage = 0
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def start_monitoring(self) -> None:
        """Start the memory monitoring thread."""
        if self.monitor_thread is None:
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MemoryMonitor"
            )
            self.monitor_thread.start()
            logger.debug("Started memory monitoring thread")
    
    def stop_monitoring(self) -> None:
        """Stop the memory monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.stop_event.set()
            self.monitor_thread.join(timeout=5.0)
            self.monitor_thread = None
            logger.debug("Stopped memory monitoring thread")
    
    def _monitoring_loop(self) -> None:
        """Background memory monitoring loop."""
        while not self.stop_event.is_set():
            try:
                # Check memory usage
                self._check_memory()
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
            
            # Sleep for the check interval
            self.stop_event.wait(self.check_interval)
    
    def _check_memory(self) -> None:
        """Check current memory usage and trigger callbacks if needed."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Update usage stats
            with self.lock:
                self.current_usage = memory_info.rss
                self.peak_usage = max(self.peak_usage, self.current_usage)
                
                # Check thresholds
                if self.current_usage >= self.critical_threshold:
                    logger.warning(f"Critical memory usage: {self.current_usage / (1024*1024):.2f} MB")
                    # Trigger critical callbacks
                    for callback in self.critical_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Error in critical memory callback: {e}")
                elif self.current_usage >= self.warning_threshold:
                    logger.info(f"Warning memory usage: {self.current_usage / (1024*1024):.2f} MB")
                    # Trigger warning callbacks
                    for callback in self.warning_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Error in warning memory callback: {e}")
        except ImportError:
            logger.warning("psutil not available, memory monitoring disabled")
            self.stop_event.set()
    
    def add_warning_callback(self, callback: Callable[[], None]) -> None:
        """
        Add a callback to be called when memory usage exceeds the warning threshold.
        
        Args:
            callback: Function to call
        """
        with self.lock:
            self.warning_callbacks.append(callback)
    
    def add_critical_callback(self, callback: Callable[[], None]) -> None:
        """
        Add a callback to be called when memory usage exceeds the critical threshold.
        
        Args:
            callback: Function to call
        """
        with self.lock:
            self.critical_callbacks.append(callback)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory usage information
        """
        with self.lock:
            return {
                "current_mb": self.current_usage / (1024 * 1024),
                "peak_mb": self.peak_usage / (1024 * 1024),
                "warning_threshold_mb": self.warning_threshold / (1024 * 1024),
                "critical_threshold_mb": self.critical_threshold / (1024 * 1024)
            }


class StreamingQueryResult:
    """
    Handles streaming query results to manage memory usage.
    
    This class allows processing large result sets without loading all results
    into memory at once.
    """
    
    def __init__(self, 
                 node_ids: List[UUID], 
                 partial_loader: PartialLoader, 
                 batch_size: int = 100):
        """
        Initialize a streaming query result.
        
        Args:
            node_ids: List of node IDs in the result
            partial_loader: Partial loader to use for loading nodes
            batch_size: Number of nodes to load in each batch
        """
        self.node_ids = node_ids
        self.partial_loader = partial_loader
        self.batch_size = batch_size
        self.total_count = len(node_ids)
    
    def __iter__(self) -> Iterator[Node]:
        """Get an iterator over the result nodes."""
        return self.partial_loader.get_streaming_iterator(
            self.node_ids, 
            batch_size=self.batch_size
        )
    
    def count(self) -> int:
        """
        Get the total count of results.
        
        Returns:
            Total number of results
        """
        return self.total_count
    
    def get_batch(self, offset: int, limit: int) -> List[Node]:
        """
        Get a batch of results.
        
        Args:
            offset: Starting offset
            limit: Maximum number of results to return
            
        Returns:
            List of nodes in the batch
        """
        # Get the relevant node IDs
        batch_ids = self.node_ids[offset:offset+limit]
        
        # Load and return the nodes
        return [
            node for node in self.partial_loader.get_streaming_iterator(
                batch_ids, 
                batch_size=min(self.batch_size, limit)
            )
        ] 
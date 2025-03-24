"""
Simplified memory management example for the Temporal-Spatial Memory Database.

This example demonstrates memory management features with minimal dependencies.
"""

import os
import sys
import uuid
import random
import time
from datetime import datetime, timedelta
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Make sure we can import from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Simple Node class to avoid dependencies
class SimpleNode:
    def __init__(self, id=None, data=None, timestamp=None, position=None):
        self.id = id or uuid.uuid4()
        self.data = data or {}
        self.timestamp = timestamp or time.time()
        self.position = position or [self.timestamp, 0, 0]  # time, x, y
        self.connections = []
    
    def add_connection(self, target_id):
        self.connections.append(target_id)
    
    def get_connected_nodes(self):
        return self.connections

# Simple in-memory node store
class SimpleNodeStore:
    def __init__(self):
        self.nodes = {}
        self.lock = threading.RLock()
    
    def put(self, node_id, node):
        with self.lock:
            self.nodes[node_id] = node
    
    def get(self, node_id):
        with self.lock:
            return self.nodes.get(node_id)
    
    def get_all(self):
        with self.lock:
            return list(self.nodes.values())
    
    def get_nodes_in_time_range(self, start_time, end_time):
        """Get nodes in a time range."""
        with self.lock:
            result = []
            for node in self.nodes.values():
                if start_time <= datetime.fromtimestamp(node.timestamp) <= end_time:
                    result.append(node.id)
            return result
    
    def get_nodes_in_spatial_region(self, x_min, y_min, x_max, y_max):
        """Get nodes in a spatial region."""
        with self.lock:
            result = []
            for node in self.nodes.values():
                x, y = node.position[1], node.position[2]
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    result.append(node.id)
            return result

# Simple partial loader implementation
class SimplePartialLoader:
    def __init__(self, store, max_nodes_in_memory=1000):
        self.store = store
        self.max_nodes_in_memory = max_nodes_in_memory
        self.loaded_nodes = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get_node(self, node_id):
        """Get a node, loading it if necessary."""
        with self.lock:
            # Update access time
            self.access_times[node_id] = time.time()
            
            # Check if already loaded
            if node_id in self.loaded_nodes:
                return self.loaded_nodes[node_id]
            
            # Load from store
            node = self.store.get(node_id)
            if node:
                # Add to memory
                self.loaded_nodes[node_id] = node
                
                # Check if we need garbage collection
                if len(self.loaded_nodes) > self.max_nodes_in_memory:
                    self._run_gc()
                
                return node
            
            return None
    
    def _run_gc(self):
        """Run garbage collection to free memory."""
        # We'll evict 10% of the nodes
        to_evict = int(len(self.loaded_nodes) * 0.1)
        
        # Sort by access time (oldest first)
        sorted_nodes = sorted(
            self.loaded_nodes.keys(),
            key=lambda nid: self.access_times.get(nid, 0)
        )
        
        # Evict oldest nodes
        for node_id in sorted_nodes[:to_evict]:
            del self.loaded_nodes[node_id]
            del self.access_times[node_id]
        
        print(f"GC: Evicted {to_evict} nodes, memory usage: {len(self.loaded_nodes)}/{self.max_nodes_in_memory}")
    
    def load_temporal_window(self, start_time, end_time):
        """Load all nodes in a time window."""
        node_ids = self.store.get_nodes_in_time_range(start_time, end_time)
        
        # Load nodes
        nodes = []
        for node_id in node_ids:
            node = self.get_node(node_id)
            if node:
                nodes.append(node)
        
        return nodes
    
    def load_spatial_region(self, x_min, y_min, x_max, y_max):
        """Load all nodes in a spatial region."""
        node_ids = self.store.get_nodes_in_spatial_region(x_min, y_min, x_max, y_max)
        
        # Load nodes
        nodes = []
        for node_id in node_ids:
            node = self.get_node(node_id)
            if node:
                nodes.append(node)
        
        return nodes
    
    def get_memory_usage(self):
        """Get current memory usage statistics."""
        return {
            "loaded_nodes": len(self.loaded_nodes),
            "max_nodes": self.max_nodes_in_memory,
            "usage_percent": len(self.loaded_nodes) / self.max_nodes_in_memory * 100
        }

# Simple cache implementation
class SimpleCache:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, node_id):
        """Get a node from cache."""
        with self.lock:
            if node_id in self.cache:
                # Update access time
                self.access_times[node_id] = time.time()
                return self.cache[node_id]
            return None
    
    def put(self, node):
        """Add a node to cache."""
        with self.lock:
            # Add to cache
            self.cache[node.id] = node
            self.access_times[node.id] = time.time()
            
            # Evict if cache is full
            if len(self.cache) > self.max_size:
                self._evict_oldest()
    
    def _evict_oldest(self):
        """Evict the oldest node from cache."""
        if not self.cache:
            return
            
        # Find oldest
        oldest_id = min(self.cache.keys(), key=lambda nid: self.access_times.get(nid, 0))
        
        # Remove from cache
        del self.cache[oldest_id]
        del self.access_times[oldest_id]
    
    def get_stats(self):
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "usage_percent": len(self.cache) / self.max_size * 100
        }

# Generate test nodes
def generate_test_nodes(count):
    """Generate random test nodes."""
    nodes = []
    for i in range(count):
        # Create a random timestamp between 2020 and 2023
        year = random.randint(2020, 2023)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        timestamp = datetime(year, month, day).timestamp()
        
        # Create random position
        x = random.uniform(0, 100)
        y = random.uniform(0, 100)
        
        # Create node
        node = SimpleNode(
            data={"value": f"Node-{i}", "importance": random.randint(1, 10)},
            timestamp=timestamp,
            position=[timestamp, x, y]
        )
        
        # Add some connections
        for j in range(random.randint(1, 5)):
            node.add_connection(uuid.uuid4())
        
        nodes.append(node)
    
    return nodes

# Main example function
def run_memory_management_example():
    print("\n=== Memory Management Example ===\n")
    
    # Create a node store with 10,000 nodes
    print("Creating test dataset with 10,000 nodes...")
    store = SimpleNodeStore()
    nodes = generate_test_nodes(10000)
    
    # Add nodes to store
    for node in nodes:
        store.put(node.id, node)
    
    # Create a partial loader with a small memory limit
    print("Creating partial loader with 1,000 node memory limit...")
    loader = SimplePartialLoader(
        store=store,
        max_nodes_in_memory=1000  # Only keep 1,000 nodes in memory
    )
    
    # Create a cache
    print("Creating cache with 500 node limit...")
    cache = SimpleCache(max_size=500)
    
    # Simulate running several queries
    print("\nRunning temporal window queries...")
    
    time_ranges = [
        (datetime(2020, 1, 1), datetime(2020, 6, 30)),
        (datetime(2021, 1, 1), datetime(2021, 6, 30)),
        (datetime(2022, 1, 1), datetime(2022, 6, 30)),
    ]
    
    for start_time, end_time in time_ranges:
        print(f"\nLoading nodes from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}...")
        
        # Load nodes in time window
        start = time.time()
        nodes = loader.load_temporal_window(start_time, end_time)
        duration = time.time() - start
        
        print(f"Loaded {len(nodes)} nodes in {duration:.2f} seconds")
        
        # Add to cache
        for node in nodes[:100]:  # Cache the first 100 nodes
            cache.put(node)
        
        # Get memory usage
        memory_usage = loader.get_memory_usage()
        cache_stats = cache.get_stats()
        
        print(f"Memory usage: {memory_usage['loaded_nodes']}/{memory_usage['max_nodes']} nodes ({memory_usage['usage_percent']:.1f}%)")
        print(f"Cache usage: {cache_stats['size']}/{cache_stats['max_size']} nodes ({cache_stats['usage_percent']:.1f}%)")
    
    print("\nRunning spatial region queries...")
    
    regions = [
        (0, 0, 25, 25),     # Bottom left
        (25, 25, 50, 50),   # Middle
        (50, 50, 75, 75),   # Top right
    ]
    
    for x_min, y_min, x_max, y_max in regions:
        print(f"\nLoading nodes in region ({x_min}, {y_min}) to ({x_max}, {y_max})...")
        
        # Load nodes in spatial region
        start = time.time()
        nodes = loader.load_spatial_region(x_min, y_min, x_max, y_max)
        duration = time.time() - start
        
        print(f"Loaded {len(nodes)} nodes in {duration:.2f} seconds")
        
        # Add to cache
        for node in nodes[:100]:  # Cache the first 100 nodes
            cache.put(node)
        
        # Get memory usage
        memory_usage = loader.get_memory_usage()
        cache_stats = cache.get_stats()
        
        print(f"Memory usage: {memory_usage['loaded_nodes']}/{memory_usage['max_nodes']} nodes ({memory_usage['usage_percent']:.1f}%)")
        print(f"Cache usage: {cache_stats['size']}/{cache_stats['max_size']} nodes ({cache_stats['usage_percent']:.1f}%)")
    
    # Test cache performance
    print("\nTesting cache performance...")
    
    # Get a set of nodes to query
    test_nodes = nodes[:1000]
    
    # Try to get each node, some should be in cache
    cache_hits = 0
    store_hits = 0
    
    start = time.time()
    
    for node in test_nodes:
        # Try cache first
        cached_node = cache.get(node.id)
        
        if cached_node:
            cache_hits += 1
        else:
            # Try loader
            loaded_node = loader.get_node(node.id)
            if loaded_node:
                store_hits += 1
                # Add to cache for next time
                cache.put(loaded_node)
    
    duration = time.time() - start
    
    print(f"Processed {len(test_nodes)} node lookups in {duration:.2f} seconds")
    print(f"Cache hits: {cache_hits} ({cache_hits/len(test_nodes)*100:.1f}%)")
    print(f"Store hits: {store_hits} ({store_hits/len(test_nodes)*100:.1f}%)")
    
    print("\nMemory management example complete!")


if __name__ == "__main__":
    print("=== Simplified Memory Management Example ===")
    print("\nThis example demonstrates memory management and caching features")
    print("without relying on external dependencies.\n")
    
    run_memory_management_example() 
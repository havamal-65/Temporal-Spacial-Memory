"""
Memory management and caching example for the Temporal-Spatial Memory Database.

This example demonstrates how to use the memory management and caching features
to efficiently work with large datasets.
"""

import os
import sys
import uuid
import random
import time
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.node_v2 import Node
from src.storage.node_store import InMemoryNodeStore
# Import RocksDB conditionally to avoid dependency issues
try:
    from src.storage.rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError:
    print("RocksDB not available, using in-memory store only")
    ROCKSDB_AVAILABLE = False

from src.storage.partial_loader import PartialLoader, MemoryMonitor, StreamingQueryResult
from src.storage.cache import LRUCache, TemporalAwareCache, PredictivePrefetchCache, TemporalFrequencyCache
from src.query.query_builder import Query
from src.query.query_engine import QueryEngine
from src.indexing.combined_index import CombinedIndex


def generate_random_nodes(count: int, 
                         time_start: datetime = None,
                         time_end: datetime = None,
                         spatial_bounds: tuple = None):
    """Generate random nodes for testing."""
    if time_start is None:
        time_start = datetime(2020, 1, 1)
    if time_end is None:
        time_end = datetime(2023, 12, 31)
    if spatial_bounds is None:
        spatial_bounds = (0, 0, 100, 100)  # x_min, y_min, x_max, y_max
    
    x_min, y_min, x_max, y_max = spatial_bounds
    time_span = (time_end - time_start).total_seconds()
    
    nodes = []
    for i in range(count):
        # Create a node with random coordinates
        node_id = uuid.uuid4()
        
        # Random temporal coordinate
        random_time = time_start + timedelta(seconds=random.random() * time_span)
        time_coord = random_time.timestamp()
        
        # Random spatial coordinates
        x_coord = x_min + random.random() * (x_max - x_min)
        y_coord = y_min + random.random() * (y_max - y_min)
        
        # Create the node
        node = Node(
            id=node_id,
            position=[time_coord, x_coord, y_coord],
            data={
                "value": f"Node-{i}",
                "timestamp": random_time.isoformat(),
                "importance": random.randint(1, 10)
            }
        )
        
        nodes.append(node)
    
    return nodes


def basic_memory_management_example():
    """Demonstrate basic memory management with partial loading."""
    print("\n=== Basic Memory Management Example ===\n")
    
    # Create a node store with 10,000 nodes
    print("Creating test dataset with 10,000 nodes...")
    store = InMemoryNodeStore()
    nodes = generate_random_nodes(10000)
    
    # Create indices for time and space
    print("Building indices...")
    time_index = {}  # timestamp -> list of node IDs
    region_index = {}  # (x_min, y_min, x_max, y_max) -> list of node IDs
    
    # We'll use simple grid-based spatial indexing for this example
    grid_size = 10
    x_cell_size = 10  # (x_max - x_min) / grid_size
    y_cell_size = 10  # (y_max - y_min) / grid_size
    
    # Add nodes to store and build indices
    for node in nodes:
        # Add to store
        store.put(node.id, node)
        
        # Get coordinates
        time_coord = node.position[0]
        x_coord = node.position[1]
        y_coord = node.position[2]
        
        # Add to time index
        time_key = int(time_coord) // (60 * 60 * 24)  # Group by day
        if time_key not in time_index:
            time_index[time_key] = []
        time_index[time_key].append(node.id)
        
        # Add to region index
        x_cell = int(x_coord // x_cell_size)
        y_cell = int(y_coord // y_cell_size)
        
        region_key = (x_cell, y_cell)
        if region_key not in region_index:
            region_index[region_key] = []
        region_index[region_key].append(node.id)
    
    # Add methods to the store for spatial and temporal queries
    def get_nodes_in_time_range(start_time: datetime, end_time: datetime):
        """Get nodes in a time range."""
        start_key = int(start_time.timestamp()) // (60 * 60 * 24)
        end_key = int(end_time.timestamp()) // (60 * 60 * 24)
        
        result = []
        for time_key in range(start_key, end_key + 1):
            if time_key in time_index:
                result.extend(time_index[time_key])
        
        return result
    
    def get_nodes_in_spatial_region(x_min, y_min, x_max, y_max):
        """Get nodes in a spatial region."""
        min_x_cell = max(0, int(x_min // x_cell_size))
        min_y_cell = max(0, int(y_min // y_cell_size))
        max_x_cell = min(grid_size - 1, int(x_max // x_cell_size))
        max_y_cell = min(grid_size - 1, int(y_max // y_cell_size))
        
        result = []
        for x_cell in range(min_x_cell, max_x_cell + 1):
            for y_cell in range(min_y_cell, max_y_cell + 1):
                region_key = (x_cell, y_cell)
                if region_key in region_index:
                    result.extend(region_index[region_key])
        
        return result
    
    # Add these methods to the store
    store.get_nodes_in_time_range = get_nodes_in_time_range
    store.get_nodes_in_spatial_region = get_nodes_in_spatial_region
    
    # Create a partial loader with a small memory limit
    print("Creating partial loader with 1,000 node memory limit...")
    loader = PartialLoader(
        store=store,
        max_nodes_in_memory=1000,  # Only keep 1,000 nodes in memory
        prefetch_size=50,
        gc_interval=5.0
    )
    
    # Set up memory monitoring
    monitor = MemoryMonitor(
        warning_threshold_mb=100,
        critical_threshold_mb=200
    )
    
    # Add a callback for high memory
    def handle_high_memory():
        print("WARNING: Memory usage is high, forcing garbage collection...")
        loader._run_gc()
    
    monitor.add_warning_callback(handle_high_memory)
    monitor.start_monitoring()
    
    # Simulate running several queries
    print("\nRunning temporal window queries...")
    
    time_ranges = [
        (datetime(2020, 1, 1), datetime(2020, 3, 31)),
        (datetime(2021, 6, 1), datetime(2021, 8, 31)),
        (datetime(2022, 9, 1), datetime(2022, 12, 31)),
    ]
    
    for start_time, end_time in time_ranges:
        print(f"\nLoading nodes from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}...")
        
        # Load nodes in time window
        start = time.time()
        nodes = loader.load_temporal_window(start_time, end_time)
        duration = time.time() - start
        
        print(f"Loaded {len(nodes)} nodes in {duration:.2f} seconds")
        print(f"Memory usage: {len(loader.loaded_nodes)} nodes in memory")
        
        # Process some nodes
        if nodes:
            print(f"First node: {nodes[0].data.get('value')} from {datetime.fromtimestamp(nodes[0].position[0]).strftime('%Y-%m-%d')}")
    
    print("\nRunning spatial region queries...")
    
    regions = [
        (0, 0, 30, 30),     # Bottom left
        (30, 30, 60, 60),   # Middle
        (60, 60, 100, 100), # Top right
    ]
    
    for x_min, y_min, x_max, y_max in regions:
        print(f"\nLoading nodes in region ({x_min}, {y_min}) to ({x_max}, {y_max})...")
        
        # Load nodes in spatial region
        start = time.time()
        nodes = loader.load_spatial_region(x_min, y_min, x_max, y_max)
        duration = time.time() - start
        
        print(f"Loaded {len(nodes)} nodes in {duration:.2f} seconds")
        print(f"Memory usage: {len(loader.loaded_nodes)} nodes in memory")
        
        # Process some nodes
        if nodes:
            print(f"First node: {nodes[0].data.get('value')} at position ({nodes[0].position[1]:.1f}, {nodes[0].position[2]:.1f})")
    
    # Test streaming results
    print("\nTesting streaming results...")
    
    # Get many node IDs
    many_ids = []
    for time_key, ids in time_index.items():
        many_ids.extend(ids)
        if len(many_ids) >= 5000:
            break
    
    # Create a streaming result
    streaming_result = StreamingQueryResult(
        node_ids=many_ids,
        partial_loader=loader,
        batch_size=100  # Process 100 nodes at a time
    )
    
    # Process the results in batches
    print(f"Processing {streaming_result.count()} nodes in batches...")
    
    start = time.time()
    processed = 0
    
    # We'll use batched iteration
    for batch_start in range(0, streaming_result.count(), 500):
        batch = streaming_result.get_batch(batch_start, 500)
        processed += len(batch)
        
        print(f"Processed batch: {batch_start} to {batch_start + len(batch)}, Memory usage: {len(loader.loaded_nodes)} nodes")
    
    duration = time.time() - start
    print(f"Processed {processed} nodes in {duration:.2f} seconds using batches")
    
    # Clean up
    print("\nCleaning up...")
    loader.close()
    monitor.stop_monitoring()
    
    print("Memory management example complete!")


def enhanced_caching_example():
    """Demonstrate enhanced caching with predictive prefetching and temporal-aware frequency caching."""
    print("\n=== Enhanced Caching Example ===\n")
    
    # Create a node store with 5,000 nodes
    print("Creating test dataset with 5,000 nodes...")
    store = InMemoryNodeStore()
    nodes = generate_random_nodes(5000)
    
    # Add nodes to store
    for node in nodes:
        store.put(node.id, node)
    
    # Create an index manager with a combined index
    class SimpleIndexManager:
        def __init__(self):
            self.indices = {}
            self.combined = CombinedIndex()
        
        def has_index(self, name):
            return name == "combined"
        
        def get_index(self, name):
            return self.combined if name == "combined" else None
    
    index_manager = SimpleIndexManager()
    
    # Add nodes to the combined index
    for node in nodes:
        index_manager.combined.insert(
            node_id=node.id,
            time=node.position[0],
            position=(node.position[1], node.position[2])
        )
    
    # Set up predictive prefetch cache
    print("Setting up predictive prefetch cache...")
    prefetch_cache = PredictivePrefetchCache(
        max_size=500,
        prefetch_count=50,
        prefetch_threshold=0.4
    )
    prefetch_cache.set_node_store(store)
    
    # Set up temporal frequency cache
    print("Setting up temporal frequency cache...")
    temporal_cache = TemporalFrequencyCache(
        max_size=500,
        time_weight=0.5,
        frequency_weight=0.3,
        recency_weight=0.2
    )
    
    # Create a query engine with the enhanced caches
    print("Creating query engine...")
    engine = QueryEngine(
        node_store=store,
        index_manager=index_manager,
        config={
            "enable_statistics": True,
            "cache_ttl": 60.0
        }
    )
    
    # Add the caches to the query engine
    temporal_now = datetime.now()
    temporal_start = temporal_now - timedelta(days=14)
    temporal_end = temporal_now + timedelta(days=1)
    temporal_cache.set_time_window(temporal_start, temporal_end)
    
    # Create a pattern of queries to demonstrate predictive patterns
    print("\nRunning queries to establish access patterns...")
    
    # We'll create a pattern where a temporal query is often followed by a spatial query
    for i in range(10):
        # Temporal query: "What happened last week?"
        time_start = datetime(2020 + i % 3, 1, 1)
        time_end = time_start + timedelta(days=7)
        
        temporal_query = Query().filter(
            time_between=(time_start.timestamp(), time_end.timestamp())
        )
        
        print(f"Executing temporal query for {time_start.strftime('%Y-%m-%d')} to {time_end.strftime('%Y-%m-%d')}...")
        temporal_result = engine.execute(temporal_query)
        
        # After a temporal query, we often look at a specific region
        # This establishes a pattern: temporal query -> spatial query
        region_center_x = 50 + (i % 5) * 10
        region_center_y = 50 + (i % 5) * 10
        
        spatial_query = Query().filter(
            region=(
                region_center_x - 10,
                region_center_y - 10,
                region_center_x + 10,
                region_center_y + 10
            )
        )
        
        print(f"Executing spatial query for region around ({region_center_x}, {region_center_y})...")
        spatial_result = engine.execute(spatial_query)
    
    # Now run a new temporal query and see if the cache prefetches the spatial query data
    test_time_start = datetime(2023, 1, 1)
    test_time_end = test_time_start + timedelta(days=7)
    
    test_temporal_query = Query().filter(
        time_between=(test_time_start.timestamp(), test_time_end.timestamp())
    )
    
    print("\nExecuting test temporal query...")
    test_temporal_result = engine.execute(test_temporal_query)
    
    # The prefetch cache should now be loading data for a predicted spatial query
    print("Waiting for prefetching to occur...")
    time.sleep(1.0)  # Give time for prefetch thread to run
    
    # Now execute the spatial query that follows the pattern and see if it's faster
    test_region_center_x = 50
    test_region_center_y = 50
    
    test_spatial_query = Query().filter(
        region=(
            test_region_center_x - 10,
            test_region_center_y - 10,
            test_region_center_x + 10,
            test_region_center_y + 10
        )
    )
    
    print("Executing test spatial query (should be faster due to prefetching)...")
    start = time.time()
    test_spatial_result = engine.execute(test_spatial_query)
    duration = time.time() - start
    
    print(f"Spatial query executed in {duration:.4f} seconds, found {test_spatial_result.count()} results")
    
    # Test the temporal frequency cache by repeatedly accessing nodes in a specific time window
    print("\nTesting temporal frequency cache...")
    
    # Find nodes in a specific time window
    window_start = datetime(2022, 1, 1)
    window_end = datetime(2022, 1, 31)
    
    window_query = Query().filter(
        time_between=(window_start.timestamp(), window_end.timestamp())
    )
    
    print(f"Finding nodes in window {window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}...")
    window_result = engine.execute(window_query)
    
    # Get some nodes from the result
    test_nodes = []
    for i, item in enumerate(window_result.items):
        if i < 10:
            test_nodes.append(item)
        else:
            break
    
    # Access these nodes repeatedly to increase their frequency
    print(f"Accessing {len(test_nodes)} nodes repeatedly...")
    for i in range(5):
        for node in test_nodes:
            temporal_cache.get(node.id)
    
    # Now clear the cache and add them back
    temporal_cache.clear()
    
    # Add nodes back in reverse order
    for node in reversed(test_nodes):
        temporal_cache.put(node)
    
    # Add some other nodes
    other_nodes = generate_random_nodes(20)
    for node in other_nodes:
        temporal_cache.put(node)
    
    # Now get a high-frequency node and see if it's still in cache
    if test_nodes:
        high_freq_node = test_nodes[0]
        print(f"Checking if high-frequency node {high_freq_node.id} is still in cache...")
        cached_node = temporal_cache.get(high_freq_node.id)
        
        if cached_node:
            print("SUCCESS: Node is still in cache despite being added before other nodes")
        else:
            print("Node was not in cache")
    
    # Clean up
    print("\nCleaning up...")
    prefetch_cache.close()
    
    print("Enhanced caching example complete!")


if __name__ == "__main__":
    print("=== Memory Management and Caching Examples ===")
    print("\nThis example demonstrates how to use the memory management and")
    print("caching features to efficiently work with large datasets.\n")
    
    basic_memory_management_example()
    enhanced_caching_example() 
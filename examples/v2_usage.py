#!/usr/bin/env python3
"""
Example usage of the Temporal-Spatial Database v2 components.

This example demonstrates how to use the new node structure, serialization,
storage, and caching systems.
"""

import os
import shutil
import time
import uuid
from datetime import datetime, timedelta
import random

from src.core.node_v2 import Node, NodeConnection
from src.storage.serializers import get_serializer
from src.storage.node_store_v2 import InMemoryNodeStore, RocksDBNodeStore
from src.storage.cache import LRUCache, TemporalAwareCache, CacheChain
from src.storage.key_management import IDGenerator, TimeBasedIDGenerator
from src.storage.error_handling import retry, ExponentialBackoffStrategy


def create_sample_nodes(num_nodes=50):
    """Create sample nodes with cylindrical coordinates."""
    nodes = []
    
    # Base time for temporal coordinates (now)
    base_time = time.time()
    
    # Generator for time-based sequential IDs
    id_generator = TimeBasedIDGenerator()
    
    for i in range(num_nodes):
        # Generate cylindrical coordinates (time, radius, theta)
        t = base_time - random.randint(0, 365 * 24 * 60 * 60)  # Random time in the past year
        r = random.uniform(0, 10)  # Radius
        theta = random.uniform(0, 2 * 3.14159)  # Angle
        
        # Create a node with these coordinates
        node = Node(
            id=id_generator.generate_uuid(),
            content={
                "name": f"Node {i}",
                "value": random.random() * 100,
                "tags": random.sample(["science", "math", "history", "art", "technology"], 
                                    k=random.randint(1, 3))
            },
            position=(t, r, theta),
            metadata={
                "creation_time": datetime.now().isoformat(),
                "importance": random.choice(["low", "medium", "high"])
            }
        )
        
        nodes.append(node)
    
    # Create connections between nodes
    for i, node in enumerate(nodes):
        # Create 1-3 random connections
        for _ in range(random.randint(1, 3)):
            # Choose a random target node that's not this node
            target_idx = random.randint(0, len(nodes) - 1)
            if target_idx == i:
                continue
            
            target_node = nodes[target_idx]
            
            # Create a connection with random properties
            node.add_connection(
                target_id=target_node.id,
                connection_type=random.choice(["reference", "association", "causal"]),
                strength=random.random(),
                metadata={"discovered_at": datetime.now().isoformat()}
            )
    
    return nodes


def demo_serialization(nodes):
    """Demonstrate serialization with different formats."""
    print("\n===== Serialization Demo =====")
    
    # Choose a node to serialize
    node = nodes[0]
    print(f"Original node: ID={node.id}, Position={node.position}")
    print(f"Connections: {len(node.connections)}")
    
    # Serialize with JSON
    json_serializer = get_serializer('json')
    json_data = json_serializer.serialize(node)
    print(f"JSON serialized size: {len(json_data)} bytes")
    
    # Serialize with MessagePack
    msgpack_serializer = get_serializer('msgpack')
    msgpack_data = msgpack_serializer.serialize(node)
    print(f"MessagePack serialized size: {len(msgpack_data)} bytes")
    print(f"Size reduction: {(1 - len(msgpack_data) / len(json_data)) * 100:.1f}%")
    
    # Deserialize and verify
    restored_node = msgpack_serializer.deserialize(msgpack_data)
    print(f"Restored node: ID={restored_node.id}, Position={restored_node.position}")
    print(f"Connections: {len(restored_node.connections)}")
    
    # Verify fields
    assert node.id == restored_node.id, "ID mismatch"
    assert node.position == restored_node.position, "Position mismatch"
    assert len(node.connections) == len(restored_node.connections), "Connections count mismatch"
    print("✓ Serialization integrity verified")


def demo_storage(nodes):
    """Demonstrate storage with different backends."""
    print("\n===== Storage Demo =====")
    
    # In-memory storage
    print("Testing in-memory storage...")
    memory_store = InMemoryNodeStore()
    
    # Store all nodes
    start_time = time.time()
    for node in nodes:
        memory_store.put(node)
    
    memory_time = time.time() - start_time
    print(f"Stored {len(nodes)} nodes in memory in {memory_time:.4f} seconds")
    
    # Verify count
    assert memory_store.count() == len(nodes), "Node count mismatch"
    
    # RocksDB storage
    print("Testing RocksDB storage...")
    db_path = "./example_rocksdb"
    
    # Clean up any existing DB
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # Create the store with MessagePack serialization
    rocksdb_store = RocksDBNodeStore(
        db_path=db_path,
        create_if_missing=True,
        serialization_format='msgpack'
    )
    
    # Store all nodes
    start_time = time.time()
    for node in nodes:
        rocksdb_store.put(node)
    
    rocksdb_time = time.time() - start_time
    print(f"Stored {len(nodes)} nodes in RocksDB in {rocksdb_time:.4f} seconds")
    
    # Verify count
    assert rocksdb_store.count() == len(nodes), "Node count mismatch"
    
    # Batch operations
    print("Testing batch operations...")
    
    # Clear the store
    rocksdb_store.clear()
    assert rocksdb_store.count() == 0, "Store not cleared"
    
    # Batch put
    start_time = time.time()
    rocksdb_store.batch_put(nodes)
    
    batch_time = time.time() - start_time
    print(f"Batch stored {len(nodes)} nodes in {batch_time:.4f} seconds")
    print(f"Speedup vs. individual puts: {rocksdb_time / batch_time:.1f}x")
    
    # Verify count again
    assert rocksdb_store.count() == len(nodes), "Node count mismatch after batch put"
    
    # Close the store
    rocksdb_store.close()
    print(f"RocksDB store closed. Database stored at: {db_path}")


def demo_caching(nodes):
    """Demonstrate caching with different strategies."""
    print("\n===== Caching Demo =====")
    
    # Create an in-memory store to use with the cache
    store = InMemoryNodeStore()
    for node in nodes:
        store.put(node)
    
    # Create an LRU cache
    lru_cache = LRUCache(max_size=10)
    
    # Create a temporal-aware cache
    # Set the time window to the last 30 days
    now = time.time()
    month_ago = now - (30 * 24 * 60 * 60)
    time_window = (datetime.fromtimestamp(month_ago), datetime.fromtimestamp(now))
    
    temporal_cache = TemporalAwareCache(
        max_size=10,
        current_time_window=time_window,
        time_weight=0.7
    )
    
    # Create a combined cache chain
    cache_chain = CacheChain([lru_cache, temporal_cache])
    
    # Test with random access patterns
    NUM_ACCESSES = 1000
    print(f"Simulating {NUM_ACCESSES} random node accesses...")
    
    # Track performance
    no_cache_times = []
    lru_times = []
    temporal_times = []
    chain_times = []
    
    # Track cache hits
    lru_hits = 0
    temporal_hits = 0
    chain_hits = 0
    
    # Clear caches
    lru_cache.clear()
    temporal_cache.clear()
    
    # Access nodes randomly
    for _ in range(NUM_ACCESSES):
        # Choose a node
        node_id = random.choice(nodes).id
        
        # Time access without cache
        start_time = time.time()
        store.get(node_id)
        no_cache_times.append(time.time() - start_time)
        
        # Time access with LRU cache
        start_time = time.time()
        node = lru_cache.get(node_id)
        if node is None:
            node = store.get(node_id)
            lru_cache.put(node)
        else:
            lru_hits += 1
        lru_times.append(time.time() - start_time)
        
        # Time access with temporal cache
        start_time = time.time()
        node = temporal_cache.get(node_id)
        if node is None:
            node = store.get(node_id)
            temporal_cache.put(node)
        else:
            temporal_hits += 1
        temporal_times.append(time.time() - start_time)
        
        # Time access with cache chain
        start_time = time.time()
        node = cache_chain.get(node_id)
        if node is None:
            node = store.get(node_id)
            cache_chain.put(node)
        else:
            chain_hits += 1
        chain_times.append(time.time() - start_time)
    
    # Print results
    print(f"LRU Cache: {lru_hits}/{NUM_ACCESSES} hits ({lru_hits/NUM_ACCESSES*100:.1f}%)")
    print(f"Temporal Cache: {temporal_hits}/{NUM_ACCESSES} hits ({temporal_hits/NUM_ACCESSES*100:.1f}%)")
    print(f"Cache Chain: {chain_hits}/{NUM_ACCESSES} hits ({chain_hits/NUM_ACCESSES*100:.1f}%)")
    
    print(f"Average access time without cache: {sum(no_cache_times)/len(no_cache_times)*1000:.3f} ms")
    print(f"Average access time with LRU cache: {sum(lru_times)/len(lru_times)*1000:.3f} ms")
    print(f"Average access time with temporal cache: {sum(temporal_times)/len(temporal_times)*1000:.3f} ms")
    print(f"Average access time with cache chain: {sum(chain_times)/len(chain_times)*1000:.3f} ms")


def demo_error_handling():
    """Demonstrate error handling and retries."""
    print("\n===== Error Handling Demo =====")
    
    # Create a function that fails occasionally
    fail_count = 0
    
    def flaky_function():
        nonlocal fail_count
        fail_count += 1
        
        # Fail 3 times, then succeed
        if fail_count <= 3:
            print(f"Attempt {fail_count}: Simulating a failure...")
            raise ConnectionError("Simulated connection error")
        
        print(f"Attempt {fail_count}: Success!")
        return "Operation completed successfully"
    
    # Apply retry decorator
    retry_strategy = ExponentialBackoffStrategy(
        initial_delay=0.1,  # 100ms initial delay
        max_delay=1.0,      # 1s maximum delay
        backoff_factor=2.0  # Double the delay each time
    )
    
    @retry(max_attempts=5, retry_strategy=retry_strategy, 
           retryable_exceptions=[ConnectionError])
    def resilient_function():
        return flaky_function()
    
    # Try the function
    print("Calling function with retry...")
    result = resilient_function()
    print(f"Final result: {result}")
    print(f"Total attempts: {fail_count}")


def main():
    """Run all demos."""
    print("Temporal-Spatial Database v2 Demo")
    print("=================================")
    
    # Create sample nodes
    print("Creating sample nodes...")
    nodes = create_sample_nodes()
    print(f"Created {len(nodes)} nodes")
    
    # Run all demos
    demo_serialization(nodes)
    demo_storage(nodes)
    demo_caching(nodes)
    demo_error_handling()
    
    print("\nDemo completed successfully.")


if __name__ == "__main__":
    main() 
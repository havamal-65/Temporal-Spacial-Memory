#!/usr/bin/env python3
"""
Performance test script for SpatialIndex.
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta
import uuid

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.indexing.rtree import SpatialIndex, SplitStrategy, DistanceMetric
from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

def generate_random_nodes(count=10000, dimension=3, random_seed=42):
    """Generate random nodes for testing."""
    random.seed(random_seed)
    nodes = []
    
    base_time = datetime(2023, 1, 1)
    
    for i in range(count):
        node_id = str(uuid.uuid4())
        
        # Random spatial coordinates in range [0, 1000)
        coords = [random.uniform(0, 1000) for _ in range(dimension)]
        
        # Random temporal coordinate
        days = random.randint(0, 365)
        hours = random.randint(0, 23)
        minutes = random.randint(0, 59)
        seconds = random.randint(0, 59)
        timestamp = base_time + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        
        # Create node
        node = Node(
            id=node_id,
            coordinates=Coordinates(
                spatial=SpatialCoordinate(tuple(coords)),
                temporal=TemporalCoordinate(timestamp)
            ),
            data={"index": i}
        )
        
        nodes.append(node)
    
    return nodes

def test_bulk_load(nodes, dimension=3):
    """Test bulk loading performance."""
    print(f"Testing bulk load performance with {len(nodes)} nodes...")
    
    start_time = time.time()
    index = SpatialIndex(dimension=dimension, in_memory=True)
    index.bulk_load(nodes)
    elapsed = time.time() - start_time
    
    print(f"Bulk load completed in {elapsed:.3f} seconds")
    print(f"Average time per node: {(elapsed / len(nodes)) * 1000:.3f} ms")
    
    return index

def test_individual_insert(nodes, dimension=3):
    """Test individual insert performance."""
    print(f"Testing individual insert performance with {len(nodes)} nodes...")
    
    start_time = time.time()
    index = SpatialIndex(dimension=dimension, in_memory=True)
    
    for node in nodes:
        index.insert(node)
    
    elapsed = time.time() - start_time
    
    print(f"Individual inserts completed in {elapsed:.3f} seconds")
    print(f"Average time per insert: {(elapsed / len(nodes)) * 1000:.3f} ms")
    
    return index

def test_nearest_queries(index, count=1000, dimension=3):
    """Test nearest neighbor query performance."""
    print(f"Testing {count} nearest neighbor queries...")
    
    times = []
    
    for _ in range(count):
        # Random query point
        query_point = tuple(random.uniform(0, 1000) for _ in range(dimension))
        
        start_time = time.time()
        index.nearest(query_point, num_results=10)
        elapsed = time.time() - start_time
        
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"Average query time: {avg_time * 1000:.3f} ms")
    print(f"Min query time: {min(times) * 1000:.3f} ms")
    print(f"Max query time: {max(times) * 1000:.3f} ms")

def test_range_queries(index, count=1000, dimension=3):
    """Test range query performance."""
    print(f"Testing {count} range queries...")
    
    times = []
    
    for _ in range(count):
        # Random range
        center = [random.uniform(0, 1000) for _ in range(dimension)]
        size = random.uniform(10, 100)
        
        lower_bounds = tuple(c - size/2 for c in center)
        upper_bounds = tuple(c + size/2 for c in center)
        
        start_time = time.time()
        index.range_query(lower_bounds, upper_bounds)
        elapsed = time.time() - start_time
        
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"Average query time: {avg_time * 1000:.3f} ms")
    print(f"Min query time: {min(times) * 1000:.3f} ms")
    print(f"Max query time: {max(times) * 1000:.3f} ms")

def test_distance_metrics(nodes, dimension=3):
    """Compare performance of different distance metrics."""
    print("Comparing performance of different distance metrics...")
    
    # Test with Euclidean distance
    print("\nTesting EUCLIDEAN metric:")
    euclidean_index = SpatialIndex(
        dimension=dimension, 
        distance_metric=DistanceMetric.EUCLIDEAN,
        in_memory=True
    )
    euclidean_index.bulk_load(nodes[:1000])  # Use a subset for faster testing
    
    # Test with Manhattan distance
    print("\nTesting MANHATTAN metric:")
    manhattan_index = SpatialIndex(
        dimension=dimension, 
        distance_metric=DistanceMetric.MANHATTAN,
        in_memory=True
    )
    manhattan_index.bulk_load(nodes[:1000])
    
    # Test with Chebyshev distance
    print("\nTesting CHEBYSHEV metric:")
    chebyshev_index = SpatialIndex(
        dimension=dimension, 
        distance_metric=DistanceMetric.CHEBYSHEV,
        in_memory=True
    )
    chebyshev_index.bulk_load(nodes[:1000])
    
    # Test nearest neighbor queries
    query_count = 100
    
    print(f"\nRunning {query_count} nearest neighbor queries for each metric...")
    
    # Test Euclidean
    start_time = time.time()
    for _ in range(query_count):
        query_point = tuple(random.uniform(0, 1000) for _ in range(dimension))
        euclidean_index.nearest(query_point, num_results=10)
    euclidean_time = time.time() - start_time
    
    # Test Manhattan
    start_time = time.time()
    for _ in range(query_count):
        query_point = tuple(random.uniform(0, 1000) for _ in range(dimension))
        manhattan_index.nearest(query_point, num_results=10)
    manhattan_time = time.time() - start_time
    
    # Test Chebyshev
    start_time = time.time()
    for _ in range(query_count):
        query_point = tuple(random.uniform(0, 1000) for _ in range(dimension))
        chebyshev_index.nearest(query_point, num_results=10)
    chebyshev_time = time.time() - start_time
    
    print(f"Euclidean metric: {euclidean_time:.3f} seconds total, {(euclidean_time / query_count) * 1000:.3f} ms per query")
    print(f"Manhattan metric: {manhattan_time:.3f} seconds total, {(manhattan_time / query_count) * 1000:.3f} ms per query")
    print(f"Chebyshev metric: {chebyshev_time:.3f} seconds total, {(chebyshev_time / query_count) * 1000:.3f} ms per query")

def main():
    """Run the performance tests."""
    # Number of nodes to generate
    node_count = 10000
    
    # Dimensionality of the spatial index
    dimension = 3
    
    print(f"Generating {node_count} random nodes...")
    nodes = generate_random_nodes(node_count, dimension)
    print("Node generation complete.")
    
    print("\n=== BULK LOAD TEST ===")
    index = test_bulk_load(nodes, dimension)
    
    print("\n=== INDIVIDUAL INSERT TEST ===")
    test_individual_insert(nodes[:1000], dimension)  # Use a subset for faster testing
    
    print("\n=== NEAREST NEIGHBOR QUERY TEST ===")
    test_nearest_queries(index, 1000, dimension)
    
    print("\n=== RANGE QUERY TEST ===")
    test_range_queries(index, 1000, dimension)
    
    print("\n=== DISTANCE METRIC COMPARISON ===")
    test_distance_metrics(nodes, dimension)
    
    print("\nPerformance testing complete.")

if __name__ == "__main__":
    main() 
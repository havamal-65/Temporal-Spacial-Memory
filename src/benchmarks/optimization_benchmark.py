#!/usr/bin/env python3
"""
Benchmark tests for the Mesh Tube Knowledge Database optimizations.
This script compares performance before and after implementing:
1. Storage compression with delta encoding
2. R-tree spatial indexing
3. Temporal-aware caching
"""

import time
import random
import matplotlib.pyplot as plt
import numpy as np
from src.models.mesh_tube import MeshTube

def generate_test_data(num_nodes=1000, time_span=100):
    """Generate test data for the benchmark"""
    mesh_tube = MeshTube("benchmark_test")
    
    # Create nodes with random content
    nodes = []
    for i in range(num_nodes):
        # Generate random position
        t = random.uniform(0, time_span)
        distance = random.uniform(0, 10)
        angle = random.uniform(0, 360)
        
        # Create content
        content = {
            f"key_{i}": f"value_{i}",
            "timestamp": t,
            "importance": random.uniform(0, 1)
        }
        
        # Add node
        node = mesh_tube.add_node(
            content=content,
            time=t,
            distance=distance,
            angle=angle
        )
        nodes.append(node)
        
        # Create some connections
        if i > 0:
            # Connect to some previous nodes
            for _ in range(min(3, i)):
                prev_idx = random.randint(0, i-1)
                mesh_tube.connect_nodes(node.node_id, nodes[prev_idx].node_id)
    
    # Create delta chains
    for i in range(1, num_nodes, 10):
        # Choose a random node to create deltas from
        base_idx = random.randint(0, num_nodes-1)
        base_node = nodes[base_idx]
        
        # Create a chain of delta nodes
        prev_node = base_node
        for j in range(5):  # Create chain of 5 deltas
            # Calculate new position (forward in time)
            new_time = prev_node.time + random.uniform(0.1, 1.0)
            if new_time > time_span:
                break
                
            # Create delta content (small changes)
            delta_content = {
                f"delta_key_{j}": f"delta_value_{j}",
                "modified_at": new_time
            }
            
            # Apply delta
            delta_node = mesh_tube.apply_delta(
                original_node=prev_node,
                delta_content=delta_content,
                time=new_time
            )
            
            prev_node = delta_node
            nodes.append(delta_node)
    
    return mesh_tube, nodes

def benchmark_spatial_queries(mesh_tube, nodes, num_queries=100):
    """Benchmark spatial query performance"""
    start_time = time.time()
    
    # Reset cache statistics
    mesh_tube.clear_caches()
    
    for _ in range(num_queries):
        # Pick a random reference node
        ref_node = random.choice(nodes)
        
        # Get nearest nodes
        nearest = mesh_tube.get_nearest_nodes(ref_node, limit=10)
    
    # First run is without caching - clear stats
    cache_stats = mesh_tube.get_cache_statistics()
    elapsed = time.time() - start_time
    
    # Run again with caching
    start_time = time.time()
    for _ in range(num_queries):
        # Pick a random reference node (same sequence as before)
        random.seed(42)  # Make sure we use the same sequence
        ref_node = random.choice(nodes)
        
        # Get nearest nodes
        nearest = mesh_tube.get_nearest_nodes(ref_node, limit=10)
    
    cached_elapsed = time.time() - start_time
    cache_stats_after = mesh_tube.get_cache_statistics()
    
    return elapsed, cached_elapsed, cache_stats_after

def benchmark_delta_compression(mesh_tube, nodes):
    """Benchmark delta compression performance"""
    # Measure size before compression
    size_before = len(mesh_tube.nodes)
    
    # Measure time to compute states
    start_time = time.time()
    for _ in range(100):
        node = random.choice(nodes)
        state = mesh_tube.compute_node_state(node.node_id)
    compute_time_before = time.time() - start_time
    
    # Apply compression
    mesh_tube.compress_deltas(max_chain_length=3)
    
    # Measure size after compression
    size_after = len(mesh_tube.nodes)
    
    # Measure time after compression
    start_time = time.time()
    for _ in range(100):
        node = random.choice(nodes)
        state = mesh_tube.compute_node_state(node.node_id)
    compute_time_after = time.time() - start_time
    
    return size_before, size_after, compute_time_before, compute_time_after

def benchmark_temporal_window(mesh_tube, time_span):
    """Benchmark temporal window loading"""
    # Choose random time windows
    windows = []
    for _ in range(10):
        start = random.uniform(0, time_span * 0.8)
        end = start + random.uniform(time_span * 0.1, time_span * 0.2)
        windows.append((start, end))
    
    # Measure time to load windows
    times = []
    for start, end in windows:
        start_time = time.time()
        window_tube = mesh_tube.load_temporal_window(start, end)
        elapsed = time.time() - start_time
        times.append(elapsed)
        
        # Get size ratio
        full_size = len(mesh_tube.nodes)
        window_size = len(window_tube.nodes)
        ratio = window_size / full_size
        
        print(f"Window {start:.1f}-{end:.1f}: {window_size}/{full_size} nodes ({ratio:.2%}), loaded in {elapsed:.4f}s")
    
    return times

def plot_results(spatial_before, spatial_after, delta_before, delta_after):
    """Plot the benchmark results"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Spatial query performance
    labels = ['Without Cache', 'With Cache']
    times = [spatial_before, spatial_after]
    ax1.bar(labels, times, color=['#3498db', '#2ecc71'])
    ax1.set_ylabel('Time (seconds)')
    ax1.set_title('Spatial Query Performance')
    for i, v in enumerate(times):
        ax1.text(i, v + 0.01, f"{v:.4f}s", ha='center')
    
    # Delta compression
    labels = ['Before Compression', 'After Compression']
    node_counts = [delta_before, delta_after]
    ax2.bar(labels, node_counts, color=['#e74c3c', '#9b59b6'])
    ax2.set_ylabel('Number of Nodes')
    ax2.set_title('Delta Compression Effect')
    for i, v in enumerate(node_counts):
        ax2.text(i, v + 5, str(v), ha='center')
    
    plt.tight_layout()
    plt.savefig('optimization_benchmark_results.png')
    print("Results plotted and saved to optimization_benchmark_results.png")

def main():
    """Run all benchmarks"""
    print("Generating test data...")
    mesh_tube, nodes = generate_test_data(num_nodes=2000, time_span=100)
    print(f"Generated database with {len(mesh_tube.nodes)} nodes")
    
    print("\nBenchmarking spatial queries...")
    spatial_before, spatial_after, cache_stats = benchmark_spatial_queries(mesh_tube, nodes)
    print(f"Spatial query time without caching: {spatial_before:.4f}s")
    print(f"Spatial query time with caching: {spatial_after:.4f}s")
    print(f"Speedup: {spatial_before/spatial_after:.2f}x")
    print(f"Cache statistics: {cache_stats}")
    
    print("\nBenchmarking delta compression...")
    size_before, size_after, compute_before, compute_after = benchmark_delta_compression(mesh_tube, nodes)
    print(f"Size before compression: {size_before} nodes")
    print(f"Size after compression: {size_after} nodes")
    print(f"Reduction: {(size_before-size_after)/size_before:.2%}")
    print(f"Compute time before: {compute_before:.4f}s")
    print(f"Compute time after: {compute_after:.4f}s")
    
    print("\nBenchmarking temporal window loading...")
    window_times = benchmark_temporal_window(mesh_tube, 100)
    print(f"Average window load time: {sum(window_times)/len(window_times):.4f}s")
    
    print("\nPlotting results...")
    plot_results(spatial_before, spatial_after, size_before, size_after)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Benchmark runner for the Temporal-Spatial Memory Database.

This script runs performance tests for the MeshTube implementation.
"""

import os
import time
import random
import statistics
import matplotlib.pyplot as plt
import numpy as np
from src.models.mesh_tube import MeshTube
from src.models.node import Node

def create_test_database(num_nodes=100):
    """Create a test database with random nodes."""
    print(f"Creating test database with {num_nodes} nodes...")
    mesh = MeshTube(name="Benchmark", storage_path="data")
    
    # Create nodes with random positions
    nodes = []
    for i in range(num_nodes):
        node = mesh.add_node(
            content={"topic": f"Topic {i}", "data": f"Data for topic {i}"},
            time=random.uniform(0, 10),
            distance=random.uniform(0, 5),
            angle=random.uniform(0, 360)
        )
        nodes.append(node)
    
    # Create some random connections (about 5 per node)
    for node in nodes:
        connections = random.sample(nodes, min(5, len(nodes)))
        for conn in connections:
            if conn.node_id != node.node_id:
                mesh.connect_nodes(node.node_id, conn.node_id)
    
    # Create some delta chains (updates to about 20% of nodes)
    nodes_to_update = random.sample(nodes, int(num_nodes * 0.2))
    for node in nodes_to_update:
        for i in range(3):  # Create 3 updates for each selected node
            mesh.apply_delta(
                original_node=node,
                delta_content={"update": i, "timestamp": time.time()},
                time=node.time + random.uniform(0.1, 1)
            )
    
    return mesh

def benchmark_operation(mesh, operation_name, operation_fn, iterations=10):
    """Benchmark a single operation and return performance metrics."""
    # Warmup
    for _ in range(3):
        operation_fn(mesh)
    
    # Measurement phase
    times = []
    for _ in range(iterations):
        start = time.time()
        operation_fn(mesh)
        end = time.time()
        times.append((end - start) * 1000)  # Convert to ms
    
    results = {
        "min": min(times),
        "max": max(times),
        "avg": statistics.mean(times),
        "median": statistics.median(times)
    }
    
    print(f"  {operation_name}: min={results['min']:.2f}ms, max={results['max']:.2f}ms, avg={results['avg']:.2f}ms")
    
    return results

def plot_results(results, output_dir="benchmark_results"):
    """Plot the benchmark results."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create bar chart of average times
    plt.figure(figsize=(12, 6))
    operations = list(results.keys())
    avg_times = [results[op]["avg"] for op in operations]
    
    plt.bar(operations, avg_times)
    plt.title("MeshTube Operation Performance")
    plt.xlabel("Operation")
    plt.ylabel("Average Time (ms)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(os.path.join(output_dir, "benchmark_results.png"))
    print(f"Results plot saved to {output_dir}/benchmark_results.png")

def run_benchmarks(num_nodes=100, iterations=10):
    """Run all benchmarks and return results."""
    print(f"Running benchmarks with {num_nodes} nodes, {iterations} iterations per test...")
    
    # Create the test database
    mesh = create_test_database(num_nodes)
    
    # Get a sample node for testing
    sample_node = random.choice(list(mesh.nodes.values()))
    
    # Define operations to benchmark
    operations = {
        "Add Node": lambda m: m.add_node(
            content={"topic": "New Topic", "data": "Benchmark data"},
            time=random.uniform(0, 10),
            distance=random.uniform(0, 5),
            angle=random.uniform(0, 360)
        ),
        "Get Node": lambda m: m.get_node(sample_node.node_id),
        "Connect Nodes": lambda m: m.connect_nodes(
            sample_node.node_id, 
            random.choice(list(m.nodes.values())).node_id
        ),
        "Temporal Slice": lambda m: m.get_temporal_slice(
            time=random.uniform(0, 10),
            tolerance=0.5
        ),
        "Nearest Nodes": lambda m: m.get_nearest_nodes(
            sample_node,
            limit=5
        ),
        "Apply Delta": lambda m: m.apply_delta(
            original_node=sample_node,
            delta_content={"update": random.randint(0, 100)},
            time=sample_node.time + 0.1
        ),
        "Compute State": lambda m: m.compute_node_state(sample_node.node_id)
    }
    
    # Run benchmarks for each operation
    results = {}
    for name, operation in operations.items():
        print(f"Benchmarking {name}...")
        results[name] = benchmark_operation(mesh, name, operation, iterations)
    
    return results

def main():
    """Run the benchmarks and plot results."""
    print("Running benchmarks for the Temporal-Spatial Memory Database")
    print("===================================================================")
    
    results = run_benchmarks(num_nodes=100, iterations=20)
    plot_results(results)
    
if __name__ == "__main__":
    main() 
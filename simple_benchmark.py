#!/usr/bin/env python3
"""
Simple standalone benchmark for the Temporal-Spatial Memory Database.

This is a completely standalone benchmark that doesn't depend on any
of the project's code. It's useful for testing the benchmark framework.
"""

import os
import time
import random
import statistics
import matplotlib.pyplot as plt
import numpy as np

def run_operation(sleep_time):
    """Run a simple operation that just sleeps."""
    time.sleep(sleep_time)
    return True

def benchmark_operation(name, min_time, max_time, iterations=10):
    """Benchmark a single operation and return performance metrics."""
    # Measurement phase
    times = []
    for _ in range(iterations):
        sleep_time = random.uniform(min_time, max_time)
        start = time.time()
        run_operation(sleep_time)
        end = time.time()
        times.append((end - start) * 1000)  # Convert to ms
    
    results = {
        "min": min(times),
        "max": max(times),
        "avg": statistics.mean(times),
    }
    
    print(f"  {name}: min={results['min']:.2f}ms, max={results['max']:.2f}ms, avg={results['avg']:.2f}ms")
    
    return results

def plot_comparison(results, title, output_dir):
    """Plot comparison between different operations."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get operation names and values
    operation_names = list(results.keys())
    values = [results[name]["avg"] for name in operation_names]
    
    plt.figure(figsize=(10, 6))
    
    # Plot as a bar chart
    plt.bar(operation_names, values)
    plt.xlabel('Operations')
    plt.ylabel('Average Time (ms)')
    plt.title(f'{title} Performance Comparison')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the figure
    filename = os.path.join(output_dir, f"{title.replace(' ', '_').lower()}_comparison.png")
    plt.savefig(filename)
    plt.close()
    
    print(f"Plot saved to {filename}")

def run_benchmarks():
    """Run the simple benchmark."""
    print("Starting Simple Standalone Benchmark")
    print("====================================")
    
    # Define output directory
    output_dir = "benchmark_results/simple"
    os.makedirs(output_dir, exist_ok=True)
    
    # Define test operations with different sleep times
    operations = {
        "Operation_A": (0.01, 0.03),  # (min_time, max_time)
        "Operation_B": (0.02, 0.05),
        "Operation_C": (0.03, 0.07)
    }
    
    # Run the benchmarks
    results = {}
    for name, (min_time, max_time) in operations.items():
        print(f"Running benchmark for {name}...")
        results[name] = benchmark_operation(name, min_time, max_time)
    
    # Create visualization
    plot_comparison(results, "Test Operations", output_dir)
    
    print("\nBenchmark complete!")
    print(f"Results saved to {output_dir}")

if __name__ == "__main__":
    # Run the benchmark directly
    run_benchmarks() 
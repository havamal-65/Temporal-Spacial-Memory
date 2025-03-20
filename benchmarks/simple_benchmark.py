"""
Simple benchmark for the Temporal-Spatial Memory Database.

This is a simplified version of the benchmarks that just tests if the
visualization components work correctly. This is completely standalone
and doesn't depend on any of the project's code.
"""

import os
import time
import random
import statistics
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Callable, Any

class SimpleBenchmark:
    """A very simple benchmark just to test the visualization functionality."""
    
    def __init__(self, output_dir: str = "benchmark_results/simple"):
        """Initialize the simple benchmark suite."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
    
    def benchmark_operation(self, name: str, operation_func: Callable, 
                           iterations: int = 10) -> Dict[str, float]:
        """Benchmark a single operation and return performance metrics."""
        # Measurement phase
        times = []
        for _ in range(iterations):
            start = time.time()
            operation_func()
            end = time.time()
            times.append((end - start) * 1000)  # Convert to ms
        
        results = {
            "min": min(times),
            "max": max(times),
            "avg": statistics.mean(times),
        }
        
        self.results[name] = results
        return results
    
    def plot_comparison(self, title: str, operation_names: List[str]) -> None:
        """Plot comparison between different operations."""
        plt.figure(figsize=(10, 6))
        
        # Get the average values for each operation
        values = [self.results[name]["avg"] for name in operation_names]
        
        # Plot as a bar chart
        plt.bar(operation_names, values)
        plt.xlabel('Operations')
        plt.ylabel('Average Time (ms)')
        plt.title(f'{title} Performance Comparison')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save the figure
        filename = f"{title.replace(' ', '_').lower()}_comparison.png"
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def run_simple_benchmark(self):
        """Run some simple benchmarks for visualization testing."""
        print("Running simple benchmarks...")
        
        # Define some test operations
        operations = {
            "Operation_A": lambda: time.sleep(random.uniform(0.01, 0.03)),
            "Operation_B": lambda: time.sleep(random.uniform(0.02, 0.05)),
            "Operation_C": lambda: time.sleep(random.uniform(0.03, 0.07))
        }
        
        # Run the benchmarks
        for name, operation in operations.items():
            print(f"  Benchmarking {name}...")
            self.benchmark_operation(name, operation)
        
        # Create the visualizations
        print("Generating visualizations...")
        self.plot_comparison("Test Operations", list(operations.keys()))
        
        print(f"Simple benchmark complete. Results saved to {self.output_dir}")


def run_benchmarks():
    """Run the simple benchmark."""
    benchmark = SimpleBenchmark()
    benchmark.run_simple_benchmark()


if __name__ == "__main__":
    # This is separate from the __init__.py import to allow direct running
    print("Running standalone simple benchmark...")
    run_benchmarks() 
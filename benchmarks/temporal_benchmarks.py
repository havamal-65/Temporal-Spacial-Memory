"""
Benchmarks for the Temporal-Spatial Memory Database.

This module provides comprehensive benchmarks for testing the performance
of the database components, with visualization of results.
"""

import os
import time
import random
import statistics
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Tuple, Optional

# Import core components
from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

# Import index components with error handling
try:
    from src.indexing.rtree import SpatialIndex
    from src.indexing.temporal_index import TemporalIndex
    from src.indexing.combined_index import CombinedIndex
    INDEXING_AVAILABLE = True
except ImportError:
    print("WARNING: Indexing components not available. Benchmarks will not work properly.")
    INDEXING_AVAILABLE = False

# Import storage components with error handling
try:
    from src.storage.node_store import InMemoryNodeStore
    from src.storage.rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError:
    print("WARNING: RocksDB not available. Using in-memory store only.")
    ROCKSDB_AVAILABLE = False
    # Create a mock RocksDBNodeStore
    class RocksDBNodeStore(InMemoryNodeStore):
        def __init__(self, *args, **kwargs):
            super().__init__()


class BenchmarkSuite:
    """Comprehensive benchmark suite for the Temporal-Spatial Database."""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        """Initialize the benchmark suite.
        
        Args:
            output_dir: Directory to save benchmark results and visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
    
    def benchmark_operation(self, name: str, operation_func: Callable, 
                           iterations: int = 100, warmup: int = 5) -> Dict[str, float]:
        """Benchmark a single operation and return performance metrics.
        
        Args:
            name: Name of the operation
            operation_func: Function to benchmark
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not counted)
            
        Returns:
            Dictionary with performance metrics
        """
        # Warmup phase
        for _ in range(warmup):
            operation_func()
            
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
            "median": statistics.median(times),
            "p95": statistics.quantile(times, 0.95),
            "p99": statistics.quantile(times, 0.99),
            "stddev": statistics.stdev(times) if len(times) > 1 else 0
        }
        
        self.results[name] = results
        return results
    
    def plot_comparison(self, title: str, operation_names: List[str], 
                       metrics: List[str] = ["avg", "p95", "p99"]) -> None:
        """Plot comparison between different operations.
        
        Args:
            title: Plot title
            operation_names: Names of operations to compare
            metrics: Which metrics to include in the plot
        """
        plt.figure(figsize=(12, 8))
        
        x = np.arange(len(operation_names))
        width = 0.8 / len(metrics)
        
        for i, metric in enumerate(metrics):
            values = [self.results[name][metric] for name in operation_names]
            plt.bar(x + i * width - 0.4 + width/2, values, width, label=metric)
        
        plt.xlabel('Operations')
        plt.ylabel('Time (ms)')
        plt.title(f'{title} Performance Comparison')
        plt.xticks(x, operation_names, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        filename = f"{title.replace(' ', '_').lower()}_comparison.png"
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
    
    def plot_data_size_scaling(self, title: str, operation_names: List[str], 
                              sizes: List[int], metric: str = "avg") -> None:
        """Plot how performance scales with data size.
        
        Args:
            title: Plot title
            operation_names: Names of operations to plot
            sizes: Data sizes corresponding to each operation
            metric: Which metric to plot (e.g., "avg", "p95")
        """
        plt.figure(figsize=(12, 6))
        
        values = [self.results[name][metric] for name in operation_names]
        
        plt.plot(sizes, values, 'o-', linewidth=2)
        plt.xlabel('Data Size')
        plt.ylabel(f'{metric.upper()} Time (ms)')
        plt.title(f'{title} Scaling with Data Size ({metric.upper()})')
        plt.grid(True, alpha=0.3)
        
        # Add logarithmic trendline
        if min(values) > 0:  # Avoid log of zero or negative values
            coeffs = np.polyfit(np.log(sizes), np.log(values), 1)
            polynomial = np.poly1d(coeffs)
            plt.plot(sizes, np.exp(polynomial(np.log(sizes))), 'r--', 
                    label=f'Trendline: O(n^{coeffs[0]:.2f})')
            plt.legend()
        
        plt.tight_layout()
        
        filename = f"{title.replace(' ', '_').lower()}_scaling.png"
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()


class TemporalIndexBenchmark(BenchmarkSuite):
    """Benchmarks specifically for the Temporal Index component."""
    
    def __init__(self, output_dir: str = "benchmark_results/temporal"):
        """Initialize the temporal benchmark suite."""
        super().__init__(output_dir)
        self.temporal_index = TemporalIndex()
    
    def generate_random_nodes(self, count: int) -> List[Node]:
        """Generate random nodes with temporal coordinates.
        
        Args:
            count: Number of nodes to generate
            
        Returns:
            List of random nodes
        """
        nodes = []
        for i in range(count):
            # Generate a random timestamp within the past year
            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            # Create temporal coordinate
            coords = Coordinates(
                temporal=TemporalCoordinate(timestamp=timestamp)
            )
            
            # Create the node
            node = Node(
                id=f"node_{i}",
                data={"value": random.random()},
                coordinates=coords
            )
            
            nodes.append(node)
        
        return nodes
    
    def benchmark_insertions(self, sizes: List[int]) -> None:
        """Benchmark insertion performance for different batch sizes.
        
        Args:
            sizes: List of batch sizes to test
        """
        names = []
        for size in sizes:
            # Generate the nodes once
            nodes = self.generate_random_nodes(size)
            
            # Create a fresh index for each test
            index = TemporalIndex()
            
            # Define the operation to benchmark
            def operation():
                for node in nodes:
                    index.insert(node)
            
            # Run the benchmark
            name = f"temporal_insert_{size}"
            names.append(name)
            self.benchmark_operation(name, operation, iterations=5)
        
        # Plot the results
        self.plot_data_size_scaling("Temporal Index Insertion", names, sizes)
    
    def benchmark_queries(self, index_size: int = 10000, query_counts: List[int] = [10, 100, 1000]) -> None:
        """Benchmark query performance.
        
        Args:
            index_size: Size of the index to use for testing
            query_counts: List of query result sizes to test
        """
        # Create and populate the index
        self.temporal_index = TemporalIndex()
        nodes = self.generate_random_nodes(index_size)
        
        for node in nodes:
            self.temporal_index.insert(node)
        
        # Prepare query parameters
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        
        # Benchmark range queries with different time spans
        range_query_names = []
        range_spans = [1, 7, 30, 90, 180, 365]  # in days
        
        for span in range_spans:
            name = f"temporal_range_{span}d"
            range_query_names.append(name)
            
            start_time = one_year_ago
            end_time = start_time + timedelta(days=span)
            
            def operation():
                self.temporal_index.range_query(start_time, end_time)
            
            self.benchmark_operation(name, operation, iterations=20)
        
        # Plot range query results
        self.plot_comparison("Temporal Range Query Performance", range_query_names)
        
        # Benchmark nearest neighbor queries with different result counts
        nearest_query_names = []
        
        for count in query_counts:
            name = f"temporal_nearest_{count}"
            nearest_query_names.append(name)
            
            query_time = one_year_ago + timedelta(days=random.randint(0, 365))
            
            def operation():
                self.temporal_index.nearest(query_time, num_results=count)
            
            self.benchmark_operation(name, operation, iterations=20)
        
        # Plot nearest query results
        self.plot_comparison("Temporal Nearest Query Performance", nearest_query_names)


class SpatialIndexBenchmark(BenchmarkSuite):
    """Benchmarks specifically for the Spatial Index component."""
    
    def __init__(self, output_dir: str = "benchmark_results/spatial"):
        """Initialize the spatial benchmark suite."""
        super().__init__(output_dir)
        self.spatial_index = SpatialIndex(dimension=3)
    
    def generate_random_nodes(self, count: int, dimension: int = 3) -> List[Node]:
        """Generate random nodes with spatial coordinates.
        
        Args:
            count: Number of nodes to generate
            dimension: Dimensionality of the spatial coordinates
            
        Returns:
            List of random nodes
        """
        nodes = []
        for i in range(count):
            # Generate random spatial coordinates
            dimensions = tuple(random.uniform(-100, 100) for _ in range(dimension))
            
            # Create spatial coordinate
            coords = Coordinates(
                spatial=SpatialCoordinate(dimensions=dimensions)
            )
            
            # Create the node
            node = Node(
                id=f"node_{i}",
                data={"value": random.random()},
                coordinates=coords
            )
            
            nodes.append(node)
        
        return nodes
    
    def benchmark_insertions(self, sizes: List[int]) -> None:
        """Benchmark insertion performance for different batch sizes.
        
        Args:
            sizes: List of batch sizes to test
        """
        names = []
        for size in sizes:
            # Generate the nodes once
            nodes = self.generate_random_nodes(size)
            
            # Create a fresh index for each test
            index = SpatialIndex(dimension=3)
            
            # Define the operation to benchmark
            def operation():
                for node in nodes:
                    index.insert(node)
            
            # Run the benchmark
            name = f"spatial_insert_{size}"
            names.append(name)
            self.benchmark_operation(name, operation, iterations=5)
        
        # Plot the results
        self.plot_data_size_scaling("Spatial Index Insertion", names, sizes)
    
    def benchmark_queries(self, index_size: int = 10000, query_counts: List[int] = [10, 100, 1000]) -> None:
        """Benchmark query performance.
        
        Args:
            index_size: Size of the index to use for testing
            query_counts: List of query result sizes to test
        """
        # Create and populate the index
        self.spatial_index = SpatialIndex(dimension=3)
        nodes = self.generate_random_nodes(index_size)
        
        for node in nodes:
            self.spatial_index.insert(node)
        
        # Benchmark range queries with different sizes
        range_query_names = []
        range_sizes = [10, 50, 100, 200, 500]  # range size in units
        
        for size in range_sizes:
            name = f"spatial_range_{size}"
            range_query_names.append(name)
            
            center = (random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50))
            lower_bounds = tuple(c - size/2 for c in center)
            upper_bounds = tuple(c + size/2 for c in center)
            
            def operation():
                self.spatial_index.range_query(lower_bounds, upper_bounds)
            
            self.benchmark_operation(name, operation, iterations=20)
        
        # Plot range query results
        self.plot_comparison("Spatial Range Query Performance", range_query_names)
        
        # Benchmark nearest neighbor queries with different result counts
        nearest_query_names = []
        
        for count in query_counts:
            name = f"spatial_nearest_{count}"
            nearest_query_names.append(name)
            
            point = (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))
            
            def operation():
                self.spatial_index.nearest(point, num_results=count)
            
            self.benchmark_operation(name, operation, iterations=20)
        
        # Plot nearest query results
        self.plot_comparison("Spatial Nearest Query Performance", nearest_query_names)


class CombinedIndexBenchmark(BenchmarkSuite):
    """Benchmarks for the Combined Spatio-Temporal Index."""
    
    def __init__(self, output_dir: str = "benchmark_results/combined"):
        """Initialize the combined benchmark suite."""
        super().__init__(output_dir)
        self.combined_index = CombinedIndex()
    
    def generate_random_nodes(self, count: int, dimension: int = 3) -> List[Node]:
        """Generate random nodes with both spatial and temporal coordinates.
        
        Args:
            count: Number of nodes to generate
            dimension: Dimensionality of the spatial coordinates
            
        Returns:
            List of random nodes
        """
        nodes = []
        for i in range(count):
            # Generate random spatial coordinates
            spatial_dimensions = tuple(random.uniform(-100, 100) for _ in range(dimension))
            
            # Generate a random timestamp within the past year
            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            # Create combined coordinates
            coords = Coordinates(
                spatial=SpatialCoordinate(dimensions=spatial_dimensions),
                temporal=TemporalCoordinate(timestamp=timestamp)
            )
            
            # Create the node
            node = Node(
                id=f"node_{i}",
                data={"value": random.random()},
                coordinates=coords
            )
            
            nodes.append(node)
        
        return nodes
    
    def benchmark_combined_queries(self, index_size: int = 10000) -> None:
        """Benchmark combined spatio-temporal queries.
        
        Args:
            index_size: Size of the index to use for testing
        """
        # Create and populate the index
        self.combined_index = CombinedIndex()
        nodes = self.generate_random_nodes(index_size)
        
        for node in nodes:
            self.combined_index.insert(node)
        
        # Define query types to benchmark
        query_types = [
            "spatial_only", 
            "temporal_only", 
            "combined_nearest",
            "combined_range"
        ]
        
        # Prepare common query parameters
        spatial_point = (random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50))
        temporal_point = datetime.now() - timedelta(days=random.randint(0, 365))
        
        range_size = 50
        lower_bounds = tuple(c - range_size/2 for c in spatial_point)
        upper_bounds = tuple(c + range_size/2 for c in spatial_point)
        
        time_range_days = 30
        start_time = temporal_point - timedelta(days=time_range_days/2)
        end_time = temporal_point + timedelta(days=time_range_days/2)
        
        # Define operations for each query type
        operations = {
            "spatial_only": lambda: self.combined_index.spatial_nearest(spatial_point, num_results=100),
            "temporal_only": lambda: self.combined_index.temporal_nearest(temporal_point, num_results=100),
            "combined_nearest": lambda: self.combined_index.combined_query(
                spatial_point=spatial_point, 
                temporal_point=temporal_point,
                num_results=100
            ),
            "combined_range": lambda: self.combined_index.combined_query(
                spatial_range=(lower_bounds, upper_bounds),
                temporal_range=(start_time, end_time)
            )
        }
        
        # Run benchmarks for each query type
        for name, operation in operations.items():
            self.benchmark_operation(name, operation, iterations=20)
        
        # Plot results
        self.plot_comparison("Combined Index Query Performance", query_types)
    
    def benchmark_dimensionality_impact(self, index_size: int = 5000) -> None:
        """Benchmark impact of dimensionality on performance.
        
        Args:
            index_size: Size of each index to test
        """
        dimensions = [2, 3, 4, 5, 6]
        insert_names = []
        query_names = []
        
        for dim in dimensions:
            # Create a fresh index with this dimensionality
            index = CombinedIndex(spatial_dimension=dim)
            
            # Generate nodes with appropriate dimensionality
            nodes = self.generate_random_nodes(index_size, dimension=dim)
            
            # Benchmark insertion
            insert_name = f"insert_dim_{dim}"
            insert_names.append(insert_name)
            
            def insert_operation():
                for node in nodes:
                    index.insert(node)
            
            self.benchmark_operation(insert_name, insert_operation, iterations=3)
            
            # Insert nodes for query benchmark
            for node in nodes:
                index.insert(node)
            
            # Benchmark query
            query_name = f"query_dim_{dim}"
            query_names.append(query_name)
            
            spatial_point = tuple(random.uniform(-50, 50) for _ in range(dim))
            
            def query_operation():
                index.spatial_nearest(spatial_point, num_results=100)
            
            self.benchmark_operation(query_name, query_operation, iterations=10)
        
        # Plot results
        plt.figure(figsize=(12, 6))
        
        insert_values = [self.results[name]["avg"] for name in insert_names]
        query_values = [self.results[name]["avg"] for name in query_names]
        
        plt.plot(dimensions, insert_values, 'b-o', linewidth=2, label="Insert")
        plt.plot(dimensions, query_values, 'r-o', linewidth=2, label="Query")
        
        plt.xlabel('Dimensions')
        plt.ylabel('Average Time (ms)')
        plt.title('Impact of Dimensionality on Performance')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(dimensions)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "dimensionality_impact.png"))
        plt.close()


def run_benchmarks():
    """Run all benchmarks and generate visualizations."""
    # Create output directory
    if not os.path.exists("benchmark_results"):
        os.makedirs("benchmark_results")
    
    print("Running Temporal Index Benchmarks...")
    temporal_benchmark = TemporalIndexBenchmark()
    temporal_benchmark.benchmark_insertions([100, 500, 1000, 5000, 10000])
    temporal_benchmark.benchmark_queries()
    
    print("Running Spatial Index Benchmarks...")
    spatial_benchmark = SpatialIndexBenchmark()
    spatial_benchmark.benchmark_insertions([100, 500, 1000, 5000, 10000])
    spatial_benchmark.benchmark_queries()
    
    print("Running Combined Index Benchmarks...")
    combined_benchmark = CombinedIndexBenchmark()
    combined_benchmark.benchmark_combined_queries()
    combined_benchmark.benchmark_dimensionality_impact()
    
    print("Benchmarks complete. Results saved to benchmark_results/")


if __name__ == "__main__":
    run_benchmarks() 
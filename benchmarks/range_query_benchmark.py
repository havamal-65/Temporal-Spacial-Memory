"""
Range Query Benchmark for the Temporal-Spatial Memory Database.

This benchmark focuses on testing range queries perform across different 
temporal and spatial ranges with varying dataset sizes and query complexities.
"""

import os
import time
import random
import statistics
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Tuple, Optional

# Import core components with error handling
try:
    from src.core.node import Node
    from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
    CORE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Core components not available: {e}")
    CORE_COMPONENTS_AVAILABLE = False

# Import index components with error handling
try:
    from src.indexing.rtree import SpatialIndex
    from src.indexing.temporal_index import TemporalIndex
    from src.indexing.combined_index import CombinedIndex
    INDEXING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Indexing components not available: {e}")
    INDEXING_AVAILABLE = False

class RangeQueryBenchmark:
    """Benchmark suite for testing range query performance."""
    
    def __init__(self, output_dir: str = "benchmark_results/range_queries"):
        """Initialize the range query benchmark suite.
        
        Args:
            output_dir: Directory to save benchmark results and visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
        
        # Create indexes if available
        if INDEXING_AVAILABLE:
            self.temporal_index = TemporalIndex()
            self.spatial_index = SpatialIndex()
            self.combined_index = CombinedIndex()
        else:
            self.temporal_index = None
            self.spatial_index = None
            self.combined_index = None
    
    def benchmark_operation(self, name: str, operation_func: Callable, 
                           iterations: int = 50, warmup: int = 5) -> Dict[str, float]:
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
            result = operation_func()
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
    
    def generate_random_temporal_nodes(self, count: int) -> List[Node]:
        """Generate random nodes with temporal coordinates.
        
        Args:
            count: Number of nodes to generate
            
        Returns:
            List of nodes with random temporal coordinates
        """
        if not CORE_COMPONENTS_AVAILABLE:
            print("Warning: Core components not available. Using mock nodes.")
            return [{"id": i, "timestamp": datetime.now() + timedelta(minutes=random.randint(-10000, 10000))} 
                    for i in range(count)]
            
        nodes = []
        base_time = datetime.now()
        
        for i in range(count):
            # Generate random timestamp between 1 year ago and 1 year from now
            time_offset = timedelta(minutes=random.randint(-525600, 525600))
            timestamp = base_time + time_offset
            
            # Create temporal coordinate
            coords = Coordinates()
            coords.add(TemporalCoordinate(timestamp))
            
            # Create node with random content
            node = Node(
                id=f"node_{i}",
                content={"value": random.random(), "name": f"Node {i}"},
                coordinates=coords
            )
            nodes.append(node)
            
        return nodes
    
    def generate_random_spatiotemporal_nodes(self, count: int) -> List[Node]:
        """Generate random nodes with both spatial and temporal coordinates.
        
        Args:
            count: Number of nodes to generate
            
        Returns:
            List of nodes with random spatiotemporal coordinates
        """
        if not CORE_COMPONENTS_AVAILABLE:
            print("Warning: Core components not available. Using mock nodes.")
            return [{"id": i, 
                     "timestamp": datetime.now() + timedelta(minutes=random.randint(-10000, 10000)),
                     "position": (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))} 
                    for i in range(count)]
            
        nodes = []
        base_time = datetime.now()
        
        for i in range(count):
            # Generate random timestamp between 1 year ago and 1 year from now
            time_offset = timedelta(minutes=random.randint(-525600, 525600))
            timestamp = base_time + time_offset
            
            # Generate random spatial position
            x = random.uniform(-100, 100)
            y = random.uniform(-100, 100)
            z = random.uniform(-100, 100)
            
            # Create coordinates
            coords = Coordinates()
            coords.add(TemporalCoordinate(timestamp))
            coords.add(SpatialCoordinate((x, y, z)))
            
            # Create node with random content
            node = Node(
                id=f"node_{i}",
                content={"value": random.random(), "name": f"Node {i}"},
                coordinates=coords
            )
            nodes.append(node)
            
        return nodes
    
    def benchmark_temporal_range_queries(self, node_counts: List[int], range_sizes: List[float]):
        """Benchmark temporal range queries with different data sizes and range sizes.
        
        Args:
            node_counts: List of node counts to test
            range_sizes: List of range sizes as percentage of total time range (0.0-1.0)
        """
        if not INDEXING_AVAILABLE:
            print("Warning: Indexing components not available. Skipping temporal range query benchmarks.")
            return
            
        print(f"Benchmarking temporal range queries...")
        
        # For each data size
        for node_count in node_counts:
            print(f"  Testing with {node_count} nodes...")
            
            # Generate nodes and populate index
            nodes = self.generate_random_temporal_nodes(node_count)
            self.temporal_index = TemporalIndex()
            
            # Get min and max time to establish our range
            min_time = datetime.now() - timedelta(days=365)
            max_time = datetime.now() + timedelta(days=365)
            time_range = (max_time - min_time).total_seconds()
            
            # Add nodes to index
            for node in nodes:
                if CORE_COMPONENTS_AVAILABLE:
                    # Get temporal coordinate
                    temp_coord = node.coordinates.get(TemporalCoordinate)
                    if temp_coord:
                        self.temporal_index.insert(node.id, temp_coord.value)
                else:
                    # Mock version
                    self.temporal_index.insert(node["id"], node["timestamp"])
            
            # Test each range size
            for range_size in range_sizes:
                operation_name = f"Temporal_Range_{node_count}nodes_{int(range_size*100)}pct"
                
                # Define query operation
                def query_operation():
                    # Random start point
                    start_offset = random.random() * (1.0 - range_size) * time_range
                    start_time = min_time + timedelta(seconds=start_offset)
                    end_time = start_time + timedelta(seconds=range_size * time_range)
                    
                    # Execute query
                    return self.temporal_index.range_query(start_time, end_time)
                
                # Benchmark the operation
                self.benchmark_operation(operation_name, query_operation)
        
        # Plot results for each node count
        for node_count in node_counts:
            operation_names = [f"Temporal_Range_{node_count}nodes_{int(size*100)}pct" for size in range_sizes]
            title = f"Temporal Range Query Performance ({node_count} nodes)"
            
            plt.figure(figsize=(10, 6))
            metrics = ["avg", "p95"]
            
            for metric in metrics:
                values = [self.results[name][metric] for name in operation_names]
                plt.plot([int(size*100) for size in range_sizes], values, 'o-', 
                         linewidth=2, label=f"{metric.upper()}")
            
            plt.xlabel('Range Size (% of total time range)')
            plt.ylabel('Time (ms)')
            plt.title(title)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            filename = f"temporal_range_query_{node_count}nodes.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
    
    def benchmark_combined_range_queries(self, node_counts: List[int], 
                                         temporal_range_sizes: List[float],
                                         spatial_range_sizes: List[float]):
        """Benchmark combined spatiotemporal range queries.
        
        Args:
            node_counts: List of node counts to test
            temporal_range_sizes: List of temporal range sizes (0.0-1.0)
            spatial_range_sizes: List of spatial range sizes (0.0-1.0)
        """
        if not INDEXING_AVAILABLE:
            print("Warning: Indexing components not available. Skipping combined range query benchmarks.")
            return
            
        print(f"Benchmarking combined spatiotemporal range queries...")
        
        # For each data size
        for node_count in node_counts:
            print(f"  Testing with {node_count} nodes...")
            
            # Generate nodes and populate index
            nodes = self.generate_random_spatiotemporal_nodes(node_count)
            self.combined_index = CombinedIndex()
            
            # Add nodes to index
            for node in nodes:
                if CORE_COMPONENTS_AVAILABLE:
                    # Get coordinates
                    temp_coord = node.coordinates.get(TemporalCoordinate)
                    spatial_coord = node.coordinates.get(SpatialCoordinate)
                    
                    if temp_coord and spatial_coord:
                        self.combined_index.insert(
                            node.id, 
                            temp_coord.value,
                            spatial_coord.value
                        )
                else:
                    # Mock version
                    self.combined_index.insert(
                        node["id"], 
                        node["timestamp"],
                        node["position"]
                    )
            
            # Test with default spatial range and varying temporal range
            for temporal_range in temporal_range_sizes:
                operation_name = f"Combined_T{int(temporal_range*100)}pct_S50pct_{node_count}nodes"
                
                # Define query operation
                def query_operation():
                    # Temporal range
                    min_time = datetime.now() - timedelta(days=365)
                    max_time = datetime.now() + timedelta(days=365)
                    time_range = (max_time - min_time).total_seconds()
                    
                    start_offset = random.random() * (1.0 - temporal_range) * time_range
                    start_time = min_time + timedelta(seconds=start_offset)
                    end_time = start_time + timedelta(seconds=temporal_range * time_range)
                    
                    # Spatial range (50% of space)
                    center = (0, 0, 0)
                    radius = 50  # Half of the 200x200x200 cube
                    
                    # Execute query
                    return self.combined_index.query(
                        temporal_range=(start_time, end_time),
                        spatial_range=(center, radius)
                    )
                
                # Benchmark the operation
                self.benchmark_operation(operation_name, query_operation)
            
            # Test with default temporal range and varying spatial range
            for spatial_range in spatial_range_sizes:
                operation_name = f"Combined_T50pct_S{int(spatial_range*100)}pct_{node_count}nodes"
                
                # Define query operation
                def query_operation():
                    # Temporal range (50% of time)
                    min_time = datetime.now() - timedelta(days=365)
                    max_time = datetime.now() + timedelta(days=365)
                    time_range = (max_time - min_time).total_seconds()
                    
                    start_offset = random.random() * 0.5 * time_range
                    start_time = min_time + timedelta(seconds=start_offset)
                    end_time = start_time + timedelta(seconds=0.5 * time_range)
                    
                    # Spatial range
                    center = (0, 0, 0)
                    radius = spatial_range * 100  # Percentage of the 200x200x200 cube
                    
                    # Execute query
                    return self.combined_index.query(
                        temporal_range=(start_time, end_time),
                        spatial_range=(center, radius)
                    )
                
                # Benchmark the operation
                self.benchmark_operation(operation_name, query_operation)
        
        # Plot the results
        # 1. Plot varying temporal range
        for node_count in node_counts:
            operation_names = [f"Combined_T{int(size*100)}pct_S50pct_{node_count}nodes" 
                              for size in temporal_range_sizes]
            title = f"Combined Query - Varying Temporal Range ({node_count} nodes)"
            
            plt.figure(figsize=(10, 6))
            metrics = ["avg", "p95"]
            
            for metric in metrics:
                values = [self.results[name][metric] for name in operation_names]
                plt.plot([int(size*100) for size in temporal_range_sizes], values, 'o-', 
                         linewidth=2, label=f"{metric.upper()}")
            
            plt.xlabel('Temporal Range Size (% of total time range)')
            plt.ylabel('Time (ms)')
            plt.title(title)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            filename = f"combined_query_temporal_{node_count}nodes.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
        
        # 2. Plot varying spatial range
        for node_count in node_counts:
            operation_names = [f"Combined_T50pct_S{int(size*100)}pct_{node_count}nodes" 
                              for size in spatial_range_sizes]
            title = f"Combined Query - Varying Spatial Range ({node_count} nodes)"
            
            plt.figure(figsize=(10, 6))
            metrics = ["avg", "p95"]
            
            for metric in metrics:
                values = [self.results[name][metric] for name in operation_names]
                plt.plot([int(size*100) for size in spatial_range_sizes], values, 'o-', 
                         linewidth=2, label=f"{metric.upper()}")
            
            plt.xlabel('Spatial Range Size (% of maximum radius)')
            plt.ylabel('Time (ms)')
            plt.title(title)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            filename = f"combined_query_spatial_{node_count}nodes.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
    
    def run_benchmarks(self):
        """Run all range query benchmarks."""
        if not INDEXING_AVAILABLE:
            print("Indexing components not available. Cannot run range query benchmarks.")
            return
            
        print("Starting range query benchmarks...")
        
        # Define test parameters
        node_counts = [1000, 10000, 100000]
        temporal_range_sizes = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0]
        spatial_range_sizes = [0.1, 0.25, 0.5, 0.75, 1.0]
        
        # Run the benchmarks
        self.benchmark_temporal_range_queries(node_counts, temporal_range_sizes)
        self.benchmark_combined_range_queries(node_counts, temporal_range_sizes, spatial_range_sizes)
        
        print(f"Range query benchmarks complete! Results saved to {self.output_dir}")


def run_benchmarks():
    """Run the range query benchmarks."""
    benchmark = RangeQueryBenchmark()
    benchmark.run_benchmarks()


if __name__ == "__main__":
    run_benchmarks() 
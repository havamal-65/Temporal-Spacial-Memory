"""
Memory Usage Benchmark for the Temporal-Spatial Memory Database.

This benchmark focuses on measuring memory usage across different database operations
and data sizes to help identify potential memory bottlenecks.
"""

import os
import time
import random
import gc
import statistics
import matplotlib.pyplot as plt
import numpy as np
import psutil
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

# Import storage components with error handling
try:
    from src.storage.node_store import InMemoryNodeStore
    from src.storage.rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RocksDB not available: {e}")
    ROCKSDB_AVAILABLE = False

class MemoryBenchmark:
    """Benchmark suite for measuring memory usage."""
    
    def __init__(self, output_dir: str = "benchmark_results/memory"):
        """Initialize the memory benchmark suite.
        
        Args:
            output_dir: Directory to save benchmark results and visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
        
        # Initialize the process for memory measurements
        self.process = psutil.Process(os.getpid())
    
    def measure_memory(self) -> float:
        """Measure current memory usage of the process.
        
        Returns:
            Memory usage in MB
        """
        # Force garbage collection to get more accurate measurements
        gc.collect()
        
        # Get memory info
        memory_info = self.process.memory_info()
        
        # Return memory in MB
        return memory_info.rss / (1024 * 1024)
    
    def benchmark_memory(self, operation_name: str, setup_func: Callable,
                         cleanup_func: Callable = None) -> Dict[str, float]:
        """Benchmark memory usage for an operation.
        
        Args:
            operation_name: Name of the operation
            setup_func: Function that performs the setup operation
            cleanup_func: Optional function to clean up after the operation
            
        Returns:
            Dictionary with memory usage before and after
        """
        print(f"Measuring memory for {operation_name}...")
        
        # Measure baseline memory usage
        baseline_memory = self.measure_memory()
        print(f"  Baseline memory: {baseline_memory:.2f} MB")
        
        # Run the setup operation
        start_time = time.time()
        result = setup_func()
        end_time = time.time()
        
        # Measure memory after operation
        after_memory = self.measure_memory()
        print(f"  Memory after operation: {after_memory:.2f} MB")
        
        # Calculate the difference
        memory_difference = after_memory - baseline_memory
        print(f"  Memory increase: {memory_difference:.2f} MB")
        
        # Store the results
        memory_metrics = {
            "baseline_memory_mb": baseline_memory,
            "after_memory_mb": after_memory,
            "memory_difference_mb": memory_difference,
            "operation_time_ms": (end_time - start_time) * 1000
        }
        
        self.results[operation_name] = memory_metrics
        
        # Run cleanup if provided
        if cleanup_func:
            cleanup_func(result)
            
            # Measure memory after cleanup
            cleanup_memory = self.measure_memory()
            print(f"  Memory after cleanup: {cleanup_memory:.2f} MB")
            
            # Update the results
            self.results[operation_name]["after_cleanup_mb"] = cleanup_memory
            self.results[operation_name]["cleanup_difference_mb"] = cleanup_memory - baseline_memory
        
        return memory_metrics
    
    def generate_random_nodes(self, count: int) -> List:
        """Generate random nodes for testing.
        
        Args:
            count: Number of nodes to generate
            
        Returns:
            List of nodes
        """
        if not CORE_COMPONENTS_AVAILABLE:
            print("Warning: Using simplified node structure for testing.")
            return [{"id": f"node_{i}", 
                     "timestamp": datetime.now() + timedelta(minutes=random.randint(-1000, 1000)),
                     "position": (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100)),
                     "value": random.random()} 
                    for i in range(count)]
        
        nodes = []
        for i in range(count):
            # Create temporal coordinate
            coords = Coordinates()
            coords.add(TemporalCoordinate(datetime.now() + timedelta(minutes=random.randint(-1000, 1000))))
            
            # Add spatial coordinate
            pos = (random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))
            coords.add(SpatialCoordinate(pos))
            
            # Create node
            node = Node(
                id=f"node_{i}",
                content={"value": random.random(), "name": f"Node {i}"},
                coordinates=coords
            )
            nodes.append(node)
            
        return nodes
    
    def benchmark_node_creation(self, sizes: List[int]):
        """Benchmark memory usage for node creation with different sizes.
        
        Args:
            sizes: List of node counts to test
        """
        print("Benchmarking node creation memory usage...")
        
        for size in sizes:
            operation_name = f"Node_Creation_{size}"
            
            def create_nodes():
                return self.generate_random_nodes(size)
            
            def cleanup_nodes(nodes):
                # Help the garbage collector
                for i in range(len(nodes)):
                    nodes[i] = None
                
            self.benchmark_memory(operation_name, create_nodes, cleanup_nodes)
    
    def benchmark_in_memory_store(self, sizes: List[int]):
        """Benchmark memory usage for in-memory storage with different data sizes.
        
        Args:
            sizes: List of node counts to test
        """
        print("Benchmarking in-memory store memory usage...")
        
        for size in sizes:
            operation_name = f"InMemory_Storage_{size}"
            
            def setup_store():
                store = InMemoryNodeStore()
                nodes = self.generate_random_nodes(size)
                
                # Add nodes to store
                for node in nodes:
                    if CORE_COMPONENTS_AVAILABLE:
                        store.put(node.id, node)
                    else:
                        store.put(node["id"], node)
                
                return store, nodes
            
            def cleanup_store(result):
                store, nodes = result
                
                # Help the garbage collector
                for i in range(len(nodes)):
                    nodes[i] = None
                
                # Clear the store
                store = None
            
            self.benchmark_memory(operation_name, setup_store, cleanup_store)
    
    def benchmark_temporal_index(self, sizes: List[int]):
        """Benchmark memory usage for temporal index with different data sizes.
        
        Args:
            sizes: List of node counts to test
        """
        if not INDEXING_AVAILABLE:
            print("Warning: Indexing components not available. Skipping temporal index benchmark.")
            return
            
        print("Benchmarking temporal index memory usage...")
        
        for size in sizes:
            operation_name = f"Temporal_Index_{size}"
            
            def setup_index():
                index = TemporalIndex()
                nodes = self.generate_random_nodes(size)
                
                # Add nodes to index
                for node in nodes:
                    if CORE_COMPONENTS_AVAILABLE:
                        # Get temporal coordinate
                        temp_coord = node.coordinates.get(TemporalCoordinate)
                        if temp_coord:
                            index.insert(node.id, temp_coord.value)
                    else:
                        # Mock version
                        index.insert(node["id"], node["timestamp"])
                
                return index, nodes
            
            def cleanup_index(result):
                index, nodes = result
                
                # Help the garbage collector
                for i in range(len(nodes)):
                    nodes[i] = None
                
                # Clear the index
                index = None
            
            self.benchmark_memory(operation_name, setup_index, cleanup_index)
    
    def benchmark_combined_index(self, sizes: List[int]):
        """Benchmark memory usage for combined index with different data sizes.
        
        Args:
            sizes: List of node counts to test
        """
        if not INDEXING_AVAILABLE:
            print("Warning: Indexing components not available. Skipping combined index benchmark.")
            return
            
        print("Benchmarking combined index memory usage...")
        
        for size in sizes:
            operation_name = f"Combined_Index_{size}"
            
            def setup_index():
                index = CombinedIndex()
                nodes = self.generate_random_nodes(size)
                
                # Add nodes to index
                for node in nodes:
                    if CORE_COMPONENTS_AVAILABLE:
                        # Get coordinates
                        temp_coord = node.coordinates.get(TemporalCoordinate)
                        spatial_coord = node.coordinates.get(SpatialCoordinate)
                        
                        if temp_coord and spatial_coord:
                            index.insert(
                                node.id, 
                                temp_coord.value,
                                spatial_coord.value
                            )
                    else:
                        # Mock version
                        index.insert(
                            node["id"], 
                            node["timestamp"],
                            node["position"]
                        )
                
                return index, nodes
            
            def cleanup_index(result):
                index, nodes = result
                
                # Help the garbage collector
                for i in range(len(nodes)):
                    nodes[i] = None
                
                # Clear the index
                index = None
            
            self.benchmark_memory(operation_name, setup_index, cleanup_index)
    
    def benchmark_rocksdb_store(self, sizes: List[int]):
        """Benchmark memory usage for RocksDB storage with different data sizes.
        
        Args:
            sizes: List of node counts to test
        """
        if not ROCKSDB_AVAILABLE:
            print("Warning: RocksDB not available. Skipping RocksDB memory benchmark.")
            return
            
        print("Benchmarking RocksDB store memory usage...")
        
        # Create a temporary directory for RocksDB
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            for size in sizes:
                operation_name = f"RocksDB_Storage_{size}"
                
                def setup_store():
                    # Create a store with temporary directory
                    store = RocksDBNodeStore(temp_dir)
                    nodes = self.generate_random_nodes(size)
                    
                    # Add nodes to store
                    for node in nodes:
                        if CORE_COMPONENTS_AVAILABLE:
                            store.put(node.id, node)
                        else:
                            store.put(node["id"], node)
                    
                    return store, nodes
                
                def cleanup_store(result):
                    store, nodes = result
                    
                    # Close the store
                    if hasattr(store, 'close'):
                        store.close()
                    
                    # Help the garbage collector
                    for i in range(len(nodes)):
                        nodes[i] = None
                    
                    # Clear the store
                    store = None
                
                self.benchmark_memory(operation_name, setup_store, cleanup_store)
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
    
    def plot_memory_comparison(self, component_type: str, sizes: List[int]):
        """Plot memory usage comparison for a component type.
        
        Args:
            component_type: Type of component to plot (e.g., "Node_Creation", "InMemory_Storage")
            sizes: List of data sizes that were tested
        """
        operation_names = [f"{component_type}_{size}" for size in sizes]
        
        # Check if all operations exist in results
        if not all(name in self.results for name in operation_names):
            print(f"Warning: Not all operations found for {component_type}. Skipping plot.")
            return
        
        # Extract memory differences
        memory_usage = [self.results[name]["memory_difference_mb"] for name in operation_names]
        
        # Plot memory usage vs. data size
        plt.figure(figsize=(10, 6))
        plt.plot(sizes, memory_usage, 'o-', linewidth=2)
        plt.xlabel('Data Size (number of nodes)')
        plt.ylabel('Memory Usage (MB)')
        plt.title(f'Memory Usage for {component_type}')
        plt.grid(True, alpha=0.3)
        
        # Add logarithmic trendline
        if min(memory_usage) > 0:  # Avoid log of zero or negative values
            try:
                coeffs = np.polyfit(np.log(sizes), np.log(memory_usage), 1)
                polynomial = np.poly1d(coeffs)
                plt.plot(sizes, np.exp(polynomial(np.log(sizes))), 'r--', 
                        label=f'Trendline: O(n^{coeffs[0]:.2f})')
                plt.legend()
            except:
                print(f"Warning: Could not calculate trendline for {component_type}")
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"{component_type.lower()}_memory_usage.png"))
        plt.close()
    
    def plot_component_comparison(self, sizes: List[int]):
        """Plot memory usage comparison between different components.
        
        Args:
            sizes: List of data sizes that were tested
        """
        # Define the components to compare
        components = []
        
        # Add components that are available
        if any(f"Node_Creation_{size}" in self.results for size in sizes):
            components.append("Node_Creation")
        
        if any(f"InMemory_Storage_{size}" in self.results for size in sizes):
            components.append("InMemory_Storage")
        
        if any(f"Temporal_Index_{size}" in self.results for size in sizes):
            components.append("Temporal_Index")
        
        if any(f"Combined_Index_{size}" in self.results for size in sizes):
            components.append("Combined_Index")
        
        if any(f"RocksDB_Storage_{size}" in self.results for size in sizes):
            components.append("RocksDB_Storage")
        
        if not components:
            print("Warning: No components to compare. Skipping comparison plot.")
            return
        
        # For each data size, create a comparison plot
        for size in sizes:
            component_data = []
            component_labels = []
            
            for component in components:
                operation_name = f"{component}_{size}"
                if operation_name in self.results:
                    component_data.append(self.results[operation_name]["memory_difference_mb"])
                    component_labels.append(component.replace("_", " "))
            
            if not component_data:
                print(f"Warning: No data for size {size}. Skipping comparison plot.")
                continue
            
            # Plot bar chart comparing components
            plt.figure(figsize=(12, 7))
            plt.bar(component_labels, component_data)
            plt.xlabel('Component')
            plt.ylabel('Memory Usage (MB)')
            plt.title(f'Memory Usage Comparison ({size} nodes)')
            plt.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            
            plt.savefig(os.path.join(self.output_dir, f"component_comparison_{size}.png"))
            plt.close()
    
    def run_benchmarks(self):
        """Run all memory usage benchmarks."""
        print("Starting memory usage benchmarks...")
        
        # Define test parameters - be careful with large sizes as they consume memory
        sizes = [100, 1000, 10000, 100000]
        
        # Run the benchmarks
        self.benchmark_node_creation(sizes)
        self.benchmark_in_memory_store(sizes)
        self.benchmark_temporal_index(sizes)
        self.benchmark_combined_index(sizes)
        self.benchmark_rocksdb_store(sizes)
        
        # Generate plots
        for component in ["Node_Creation", "InMemory_Storage", "Temporal_Index", "Combined_Index", "RocksDB_Storage"]:
            self.plot_memory_comparison(component, sizes)
        
        # Generate comparison plots
        self.plot_component_comparison(sizes)
        
        print(f"Memory usage benchmarks complete! Results saved to {self.output_dir}")


def run_benchmarks():
    """Run the memory usage benchmarks."""
    benchmark = MemoryBenchmark()
    benchmark.run_benchmarks()


if __name__ == "__main__":
    run_benchmarks() 
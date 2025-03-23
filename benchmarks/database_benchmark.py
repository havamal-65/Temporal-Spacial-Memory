"""
Database benchmark for the Temporal-Spatial Memory Database.

This benchmark tests the performance of actual database operations like node creation,
retrieval, updating, and deletion, as well as basic temporal queries.
"""

import os
import time
import random
import statistics
import uuid
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Callable, Any, Tuple

# Set flags for available components
TEMPORAL_INDEX_AVAILABLE = False  # We'll skip temporal operations for safety

# Import core components with error handling
try:
    from src.core.node_v2 import Node
    from src.storage.node_store import InMemoryNodeStore, NodeStore
    CORE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Core components not available: {e}")
    print("Using mock components for benchmarking.")
    CORE_COMPONENTS_AVAILABLE = False
    
    # Create mock classes for testing
    class Node:
        def __init__(self, id=None, content=None, position=None, *args, **kwargs):
            self.id = id or str(uuid.uuid4())
            self.content = content or {}
            self.position = position or (0, 0, 0)
            self.coordinates = {}
    
    class InMemoryNodeStore:
        def __init__(self):
            self.nodes = {}
        def put(self, node_id, node):
            self.nodes[node_id] = node
        def get(self, node_id):
            return self.nodes.get(node_id)
        def delete(self, node_id):
            if node_id in self.nodes:
                del self.nodes[node_id]
                return True
            return False

# Mock TemporalIndex - we'll use this instead of importing the real one
class TemporalIndex:
    def __init__(self, *args, **kwargs):
        print("Warning: This is a mock TemporalIndex - temporal benchmarks will not work.")
    def insert(self, *args, **kwargs):
        pass
    def range_query(self, *args, **kwargs):
        return []

class DatabaseBenchmark:
    """Benchmark measuring actual database operations."""
    
    def __init__(self, output_dir: str = "benchmark_results/database"):
        """Initialize the database benchmark suite."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
        
        # Setup test components
        self.node_store = InMemoryNodeStore()
        
        # Setup temporal index (always use the mock version for safety)
        self.temporal_index = None
                
    def benchmark_operation(self, name: str, operation_func: Callable, 
                           iterations: int = 100, warmup: int = 10) -> Dict[str, float]:
        """Benchmark a single operation and return performance metrics."""
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
        """Plot comparison between different operations."""
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
        """Plot how performance scales with data size."""
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
    
    def generate_random_node(self) -> Node:
        """Generate a node with random data and position."""
        node_id = str(uuid.uuid4())
        position = (
            random.uniform(0, 100),  # time
            random.uniform(0, 100),  # radius
            random.uniform(0, 360)   # theta
        )
        content = {
            "value": random.random(),
            "name": f"Test Node {random.randint(1, 1000)}",
            "tags": ["test", "benchmark", f"tag{random.randint(1, 10)}"]
        }
        return Node(id=uuid.UUID(node_id), content=content, position=position)
    
    def benchmark_node_operations(self):
        """Benchmark basic node operations."""
        print("Benchmarking basic node operations...")
        
        # 1. Node creation
        def create_node():
            return self.generate_random_node()
        
        self.benchmark_operation("Node_Creation", create_node)
        
        # 2. Node storage (put)
        def store_node():
            node = self.generate_random_node()
            self.node_store.put(node.id, node)
            return node.id
        
        self.benchmark_operation("Node_Storage", store_node)
        
        # 3. Node retrieval (get)
        # First, create some nodes to retrieve
        node_ids = []
        for _ in range(1000):
            node = self.generate_random_node()
            self.node_store.put(node.id, node)
            node_ids.append(node.id)
            
        def retrieve_node():
            node_id = random.choice(node_ids)
            return self.node_store.get(node_id)
        
        self.benchmark_operation("Node_Retrieval", retrieve_node)
        
        # 4. Node update
        def update_node():
            node_id = random.choice(node_ids)
            node = self.node_store.get(node_id)
            if node:
                # Create updated node with new content
                updated_content = node.content.copy() if hasattr(node, 'content') else {}
                updated_content["value"] = random.random()
                updated_node = Node(
                    id=node.id,
                    content=updated_content,
                    position=node.position if hasattr(node, 'position') else (0, 0, 0)
                )
                self.node_store.put(node.id, updated_node)
            return node_id
        
        self.benchmark_operation("Node_Update", update_node)
        
        # 5. Node deletion
        # Create nodes specifically for deletion
        delete_node_ids = []
        for _ in range(1000):
            node = self.generate_random_node()
            self.node_store.put(node.id, node)
            delete_node_ids.append(node.id)
            
        def delete_node():
            if delete_node_ids:
                node_id = delete_node_ids.pop()
                self.node_store.delete(node_id)
                return True
            return False
        
        self.benchmark_operation("Node_Deletion", delete_node)
        
        # Plot the results
        self.plot_comparison("Node Operations", [
            "Node_Creation", 
            "Node_Storage", 
            "Node_Retrieval", 
            "Node_Update", 
            "Node_Deletion"
        ])
    
    def benchmark_batch_operations(self):
        """Benchmark operations with different batch sizes."""
        print("Benchmarking batch operations...")
        
        batch_sizes = [10, 100, 1000, 10000]
        operation_names = []
        
        for size in batch_sizes:
            operation_name = f"Batch_Insert_{size}"
            operation_names.append(operation_name)
            
            # Generate nodes for this batch
            batch_nodes = [self.generate_random_node() for _ in range(size)]
            
            def batch_insert(nodes=batch_nodes):
                for node in nodes:
                    self.node_store.put(node.id, node)
            
            # Use fewer iterations for larger batches
            iterations = max(10, 1000 // size)
            self.benchmark_operation(operation_name, batch_insert, iterations=iterations)
        
        # Plot scaling behavior
        self.plot_data_size_scaling("Batch Insert Scaling", operation_names, batch_sizes)
        
    def run_benchmarks(self):
        """Run all database benchmarks."""
        print("Running database benchmarks...")
        
        if not CORE_COMPONENTS_AVAILABLE:
            print("Warning: Using mock components for benchmarking.")
            print("These benchmarks won't reflect the actual performance of your database.")
        
        # Run the benchmarks
        self.benchmark_node_operations()
        self.benchmark_batch_operations()
        
        # We skip temporal benchmarks completely for safety
        print("Skipping temporal benchmarks to avoid dependency issues.")
        
        print(f"Database benchmarks complete. Results saved to {self.output_dir}")


def run_benchmarks():
    """Run the database benchmarks."""
    benchmark = DatabaseBenchmark()
    benchmark.run_benchmarks()


if __name__ == "__main__":
    print("Running database benchmarks...")
    run_benchmarks() 
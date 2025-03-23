"""
Concurrent Operations Benchmark for the Temporal-Spatial Memory Database.

This benchmark tests how the database performs under concurrent operations,
including mixed read/write workloads with varying levels of concurrency.
"""

import os
import time
import random
import statistics
import concurrent.futures
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

# Import index and storage components with error handling
try:
    from src.storage.node_store import InMemoryNodeStore
    from src.indexing.temporal_index import TemporalIndex
    from src.indexing.combined_index import CombinedIndex
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Required components not available: {e}")
    COMPONENTS_AVAILABLE = False
    
    # Simple mock classes for testing
    class InMemoryNodeStore:
        def __init__(self):
            self.nodes = {}
            self._lock = __import__('threading').Lock()
            
        def put(self, node_id, node):
            with self._lock:
                self.nodes[node_id] = node
                
        def get(self, node_id):
            with self._lock:
                return self.nodes.get(node_id)
                
        def delete(self, node_id):
            with self._lock:
                if node_id in self.nodes:
                    del self.nodes[node_id]
                    return True
                return False

class ConcurrentBenchmark:
    """Benchmark for testing database operations under concurrent load."""
    
    def __init__(self, output_dir: str = "benchmark_results/concurrent"):
        """Initialize the concurrent benchmark suite.
        
        Args:
            output_dir: Directory to save benchmark results and visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}
        
        # Create node store for testing
        self.node_store = InMemoryNodeStore()
        
        # Create test data
        self.test_nodes = self._create_test_data(10000)
    
    def _create_test_data(self, count: int) -> Dict:
        """Create test data for benchmarking.
        
        Args:
            count: Number of nodes to create
            
        Returns:
            Dictionary mapping node IDs to nodes
        """
        print(f"Creating {count} test nodes...")
        nodes = {}
        
        for i in range(count):
            if CORE_COMPONENTS_AVAILABLE:
                # Create a proper Node object
                coords = Coordinates()
                coords.add(TemporalCoordinate(datetime.now() + timedelta(minutes=random.randint(-1000, 1000))))
                
                node = Node(
                    id=f"node_{i}",
                    content={"value": random.random(), "name": f"Node {i}"},
                    coordinates=coords
                )
                
                # Add to both dictionary and node store
                nodes[node.id] = node
                self.node_store.put(node.id, node)
            else:
                # Create a simple mock node
                node = {
                    "id": f"node_{i}",
                    "value": random.random(),
                    "name": f"Node {i}",
                    "timestamp": datetime.now() + timedelta(minutes=random.randint(-1000, 1000))
                }
                
                # Add to both dictionary and node store
                nodes[node["id"]] = node
                self.node_store.put(node["id"], node)
        
        return nodes
    
    def benchmark_concurrent_reads(self, concurrency_levels: List[int], 
                                   operations_per_thread: int = 100) -> Dict[str, List[float]]:
        """Benchmark concurrent read operations with varying concurrency.
        
        Args:
            concurrency_levels: List of concurrency levels to test
            operations_per_thread: Number of operations each thread should perform
            
        Returns:
            Dictionary with benchmark results
        """
        print("Benchmarking concurrent reads...")
        
        # Get all node IDs to randomly select from
        node_ids = list(self.test_nodes.keys())
        
        # Function for each worker thread to perform reads
        def worker_task():
            results = []
            for _ in range(operations_per_thread):
                # Pick a random node ID
                node_id = random.choice(node_ids)
                
                # Measure time to retrieve the node
                start = time.time()
                node = self.node_store.get(node_id)
                end = time.time()
                
                # Record time in milliseconds
                results.append((end - start) * 1000)
            
            return results
        
        # Test each concurrency level
        results = {}
        latencies = []
        throughputs = []
        
        for num_threads in concurrency_levels:
            operation_name = f"Read_Concurrency_{num_threads}"
            
            # Run the test with the current concurrency level
            start_time = time.time()
            all_latencies = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                future_to_worker = {executor.submit(worker_task): i for i in range(num_threads)}
                
                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_id = future_to_worker[future]
                    try:
                        latencies_for_thread = future.result()
                        all_latencies.extend(latencies_for_thread)
                    except Exception as e:
                        print(f"Worker {worker_id} generated an exception: {e}")
            
            end_time = time.time()
            
            # Calculate total throughput (operations per second)
            total_time = end_time - start_time
            total_ops = num_threads * operations_per_thread
            throughput = total_ops / total_time if total_time > 0 else 0
            
            # Calculate latency statistics
            latency_metrics = {
                "min": min(all_latencies),
                "max": max(all_latencies),
                "avg": statistics.mean(all_latencies),
                "median": statistics.median(all_latencies),
                "p95": statistics.quantile(all_latencies, 0.95),
                "p99": statistics.quantile(all_latencies, 0.99),
                "stddev": statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
            }
            
            # Store results
            self.results[operation_name] = {**latency_metrics, "throughput": throughput}
            
            # Keep track for plotting
            latencies.append(latency_metrics["avg"])
            throughputs.append(throughput)
            
            print(f"  Concurrency level {num_threads}: {throughput:.2f} ops/sec, " 
                  f"avg latency {latency_metrics['avg']:.2f} ms")
        
        # Plot the results
        plt.figure(figsize=(10, 6))
        
        # Create two y-axes
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        # Plot latency on left y-axis
        ax1.plot(concurrency_levels, latencies, 'b-o', linewidth=2, label='Avg Latency')
        ax1.set_xlabel('Concurrency Level (threads)')
        ax1.set_ylabel('Average Latency (ms)', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Plot throughput on right y-axis
        ax2.plot(concurrency_levels, throughputs, 'r-o', linewidth=2, label='Throughput')
        ax2.set_ylabel('Throughput (ops/sec)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        plt.title('Concurrent Read Performance')
        plt.grid(True, alpha=0.3)
        
        # Add legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "concurrent_read_performance.png"))
        plt.close()
        
        return self.results
    
    def benchmark_concurrent_writes(self, concurrency_levels: List[int], 
                                    operations_per_thread: int = 100) -> Dict[str, List[float]]:
        """Benchmark concurrent write operations with varying concurrency.
        
        Args:
            concurrency_levels: List of concurrency levels to test
            operations_per_thread: Number of operations each thread should perform
            
        Returns:
            Dictionary with benchmark results
        """
        print("Benchmarking concurrent writes...")
        
        # Function for each worker thread to perform writes
        def worker_task():
            results = []
            
            for i in range(operations_per_thread):
                # Create a new node with random data
                if CORE_COMPONENTS_AVAILABLE:
                    # Create a proper Node object with unique ID
                    thread_id = __import__('threading').current_thread().ident
                    node_id = f"node_conc_{thread_id}_{i}"
                    
                    coords = Coordinates()
                    coords.add(TemporalCoordinate(datetime.now() + timedelta(minutes=random.randint(-1000, 1000))))
                    
                    node = Node(
                        id=node_id,
                        content={"value": random.random(), "name": f"Concurrent Node {i}"},
                        coordinates=coords
                    )
                    
                    # Measure time to store the node
                    start = time.time()
                    self.node_store.put(node_id, node)
                    end = time.time()
                    
                else:
                    # Create a simple mock node with unique ID
                    thread_id = __import__('threading').current_thread().ident
                    node_id = f"node_conc_{thread_id}_{i}"
                    
                    node = {
                        "id": node_id,
                        "value": random.random(),
                        "name": f"Concurrent Node {i}",
                        "timestamp": datetime.now() + timedelta(minutes=random.randint(-1000, 1000))
                    }
                    
                    # Measure time to store the node
                    start = time.time()
                    self.node_store.put(node_id, node)
                    end = time.time()
                
                # Record time in milliseconds
                results.append((end - start) * 1000)
            
            return results
        
        # Test each concurrency level
        results = {}
        latencies = []
        throughputs = []
        
        for num_threads in concurrency_levels:
            operation_name = f"Write_Concurrency_{num_threads}"
            
            # Run the test with the current concurrency level
            start_time = time.time()
            all_latencies = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                future_to_worker = {executor.submit(worker_task): i for i in range(num_threads)}
                
                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_id = future_to_worker[future]
                    try:
                        latencies_for_thread = future.result()
                        all_latencies.extend(latencies_for_thread)
                    except Exception as e:
                        print(f"Worker {worker_id} generated an exception: {e}")
            
            end_time = time.time()
            
            # Calculate total throughput (operations per second)
            total_time = end_time - start_time
            total_ops = num_threads * operations_per_thread
            throughput = total_ops / total_time if total_time > 0 else 0
            
            # Calculate latency statistics
            latency_metrics = {
                "min": min(all_latencies),
                "max": max(all_latencies),
                "avg": statistics.mean(all_latencies),
                "median": statistics.median(all_latencies),
                "p95": statistics.quantile(all_latencies, 0.95),
                "p99": statistics.quantile(all_latencies, 0.99),
                "stddev": statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
            }
            
            # Store results
            self.results[operation_name] = {**latency_metrics, "throughput": throughput}
            
            # Keep track for plotting
            latencies.append(latency_metrics["avg"])
            throughputs.append(throughput)
            
            print(f"  Concurrency level {num_threads}: {throughput:.2f} ops/sec, " 
                  f"avg latency {latency_metrics['avg']:.2f} ms")
        
        # Plot the results
        plt.figure(figsize=(10, 6))
        
        # Create two y-axes
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        # Plot latency on left y-axis
        ax1.plot(concurrency_levels, latencies, 'b-o', linewidth=2, label='Avg Latency')
        ax1.set_xlabel('Concurrency Level (threads)')
        ax1.set_ylabel('Average Latency (ms)', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Plot throughput on right y-axis
        ax2.plot(concurrency_levels, throughputs, 'r-o', linewidth=2, label='Throughput')
        ax2.set_ylabel('Throughput (ops/sec)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        plt.title('Concurrent Write Performance')
        plt.grid(True, alpha=0.3)
        
        # Add legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "concurrent_write_performance.png"))
        plt.close()
        
        return self.results
    
    def benchmark_mixed_workload(self, concurrency_levels: List[int], 
                                read_write_ratios: List[float] = [0.2, 0.5, 0.8],
                                operations_per_thread: int = 100) -> Dict[str, List[float]]:
        """Benchmark mixed read/write workloads with varying concurrency and read/write ratios.
        
        Args:
            concurrency_levels: List of concurrency levels to test
            read_write_ratios: List of read/write ratios to test (ratio of reads to total operations)
            operations_per_thread: Number of operations each thread should perform
            
        Returns:
            Dictionary with benchmark results
        """
        print("Benchmarking mixed read/write workloads...")
        
        # Get all node IDs for read operations
        node_ids = list(self.test_nodes.keys())
        
        # Function for each worker thread to perform a mix of reads and writes
        def worker_task(read_ratio):
            results = {"read": [], "write": []}
            
            for i in range(operations_per_thread):
                # Determine if this operation should be a read or write
                is_read = random.random() < read_ratio
                
                if is_read:
                    # Read operation
                    node_id = random.choice(node_ids)
                    
                    start = time.time()
                    node = self.node_store.get(node_id)
                    end = time.time()
                    
                    results["read"].append((end - start) * 1000)
                else:
                    # Write operation
                    thread_id = __import__('threading').current_thread().ident
                    node_id = f"node_mixed_{thread_id}_{i}"
                    
                    if CORE_COMPONENTS_AVAILABLE:
                        coords = Coordinates()
                        coords.add(TemporalCoordinate(datetime.now() + timedelta(minutes=random.randint(-1000, 1000))))
                        
                        node = Node(
                            id=node_id,
                            content={"value": random.random(), "name": f"Mixed Node {i}"},
                            coordinates=coords
                        )
                    else:
                        node = {
                            "id": node_id,
                            "value": random.random(),
                            "name": f"Mixed Node {i}",
                            "timestamp": datetime.now() + timedelta(minutes=random.randint(-1000, 1000))
                        }
                    
                    start = time.time()
                    self.node_store.put(node_id, node)
                    end = time.time()
                    
                    results["write"].append((end - start) * 1000)
            
            return results
        
        # Test each combination of concurrency level and read/write ratio
        throughputs_by_ratio = {ratio: [] for ratio in read_write_ratios}
        
        for ratio in read_write_ratios:
            for num_threads in concurrency_levels:
                operation_name = f"Mixed_Ratio{int(ratio*100)}_Concurrency_{num_threads}"
                
                # Run the test with the current parameters
                start_time = time.time()
                all_read_latencies = []
                all_write_latencies = []
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                    future_to_worker = {executor.submit(worker_task, ratio): i for i in range(num_threads)}
                    
                    for future in concurrent.futures.as_completed(future_to_worker):
                        worker_id = future_to_worker[future]
                        try:
                            results_for_thread = future.result()
                            all_read_latencies.extend(results_for_thread["read"])
                            all_write_latencies.extend(results_for_thread["write"])
                        except Exception as e:
                            print(f"Worker {worker_id} generated an exception: {e}")
                
                end_time = time.time()
                
                # Calculate total throughput (operations per second)
                total_time = end_time - start_time
                total_ops = num_threads * operations_per_thread
                throughput = total_ops / total_time if total_time > 0 else 0
                
                # Calculate latency statistics for reads
                if all_read_latencies:
                    read_latency_metrics = {
                        "read_min": min(all_read_latencies),
                        "read_max": max(all_read_latencies),
                        "read_avg": statistics.mean(all_read_latencies),
                        "read_median": statistics.median(all_read_latencies),
                        "read_p95": statistics.quantile(all_read_latencies, 0.95),
                        "read_p99": statistics.quantile(all_read_latencies, 0.99),
                        "read_stddev": statistics.stdev(all_read_latencies) if len(all_read_latencies) > 1 else 0
                    }
                else:
                    read_latency_metrics = {
                        "read_min": 0, "read_max": 0, "read_avg": 0, "read_median": 0,
                        "read_p95": 0, "read_p99": 0, "read_stddev": 0
                    }
                
                # Calculate latency statistics for writes
                if all_write_latencies:
                    write_latency_metrics = {
                        "write_min": min(all_write_latencies),
                        "write_max": max(all_write_latencies),
                        "write_avg": statistics.mean(all_write_latencies),
                        "write_median": statistics.median(all_write_latencies),
                        "write_p95": statistics.quantile(all_write_latencies, 0.95),
                        "write_p99": statistics.quantile(all_write_latencies, 0.99),
                        "write_stddev": statistics.stdev(all_write_latencies) if len(all_write_latencies) > 1 else 0
                    }
                else:
                    write_latency_metrics = {
                        "write_min": 0, "write_max": 0, "write_avg": 0, "write_median": 0,
                        "write_p95": 0, "write_p99": 0, "write_stddev": 0
                    }
                
                # Store results
                self.results[operation_name] = {
                    **read_latency_metrics, 
                    **write_latency_metrics, 
                    "throughput": throughput
                }
                
                # Keep track for plotting
                throughputs_by_ratio[ratio].append(throughput)
                
                print(f"  Ratio {ratio:.1f} Concurrency {num_threads}: {throughput:.2f} ops/sec, " 
                      f"read latency {read_latency_metrics['read_avg']:.2f} ms, "
                      f"write latency {write_latency_metrics['write_avg']:.2f} ms")
        
        # Plot the results
        plt.figure(figsize=(12, 8))
        
        for ratio in read_write_ratios:
            plt.plot(concurrency_levels, throughputs_by_ratio[ratio], 'o-', 
                     linewidth=2, label=f"Read Ratio {ratio:.1f}")
        
        plt.xlabel('Concurrency Level (threads)')
        plt.ylabel('Throughput (ops/sec)')
        plt.title('Mixed Workload Performance')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.output_dir, "mixed_workload_performance.png"))
        plt.close()
        
        # Also plot latency comparison for each ratio
        for ratio in read_write_ratios:
            plt.figure(figsize=(10, 6))
            
            read_latencies = []
            write_latencies = []
            
            for num_threads in concurrency_levels:
                operation_name = f"Mixed_Ratio{int(ratio*100)}_Concurrency_{num_threads}"
                read_latencies.append(self.results[operation_name]["read_avg"])
                write_latencies.append(self.results[operation_name]["write_avg"])
            
            plt.plot(concurrency_levels, read_latencies, 'b-o', linewidth=2, label='Read Latency')
            plt.plot(concurrency_levels, write_latencies, 'r-o', linewidth=2, label='Write Latency')
            
            plt.xlabel('Concurrency Level (threads)')
            plt.ylabel('Average Latency (ms)')
            plt.title(f'Latency Comparison - Read Ratio {ratio:.1f}')
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            plt.savefig(os.path.join(self.output_dir, f"latency_comparison_ratio{int(ratio*100)}.png"))
            plt.close()
        
        return self.results
    
    def run_benchmarks(self):
        """Run all concurrent operation benchmarks."""
        print("Starting concurrent operation benchmarks...")
        
        # Define test parameters
        concurrency_levels = [1, 2, 4, 8, 16, 32]
        read_write_ratios = [0.2, 0.5, 0.8]
        operations_per_thread = 100
        
        # Run the benchmarks
        self.benchmark_concurrent_reads(concurrency_levels, operations_per_thread)
        self.benchmark_concurrent_writes(concurrency_levels, operations_per_thread)
        self.benchmark_mixed_workload(concurrency_levels, read_write_ratios, operations_per_thread)
        
        print(f"Concurrent operation benchmarks complete! Results saved to {self.output_dir}")


def run_benchmarks():
    """Run the concurrent operation benchmarks."""
    benchmark = ConcurrentBenchmark()
    benchmark.run_benchmarks()


if __name__ == "__main__":
    run_benchmarks() 
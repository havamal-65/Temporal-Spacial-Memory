"""
Performance benchmarks for the Temporal-Spatial Knowledge Database.

This module measures performance metrics for various operations.
"""

import time
import math
import tempfile
import shutil
import os
import json
import pandas as pd
from typing import Dict, List, Any

from tests.integration.test_environment import TestEnvironment
from tests.integration.test_data_generator import TestDataGenerator
from src.core.coordinates import SpatioTemporalCoordinate


class BasicOperationBenchmark:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        """
        Initialize benchmark
        
        Args:
            env: Test environment
            generator: Test data generator
        """
        self.env = env
        self.generator = generator
        
    def benchmark_node_insertion(self, node_count: int = 10000):
        """Benchmark node insertion performance"""
        # Generate nodes
        nodes = [self.generator.generate_node() for _ in range(node_count)]
        
        # Measure insertion time
        start_time = time.time()
        for node in nodes:
            self.env.node_store.put(node)
        end_time = time.time()
        
        insertion_time = end_time - start_time
        ops_per_second = node_count / insertion_time
        
        return {
            "operation": "node_insertion",
            "count": node_count,
            "total_time": insertion_time,
            "ops_per_second": ops_per_second
        }
        
    def benchmark_node_retrieval(self, node_count: int = 10000):
        """Benchmark node retrieval performance"""
        # Generate and store nodes
        node_ids = []
        for _ in range(node_count):
            node = self.generator.generate_node()
            self.env.node_store.put(node)
            node_ids.append(node.id)
            
        # Measure retrieval time
        start_time = time.time()
        for node_id in node_ids:
            self.env.node_store.get(node_id)
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        ops_per_second = node_count / retrieval_time
        
        return {
            "operation": "node_retrieval",
            "count": node_count,
            "total_time": retrieval_time,
            "ops_per_second": ops_per_second
        }
        
    def benchmark_spatial_indexing(self, node_count: int = 10000):
        """Benchmark spatial indexing performance"""
        # Generate nodes
        nodes = [self.generator.generate_node() for _ in range(node_count)]
        
        # Measure index insertion time
        start_time = time.time()
        for node in nodes:
            coord = SpatioTemporalCoordinate(*node.position)
            self.env.spatial_index.insert(coord, node.id)
        end_time = time.time()
        
        insertion_time = end_time - start_time
        insertion_ops_per_second = node_count / insertion_time
        
        # Measure query time (nearest neighbor)
        query_times = []
        
        for _ in range(100):  # 100 queries
            query_pos = (
                self.generator.random.uniform(0, 100),
                self.generator.random.uniform(0, 10),
                self.generator.random.uniform(0, 2 * math.pi)
            )
            query_coord = SpatioTemporalCoordinate(*query_pos)
            
            query_start = time.time()
            self.env.spatial_index.nearest_neighbors(query_coord, k=10)
            query_end = time.time()
            
            query_times.append(query_end - query_start)
            
        avg_query_time = sum(query_times) / len(query_times)
        query_ops_per_second = 1 / avg_query_time
        
        return {
            "operation": "spatial_indexing",
            "count": node_count,
            "insertion_time": insertion_time,
            "insertion_ops_per_second": insertion_ops_per_second,
            "avg_query_time": avg_query_time,
            "query_ops_per_second": query_ops_per_second
        }
        
    def benchmark_delta_reconstruction(self, chain_length: int = 100):
        """Benchmark delta chain reconstruction performance"""
        # Generate base node
        base_node = self.generator.generate_node()
        self.env.node_store.put(base_node)
        
        # Create a chain of deltas
        from src.delta.detector import ChangeDetector
        from src.delta.reconstruction import StateReconstructor
        
        detector = ChangeDetector()
        
        # Create chain
        previous_content = base_node.content
        previous_delta_id = None
        base_t = base_node.position[0]
        
        for i in range(1, chain_length + 1):
            # Create evolved content
            new_content = self.generator._evolve_content(
                previous_content,
                magnitude=0.1
            )
            
            # Create delta
            delta = detector.create_delta(
                node_id=base_node.id,
                previous_content=previous_content,
                new_content=new_content,
                timestamp=base_t + i,
                previous_delta_id=previous_delta_id
            )
            
            # Store delta
            self.env.delta_store.store_delta(delta)
            
            # Update for next iteration
            previous_content = new_content
            previous_delta_id = delta.delta_id
            
        # Measure reconstruction time
        reconstructor = StateReconstructor(self.env.delta_store)
        
        start_time = time.time()
        reconstructed = reconstructor.reconstruct_state(
            node_id=base_node.id,
            origin_content=base_node.content,
            target_timestamp=base_t + chain_length
        )
        end_time = time.time()
        
        reconstruction_time = end_time - start_time
        
        return {
            "operation": "delta_reconstruction",
            "chain_length": chain_length,
            "reconstruction_time": reconstruction_time,
            "ops_per_second": 1 / reconstruction_time
        }


class ScalabilityBenchmark:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        """
        Initialize benchmark
        
        Args:
            env: Test environment
            generator: Test data generator
        """
        self.env = env
        self.generator = generator
        
    def benchmark_increasing_node_count(self, 
                                      max_nodes: int = 100000, 
                                      step: int = 10000):
        """Benchmark performance with increasing node count"""
        results = []
        
        for node_count in range(step, max_nodes + step, step):
            # Generate nodes
            nodes = [self.generator.generate_node() for _ in range(step)]
            
            # Measure insertion time
            start_time = time.time()
            for node in nodes:
                self.env.node_store.put(node)
                coord = SpatioTemporalCoordinate(*node.position)
                self.env.spatial_index.insert(coord, node.id)
            end_time = time.time()
            
            # Measure query time
            query_times = []
            for _ in range(100):  # 100 random queries
                t = self.generator.random.uniform(0, 100)
                r = self.generator.random.uniform(0, 10)
                theta = self.generator.random.uniform(0, 2 * math.pi)
                coord = SpatioTemporalCoordinate(t, r, theta)
                
                query_start = time.time()
                self.env.spatial_index.nearest_neighbors(coord, k=10)
                query_end = time.time()
                
                query_times.append(query_end - query_start)
            
            # Record results
            results.append({
                "node_count": node_count,
                "insertion_time": end_time - start_time,
                "avg_query_time": sum(query_times) / len(query_times),
                "min_query_time": min(query_times),
                "max_query_time": max(query_times)
            })
            
        return results
        
    def benchmark_increasing_delta_chain_length(self,
                                              max_length: int = 1000,
                                              step: int = 100):
        """Benchmark performance with increasing delta chain length"""
        # Generate base node
        base_node = self.generator.generate_node()
        self.env.node_store.put(base_node)
        
        # Set up for delta chain
        from src.delta.detector import ChangeDetector
        from src.delta.reconstruction import StateReconstructor
        
        detector = ChangeDetector()
        reconstructor = StateReconstructor(self.env.delta_store)
        
        # Create chain incrementally and benchmark
        results = []
        previous_content = base_node.content
        previous_delta_id = None
        base_t = base_node.position[0]
        
        current_length = 0
        
        while current_length < max_length:
            # Add 'step' more deltas to the chain
            for i in range(1, step + 1):
                # Create evolved content
                new_content = self.generator._evolve_content(
                    previous_content,
                    magnitude=0.1
                )
                
                # Create delta
                delta = detector.create_delta(
                    node_id=base_node.id,
                    previous_content=previous_content,
                    new_content=new_content,
                    timestamp=base_t + current_length + i,
                    previous_delta_id=previous_delta_id
                )
                
                # Store delta
                self.env.delta_store.store_delta(delta)
                
                # Update for next iteration
                previous_content = new_content
                previous_delta_id = delta.delta_id
                
            # Update current length
            current_length += step
            
            # Measure reconstruction time
            start_time = time.time()
            reconstructed = reconstructor.reconstruct_state(
                node_id=base_node.id,
                origin_content=base_node.content,
                target_timestamp=base_t + current_length
            )
            end_time = time.time()
            
            # Record results
            results.append({
                "chain_length": current_length,
                "reconstruction_time": end_time - start_time,
                "ops_per_second": 1 / (end_time - start_time)
            })
            
        return results


class ComparativeBenchmark:
    def __init__(self):
        """Initialize comparative benchmark"""
        self.results = {}
        
    def compare_storage_implementations(self, 
                                      node_count: int = 10000,
                                      implementations: List[str] = ["memory", "rocksdb"]):
        """Compare different storage implementations"""
        for impl in implementations:
            # Create appropriate environment
            if impl == "memory":
                env = TestEnvironment(use_in_memory=True)
            else:
                test_dir = tempfile.mkdtemp()
                env = TestEnvironment(use_in_memory=False, 
                                      test_data_path=test_dir)
            
            generator = TestDataGenerator()
            benchmark = BasicOperationBenchmark(env, generator)
            
            # Run benchmarks
            env.setup()
            insertion_results = benchmark.benchmark_node_insertion(node_count)
            retrieval_results = benchmark.benchmark_node_retrieval(node_count)
            env.teardown()
            
            # Store results
            self.results[f"{impl}_insertion"] = insertion_results
            self.results[f"{impl}_retrieval"] = retrieval_results
            
            # Clean up
            if impl != "memory":
                shutil.rmtree(test_dir)
            
        return self.results
        
    def compare_indexing_strategies(self,
                                  node_count: int = 10000,
                                  strategies: List[Dict] = [
                                      {"name": "default", "max_entries": 50, "min_entries": 20},
                                      {"name": "small_nodes", "max_entries": 20, "min_entries": 8},
                                      {"name": "large_nodes", "max_entries": 100, "min_entries": 40}
                                  ]):
        """Compare different indexing strategies"""
        for strategy in strategies:
            # Create environment with specific strategy
            env = TestEnvironment(use_in_memory=True)
            env.setup()
            
            # Override the spatial index with specified parameters
            from src.indexing.rtree import RTree
            env.spatial_index = RTree(
                max_entries=strategy["max_entries"],
                min_entries=strategy["min_entries"]
            )
            
            # Run benchmarks
            generator = TestDataGenerator()
            benchmark = BasicOperationBenchmark(env, generator)
            
            results = benchmark.benchmark_spatial_indexing(node_count)
            
            # Store results with strategy name
            self.results[f"strategy_{strategy['name']}"] = results
            
            # Clean up
            env.teardown()
            
        return self.results


def format_benchmark_results(results: Dict) -> pd.DataFrame:
    """Convert benchmark results to a pandas DataFrame"""
    # If results is a list of dicts, convert to DataFrame directly
    if isinstance(results, list):
        return pd.DataFrame(results)
    
    # If results is a nested dict, flatten it
    flattened = []
    for key, value in results.items():
        if isinstance(value, dict):
            row = {"benchmark": key}
            row.update(value)
            flattened.append(row)
        elif isinstance(value, list):
            for item in value:
                row = {"benchmark": key}
                row.update(item)
                flattened.append(row)
    
    return pd.DataFrame(flattened)


def save_results_to_file(results: Dict, filename: str):
    """Save benchmark results to file (JSON and CSV)"""
    # Save as JSON
    with open(f"{filename}.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save as CSV
    df = format_benchmark_results(results)
    df.to_csv(f"{filename}.csv", index=False)
    
    print(f"Results saved to {filename}.json and {filename}.csv")


def plot_operation_performance(results: pd.DataFrame, operation: str):
    """Plot performance of a specific operation"""
    try:
        import matplotlib.pyplot as plt
        
        # Filter for the specific operation
        op_results = results[results['operation'] == operation]
        
        plt.figure(figsize=(10, 6))
        plt.bar(op_results['benchmark'], op_results['ops_per_second'])
        plt.xlabel('Benchmark')
        plt.ylabel('Operations per second')
        plt.title(f'{operation} Performance')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save plot
        plt.savefig(f"{operation}_performance.png")
        plt.close()
        
        print(f"Plot saved to {operation}_performance.png")
        
    except ImportError:
        print("Matplotlib not available for plotting. Install with: pip install matplotlib")


def plot_scalability_results(results: pd.DataFrame, x_column: str, y_column: str):
    """Plot scalability test results"""
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(10, 6))
        plt.plot(results[x_column], results[y_column], marker='o')
        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.title(f'{y_column} vs {x_column}')
        plt.grid(True)
        
        # Save plot
        plt.savefig(f"{y_column}_vs_{x_column}.png")
        plt.close()
        
        print(f"Plot saved to {y_column}_vs_{x_column}.png")
        
    except ImportError:
        print("Matplotlib not available for plotting. Install with: pip install matplotlib")


def run_basic_benchmarks(node_count: int = 10000):
    """Run basic benchmarks and save results"""
    # Set up environment
    env = TestEnvironment(use_in_memory=True)
    generator = TestDataGenerator()
    
    env.setup()
    
    # Create benchmark
    benchmark = BasicOperationBenchmark(env, generator)
    
    # Run benchmarks
    results = {
        "node_insertion": benchmark.benchmark_node_insertion(node_count),
        "node_retrieval": benchmark.benchmark_node_retrieval(node_count),
        "spatial_indexing": benchmark.benchmark_spatial_indexing(node_count // 10),
        "delta_reconstruction": benchmark.benchmark_delta_reconstruction(100)
    }
    
    # Clean up
    env.teardown()
    
    # Save results
    save_results_to_file(results, "basic_benchmarks")
    
    # Format and return results
    return format_benchmark_results(results)


def run_comparison_benchmarks(node_count: int = 5000):
    """Run comparison benchmarks and save results"""
    # Run storage comparison
    comparison = ComparativeBenchmark()
    storage_results = comparison.compare_storage_implementations(node_count)
    
    # Run indexing strategy comparison
    indexing_results = comparison.compare_indexing_strategies(node_count)
    
    # Combine results
    all_results = {**storage_results, **indexing_results}
    
    # Save results
    save_results_to_file(all_results, "comparison_benchmarks")
    
    # Format and return results
    return format_benchmark_results(all_results)


def run_scalability_benchmarks(max_nodes: int = 50000, node_step: int = 10000):
    """Run scalability benchmarks and save results"""
    # Set up environment
    env = TestEnvironment(use_in_memory=True)
    generator = TestDataGenerator()
    
    env.setup()
    
    # Create benchmark
    benchmark = ScalabilityBenchmark(env, generator)
    
    # Run node count scalability benchmark
    node_count_results = benchmark.benchmark_increasing_node_count(
        max_nodes=max_nodes, 
        step=node_step
    )
    
    # Run delta chain scalability benchmark (with smaller values)
    delta_chain_results = benchmark.benchmark_increasing_delta_chain_length(
        max_length=500,
        step=100
    )
    
    # Clean up
    env.teardown()
    
    # Save results
    save_results_to_file({
        "node_count_scalability": node_count_results,
        "delta_chain_scalability": delta_chain_results
    }, "scalability_benchmarks")
    
    # Plot results
    node_df = pd.DataFrame(node_count_results)
    plot_scalability_results(node_df, "node_count", "avg_query_time")
    
    delta_df = pd.DataFrame(delta_chain_results)
    plot_scalability_results(delta_df, "chain_length", "reconstruction_time")
    
    return {
        "node_count_results": node_df,
        "delta_chain_results": delta_df
    }


if __name__ == "__main__":
    print("Running basic benchmarks...")
    basic_results = run_basic_benchmarks(5000)
    print(basic_results)
    
    print("\nRunning comparison benchmarks...")
    comparison_results = run_comparison_benchmarks(2000)
    print(comparison_results)
    
    print("\nRunning scalability benchmarks...")
    scalability_results = run_scalability_benchmarks(30000, 10000)
    print(scalability_results) 
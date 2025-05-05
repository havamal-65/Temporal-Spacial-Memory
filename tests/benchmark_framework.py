"""
Benchmarking Framework for Temporal-Spatial Memory System.

This module provides tools for benchmarking and comparing the performance of
standard vector embeddings versus the 4D polar-temporal coordinate system.
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional, Callable
import logging
from pathlib import Path

# Add src directory to path to allow importing atlas components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from models.narrative_atlas import NarrativeAtlas, Node
from coordinates import PolarTemporalCoordinate
from nl_parser import CoordinateFilters
from utils.embedding_service import create_embedding_service
from data_models import PolarTemporalCoordinate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Benchmark")


class BenchmarkResult:
    """Container for benchmark test results."""
    
    def __init__(self, name: str):
        """
        Initialize a benchmark result container.
        
        Args:
            name: Name of the benchmark test
        """
        self.name = name
        self.metrics = {}
        self.timings = {}
        self.memory_usage = {}
        self.comparison_data = {}
        self.accuracy_metrics = {}
        self.metadata = {}
        
    def add_metric(self, metric_name: str, value: Any):
        """Add a metric result."""
        self.metrics[metric_name] = value
        
    def add_timing(self, operation_name: str, time_seconds: float):
        """Add a timing result."""
        self.timings[operation_name] = time_seconds
        
    def add_memory_usage(self, stage_name: str, memory_mb: float):
        """Add memory usage information."""
        self.memory_usage[stage_name] = memory_mb
        
    def add_accuracy(self, metric_name: str, value: float):
        """Add an accuracy metric."""
        self.accuracy_metrics[metric_name] = value
        
    def add_metadata(self, key: str, value: Any):
        """Add metadata about the benchmark."""
        self.metadata[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to a dictionary."""
        return {
            "name": self.name,
            "metrics": self.metrics,
            "timings": self.timings,
            "memory_usage": self.memory_usage,
            "accuracy_metrics": self.accuracy_metrics,
            "metadata": self.metadata,
            "comparison_data": self.comparison_data
        }
    
    def save_to_json(self, output_path: str):
        """Save results to a JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Benchmark results saved to {output_path}")
        
    def plot_timings(self, output_path: Optional[str] = None):
        """Generate a bar chart of timing results."""
        if not self.timings:
            logger.warning("No timing data to plot")
            return
        
        plt.figure(figsize=(10, 6))
        operations = list(self.timings.keys())
        times = list(self.timings.values())
        
        plt.bar(operations, times)
        plt.xlabel('Operation')
        plt.ylabel('Time (seconds)')
        plt.title(f'Timing Results for {self.name}')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path)
            logger.info(f"Timing plot saved to {output_path}")
        else:
            plt.show()


class BenchmarkRunner:
    """
    Framework for running performance and accuracy benchmarks on the
    Temporal-Spatial Memory System.
    """
    
    def __init__(self, 
                 output_dir: str = "output/benchmarks",
                 enable_memory_profiling: bool = True):
        """
        Initialize the benchmark runner.
        
        Args:
            output_dir: Directory to save benchmark results
            enable_memory_profiling: Whether to track memory usage (requires psutil)
        """
        self.output_dir = output_dir
        self.enable_memory_profiling = enable_memory_profiling
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup memory profiling if enabled
        self.psutil = None
        if enable_memory_profiling:
            try:
                import psutil
                self.psutil = psutil
                logger.info("Memory profiling enabled")
            except ImportError:
                logger.warning("psutil not available. Memory profiling disabled.")
                self.enable_memory_profiling = False
    
    def measure_execution_time(self, func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure execution time of a function.
        
        Args:
            func: Function to measure
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Tuple of (function result, execution time in seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    def get_current_memory_usage(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in MB or -1 if memory profiling is disabled
        """
        if not self.enable_memory_profiling or self.psutil is None:
            return -1
        
        process = self.psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # Convert to MB
        return memory_info.rss / (1024 * 1024)
    
    def compare_atlases(self, 
                       standard_atlas: NarrativeAtlas, 
                       polar_atlas: NarrativeAtlas,
                       query_texts: List[str],
                       ground_truth: Dict[str, List[str]] = None) -> BenchmarkResult:
        """
        Compare performance and retrieval results between standard and polar coordinate atlases.
        
        Args:
            standard_atlas: NarrativeAtlas using standard vector embeddings
            polar_atlas: NarrativeAtlas using polar-temporal coordinates
            query_texts: List of query texts to test retrieval
            ground_truth: Dictionary mapping query texts to lists of relevant node IDs
            
        Returns:
            BenchmarkResult with comparison metrics
        """
        result = BenchmarkResult("Atlas Comparison Benchmark")
        
        # Record atlas metadata
        result.add_metadata("standard_atlas_nodes", len(standard_atlas.db.nodes))
        result.add_metadata("polar_atlas_nodes", len(polar_atlas.db.nodes))
        
        # Compare memory usage
        if self.enable_memory_profiling:
            # First measure baseline
            baseline_memory = self.get_current_memory_usage()
            
            # Get standard atlas size
            standard_size = sys.getsizeof(standard_atlas)
            result.add_memory_usage("standard_atlas_size", standard_size / (1024 * 1024))
            
            # Get polar atlas size
            polar_size = sys.getsizeof(polar_atlas)
            result.add_memory_usage("polar_atlas_size", polar_size / (1024 * 1024))
        
        # Compare retrieval performance and accuracy
        standard_timings = []
        polar_timings = []
        standard_precision = []
        polar_precision = []
        
        for query in query_texts:
            # Measure standard atlas query time
            standard_results, standard_time = self.measure_execution_time(
                standard_atlas.similarity_search, query, k=5
            )
            standard_timings.append(standard_time)
            
            # Measure polar atlas query time
            polar_results, polar_time = self.measure_execution_time(
                polar_atlas.similarity_search, query, k=5
            )
            polar_timings.append(polar_time)
            
            # Calculate precision if ground truth is provided
            if ground_truth and query in ground_truth:
                relevant_ids = ground_truth[query]
                
                # Calculate precision for standard atlas
                standard_retrieved_ids = [r[0].metadata.get('node_id') for r in standard_results]
                standard_relevant_count = sum(1 for id in standard_retrieved_ids if id in relevant_ids)
                standard_precision.append(standard_relevant_count / len(standard_retrieved_ids) if standard_retrieved_ids else 0)
                
                # Calculate precision for polar atlas
                polar_retrieved_ids = [r[0].metadata.get('node_id') for r in polar_results]
                polar_relevant_count = sum(1 for id in polar_retrieved_ids if id in relevant_ids)
                polar_precision.append(polar_relevant_count / len(polar_retrieved_ids) if polar_retrieved_ids else 0)
        
        # Calculate average query time
        avg_standard_time = sum(standard_timings) / len(standard_timings) if standard_timings else 0
        avg_polar_time = sum(polar_timings) / len(polar_timings) if polar_timings else 0
        
        result.add_timing("standard_atlas_avg_query", avg_standard_time)
        result.add_timing("polar_atlas_avg_query", avg_polar_time)
        result.add_metric("query_speedup", avg_standard_time / avg_polar_time if avg_polar_time > 0 else float('inf'))
        
        # Record precision metrics if ground truth was provided
        if ground_truth:
            avg_standard_precision = sum(standard_precision) / len(standard_precision) if standard_precision else 0
            avg_polar_precision = sum(polar_precision) / len(polar_precision) if polar_precision else 0
            
            result.add_accuracy("standard_atlas_precision", avg_standard_precision)
            result.add_accuracy("polar_atlas_precision", avg_polar_precision)
            result.add_metric("precision_improvement", 
                             (avg_polar_precision - avg_standard_precision) / avg_standard_precision 
                             if avg_standard_precision > 0 else float('inf'))
        
        return result
    
    def benchmark_retrieval_options(self, 
                                  atlas: NarrativeAtlas,
                                  query_texts: List[str],
                                  filter_options: List[Dict[str, Any]]) -> BenchmarkResult:
        """
        Benchmark different retrieval filter options.
        
        Args:
            atlas: NarrativeAtlas to benchmark
            query_texts: List of query texts to test
            filter_options: List of filter option dictionaries to test
            
        Returns:
            BenchmarkResult with option comparison metrics
        """
        result = BenchmarkResult("Filter Options Benchmark")
        
        result.add_metadata("atlas_nodes", len(atlas.db.nodes))
        result.add_metadata("filter_options_count", len(filter_options))
        
        # Compare different filter options
        for i, options in enumerate(filter_options):
            option_name = options.get('name', f"Option_{i}")
            
            # Create coordinate filters
            filters = CoordinateFilters(
                r_max=options.get('r_max'),
                t_min=options.get('t_min'),
                t_max=options.get('t_max'),
                z_min=options.get('z_min'),
                z_max=options.get('z_max'),
                theta_min=options.get('theta_min'),
                theta_max=options.get('theta_max')
            )
            
            # Test query time
            query_times = []
            result_counts = []
            
            for query in query_texts:
                # Measure query time with these filters
                results, query_time = self.measure_execution_time(
                    atlas.similarity_search_with_filters, query, filters, k=5
                )
                
                query_times.append(query_time)
                result_counts.append(len(results))
            
            # Calculate average metrics
            avg_query_time = sum(query_times) / len(query_times) if query_times else 0
            avg_result_count = sum(result_counts) / len(result_counts) if result_counts else 0
            
            # Add to results
            result.add_timing(f"{option_name}_avg_query", avg_query_time)
            result.add_metric(f"{option_name}_avg_results", avg_result_count)
            
            # Store filter details
            result.metadata[f"filter_{option_name}"] = {
                "r_max": options.get('r_max'),
                "t_min": options.get('t_min'),
                "t_max": options.get('t_max'),
                "z_min": options.get('z_min'),
                "z_max": options.get('z_max'),
                "theta_min": options.get('theta_min'),
                "theta_max": options.get('theta_max')
            }
        
        return result
    
    def benchmark_atlas_operations(self, atlas: NarrativeAtlas) -> BenchmarkResult:
        """
        Benchmark basic atlas operations like adding and retrieving nodes.
        
        Args:
            atlas: NarrativeAtlas to benchmark
            
        Returns:
            BenchmarkResult with operation timing metrics
        """
        result = BenchmarkResult("Atlas Operations Benchmark")
        
        # Generate random test data
        test_nodes = []
        for i in range(10):
            node_id = f"benchmark_node_{i}"
            node_content = f"Benchmark test content for node {i}"
            node_type = "benchmark"
            node_coords = PolarTemporalCoordinate(
                r=0.5, 
                theta=i * 0.1 * np.pi, 
                z=1, 
                t=i * 10,
                z_type="test"
            )
            test_nodes.append((node_id, node_content, node_type, node_coords))
        
        # Benchmark node addition
        total_add_time = 0
        for node_id, content, node_type, coords in test_nodes:
            # Time adding a node
            _, add_time = self.measure_execution_time(
                atlas.add_node,
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coords
            )
            total_add_time += add_time
        
        avg_add_time = total_add_time / len(test_nodes)
        result.add_timing("avg_node_add", avg_add_time)
        
        # Benchmark node retrieval by ID
        total_get_time = 0
        for node_id, _, _, _ in test_nodes:
            # Time getting a node by ID
            _, get_time = self.measure_execution_time(
                atlas.get_node,
                node_id
            )
            total_get_time += get_time
        
        avg_get_time = total_get_time / len(test_nodes)
        result.add_timing("avg_node_get", avg_get_time)
        
        # Benchmark node updates
        total_update_time = 0
        for node_id, _, _, _ in test_nodes:
            # Get the node
            node = atlas.get_node(node_id)
            if node:
                # Update its coordinates
                node.coordinates.r += 0.1
                # Time updating the node
                _, update_time = self.measure_execution_time(
                    atlas.update_node,
                    node
                )
                total_update_time += update_time
        
        avg_update_time = total_update_time / len(test_nodes)
        result.add_timing("avg_node_update", avg_update_time)
        
        # Clean up test nodes
        for node_id, _, _, _ in test_nodes:
            atlas.remove_node(node_id)
        
        return result


def run_full_benchmark_suite(
    atlas_path: str,
    output_dir: str = "output/benchmarks",
    embedding_service_type: str = "langchain"
) -> Dict[str, BenchmarkResult]:
    """
    Run a complete benchmark suite on the Temporal-Spatial Memory System.
    
    Args:
        atlas_path: Path to the atlas to benchmark
        output_dir: Directory to save benchmark results
        embedding_service_type: Type of embedding service to use
        
    Returns:
        Dictionary of benchmark names to results
    """
    logger.info(f"Starting full benchmark suite on atlas: {atlas_path}")
    
    # Create benchmark runner
    runner = BenchmarkRunner(output_dir=output_dir)
    
    # Create embedding service
    embedding_service = create_embedding_service(service_type=embedding_service_type)
    
    # Load the atlas
    atlas = NarrativeAtlas(storage_path=atlas_path, embedding_service=embedding_service)
    
    # Check if atlas has nodes
    if not atlas.db.nodes:
        logger.error(f"No nodes found in atlas at {atlas_path}")
        return {}
    
    logger.info(f"Loaded atlas with {len(atlas.db.nodes)} nodes")
    
    # Results container
    results = {}
    
    # Benchmark 1: Basic Atlas Operations
    logger.info("Running Atlas Operations Benchmark")
    op_result = runner.benchmark_atlas_operations(atlas)
    op_result.save_to_json(f"{output_dir}/operations_benchmark.json")
    op_result.plot_timings(f"{output_dir}/operations_benchmark.png")
    results["operations"] = op_result
    
    # Benchmark 2: Retrieval Options
    logger.info("Running Retrieval Options Benchmark")
    
    # Sample queries from node content
    sample_nodes = list(atlas.db.nodes.values())[:5]
    query_texts = [str(node.content)[:50] for node in sample_nodes if node.content]
    
    # Define filter options to test
    filter_options = [
        {'name': 'no_filters', 'r_max': None, 't_min': None, 't_max': None},
        {'name': 'r_filter', 'r_max': 0.5, 't_min': None, 't_max': None},
        {'name': 't_filter', 'r_max': None, 't_min': 10, 't_max': 100},
        {'name': 'r_t_filter', 'r_max': 0.5, 't_min': 10, 't_max': 100},
    ]
    
    retrieval_result = runner.benchmark_retrieval_options(atlas, query_texts, filter_options)
    retrieval_result.save_to_json(f"{output_dir}/retrieval_options_benchmark.json")
    retrieval_result.plot_timings(f"{output_dir}/retrieval_options_benchmark.png")
    results["retrieval_options"] = retrieval_result
    
    # Benchmark 3: Generate summary report
    logger.info("Generating benchmark summary report")
    
    # Combine results into a summary
    summary = {
        "timestamp": time.time(),
        "atlas_path": atlas_path,
        "node_count": len(atlas.db.nodes),
        "benchmarks": {name: result.to_dict() for name, result in results.items()}
    }
    
    # Save summary
    with open(f"{output_dir}/benchmark_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Benchmark suite completed. Results saved to {output_dir}")
    return results


if __name__ == "__main__":
    # Example usage when run directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Run benchmarks on Temporal-Spatial Memory System")
    parser.add_argument("--atlas-path", type=str, required=True, help="Path to the atlas to benchmark")
    parser.add_argument("--output-dir", type=str, default="output/benchmarks", help="Directory to save benchmark results")
    parser.add_argument("--embedding-service", type=str, default="langchain", help="Embedding service type to use")
    
    args = parser.parse_args()
    
    run_full_benchmark_suite(
        atlas_path=args.atlas_path,
        output_dir=args.output_dir,
        embedding_service_type=args.embedding_service
    ) 
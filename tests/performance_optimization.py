"""
Performance Optimization Tool for Temporal-Spatial Memory System.

This script analyzes and optimizes performance bottlenecks in the system.
"""

import os
import sys
import time
import cProfile
import pstats
import io
import gc
import json
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from pathlib import Path

# Add src directory to path to allow importing atlas components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import local modules
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

logger = logging.getLogger("PerformanceOptimization")


def profile_function(func):
    """Decorator to profile a function's performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Print top 20 functions by cumulative time
        
        logger.info(f"Profile for {func.__name__}:\n{s.getvalue()}")
        return result
    return wrapper


class PerformanceOptimizer:
    """
    Tool for identifying and addressing performance bottlenecks.
    """
    
    def __init__(self, 
                 output_dir: str = "output/optimizations",
                 embedding_service_type: str = "langchain"):
        """
        Initialize the performance optimizer.
        
        Args:
            output_dir: Directory to save optimization results
            embedding_service_type: Type of embedding service to use
        """
        self.output_dir = output_dir
        self.embedding_service_type = embedding_service_type
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Create embedding service
        self.embedding_service = create_embedding_service(service_type=embedding_service_type)
        
        # Performance metrics
        self.metrics = {}
        
    def generate_test_data(self, num_nodes: int = 1000) -> List[Dict[str, Any]]:
        """
        Generate test data for performance testing.
        
        Args:
            num_nodes: Number of nodes to generate
            
        Returns:
            List of dictionaries with node data
        """
        logger.info(f"Generating {num_nodes} test nodes")
        
        node_types = ["document", "section", "paragraph", "entity"]
        
        test_nodes = []
        for i in range(num_nodes):
            # Create a unique node ID
            node_id = f"perf_node_{i:04d}"
            
            # Generate content with some repetitive patterns
            topic_idx = i % 5
            topic = ["science", "history", "technology", "art", "literature"][topic_idx]
            
            # Create content
            content = f"This is content about {topic} for performance testing node {i}."
            
            # Select node type
            node_type = node_types[i % len(node_types)]
            
            # Generate coordinates
            r = 0.1 + 0.8 * (i / num_nodes)  # Distribute r values
            theta = (i / num_nodes) * 2 * np.pi  # Distribute theta values evenly
            z = 1 + (i % 5)  # z values 1-5
            t = i * 10  # Sequential temporal position
            
            # Create node data
            node_data = {
                "id": node_id,
                "content": content,
                "type": node_type,
                "coordinates": {
                    "r": r,
                    "theta": theta,
                    "z": z,
                    "t": t,
                    "z_type": "test"
                }
            }
            
            test_nodes.append(node_data)
        
        return test_nodes
    
    @profile_function
    def test_atlas_creation(self, test_nodes: List[Dict[str, Any]], atlas_path: str) -> float:
        """
        Test atlas creation performance.
        
        Args:
            test_nodes: List of node data dictionaries
            atlas_path: Path to atlas storage
            
        Returns:
            Elapsed time in seconds
        """
        logger.info("Testing atlas creation performance")
        
        # Clean up existing atlas data
        if os.path.exists(atlas_path):
            for item in os.listdir(atlas_path):
                item_path = os.path.join(atlas_path, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    import shutil
                    shutil.rmtree(item_path)
        
        # Create atlas
        atlas = NarrativeAtlas(
            storage_path=atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Time adding nodes
        start_time = time.time()
        
        for node_data in test_nodes:
            # Extract node data
            node_id = node_data["id"]
            content = node_data["content"]
            node_type = node_data["type"]
            
            # Extract coordinates
            coord_data = node_data["coordinates"]
            coordinates = PolarTemporalCoordinate(
                r=coord_data["r"],
                theta=coord_data["theta"],
                z=coord_data["z"],
                t=coord_data["t"],
                z_type=coord_data.get("z_type", "")
            )
            
            # Add to atlas
            atlas.add_node(
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coordinates
            )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Atlas creation time: {elapsed_time:.2f} seconds for {len(test_nodes)} nodes")
        
        # Add metrics
        self.metrics["atlas_creation_time"] = elapsed_time
        self.metrics["nodes_per_second"] = len(test_nodes) / elapsed_time
        
        return elapsed_time
    
    @profile_function
    def test_query_performance(self, atlas_path: str, num_queries: int = 20) -> Dict[str, float]:
        """
        Test query performance.
        
        Args:
            atlas_path: Path to atlas storage
            num_queries: Number of queries to run
            
        Returns:
            Dictionary of query metrics
        """
        logger.info("Testing query performance")
        
        # Load atlas
        atlas = NarrativeAtlas(
            storage_path=atlas_path,
            embedding_service=self.embedding_service
        )
        
        num_nodes = len(atlas.db.nodes)
        logger.info(f"Loaded atlas with {num_nodes} nodes")
        
        # Generate test queries
        queries = [
            "science research",
            "history events",
            "technology innovations",
            "art concepts",
            "literature themes"
        ]
        
        # Multiply queries to reach desired count
        queries = queries * (num_queries // len(queries) + 1)
        queries = queries[:num_queries]
        
        # Test standard queries
        start_time = time.time()
        for query in queries:
            results = atlas.similarity_search(query, k=5)
        standard_query_time = time.time() - start_time
        avg_standard_query_time = standard_query_time / len(queries)
        
        logger.info(f"Standard query time: {standard_query_time:.2f} seconds for {len(queries)} queries")
        logger.info(f"Average query time: {avg_standard_query_time:.4f} seconds per query")
        
        # Test filtered queries
        filters = CoordinateFilters(r_max=0.5, t_min=100, t_max=500)
        
        start_time = time.time()
        for query in queries:
            results = atlas.similarity_search_with_filters(query, filters, k=5)
        filtered_query_time = time.time() - start_time
        avg_filtered_query_time = filtered_query_time / len(queries)
        
        logger.info(f"Filtered query time: {filtered_query_time:.2f} seconds for {len(queries)} queries")
        logger.info(f"Average filtered query time: {avg_filtered_query_time:.4f} seconds per query")
        
        # Add metrics
        query_metrics = {
            "total_standard_query_time": standard_query_time,
            "avg_standard_query_time": avg_standard_query_time,
            "total_filtered_query_time": filtered_query_time,
            "avg_filtered_query_time": avg_filtered_query_time,
            "filter_overhead": avg_filtered_query_time / avg_standard_query_time if avg_standard_query_time > 0 else 0
        }
        
        self.metrics.update(query_metrics)
        return query_metrics
    
    @profile_function
    def test_memory_usage(self, atlas_path: str) -> Dict[str, float]:
        """
        Test memory usage.
        
        Args:
            atlas_path: Path to atlas storage
            
        Returns:
            Dictionary of memory metrics
        """
        logger.info("Testing memory usage")
        
        # Force garbage collection
        gc.collect()
        
        # Get baseline memory
        try:
            import psutil
            baseline_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        except ImportError:
            logger.warning("psutil not available, memory metrics will be limited")
            baseline_memory = 0
        
        # Load atlas
        atlas = NarrativeAtlas(
            storage_path=atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Get memory after loading
        try:
            import psutil
            loaded_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
            atlas_memory = loaded_memory - baseline_memory
        except ImportError:
            loaded_memory = 0
            atlas_memory = 0
        
        # Number of nodes
        num_nodes = len(atlas.db.nodes)
        
        # Calculate memory metrics
        memory_metrics = {
            "baseline_memory_mb": baseline_memory,
            "loaded_memory_mb": loaded_memory,
            "atlas_memory_mb": atlas_memory,
            "memory_per_node_kb": (atlas_memory * 1024) / num_nodes if num_nodes > 0 else 0
        }
        
        logger.info(f"Memory metrics: {memory_metrics}")
        
        # Add metrics
        self.metrics.update(memory_metrics)
        return memory_metrics
    
    def analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Analyze bottlenecks based on collected metrics.
        
        Returns:
            List of bottleneck issues and recommendations
        """
        logger.info("Analyzing performance bottlenecks")
        
        bottlenecks = []
        
        # Check node creation speed
        nodes_per_second = self.metrics.get("nodes_per_second", 0)
        if nodes_per_second < 10:
            bottlenecks.append({
                "issue": "Slow node creation",
                "metric": f"{nodes_per_second:.2f} nodes/second",
                "recommendation": "Consider batching node creation or optimizing embedding generation"
            })
        
        # Check query speed
        avg_query_time = self.metrics.get("avg_standard_query_time", 0)
        if avg_query_time > 0.1:
            bottlenecks.append({
                "issue": "Slow query performance",
                "metric": f"{avg_query_time:.4f} seconds/query",
                "recommendation": "Optimize vector search or add caching for frequent queries"
            })
        
        # Check filter overhead
        filter_overhead = self.metrics.get("filter_overhead", 0)
        if filter_overhead > 2.0:
            bottlenecks.append({
                "issue": "High filtering overhead",
                "metric": f"{filter_overhead:.2f}x slower with filters",
                "recommendation": "Pre-filter candidates before embedding similarity or implement coordinate indexing"
            })
        
        # Check memory usage
        memory_per_node = self.metrics.get("memory_per_node_kb", 0)
        if memory_per_node > 100:  # More than 100KB per node
            bottlenecks.append({
                "issue": "High memory usage per node",
                "metric": f"{memory_per_node:.2f} KB/node",
                "recommendation": "Implement more efficient storage or compression for node content"
            })
        
        logger.info(f"Found {len(bottlenecks)} potential bottlenecks")
        return bottlenecks
    
    def recommend_optimizations(self, bottlenecks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate optimization recommendations.
        
        Args:
            bottlenecks: List of identified bottlenecks
            
        Returns:
            Dictionary of optimization recommendations
        """
        logger.info("Generating optimization recommendations")
        
        # General recommendations
        general_recommendations = [
            "Use dimension reduction techniques for embeddings to reduce memory and improve search speed",
            "Implement caching for frequently accessed nodes and query results",
            "Consider using approximate nearest neighbor algorithms for faster retrieval",
            "Optimize coordinate transformation functions, especially for large batch operations",
            "Profile the system regularly to identify new bottlenecks as the system grows"
        ]
        
        # Specific recommendations based on bottlenecks
        specific_recommendations = []
        for bottleneck in bottlenecks:
            specific_recommendations.append(f"{bottleneck['issue']}: {bottleneck['recommendation']}")
        
        # Implementation suggestions
        implementation_suggestions = []
        
        # Add suggestions based on metrics
        if self.metrics.get("nodes_per_second", 0) < 10:
            implementation_suggestions.append(
                "Implement batch embedding generation to reduce API calls and improve throughput"
            )
        
        if self.metrics.get("filter_overhead", 0) > 2.0:
            implementation_suggestions.append(
                "Create a secondary index for coordinate values to speed up filtering operations"
            )
        
        if self.metrics.get("avg_standard_query_time", 0) > 0.1:
            implementation_suggestions.append(
                "Implement query result caching using a LRU (Least Recently Used) cache"
            )
        
        # Combine recommendations
        recommendations = {
            "general_recommendations": general_recommendations,
            "specific_recommendations": specific_recommendations,
            "implementation_suggestions": implementation_suggestions,
            "metrics": self.metrics
        }
        
        return recommendations
    
    def run_optimization_analysis(self) -> Dict[str, Any]:
        """
        Run a complete optimization analysis.
        
        Returns:
            Dictionary with optimization results
        """
        logger.info("Starting optimization analysis")
        
        # Generate test data
        test_nodes = self.generate_test_data(num_nodes=500)
        
        # Create test atlas path
        atlas_path = os.path.join(self.output_dir, "test_atlas")
        os.makedirs(atlas_path, exist_ok=True)
        
        # Test atlas creation
        self.test_atlas_creation(test_nodes, atlas_path)
        
        # Test query performance
        self.test_query_performance(atlas_path)
        
        # Test memory usage
        self.test_memory_usage(atlas_path)
        
        # Analyze bottlenecks
        bottlenecks = self.analyze_bottlenecks()
        
        # Generate recommendations
        recommendations = self.recommend_optimizations(bottlenecks)
        
        # Combine results
        results = {
            "metrics": self.metrics,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations
        }
        
        # Save results
        results_path = os.path.join(self.output_dir, "optimization_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Optimization analysis completed. Results saved to {results_path}")
        return results


def run_optimization_analysis(output_dir: str = "output/optimizations"):
    """
    Run a performance optimization analysis.
    
    Args:
        output_dir: Directory to save optimization results
    """
    optimizer = PerformanceOptimizer(output_dir=output_dir)
    results = optimizer.run_optimization_analysis()
    
    # Print summary of findings
    print("\n== Performance Optimization Summary ==")
    print(f"Nodes per second: {results['metrics'].get('nodes_per_second', 0):.2f}")
    print(f"Average query time: {results['metrics'].get('avg_standard_query_time', 0):.4f} seconds")
    print(f"Memory per node: {results['metrics'].get('memory_per_node_kb', 0):.2f} KB")
    
    print("\n== Identified Bottlenecks ==")
    for bottleneck in results['bottlenecks']:
        print(f"- {bottleneck['issue']}: {bottleneck['metric']}")
        print(f"  Recommendation: {bottleneck['recommendation']}")
    
    print("\n== Top Implementation Suggestions ==")
    for suggestion in results['recommendations']['implementation_suggestions'][:3]:
        print(f"- {suggestion}")
    
    print(f"\nDetailed results saved to {output_dir}/optimization_results.json")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance optimization analysis")
    parser.add_argument("--output-dir", type=str, default="output/optimizations", 
                        help="Directory to save optimization results")
    
    args = parser.parse_args()
    
    run_optimization_analysis(output_dir=args.output_dir) 
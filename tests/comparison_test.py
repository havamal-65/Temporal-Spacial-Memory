"""
Comparative Testing Framework for Temporal-Spatial Memory System.

This script performs direct comparisons between standard vector embeddings and 
the polar-temporal coordinate system by ingesting the same data into two different
atlases and measuring their performance characteristics.
"""

import os
import sys
import argparse
import time
import json
import numpy as np
import pandas as pd
import logging
from pathlib import Path
import shutil
from typing import Dict, List, Any, Optional, Tuple

# Add src directory to path to allow importing atlas components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import local modules
from models.narrative_atlas import NarrativeAtlas, Node
from coordinates import PolarTemporalCoordinate
from nl_parser import CoordinateFilters
from utils.embedding_service import create_embedding_service
from data_models import PolarTemporalCoordinate
from benchmark_framework import BenchmarkResult, BenchmarkRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ComparisonTest")


class ComparativeTester:
    """
    Framework for testing standard vector embeddings vs. polar-temporal coordinates.
    
    This class creates and manages two NarrativeAtlas instances - one using
    standard vector embeddings and one using the 4D polar-temporal coordinate system.
    It then performs direct comparisons in performance, accuracy, and efficiency.
    """
    
    def __init__(self, 
                 output_dir: str = "output/comparative_tests",
                 test_data_dir: str = "tests/test_data",
                 embedding_service_type: str = "langchain"):
        """
        Initialize the comparative tester.
        
        Args:
            output_dir: Directory to save test results
            test_data_dir: Directory containing test data
            embedding_service_type: Type of embedding service to use
        """
        self.output_dir = output_dir
        self.test_data_dir = test_data_dir
        self.embedding_service_type = embedding_service_type
        
        # Create output and test data directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(test_data_dir, exist_ok=True)
        
        # Create benchmark runner for performance measurements
        self.benchmark_runner = BenchmarkRunner(output_dir=output_dir)
        
        # Embedding service
        self.embedding_service = create_embedding_service(service_type=embedding_service_type)
        
        # Atlas storage paths
        self.standard_atlas_path = os.path.join(output_dir, "standard_atlas")
        self.polar_atlas_path = os.path.join(output_dir, "polar_atlas")
        
        # Ensure atlas storage directories exist
        os.makedirs(self.standard_atlas_path, exist_ok=True)
        os.makedirs(self.polar_atlas_path, exist_ok=True)
        
        # Atlas instances (will be created during setup)
        self.standard_atlas = None
        self.polar_atlas = None
    
    def setup_test_data(self, 
                       source_data_path: Optional[str] = None,
                       num_test_nodes: int = 100) -> List[Dict[str, Any]]:
        """
        Set up test data for ingestion into atlases.
        
        Args:
            source_data_path: Path to source data (if None, generates synthetic data)
            num_test_nodes: Number of test nodes to generate (if using synthetic data)
            
        Returns:
            List of dictionaries with node data
        """
        logger.info("Setting up test data")
        
        test_nodes = []
        
        if source_data_path and os.path.exists(source_data_path):
            # Load from existing source
            logger.info(f"Loading test data from {source_data_path}")
            
            if source_data_path.endswith('.json'):
                # Load from JSON
                with open(source_data_path, 'r') as f:
                    test_nodes = json.load(f)
            elif source_data_path.endswith('.csv'):
                # Load from CSV
                df = pd.read_csv(source_data_path)
                test_nodes = df.to_dict(orient='records')
            else:
                logger.warning(f"Unsupported data format: {source_data_path}")
                # Fall back to synthetic data
                test_nodes = self._generate_synthetic_data(num_test_nodes)
        else:
            # Generate synthetic test data
            logger.info(f"Generating {num_test_nodes} synthetic test nodes")
            test_nodes = self._generate_synthetic_data(num_test_nodes)
        
        # Save test data for reference
        test_data_path = os.path.join(self.test_data_dir, "test_nodes.json")
        with open(test_data_path, 'w') as f:
            json.dump(test_nodes, f, indent=2)
        
        logger.info(f"Test data setup complete with {len(test_nodes)} nodes")
        return test_nodes
    
    def _generate_synthetic_data(self, num_nodes: int) -> List[Dict[str, Any]]:
        """
        Generate synthetic test data.
        
        Args:
            num_nodes: Number of nodes to generate
            
        Returns:
            List of dictionaries with node data
        """
        node_types = ["document", "section", "paragraph", "sentence", "entity"]
        z_types = ["structural", "semantic", "temporal", "mixed"]
        
        test_nodes = []
        
        for i in range(num_nodes):
            # Create a unique node ID
            node_id = f"test_node_{i:04d}"
            
            # Generate fake content (with some semantic patterns for later retrieval tests)
            topics = ["science", "history", "technology", "art", "literature"]
            topic_idx = i % len(topics)
            topic = topics[topic_idx]
            
            # Create content with some repetitive patterns for retrieval testing
            sequence_pos = i // len(topics)
            if sequence_pos % 3 == 0:
                content = f"This is a {topic} related text about important concepts and ideas."
            elif sequence_pos % 3 == 1:
                content = f"The {topic} field has many interesting applications and theories to explore."
            else:
                content = f"Researchers in {topic} are making new discoveries every day."
            
            # Add some unique text to make each node distinct
            content += f" This is unique content for node {i}."
            
            # Select node type (distribute types evenly)
            node_type = node_types[i % len(node_types)]
            
            # Generate "polar-temporal" coordinates
            # For synthetic data, create some patterns in the coordinates
            # that should be detectable in similarity searches
            r = 0.1 + 0.8 * (topic_idx / len(topics))  # r varies by topic (0.1-0.9)
            theta = (topic_idx / len(topics)) * 2 * np.pi  # theta by topic (0-2π)
            z = 1 + (i % 5)  # z between 1-5
            t = i * 10  # sequential temporal position
            z_type = z_types[i % len(z_types)]
            
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
                    "z_type": z_type
                },
                "metadata": {
                    "topic": topic,
                    "sequence_position": sequence_pos
                }
            }
            
            test_nodes.append(node_data)
        
        return test_nodes
    
    def setup_atlases(self, 
                     test_nodes: List[Dict[str, Any]],
                     clean_existing: bool = True) -> Tuple[NarrativeAtlas, NarrativeAtlas]:
        """
        Set up standard and polar-temporal atlases with the same test data.
        
        Args:
            test_nodes: List of dictionaries with node data
            clean_existing: Whether to clean existing atlas data
            
        Returns:
            Tuple of (standard_atlas, polar_atlas)
        """
        logger.info("Setting up test atlases")
        
        # Clean existing atlas data if requested
        if clean_existing:
            for path in [self.standard_atlas_path, self.polar_atlas_path]:
                if os.path.exists(path):
                    logger.info(f"Cleaning existing atlas data at {path}")
                    # Don't remove the directory itself, just its contents
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
        
        # Create standard atlas (using default settings)
        self.standard_atlas = NarrativeAtlas(
            storage_path=self.standard_atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Create polar atlas (with polar coordinate optimizations enabled)
        self.polar_atlas = NarrativeAtlas(
            storage_path=self.polar_atlas_path,
            embedding_service=self.embedding_service,
            use_polar_optimization=True  # Enable polar coordinate optimizations
        )
        
        # Ingest test nodes into both atlases
        logger.info(f"Ingesting {len(test_nodes)} test nodes into atlases")
        
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
            
            # Extract metadata
            metadata = node_data.get("metadata", {})
            
            # Add to standard atlas
            self.standard_atlas.add_node(
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coordinates,
                metadata=metadata
            )
            
            # Add to polar atlas
            self.polar_atlas.add_node(
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coordinates,
                metadata=metadata
            )
        
        logger.info(f"Atlas setup complete with {len(self.standard_atlas.db.nodes)} nodes")
        return self.standard_atlas, self.polar_atlas
    
    def generate_test_queries(self, test_nodes: List[Dict[str, Any]], num_queries: int = 10) -> List[Dict[str, Any]]:
        """
        Generate test queries and expected results from test data.
        
        Args:
            test_nodes: List of test node data
            num_queries: Number of queries to generate
            
        Returns:
            List of dictionaries with query data and expected results
        """
        logger.info(f"Generating {num_queries} test queries")
        
        # Group nodes by topic
        topics = {}
        for node in test_nodes:
            topic = node.get("metadata", {}).get("topic", "unknown")
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(node)
        
        test_queries = []
        
        # Create topic-based queries
        for topic, topic_nodes in topics.items():
            if len(topic_nodes) > 0:
                # Create a query based on this topic
                query_text = f"Information about {topic}"
                
                # Expected results are nodes with this topic
                expected_node_ids = [node["id"] for node in topic_nodes]
                
                test_queries.append({
                    "query_text": query_text,
                    "expected_nodes": expected_node_ids,
                    "type": "topic",
                    "topic": topic
                })
        
        # Create content-based queries
        for i in range(min(num_queries - len(topics), len(test_nodes))):
            # Select a random node
            node = test_nodes[i]
            
            # Extract a portion of its content as a query
            content = node["content"]
            words = content.split()
            if len(words) >= 5:
                query_words = words[:5]  # Take first 5 words
                query_text = " ".join(query_words)
                
                # The source node should be in the results
                expected_node_ids = [node["id"]]
                
                # Also include nodes with the same topic
                topic = node.get("metadata", {}).get("topic", "unknown")
                expected_node_ids.extend([
                    n["id"] for n in test_nodes 
                    if n["id"] != node["id"] and 
                    n.get("metadata", {}).get("topic", "") == topic
                ])
                
                test_queries.append({
                    "query_text": query_text,
                    "expected_nodes": expected_node_ids[:5],  # Limit to top 5 expected results
                    "type": "content",
                    "source_node": node["id"]
                })
        
        # Save test queries for reference
        queries_path = os.path.join(self.test_data_dir, "test_queries.json")
        with open(queries_path, 'w') as f:
            json.dump(test_queries, f, indent=2)
        
        logger.info(f"Generated {len(test_queries)} test queries")
        return test_queries
    
    def run_comparison_tests(self, 
                           test_queries: List[Dict[str, Any]],
                           k_values: List[int] = [1, 3, 5, 10]) -> BenchmarkResult:
        """
        Run comparative tests between standard and polar-temporal atlases.
        
        Args:
            test_queries: List of query data with expected results
            k_values: List of k values to test for retrieval
            
        Returns:
            BenchmarkResult with comparison metrics
        """
        logger.info("Running comparison tests")
        
        # Check if atlases are initialized
        if not self.standard_atlas or not self.polar_atlas:
            logger.error("Atlases not initialized. Call setup_atlases() first.")
            return None
        
        # Create benchmark result
        result = BenchmarkResult("Standard vs. Polar Atlas Comparison")
        
        # Metadata
        result.add_metadata("standard_atlas_nodes", len(self.standard_atlas.db.nodes))
        result.add_metadata("polar_atlas_nodes", len(self.polar_atlas.db.nodes))
        result.add_metadata("test_queries", len(test_queries))
        result.add_metadata("k_values", k_values)
        
        # Compare for different k values
        for k in k_values:
            logger.info(f"Testing with k={k}")
            
            # Performance metrics
            standard_query_times = []
            polar_query_times = []
            
            # Accuracy metrics
            standard_precision = []
            polar_precision = []
            standard_recall = []
            polar_recall = []
            
            # Individual query results for detailed analysis
            query_details = []
            
            # Run queries
            for query_data in test_queries:
                query_text = query_data["query_text"]
                expected_nodes = query_data["expected_nodes"]
                
                # Run query on standard atlas
                standard_results, standard_time = self.benchmark_runner.measure_execution_time(
                    self.standard_atlas.similarity_search, query_text, k=k
                )
                standard_query_times.append(standard_time)
                
                # Run query on polar atlas
                polar_results, polar_time = self.benchmark_runner.measure_execution_time(
                    self.polar_atlas.similarity_search, query_text, k=k
                )
                polar_query_times.append(polar_time)
                
                # Extract result node IDs
                standard_node_ids = []
                for doc, _ in standard_results:
                    node_id = self.standard_atlas.doc_id_to_node_id.get(doc.metadata.get("id"))
                    if node_id:
                        standard_node_ids.append(node_id)
                
                polar_node_ids = []
                for doc, _ in polar_results:
                    node_id = self.polar_atlas.doc_id_to_node_id.get(doc.metadata.get("id"))
                    if node_id:
                        polar_node_ids.append(node_id)
                
                # Calculate precision and recall
                if expected_nodes:
                    # Precision: fraction of retrieved items that are relevant
                    standard_prec = len(set(standard_node_ids) & set(expected_nodes)) / len(standard_node_ids) if standard_node_ids else 0
                    polar_prec = len(set(polar_node_ids) & set(expected_nodes)) / len(polar_node_ids) if polar_node_ids else 0
                    
                    standard_precision.append(standard_prec)
                    polar_precision.append(polar_prec)
                    
                    # Recall: fraction of relevant items that are retrieved
                    standard_rec = len(set(standard_node_ids) & set(expected_nodes)) / len(expected_nodes) if expected_nodes else 0
                    polar_rec = len(set(polar_node_ids) & set(expected_nodes)) / len(expected_nodes) if expected_nodes else 0
                    
                    standard_recall.append(standard_rec)
                    polar_recall.append(polar_rec)
                    
                    # Add query details
                    query_details.append({
                        "query_text": query_text,
                        "query_type": query_data.get("type", "unknown"),
                        "expected_nodes": expected_nodes,
                        "standard_results": standard_node_ids,
                        "polar_results": polar_node_ids,
                        "standard_precision": standard_prec,
                        "polar_precision": polar_prec,
                        "standard_recall": standard_rec,
                        "polar_recall": polar_rec,
                        "standard_time": standard_time,
                        "polar_time": polar_time
                    })
            
            # Calculate average metrics
            avg_standard_time = sum(standard_query_times) / len(standard_query_times) if standard_query_times else 0
            avg_polar_time = sum(polar_query_times) / len(polar_query_times) if polar_query_times else 0
            
            avg_standard_precision = sum(standard_precision) / len(standard_precision) if standard_precision else 0
            avg_polar_precision = sum(polar_precision) / len(polar_precision) if polar_precision else 0
            
            avg_standard_recall = sum(standard_recall) / len(standard_recall) if standard_recall else 0
            avg_polar_recall = sum(polar_recall) / len(polar_recall) if polar_recall else 0
            
            # Calculate F1 scores
            avg_standard_f1 = 2 * (avg_standard_precision * avg_standard_recall) / (avg_standard_precision + avg_standard_recall) if (avg_standard_precision + avg_standard_recall) > 0 else 0
            avg_polar_f1 = 2 * (avg_polar_precision * avg_polar_recall) / (avg_polar_precision + avg_polar_recall) if (avg_polar_precision + avg_polar_recall) > 0 else 0
            
            # Add to results
            result.add_timing(f"standard_avg_query_time_k{k}", avg_standard_time)
            result.add_timing(f"polar_avg_query_time_k{k}", avg_polar_time)
            
            result.add_accuracy(f"standard_precision_k{k}", avg_standard_precision)
            result.add_accuracy(f"polar_precision_k{k}", avg_polar_precision)
            
            result.add_accuracy(f"standard_recall_k{k}", avg_standard_recall)
            result.add_accuracy(f"polar_recall_k{k}", avg_polar_recall)
            
            result.add_accuracy(f"standard_f1_k{k}", avg_standard_f1)
            result.add_accuracy(f"polar_f1_k{k}", avg_polar_f1)
            
            # Add speedup metrics
            speedup = avg_standard_time / avg_polar_time if avg_polar_time > 0 else float('inf')
            result.add_metric(f"query_speedup_k{k}", speedup)
            
            # Add accuracy improvement metrics
            precision_improvement = (avg_polar_precision - avg_standard_precision) / avg_standard_precision if avg_standard_precision > 0 else float('inf')
            result.add_metric(f"precision_improvement_k{k}", precision_improvement)
            
            recall_improvement = (avg_polar_recall - avg_standard_recall) / avg_standard_recall if avg_standard_recall > 0 else float('inf')
            result.add_metric(f"recall_improvement_k{k}", recall_improvement)
            
            f1_improvement = (avg_polar_f1 - avg_standard_f1) / avg_standard_f1 if avg_standard_f1 > 0 else float('inf')
            result.add_metric(f"f1_improvement_k{k}", f1_improvement)
        
        # Add detailed query results
        result.comparison_data["query_details"] = query_details
        
        # Save results
        result_path = os.path.join(self.output_dir, "comparison_results.json")
        result.save_to_json(result_path)
        
        # Generate visualization
        self._generate_comparison_visualizations(result)
        
        logger.info(f"Comparison tests completed. Results saved to {result_path}")
        return result
    
    def _generate_comparison_visualizations(self, result: BenchmarkResult):
        """
        Generate visualizations of comparison results.
        
        Args:
            result: BenchmarkResult to visualize
        """
        logger.info("Generating comparison visualizations")
        
        # Extract k values from metrics
        k_values = []
        for key in result.timings.keys():
            if key.startswith("standard_avg_query_time_k"):
                k = key.split("_k")[1]
                k_values.append(k)
        
        # Performance comparison
        plt.figure(figsize=(10, 6))
        ind = np.arange(len(k_values))
        width = 0.35
        
        standard_times = [result.timings.get(f"standard_avg_query_time_k{k}", 0) for k in k_values]
        polar_times = [result.timings.get(f"polar_avg_query_time_k{k}", 0) for k in k_values]
        
        plt.bar(ind - width/2, standard_times, width, label='Standard Atlas')
        plt.bar(ind + width/2, polar_times, width, label='Polar Atlas')
        
        plt.xlabel('k Value')
        plt.ylabel('Average Query Time (seconds)')
        plt.title('Query Performance Comparison')
        plt.xticks(ind, k_values)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save performance chart
        performance_path = os.path.join(self.output_dir, "performance_comparison.png")
        plt.savefig(performance_path)
        plt.close()
        
        # Precision/Recall comparison
        plt.figure(figsize=(12, 8))
        
        # Create subplots
        fig, axs = plt.subplots(1, 2, figsize=(15, 6))
        
        # Precision plot
        standard_precision = [result.accuracy_metrics.get(f"standard_precision_k{k}", 0) for k in k_values]
        polar_precision = [result.accuracy_metrics.get(f"polar_precision_k{k}", 0) for k in k_values]
        
        axs[0].bar(ind - width/2, standard_precision, width, label='Standard Atlas')
        axs[0].bar(ind + width/2, polar_precision, width, label='Polar Atlas')
        axs[0].set_xlabel('k Value')
        axs[0].set_ylabel('Average Precision')
        axs[0].set_title('Precision Comparison')
        axs[0].set_xticks(ind)
        axs[0].set_xticklabels(k_values)
        axs[0].legend()
        axs[0].grid(True, linestyle='--', alpha=0.7)
        
        # Recall plot
        standard_recall = [result.accuracy_metrics.get(f"standard_recall_k{k}", 0) for k in k_values]
        polar_recall = [result.accuracy_metrics.get(f"polar_recall_k{k}", 0) for k in k_values]
        
        axs[1].bar(ind - width/2, standard_recall, width, label='Standard Atlas')
        axs[1].bar(ind + width/2, polar_recall, width, label='Polar Atlas')
        axs[1].set_xlabel('k Value')
        axs[1].set_ylabel('Average Recall')
        axs[1].set_title('Recall Comparison')
        axs[1].set_xticks(ind)
        axs[1].set_xticklabels(k_values)
        axs[1].legend()
        axs[1].grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save precision/recall chart
        accuracy_path = os.path.join(self.output_dir, "accuracy_comparison.png")
        plt.savefig(accuracy_path)
        plt.close()
        
        # F1 score comparison
        plt.figure(figsize=(10, 6))
        
        standard_f1 = [result.accuracy_metrics.get(f"standard_f1_k{k}", 0) for k in k_values]
        polar_f1 = [result.accuracy_metrics.get(f"polar_f1_k{k}", 0) for k in k_values]
        
        plt.bar(ind - width/2, standard_f1, width, label='Standard Atlas')
        plt.bar(ind + width/2, polar_f1, width, label='Polar Atlas')
        
        plt.xlabel('k Value')
        plt.ylabel('F1 Score')
        plt.title('F1 Score Comparison')
        plt.xticks(ind, k_values)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save F1 chart
        f1_path = os.path.join(self.output_dir, "f1_comparison.png")
        plt.savefig(f1_path)
        plt.close()
        
        logger.info("Comparison visualizations generated")


def run_comparative_tests(
    output_dir: str = "output/comparative_tests",
    test_data_path: Optional[str] = None,
    num_test_nodes: int = 100,
    embedding_service_type: str = "langchain"
) -> BenchmarkResult:
    """
    Run a complete comparative test suite.
    
    Args:
        output_dir: Directory to save test results
        test_data_path: Path to test data (if None, generates synthetic data)
        num_test_nodes: Number of test nodes to generate
        embedding_service_type: Type of embedding service to use
        
    Returns:
        BenchmarkResult with comparison metrics
    """
    logger.info(f"Starting comparative test suite")
    
    # Create comparative tester
    tester = ComparativeTester(
        output_dir=output_dir,
        embedding_service_type=embedding_service_type
    )
    
    # Set up test data
    test_nodes = tester.setup_test_data(
        source_data_path=test_data_path,
        num_test_nodes=num_test_nodes
    )
    
    # Set up atlases
    standard_atlas, polar_atlas = tester.setup_atlases(test_nodes)
    
    # Generate test queries
    test_queries = tester.generate_test_queries(test_nodes)
    
    # Run comparison tests
    result = tester.run_comparison_tests(test_queries)
    
    logger.info(f"Comparative test suite completed. Results saved to {output_dir}")
    return result


if __name__ == "__main__":
    # Example usage when run directly
    parser = argparse.ArgumentParser(description="Run comparative tests on Temporal-Spatial Memory System")
    parser.add_argument("--output-dir", type=str, default="output/comparative_tests", help="Directory to save test results")
    parser.add_argument("--test-data", type=str, default=None, help="Path to test data (if None, generates synthetic data)")
    parser.add_argument("--num-nodes", type=int, default=100, help="Number of test nodes to generate")
    parser.add_argument("--embedding-service", type=str, default="langchain", help="Embedding service type to use")
    
    args = parser.parse_args()
    
    run_comparative_tests(
        output_dir=args.output_dir,
        test_data_path=args.test_data,
        num_test_nodes=args.num_nodes,
        embedding_service_type=args.embedding_service
    ) 
"""
Performance benchmarks for the query engine and temporal-spatial index.

This script runs benchmarks to measure the performance of the query engine
and combined temporal-spatial index under various workloads.
"""

import sys
import os
import time
import random
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from datetime import datetime, timedelta

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tests.benchmarks.benchmark_framework import BenchmarkRunner
from src.query.query_engine import QueryEngine
from src.query.query import Query
from src.indexing.combined_index import TemporalSpatialIndex
from src.indexing.rtree import SpatialIndex
from src.core.node import Node
from src.core.coordinates import Coordinates

# Configure logger
logger = logging.getLogger(__name__)

class MockIndexManager:
    """Mock index manager for benchmarking."""
    
    def __init__(self, spatial_index: SpatialIndex, temporal_spatial_index: TemporalSpatialIndex):
        """
        Initialize the mock index manager.
        
        Args:
            spatial_index: The spatial index
            temporal_spatial_index: The combined temporal-spatial index
        """
        self.indices = {
            "spatial": spatial_index,
            "temporal": None,  # Not used directly
            "combined": temporal_spatial_index
        }
    
    def has_index(self, index_name: str) -> bool:
        """Check if an index exists."""
        return index_name in self.indices
    
    def get_index(self, index_name: str) -> Any:
        """Get an index by name."""
        return self.indices.get(index_name)

class MockNodeStore:
    """Mock node store for benchmarking."""
    
    def __init__(self, nodes: Dict[str, Node]):
        """
        Initialize the mock node store.
        
        Args:
            nodes: Dictionary of nodes
        """
        self.nodes = nodes
    
    def get_all_nodes(self) -> List[Node]:
        """Get all nodes."""
        return list(self.nodes.values())
    
    def get_node(self, node_id: str) -> Node:
        """Get a node by ID."""
        return self.nodes.get(node_id)

def generate_random_nodes(count: int = 10000) -> List[Node]:
    """
    Generate random nodes for benchmarking.
    
    Args:
        count: Number of nodes to generate
        
    Returns:
        List of generated nodes
    """
    nodes = []
    
    # Generate nodes with random coordinates and timestamps
    for i in range(count):
        # Generate random spatial coordinates
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        z = random.uniform(-100, 100)
        
        # Generate random timestamp within the last year
        now = time.time()
        year_ago = now - 365 * 24 * 3600
        timestamp = random.uniform(year_ago, now)
        
        # Create node
        node = Node(
            id=f"node_{i}",
            content=f"Test node {i}",
            coordinates=Coordinates(spatial=(x, y, z), temporal=timestamp)
        )
        
        nodes.append(node)
    
    return nodes

def setup_benchmark_data(node_count: int = 10000) -> Tuple[TemporalSpatialIndex, SpatialIndex, Dict[str, Node]]:
    """
    Set up data for benchmarking.
    
    Args:
        node_count: Number of nodes to generate
        
    Returns:
        Tuple of (combined_index, spatial_index, nodes_dict)
    """
    logger.info(f"Generating {node_count} random nodes for benchmarks...")
    
    # Generate random nodes
    nodes = generate_random_nodes(count=node_count)
    
    # Create indices
    spatial_index = SpatialIndex(dimension=3)
    combined_index = TemporalSpatialIndex(config={
        "temporal_bucket_size": 60,  # 1 hour
        "spatial_dimension": 3,
        "auto_tuning": False
    })
    
    # Build node dictionary
    nodes_dict = {node.id: node for node in nodes}
    
    logger.info("Loading nodes into indices...")
    
    # Load nodes into indices
    spatial_index.bulk_load(nodes)
    combined_index.bulk_load(nodes)
    
    logger.info("Benchmark data setup complete.")
    
    return combined_index, spatial_index, nodes_dict

def run_benchmarks():
    """Run all benchmarks."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create benchmark runner
    runner = BenchmarkRunner(
        name="Query Engine and Index Benchmarks",
        description="Performance benchmarks for query execution engine and combined temporal-spatial index"
    )
    
    # Set up benchmark data
    node_count = 10000
    combined_index, spatial_index, nodes_dict = setup_benchmark_data(node_count)
    
    # Create mock components
    index_manager = MockIndexManager(spatial_index, combined_index)
    node_store = MockNodeStore(nodes_dict)
    
    # Create query engine
    query_engine = QueryEngine(node_store, index_manager)
    
    # Run spatial index benchmarks
    runner.run_benchmark(
        name="Spatial Nearest Neighbor (10)",
        func=lambda: spatial_index.nearest((0, 0, 0), num_results=10),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "spatial_nearest"}
    )
    
    runner.run_benchmark(
        name="Spatial Nearest Neighbor (100)",
        func=lambda: spatial_index.nearest((0, 0, 0), num_results=100),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "spatial_nearest"}
    )
    
    # Prepare some point ranges for region queries
    small_range = ((0, 0, 0), (10, 10, 10))
    medium_range = ((-25, -25, -25), (25, 25, 25))
    large_range = ((-50, -50, -50), (50, 50, 50))
    
    runner.run_benchmark(
        name="Spatial Region Query (Small)",
        func=lambda: spatial_index.range_query(small_range[0], small_range[1]),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "spatial_region", "range_size": "small"}
    )
    
    runner.run_benchmark(
        name="Spatial Region Query (Medium)",
        func=lambda: spatial_index.range_query(medium_range[0], medium_range[1]),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "spatial_region", "range_size": "medium"}
    )
    
    runner.run_benchmark(
        name="Spatial Region Query (Large)",
        func=lambda: spatial_index.range_query(large_range[0], large_range[1]),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "spatial_region", "range_size": "large"}
    )
    
    # Run combined index benchmarks
    now = time.time()
    hour_ago = now - 3600
    day_ago = now - 24 * 3600
    week_ago = now - 7 * 24 * 3600
    month_ago = now - 30 * 24 * 3600
    
    runner.run_benchmark(
        name="Temporal Query (Hour)",
        func=lambda: combined_index.query(temporal_criteria={"start_time": hour_ago, "end_time": now}),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "temporal", "range": "hour"}
    )
    
    runner.run_benchmark(
        name="Temporal Query (Day)",
        func=lambda: combined_index.query(temporal_criteria={"start_time": day_ago, "end_time": now}),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "temporal", "range": "day"}
    )
    
    runner.run_benchmark(
        name="Temporal Query (Week)",
        func=lambda: combined_index.query(temporal_criteria={"start_time": week_ago, "end_time": now}),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "temporal", "range": "week"}
    )
    
    runner.run_benchmark(
        name="Combined Query (Hour + Small Region)",
        func=lambda: combined_index.query(
            temporal_criteria={"start_time": hour_ago, "end_time": now},
            spatial_criteria={"region": {"lower": small_range[0], "upper": small_range[1]}}
        ),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "combined", "range": "hour+small"}
    )
    
    runner.run_benchmark(
        name="Combined Query (Day + Medium Region)",
        func=lambda: combined_index.query(
            temporal_criteria={"start_time": day_ago, "end_time": now},
            spatial_criteria={"region": {"lower": medium_range[0], "upper": medium_range[1]}}
        ),
        iterations=100,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "combined", "range": "day+medium"}
    )
    
    runner.run_benchmark(
        name="Time Series Query (Week, 1-day intervals)",
        func=lambda: combined_index.query_time_series(
            start_time=week_ago,
            end_time=now,
            interval=24 * 3600  # 1 day
        ),
        iterations=50,
        warmup_iterations=5,
        metadata={"node_count": node_count, "query_type": "time_series", "range": "week", "interval": "day"}
    )
    
    # Run query engine benchmarks
    
    # Create mock queries
    spatial_query = Query(type=Query.SPATIAL, criteria={"point": (0, 0, 0), "distance": 10.0})
    temporal_query = Query(type=Query.TEMPORAL, criteria={"start_time": day_ago, "end_time": now})
    combined_query = Query(type=Query.COMBINED, criteria={
        "spatial": {"point": (0, 0, 0), "distance": 10.0},
        "temporal": {"start_time": day_ago, "end_time": now}
    })
    
    runner.run_benchmark(
        name="Query Engine - Spatial Query",
        func=lambda: query_engine.execute(spatial_query),
        iterations=50,
        warmup_iterations=5,
        metadata={"node_count": node_count, "query_type": "spatial"}
    )
    
    runner.run_benchmark(
        name="Query Engine - Temporal Query",
        func=lambda: query_engine.execute(temporal_query),
        iterations=50,
        warmup_iterations=5,
        metadata={"node_count": node_count, "query_type": "temporal"}
    )
    
    runner.run_benchmark(
        name="Query Engine - Combined Query",
        func=lambda: query_engine.execute(combined_query),
        iterations=50,
        warmup_iterations=5,
        metadata={"node_count": node_count, "query_type": "combined"}
    )
    
    # Run query engine cache benchmarks
    runner.run_benchmark(
        name="Query Engine - Cached Query",
        setup=lambda: query_engine.execute(spatial_query, options={"use_cache": True}),
        func=lambda: query_engine.execute(spatial_query, options={"use_cache": True}),
        iterations=1000,
        warmup_iterations=10,
        metadata={"node_count": node_count, "query_type": "cached"}
    )
    
    # Save results and generate report
    runner.save_results("query_engine_benchmarks.json")
    report_path = runner.generate_report()
    
    logger.info(f"Benchmark report generated: {report_path}")

if __name__ == "__main__":
    run_benchmarks() 
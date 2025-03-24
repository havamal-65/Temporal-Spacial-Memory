#!/usr/bin/env python3
"""
Basic test script for SpatialIndex functionality.
"""

import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.indexing.rtree import SpatialIndex, SplitStrategy, DistanceMetric
from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

def main():
    """Run basic tests to validate the SpatialIndex functionality."""
    print("Creating SpatialIndex...")
    index = SpatialIndex(dimension=3, in_memory=True)
    
    print("Creating test nodes...")
    nodes = []
    base_time = datetime(2023, 1, 1)  # Base time: January 1, 2023
    
    for x in range(5):
        for y in range(5):
            node_id = f"node_{x}_{y}"
            
            # Create a timestamp with increasing hour values
            timestamp = datetime(
                year=base_time.year,
                month=base_time.month,
                day=base_time.day,
                hour=base_time.hour + x,
                minute=base_time.minute + y
            )
            
            coords = Coordinates(
                spatial=SpatialCoordinate((float(x), float(y), 0.0)),
                temporal=TemporalCoordinate(timestamp=timestamp)
            )
            node = Node(id=node_id, coordinates=coords, data={"x": x, "y": y})
            nodes.append(node)
    
    print(f"Created {len(nodes)} test nodes")
    
    print("Inserting nodes into index...")
    for node in nodes:
        index.insert(node)
    
    print(f"Index now contains {index.count()} nodes")
    
    # Test nearest neighbor
    print("\nTesting nearest neighbor...")
    query_point = (2.5, 2.5, 0.0)
    nearest = index.nearest(query_point, num_results=5)
    print(f"Found {len(nearest)} nearest nodes to {query_point}:")
    for node in nearest:
        print(f"  Node {node.id}: {node.coordinates.spatial.dimensions}")
    
    # Test range query
    print("\nTesting range query...")
    lower_bounds = (1.0, 1.0, 0.0)
    upper_bounds = (3.0, 3.0, 0.0)
    in_range = index.range_query(lower_bounds, upper_bounds)
    print(f"Found {len(in_range)} nodes in range {lower_bounds} to {upper_bounds}:")
    for node in in_range:
        print(f"  Node {node.id}: {node.coordinates.spatial.dimensions}")
    
    # Test bulk loading
    print("\nTesting clear and bulk load...")
    index.clear()
    print(f"After clearing, index contains {index.count()} nodes")
    
    index.bulk_load(nodes)
    print(f"After bulk loading, index contains {index.count()} nodes")
    
    # Get statistics
    print("\nSpatialIndex statistics:")
    stats = index.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 
"""
Basic usage example for the Temporal-Spatial Knowledge Database.

This example demonstrates how to create, store, and query nodes with 
spatial and temporal coordinates.
"""

import os
import shutil
from datetime import datetime, timedelta
import random

from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
from src.storage.rocksdb_store import RocksDBNodeStore
from src.indexing.combined_index import CombinedIndex


def create_sample_nodes(num_nodes=100):
    """Create sample nodes with random spatial and temporal coordinates."""
    nodes = []
    
    # Base time for temporal coordinates
    base_time = datetime.now()
    
    for i in range(num_nodes):
        # Generate random 3D spatial coordinates
        spatial = SpatialCoordinate(dimensions=(
            random.uniform(-10, 10),  # x
            random.uniform(-10, 10),  # y
            random.uniform(-10, 10)   # z
        ))
        
        # Generate random temporal coordinate within the past year
        days_ago = random.randint(0, 365)
        timestamp = base_time - timedelta(days=days_ago, 
                                          hours=random.randint(0, 23),
                                          minutes=random.randint(0, 59))
        temporal = TemporalCoordinate(timestamp=timestamp)
        
        # Create coordinates with both spatial and temporal components
        coordinates = Coordinates(spatial=spatial, temporal=temporal)
        
        # Create a node with these coordinates and some sample data
        node = Node(
            coordinates=coordinates,
            data={
                "name": f"Node {i}",
                "value": random.random() * 100,
                "category": random.choice(["A", "B", "C", "D"]),
                "is_important": random.choice([True, False])
            }
        )
        
        nodes.append(node)
    
    return nodes


def main():
    # Create db directory if it doesn't exist
    db_path = "example_db"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # Initialize the database
    print("Initializing the database...")
    with RocksDBNodeStore(db_path=db_path) as store:
        # Create the combined index
        index = CombinedIndex()
        
        # Generate sample nodes
        print("Generating sample nodes...")
        nodes = create_sample_nodes(100)
        
        # Store the nodes and add them to the index
        print("Storing and indexing nodes...")
        for node in nodes:
            store.save(node)
            index.insert(node)
        
        print(f"Added {len(nodes)} nodes to the database")
        
        # Perform some example queries
        print("\n--- Spatial Queries ---")
        origin = (0.0, 0.0, 0.0)
        nearest_nodes = index.spatial_nearest(origin, num_results=5)
        print(f"5 nodes nearest to origin {origin}:")
        for i, node in enumerate(nearest_nodes, 1):
            spatial = node.coordinates.spatial
            distance = spatial.distance_to(SpatialCoordinate(dimensions=origin))
            print(f"  {i}. Node {node.id[:8]} at {spatial.dimensions} - Distance: {distance:.2f}")
        
        print("\n--- Temporal Queries ---")
        now = datetime.now()
        last_week = now - timedelta(days=7)
        temporal_nodes = index.temporal_range(last_week, now)
        print(f"Nodes from last week ({last_week.date()} to {now.date()}):")
        for i, node in enumerate(temporal_nodes[:5], 1):
            timestamp = node.coordinates.temporal.timestamp
            print(f"  {i}. Node {node.id[:8]} at {timestamp}")
        
        if len(temporal_nodes) > 5:
            print(f"  ... and {len(temporal_nodes) - 5} more")
        
        print("\n--- Combined Queries ---")
        combined_nodes = index.combined_query(
            spatial_point=origin,
            temporal_range=(now - timedelta(days=30), now),
            num_results=5
        )
        print(f"Nodes near origin within the last 30 days:")
        for i, node in enumerate(combined_nodes, 1):
            spatial = node.coordinates.spatial
            temporal = node.coordinates.temporal
            print(f"  {i}. Node {node.id[:8]} at {spatial.dimensions} on {temporal.timestamp.date()}")
    
    print("\nExample completed successfully. Database stored at:", db_path)


if __name__ == "__main__":
    main() 
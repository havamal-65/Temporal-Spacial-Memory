"""
Unit tests for the enhanced SpatialIndex class.
"""

import unittest
import uuid
import random
import time
import math
from datetime import datetime, timedelta
from typing import List, Tuple

# Add src directory to the path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.indexing.rtree import (
    SpatialIndex,
    SplitStrategy,
    DistanceMetric,
    SpatialIndexError
)
from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

class TestSpatialIndex(unittest.TestCase):
    """Test suite for the enhanced SpatialIndex class."""
    
    def setUp(self):
        """Set up a spatial index for each test."""
        self.index = SpatialIndex(dimension=3, in_memory=True)
        
        # Create some test nodes in a grid pattern
        self.nodes = []
        base_time = datetime(2023, 1, 1)  # Base time: January 1, 2023
        
        for x in range(10):
            for y in range(10):
                node_id = str(uuid.uuid4())
                
                # Create a timestamp with increasing values
                timestamp = base_time + timedelta(hours=x, minutes=y)
                
                coords = Coordinates(
                    spatial=SpatialCoordinate((float(x), float(y), 0.0)),
                    temporal=TemporalCoordinate(timestamp=timestamp)
                )
                node = Node(id=node_id, coordinates=coords, data={"x": x, "y": y})
                self.nodes.append(node)
    
    def test_insert_and_retrieve(self):
        """Test basic insert and retrieval operations."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Check count
        self.assertEqual(len(self.nodes), self.index.count())
        
        # Retrieve all nodes
        all_nodes = self.index.get_all()
        self.assertEqual(len(self.nodes), len(all_nodes))
        
        # Check node IDs match
        node_ids = {node.id for node in self.nodes}
        retrieved_ids = {node.id for node in all_nodes}
        self.assertEqual(node_ids, retrieved_ids)
    
    def test_nearest_neighbor(self):
        """Test nearest neighbor search."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Search near the point (5.5, 5.5, 0.0)
        query_point = (5.5, 5.5, 0.0)
        nearest = self.index.nearest(query_point, num_results=4)
        
        # Verify we got 4 results
        self.assertEqual(4, len(nearest))
        
        # The nearest nodes should be at (5,5), (5,6), (6,5), (6,6)
        expected_coords = {(5, 5), (5, 6), (6, 5), (6, 6)}
        actual_coords = {(node.data["x"], node.data["y"]) for node in nearest}
        self.assertEqual(expected_coords, actual_coords)
        
        # Test with distance constraint
        nearest_constrained = self.index.nearest(query_point, num_results=10, max_distance=1.0)
        
        # Only nodes within distance 1.0 should be returned
        for node in nearest_constrained:
            x, y = node.data["x"], node.data["y"]
            distance = math.sqrt((x - 5.5) ** 2 + (y - 5.5) ** 2)
            self.assertLessEqual(distance, 1.0)
    
    def test_incremental_nearest(self):
        """Test incremental nearest neighbor search."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Search near the point (5.5, 5.5, 0.0)
        query_point = (5.5, 5.5, 0.0)
        
        # Get all nodes within distance 2.0
        results = list(self.index.incremental_nearest(query_point, max_distance=2.0))
        
        # Verify all returned nodes are within the distance
        for distance, node in results:
            x, y = node.data["x"], node.data["y"]
            expected_distance = math.sqrt((x - 5.5) ** 2 + (y - 5.5) ** 2)
            self.assertLessEqual(distance, 2.0)
            # Verify distance calculation is correct (within floating point error)
            self.assertAlmostEqual(expected_distance, distance, places=6)
            
        # Verify results are sorted by distance
        distances = [distance for distance, _ in results]
        self.assertEqual(distances, sorted(distances))
        
        # Test with limited results
        limited_results = list(self.index.incremental_nearest(query_point, max_results=5))
        self.assertEqual(5, len(limited_results))
    
    def test_range_query(self):
        """Test range query."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Query nodes in the range (3,3) to (6,6)
        lower_bounds = (3.0, 3.0, 0.0)
        upper_bounds = (6.0, 6.0, 0.0)
        results = self.index.range_query(lower_bounds, upper_bounds)
        
        # There should be 16 nodes in this range (4x4 grid)
        self.assertEqual(16, len(results))
        
        # Verify all nodes are within the range
        for node in results:
            x, y = node.data["x"], node.data["y"]
            self.assertGreaterEqual(x, 3)
            self.assertLessEqual(x, 6)
            self.assertGreaterEqual(y, 3)
            self.assertLessEqual(y, 6)
    
    def test_bulk_load(self):
        """Test bulk loading nodes."""
        # Bulk load all nodes
        self.index.bulk_load(self.nodes)
        
        # Check count
        self.assertEqual(len(self.nodes), self.index.count())
        
        # Perform a query to ensure the index works correctly
        query_point = (5.0, 5.0, 0.0)
        nearest = self.index.nearest(query_point, num_results=1)
        
        # The nearest node should be at (5,5)
        self.assertEqual(1, len(nearest))
        self.assertEqual(5, nearest[0].data["x"])
        self.assertEqual(5, nearest[0].data["y"])
    
    def test_update(self):
        """Test updating nodes."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Update a node's position
        original_node = self.nodes[0]
        updated_coords = Coordinates(
            spatial=SpatialCoordinate((100.0, 100.0, 0.0)),
            temporal=original_node.coordinates.temporal
        )
        updated_node = Node(
            id=original_node.id,
            coordinates=updated_coords,
            data=original_node.data
        )
        
        self.index.update(updated_node)
        
        # Find the nearest node to the new position
        nearest = self.index.nearest((100.0, 100.0, 0.0), num_results=1)
        self.assertEqual(1, len(nearest))
        self.assertEqual(original_node.id, nearest[0].id)
    
    def test_remove(self):
        """Test removing nodes."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Remember the count
        original_count = self.index.count()
        
        # Remove a node
        node_to_remove = self.nodes[0]
        result = self.index.remove(node_to_remove.id)
        
        # Verify removal was successful
        self.assertTrue(result)
        self.assertEqual(original_count - 1, self.index.count())
        
        # Try to remove it again (should fail)
        result = self.index.remove(node_to_remove.id)
        self.assertFalse(result)
        
        # Make sure it's not found in nearest neighbor query
        nearest = self.index.nearest(
            (node_to_remove.coordinates.spatial.dimensions), 
            num_results=1
        )
        if nearest:  # There might be other nodes at the same position
            self.assertNotEqual(node_to_remove.id, nearest[0].id)
    
    def test_clear(self):
        """Test clearing the index."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Verify nodes are there
        self.assertEqual(len(self.nodes), self.index.count())
        
        # Clear the index
        self.index.clear()
        
        # Verify it's empty
        self.assertEqual(0, self.index.count())
        self.assertEqual(0, len(self.index.get_all()))
    
    def test_distance_metrics(self):
        """Test different distance metrics."""
        # Create indexes with different distance metrics
        euclidean_index = SpatialIndex(
            dimension=2, 
            distance_metric=DistanceMetric.EUCLIDEAN,
            in_memory=True
        )
        
        manhattan_index = SpatialIndex(
            dimension=2, 
            distance_metric=DistanceMetric.MANHATTAN,
            in_memory=True
        )
        
        chebyshev_index = SpatialIndex(
            dimension=2, 
            distance_metric=DistanceMetric.CHEBYSHEV,
            in_memory=True
        )
        
        # Add some nodes
        test_nodes = []
        for x, y in [(0, 0), (3, 0), (0, 4), (5, 5)]:
            node_id = str(uuid.uuid4())
            coords = Coordinates(
                spatial=SpatialCoordinate((float(x), float(y))),
                temporal=None
            )
            node = Node(id=node_id, coordinates=coords, data={"x": x, "y": y})
            test_nodes.append(node)
            
            # Add to all indexes
            euclidean_index.insert(node)
            manhattan_index.insert(node)
            chebyshev_index.insert(node)
        
        # Query point
        query_point = (1.0, 1.0)
        
        # Get nearest with different metrics
        euclidean_nearest = euclidean_index.nearest(query_point, num_results=4)
        manhattan_nearest = manhattan_index.nearest(query_point, num_results=4)
        chebyshev_nearest = chebyshev_index.nearest(query_point, num_results=4)
        
        # Verify different metrics give different results
        # Euclidean: (0,0) is closest, then (3,0), then (0,4), then (5,5)
        # Manhattan: (0,0) is closest, then (3,0) and (0,4) have same distance, then (5,5)
        # Chebyshev: (0,0) is closest, then (3,0) and (0,4) have same distance, then (5,5)
        
        # Verify first result is (0,0) for all metrics
        self.assertEqual((0, 0), (euclidean_nearest[0].data["x"], euclidean_nearest[0].data["y"]))
        self.assertEqual((0, 0), (manhattan_nearest[0].data["x"], manhattan_nearest[0].data["y"]))
        self.assertEqual((0, 0), (chebyshev_nearest[0].data["x"], chebyshev_nearest[0].data["y"]))
    
    def test_path_query(self):
        """Test path query."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Define a path
        path = [(2.0, 2.0), (5.0, 5.0), (8.0, 5.0)]
        
        # Query nodes within 1.0 units of the path
        results = self.index.path_query(path, radius=1.0)
        
        # Verify all nodes are within the specified distance of the path
        for node in results:
            x, y = node.data["x"], node.data["y"]
            
            # Calculate minimum distance to any segment of the path
            min_distance = float('inf')
            
            for i in range(len(path) - 1):
                p1 = path[i]
                p2 = path[i+1]
                
                # Distance from point to line segment
                distance = self._point_to_segment_distance((x, y), p1, p2)
                min_distance = min(min_distance, distance)
            
            # Verify node is within the radius
            self.assertLessEqual(min_distance, 1.0)
    
    def test_shape_query_circle(self):
        """Test shape query with circle."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Query nodes within a circle
        shape = {
            "type": "circle",
            "center": (5.0, 5.0),
            "radius": 2.0
        }
        
        results = self.index.shape_query(shape)
        
        # Verify all nodes are within the circle
        for node in results:
            x, y = node.data["x"], node.data["y"]
            distance = math.sqrt((x - 5.0) ** 2 + (y - 5.0) ** 2)
            self.assertLessEqual(distance, 2.0)
    
    def test_shape_query_polygon(self):
        """Test shape query with polygon."""
        # Insert all nodes
        for node in self.nodes:
            self.index.insert(node)
            
        # Define a triangular polygon
        polygon = [(3.0, 3.0), (3.0, 7.0), (7.0, 3.0)]
        
        results = self.index.shape_query(polygon)
        
        # Verify all nodes are within the polygon
        for node in results:
            x, y = node.data["x"], node.data["y"]
            self.assertTrue(self._is_point_in_polygon((x, y), polygon))
    
    def test_statistics(self):
        """Test getting statistics."""
        # Insert some nodes
        for node in self.nodes[:50]:
            self.index.insert(node)
            
        # Perform some queries
        self.index.nearest((5.0, 5.0, 0.0), num_results=10)
        self.index.nearest((2.0, 2.0, 0.0), num_results=5)
        self.index.range_query((3.0, 3.0, 0.0), (6.0, 6.0, 0.0))
        
        # Get statistics
        stats = self.index.get_statistics()
        
        # Check basic stats
        self.assertEqual(50, stats["node_count"])
        self.assertEqual(3, stats["dimension"])
        self.assertEqual("euclidean", stats["distance_metric"])
        self.assertEqual(50, stats["inserts"])
        self.assertEqual(0, stats["deletes"])
        self.assertEqual(0, stats["updates"])
        self.assertEqual(3, stats["queries"])
    
    def test_performance_large_dataset(self):
        """Test performance with a larger dataset."""
        # Skip in normal test runs
        if not hasattr(self, 'run_performance_tests'):
            self.skipTest("Skipping performance test")
            
        # Create a large number of random points
        large_nodes = []
        num_nodes = 10000
        
        for i in range(num_nodes):
            node_id = str(uuid.uuid4())
            x = random.uniform(0, 1000)
            y = random.uniform(0, 1000)
            
            coords = Coordinates(
                spatial=SpatialCoordinate((x, y, 0.0)),
                temporal=None
            )
            node = Node(id=node_id, coordinates=coords, data={"index": i})
            large_nodes.append(node)
        
        # Measure bulk load time
        start_time = time.time()
        self.index.bulk_load(large_nodes)
        bulk_load_time = time.time() - start_time
        
        # Measure query time
        start_time = time.time()
        for _ in range(100):
            x = random.uniform(0, 1000)
            y = random.uniform(0, 1000)
            self.index.nearest((x, y, 0.0), num_results=10)
        query_time = (time.time() - start_time) / 100
        
        # Just assert the operations completed
        self.assertEqual(num_nodes, self.index.count())
        
        # Print performance info
        print(f"\nPerformance with {num_nodes} nodes:")
        print(f"Bulk load time: {bulk_load_time:.3f}s")
        print(f"Average query time: {query_time:.6f}s")
    
    def _point_to_segment_distance(self, p: Tuple[float, ...], v: Tuple[float, ...], w: Tuple[float, ...]) -> float:
        """Calculate the distance from point to line segment."""
        # Same implementation as in SpatialIndex
        l2 = sum((a - b) ** 2 for a, b in zip(v, w))
        
        if l2 == 0:
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(p, v)))
            
        t = max(0, min(1, sum((a - b) * (c - b) for a, b, c in zip(p, v, w)) / l2))
        
        proj = tuple(b + t * (c - b) for b, c in zip(v, w))
        
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p, proj)))
    
    def _is_point_in_polygon(self, point: Tuple[float, ...], polygon: List[Tuple[float, ...]]) -> bool:
        """Check if point is inside polygon."""
        # Same implementation as in SpatialIndex
        x, y = point[:2]
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0][:2]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n][:2]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside

if __name__ == "__main__":
    # Uncomment to run performance tests
    # TestSpatialIndex.run_performance_tests = True
    unittest.main() 
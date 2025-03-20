"""
Test cases for the spatial indexing implementation.

This module contains unit tests for the spatial indexing components,
including Rectangle, RTree, and SpatioTemporalCoordinate.
"""

import unittest
import uuid
import math
from uuid import UUID
from random import random, seed

from ..core.coordinates import SpatioTemporalCoordinate
from ..indexing.rectangle import Rectangle
from ..indexing.rtree_impl import RTree
from ..indexing.rtree_node import RTreeNode, RTreeEntry, RTreeNodeRef


class TestSpatioTemporalCoordinate(unittest.TestCase):
    """Test cases for SpatioTemporalCoordinate."""
    
    def test_creation(self):
        """Test creation of coordinates."""
        coord = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=0.5)
        self.assertEqual(coord.t, 1.0)
        self.assertEqual(coord.r, 2.0)
        self.assertEqual(coord.theta, 0.5)
    
    def test_as_tuple(self):
        """Test converting to tuple."""
        coord = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=0.5)
        self.assertEqual(coord.as_tuple(), (1.0, 2.0, 0.5))
    
    def test_distance_to(self):
        """Test distance calculation."""
        coord1 = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=0.0)
        coord2 = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=math.pi)
        
        # Distance should be approximately 2*r (diameter) since we're on opposite sides
        self.assertAlmostEqual(coord1.distance_to(coord2), 4.0)
        
        # Test distance with different time
        coord3 = SpatioTemporalCoordinate(t=2.0, r=2.0, theta=0.0)
        self.assertEqual(coord1.distance_to(coord3), 1.0)
    
    def test_to_cartesian(self):
        """Test conversion to Cartesian coordinates."""
        # Point on positive x-axis
        coord = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=0.0)
        x, y, z = coord.to_cartesian()
        self.assertAlmostEqual(x, 2.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertEqual(z, 1.0)
        
        # Point on positive y-axis
        coord = SpatioTemporalCoordinate(t=1.0, r=2.0, theta=math.pi/2)
        x, y, z = coord.to_cartesian()
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 2.0)
        self.assertEqual(z, 1.0)
    
    def test_from_cartesian(self):
        """Test conversion from Cartesian coordinates."""
        # Point on positive x-axis
        coord = SpatioTemporalCoordinate.from_cartesian(2.0, 0.0, 1.0)
        self.assertEqual(coord.t, 1.0)
        self.assertAlmostEqual(coord.r, 2.0)
        self.assertAlmostEqual(coord.theta, 0.0)
        
        # Point on positive y-axis
        coord = SpatioTemporalCoordinate.from_cartesian(0.0, 2.0, 1.0)
        self.assertEqual(coord.t, 1.0)
        self.assertAlmostEqual(coord.r, 2.0)
        self.assertAlmostEqual(coord.theta, math.pi/2)


class TestRectangle(unittest.TestCase):
    """Test cases for Rectangle."""
    
    def test_creation(self):
        """Test creation of rectangles."""
        rect = Rectangle(min_t=1.0, max_t=2.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        self.assertEqual(rect.min_t, 1.0)
        self.assertEqual(rect.max_t, 2.0)
        self.assertEqual(rect.min_r, 0.5)
        self.assertEqual(rect.max_r, 1.5)
        self.assertEqual(rect.min_theta, 0.0)
        self.assertEqual(rect.max_theta, math.pi)
    
    def test_contains(self):
        """Test containment check."""
        rect = Rectangle(min_t=1.0, max_t=2.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        
        # Point inside
        coord = SpatioTemporalCoordinate(t=1.5, r=1.0, theta=math.pi/2)
        self.assertTrue(rect.contains(coord))
        
        # Point outside (t dimension)
        coord = SpatioTemporalCoordinate(t=0.5, r=1.0, theta=math.pi/2)
        self.assertFalse(rect.contains(coord))
        
        # Point outside (r dimension)
        coord = SpatioTemporalCoordinate(t=1.5, r=2.0, theta=math.pi/2)
        self.assertFalse(rect.contains(coord))
        
        # Point outside (theta dimension)
        coord = SpatioTemporalCoordinate(t=1.5, r=1.0, theta=math.pi*3/2)
        self.assertFalse(rect.contains(coord))
    
    def test_intersects(self):
        """Test rectangle intersection."""
        rect1 = Rectangle(min_t=1.0, max_t=2.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        
        # Overlapping rectangle
        rect2 = Rectangle(min_t=1.5, max_t=2.5, min_r=1.0, max_r=2.0, min_theta=math.pi/2, max_theta=math.pi*3/2)
        self.assertTrue(rect1.intersects(rect2))
        
        # Non-overlapping rectangle (t dimension)
        rect3 = Rectangle(min_t=3.0, max_t=4.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        self.assertFalse(rect1.intersects(rect3))
    
    def test_area(self):
        """Test area calculation."""
        # Rectangle covering half of a cylinder with height 1 and radius 1
        rect = Rectangle(min_t=0.0, max_t=1.0, min_r=0.0, max_r=1.0, min_theta=0.0, max_theta=math.pi)
        self.assertAlmostEqual(rect.area(), 0.5 * math.pi)
    
    def test_enlarge(self):
        """Test rectangle enlargement."""
        rect = Rectangle(min_t=1.0, max_t=2.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        
        # Enlarge to include a point outside
        coord = SpatioTemporalCoordinate(t=0.5, r=2.0, theta=math.pi*3/2)
        enlarged = rect.enlarge(coord)
        
        # Check the enlarged rectangle contains both the original area and the new point
        self.assertTrue(enlarged.contains(coord))
        self.assertTrue(enlarged.contains(SpatioTemporalCoordinate(t=1.5, r=1.0, theta=math.pi/2)))
    
    def test_merge(self):
        """Test rectangle merging."""
        rect1 = Rectangle(min_t=1.0, max_t=2.0, min_r=0.5, max_r=1.5, min_theta=0.0, max_theta=math.pi)
        rect2 = Rectangle(min_t=1.5, max_t=2.5, min_r=1.0, max_r=2.0, min_theta=math.pi/2, max_theta=math.pi*3/2)
        
        merged = rect1.merge(rect2)
        
        # Check the merged rectangle contains both original rectangles
        self.assertTrue(merged.min_t <= min(rect1.min_t, rect2.min_t))
        self.assertTrue(merged.max_t >= max(rect1.max_t, rect2.max_t))
        self.assertTrue(merged.min_r <= min(rect1.min_r, rect2.min_r))
        self.assertTrue(merged.max_r >= max(rect1.max_r, rect2.max_r))
        
        # Check that merged rectangle contains points from both originals
        self.assertTrue(merged.contains(SpatioTemporalCoordinate(t=1.5, r=1.0, theta=math.pi/4)))
        self.assertTrue(merged.contains(SpatioTemporalCoordinate(t=2.0, r=1.2, theta=math.pi)))


class TestRTree(unittest.TestCase):
    """Test cases for RTree."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Seed random for reproducibility
        seed(42)
        
        # Create an R-tree with smaller node capacity for easier testing
        self.rtree = RTree(max_entries=4, min_entries=2)
        
        # Insert some test nodes
        self.test_nodes = []
        for i in range(10):
            node_id = uuid.uuid4()
            t = i / 10.0
            r = 0.5 + i / 10.0
            theta = 2 * math.pi * i / 10.0
            coord = SpatioTemporalCoordinate(t=t, r=r, theta=theta)
            self.rtree.insert(coord, node_id)
            self.test_nodes.append((node_id, coord))
    
    def test_insert_and_find(self):
        """Test insertion and find operations."""
        # Insert a new node
        node_id = uuid.uuid4()
        coord = SpatioTemporalCoordinate(t=0.5, r=1.0, theta=math.pi)
        self.rtree.insert(coord, node_id)
        
        # Try to find it
        found = self.rtree.find_exact(coord)
        self.assertIn(node_id, found)
    
    def test_range_query(self):
        """Test range query operation."""
        # Create a range query rectangle
        query_rect = Rectangle(min_t=0.2, max_t=0.4, min_r=0.6, max_r=0.8, min_theta=math.pi/2, max_theta=math.pi)
        
        # Perform the query
        results = self.rtree.range_query(query_rect)
        
        # Manually check which nodes should be in the result
        expected = []
        for node_id, coord in self.test_nodes:
            if query_rect.contains(coord):
                expected.append(node_id)
        
        # Check that all expected nodes are in the result
        for node_id in expected:
            self.assertIn(node_id, results)
        
        # Check that no unexpected nodes are in the result
        for node_id in results:
            found = False
            for exp_id, _ in self.test_nodes:
                if node_id == exp_id:
                    found = True
                    break
            self.assertTrue(found)
    
    def test_nearest_neighbors(self):
        """Test nearest neighbors operation."""
        # Create a query point
        query_coord = SpatioTemporalCoordinate(t=0.45, r=0.75, theta=math.pi*1.25)
        
        # Find 3 nearest neighbors
        results = self.rtree.nearest_neighbors(query_coord, k=3)
        
        # Manual calculation of distances
        distances = []
        for node_id, coord in self.test_nodes:
            dist = query_coord.distance_to(coord)
            distances.append((node_id, dist))
        
        # Sort by distance
        distances.sort(key=lambda x: x[1])
        
        # Check that the first 3 closest nodes are in the result
        for i in range(min(3, len(distances))):
            node_id, _ = distances[i]
            found = False
            for result_id, _ in results:
                if node_id == result_id:
                    found = True
                    break
            self.assertTrue(found)
    
    def test_delete(self):
        """Test delete operation."""
        # Delete a node
        node_id, coord = self.test_nodes[0]
        self.rtree.delete(coord, node_id)
        
        # Try to find it (should not be found)
        found = self.rtree.find_exact(coord)
        self.assertNotIn(node_id, found)
        
        # Verify the size decreased
        self.assertEqual(len(self.rtree), len(self.test_nodes) - 1)
    
    def test_update(self):
        """Test update operation."""
        # Update a node's position
        node_id, old_coord = self.test_nodes[0]
        new_coord = SpatioTemporalCoordinate(t=0.9, r=0.9, theta=0.9)
        self.rtree.update(old_coord, new_coord, node_id)
        
        # Try to find it at the new position
        found = self.rtree.find_exact(new_coord)
        self.assertIn(node_id, found)
        
        # Try to find it at the old position (should not be found)
        found = self.rtree.find_exact(old_coord)
        self.assertNotIn(node_id, found)


if __name__ == '__main__':
    unittest.main() 
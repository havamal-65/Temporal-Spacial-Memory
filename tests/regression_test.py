"""
Regression Test Suite for Temporal-Spatial Memory System.

This module provides automated tests to ensure that changes don't break
existing functionality. It should be run after every significant change.
"""

import os
import sys
import unittest
import json
import tempfile
import shutil
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src directory to path to allow importing atlas components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import local modules
from models.narrative_atlas import NarrativeAtlas, Node
from coordinates import PolarTemporalCoordinate
from nl_parser import CoordinateFilters
from utils.embedding_service import create_embedding_service, MockEmbeddingService
from data_models import PolarTemporalCoordinate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("RegressionTest")


class RegressionTestSuite(unittest.TestCase):
    """
    Comprehensive regression test suite for Temporal-Spatial Memory System.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up resources that will be shared across all tests."""
        # Create a temporary directory for test data
        cls.test_dir = tempfile.mkdtemp(prefix="temporal_memory_regression_")
        
        # Create a mock embedding service for testing
        cls.embedding_service = MockEmbeddingService(dimension=4)
        
        # Sample coordinates for testing
        cls.sample_coordinates = [
            PolarTemporalCoordinate(r=0.1, theta=0.2, z=1, t=10, z_type="structural"),
            PolarTemporalCoordinate(r=0.3, theta=1.5, z=2, t=20, z_type="semantic"),
            PolarTemporalCoordinate(r=0.7, theta=3.0, z=3, t=30, z_type="temporal")
        ]
        
        # Sample content for nodes
        cls.sample_content = [
            "This is sample content for node 1.",
            "This is sample content for node 2 with different words.",
            "The third node has completely unique text content."
        ]
        
        logger.info(f"Test directory: {cls.test_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up shared resources after all tests have run."""
        # Remove the temporary directory
        shutil.rmtree(cls.test_dir)
        logger.info("Cleaned up test resources")
    
    def setUp(self):
        """Set up resources for each individual test."""
        # Create a fresh atlas for each test
        self.atlas_path = os.path.join(self.test_dir, f"atlas_{self._testMethodName}")
        os.makedirs(self.atlas_path, exist_ok=True)
        
        self.atlas = NarrativeAtlas(
            storage_path=self.atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Add some test nodes for each test
        self.test_nodes = []
        for i in range(3):
            node_id = f"test_node_{i}"
            node_type = "test"
            coordinates = self.sample_coordinates[i]
            content = self.sample_content[i]
            
            self.atlas.add_node(
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coordinates
            )
            
            self.test_nodes.append(node_id)
    
    def tearDown(self):
        """Clean up resources after each individual test."""
        # Clear the atlas
        if hasattr(self, 'atlas') and self.atlas:
            self.atlas = None
    
    def test_node_retrieval(self):
        """Test that nodes can be retrieved correctly."""
        # Check that all test nodes exist
        for node_id in self.test_nodes:
            node = self.atlas.get_node(node_id)
            self.assertIsNotNone(node, f"Node {node_id} not found")
            self.assertEqual(node.id, node_id, f"Node ID mismatch for {node_id}")
    
    def test_coordinate_properties(self):
        """Test that node coordinates have the correct properties."""
        for i, node_id in enumerate(self.test_nodes):
            node = self.atlas.get_node(node_id)
            self.assertIsNotNone(node.coordinates, f"Node {node_id} has no coordinates")
            
            # Check coordinate values
            expected_coords = self.sample_coordinates[i]
            self.assertEqual(node.coordinates.r, expected_coords.r, f"r mismatch for {node_id}")
            self.assertEqual(node.coordinates.theta, expected_coords.theta, f"theta mismatch for {node_id}")
            self.assertEqual(node.coordinates.z, expected_coords.z, f"z mismatch for {node_id}")
            self.assertEqual(node.coordinates.t, expected_coords.t, f"t mismatch for {node_id}")
            self.assertEqual(node.coordinates.z_type, expected_coords.z_type, f"z_type mismatch for {node_id}")
    
    def test_node_update(self):
        """Test that nodes can be updated correctly."""
        # Update a node's coordinates
        node_id = self.test_nodes[0]
        node = self.atlas.get_node(node_id)
        
        # Modify the coordinates
        node.coordinates.r = 0.9
        node.coordinates.theta = 4.5
        
        # Update the node
        self.atlas.update_node(node)
        
        # Retrieve the node again and check the updated coordinates
        updated_node = self.atlas.get_node(node_id)
        self.assertEqual(updated_node.coordinates.r, 0.9, "r was not updated")
        self.assertEqual(updated_node.coordinates.theta, 4.5, "theta was not updated")
    
    def test_node_removal(self):
        """Test that nodes can be removed correctly."""
        # Remove a node
        node_id = self.test_nodes[0]
        self.atlas.remove_node(node_id)
        
        # Check that the node is gone
        node = self.atlas.get_node(node_id)
        self.assertIsNone(node, f"Node {node_id} was not removed")
        
        # Check that other nodes still exist
        for node_id in self.test_nodes[1:]:
            node = self.atlas.get_node(node_id)
            self.assertIsNotNone(node, f"Node {node_id} was incorrectly removed")
    
    def test_similarity_search(self):
        """Test similarity search functionality."""
        # Perform a search
        results = self.atlas.similarity_search("sample content", k=2)
        
        # Check that we got the expected number of results
        self.assertEqual(len(results), 2, "Expected 2 search results")
        
        # Results should contain document objects and scores
        for doc, score in results:
            # Verify doc is a document object with content
            self.assertTrue(hasattr(doc, 'page_content'), "Result missing page_content")
            # Verify score is a float between 0 and 1
            self.assertIsInstance(score, float, "Score is not a float")
            self.assertTrue(0 <= score <= 1, "Score not in range 0-1")
    
    def test_filter_search(self):
        """Test search with coordinate filters."""
        # Create filters
        filters = CoordinateFilters(
            r_max=0.5,  # Only low-r nodes (more relevant)
            t_min=5,    # Time >= 5
            t_max=25    # Time <= 25
        )
        
        # Perform filtered search
        results = self.atlas.similarity_search_with_filters("sample content", filters, k=10)
        
        # Check that we got only nodes matching the filter
        for doc, _ in results:
            # Get node ID from doc metadata
            doc_id = doc.metadata.get('id')
            node_id = self.atlas.doc_id_to_node_id.get(doc_id)
            node = self.atlas.get_node(node_id)
            
            # Check filter conditions
            self.assertLessEqual(node.coordinates.r, 0.5, f"Node {node_id} has r > 0.5")
            self.assertGreaterEqual(node.coordinates.t, 5, f"Node {node_id} has t < 5")
            self.assertLessEqual(node.coordinates.t, 25, f"Node {node_id} has t > 25")
    
    def test_persistence(self):
        """Test that atlas data persists correctly."""
        # Create a new atlas with the same storage path
        new_atlas = NarrativeAtlas(
            storage_path=self.atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Check that the nodes are still there
        for node_id in self.test_nodes:
            node = new_atlas.get_node(node_id)
            self.assertIsNotNone(node, f"Node {node_id} not found after reload")
    
    def test_coordinate_transformations(self):
        """Test coordinate transformation functions."""
        # Test cartesian to polar transformation
        cartesian = [0.7071, 0.7071]  # 45 degrees in unit circle
        r, theta = self.atlas.transform_to_polar(cartesian)
        
        self.assertAlmostEqual(r, 1.0, places=4, msg="r value incorrect in transformation")
        self.assertAlmostEqual(theta, np.pi/4, places=4, msg="theta value incorrect in transformation")
        
        # Test polar to cartesian transformation
        r = 2.0
        theta = np.pi/3  # 60 degrees
        x, y = self.atlas.transform_to_cartesian(r, theta)
        
        self.assertAlmostEqual(x, r * np.cos(theta), places=4, msg="x value incorrect in transformation")
        self.assertAlmostEqual(y, r * np.sin(theta), places=4, msg="y value incorrect in transformation")
    
    def test_distance_calculations(self):
        """Test distance calculation in coordinate space."""
        # Create two nodes with different coordinates
        coord1 = PolarTemporalCoordinate(r=0.5, theta=1.0, z=1, t=10)
        coord2 = PolarTemporalCoordinate(r=0.8, theta=2.0, z=2, t=20)
        
        # Calculate Euclidean distance in polar-temporal space
        distance = self.atlas.calculate_coordinate_distance(coord1, coord2)
        
        # Verify result is positive
        self.assertGreater(distance, 0, "Distance calculation returned non-positive value")
        
        # Verify symmetry
        distance_reverse = self.atlas.calculate_coordinate_distance(coord2, coord1)
        self.assertAlmostEqual(distance, distance_reverse, places=4, 
                               msg="Distance calculation not symmetric")
    
    def test_temporal_decay(self):
        """Test temporal decay function for relevance scoring."""
        # Test decay at different time points
        current_t = 20
        
        # Node at same time should have no decay
        node_same_time = PolarTemporalCoordinate(r=0.5, theta=1.0, z=1, t=current_t)
        decay_same = self.atlas.apply_temporal_decay(node_same_time, current_t)
        self.assertAlmostEqual(decay_same, 1.0, places=4, 
                               msg="Decay incorrect for node at same time")
        
        # Node before current time should have decay < 1
        node_before = PolarTemporalCoordinate(r=0.5, theta=1.0, z=1, t=current_t - 10)
        decay_before = self.atlas.apply_temporal_decay(node_before, current_t)
        self.assertLess(decay_before, 1.0, "Decay incorrect for node before current time")
        
        # Node after current time should have decay < 1
        node_after = PolarTemporalCoordinate(r=0.5, theta=1.0, z=1, t=current_t + 10)
        decay_after = self.atlas.apply_temporal_decay(node_after, current_t)
        self.assertLess(decay_after, 1.0, "Decay incorrect for node after current time")
    
    def test_large_atlas_operations(self):
        """Test operations on a larger atlas."""
        # Create a separate atlas for this test
        large_atlas_path = os.path.join(self.test_dir, "large_atlas")
        os.makedirs(large_atlas_path, exist_ok=True)
        
        large_atlas = NarrativeAtlas(
            storage_path=large_atlas_path,
            embedding_service=self.embedding_service
        )
        
        # Add a larger number of nodes
        num_nodes = 50
        for i in range(num_nodes):
            node_id = f"large_node_{i}"
            content = f"Content for large node {i}"
            node_type = "large_test"
            
            # Create coordinates with patterns
            r = 0.1 + (i % 10) * 0.09  # 0.1 to 0.91
            theta = (i % 8) * np.pi / 4  # 0 to 7π/4
            z = 1 + (i % 3)  # 1 to 3
            t = i * 5  # 0, 5, 10, ...
            
            coordinates = PolarTemporalCoordinate(r=r, theta=theta, z=z, t=t)
            
            large_atlas.add_node(
                node_id=node_id,
                content=content,
                node_type=node_type,
                coordinates=coordinates
            )
        
        # Verify all nodes were added
        self.assertEqual(len(large_atlas.db.nodes), num_nodes, 
                         f"Expected {num_nodes} nodes in large atlas")
        
        # Test batch operations
        batch_ids = [f"large_node_{i}" for i in range(5)]
        batch_nodes = [large_atlas.get_node(node_id) for node_id in batch_ids]
        
        # Update all nodes in batch
        for node in batch_nodes:
            node.coordinates.r = 0.99
        
        # Update batch
        for node in batch_nodes:
            large_atlas.update_node(node)
        
        # Verify updates
        for node_id in batch_ids:
            node = large_atlas.get_node(node_id)
            self.assertAlmostEqual(node.coordinates.r, 0.99, places=4,
                                 msg=f"Batch update failed for {node_id}")


def run_regression_tests():
    """Run all regression tests."""
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(RegressionTestSuite)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests when script is executed directly
    success = run_regression_tests()
    
    # Use exit code based on test results
    sys.exit(0 if success else 1) 
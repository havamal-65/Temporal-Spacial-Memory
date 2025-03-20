"""
End-to-end integration tests for the Temporal-Spatial Knowledge Database.

These tests verify that all components of the system work together correctly.
"""

import math
import unittest
import tempfile
import shutil
import os
from uuid import uuid4

# Import with error handling
from src.core.node_v2 import Node

# Handle possibly missing dependencies
try:
    from src.core.coordinates import SpatioTemporalCoordinate
    COORDINATES_AVAILABLE = True
except ImportError:
    # Create a simple mock class
    class SpatioTemporalCoordinate:
        def __init__(self, t, r, theta):
            self.t = t
            self.r = r
            self.theta = theta
    COORDINATES_AVAILABLE = False

try:
    from src.indexing.rectangle import Rectangle
    RECTANGLE_AVAILABLE = True
except ImportError:
    # Create a simple mock class
    class Rectangle:
        def __init__(self, min_t, max_t, min_r, max_r, min_theta, max_theta):
            self.min_t = min_t
            self.max_t = max_t
            self.min_r = min_r
            self.max_r = max_r
            self.min_theta = min_theta
            self.max_theta = max_theta
    RECTANGLE_AVAILABLE = False

try:
    from src.delta.detector import ChangeDetector
    from src.delta.reconstruction import StateReconstructor
    DELTA_AVAILABLE = True
except ImportError:
    # Create mock classes if not available
    class ChangeDetector:
        def create_delta(self, *args, **kwargs):
            return None
        def apply_delta(self, *args, **kwargs):
            return None
    
    class StateReconstructor:
        def __init__(self, *args, **kwargs):
            pass
        def reconstruct_state(self, *args, **kwargs):
            return None
    DELTA_AVAILABLE = False

from tests.integration.test_environment import TestEnvironment
from tests.integration.test_data_generator import TestDataGenerator


@unittest.skipIf(not COORDINATES_AVAILABLE or not RECTANGLE_AVAILABLE or not DELTA_AVAILABLE,
                "Required dependencies not available")
class EndToEndTest(unittest.TestCase):
    def setUp(self):
        """Set up the test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.env = TestEnvironment(test_data_path=self.temp_dir, use_in_memory=True)
        self.generator = TestDataGenerator()
        self.env.setup()
        
    def tearDown(self):
        """Clean up after tests"""
        self.env.teardown()
        shutil.rmtree(self.temp_dir)
        
    def test_node_storage_and_retrieval(self):
        """Test basic node storage and retrieval"""
        # Generate test node
        node = self.generator.generate_node()
        
        # Store node
        self.env.node_store.put(node)
        
        # Retrieve node
        retrieved_node = self.env.node_store.get(node.id)
        
        # Verify node was retrieved correctly
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node.id, node.id)
        self.assertEqual(retrieved_node.content, node.content)
        self.assertEqual(retrieved_node.position, node.position)
        
    def test_spatial_index_queries(self):
        """Test spatial index queries"""
        # Generate cluster of nodes
        center = (50.0, 5.0, math.pi)
        nodes = self.generator.generate_node_cluster(
            center=center,
            radius=2.0,
            count=20
        )
        
        # Store nodes and build index
        for node in nodes:
            self.env.node_store.put(node)
            coord = SpatioTemporalCoordinate(*node.position)
            self.env.spatial_index.insert(coord, node.id)
            
        # Test nearest neighbor query
        test_coord = SpatioTemporalCoordinate(
            center[0], center[1], center[2])
        nearest = self.env.spatial_index.nearest_neighbors(
            test_coord, k=5)
        
        # Verify results
        self.assertEqual(len(nearest), 5)
        
        # Test range query
        query_rect = Rectangle(
            min_t=center[0] - 5, max_t=center[0] + 5,
            min_r=center[1] - 2, max_r=center[1] + 2,
            min_theta=center[2] - 0.5, max_theta=center[2] + 0.5
        )
        range_results = self.env.spatial_index.range_query(query_rect)
        
        # Verify range results
        self.assertTrue(len(range_results) > 0)
        
    def test_delta_chain_evolution(self):
        """Test delta chain evolution and reconstruction"""
        # Generate evolving node sequence
        base_position = (10.0, 1.0, 0.5 * math.pi)
        nodes = self.generator.generate_evolving_node_sequence(
            base_position=base_position,
            num_evolution_steps=10,
            time_step=1.0
        )
        
        # Store base node
        base_node = nodes[0]
        self.env.node_store.put(base_node)
        
        # Create detector and store
        detector = ChangeDetector()
        
        # Process evolution
        previous_content = base_node.content
        previous_delta_id = None
        
        for i in range(1, len(nodes)):
            node = nodes[i]
            # Detect changes
            delta = detector.create_delta(
                node_id=base_node.id,
                previous_content=previous_content,
                new_content=node.content,
                timestamp=node.position[0],
                previous_delta_id=previous_delta_id
            )
            
            # Store delta
            self.env.delta_store.store_delta(delta)
            
            # Update for next iteration
            previous_content = node.content
            previous_delta_id = delta.delta_id
            
        # Test state reconstruction
        reconstructor = StateReconstructor(self.env.delta_store)
        
        # Reconstruct at each time point
        for i in range(1, len(nodes)):
            node = nodes[i]
            reconstructed = reconstructor.reconstruct_state(
                node_id=base_node.id,
                origin_content=base_node.content,
                target_timestamp=node.position[0]
            )
            
            # Verify reconstruction
            self.assertEqual(reconstructed, node.content)
            
    def test_combined_query_functionality(self):
        """Test combined spatiotemporal queries"""
        # Generate time series of node clusters
        base_t = 10.0
        clusters = []
        
        # Create three clusters at different time points
        for t_offset in [0, 10, 20]:
            center = (base_t + t_offset, 5.0, math.pi / 2)
            nodes = self.generator.generate_node_cluster(
                center=center,
                radius=1.0,
                count=15,
                time_variance=0.5
            )
            clusters.append(nodes)
            
            # Store and index nodes
            for node in nodes:
                self.env.node_store.put(node)
                self.env.combined_index.insert(node)
        
        # Test temporal range query
        temporal_results = self.env.combined_index.query_temporal_range(
            min_t=base_t + 9,
            max_t=base_t + 11
        )
        
        # Should primarily get nodes from the second cluster
        self.assertTrue(len(temporal_results) > 0)
        
        # Test spatial range query
        spatial_results = self.env.combined_index.query_spatial_range(
            min_r=4.0,
            max_r=6.0,
            min_theta=math.pi/3,
            max_theta=2*math.pi/3
        )
        
        self.assertTrue(len(spatial_results) > 0)
        
        # Test combined query
        combined_results = self.env.combined_index.query(
            min_t=base_t + 9,
            max_t=base_t + 21,
            min_r=4.0,
            max_r=6.0, 
            min_theta=0,
            max_theta=math.pi
        )
        
        # Should get nodes primarily from second and third clusters
        self.assertTrue(len(combined_results) > 0)
        
        # Test nearest neighbors with temporal constraint
        nearest = self.env.combined_index.query_nearest(
            t=base_t + 10,
            r=5.0,
            theta=math.pi/2,
            k=5,
            max_distance=2.0
        )
        
        self.assertTrue(len(nearest) > 0)
        self.assertTrue(len(nearest) <= 5)  # May get fewer than k if max_distance is constraining


if __name__ == '__main__':
    unittest.main() 
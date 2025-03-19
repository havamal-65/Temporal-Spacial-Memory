import os
import unittest
import tempfile
import json
from datetime import datetime

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.mesh_tube import MeshTube
from src.models.node import Node

class TestMeshTube(unittest.TestCase):
    """Tests for the MeshTube class"""
    
    def setUp(self):
        """Set up a test mesh tube instance with sample data"""
        self.mesh = MeshTube(name="Test Mesh", storage_path=None)
        
        # Add some test nodes
        self.node1 = self.mesh.add_node(
            content={"topic": "Test Topic 1"},
            time=0.0,
            distance=0.1,
            angle=0.0
        )
        
        self.node2 = self.mesh.add_node(
            content={"topic": "Test Topic 2"},
            time=1.0,
            distance=0.5,
            angle=90.0
        )
        
        self.node3 = self.mesh.add_node(
            content={"topic": "Test Topic 3"},
            time=1.0,
            distance=0.8,
            angle=180.0
        )
        
        # Connect some nodes
        self.mesh.connect_nodes(self.node1.node_id, self.node2.node_id)
    
    def test_node_creation(self):
        """Test that nodes are created correctly"""
        self.assertEqual(len(self.mesh.nodes), 3)
        self.assertEqual(self.node1.content["topic"], "Test Topic 1")
        self.assertEqual(self.node1.time, 0.0)
        self.assertEqual(self.node1.distance, 0.1)
        self.assertEqual(self.node1.angle, 0.0)
    
    def test_node_connections(self):
        """Test that node connections work properly"""
        # Check that node1 and node2 are connected
        self.assertIn(self.node2.node_id, self.node1.connections)
        self.assertIn(self.node1.node_id, self.node2.connections)
        
        # Check that node3 is not connected to either
        self.assertNotIn(self.node3.node_id, self.node1.connections)
        self.assertNotIn(self.node3.node_id, self.node2.connections)
        
        # Connect node3 to node1
        self.mesh.connect_nodes(self.node1.node_id, self.node3.node_id)
        self.assertIn(self.node3.node_id, self.node1.connections)
        self.assertIn(self.node1.node_id, self.node3.connections)
    
    def test_temporal_slice(self):
        """Test retrieving nodes by temporal slice"""
        # Get nodes at time 1.0
        nodes_t1 = self.mesh.get_temporal_slice(time=1.0, tolerance=0.1)
        self.assertEqual(len(nodes_t1), 2)
        
        # Get nodes at time 0.0
        nodes_t0 = self.mesh.get_temporal_slice(time=0.0, tolerance=0.1)
        self.assertEqual(len(nodes_t0), 1)
        self.assertEqual(nodes_t0[0].node_id, self.node1.node_id)
        
        # Get nodes with a wider tolerance
        nodes_wide = self.mesh.get_temporal_slice(time=0.5, tolerance=0.6)
        self.assertEqual(len(nodes_wide), 3)  # Should include all nodes
    
    def test_delta_encoding(self):
        """Test delta encoding functionality"""
        # Create a delta node
        delta_node = self.mesh.apply_delta(
            original_node=self.node1,
            delta_content={"subtopic": "Delta Test"},
            time=2.0
        )
        
        # Check delta reference
        self.assertIn(self.node1.node_id, delta_node.delta_references)
        
        # Check computed state
        computed_state = self.mesh.compute_node_state(delta_node.node_id)
        self.assertEqual(computed_state["topic"], "Test Topic 1")  # Original content
        self.assertEqual(computed_state["subtopic"], "Delta Test")  # New content
        
        # Create another delta
        delta_node2 = self.mesh.apply_delta(
            original_node=delta_node,
            delta_content={"subtopic": "Updated Delta Test"},
            time=3.0
        )
        
        # Check computed state with chain of deltas
        computed_state2 = self.mesh.compute_node_state(delta_node2.node_id)
        self.assertEqual(computed_state2["topic"], "Test Topic 1")
        self.assertEqual(computed_state2["subtopic"], "Updated Delta Test")
    
    def test_save_and_load(self):
        """Test saving and loading the database"""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Save the database
            self.mesh.save(temp_path)
            
            # Verify the file exists and has content
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(data["name"], "Test Mesh")
                self.assertEqual(len(data["nodes"]), 3)
            
            # Load the database
            loaded_mesh = MeshTube.load(temp_path)
            
            # Verify loaded content
            self.assertEqual(loaded_mesh.name, "Test Mesh")
            self.assertEqual(len(loaded_mesh.nodes), 3)
            
            # Check that a specific node exists
            loaded_node1 = None
            for node in loaded_mesh.nodes.values():
                if node.content.get("topic") == "Test Topic 1":
                    loaded_node1 = node
                    break
                    
            self.assertIsNotNone(loaded_node1)
            self.assertEqual(loaded_node1.distance, 0.1)
            
            # Verify connections were preserved
            for node_id in loaded_node1.connections:
                node = loaded_mesh.get_node(node_id)
                self.assertIn(loaded_node1.node_id, node.connections)
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_spatial_distance(self):
        """Test the spatial distance calculation between nodes"""
        # Calculate distance between node1 and node2
        distance = self.node1.spatial_distance(self.node2)
        
        # Expected distance in cylindrical coordinates
        # sqrt(r1^2 + r2^2 - 2*r1*r2*cos(θ1-θ2) + (z1-z2)^2)
        # = sqrt(0.1^2 + 0.5^2 - 2*0.1*0.5*cos(90°) + (0-1)^2)
        # = sqrt(0.01 + 0.25 - 0 + 1)
        # = sqrt(1.26)
        # ≈ 1.12
        expected_distance = 1.12
        self.assertAlmostEqual(distance, expected_distance, places=2)
        
        # Distance should be symmetric
        distance_reverse = self.node2.spatial_distance(self.node1)
        self.assertAlmostEqual(distance, distance_reverse)

if __name__ == '__main__':
    unittest.main() 
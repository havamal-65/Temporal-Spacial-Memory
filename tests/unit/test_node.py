"""
Unit tests for the Node class.
"""

import unittest
from datetime import datetime

from src.core.node import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
from src.core.exceptions import NodeError


class TestNode(unittest.TestCase):
    def test_node_creation(self):
        """Test basic node creation."""
        # Create coordinates
        spatial = SpatialCoordinate(dimensions=(1.0, 2.0, 3.0))
        temporal = TemporalCoordinate(timestamp=datetime.now())
        coords = Coordinates(spatial=spatial, temporal=temporal)
        
        # Create a node
        node = Node(coordinates=coords, data={"test": "value"})
        
        # Check node properties
        self.assertIsNotNone(node.id)
        self.assertEqual(node.coordinates, coords)
        self.assertEqual(node.data, {"test": "value"})
        self.assertEqual(len(node.references), 0)
        self.assertEqual(len(node.metadata), 0)
    
    def test_node_with_data(self):
        """Test creating a new node with updated data."""
        # Create a node
        coords = Coordinates(spatial=SpatialCoordinate(dimensions=(1.0, 2.0, 3.0)))
        node = Node(coordinates=coords, data={"a": 1})
        
        # Create a new node with updated data
        new_node = node.with_data({"b": 2})
        
        # Check that the new node has the combined data
        self.assertEqual(new_node.data, {"a": 1, "b": 2})
        
        # Check that the original node is unchanged
        self.assertEqual(node.data, {"a": 1})
        
        # Check that other properties are preserved
        self.assertEqual(node.id, new_node.id)
        self.assertEqual(node.coordinates, new_node.coordinates)
    
    def test_node_with_coordinates(self):
        """Test creating a new node with updated coordinates."""
        # Create a node
        coords1 = Coordinates(spatial=SpatialCoordinate(dimensions=(1.0, 2.0, 3.0)))
        node = Node(coordinates=coords1)
        
        # Create a new node with updated coordinates
        coords2 = Coordinates(spatial=SpatialCoordinate(dimensions=(4.0, 5.0, 6.0)))
        new_node = node.with_coordinates(coords2)
        
        # Check that the new node has the new coordinates
        self.assertEqual(new_node.coordinates, coords2)
        
        # Check that the original node is unchanged
        self.assertEqual(node.coordinates, coords1)
        
        # Check that other properties are preserved
        self.assertEqual(node.id, new_node.id)
    
    def test_node_references(self):
        """Test adding and removing references."""
        # Create a node
        coords = Coordinates(spatial=SpatialCoordinate(dimensions=(1.0, 2.0, 3.0)))
        node = Node(coordinates=coords)
        
        # Add a reference
        ref_id = "reference_id"
        new_node = node.add_reference(ref_id)
        
        # Check that the reference was added
        self.assertIn(ref_id, new_node.references)
        self.assertEqual(len(new_node.references), 1)
        
        # Check that the original node is unchanged
        self.assertNotIn(ref_id, node.references)
        
        # Remove the reference
        newer_node = new_node.remove_reference(ref_id)
        
        # Check that the reference was removed
        self.assertNotIn(ref_id, newer_node.references)
        self.assertEqual(len(newer_node.references), 0)
        
        # Check that removing a non-existent reference does nothing
        same_node = newer_node.remove_reference("non_existent")
        self.assertEqual(same_node, newer_node)
    
    def test_node_distance(self):
        """Test calculating distance between nodes."""
        # Create two nodes with different spatial coordinates
        coords1 = Coordinates(spatial=SpatialCoordinate(dimensions=(0.0, 0.0, 0.0)))
        coords2 = Coordinates(spatial=SpatialCoordinate(dimensions=(3.0, 4.0, 0.0)))
        
        node1 = Node(coordinates=coords1)
        node2 = Node(coordinates=coords2)
        
        # Distance should be 5.0 (3-4-5 triangle)
        self.assertEqual(node1.distance_to(node2), 5.0)
        
        # Distance should be the same in reverse
        self.assertEqual(node2.distance_to(node1), 5.0)
    
    def test_node_serialization(self):
        """Test node serialization to and from dictionary."""
        # Create a node
        spatial = SpatialCoordinate(dimensions=(1.0, 2.0, 3.0))
        temporal = TemporalCoordinate(timestamp=datetime.now())
        coords = Coordinates(spatial=spatial, temporal=temporal)
        
        node = Node(
            coordinates=coords,
            data={"test": "value"},
            references={"ref1", "ref2"},
            metadata={"meta": "data"}
        )
        
        # Convert to dictionary
        node_dict = node.to_dict()
        
        # Check dictionary structure
        self.assertEqual(node_dict["id"], node.id)
        self.assertIn("coordinates", node_dict)
        self.assertIn("data", node_dict)
        self.assertIn("created_at", node_dict)
        self.assertIn("references", node_dict)
        self.assertIn("metadata", node_dict)
        
        # Convert back to node
        restored_node = Node.from_dict(node_dict)
        
        # Check restored node
        self.assertEqual(restored_node.id, node.id)
        self.assertEqual(restored_node.data, node.data)
        self.assertEqual(restored_node.references, node.references)
        self.assertEqual(restored_node.metadata, node.metadata)
        
        # Coordinates should be equal but might not be identical objects
        self.assertEqual(restored_node.coordinates.spatial.dimensions, 
                         node.coordinates.spatial.dimensions)
        self.assertEqual(restored_node.coordinates.temporal.timestamp, 
                         node.coordinates.temporal.timestamp)
    
    def test_node_from_dict_validation(self):
        """Test validation during deserialization."""
        # Missing required fields should raise an error
        with self.assertRaises(NodeError):
            Node.from_dict({})
        
        with self.assertRaises(NodeError):
            Node.from_dict({"id": "test"})
        
        with self.assertRaises(NodeError):
            Node.from_dict({"coordinates": {}})


if __name__ == "__main__":
    unittest.main() 
"""
Unit tests for the Node v2 class.
"""

import unittest
from uuid import UUID
from datetime import datetime

from src.core.node_v2 import Node, NodeConnection


class TestNodeV2(unittest.TestCase):
    """Test cases for the Node v2 class."""
    
    def test_node_creation(self):
        """Test basic node creation with default values."""
        # Create a node with minimal parameters
        node = Node(content={"test": "value"}, position=(1.0, 2.0, 3.0))
        
        # Check that UUID was generated
        self.assertIsInstance(node.id, UUID)
        
        # Check that other fields have expected values
        self.assertEqual(node.content, {"test": "value"})
        self.assertEqual(node.position, (1.0, 2.0, 3.0))
        self.assertEqual(node.connections, [])
        self.assertIsNone(node.origin_reference)
        self.assertEqual(node.delta_information, {})
        self.assertEqual(node.metadata, {})
    
    def test_node_with_explicit_values(self):
        """Test node creation with all parameters specified."""
        # Create node with all values
        node_id = UUID('12345678-1234-5678-1234-567812345678')
        origin_ref = UUID('87654321-8765-4321-8765-432187654321')
        
        node = Node(
            id=node_id,
            content={"name": "test node"},
            position=(10.0, 20.0, 30.0),
            connections=[
                NodeConnection(
                    target_id=UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                    connection_type="reference",
                    strength=0.5,
                    metadata={"relation": "uses"}
                )
            ],
            origin_reference=origin_ref,
            delta_information={"version": 1},
            metadata={"tags": ["test", "example"]}
        )
        
        # Check values
        self.assertEqual(node.id, node_id)
        self.assertEqual(node.content, {"name": "test node"})
        self.assertEqual(node.position, (10.0, 20.0, 30.0))
        self.assertEqual(len(node.connections), 1)
        self.assertEqual(node.connections[0].connection_type, "reference")
        self.assertEqual(node.connections[0].strength, 0.5)
        self.assertEqual(node.origin_reference, origin_ref)
        self.assertEqual(node.delta_information, {"version": 1})
        self.assertEqual(node.metadata, {"tags": ["test", "example"]})
    
    def test_node_connection(self):
        """Test creating and using node connections."""
        # Create a node
        node = Node(content={}, position=(0.0, 0.0, 0.0))
        
        # Add a connection
        target_id = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        node.add_connection(
            target_id=target_id,
            connection_type="source",
            strength=0.8,
            metadata={"importance": "high"}
        )
        
        # Check that the connection was added
        self.assertEqual(len(node.connections), 1)
        
        connection = node.connections[0]
        self.assertEqual(connection.target_id, target_id)
        self.assertEqual(connection.connection_type, "source")
        self.assertEqual(connection.strength, 0.8)
        self.assertEqual(connection.metadata, {"importance": "high"})
        
        # Test get_connections_by_type
        source_connections = node.get_connections_by_type("source")
        self.assertEqual(len(source_connections), 1)
        self.assertEqual(source_connections[0].target_id, target_id)
        
        # Test with a different type
        other_connections = node.get_connections_by_type("destination")
        self.assertEqual(len(other_connections), 0)
    
    def test_node_distance(self):
        """Test calculating distance between nodes."""
        # Create two nodes with different positions
        node1 = Node(content={}, position=(0.0, 0.0, 0.0))
        node2 = Node(content={}, position=(3.0, 4.0, 0.0))
        
        # Distance should be 5.0 (3-4-5 triangle)
        self.assertEqual(node1.distance_to(node2), 5.0)
        
        # Distance should be the same in reverse
        self.assertEqual(node2.distance_to(node1), 5.0)
    
    def test_node_serialization(self):
        """Test serialization and deserialization of nodes."""
        # Create a node with various fields
        original_node = Node(
            content={"name": "example"},
            position=(1.5, 2.5, 3.5),
            connections=[
                NodeConnection(
                    target_id=UUID('cccccccc-cccc-cccc-cccc-cccccccccccc'),
                    connection_type="related",
                    strength=0.7
                )
            ],
            metadata={"created_by": "test"}
        )
        
        # Convert to dict
        node_dict = original_node.to_dict()
        
        # Check dict structure
        self.assertEqual(node_dict["content"], {"name": "example"})
        self.assertEqual(node_dict["position"], (1.5, 2.5, 3.5))
        self.assertEqual(len(node_dict["connections"]), 1)
        self.assertEqual(node_dict["connections"][0]["connection_type"], "related")
        
        # Deserialize back to node
        restored_node = Node.from_dict(node_dict)
        
        # Check that the restored node matches the original
        self.assertEqual(restored_node.id, original_node.id)
        self.assertEqual(restored_node.content, original_node.content)
        self.assertEqual(restored_node.position, original_node.position)
        self.assertEqual(len(restored_node.connections), len(original_node.connections))
        self.assertEqual(restored_node.connections[0].target_id, 
                         original_node.connections[0].target_id)
    
    def test_connection_validation(self):
        """Test validation in NodeConnection."""
        # Test valid connection
        conn = NodeConnection(
            target_id=UUID('dddddddd-dddd-dddd-dddd-dddddddddddd'),
            connection_type="test",
            strength=0.5
        )
        self.assertEqual(conn.strength, 0.5)
        
        # Test invalid strength (should raise ValueError)
        with self.assertRaises(ValueError):
            NodeConnection(
                target_id=UUID('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'),
                connection_type="test",
                strength=1.5  # Invalid: > 1.0
            )


if __name__ == '__main__':
    unittest.main() 
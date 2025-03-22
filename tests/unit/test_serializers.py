"""
Unit tests for the serialization system.
"""

import unittest
import uuid
from datetime import datetime

from src.core.node_v2 import Node, NodeConnection

# Try to import serializers, skip tests if not available
try:
    from src.storage.serializers import (
        JSONSerializer, 
        MessagePackSerializer,
        get_serializer
    )
    SERIALIZERS_AVAILABLE = True
except ImportError:
    SERIALIZERS_AVAILABLE = False


@unittest.skipIf(not SERIALIZERS_AVAILABLE, "Serializers not available")
class TestSerializers(unittest.TestCase):
    """Test cases for the serialization system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test node with various fields
        self.node = Node(
            id=uuid.UUID('12345678-1234-5678-1234-567812345678'),
            content={"name": "Test Node", "value": 42},
            position=(1.0, 2.0, 3.0),
            connections=[
                NodeConnection(
                    target_id=uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                    connection_type="reference",
                    strength=0.5,
                    metadata={"relation": "uses"}
                ),
                NodeConnection(
                    target_id=uuid.UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
                    connection_type="source",
                    strength=0.8,
                    metadata={"importance": "high"}
                )
            ],
            origin_reference=uuid.UUID('cccccccc-cccc-cccc-cccc-cccccccccccc'),
            delta_information={"version": 1, "parent": "original"},
            metadata={"tags": ["test", "example"], "created": datetime.now().isoformat()}
        )
        
        # Create serializers
        self.json_serializer = JSONSerializer()
        self.msgpack_serializer = MessagePackSerializer()
    
    def test_json_serializer(self):
        """Test JSON serialization and deserialization."""
        # Serialize the node
        serialized_data = self.json_serializer.serialize(self.node)
        
        # Check that we got bytes
        self.assertIsInstance(serialized_data, bytes)
        
        # Deserialize back to a node
        restored_node = self.json_serializer.deserialize(serialized_data)
        
        # Check that the restored node matches the original
        self.assertEqual(restored_node.id, self.node.id)
        self.assertEqual(restored_node.content, self.node.content)
        self.assertEqual(restored_node.position, self.node.position)
        self.assertEqual(len(restored_node.connections), len(self.node.connections))
        
        # Check connections
        self.assertEqual(restored_node.connections[0].target_id, 
                         self.node.connections[0].target_id)
        self.assertEqual(restored_node.connections[0].connection_type, 
                         self.node.connections[0].connection_type)
        self.assertEqual(restored_node.connections[1].target_id, 
                         self.node.connections[1].target_id)
        
        # Check other fields
        self.assertEqual(restored_node.origin_reference, self.node.origin_reference)
        self.assertEqual(restored_node.delta_information, self.node.delta_information)
        self.assertEqual(restored_node.metadata, self.node.metadata)
    
    def test_messagepack_serializer(self):
        """Test MessagePack serialization and deserialization."""
        # Serialize the node
        serialized_data = self.msgpack_serializer.serialize(self.node)
        
        # Check that we got bytes
        self.assertIsInstance(serialized_data, bytes)
        
        # Deserialize back to a node
        restored_node = self.msgpack_serializer.deserialize(serialized_data)
        
        # Check that the restored node matches the original
        self.assertEqual(restored_node.id, self.node.id)
        self.assertEqual(restored_node.content, self.node.content)
        self.assertEqual(restored_node.position, self.node.position)
        self.assertEqual(len(restored_node.connections), len(self.node.connections))
        
        # Check connections
        self.assertEqual(restored_node.connections[0].target_id, 
                         self.node.connections[0].target_id)
        self.assertEqual(restored_node.connections[0].connection_type, 
                         self.node.connections[0].connection_type)
        self.assertEqual(restored_node.connections[1].target_id, 
                         self.node.connections[1].target_id)
        
        # Check other fields
        self.assertEqual(restored_node.origin_reference, self.node.origin_reference)
        self.assertEqual(restored_node.delta_information, self.node.delta_information)
        self.assertEqual(restored_node.metadata, self.node.metadata)
    
    def test_complex_types(self):
        """Test serialization of complex types."""
        # Create a node with complex types
        complex_node = Node(
            content={
                "tuple_value": (1, 2, 3),
                "set_value": {1, 2, 3},
                "nested_dict": {
                    "a": [1, 2, 3],
                    "b": {"x": 1, "y": 2}
                }
            },
            position=(0.0, 0.0, 0.0)
        )
        
        # Test with both serializers
        for serializer in [self.json_serializer, self.msgpack_serializer]:
            # Serialize and deserialize
            serialized_data = serializer.serialize(complex_node)
            restored_node = serializer.deserialize(serialized_data)
            
            # Check content - tuple may be preserved or converted to list
            tuple_value = restored_node.content.get("tuple_value")
            if isinstance(tuple_value, tuple):
                self.assertEqual(tuple_value, (1, 2, 3))
            else:
                self.assertEqual(tuple_value, [1, 2, 3])
                
            # Set may be converted to list, we just check the values
            restored_set = restored_node.content.get("set_value")
            if isinstance(restored_set, set):
                self.assertEqual(restored_set, {1, 2, 3})
            else:
                self.assertEqual(set(restored_set), {1, 2, 3})
            
            # Check nested dict
            nested_a = restored_node.content.get("nested_dict").get("a")
            # Handle both list and tuple
            if isinstance(nested_a, tuple):
                self.assertEqual(nested_a, (1, 2, 3))
            else:
                self.assertEqual(nested_a, [1, 2, 3])
                
            self.assertEqual(restored_node.content.get("nested_dict").get("b"), {"x": 1, "y": 2})
    
    def test_get_serializer(self):
        """Test the serializer factory function."""
        # Get JSON serializer
        json_serializer = get_serializer('json')
        self.assertIsInstance(json_serializer, JSONSerializer)
        
        # Get MessagePack serializer
        msgpack_serializer = get_serializer('msgpack')
        self.assertIsInstance(msgpack_serializer, MessagePackSerializer)
        
        # Check with alternative name
        alt_msgpack_serializer = get_serializer('messagepack')
        self.assertIsInstance(alt_msgpack_serializer, MessagePackSerializer)
        
        # Check invalid format
        with self.assertRaises(ValueError):
            get_serializer('invalid_format')
    
    def test_serialization_size_comparison(self):
        """Compare the size of serialized data between formats."""
        # Create a large node
        large_node = Node(
            content={"data": "A" * 1000},  # 1000 'A' characters
            position=(1.1, 2.2, 3.3)
        )
        
        # Serialize with both formats
        json_data = self.json_serializer.serialize(large_node)
        msgpack_data = self.msgpack_serializer.serialize(large_node)
        
        # MessagePack should be more compact
        self.assertLess(len(msgpack_data), len(json_data),
                        "MessagePack serialization should be smaller than JSON")


if __name__ == '__main__':
    unittest.main() 
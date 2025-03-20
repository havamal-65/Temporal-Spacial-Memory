"""
Simplified integration tests for Temporal-Spatial Knowledge Database.

This module provides basic tests for the storage and node components.
"""

import unittest
import tempfile
import shutil
import os
from uuid import uuid4

from src.core.node_v2 import Node
from src.storage.node_store import InMemoryNodeStore


class BasicNodeStorageTest(unittest.TestCase):
    """Tests for basic node storage with in-memory store."""
    
    def setUp(self):
        """Set up the test."""
        self.store = InMemoryNodeStore()
        
    def test_create_and_retrieve(self):
        """Test creating and retrieving a node."""
        # Create a test node
        node = Node(
            content={"test": "value"},
            position=(1.0, 2.0, 3.0),
            connections=[]
        )
        
        # Store the node
        self.store.put(node)
        
        # Retrieve the node
        retrieved = self.store.get(node.id)
        
        # Verify it's the same node
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, node.id)
        self.assertEqual(retrieved.content, {"test": "value"})
        self.assertEqual(retrieved.position, (1.0, 2.0, 3.0))
        
    def test_update(self):
        """Test updating a node."""
        # Create a test node
        node = Node(
            content={"test": "value"},
            position=(1.0, 2.0, 3.0),
            connections=[]
        )
        
        # Store the node
        self.store.put(node)
        
        # Create an updated version of the node (with same ID)
        updated = Node(
            id=node.id,
            content={"test": "updated"},
            position=(1.0, 2.0, 3.0),
            connections=[]
        )
        
        # Update the node
        self.store.put(updated)
        
        # Retrieve the node
        retrieved = self.store.get(node.id)
        
        # Verify it's updated
        self.assertEqual(retrieved.content, {"test": "updated"})
        
    def test_delete(self):
        """Test deleting a node."""
        # Create a test node
        node = Node(
            content={"test": "value"},
            position=(1.0, 2.0, 3.0),
            connections=[]
        )
        
        # Store the node
        self.store.put(node)
        
        # Verify it exists
        self.assertTrue(self.store.exists(node.id))
        
        # Delete the node
        result = self.store.delete(node.id)
        
        # Verify delete succeeded
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertFalse(self.store.exists(node.id))
        self.assertIsNone(self.store.get(node.id))
        
    def test_batch_operations(self):
        """Test batch operations."""
        # Create test nodes
        nodes = [
            Node(
                content={"index": i},
                position=(float(i), 0.0, 0.0),
                connections=[]
            )
            for i in range(10)
        ]
        
        # Store nodes in batch
        self.store.put_many(nodes)
        
        # Get in batch
        ids = [node.id for node in nodes]
        batch_results = self.store.get_many(ids)
        
        # Verify all were retrieved
        self.assertEqual(len(batch_results), 10)
        for i, node_id in enumerate(ids):
            self.assertEqual(batch_results[node_id].content["index"], i)
        
        # Test count
        self.assertEqual(self.store.count(), 10)
        
        # Test list_ids
        stored_ids = self.store.list_ids()
        for node_id in ids:
            self.assertIn(node_id, stored_ids)


class NodeConnectionTest(unittest.TestCase):
    """Tests for node connections."""
    
    def setUp(self):
        """Set up the test."""
        self.store = InMemoryNodeStore()
        
    def test_node_connections(self):
        """Test creating and using node connections."""
        # Create two test nodes
        node1 = Node(
            content={"name": "Node 1"},
            position=(1.0, 0.0, 0.0),
            connections=[]
        )
        
        node2 = Node(
            content={"name": "Node 2"},
            position=(2.0, 0.0, 0.0),
            connections=[]
        )
        
        # Store the nodes
        self.store.put(node1)
        self.store.put(node2)
        
        # Add a connection from node1 to node2
        node1.add_connection(
            target_id=node2.id,
            connection_type="reference",
            strength=0.8,
            metadata={"relation": "depends_on"}
        )
        
        # Update node1 in store
        self.store.put(node1)
        
        # Retrieve node1
        retrieved = self.store.get(node1.id)
        
        # Verify connection
        self.assertEqual(len(retrieved.connections), 1)
        connection = retrieved.connections[0]
        
        self.assertEqual(connection.target_id, node2.id)
        self.assertEqual(connection.connection_type, "reference")
        self.assertEqual(connection.strength, 0.8)
        self.assertEqual(connection.metadata, {"relation": "depends_on"})
        
        # Add a connection back from node2 to node1
        node2.add_connection(
            target_id=node1.id,
            connection_type="bidirectional",
            strength=0.9
        )
        
        # Update node2 in store
        self.store.put(node2)
        
        # Retrieve node2
        retrieved2 = self.store.get(node2.id)
        
        # Verify connection
        self.assertEqual(len(retrieved2.connections), 1)
        connection2 = retrieved2.connections[0]
        
        self.assertEqual(connection2.target_id, node1.id)
        self.assertEqual(connection2.connection_type, "bidirectional")
        self.assertEqual(connection2.strength, 0.9)


if __name__ == '__main__':
    unittest.main() 
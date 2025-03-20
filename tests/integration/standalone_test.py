"""
Standalone test for Temporal-Spatial Knowledge Database.

This test implements a minimal version of the Node structures and tests them.
"""

import unittest
import copy
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4


@dataclass
class NodeConnection:
    """A connection between nodes."""
    target_id: UUID
    connection_type: str
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """A node in the knowledge graph."""
    id: UUID = field(default_factory=uuid4)
    content: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[float, float, float] = field(default=(0.0, 0.0, 0.0))
    connections: List[NodeConnection] = field(default_factory=list)
    origin_reference: Optional[UUID] = None
    delta_information: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_connection(self, target_id, connection_type, strength=1.0, metadata=None):
        """Add a connection to this node."""
        self.connections.append(NodeConnection(
            target_id=target_id,
            connection_type=connection_type,
            strength=strength,
            metadata=metadata or {}
        ))


class InMemoryNodeStore:
    """In-memory store for nodes."""
    
    def __init__(self):
        """Initialize an empty store."""
        self.nodes = {}
        
    def put(self, node: Node) -> None:
        """Store a node."""
        self.nodes[node.id] = copy.deepcopy(node)
        
    def get(self, node_id: UUID) -> Optional[Node]:
        """Retrieve a node by ID."""
        return copy.deepcopy(self.nodes.get(node_id))
    
    def exists(self, node_id: UUID) -> bool:
        """Check if a node exists."""
        return node_id in self.nodes
    
    def delete(self, node_id: UUID) -> bool:
        """Delete a node."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False
    
    def count(self) -> int:
        """Count the number of nodes."""
        return len(self.nodes)
    
    def list_ids(self) -> List[UUID]:
        """List all node IDs."""
        return list(self.nodes.keys())


class TestNodeStorage(unittest.TestCase):
    """Tests for the node storage."""
    
    def setUp(self):
        """Set up the test."""
        self.store = InMemoryNodeStore()
        
    def test_create_and_retrieve(self):
        """Test creating and retrieving a node."""
        # Create a test node
        node = Node(
            content={"test": "value"},
            position=(1.0, 2.0, 3.0)
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
            position=(1.0, 2.0, 3.0)
        )
        
        # Store the node
        self.store.put(node)
        
        # Create an updated version of the node (with same ID)
        updated = Node(
            id=node.id,
            content={"test": "updated"},
            position=(1.0, 2.0, 3.0)
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
            position=(1.0, 2.0, 3.0)
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


class TestNodeConnections(unittest.TestCase):
    """Tests for node connections."""
    
    def setUp(self):
        """Set up the test."""
        self.store = InMemoryNodeStore()
        
    def test_node_connections(self):
        """Test creating and using node connections."""
        # Create two test nodes
        node1 = Node(
            content={"name": "Node 1"},
            position=(1.0, 0.0, 0.0)
        )
        
        node2 = Node(
            content={"name": "Node 2"},
            position=(2.0, 0.0, 0.0)
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
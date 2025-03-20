"""
Integration tests for storage and indexing components.

These tests verify that the storage and indexing components work together correctly.
"""

import unittest
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

# Update to use node_v2
from src.core.node_v2 import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

# Import with error handling
try:
    from src.storage.rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError:
    from src.storage.node_store import InMemoryNodeStore
    # Create a placeholder class
    class RocksDBNodeStore(InMemoryNodeStore):
        def __init__(self, db_path=None, create_if_missing=True):
            super().__init__()
            print("WARNING: RocksDB not available, using in-memory store")
    ROCKSDB_AVAILABLE = False

try:
    from src.indexing.combined_index import CombinedIndex
    INDEXING_AVAILABLE = True
except ImportError:
    # Create a placeholder class
    class CombinedIndex:
        def __init__(self):
            print("WARNING: Indexing components not available")
        def insert(self, node):
            pass
        def remove(self, node_id):
            pass
        def update(self, node):
            pass
        def spatial_nearest(self, point, num_results=10):
            return []
        def temporal_range(self, start, end):
            return []
        def combined_query(self, spatial_point, temporal_range, num_results=10):
            return []
        def get_all(self):
            return []
    INDEXING_AVAILABLE = False


@unittest.skipIf(not ROCKSDB_AVAILABLE or not INDEXING_AVAILABLE, 
                "RocksDB or indexing dependencies not available")
class TestStorageIndexingIntegration(unittest.TestCase):
    def setUp(self):
        """Set up temporary storage and indices for testing."""
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_db")
        
        # Create the database and index
        self.store = RocksDBNodeStore(db_path=self.db_path, create_if_missing=True)
        self.index = CombinedIndex()
        
        # Create some test nodes
        self.create_test_nodes()
    
    def tearDown(self):
        """Clean up after tests."""
        self.store.close()
        shutil.rmtree(self.temp_dir)
    
    def create_test_nodes(self):
        """Create and store test nodes."""
        self.nodes = []
        
        # Base time for temporal coordinates
        now = datetime.now()
        
        # Create nodes at positions along the x-axis at various times
        for i in range(10):
            # Create node with cylindrical coordinates (time, radius, theta)
            node = Node(
                id=uuid4(),
                content={"index": i, "value": i * 10},
                # Use (time, x-position, 0) as cylindrical coordinates
                position=(now.timestamp() - i*86400, float(i), 0.0)
            )
            
            # Save the node and add to the index
            self.store.save(node)
            self.index.insert(node)
            
            # Remember the node for tests
            self.nodes.append(node)
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving nodes from RocksDB."""
        # Check that all nodes were stored
        self.assertEqual(self.store.count(), len(self.nodes))
        
        # Check that each node can be retrieved
        for node in self.nodes:
            retrieved_node = self.store.get(node.id)
            self.assertIsNotNone(retrieved_node)
            self.assertEqual(retrieved_node.id, node.id)
            self.assertEqual(retrieved_node.content, node.content)
    
    def test_spatial_index(self):
        """Test spatial indexing and queries."""
        # Query for nodes near the origin
        origin = (self.nodes[0].position[0], 0.0, 0.0)  # Use same time as first node
        nearest_nodes = self.index.spatial_nearest(origin, num_results=3)
        
        # Should get the 3 nodes closest to origin - nodes 0, 1, 2
        self.assertEqual(len(nearest_nodes), 3)
        
        # Check the results are sorted by spatial distance
        sorted_nodes = sorted(nearest_nodes, 
                            key=lambda n: abs(n.position[1] - origin[1]))
        
        for i, node in enumerate(sorted_nodes[:3]):
            # The i-th result should be the node at position i
            self.assertEqual(node.content["index"], i)
    
    def test_temporal_index(self):
        """Test temporal indexing and queries."""
        # Base time
        now = datetime.now()
        
        # Query for nodes in the last 3 days
        three_days_ago = now - timedelta(days=3)
        recent_nodes = self.index.temporal_range(
            three_days_ago.timestamp(), now.timestamp())
        
        # Should get 4 nodes (days 0, 1, 2, 3)
        self.assertEqual(len(recent_nodes), 4)
    
    def test_combined_query(self):
        """Test combined spatial and temporal queries."""
        # Base time
        now = datetime.now()
        
        # Query for nodes near position 5 within the last 7 days
        position = (now.timestamp() - 5*86400, 5.0, 0.0)  # Time 5 days ago, position 5
        week_ago = now - timedelta(days=7)
        
        results = self.index.combined_query(
            spatial_point=(position[1], position[2]),  # Just spatial part
            temporal_range=(week_ago.timestamp(), now.timestamp()),
            num_results=3
        )
        
        # Should get nodes, sorted by distance to position 5
        self.assertEqual(len(results), 3)
        
        # Sort results by distance to position 5
        sorted_results = sorted(results, 
                              key=lambda n: abs(n.position[1] - 5.0))
        
        # The closest should be node 5
        self.assertEqual(sorted_results[0].content["index"], 5)
    
    def test_delete_and_update(self):
        """Test deleting and updating nodes."""
        # Delete the first node
        first_node = self.nodes[0]
        self.store.delete(first_node.id)
        self.index.remove(first_node.id)
        
        # Check it's gone from storage
        self.assertIsNone(self.store.get(first_node.id))
        
        # Check it's gone from index
        self.assertNotIn(first_node.id, self.index.get_all())
        
        # Update the second node
        second_node = self.nodes[1]
        # Create a new node with updated content
        updated_node = Node(
            id=second_node.id,
            content={**second_node.content, "updated": True},
            position=second_node.position,
            connections=second_node.connections
        )
        
        self.store.save(updated_node)
        self.index.update(updated_node)
        
        # Check it's updated in storage
        retrieved_node = self.store.get(second_node.id)
        self.assertTrue(retrieved_node.content.get("updated", False))
        
        # Check it's updated in index
        indexed_node = next((n for n in self.index.get_all() if n.id == second_node.id), None)
        self.assertTrue(indexed_node.content.get("updated", False))


if __name__ == "__main__":
    unittest.main() 
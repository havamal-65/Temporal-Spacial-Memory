"""
Unit tests for the RocksDBNodeStore with transaction support.
"""

import unittest
import tempfile
import shutil
import os
import uuid
from typing import Dict, Any

from src.storage.rocksdb_store import RocksDBNodeStore, RocksDBTransaction, TransactionError
from src.core.node_v2 import Node
from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate

class TestRocksDBNodeStore(unittest.TestCase):
    """Test suite for RocksDBNodeStore."""
    
    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_db")
        self.store = RocksDBNodeStore(self.db_path)
        
        # Create some test nodes
        self.nodes = {}
        for i in range(10):
            node_id = str(uuid.uuid4())
            coords = Coordinates(
                spatial=SpatialCoordinate((float(i), float(i * 2), 0.0)),
                temporal=TemporalCoordinate(timestamp=1000 + i * 100)
            )
            node = Node(id=node_id, coordinates=coords, data={"value": f"test_{i}"})
            self.nodes[node_id] = node
    
    def tearDown(self):
        """Clean up temporary database after each test."""
        self.store.close()
        shutil.rmtree(self.temp_dir)
    
    def test_basic_operations(self):
        """Test basic store operations."""
        # Test put and get
        node = list(self.nodes.values())[0]
        self.store.put(node)
        
        retrieved = self.store.get(uuid.UUID(node.id))
        self.assertIsNotNone(retrieved)
        self.assertEqual(node.id, retrieved.id)
        self.assertEqual(node.data, retrieved.data)
        
        # Test exists
        self.assertTrue(self.store.exists(uuid.UUID(node.id)))
        self.assertFalse(self.store.exists(uuid.UUID(str(uuid.uuid4()))))
        
        # Test delete
        self.assertTrue(self.store.delete(uuid.UUID(node.id)))
        self.assertFalse(self.store.exists(uuid.UUID(node.id)))
        self.assertFalse(self.store.delete(uuid.UUID(node.id)))  # Already deleted
    
    def test_batch_operations(self):
        """Test batch operations."""
        # Put multiple nodes
        node_list = list(self.nodes.values())
        self.store.put_many(node_list)
        
        # Get multiple nodes
        node_ids = [uuid.UUID(node.id) for node in node_list]
        retrieved_nodes = self.store.get_many(node_ids)
        
        self.assertEqual(len(node_ids), len(retrieved_nodes))
        for node_id in node_ids:
            self.assertIn(node_id, retrieved_nodes)
            self.assertEqual(str(node_id), retrieved_nodes[node_id].id)
            
        # Count nodes
        self.assertEqual(len(node_list), self.store.count())
        
        # List IDs
        stored_ids = self.store.list_ids()
        self.assertEqual(len(node_ids), len(stored_ids))
        for node_id in node_ids:
            self.assertIn(node_id, stored_ids)
    
    def test_transaction_commit(self):
        """Test transaction commits."""
        # Add some initial data
        initial_node = list(self.nodes.values())[0]
        self.store.put(initial_node)
        
        # Create a transaction
        with self.store.transaction() as tx:
            # Add a new node
            new_node = list(self.nodes.values())[1]
            tx.put(new_node)
            
            # Verify it's visible within the transaction
            retrieved = tx.get(uuid.UUID(new_node.id))
            self.assertIsNotNone(retrieved)
            
            # Verify it's not visible outside the transaction yet
            outside_retrieved = self.store.get(uuid.UUID(new_node.id))
            self.assertIsNone(outside_retrieved)
            
            # Update an existing node
            updated_node = Node(
                id=initial_node.id,
                coordinates=initial_node.coordinates,
                data={"value": "updated"}
            )
            tx.put(updated_node)
            
            # Commit the transaction
            self.assertTrue(tx.commit())
        
        # Verify changes are now visible outside the transaction
        self.assertTrue(self.store.exists(uuid.UUID(new_node.id)))
        updated = self.store.get(uuid.UUID(initial_node.id))
        self.assertEqual("updated", updated.data["value"])
    
    def test_transaction_rollback(self):
        """Test transaction rollbacks."""
        # Add some initial data
        initial_node = list(self.nodes.values())[0]
        self.store.put(initial_node)
        
        # Create a transaction
        tx = self.store.create_transaction()
        
        # Add a new node
        new_node = list(self.nodes.values())[1]
        tx.put(new_node)
        
        # Verify it's visible within the transaction
        retrieved = tx.get(uuid.UUID(new_node.id))
        self.assertIsNotNone(retrieved)
        
        # Rollback the transaction
        tx.rollback()
        
        # Verify the new node is not in the database
        self.assertFalse(self.store.exists(uuid.UUID(new_node.id)))
        
        # Verify the initial node is unchanged
        original = self.store.get(uuid.UUID(initial_node.id))
        self.assertEqual(initial_node.data["value"], original.data["value"])
        
        # Clean up
        tx.release_snapshot()
    
    def test_transaction_automatic_rollback(self):
        """Test automatic rollback in context manager."""
        initial_node = list(self.nodes.values())[0]
        self.store.put(initial_node)
        
        # Create a transaction that exists the context without committing
        with self.store.transaction() as tx:
            new_node = list(self.nodes.values())[1]
            tx.put(new_node)
            # No commit, should rollback automatically
        
        # Verify the new node is not in the database
        self.assertFalse(self.store.exists(uuid.UUID(new_node.id)))
    
    def test_transaction_commit_after_exception(self):
        """Test that transactions are rolled back if an exception occurs."""
        initial_node = list(self.nodes.values())[0]
        self.store.put(initial_node)
        
        try:
            with self.store.transaction() as tx:
                new_node = list(self.nodes.values())[1]
                tx.put(new_node)
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Verify the new node is not in the database
        self.assertFalse(self.store.exists(uuid.UUID(new_node.id)))
    
    def test_double_commit(self):
        """Test that committing twice raises an error."""
        tx = self.store.create_transaction()
        
        # Add a node
        node = list(self.nodes.values())[0]
        tx.put(node)
        
        # First commit should succeed
        self.assertTrue(tx.commit())
        
        # Second commit should raise an error
        with self.assertRaises(TransactionError):
            tx.commit()
            
        # Clean up
        tx.release_snapshot()
    
    def test_rollback_after_commit(self):
        """Test that rolling back after commit raises an error."""
        tx = self.store.create_transaction()
        
        # Add a node
        node = list(self.nodes.values())[0]
        tx.put(node)
        
        # Commit
        self.assertTrue(tx.commit())
        
        # Rollback should raise an error
        with self.assertRaises(TransactionError):
            tx.rollback()
            
        # Clean up
        tx.release_snapshot()
    
    def test_transaction_conflict(self):
        """Test transaction conflict detection."""
        # Add a node
        node = list(self.nodes.values())[0]
        self.store.put(node)
        
        # Create two transactions
        tx1 = self.store.create_transaction()
        tx2 = self.store.create_transaction()
        
        # Both read the same node
        retrieved1 = tx1.get(uuid.UUID(node.id))
        retrieved2 = tx2.get(uuid.UUID(node.id))
        
        # Update in the first transaction and commit
        updated_node = Node(
            id=node.id,
            coordinates=node.coordinates,
            data={"value": "updated_by_tx1"}
        )
        tx1.put(updated_node)
        self.assertTrue(tx1.commit())
        
        # Update in the second transaction and try to commit
        # This should fail due to conflict
        updated_node2 = Node(
            id=node.id,
            coordinates=node.coordinates,
            data={"value": "updated_by_tx2"}
        )
        tx2.put(updated_node2)
        
        # Should detect conflict because tx1 modified data after tx2's snapshot
        self.assertFalse(tx2.commit())
        
        # Verify the database has tx1's update
        final = self.store.get(uuid.UUID(node.id))
        self.assertEqual("updated_by_tx1", final.data["value"])
        
        # Clean up
        tx1.release_snapshot()
        tx2.release_snapshot()
    
    def test_get_statistics(self):
        """Test getting database statistics."""
        # Add some nodes
        for node in list(self.nodes.values())[:5]:
            self.store.put(node)
            
        # Get statistics
        stats = self.store.get_statistics()
        
        # Check basic stats
        self.assertEqual(5, stats["node_count"])
        self.assertEqual(self.db_path, stats["db_path"])
        self.assertEqual(0, stats["active_transactions"])
        
        # Create a transaction to see if it's counted
        tx = self.store.create_transaction()
        stats = self.store.get_statistics()
        self.assertEqual(1, stats["active_transactions"])
        
        # Clean up
        tx.release_snapshot()
    
    def test_iterator(self):
        """Test iterator functionality."""
        # Add some nodes
        for node in list(self.nodes.values())[:5]:
            self.store.put(node)
            
        # Get all nodes using iterator
        count = 0
        for node_id, node in self.store.get_iterator():
            count += 1
            self.assertIn(str(node_id), self.nodes)
            self.assertEqual(str(node_id), node.id)
            
        self.assertEqual(5, count)
        
        # Test prefix iteration
        # Use a prefix from one of the node IDs
        prefix = list(self.nodes.keys())[0][:8]
        matching_ids = [id for id in self.nodes.keys() if id.startswith(prefix)]
        
        count = 0
        for node_id, node in self.store.get_iterator(prefix=prefix):
            count += 1
            self.assertIn(str(node_id), matching_ids)
            
        self.assertEqual(len(matching_ids), count)
    
    def test_backup(self):
        """Test database backup functionality."""
        # Add some nodes
        for node in list(self.nodes.values())[:5]:
            self.store.put(node)
            
        # Create a backup
        backup_path = os.path.join(self.temp_dir, "backup_db")
        success = self.store.backup(backup_path)
        self.assertTrue(success)
        
        # Verify the backup exists
        self.assertTrue(os.path.exists(backup_path))
        
        # Open the backup and verify data
        backup_store = RocksDBNodeStore(backup_path)
        
        for node in list(self.nodes.values())[:5]:
            retrieved = backup_store.get(uuid.UUID(node.id))
            self.assertIsNotNone(retrieved)
            self.assertEqual(node.id, retrieved.id)
            self.assertEqual(node.data, retrieved.data)
            
        backup_store.close()
    
    def test_compact(self):
        """Test database compaction."""
        # Add and then delete nodes to create fragmentation
        for node in list(self.nodes.values()):
            self.store.put(node)
            
        for node_id in list(self.nodes.keys())[:5]:
            self.store.delete(uuid.UUID(node_id))
            
        # Compact the database
        self.store.compact()
        
        # Verify remaining nodes are still accessible
        for node_id in list(self.nodes.keys())[5:]:
            self.assertTrue(self.store.exists(uuid.UUID(node_id)))

if __name__ == "__main__":
    unittest.main() 
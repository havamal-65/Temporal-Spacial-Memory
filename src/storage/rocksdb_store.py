"""
RocksDB implementation of the NodeStore for Temporal-Spatial Knowledge Database.

This module provides a persistent storage implementation using RocksDB.
"""

import os
import json
import rocksdb
from typing import Dict, Optional, List, Any, Set, Iterator, Tuple, Callable, ContextManager
from uuid import UUID
import uuid
import logging
from contextlib import contextmanager
import time

from .node_store import NodeStore
from ..core.node_v2 import Node
from .serialization import NodeSerializer, SimpleNodeSerializer

# Configure logger
logger = logging.getLogger(__name__)

class RocksDBError(Exception):
    """Base exception for RocksDB related errors."""
    pass

class TransactionError(RocksDBError):
    """Exception raised for transaction errors."""
    pass

class RocksDBTransaction:
    """
    Transaction wrapper for RocksDB operations.
    
    Provides methods for atomic operations and transaction management.
    """
    
    def __init__(self, db: rocksdb.DB, serializer: NodeSerializer):
        """
        Initialize a new transaction.
        
        Args:
            db: RocksDB database instance
            serializer: Serializer for node objects
        """
        self.db = db
        self.serializer = serializer
        self.batch = rocksdb.WriteBatch()
        self.reads: Set[bytes] = set()  # Track read keys for conflict detection
        self.writes: Set[bytes] = set()  # Track written keys
        self.deletes: Set[bytes] = set()  # Track deleted keys
        self.snapshot = db.snapshot()  # Create a consistent view of the database
        self.committed = False
        self.transaction_id = str(uuid.uuid4())
    
    def put(self, node: Node) -> None:
        """
        Add a node to the transaction.
        
        Args:
            node: Node to store
        """
        key = str(node.id).encode('utf-8')
        value = self.serializer.serialize(node)
        self.batch.put(key, value)
        self.writes.add(key)
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """
        Get a node within the transaction context.
        
        Args:
            node_id: ID of the node to retrieve
            
        Returns:
            Node if found, None otherwise
        """
        key = str(node_id).encode('utf-8')
        self.reads.add(key)
        
        # Read from the snapshot for consistency
        value = self.db.get(key, snapshot=self.snapshot)
        
        if value is None:
            return None
            
        return self.serializer.deserialize(value)
    
    def delete(self, node_id: UUID) -> bool:
        """
        Mark a node for deletion in the transaction.
        
        Args:
            node_id: ID of the node to delete
            
        Returns:
            True if node exists and was marked for deletion, False otherwise
        """
        key = str(node_id).encode('utf-8')
        self.reads.add(key)
        
        # Check if the node exists
        if self.db.get(key, snapshot=self.snapshot) is None:
            return False
            
        self.batch.delete(key)
        self.deletes.add(key)
        return True
    
    def exists(self, node_id: UUID) -> bool:
        """
        Check if a node exists within the transaction context.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node exists, False otherwise
        """
        key = str(node_id).encode('utf-8')
        self.reads.add(key)
        return self.db.get(key, snapshot=self.snapshot) is not None
    
    def put_many(self, nodes: List[Node]) -> None:
        """
        Add multiple nodes to the transaction.
        
        Args:
            nodes: Nodes to store
        """
        for node in nodes:
            self.put(node)
    
    def get_many(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """
        Get multiple nodes within the transaction context.
        
        Args:
            node_ids: IDs of the nodes to retrieve
            
        Returns:
            Dictionary mapping IDs to nodes
        """
        result = {}
        for node_id in node_ids:
            node = self.get(node_id)
            if node is not None:
                result[node_id] = node
                
        return result
    
    def has_conflicts(self) -> bool:
        """
        Check for conflicts with the current database state.
        
        Returns:
            True if there are conflicts, False otherwise
        """
        for key in self.reads:
            # Check if the values changed since the snapshot was created
            current_value = self.db.get(key)
            snapshot_value = self.db.get(key, snapshot=self.snapshot)
            
            if current_value != snapshot_value:
                return True
                
        return False
    
    def commit(self) -> bool:
        """
        Commit the transaction.
        
        Returns:
            True if commit was successful, False if conflicts were detected
        
        Raises:
            TransactionError: If the transaction was already committed
        """
        if self.committed:
            raise TransactionError("Transaction already committed")
            
        # Check for conflicts
        if self.has_conflicts():
            return False
            
        # Commit changes
        self.db.write(self.batch)
        self.committed = True
        return True
    
    def rollback(self) -> None:
        """
        Rollback the transaction.
        
        This abandons all operations in the transaction.
        
        Raises:
            TransactionError: If the transaction was already committed
        """
        if self.committed:
            raise TransactionError("Cannot rollback: transaction already committed")
            
        # Clear batch (no need to do anything else as changes weren't applied)
        self.batch = rocksdb.WriteBatch()
        self.reads.clear()
        self.writes.clear()
        self.deletes.clear()
    
    def release_snapshot(self) -> None:
        """Release the snapshot to free resources."""
        del self.snapshot

class RocksDBNodeStore(NodeStore):
    """
    RocksDB implementation of NodeStore.
    
    This provides persistent storage of nodes using RocksDB.
    """
    
    def __init__(self, db_path: str, 
                 serializer: Optional[NodeSerializer] = None,
                 create_if_missing: bool = True,
                 max_open_files: int = -1,
                 write_buffer_size: int = 67108864,  # 64MB
                 max_write_buffer_number: int = 3,
                 target_file_size_base: int = 67108864,  # 64MB
                 compression: Optional[rocksdb.CompressionType] = None):
        """
        Initialize a RocksDB node store.
        
        Args:
            db_path: Path to the RocksDB database
            serializer: Optional custom serializer (defaults to SimpleNodeSerializer)
            create_if_missing: Whether to create the database if it doesn't exist
            max_open_files: Max number of open files (-1 for unlimited)
            write_buffer_size: Size of a single memtable
            max_write_buffer_number: Maximum number of memtables
            target_file_size_base: Target file size for level-1
            compression: Compression type to use
        """
        self.db_path = db_path
        self.serializer = serializer or SimpleNodeSerializer()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Configure RocksDB options
        opts = rocksdb.Options()
        opts.create_if_missing = create_if_missing
        opts.max_open_files = max_open_files
        opts.write_buffer_size = write_buffer_size
        opts.max_write_buffer_number = max_write_buffer_number
        opts.target_file_size_base = target_file_size_base
        
        if compression:
            opts.compression = compression
        
        # Additional tuning options
        opts.allow_concurrent_memtable_write = True
        opts.enable_write_thread_adaptive_yield = True
        
        # Open RocksDB database
        try:
            self.db = rocksdb.DB(db_path, opts)
            logger.info(f"Opened RocksDB database at {db_path}")
        except rocksdb.errors.RocksIOError as e:
            logger.error(f"Failed to open RocksDB database at {db_path}: {e}")
            raise RocksDBError(f"Failed to open database: {e}")
        
        # Track active transactions
        self._active_transactions = set()
        
    def put(self, node: Node) -> None:
        """
        Store a node in RocksDB.
        
        Args:
            node: Node to store
        """
        key = str(node.id).encode('utf-8')
        value = self.serializer.serialize(node)
        self.db.put(key, value)
        
    def get(self, node_id: UUID) -> Optional[Node]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: ID of the node to retrieve
            
        Returns:
            Node if found, None otherwise
        """
        key = str(node_id).encode('utf-8')
        value = self.db.get(key)
        
        if value is None:
            return None
            
        return self.serializer.deserialize(value)
        
    def delete(self, node_id: UUID) -> bool:
        """
        Delete a node by its ID.
        
        Args:
            node_id: ID of the node to delete
            
        Returns:
            True if node was deleted, False if not found
        """
        key = str(node_id).encode('utf-8')
        if self.db.get(key) is None:
            return False
            
        self.db.delete(key)
        return True
        
    def exists(self, node_id: UUID) -> bool:
        """
        Check if a node exists.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node exists, False otherwise
        """
        key = str(node_id).encode('utf-8')
        return self.db.get(key) is not None
        
    def list_ids(self) -> List[UUID]:
        """
        List all node IDs.
        
        Returns:
            List of all node IDs
        """
        it = self.db.iterkeys()
        it.seek_to_first()
        
        return [uuid.UUID(key.decode('utf-8')) for key in it]
        
    def count(self) -> int:
        """
        Count the number of nodes.
        
        Returns:
            Number of nodes in the store
        """
        # RocksDB doesn't have a built-in count method
        # This is not very efficient for large databases
        count = 0
        it = self.db.iterkeys()
        it.seek_to_first()
        
        for _ in it:
            count += 1
            
        return count
        
    def get_many(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """
        Retrieve multiple nodes by their IDs.
        
        Args:
            node_ids: IDs of the nodes to retrieve
            
        Returns:
            Dictionary mapping IDs to nodes
        """
        result = {}
        for node_id in node_ids:
            key = str(node_id).encode('utf-8')
            value = self.db.get(key)
            
            if value is not None:
                result[node_id] = self.serializer.deserialize(value)
                
        return result
        
    def put_many(self, nodes: List[Node]) -> None:
        """
        Store multiple nodes.
        
        Args:
            nodes: Nodes to store
        """
        # Use RocksDB WriteBatch for efficient batch operations
        batch = rocksdb.WriteBatch()
        
        for node in nodes:
            key = str(node.id).encode('utf-8')
            value = self.serializer.serialize(node)
            batch.put(key, value)
            
        self.db.write(batch)
        
    def create_transaction(self) -> RocksDBTransaction:
        """
        Create a new transaction.
        
        Returns:
            A new RocksDBTransaction object
        """
        tx = RocksDBTransaction(self.db, self.serializer)
        self._active_transactions.add(tx.transaction_id)
        return tx
        
    @contextmanager
    def transaction(self) -> ContextManager[RocksDBTransaction]:
        """
        Context manager for transactions.
        
        Usage:
            with store.transaction() as tx:
                # Use tx for operations
                tx.put(node)
                tx.commit()  # Must explicitly commit
                
        Returns:
            Transaction context manager
        """
        tx = self.create_transaction()
        try:
            yield tx
        finally:
            if not tx.committed:
                tx.rollback()
            tx.release_snapshot()
            self._active_transactions.remove(tx.transaction_id)
            
    def get_iterator(self, prefix: Optional[str] = None, reverse: bool = False) -> Iterator[Tuple[UUID, Node]]:
        """
        Get an iterator over nodes.
        
        Args:
            prefix: Optional prefix for node IDs
            reverse: Whether to iterate in reverse order
            
        Returns:
            Iterator yielding (node_id, node) tuples
        """
        it = self.db.iteritems() if not reverse else self.db.iteritems(reverse=True)
        
        if prefix:
            prefix_bytes = prefix.encode('utf-8')
            it.seek(prefix_bytes)
            
            # Iterate while keys start with prefix
            for key_bytes, value_bytes in it:
                key = key_bytes.decode('utf-8')
                if not key.startswith(prefix):
                    break
                    
                node_id = uuid.UUID(key)
                node = self.serializer.deserialize(value_bytes)
                yield (node_id, node)
        else:
            # Iterate all items
            it.seek_to_first() if not reverse else it.seek_to_last()
            
            for key_bytes, value_bytes in it:
                key = key_bytes.decode('utf-8')
                node_id = uuid.UUID(key)
                node = self.serializer.deserialize(value_bytes)
                yield (node_id, node)
                
    def clear(self) -> None:
        """
        Clear all data from the database.
        
        Warning: This deletes all nodes!
        """
        it = self.db.iterkeys()
        it.seek_to_first()
        
        batch = rocksdb.WriteBatch()
        for key in it:
            batch.delete(key)
            
        self.db.write(batch)
        
    def compact(self) -> None:
        """
        Manually trigger database compaction.
        
        This can be useful after many deletes or updates.
        """
        self.db.compact_range()
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        # Basic statistics
        stats = {
            "node_count": self.count(),
            "db_path": self.db_path,
            "active_transactions": len(self._active_transactions)
        }
        
        # Try to get property values from RocksDB
        properties = [
            "rocksdb.estimate-table-readers-mem",
            "rocksdb.cur-size-all-mem-tables",
            "rocksdb.size-all-mem-tables",
            "rocksdb.estimate-live-data-size",
            "rocksdb.num-snapshots"
        ]
        
        for prop in properties:
            try:
                value = self.db.get_property(prop)
                if value is not None:
                    # Convert to int if possible
                    try:
                        stats[prop.replace("rocksdb.", "")] = int(value)
                    except ValueError:
                        stats[prop.replace("rocksdb.", "")] = value
            except Exception as e:
                logger.warning(f"Failed to get property {prop}: {e}")
                
        return stats
    
    def backup(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path to store the backup
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Create a checkpoint
            checkpoint = rocksdb.Checkpoint(self.db)
            checkpoint.create_checkpoint(backup_path)
            
            logger.info(f"Created backup at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
        
    def close(self) -> None:
        """Close the database and release resources."""
        # RocksDB DB object will be garbage collected, 
        # but we can help by removing the reference
        logger.info(f"Closing RocksDB database at {self.db_path}")
        del self.db 
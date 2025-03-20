"""
RocksDB implementation of the NodeStore for Temporal-Spatial Knowledge Database.

This module provides a persistent storage implementation using RocksDB.
"""

import os
import json
import rocksdb
from typing import Dict, Optional, List, Any, Set, Iterator
from uuid import UUID
import uuid

from .node_store import NodeStore
from ..core.node_v2 import Node
from .serialization import NodeSerializer, SimpleNodeSerializer


class RocksDBNodeStore(NodeStore):
    """
    RocksDB implementation of NodeStore.
    
    This provides persistent storage of nodes using RocksDB.
    """
    
    def __init__(self, db_path: str, 
                 serializer: Optional[NodeSerializer] = None,
                 create_if_missing: bool = True):
        """
        Initialize a RocksDB node store.
        
        Args:
            db_path: Path to the RocksDB database
            serializer: Optional custom serializer (defaults to SimpleNodeSerializer)
            create_if_missing: Whether to create the database if it doesn't exist
        """
        self.db_path = db_path
        self.serializer = serializer or SimpleNodeSerializer()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Open RocksDB database
        opts = rocksdb.Options()
        opts.create_if_missing = create_if_missing
        self.db = rocksdb.DB(db_path, opts)
        
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
        
    def close(self) -> None:
        """Close the database and release resources."""
        # RocksDB DB object will be garbage collected, 
        # but we can help by removing the reference
        del self.db 
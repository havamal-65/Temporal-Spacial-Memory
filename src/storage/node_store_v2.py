"""
Storage interfaces and implementations for the Temporal-Spatial Knowledge Database.

This module provides abstract interfaces and concrete implementations for storing
and retrieving nodes from different storage backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Iterator, Union, Any
import os
import shutil
from uuid import UUID
import rocksdb

from ..core.node_v2 import Node
from ..core.exceptions import StorageError
from .serializers import NodeSerializer, get_serializer


class NodeStore(ABC):
    """
    Abstract base class for node storage.
    
    This class defines the interface that all node storage implementations must
    follow to be compatible with the database.
    """
    
    @abstractmethod
    def put(self, node: Node) -> None:
        """
        Store a node in the database.
        
        Args:
            node: The node to store
            
        Raises:
            StorageError: If the node cannot be stored
        """
        pass
    
    @abstractmethod
    def get(self, node_id: UUID) -> Optional[Node]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            The node if found, None otherwise
            
        Raises:
            StorageError: If there's an error retrieving the node
        """
        pass
    
    @abstractmethod
    def delete(self, node_id: UUID) -> None:
        """
        Delete a node from the database.
        
        Args:
            node_id: The ID of the node to delete
            
        Raises:
            StorageError: If the node cannot be deleted
        """
        pass
    
    @abstractmethod
    def update(self, node: Node) -> None:
        """
        Update an existing node.
        
        Args:
            node: The node with updated data
            
        Raises:
            StorageError: If the node cannot be updated
        """
        pass
    
    @abstractmethod
    def exists(self, node_id: UUID) -> bool:
        """
        Check if a node exists in the database.
        
        Args:
            node_id: The ID of the node to check
            
        Returns:
            True if the node exists, False otherwise
            
        Raises:
            StorageError: If there's an error checking node existence
        """
        pass
    
    @abstractmethod
    def batch_get(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """
        Retrieve multiple nodes by their IDs.
        
        Args:
            node_ids: List of node IDs to retrieve
            
        Returns:
            Dictionary mapping node IDs to nodes (excludes IDs not found)
            
        Raises:
            StorageError: If there's an error retrieving the nodes
        """
        pass
    
    @abstractmethod
    def batch_put(self, nodes: List[Node]) -> None:
        """
        Store multiple nodes at once.
        
        Args:
            nodes: List of nodes to store
            
        Raises:
            StorageError: If the nodes cannot be stored
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count the number of nodes in the database.
        
        Returns:
            Number of nodes in the database
            
        Raises:
            StorageError: If there's an error counting the nodes
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """
        Remove all nodes from the database.
        
        Raises:
            StorageError: If there's an error clearing the database
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close the database connection.
        
        Raises:
            StorageError: If there's an error closing the connection
        """
        pass
    
    @abstractmethod
    def __enter__(self):
        """Context manager entry."""
        return self
    
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class InMemoryNodeStore(NodeStore):
    """
    In-memory implementation of the NodeStore interface.
    
    This class provides a simple in-memory storage backend, useful for testing
    and small datasets.
    """
    
    def __init__(self):
        """Initialize an empty in-memory node store."""
        self.nodes: Dict[UUID, Node] = {}
    
    def put(self, node: Node) -> None:
        """Store a node in memory."""
        self.nodes[node.id] = node
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Retrieve a node by its ID."""
        return self.nodes.get(node_id)
    
    def delete(self, node_id: UUID) -> None:
        """Delete a node from memory."""
        if node_id in self.nodes:
            del self.nodes[node_id]
    
    def update(self, node: Node) -> None:
        """Update an existing node."""
        self.nodes[node.id] = node
    
    def exists(self, node_id: UUID) -> bool:
        """Check if a node exists in memory."""
        return node_id in self.nodes
    
    def batch_get(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """Retrieve multiple nodes by their IDs."""
        return {node_id: self.nodes[node_id] for node_id in node_ids if node_id in self.nodes}
    
    def batch_put(self, nodes: List[Node]) -> None:
        """Store multiple nodes at once."""
        for node in nodes:
            self.nodes[node.id] = node
    
    def count(self) -> int:
        """Count the number of nodes in memory."""
        return len(self.nodes)
    
    def clear(self) -> None:
        """Remove all nodes from memory."""
        self.nodes.clear()
    
    def close(self) -> None:
        """No-op for in-memory store."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
    
    def get_all(self) -> List[Node]:
        """Get all nodes in the store."""
        return list(self.nodes.values())
    
    def save_to_file(self, filepath: str, format: str = 'json') -> None:
        """
        Save the in-memory database to a file.
        
        Args:
            filepath: Path to save the database to
            format: Serialization format ('json' or 'msgpack')
            
        Raises:
            StorageError: If there's an error saving to file
        """
        import json
        try:
            serializer = get_serializer(format)
            nodes_data = {}
            
            for node_id, node in self.nodes.items():
                nodes_data[str(node_id)] = node.to_dict()
            
            with open(filepath, 'wb') as f:
                serialized = json.dumps(nodes_data).encode('utf-8') if format == 'json' else serializer.serialize(nodes_data)
                f.write(serialized)
        except Exception as e:
            raise StorageError(f"Failed to save in-memory database to file: {e}") from e
    
    def load_from_file(self, filepath: str, format: str = 'json') -> None:
        """
        Load the in-memory database from a file.
        
        Args:
            filepath: Path to load the database from
            format: Serialization format ('json' or 'msgpack')
            
        Raises:
            StorageError: If there's an error loading from file
        """
        import json
        try:
            serializer = get_serializer(format)
            
            with open(filepath, 'rb') as f:
                data = f.read()
                
            if format == 'json':
                nodes_data = json.loads(data.decode('utf-8'))
            else:
                nodes_data = serializer.deserialize(data)
            
            self.clear()
            for node_id_str, node_dict in nodes_data.items():
                node = Node.from_dict(node_dict)
                self.nodes[node.id] = node
        except Exception as e:
            raise StorageError(f"Failed to load in-memory database from file: {e}") from e


class RocksDBNodeStore(NodeStore):
    """
    RocksDB implementation of the NodeStore interface.
    
    This class provides a persistent storage backend for nodes using RocksDB.
    """
    
    def __init__(self, 
                 db_path: str, 
                 create_if_missing: bool = True, 
                 serialization_format: str = 'msgpack',
                 use_column_families: bool = True):
        """
        Initialize the RocksDB node store.
        
        Args:
            db_path: Path to the RocksDB database directory
            create_if_missing: Whether to create the database if it doesn't exist
            serialization_format: Format to use for serialization ('json' or 'msgpack')
            use_column_families: Whether to use column families for different data types
            
        Raises:
            StorageError: If the database cannot be opened
        """
        self.db_path = db_path
        self.serialization_format = serialization_format
        self.use_column_families = use_column_families
        self.serializer = get_serializer(serialization_format)
        
        # Column family names
        self.cf_nodes = b'nodes'
        self.cf_metadata = b'metadata'
        self.cf_indices = b'indices'
        
        try:
            # Set up RocksDB options
            self.options = rocksdb.Options()
            self.options.create_if_missing = create_if_missing
            self.options.create_missing_column_families = create_if_missing
            self.options.paranoid_checks = True
            self.options.max_open_files = 300
            self.options.write_buffer_size = 67108864  # 64MB
            self.options.max_write_buffer_number = 3
            self.options.target_file_size_base = 67108864  # 64MB
            
            # Configure compaction
            self.options.level0_file_num_compaction_trigger = 4
            self.options.level0_slowdown_writes_trigger = 8
            self.options.level0_stop_writes_trigger = 12
            self.options.num_levels = 7
            
            # Open the database
            if use_column_families:
                # Check if DB exists to determine existing column families
                if os.path.exists(db_path):
                    cf_names = rocksdb.list_column_families(self.options, db_path)
                    # Add our required column families if they don't exist
                    for cf in [self.cf_nodes, self.cf_metadata, self.cf_indices]:
                        if cf not in cf_names:
                            cf_names.append(cf)
                else:
                    # Default column families if creating new DB
                    cf_names = [b'default', self.cf_nodes, self.cf_metadata, self.cf_indices]
                
                # Create column family handles
                cf_options = []
                for _ in cf_names:
                    cf_opt = rocksdb.ColumnFamilyOptions()
                    cf_opt.write_buffer_size = 67108864  # 64MB
                    cf_opt.target_file_size_base = 67108864  # 64MB
                    cf_options.append(cf_opt)
                
                # Open DB with column families
                self.db, self.cf_handles = rocksdb.open_for_read_write_with_column_families(
                    db_path,
                    self.options,
                    [(name, opt) for name, opt in zip(cf_names, cf_options)]
                )
                
                # Store handles by name for easier access
                self.cf_handle_dict = {name: handle for name, handle in zip(cf_names, self.cf_handles)}
                self.default_handle = self.cf_handle_dict[b'default']
                self.nodes_handle = self.cf_handle_dict[self.cf_nodes]
                self.metadata_handle = self.cf_handle_dict[self.cf_metadata]
                self.indices_handle = self.cf_handle_dict[self.cf_indices]
            else:
                # Open DB without column families
                self.db = rocksdb.DB(db_path, self.options)
                self.cf_handles = []
                self.default_handle = None
        except Exception as e:
            raise StorageError(f"Failed to open RocksDB at {db_path}: {e}") from e
    
    def _get_handle(self, handle_type: bytes):
        """Get the appropriate column family handle."""
        if not self.use_column_families:
            return None
        
        if handle_type == self.cf_nodes:
            return self.nodes_handle
        elif handle_type == self.cf_metadata:
            return self.metadata_handle
        elif handle_type == self.cf_indices:
            return self.indices_handle
        else:
            return self.default_handle
    
    def _encode_key(self, key: Union[UUID, str, bytes]) -> bytes:
        """Encode a key to bytes."""
        if isinstance(key, UUID):
            return key.bytes
        elif isinstance(key, str):
            return key.encode('utf-8')
        return key
    
    def put(self, node: Node) -> None:
        """Store a node in the database."""
        try:
            # Serialize the node
            node_data = self.serializer.serialize(node)
            
            # Store the node
            node_key = self._encode_key(node.id)
            handle = self._get_handle(self.cf_nodes)
            
            if handle:
                self.db.put(node_key, node_data, handle)
            else:
                self.db.put(node_key, node_data)
        except Exception as e:
            raise StorageError(f"Failed to store node {node.id}: {e}") from e
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Retrieve a node by its ID."""
        try:
            node_key = self._encode_key(node_id)
            handle = self._get_handle(self.cf_nodes)
            
            # Get the node data
            if handle:
                node_data = self.db.get(node_key, handle)
            else:
                node_data = self.db.get(node_key)
            
            if node_data is None:
                return None
            
            # Deserialize the node
            return self.serializer.deserialize(node_data)
        except Exception as e:
            raise StorageError(f"Failed to retrieve node {node_id}: {e}") from e
    
    def delete(self, node_id: UUID) -> None:
        """Delete a node from the database."""
        try:
            node_key = self._encode_key(node_id)
            handle = self._get_handle(self.cf_nodes)
            
            # Delete the node
            if handle:
                self.db.delete(node_key, handle)
            else:
                self.db.delete(node_key)
        except Exception as e:
            raise StorageError(f"Failed to delete node {node_id}: {e}") from e
    
    def update(self, node: Node) -> None:
        """Update an existing node."""
        # Since RocksDB is a key-value store, update is the same as put
        self.put(node)
    
    def exists(self, node_id: UUID) -> bool:
        """Check if a node exists in the database."""
        try:
            node_key = self._encode_key(node_id)
            handle = self._get_handle(self.cf_nodes)
            
            # Check if the node exists
            if handle:
                return self.db.get(node_key, handle) is not None
            else:
                return self.db.get(node_key) is not None
        except Exception as e:
            raise StorageError(f"Failed to check if node {node_id} exists: {e}") from e
    
    def batch_get(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """Retrieve multiple nodes by their IDs."""
        result = {}
        
        try:
            # RocksDB doesn't have a native multi-get with column families,
            # so we retrieve nodes one by one
            for node_id in node_ids:
                node = self.get(node_id)
                if node:
                    result[node_id] = node
        except Exception as e:
            raise StorageError(f"Failed to batch retrieve nodes: {e}") from e
        
        return result
    
    def batch_put(self, nodes: List[Node]) -> None:
        """Store multiple nodes at once."""
        if not nodes:
            return
        
        try:
            # Create a write batch
            batch = rocksdb.WriteBatch()
            handle = self._get_handle(self.cf_nodes)
            
            # Add each node to the batch
            for node in nodes:
                node_key = self._encode_key(node.id)
                node_data = self.serializer.serialize(node)
                
                if handle:
                    batch.put(node_key, node_data, handle)
                else:
                    batch.put(node_key, node_data)
            
            # Write the batch
            self.db.write(batch)
        except Exception as e:
            raise StorageError(f"Failed to batch store nodes: {e}") from e
    
    def count(self) -> int:
        """Count the number of nodes in the database."""
        try:
            count = 0
            handle = self._get_handle(self.cf_nodes)
            
            # Iterate over all keys
            it = self.db.iterkeys() if not handle else self.db.iterkeys(handle)
            it.seek_to_first()
            
            for _ in it:
                count += 1
            
            return count
        except Exception as e:
            raise StorageError(f"Failed to count nodes: {e}") from e
    
    def clear(self) -> None:
        """Remove all nodes from the database."""
        try:
            # The most reliable way to clear a RocksDB database is to
            # close it, delete the files, and reopen it
            self.close()
            
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path)
            
            # Reopen the database
            self.__init__(self.db_path, create_if_missing=True, 
                         serialization_format=self.serialization_format,
                         use_column_families=self.use_column_families)
        except Exception as e:
            raise StorageError(f"Failed to clear database: {e}") from e
    
    def close(self) -> None:
        """Close the database connection."""
        try:
            # Delete the column family handles
            for handle in self.cf_handles:
                del handle
            
            # Delete the database
            del self.db
        except Exception as e:
            raise StorageError(f"Failed to close database: {e}") from e
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 
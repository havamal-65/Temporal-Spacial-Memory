"""
Delta storage for the delta chain system.

This module provides the DeltaStore interface and implementations
for storing and retrieving delta records.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID
import json
import rocksdb
import pickle
import time
import struct

from .records import DeltaRecord
from .operations import DeltaOperation
from ..storage.serialization import Serializer, JsonSerializer


class DeltaStore(ABC):
    """
    Abstract interface for storing and retrieving delta records.
    """
    
    @abstractmethod
    def store_delta(self, delta: DeltaRecord) -> None:
        """
        Store a delta record.
        
        Args:
            delta: The delta record to store
        """
        pass
        
    @abstractmethod
    def get_delta(self, delta_id: UUID) -> Optional[DeltaRecord]:
        """
        Retrieve a delta by ID.
        
        Args:
            delta_id: The ID of the delta to retrieve
            
        Returns:
            The delta record if found, None otherwise
        """
        pass
        
    @abstractmethod
    def get_deltas_for_node(self, node_id: UUID) -> List[DeltaRecord]:
        """
        Get all deltas for a node.
        
        Args:
            node_id: The ID of the node
            
        Returns:
            List of delta records for the node
        """
        pass
        
    @abstractmethod
    def get_latest_delta_for_node(self, node_id: UUID) -> Optional[DeltaRecord]:
        """
        Get the most recent delta for a node.
        
        Args:
            node_id: The ID of the node
            
        Returns:
            The most recent delta record, or None if no deltas exist
        """
        pass
        
    @abstractmethod
    def delete_delta(self, delta_id: UUID) -> bool:
        """
        Delete a delta.
        
        Args:
            delta_id: The ID of the delta to delete
            
        Returns:
            True if the delta was deleted, False if not found
        """
        pass
        
    @abstractmethod
    def get_deltas_in_time_range(self, 
                                node_id: UUID, 
                                start_time: float, 
                                end_time: float) -> List[DeltaRecord]:
        """
        Get deltas in a time range.
        
        Args:
            node_id: The ID of the node
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            
        Returns:
            List of delta records in the time range
        """
        pass


class DeltaSerializer:
    """
    Serializer for delta records.
    
    This class handles the serialization and deserialization of
    delta records and their operations.
    """
    
    def __init__(self):
        """Initialize the delta serializer."""
        self.json_serializer = JsonSerializer()
    
    def serialize_delta(self, delta: DeltaRecord) -> bytes:
        """
        Serialize a delta record to bytes.
        
        Args:
            delta: The delta record to serialize
            
        Returns:
            Serialized delta as bytes
        """
        # We can't directly serialize operation objects with JSON
        # So we need to convert them to a format we can serialize
        serialized_ops = []
        for op in delta.operations:
            op_dict = {
                "type": op.__class__.__name__,
                "data": {k: v for k, v in op.__dict__.items()}
            }
            serialized_ops.append(op_dict)
        
        delta_dict = {
            "node_id": str(delta.node_id),
            "delta_id": str(delta.delta_id),
            "timestamp": delta.timestamp,
            "previous_delta_id": str(delta.previous_delta_id) if delta.previous_delta_id else None,
            "operations": serialized_ops,
            "metadata": delta.metadata
        }
        
        return self.json_serializer.serialize(delta_dict)
    
    def deserialize_delta(self, data: bytes) -> DeltaRecord:
        """
        Deserialize bytes to a delta record.
        
        Args:
            data: Serialized delta bytes
            
        Returns:
            Deserialized delta record
            
        Raises:
            ValueError: If the data is invalid
        """
        try:
            delta_dict = self.json_serializer.deserialize(data)
            
            # Convert string UUIDs back to UUID objects
            node_id = UUID(delta_dict["node_id"])
            delta_id = UUID(delta_dict["delta_id"])
            previous_delta_id = UUID(delta_dict["previous_delta_id"]) if delta_dict["previous_delta_id"] else None
            
            # Reconstruct operations
            operations = []
            from . import operations as ops_module
            
            for op_dict in delta_dict["operations"]:
                op_type = op_dict["type"]
                op_data = op_dict["data"]
                
                # Get the operation class by name
                op_class = getattr(ops_module, op_type)
                
                # Create a new instance with the correct data
                op = object.__new__(op_class)
                op.__dict__.update(op_data)
                operations.append(op)
            
            # Create the delta record
            return DeltaRecord(
                node_id=node_id,
                timestamp=delta_dict["timestamp"],
                operations=operations,
                previous_delta_id=previous_delta_id,
                delta_id=delta_id,
                metadata=delta_dict["metadata"]
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize delta: {e}")


class RocksDBDeltaStore(DeltaStore):
    """
    RocksDB implementation of DeltaStore.
    
    This class stores delta records in a RocksDB database with
    efficient indexing for time-based queries.
    """
    
    # Key prefixes for different types of data
    DELTA_PREFIX = b'delta:'      # delta_id -> delta record
    NODE_PREFIX = b'node:'        # node_id -> list of delta_ids
    TIME_PREFIX = b'time:'        # node_id:timestamp -> delta_id
    LATEST_PREFIX = b'latest:'    # node_id -> latest delta_id
    
    def __init__(self, db_path: str, create_if_missing: bool = True):
        """
        Initialize the RocksDB delta store.
        
        Args:
            db_path: Path to the RocksDB database
            create_if_missing: Whether to create the database if it doesn't exist
        """
        # Create options
        opts = rocksdb.Options()
        opts.create_if_missing = create_if_missing
        opts.max_open_files = 300
        opts.write_buffer_size = 67108864  # 64MB
        opts.max_write_buffer_number = 3
        opts.target_file_size_base = 67108864  # 64MB
        
        # Create column family options
        cf_opts = rocksdb.ColumnFamilyOptions()
        
        # Define column families
        self.cf_names = [b'default', b'deltas', b'node_index', b'time_index']
        
        # Create column family descriptors
        cf_descriptors = [rocksdb.ColumnFamilyDescriptor(name, cf_opts) for name in self.cf_names]
        
        # Open the database
        self.db, self.cf_handles = rocksdb.DB.open_for_read_write(
            str(db_path),
            opts,
            cf_descriptors
        )
        
        # Get the column family handles
        self.deltas_cf = self.cf_handles[1]
        self.node_index_cf = self.cf_handles[2]
        self.time_index_cf = self.cf_handles[3]
        
        # Create a serializer
        self.serializer = DeltaSerializer()
    
    def _make_delta_key(self, delta_id: UUID) -> bytes:
        """Create a key for storing a delta record."""
        return self.DELTA_PREFIX + str(delta_id).encode()
    
    def _make_node_key(self, node_id: UUID) -> bytes:
        """Create a key for a node's delta list."""
        return self.NODE_PREFIX + str(node_id).encode()
    
    def _make_time_key(self, node_id: UUID, timestamp: float) -> bytes:
        """Create a time index key."""
        # Use a format that allows for range scans
        # node_id:timestamp (padded for lexicographic ordering)
        timestamp_bytes = struct.pack('>d', timestamp)  # Big-endian double
        return self.TIME_PREFIX + str(node_id).encode() + b':' + timestamp_bytes
    
    def _make_latest_key(self, node_id: UUID) -> bytes:
        """Create a key for the latest delta of a node."""
        return self.LATEST_PREFIX + str(node_id).encode()
    
    def _decode_time_key(self, key: bytes) -> Tuple[UUID, float]:
        """Decode a time index key to get node_id and timestamp."""
        if not key.startswith(self.TIME_PREFIX):
            raise ValueError(f"Not a time key: {key}")
            
        # Strip the prefix
        key = key[len(self.TIME_PREFIX):]
        
        # Split node_id and timestamp
        node_id_str, timestamp_bytes = key.split(b':')
        
        # Decode
        node_id = UUID(node_id_str.decode())
        timestamp = struct.unpack('>d', timestamp_bytes)[0]
        
        return node_id, timestamp
    
    def store_delta(self, delta: DeltaRecord) -> None:
        """Store a delta record."""
        # Serialize the delta
        serialized_delta = self.serializer.serialize_delta(delta)
        
        # Prepare batch
        batch = rocksdb.WriteBatch()
        
        # Add delta record
        delta_key = self._make_delta_key(delta.delta_id)
        batch.put(delta_key, serialized_delta, self.deltas_cf)
        
        # Add to node index
        node_key = self._make_node_key(delta.node_id)
        node_deltas = self.db.get(node_key, self.node_index_cf)
        
        if node_deltas:
            delta_ids = pickle.loads(node_deltas)
            delta_ids.append(delta.delta_id)
        else:
            delta_ids = [delta.delta_id]
            
        batch.put(node_key, pickle.dumps(delta_ids), self.node_index_cf)
        
        # Add to time index
        time_key = self._make_time_key(delta.node_id, delta.timestamp)
        batch.put(time_key, str(delta.delta_id).encode(), self.time_index_cf)
        
        # Update latest delta
        latest_key = self._make_latest_key(delta.node_id)
        current_latest = self.db.get(latest_key)
        
        if not current_latest or delta.timestamp > float(self.get_delta(UUID(current_latest.decode())).timestamp):
            batch.put(latest_key, str(delta.delta_id).encode())
        
        # Commit the batch
        self.db.write(batch)
    
    def get_delta(self, delta_id: UUID) -> Optional[DeltaRecord]:
        """Retrieve a delta by ID."""
        delta_key = self._make_delta_key(delta_id)
        serialized_delta = self.db.get(delta_key, self.deltas_cf)
        
        if not serialized_delta:
            return None
            
        return self.serializer.deserialize_delta(serialized_delta)
    
    def get_deltas_for_node(self, node_id: UUID) -> List[DeltaRecord]:
        """Get all deltas for a node."""
        node_key = self._make_node_key(node_id)
        node_deltas = self.db.get(node_key, self.node_index_cf)
        
        if not node_deltas:
            return []
            
        delta_ids = pickle.loads(node_deltas)
        result = []
        
        for delta_id in delta_ids:
            delta = self.get_delta(delta_id)
            if delta:
                result.append(delta)
        
        # Sort by timestamp
        result.sort(key=lambda d: d.timestamp)
        return result
    
    def get_latest_delta_for_node(self, node_id: UUID) -> Optional[DeltaRecord]:
        """Get the most recent delta for a node."""
        latest_key = self._make_latest_key(node_id)
        latest_id = self.db.get(latest_key)
        
        if not latest_id:
            return None
            
        return self.get_delta(UUID(latest_id.decode()))
    
    def delete_delta(self, delta_id: UUID) -> bool:
        """Delete a delta."""
        # Get the delta first to check if it exists and get its node_id
        delta = self.get_delta(delta_id)
        if not delta:
            return False
            
        # Prepare batch
        batch = rocksdb.WriteBatch()
        
        # Remove from delta storage
        delta_key = self._make_delta_key(delta_id)
        batch.delete(delta_key, self.deltas_cf)
        
        # Remove from node index
        node_key = self._make_node_key(delta.node_id)
        node_deltas = self.db.get(node_key, self.node_index_cf)
        
        if node_deltas:
            delta_ids = pickle.loads(node_deltas)
            delta_ids.remove(delta_id)
            batch.put(node_key, pickle.dumps(delta_ids), self.node_index_cf)
        
        # Remove from time index
        time_key = self._make_time_key(delta.node_id, delta.timestamp)
        batch.delete(time_key, self.time_index_cf)
        
        # Update latest delta if necessary
        latest_key = self._make_latest_key(delta.node_id)
        current_latest_bytes = self.db.get(latest_key)
        
        if current_latest_bytes and UUID(current_latest_bytes.decode()) == delta_id:
            # We're deleting the latest delta, so we need to find the new latest
            remaining_deltas = self.get_deltas_for_node(delta.node_id)
            if remaining_deltas:
                new_latest = max(remaining_deltas, key=lambda d: d.timestamp)
                batch.put(latest_key, str(new_latest.delta_id).encode())
            else:
                batch.delete(latest_key)
        
        # Commit the batch
        self.db.write(batch)
        return True
    
    def get_deltas_in_time_range(self, 
                                node_id: UUID, 
                                start_time: float, 
                                end_time: float) -> List[DeltaRecord]:
        """Get deltas in a time range."""
        # Create prefix for range scan
        prefix = self.TIME_PREFIX + str(node_id).encode() + b':'
        
        # Create start and end keys
        start_key = self._make_time_key(node_id, start_time)
        end_key = self._make_time_key(node_id, end_time)
        
        # Perform the range scan
        it = self.db.iteritems(self.time_index_cf)
        it.seek(start_key)
        
        result = []
        while it.valid():
            key, value = it.item()
            
            # Check if we're still in the range and the correct node
            if not key.startswith(prefix) or key > end_key:
                break
                
            # Get the delta
            delta_id = UUID(value.decode())
            delta = self.get_delta(delta_id)
            
            if delta:
                result.append(delta)
                
            it.next()
        
        # Sort by timestamp
        result.sort(key=lambda d: d.timestamp)
        return result
    
    def close(self) -> None:
        """Close the database."""
        for handle in self.cf_handles:
            self.db.close_column_family(handle)
        del self.db 
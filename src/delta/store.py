"""
Delta storage for the delta chain system.

This module provides the DeltaStore interface and implementations
for storing and retrieving delta records.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID
import json
import time
import struct

from .records import DeltaRecord
from .operations import DeltaOperation
from ..storage.serialization import SimpleNodeSerializer

try:
    import rocksdb
    ROCKSDB_AVAILABLE = True
except ImportError:
    ROCKSDB_AVAILABLE = False


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


class InMemoryDeltaStore(DeltaStore):
    def __init__(self):
        self.deltas: Dict[UUID, DeltaRecord] = {}
        self.node_index: Dict[UUID, List[UUID]] = {}

    def store_delta(self, delta: DeltaRecord) -> None:
        self.deltas[delta.delta_id] = delta
        if delta.node_id not in self.node_index:
            self.node_index[delta.node_id] = []
        self.node_index[delta.node_id].append(delta.delta_id)
        # Keep index sorted by timestamp
        self.node_index[delta.node_id].sort(key=lambda did: self.deltas[did].timestamp)

    def get_delta(self, delta_id: UUID) -> Optional[DeltaRecord]:
        return self.deltas.get(delta_id)

    def get_deltas_for_node(self, node_id: UUID) -> List[DeltaRecord]:
        ids = self.node_index.get(node_id, [])
        return [self.deltas[did] for did in ids]

    def get_latest_delta_for_node(self, node_id: UUID) -> Optional[DeltaRecord]:
        ids = self.node_index.get(node_id, [])
        if not ids:
            return None
        return self.deltas[ids[-1]]

    def delete_delta(self, delta_id: UUID) -> bool:
        delta = self.deltas.pop(delta_id, None)
        if not delta:
            return False
        if delta.node_id in self.node_index:
            self.node_index[delta.node_id] = [did for did in self.node_index[delta.node_id] if did != delta_id]
            if not self.node_index[delta.node_id]:
                del self.node_index[delta.node_id]
        return True

    def get_deltas_in_time_range(self, node_id: UUID, start_time: float, end_time: float) -> List[DeltaRecord]:
        ids = self.node_index.get(node_id, [])
        return [self.deltas[did] for did in ids if start_time <= self.deltas[did].timestamp <= end_time]


if ROCKSDB_AVAILABLE:
    class RocksDBDeltaStore(DeltaStore):
        # ... existing code ...
        pass
else:
    RocksDBDeltaStore = None 
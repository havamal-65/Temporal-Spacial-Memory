"""
Key management utilities for the Temporal-Spatial Knowledge Database.

This module provides utilities for generating and managing node IDs and
encoding keys for efficient storage and retrieval.
"""

import uuid
from typing import Union, Tuple, List, Optional, Any
from uuid import UUID
import struct
import time
import threading
import os
import hashlib


class IDGenerator:
    """
    Generator for unique node IDs.
    
    This class provides methods for generating unique IDs for nodes,
    with support for different ID schemes.
    """
    
    @staticmethod
    def generate_uuid4() -> UUID:
        """
        Generate a random UUID v4.
        
        Returns:
            A new UUID v4
        """
        return uuid.uuid4()
    
    @staticmethod
    def generate_uuid1() -> UUID:
        """
        Generate a time-based UUID v1.
        
        This UUID includes the MAC address of the machine and a timestamp,
        which can be useful for distributed systems.
        
        Returns:
            A new UUID v1
        """
        return uuid.uuid1()
    
    @staticmethod
    def generate_uuid5(namespace: UUID, name: str) -> UUID:
        """
        Generate a UUID v5 (SHA-1 hash of namespace and name).
        
        This can be useful for generating deterministic IDs for nodes
        with specific meaning.
        
        Args:
            namespace: The namespace UUID
            name: The name string
            
        Returns:
            A new UUID v5
        """
        return uuid.uuid5(namespace, name)
    
    @staticmethod
    def parse_uuid(uuid_str: str) -> UUID:
        """
        Parse a UUID string.
        
        Args:
            uuid_str: The UUID string to parse
            
        Returns:
            A UUID object
            
        Raises:
            ValueError: If the string is not a valid UUID
        """
        return UUID(uuid_str)
    
    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        """
        Check if a string is a valid UUID.
        
        Args:
            uuid_str: The string to check
            
        Returns:
            True if the string is a valid UUID, False otherwise
        """
        try:
            UUID(uuid_str)
            return True
        except (ValueError, AttributeError):
            return False


class TimeBasedIDGenerator:
    """
    Generator for time-based sequential IDs.
    
    This class generates IDs that include a timestamp component, making them
    naturally sortable by time.
    """
    
    def __init__(self, node_id: Optional[bytes] = None):
        """
        Initialize a time-based ID generator.
        
        Args:
            node_id: A unique identifier for this generator instance (default: machine ID)
        """
        if node_id is None:
            # Generate a unique node ID based on MAC address or hostname
            node_id = hashlib.md5(uuid.getnode().to_bytes(6, 'big')).digest()[:6]
        
        self.node_id = node_id
        self.sequence = 0
        self.last_timestamp = 0
        self.lock = threading.Lock()
    
    def generate(self) -> bytes:
        """
        Generate a time-based ID.
        
        The ID consists of:
        - 6 bytes: Unix timestamp in milliseconds
        - 6 bytes: Node ID
        - 4 bytes: Sequence number
        
        Returns:
            A 16-byte ID
        """
        with self.lock:
            timestamp = int(time.time() * 1000)
            
            # Handle clock skew by ensuring timestamp is always increasing
            if timestamp <= self.last_timestamp:
                timestamp = self.last_timestamp + 1
            
            # Reset sequence if timestamp has changed
            if timestamp != self.last_timestamp:
                self.sequence = 0
            
            # Update last timestamp
            self.last_timestamp = timestamp
            
            # Increment sequence
            self.sequence = (self.sequence + 1) & 0xFFFFFFFF
            
            # Pack the ID components
            id_bytes = (
                timestamp.to_bytes(6, 'big') +
                self.node_id +
                self.sequence.to_bytes(4, 'big')
            )
            
            return id_bytes
    
    def generate_uuid(self) -> UUID:
        """
        Generate a time-based ID as a UUID.
        
        Returns:
            A UUID containing the time-based ID
        """
        return UUID(bytes=self.generate())


class KeyEncoder:
    """
    Encoder for database keys.
    
    This class provides methods for encoding and decoding keys for storage
    in the database, with support for prefixing and range scanning.
    """
    
    # Prefix constants
    NODE_PREFIX = b'n:'  # Node data
    META_PREFIX = b'm:'  # Metadata
    TINDX_PREFIX = b't:'  # Temporal index
    SINDX_PREFIX = b's:'  # Spatial index
    RINDX_PREFIX = b'r:'  # Relationship index
    
    @staticmethod
    def encode_node_key(node_id: UUID) -> bytes:
        """
        Encode a node ID as a storage key.
        
        Args:
            node_id: The node ID to encode
            
        Returns:
            The encoded key
        """
        return KeyEncoder.NODE_PREFIX + node_id.bytes
    
    @staticmethod
    def decode_node_key(key: bytes) -> Optional[UUID]:
        """
        Decode a node key to a node ID.
        
        Args:
            key: The key to decode
            
        Returns:
            The node ID, or None if the key is not a node key
        """
        if key.startswith(KeyEncoder.NODE_PREFIX):
            return UUID(bytes=key[len(KeyEncoder.NODE_PREFIX):])
        return None
    
    @staticmethod
    def encode_meta_key(node_id: UUID, meta_key: str) -> bytes:
        """
        Encode a metadata key.
        
        Args:
            node_id: The node ID
            meta_key: The metadata key string
            
        Returns:
            The encoded key
        """
        return KeyEncoder.META_PREFIX + node_id.bytes + b':' + meta_key.encode('utf-8')
    
    @staticmethod
    def encode_temporal_index_key(timestamp: float, node_id: UUID) -> bytes:
        """
        Encode a temporal index key.
        
        Args:
            timestamp: The timestamp (Unix timestamp)
            node_id: The node ID
            
        Returns:
            The encoded key
        """
        # Pack the timestamp as a big-endian 8-byte float for correct sorting
        ts_bytes = struct.pack('>d', timestamp)
        return KeyEncoder.TINDX_PREFIX + ts_bytes + node_id.bytes
    
    @staticmethod
    def decode_temporal_index_key(key: bytes) -> Optional[Tuple[float, UUID]]:
        """
        Decode a temporal index key.
        
        Args:
            key: The key to decode
            
        Returns:
            Tuple of (timestamp, node_id), or None if not a temporal index key
        """
        if not key.startswith(KeyEncoder.TINDX_PREFIX):
            return None
        
        # Skip prefix
        key = key[len(KeyEncoder.TINDX_PREFIX):]
        
        # Extract timestamp and node ID
        ts_bytes = key[:8]
        node_id_bytes = key[8:]
        
        timestamp = struct.unpack('>d', ts_bytes)[0]
        node_id = UUID(bytes=node_id_bytes)
        
        return (timestamp, node_id)
    
    @staticmethod
    def encode_spatial_index_key(dimensions: Tuple[float, ...], node_id: UUID) -> bytes:
        """
        Encode a spatial index key.
        
        Args:
            dimensions: The spatial coordinates (x, y, z, ...)
            node_id: The node ID
            
        Returns:
            The encoded key
        """
        # Pack all dimensions as big-endian 8-byte floats for correct sorting
        dims_bytes = b''.join(struct.pack('>d', dim) for dim in dimensions)
        return KeyEncoder.SINDX_PREFIX + dims_bytes + node_id.bytes
    
    @staticmethod
    def get_temporal_range_bounds(start_time: float, end_time: float) -> Tuple[bytes, bytes]:
        """
        Get the range bounds for a temporal range query.
        
        Args:
            start_time: The start time (Unix timestamp)
            end_time: The end time (Unix timestamp)
            
        Returns:
            Tuple of (lower_bound, upper_bound) keys
        """
        lower_bound = KeyEncoder.TINDX_PREFIX + struct.pack('>d', start_time)
        upper_bound = KeyEncoder.TINDX_PREFIX + struct.pack('>d', end_time) + b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
        return (lower_bound, upper_bound)
    
    @staticmethod
    def get_spatial_range_bounds(min_dims: Tuple[float, ...], max_dims: Tuple[float, ...]) -> Tuple[bytes, bytes]:
        """
        Get the range bounds for a spatial range query.
        
        Args:
            min_dims: The minimum coordinates for each dimension
            max_dims: The maximum coordinates for each dimension
            
        Returns:
            Tuple of (lower_bound, upper_bound) keys
        """
        lower_bound = KeyEncoder.SINDX_PREFIX + b''.join(struct.pack('>d', dim) for dim in min_dims)
        upper_bound = KeyEncoder.SINDX_PREFIX + b''.join(struct.pack('>d', dim) for dim in max_dims) + b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
        return (lower_bound, upper_bound)
    
    @staticmethod
    def get_prefix_bounds(prefix: bytes) -> Tuple[bytes, bytes]:
        """
        Get the range bounds for a prefix query.
        
        Args:
            prefix: The key prefix
            
        Returns:
            Tuple of (lower_bound, upper_bound) keys
        """
        lower_bound = prefix
        upper_bound = prefix + b'\xff'
        return (lower_bound, upper_bound) 
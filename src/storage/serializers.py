"""
Serialization system for the Temporal-Spatial Knowledge Database.

This module provides interfaces and implementations for serializing and
deserializing nodes for storage.
"""

from abc import ABC, abstractmethod
import json
import uuid
from typing import Dict, Any, Union, Optional
from datetime import datetime
import msgpack

from ..core.node_v2 import Node
from ..core.exceptions import SerializationError


class NodeSerializer(ABC):
    """
    Abstract base class for node serializers.
    
    This class defines the interface that all node serializer implementations
    must adhere to.
    """
    
    @abstractmethod
    def serialize(self, node: Node) -> bytes:
        """
        Convert a node object to bytes for storage.
        
        Args:
            node: The node to serialize
            
        Returns:
            Serialized node as bytes
            
        Raises:
            SerializationError: If the node cannot be serialized
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Node:
        """
        Convert stored bytes back to a node object.
        
        Args:
            data: The serialized node data
            
        Returns:
            Deserialized Node object
            
        Raises:
            SerializationError: If the data cannot be deserialized
        """
        pass


class JSONSerializer(NodeSerializer):
    """
    JSON-based serializer for nodes.
    
    This serializer uses JSON for a human-readable, debug-friendly format.
    """
    
    def serialize(self, node: Node) -> bytes:
        """Serialize a node to JSON bytes."""
        try:
            node_dict = node.to_dict()
            return json.dumps(node_dict, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            raise SerializationError(f"Failed to serialize node to JSON: {e}") from e
    
    def deserialize(self, data: bytes) -> Node:
        """Deserialize JSON bytes to a node."""
        try:
            node_dict = json.loads(data.decode('utf-8'))
            return Node.from_dict(node_dict)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize node from JSON: {e}") from e


class MessagePackSerializer(NodeSerializer):
    """
    MessagePack-based serializer for nodes.
    
    This serializer uses MessagePack for a compact binary format that is more
    efficient than JSON.
    """
    
    def __init__(self, use_bin_type: bool = True):
        """
        Initialize the MessagePack serializer.
        
        Args:
            use_bin_type: Whether to use binary type for encoding
        """
        self.use_bin_type = use_bin_type
    
    def _encode_for_msgpack(self, obj: Any) -> Any:
        """Handle special types for MessagePack serialization."""
        if isinstance(obj, uuid.UUID):
            return {"__uuid__": obj.hex}
        elif isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        elif isinstance(obj, tuple):
            return {"__tuple__": list(obj)}
        elif isinstance(obj, set):
            return {"__set__": list(obj)}
        elif isinstance(obj, dict):
            return {k: self._encode_for_msgpack(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._encode_for_msgpack(item) for item in obj]
        return obj
    
    def _decode_from_msgpack(self, obj: Any) -> Any:
        """Handle special types when deserializing from MessagePack."""
        if isinstance(obj, dict):
            if "__uuid__" in obj and len(obj) == 1:
                return uuid.UUID(obj["__uuid__"])
            elif "__datetime__" in obj and len(obj) == 1:
                return datetime.fromisoformat(obj["__datetime__"])
            elif "__tuple__" in obj and len(obj) == 1:
                return tuple(self._decode_from_msgpack(item) for item in obj["__tuple__"])
            elif "__set__" in obj and len(obj) == 1:
                return set(self._decode_from_msgpack(item) for item in obj["__set__"])
            return {k: self._decode_from_msgpack(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decode_from_msgpack(item) for item in obj]
        return obj
    
    def serialize(self, node: Node) -> bytes:
        """Serialize a node to MessagePack bytes."""
        try:
            node_dict = node.to_dict()
            encoded_dict = self._encode_for_msgpack(node_dict)
            return msgpack.packb(encoded_dict, use_bin_type=self.use_bin_type)
        except Exception as e:
            raise SerializationError(f"Failed to serialize node to MessagePack: {e}") from e
    
    def deserialize(self, data: bytes) -> Node:
        """Deserialize MessagePack bytes to a node."""
        try:
            encoded_dict = msgpack.unpackb(data, raw=False)
            node_dict = self._decode_from_msgpack(encoded_dict)
            return Node.from_dict(node_dict)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize node from MessagePack: {e}") from e


# Factory function to get the appropriate serializer
def get_serializer(format: str = 'json') -> NodeSerializer:
    """
    Get a serializer instance for the specified format.
    
    Args:
        format: The serialization format ('json' or 'msgpack')
        
    Returns:
        A serializer instance
        
    Raises:
        ValueError: If the format is not supported
    """
    if format.lower() == 'json':
        return JSONSerializer()
    elif format.lower() in ('msgpack', 'messagepack'):
        return MessagePackSerializer()
    else:
        raise ValueError(f"Unsupported serialization format: {format}") 
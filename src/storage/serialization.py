"""
Serialization utilities for the Temporal-Spatial Knowledge Database.

This module provides serialization and deserialization functions for nodes.
"""

import json
import pickle
from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

from ..core.node_v2 import Node, NodeConnection


class NodeSerializer(ABC):
    """Abstract base class for node serializers."""
    
    @abstractmethod
    def serialize(self, node: Node) -> bytes:
        """Serialize a node to bytes."""
        pass
        
    @abstractmethod
    def deserialize(self, data: bytes) -> Node:
        """Deserialize bytes to a node."""
        pass


class SimpleNodeSerializer(NodeSerializer):
    """Simple JSON serializer for nodes."""
    
    def serialize(self, node: Node) -> bytes:
        """
        Serialize a node to JSON bytes.
        
        Args:
            node: Node to serialize
            
        Returns:
            JSON bytes representation
        """
        # Convert to JSON-serializable dict
        node_dict = {
            "id": str(node.id),
            "content": node.content,
            "position": node.position,
            "connections": [
                {
                    "target_id": str(conn.target_id),
                    "connection_type": conn.connection_type,
                    "strength": conn.strength,
                    "metadata": conn.metadata
                }
                for conn in node.connections
            ],
            "origin_reference": str(node.origin_reference) if node.origin_reference else None,
            "delta_information": node.delta_information,
            "metadata": node.metadata
        }
        
        # Serialize to JSON bytes
        return json.dumps(node_dict).encode('utf-8')
        
    def deserialize(self, data: bytes) -> Node:
        """
        Deserialize JSON bytes to a node.
        
        Args:
            data: JSON bytes representation
            
        Returns:
            Deserialized node
        """
        # Parse JSON
        node_dict = json.loads(data.decode('utf-8'))
        
        # Convert connections
        connections = []
        for conn_dict in node_dict.get("connections", []):
            connections.append(NodeConnection(
                target_id=UUID(conn_dict["target_id"]),
                connection_type=conn_dict["connection_type"],
                strength=conn_dict.get("strength", 1.0),
                metadata=conn_dict.get("metadata", {})
            ))
        
        # Convert origin reference
        origin_ref = None
        if node_dict.get("origin_reference"):
            origin_ref = UUID(node_dict["origin_reference"])
            
        # Create node
        return Node(
            id=UUID(node_dict["id"]),
            content=node_dict.get("content", {}),
            position=node_dict.get("position", (0.0, 0.0, 0.0)),
            connections=connections,
            origin_reference=origin_ref,
            delta_information=node_dict.get("delta_information", {}),
            metadata=node_dict.get("metadata", {})
        )


class PickleNodeSerializer(NodeSerializer):
    """Pickle serializer for nodes."""
    
    def serialize(self, node: Node) -> bytes:
        """
        Serialize a node using pickle.
        
        Args:
            node: Node to serialize
            
        Returns:
            Pickle bytes representation
        """
        return pickle.dumps(node)
        
    def deserialize(self, data: bytes) -> Node:
        """
        Deserialize pickle bytes to a node.
        
        Args:
            data: Pickle bytes representation
            
        Returns:
            Deserialized node
        """
        return pickle.loads(data)


def serialize_value(value: Any, format: str = 'json') -> bytes:
    """
    Serialize any value to bytes for storage.
    
    Args:
        value: The value to serialize
        format: The serialization format ('json' or 'pickle')
        
    Returns:
        Serialized value as bytes
        
    Raises:
        SerializationError: If the value cannot be serialized
    """
    if format == 'json':
        try:
            return json.dumps(value).encode('utf-8')
        except Exception as e:
            raise SerializationError(f"Failed to serialize value to JSON: {e}") from e
    elif format == 'pickle':
        try:
            return pickle.dumps(value)
        except Exception as e:
            raise SerializationError(f"Failed to serialize value with pickle: {e}") from e
    else:
        raise SerializationError(f"Unsupported serialization format: {format}")


def deserialize_value(data: bytes, format: str = 'json') -> Any:
    """
    Deserialize a value from bytes.
    
    Args:
        data: The serialized value data
        format: The serialization format ('json' or 'pickle')
        
    Returns:
        Deserialized value
        
    Raises:
        SerializationError: If the value cannot be deserialized
    """
    if format == 'json':
        try:
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            raise SerializationError(f"Failed to deserialize value from JSON: {e}") from e
    elif format == 'pickle':
        try:
            return pickle.loads(data)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize value with pickle: {e}") from e
    else:
        raise SerializationError(f"Unsupported serialization format: {format}") 
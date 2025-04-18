"""
Storage module for the Temporal-Spatial Knowledge Database.

This module provides storage backends for persisting nodes and their relationships.
"""

from .node_store import NodeStore

# Try to import serializers
try:
    from .serializers import JSONSerializer, MessagePackSerializer, get_serializer
    SERIALIZERS_AVAILABLE = True
except ImportError:
    SERIALIZERS_AVAILABLE = False

__all__ = [
    'NodeStore',
    'SERIALIZERS_AVAILABLE'
]

# Add serializer exports if available
if SERIALIZERS_AVAILABLE:
    __all__.extend(['JSONSerializer', 'MessagePackSerializer', 'get_serializer']) 
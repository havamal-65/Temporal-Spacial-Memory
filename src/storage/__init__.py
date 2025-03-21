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

# Try to import RocksDB, but don't fail if it's not available
try:
    from .rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError:
    ROCKSDB_AVAILABLE = False
    # Create a mock RocksDBNodeStore that raises an informative error if used
    class RocksDBNodeStore:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The RocksDB Python package is not installed. "
                "Please install it with: pip install python-rocksdb"
            )

__all__ = [
    'NodeStore',
    'RocksDBNodeStore',
    'ROCKSDB_AVAILABLE',
    'SERIALIZERS_AVAILABLE'
]

# Add serializer exports if available
if SERIALIZERS_AVAILABLE:
    __all__.extend(['JSONSerializer', 'MessagePackSerializer', 'get_serializer']) 
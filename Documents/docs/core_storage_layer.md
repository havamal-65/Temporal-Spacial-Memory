# Core Storage Layer for Temporal-Spatial Database

This document provides an overview of the Core Storage Layer implementation for the Temporal-Spatial Knowledge Database, focusing on the v2 components.

## Components Overview

The Core Storage Layer consists of the following main components:

1. **Node Structure** - The fundamental data structure for storing knowledge points.
2. **Serialization System** - Converts nodes to/from bytes for storage.
3. **Storage Engine** - Manages the persistent storage of nodes.
4. **Cache System** - Improves performance by reducing database access.
5. **Key Management** - Handles node IDs and key encoding for storage.
6. **Error Handling** - Provides robust error handling and retry mechanisms.

## Node Structure

The fundamental data structure is the `Node` class, which represents a point of knowledge in the temporal-spatial continuum:

```python
class Node:
    id: UUID                         # Unique identifier
    content: Dict[str, Any]          # Main content/payload
    position: Tuple[float, float, float]  # Cylindrical coordinates (t, r, θ)
    connections: List[NodeConnection] # Connections to other nodes
    origin_reference: Optional[UUID]  # Reference to originating node
    delta_information: Dict[str, Any] # Information for delta operations
    metadata: Dict[str, Any]         # Additional metadata
```

Nodes are connected to other nodes through the `NodeConnection` class:

```python
class NodeConnection:
    target_id: UUID                  # Target node ID
    connection_type: str             # Type of connection
    strength: float                  # Connection strength (0.0-1.0)
    metadata: Dict[str, Any]         # Connection metadata
```

## Serialization System

The serialization system provides a consistent interface for converting nodes to and from bytes for storage. Two serialization formats are supported:

1. **JSON** - Human-readable format, useful for debugging and export.
2. **MessagePack** - Compact binary format, more efficient for storage and retrieval.

The system handles special types like UUIDs, complex nested structures, and temporal coordinates with high precision.

## Storage Engine

The storage engine provides a unified interface for storing and retrieving nodes:

```python
class NodeStore(ABC):
    def put(self, node: Node) -> None: ...
    def get(self, node_id: UUID) -> Optional[Node]: ...
    def delete(self, node_id: UUID) -> None: ...
    def update(self, node: Node) -> None: ...
    def exists(self, node_id: UUID) -> bool: ...
    def batch_get(self, node_ids: List[UUID]) -> Dict[UUID, Node]: ...
    def batch_put(self, nodes: List[Node]) -> None: ...
    def count(self) -> int: ...
    def clear(self) -> None: ...
    def close(self) -> None: ...
```

Two implementations are provided:

1. **InMemoryNodeStore** - Simple in-memory storage for testing and small datasets.
2. **RocksDBNodeStore** - Persistent storage backed by RocksDB for production use.

The RocksDB implementation includes optimizations like:
- Configurable column families for different types of data
- Efficient batch operations
- Custom key encoding for range scans

## Cache System

The cache system improves performance by reducing the number of database accesses:

```python
class NodeCache(ABC):
    def get(self, node_id: UUID) -> Optional[Node]: ...
    def put(self, node: Node) -> None: ...
    def invalidate(self, node_id: UUID) -> None: ...
    def clear(self) -> None: ...
    def size(self) -> int: ...
```

Three cache implementations are provided:

1. **LRUCache** - Least Recently Used cache, evicts the least recently accessed nodes.
2. **TemporalAwareCache** - Prioritizes nodes in the current time window of interest.
3. **CacheChain** - Combines multiple caches in a hierarchy.

## Key Management

The key management system provides utilities for generating and managing node IDs:

1. **IDGenerator** - Generates UUIDs for nodes with various strategies.
2. **TimeBasedIDGenerator** - Generates IDs that include a timestamp component.
3. **KeyEncoder** - Encodes keys for efficient storage and range scanning.

## Error Handling

The error handling system provides robust mechanisms for dealing with errors:

1. **Exception Hierarchy** - Domain-specific exceptions for different error types.
2. **Retry Mechanism** - Decorator for retrying operations on transient errors.
3. **Circuit Breaker** - Prevents repeated failures by temporarily stopping operations.
4. **Error Tracking** - Monitors error patterns and adjusts behavior accordingly.

## Usage Example

Here's a basic example of using the core storage layer:

```python
from src.core.node_v2 import Node
from src.storage.node_store_v2 import RocksDBNodeStore
from src.storage.cache import LRUCache

# Create a node
node = Node(
    content={"name": "Example Node", "value": 42},
    position=(time.time(), 5.0, 1.5),  # (time, radius, theta)
)

# Add a connection to another node
node.add_connection(
    target_id=uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    connection_type="reference",
    strength=0.7
)

# Create a RocksDB store with a cache
store = RocksDBNodeStore(
    db_path="./my_database",
    create_if_missing=True,
    serialization_format='msgpack'
)
cache = LRUCache(max_size=1000)

# Store the node
store.put(node)
cache.put(node)

# Retrieve the node (first check cache, then store)
retrieved_node = cache.get(node.id)
if retrieved_node is None:
    retrieved_node = store.get(node.id)
    if retrieved_node:
        cache.put(retrieved_node)
```

## Performance Considerations

The core storage layer is designed with the following performance considerations:

1. **Efficient Serialization** - MessagePack provides more compact serialization than JSON.
2. **Batch Operations** - Batch put/get operations for improved performance.
3. **Caching** - Multiple caching strategies to reduce database access.
4. **Concurrency** - Thread-safe implementations for concurrent access.
5. **Error Resilience** - Retry mechanisms and circuit breakers for handling transient errors.

## Future Improvements

Potential future improvements to the core storage layer include:

1. **Distributed Storage** - Support for distributed storage across multiple machines.
2. **Compression** - Data compression for more efficient storage.
3. **Encryption** - Encryption of sensitive data.
4. **Secondary Indices** - More advanced indexing for complex queries.
5. **Streaming** - Support for streaming large result sets. 
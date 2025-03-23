# Temporal-Spatial Memory Database

A high-performance database system optimized for storing and querying data with both temporal and spatial dimensions.

## Project Status

- **Sprint 1**: ✅ Completed - Core Storage, Spatial Indexing, and Query Building
- **Sprint 2**: ✅ Completed - Query Engine, Combined Temporal-Spatial Indexing, and Testing
- **Sprint 3**: 🔄 Planned - API Design and Delta Optimization

## Key Features

- **Multi-dimensional indexing**: Efficiently query data across both time and space dimensions
- **Immutable time-series storage**: Track changes to spatial data over time
- **High-performance queries**: Optimized query execution with cost-based optimization
- **Efficient storage**: RocksDB-based storage with compression and batching
- **Flexible query API**: Build complex temporal and spatial queries with an intuitive API

## Project Components

### Core Infrastructure

- **Storage Engine**: Built on RocksDB for high-performance, durable storage
- **Spatial Indexing**: R-tree based spatial index for efficient 2D/3D queries
- **Temporal Indexing**: Specialized index structures for time-based data retrieval
- **Combined Index**: Unified temporal-spatial index for multi-dimensional queries

### Query System

- **Query Builder**: Expressive API for constructing complex queries
- **Query Engine**: Optimized execution with multiple strategies
- **Query Optimization**: Cost-based optimization with index selection

### Testing & Performance

- **Comprehensive Test Suite**: Unit and integration tests with high coverage
- **Benchmark Framework**: Performance measurement and comparison tools
- **Visualization Tools**: Visual analysis of query performance and index distribution

## Getting Started

### Prerequisites

- Python 3.8+
- RocksDB
- Required Python packages (see requirements.txt)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/temporal-spatial-memory.git

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from src.query.query_builder import QueryBuilder
from src.query.query_engine import QueryEngine
from src.storage.rocksdb_store import RocksDBStore

# Initialize storage
store = RocksDBStore("path/to/db")

# Create a query engine
engine = QueryEngine(store)

# Build and execute a query
result = (QueryBuilder()
    .spatial_within(center=(37.7749, -122.4194), radius=5000)  # meters
    .temporal_range(start='2023-01-01', end='2023-01-31')
    .execute(engine))

# Process results
for item in result:
    print(item)
```

## Project Structure

```
src/
├── core/              # Core data structures and utilities
├── delta/             # Change tracking and versioning
├── indexing/          # Spatial, temporal and combined indexing
│   ├── rtree.py       # R-tree spatial index implementation
│   ├── combined_index.py  # Combined temporal-spatial index
│   └── test_combined_index.py  # Tests for combined index
├── models/            # Data models and schemas
├── query/             # Query building and execution
│   ├── query_builder.py  # Fluent API for building queries
│   ├── query_engine.py   # Query execution and optimization
│   └── test_query_engine.py  # Tests for query engine
├── storage/           # Storage backends
│   └── rocksdb_store.py  # RocksDB integration
└── tests/             # Test suites
    └── benchmarks/    # Performance benchmarks
        ├── benchmark_framework.py  # Benchmark utilities
        └── benchmark_query_engine.py  # Query performance tests
```

## Performance

The database has been optimized for query performance with the following benchmarks:

- Spatial queries: ~35% faster than traditional approaches
- Combined temporal-spatial queries: Efficient pruning reduces query time by up to 60%
- Bulk loading: Optimized for fast data ingestion

## Contributing

Contributions are welcome! Please check the issues page for current tasks or create a new issue to discuss proposed changes.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
# Temporal-Spatial Memory Database Performance Tuning Guide

This guide provides detailed information on optimizing the performance of your Temporal-Spatial Memory Database deployment. It covers configuration adjustments, indexing strategies, query optimization, and hardware considerations.

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [Hardware Recommendations](#hardware-recommendations)
3. [RocksDB Tuning](#rocksdb-tuning)
4. [Index Optimization](#index-optimization)
5. [Query Optimization](#query-optimization)
6. [Caching Strategies](#caching-strategies)
7. [Delta Storage Tuning](#delta-storage-tuning)
8. [Bulk Operations](#bulk-operations)
9. [API Server Scaling](#api-server-scaling)
10. [Monitoring Performance](#monitoring-performance)
11. [Benchmarking](#benchmarking)
12. [Frequently Asked Questions](#frequently-asked-questions)

## Performance Overview

The Temporal-Spatial Memory Database balances several performance factors:

- **Query Speed**: How quickly results are returned
- **Insertion Rate**: How many nodes can be added per second
- **Storage Efficiency**: How compactly data is stored
- **Memory Usage**: RAM requirements for operation
- **Scaling Characteristics**: How performance changes with data size

Understanding your specific workload characteristics is essential for effective tuning:

- **Read-heavy** workloads benefit from aggressive caching and index optimization
- **Write-heavy** workloads benefit from batching and tuned RocksDB settings
- **Mixed workloads** require balanced optimizations

## Hardware Recommendations

### Minimum Requirements

- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: SSD with at least 50GB free space
- **Network**: 1 Gbps (for distributed deployments)

### Recommended for Production

- **CPU**: 8+ cores (preferably high clock speed)
- **RAM**: 32GB+
- **Storage**: NVMe SSD with 500GB+ free space
- **Network**: 10 Gbps (for distributed deployments)

### Resource Allocation Guidelines

| Database Size | Recommended RAM | Recommended CPU | Storage |
|---------------|----------------|----------------|---------|
| < 1 million nodes | 8GB | 4 cores | 50GB SSD |
| 1-10 million nodes | 16GB | 8 cores | 200GB SSD |
| 10-100 million nodes | 32GB | 16 cores | 1TB NVMe |
| 100M+ nodes | 64GB+ | 32+ cores | 2TB+ NVMe |

## RocksDB Tuning

RocksDB is the underlying storage engine and can be tuned for different workloads.

### Memory Usage

```python
# In config.py or environment variables
ROCKSDB_WRITE_BUFFER_SIZE = 67108864  # 64MB
ROCKSDB_MAX_WRITE_BUFFER_NUMBER = 3
ROCKSDB_TARGET_FILE_SIZE_BASE = 67108864  # 64MB
ROCKSDB_MAX_BACKGROUND_COMPACTIONS = 4
ROCKSDB_MAX_BACKGROUND_FLUSHES = 2
ROCKSDB_BLOCK_CACHE_SIZE = 8589934592  # 8GB
```

#### For Write-Heavy Workloads

```python
ROCKSDB_WRITE_BUFFER_SIZE = 134217728  # 128MB
ROCKSDB_MAX_WRITE_BUFFER_NUMBER = 6
ROCKSDB_LEVEL0_SLOWDOWN_WRITES_TRIGGER = 20
ROCKSDB_LEVEL0_STOP_WRITES_TRIGGER = 36
ROCKSDB_MAX_BACKGROUND_COMPACTIONS = 8
ROCKSDB_MAX_BACKGROUND_FLUSHES = 4
```

#### For Read-Heavy Workloads

```python
ROCKSDB_BLOCK_CACHE_SIZE = 17179869184  # 16GB
ROCKSDB_CACHE_INDEX_AND_FILTER_BLOCKS = True
ROCKSDB_PIN_L0_FILTER_AND_INDEX_BLOCKS_IN_CACHE = True
ROCKSDB_BLOOM_FILTER_BITS_PER_KEY = 10
```

### Compression Settings

```python
# Lighter compression = faster processing but more disk space
ROCKSDB_COMPRESSION_TYPE = "lz4"  # Options: "none", "snappy", "lz4", "zstd"
ROCKSDB_COMPRESSION_LEVEL = 3     # Higher = better compression but slower
```

### Filesystem Optimizations

```bash
# For Linux systems, configure the filesystem
sudo blockdev --setra 16384 /dev/nvme0n1  # Set readahead
sudo echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

## Index Optimization

### Spatial Index Tuning

The R-tree spatial index can be optimized for different query patterns:

```python
# In config.py
RTREE_MAX_CHILDREN = 16    # Default: 4, increase for more dense data
RTREE_MIN_CHILDREN = 4     # Default: 2, typically 1/4 of MAX_CHILDREN
RTREE_REINSERT_PERCENTAGE = 30  # Percentage of nodes to reinsert on split
RTREE_DIMENSION = 2        # 2 for lat/lon, 3 for x/y/z
```

#### Finding Optimal Node Size

R-tree performance is highly dependent on the node size. Use the benchmark tool to find the optimal value:

```bash
python -m src.benchmarks.rtree_tuning --min-children 4 --max-children 64 --step 4
```

### Temporal Index Tuning

```python
# In config.py
TEMPORAL_INDEX_BUCKET_SIZE = 86400  # One day in seconds
TEMPORAL_INDEX_CACHE_SIZE = 1000    # Number of recent timestamps to keep in memory
```

### Combined Index Parameters

```python
# In config.py
COMBINED_INDEX_SPATIAL_WEIGHT = 0.7  # Weight for spatial component (0.0-1.0)
COMBINED_INDEX_TEMPORAL_WEIGHT = 0.3  # Weight for temporal component
COMBINED_INDEX_REBALANCE_THRESHOLD = 10000  # Nodes before rebalancing
```

#### Index Auto-Tuning

Enable the auto-tuning feature to periodically optimize index parameters based on actual query patterns:

```python
# In config.py
INDEX_AUTO_TUNE = True
INDEX_TUNE_INTERVAL = 86400  # Seconds between tuning runs (daily)
```

## Query Optimization

### Query Parameters

```python
# In config.py
QUERY_TIMEOUT = 30  # Maximum query execution time in seconds
QUERY_MAX_RESULTS = 10000  # Maximum results per query
QUERY_BATCH_SIZE = 1000  # Process results in batches of this size
```

### Query Planning

The query engine uses statistics to optimize execution plans. Rebuild statistics periodically:

```python
# Using the client SDK
client.rebuild_statistics()
```

### Common Query Patterns Optimization

#### Optimize for Spatial-First Queries

If your application primarily queries by location first:

```python
# In config.py
COMBINED_INDEX_SPATIAL_WEIGHT = 0.8
COMBINED_INDEX_TEMPORAL_WEIGHT = 0.2
```

#### Optimize for Temporal-First Queries

If your application primarily queries by time ranges first:

```python
# In config.py
COMBINED_INDEX_SPATIAL_WEIGHT = 0.3
COMBINED_INDEX_TEMPORAL_WEIGHT = 0.7
```

### Query Rewriting Hints

Certain query patterns can be rewritten for better performance:

- Replace large polygon queries with multiple smaller bounding box queries
- Use `nearest_neighbors` with a small `k` instead of large radius searches
- For very large result sets, paginate using `limit` and `offset`
- Use property filters that take advantage of the property index

## Caching Strategies

### Memory Cache Configuration

```python
# In config.py
CACHE_ENABLED = True
CACHE_MAX_SIZE = 100000  # Maximum nodes in cache
CACHE_TTL = 3600  # Time-to-live in seconds
CACHE_STRATEGY = "lru"  # Options: "lru", "lfu"
```

### Query Cache

```python
# In config.py
QUERY_CACHE_ENABLED = True
QUERY_CACHE_SIZE = 1000  # Number of queries to cache
QUERY_CACHE_TTL = 300  # Seconds to cache query results
```

### External Caching

For high-throughput systems, consider adding Redis:

```python
# In config.py
REDIS_ENABLED = True
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = "your_password"
REDIS_PREFIX = "tsdb:"
```

### Selective Caching

Configure which node types to prioritize in cache:

```python
# In config.py
CACHE_PRIORITY_PROPERTIES = [
    {"field": "category", "value": "high_priority", "weight": 2.0},
    {"field": "updated_frequency", "value": "high", "weight": 1.5}
]
```

## Delta Storage Tuning

### Compression Settings

```python
# In config.py
DELTA_COMPRESSION_ENABLED = True
DELTA_COMPRESSION_ALGORITHM = "zstd"  # Options: "zstd", "lz4", "gzip"
DELTA_COMPRESSION_LEVEL = 3  # Higher = better compression but slower
```

### Delta Chain Optimization

```python
# In config.py
DELTA_MAX_CHAIN_LENGTH = 50  # Maximum deltas before compaction
DELTA_COMPACTION_INTERVAL = 86400  # Seconds between compaction runs
DELTA_COMPACTION_THRESHOLD = 20  # Compact chains longer than this
```

### Pruning Configuration

```python
# In config.py
DELTA_PRUNING_ENABLED = True
DELTA_MAX_AGE_DAYS = 90  # Maximum age of deltas to keep
DELTA_KEEP_VERSIONS = 10  # Minimum versions to keep regardless of age
```

## Bulk Operations

### Batch Insertion

Tune batch sizes for optimal throughput:

```python
# In config.py
BULK_INSERT_BATCH_SIZE = 5000  # Nodes per batch
BULK_INSERT_WORKERS = 4  # Parallel workers
```

Example of efficient bulk loading:

```python
# Using the Python SDK
nodes = [...]  # Large list of nodes

# Inefficient way:
# for node in nodes:
#     client.create_node(node)  # Slow - one request per node

# Efficient way:
for i in range(0, len(nodes), 5000):
    batch = nodes[i:i+5000]
    client.batch_create_nodes(batch)
```

### Bulk Index Building

For initial data loading, disable automatic indexing and build indices afterward:

```python
# Using the Python SDK
client.set_config("AUTO_INDEXING", False)

# Bulk insert data
for batch in data_batches:
    client.batch_create_nodes(batch)

# Build indices after all data is loaded
client.rebuild_indices()
client.set_config("AUTO_INDEXING", True)
```

## API Server Scaling

### Worker Processes

```python
# In config.py or command line
API_WORKERS = 8  # Number of worker processes
API_THREADS = 4  # Threads per worker
```

### Connection Pooling

```python
# In config.py
DB_CONNECTION_POOL_SIZE = 20  # Maximum concurrent database connections
DB_CONNECTION_MAX_OVERFLOW = 10  # Additional connections when pool is full
DB_CONNECTION_POOL_RECYCLE = 3600  # Seconds before recycling a connection
```

### Rate Limiting

```python
# In config.py
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DEFAULT = "1000/hour"  # Default rate limit
RATE_LIMIT_QUERY = "100/minute"   # Rate limit for query endpoint
RATE_LIMIT_BATCH = "50/minute"    # Rate limit for batch operations
```

## Monitoring Performance

### Performance Metrics

Key metrics to monitor:

1. Query response time (average, 95th percentile, 99th percentile)
2. Queries per second
3. Inserts per second
4. Cache hit ratio
5. Index traversal statistics
6. RocksDB compaction statistics
7. Memory usage

### Prometheus Integration

```python
# In config.py
PROMETHEUS_ENABLED = True
PROMETHEUS_PORT = 9090
```

Example metrics exposed:

```
# HELP tsdb_query_duration_seconds Query execution time in seconds
# TYPE tsdb_query_duration_seconds histogram
tsdb_query_duration_seconds_bucket{query_type="spatial",le="0.1"} 12
tsdb_query_duration_seconds_bucket{query_type="spatial",le="0.5"} 45
tsdb_query_duration_seconds_bucket{query_type="spatial",le="1.0"} 78
```

### Logging Configuration

```python
# In config.py
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_QUERY_STATS = True  # Log statistics for each query
```

For performance debugging:

```python
LOG_LEVEL = "DEBUG"
LOG_SLOW_QUERIES = True
LOG_SLOW_QUERY_THRESHOLD = 1.0  # Log queries taking more than 1 second
```

## Benchmarking

Use the built-in benchmark framework to evaluate performance:

```bash
# Run standard benchmark suite
python -m src.tests.benchmarks.benchmark_runner

# Run specific benchmark
python -m src.tests.benchmarks.benchmark_query_engine

# Run with custom parameters
python -m src.tests.benchmarks.benchmark_runner --nodes 1000000 --queries 1000
```

### Performance Baseline

Expected performance characteristics on recommended hardware:

| Operation | Data Size | Expected Performance |
|-----------|-----------|----------------------|
| Node insertion | 1M nodes | 10,000+ nodes/second |
| Point lookup | 1M nodes | < 1ms per node |
| Spatial radius query (100m) | 1M nodes | < 10ms |
| Spatial radius query (1km) | 1M nodes | < 50ms |
| Temporal range query (1 day) | 1M nodes | < 20ms |
| Combined query | 1M nodes | < 100ms |
| Bulk loading | 1M nodes | > 50,000 nodes/second |

## Frequently Asked Questions

### How do I determine the optimal R-tree parameters for my data?

Run the R-tree tuning benchmark with your actual data distribution:

```bash
python -m src.benchmarks.rtree_tuning --data-sample-file my_data_sample.json
```

This will test various parameter combinations and recommend the optimal settings.

### What's the most impactful change for improving query performance?

The most effective improvements are typically:

1. Ensure all queries leverage the combined index
2. Increase cache size to keep frequently accessed nodes in memory
3. Use SSDs instead of HDDs for storage
4. Add property filters to reduce result set sizes

### How can I optimize for time-travel queries?

Time-travel queries (as_of) are more expensive than regular queries since they need to reconstruct historical states:

1. Increase the `DELTA_COMPACTION_INTERVAL` for more efficient historical reconstruction
2. Add a dedicated cache for historical versions: `HISTORICAL_CACHE_SIZE = 10000`
3. For frequently accessed historical snapshots, consider materializing them: `MATERIALIZE_SNAPSHOTS = True`

### How can I reduce disk space usage?

1. Enable delta compression: `DELTA_COMPRESSION_ENABLED = True`
2. Use aggressive compression for RocksDB: `ROCKSDB_COMPRESSION_TYPE = "zstd"` with `ROCKSDB_COMPRESSION_LEVEL = 6`
3. Enable delta pruning to remove old historical versions: `DELTA_PRUNING_ENABLED = True`
4. Consider data archiving for very old data that's rarely accessed

### What are the most common performance bottlenecks?

1. **Disk I/O**: Use NVMe SSDs and ensure proper filesystem configuration
2. **Memory pressure**: Increase cache sizes and tune RocksDB memory usage
3. **CPU saturation**: Add more cores or distribute the workload
4. **Network latency**: Use connection pooling and minimize round trips

### How should I tune for Docker/containerized environments?

1. Ensure adequate CPU allocation: at least 4 dedicated cores
2. Provide enough memory: minimum 8GB, recommended 16GB+
3. Use volume mounts with high-performance storage
4. Adjust JVM settings if using JVM-based clients: `-Xmx4g -XX:+UseG1GC`
5. Consider resource limits: `--cpus=4 --memory=16g --memory-swap=16g` 
# Temporal-Spatial Memory Database Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Temporal-Spatial Memory Database system.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API Server Problems](#api-server-problems)
3. [Query Performance Issues](#query-performance-issues)
4. [Storage Issues](#storage-issues)
5. [Delta Optimization Problems](#delta-optimization-problems)
6. [Client SDK Issues](#client-sdk-issues)
7. [Deployment Challenges](#deployment-challenges)
8. [Logging and Diagnostics](#logging-and-diagnostics)

## Installation Issues

### RocksDB Installation Failures

**Symptoms**: 
- `ImportError: No module named 'rocksdb'`
- `Error loading shared library librocksdb.so`

**Solutions**:

1. Ensure you have the RocksDB development libraries installed:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y librocksdb-dev
   
   # CentOS/RHEL
   sudo yum install rocksdb-devel
   
   # macOS
   brew install rocksdb
   ```

2. For Python bindings, ensure you're using the correct version:
   ```bash
   pip uninstall python-rocksdb
   pip install python-rocksdb==0.7.0
   ```

3. If building from source, check compiler requirements:
   ```bash
   # Install build essentials
   sudo apt-get install build-essential libgflags-dev libsnappy-dev zlib1g-dev libbz2-dev liblz4-dev libzstd-dev
   ```

### Python Dependency Issues

**Symptoms**:
- `ImportError: No module named 'fastapi'`
- Version compatibility errors

**Solutions**:

1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Check Python version (should be 3.8+):
   ```bash
   python --version
   ```

3. Create a virtual environment to isolate dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## API Server Problems

### Server Won't Start

**Symptoms**:
- `Address already in use` error
- Server crashes immediately after starting

**Solutions**:

1. Check if the port is already in use:
   ```bash
   # Linux/macOS
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. Change the port if needed:
   ```bash
   export API_PORT=8001
   python -m src.api.api_server
   ```

3. Check for error logs:
   ```bash
   tail -f logs/api_server.log
   ```

### Authentication Failures

**Symptoms**:
- 401 Unauthorized responses
- "Invalid credentials" errors

**Solutions**:

1. Verify credentials in authentication requests:
   ```bash
   # Check login request format
   curl -X POST "http://localhost:8000/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=demo&password=password"
   ```

2. Check token expiration:
   ```bash
   # Token expiry is typically in the response when authenticating
   # You might need to re-authenticate if the token has expired
   ```

3. For development, reset to default credentials by restarting the server.

### 500 Internal Server Errors

**Symptoms**:
- API returns 500 error codes
- Server logs show exceptions

**Solutions**:

1. Check server logs for detailed error information:
   ```bash
   tail -f logs/api_server.log
   ```

2. Increase log verbosity for more details:
   ```bash
   export LOG_LEVEL=DEBUG
   python -m src.api.api_server
   ```

3. Check database connectivity:
   ```python
   # Quick test script
   from src.storage.rocksdb_store import RocksDBStore
   
   db = RocksDBStore("data/temporal_spatial_db")
   try:
       db.get_all_keys()
       print("Database connection successful")
   except Exception as e:
       print(f"Database error: {str(e)}")
   ```

## Query Performance Issues

### Slow Query Execution

**Symptoms**:
- Queries take longer than expected
- Timeouts on complex queries

**Solutions**:

1. Check query patterns:
   - Avoid querying large date ranges without limits
   - Use both spatial and temporal criteria for narrower result sets
   - Add appropriate limits to queries

2. Analyze query execution with the statistics endpoint:
   ```bash
   curl -X GET "http://localhost:8000/stats" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. Optimize indices:
   ```python
   # Run this as a maintenance script
   from src.indexing.combined_index import TemporalSpatialIndex
   
   index = TemporalSpatialIndex()
   index.tune_parameters()
   index.rebuild()
   ```

### Missing Query Results

**Symptoms**:
- Queries return fewer results than expected
- Known data is not appearing in results

**Solutions**:

1. Verify data was properly indexed:
   ```python
   # Check if node exists in index
   node_id = "your-node-id"
   from src.storage.rocksdb_store import RocksDBStore
   
   db = RocksDBStore("data/temporal_spatial_db")
   node = db.get_node(node_id)
   print(f"Node exists in storage: {node is not None}")
   ```

2. Check query criteria for restrictive filters:
   - Ensure time ranges include the expected time period
   - Verify spatial coordinates and distances are appropriate

3. Rebuild indices if necessary:
   ```python
   from src.indexing.combined_index import TemporalSpatialIndex
   from src.storage.rocksdb_store import RocksDBStore
   
   db = RocksDBStore("data/temporal_spatial_db")
   nodes = db.get_all_nodes()
   
   index = TemporalSpatialIndex()
   index.rebuild()
   index.bulk_load(nodes)
   ```

## Storage Issues

### Disk Space Problems

**Symptoms**:
- `No space left on device` errors
- Database writes failing

**Solutions**:

1. Check available disk space:
   ```bash
   df -h
   ```

2. Clean up old data or backups:
   ```bash
   # Remove old backups
   find /backups -name "tsdb_backup_*.tar.gz" -mtime +30 -delete
   ```

3. Implement delta pruning to reduce storage requirements:
   ```python
   from src.delta.delta_optimizer import DeltaStore, DeltaOptimizer
   
   store = DeltaStore()
   optimizer = DeltaOptimizer(store)
   stats = optimizer.optimize_all()
   print(f"Freed up space by pruning {stats['total_pruned']} deltas")
   ```

### Database Corruption

**Symptoms**:
- `Corruption: Bad CRC` or similar errors
- Crashes when accessing certain data

**Solutions**:

1. Try database recovery (RocksDB has built-in recovery mechanisms)

2. Restore from backup if available:
   ```bash
   # Stop the service first
   sudo systemctl stop tsdb
   
   # Restore from backup
   rm -rf /opt/temporal-spatial-memory/data/rocksdb
   tar -xzf /backups/tsdb_backup_TIMESTAMP.tar.gz -C /
   
   # Restart the service
   sudo systemctl start tsdb
   ```

3. If no backup is available, rebuild the database from other sources if possible.

## Delta Optimization Problems

### Delta Storage Errors

**Symptoms**:
- Node updates fail
- Error messages about delta encoding

**Solutions**:

1. Check delta storage configuration:
   ```bash
   # Ensure the directory exists and is writable
   ls -la data/delta_store
   touch data/delta_store/test_file
   rm data/delta_store/test_file
   ```

2. Reset delta store index if corrupted:
   ```python
   import os
   
   # Back up the old index
   os.rename("data/delta_store/index.json", "data/delta_store/index.json.bak")
   
   # Restart the service to rebuild index
   ```

### Delta Reconstruction Failures

**Symptoms**:
- Cannot retrieve historical versions of nodes
- Errors in delta chain application

**Solutions**:

1. Check for missing delta files:
   ```bash
   # List all delta files for a node
   find data/delta_store -name "node_id_*.delta" | sort
   ```

2. Reset to latest version if historical versions are corrupted:
   ```python
   from src.delta.delta_optimizer import DeltaStore
   from src.storage.rocksdb_store import RocksDBStore
   
   node_id = "problematic_node_id"
   db = RocksDBStore("data/temporal_spatial_db")
   node = db.get_node(node_id)
   
   if node:
       # Create a fresh delta chain starting from current version
       store = DeltaStore()
       # Clear existing deltas
       for version in range(1, node.metadata.get("version", 1) + 1):
           store.remove_delta(node_id, version)
   ```

## Client SDK Issues

### Connection Problems

**Symptoms**:
- `ConnectionError` or `ConnectionRefusedError`
- Timeouts when using the SDK

**Solutions**:

1. Verify API server is running:
   ```bash
   curl http://localhost:8000/docs
   ```

2. Check network connectivity:
   ```bash
   ping localhost
   telnet localhost 8000
   ```

3. Increase connection timeouts:
   ```python
   client = TemporalSpatialClient(
       base_url="http://localhost:8000",
       username="demo",
       password="password",
       timeout=30.0  # Increase from default 10 seconds
   )
   ```

### Circuit Breaker Trips

**Symptoms**:
- "Circuit is OPEN" error messages
- SDK refusing to make requests

**Solutions**:

1. Check API server health and fix any issues

2. Adjust circuit breaker parameters:
   ```python
   client = TemporalSpatialClient(
       base_url="http://localhost:8000",
       username="demo",
       password="password",
       circuit_breaker_threshold=10,     # More failures before opening
       circuit_breaker_timeout=5         # Shorter recovery time
   )
   ```

3. Reset the circuit breaker if needed:
   ```python
   # Manually reset circuit breaker state
   client.circuit_breaker.state = "CLOSED"
   client.circuit_breaker.failures = 0
   ```

## Deployment Challenges

### Docker Deployment Issues

**Symptoms**:
- Container exits immediately
- Cannot connect to containerized service

**Solutions**:

1. Check container logs:
   ```bash
   docker logs tsdb
   ```

2. Verify volume mounts are correct:
   ```bash
   docker inspect tsdb | grep -A 10 Mounts
   ```

3. Ensure ports are properly mapped:
   ```bash
   docker port tsdb
   ```

### systemd Service Problems

**Symptoms**:
- Service fails to start
- Service starts but quickly exits

**Solutions**:

1. Check service status:
   ```bash
   sudo systemctl status tsdb
   ```

2. View service logs:
   ```bash
   sudo journalctl -u tsdb
   ```

3. Verify service configuration:
   ```bash
   sudo systemctl cat tsdb
   ```

4. Test the command manually:
   ```bash
   cd /opt/temporal-spatial-memory
   python -m src.api.api_server
   ```

## Logging and Diagnostics

### Enabling Debug Logging

For more detailed logs, set the `LOG_LEVEL` environment variable:

```bash
export LOG_LEVEL=DEBUG
python -m src.api.api_server
```

### Log File Locations

- API Server logs: `logs/api_server.log`
- Database logs: `logs/rocksdb.log`
- Delta system logs: `logs/delta.log`

### Runtime Diagnostics

Access the statistics endpoint for real-time diagnostics:

```bash
curl -X GET "http://localhost:8000/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Performance Profiling

For advanced performance analysis, use Python profiling tools:

```bash
# Profile the API server
python -m cProfile -o profile.stats -m src.api.api_server

# Analyze the profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime').print_stats(30)"
```

## Getting Help

If you're still experiencing issues after trying these troubleshooting steps:

1. Check the GitHub Issues page for similar problems and solutions
2. Provide the following information when reporting a problem:
   - System information (OS, Python version)
   - Detailed error messages
   - Steps to reproduce the issue
   - Log excerpts
3. For urgent production issues, contact the support team directly 
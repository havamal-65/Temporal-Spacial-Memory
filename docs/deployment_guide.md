# Temporal-Spatial Memory Database Deployment Guide

This guide provides instructions for deploying the Temporal-Spatial Memory Database system in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Deployment Options](#deployment-options)
   - [Local Development](#local-development)
   - [Docker Deployment](#docker-deployment)
   - [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Security Considerations](#security-considerations)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying the Temporal-Spatial Memory Database, ensure you have the following prerequisites:

- Python 3.8 or higher
- RocksDB installed on your system
- Sufficient disk space for database storage
- (Optional) Docker and Docker Compose for containerized deployment

### System Requirements

- **CPU**: 2+ cores recommended (4+ for production)
- **RAM**: 4GB minimum (8GB+ recommended for production)
- **Disk**: SSD storage recommended for optimal performance
- **Network**: Stable network connection with moderate bandwidth

## Installation

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/temporal-spatial-memory.git
   cd temporal-spatial-memory
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install RocksDB if not already installed:
   - **Ubuntu/Debian**:
     ```bash
     apt-get update
     apt-get install -y librocksdb-dev
     ```
   - **MacOS**:
     ```bash
     brew install rocksdb
     ```
   - **Windows**: Follow the [official RocksDB guide](https://github.com/facebook/rocksdb/wiki/Building-on-Windows)

## Deployment Options

### Local Development

For local development and testing:

1. Set up environment variables:
   ```bash
   export DB_PATH="./data/dev_db"
   export API_HOST="127.0.0.1"
   export API_PORT="8000"
   export ENABLE_DELTA="true"
   ```

2. Run the API server:
   ```bash
   python -m src.api.api_server
   ```

3. Access the API at `http://127.0.0.1:8000`
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

### Docker Deployment

For containerized deployment:

1. Build the Docker image:
   ```bash
   docker build -t temporal-spatial-db .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name tsdb \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     -e DB_PATH="/app/data/rocksdb" \
     -e ENABLE_DELTA="true" \
     temporal-spatial-db
   ```

3. For Docker Compose deployment, create a `docker-compose.yml` file:
   ```yaml
   version: '3'
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
       environment:
         - DB_PATH=/app/data/rocksdb
         - ENABLE_DELTA=true
         - API_HOST=0.0.0.0
         - API_PORT=8000
       restart: unless-stopped
   ```

4. Launch with Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Production Deployment

For production deployment, we recommend:

1. Using a reverse proxy like Nginx:
   ```nginx
   server {
       listen 80;
       server_name tsdb.yourdomain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. Using a process manager like systemd:
   ```ini
   [Unit]
   Description=Temporal-Spatial Memory Database
   After=network.target

   [Service]
   User=tsdb
   WorkingDirectory=/opt/temporal-spatial-memory
   ExecStart=/usr/bin/python -m src.api.api_server
   Restart=on-failure
   Environment=DB_PATH=/opt/temporal-spatial-memory/data/rocksdb
   Environment=API_HOST=127.0.0.1
   Environment=API_PORT=8000
   Environment=ENABLE_DELTA=true

   [Install]
   WantedBy=multi-user.target
   ```

3. Set up with systemd:
   ```bash
   sudo cp tsdb.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable tsdb
   sudo systemctl start tsdb
   ```

## Configuration

The Temporal-Spatial Memory Database can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_PATH` | Path to the RocksDB database | `data/temporal_spatial_db` |
| `API_HOST` | Host to bind the API server | `0.0.0.0` |
| `API_PORT` | Port for the API server | `8000` |
| `ENABLE_DELTA` | Enable delta optimization | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_CONNECTIONS` | Maximum database connections | `10` |
| `QUERY_CACHE_SIZE` | Size of the query cache | `1000` |
| `AUTH_SECRET_KEY` | Secret key for JWT tokens | Random UUID |
| `AUTH_ALGORITHM` | JWT algorithm | `HS256` |
| `AUTH_EXPIRY_MINUTES` | JWT token expiry time in minutes | `60` |

## Security Considerations

For securing your deployment:

1. **Authentication**: Replace the demo authentication with a proper user management system in production.

2. **HTTPS**: Always use HTTPS in production by setting up SSL certificates with Let's Encrypt or similar.

3. **Firewall**: Restrict access to the API server using a firewall:
   ```bash
   # Allow only specific IPs for API access
   sudo ufw allow from 192.168.1.0/24 to any port 8000
   ```

4. **API Keys**: Generate strong API keys and rotate them regularly.

5. **Database Backups**: Set up regular backups of the database:
   ```bash
   # Example backup script
   #!/bin/bash
   TIMESTAMP=$(date +%Y%m%d%H%M%S)
   mkdir -p /backups
   tar -czf /backups/tsdb_backup_$TIMESTAMP.tar.gz /opt/temporal-spatial-memory/data
   ```

## Monitoring and Maintenance

### Monitoring

1. Use the `/stats` endpoint to monitor database health and performance.

2. Set up Prometheus metrics by adding the FastAPI Prometheus middleware.

3. Create Grafana dashboards for visualizing metrics.

### Maintenance

1. **Database compaction**: RocksDB performs automatic compaction, but you can trigger manual compaction:
   ```python
   db.compact_range()
   ```

2. **Delta optimization**: Run delta optimization regularly:
   ```bash
   python -m src.delta.maintenance optimize_all
   ```

3. **Database backups**: Schedule regular backups as described in the security section.

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if the API server is running
   - Verify firewall settings
   - Ensure the correct port is exposed in Docker

2. **Authentication Failures**:
   - Check if the correct credentials are being used
   - Verify that the JWT token hasn't expired
   - Restart the API server if the authentication system is stuck

3. **Performance Issues**:
   - Check system resource usage (CPU, RAM, disk I/O)
   - Review query patterns for inefficient queries
   - Run delta optimization to reduce storage overhead
   - Consider upgrading hardware for production deployments

### Logs

Check the logs for detailed error information:

```bash
# For systemd deployment
sudo journalctl -u tsdb

# For Docker deployment
docker logs tsdb
```

For more detailed logging, set `LOG_LEVEL=DEBUG` in the environment variables.

---

For additional support, please file an issue on the GitHub repository or contact the development team. 
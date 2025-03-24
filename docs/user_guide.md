# Temporal-Spatial Memory Database User Guide

This guide provides detailed instructions on how to use the Temporal-Spatial Memory Database system for storing, retrieving, and analyzing data with temporal and spatial dimensions.

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Getting Started](#getting-started)
4. [API Guide](#api-guide)
5. [Client SDK](#client-sdk)
6. [Query Language](#query-language)
7. [Advanced Features](#advanced-features)
8. [Best Practices](#best-practices)
9. [Examples](#examples)
10. [Reference](#reference)

## Introduction

The Temporal-Spatial Memory Database is a specialized system designed to efficiently store and query data that has both time and location dimensions. It's ideal for applications such as:

- Event tracking systems
- Geospatial analytics
- Movement pattern analysis
- Location-based services
- Historical data analysis with spatial context

This database allows you to perform complex queries such as:
- "Find all events that occurred within 5km of location X between January and March"
- "Retrieve the trajectory of object Y over the past week"
- "Identify clusters of activity in region Z during peak hours"

## Core Concepts

### Nodes

A **node** is the basic unit of data in the system. Each node has:

- A unique identifier
- Spatial coordinates (latitude/longitude or x/y/z)
- Temporal information (timestamp)
- Properties (key-value pairs for custom data)
- Metadata (system information)

Example node structure:
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "timestamp": "2023-05-15T14:30:00Z",
  "properties": {
    "name": "Golden Gate Park Event",
    "type": "concert",
    "attendance": 5000
  },
  "metadata": {
    "created_at": "2023-05-10T09:15:22Z",
    "version": 2
  }
}
```

### Indices

The database uses specialized indices to optimize query performance:

1. **Spatial Index**: Uses R-tree data structure to efficiently query geographical locations
2. **Temporal Index**: Optimized for time-range queries
3. **Combined Temporal-Spatial Index**: Integrates both dimensions for complex queries

### Delta Storage

The system maintains a history of changes to nodes using delta encoding, allowing:
- Efficient storage of historical data
- Ability to reconstruct previous states of nodes
- Time-travel queries (querying data as it existed at a specific point in time)

## Getting Started

### Installation

Follow the [Deployment Guide](deployment_guide.md) for detailed installation instructions.

### Creating Your First Node

Using the REST API:

```bash
curl -X POST "http://localhost:8000/nodes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "id": "my_first_node",
    "coordinates": {
      "lat": 40.7128,
      "lon": -74.0060
    },
    "timestamp": "2023-06-01T12:00:00Z",
    "properties": {
      "name": "New York Event",
      "category": "meeting"
    }
  }'
```

Using the Python SDK:

```python
from tsdb_client import TemporalSpatialClient

client = TemporalSpatialClient("http://localhost:8000", "username", "password")

node = {
    "id": "my_first_node",
    "coordinates": {
        "lat": 40.7128,
        "lon": -74.0060
    },
    "timestamp": "2023-06-01T12:00:00Z",
    "properties": {
        "name": "New York Event",
        "category": "meeting"
    }
}

result = client.create_node(node)
print(f"Node created with ID: {result['id']}")
```

### Your First Query

Using the REST API:

```bash
curl -X GET "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "spatial": {
      "center": {"lat": 40.7128, "lon": -74.0060},
      "radius": 10000
    },
    "temporal": {
      "start": "2023-06-01T00:00:00Z",
      "end": "2023-06-02T00:00:00Z"
    },
    "limit": 10
  }'
```

Using the Python SDK:

```python
results = client.query()
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=10000)
    .temporal_range(start="2023-06-01T00:00:00Z", end="2023-06-02T00:00:00Z")
    .limit(10)
    .execute()

for node in results:
    print(f"Found: {node['id']} - {node['properties']['name']}")
```

## API Guide

### Authentication

The API uses JWT (JSON Web Token) for authentication:

1. Obtain a token:
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

2. Use the token in subsequent requests:
```bash
curl -X GET "http://localhost:8000/nodes/node123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Key Endpoints

| Endpoint               | Method | Description                                 |
|------------------------|--------|---------------------------------------------|
| `/nodes`               | GET    | List all nodes (with pagination)            |
| `/nodes`               | POST   | Create a new node                           |
| `/nodes/{id}`          | GET    | Retrieve a specific node                    |
| `/nodes/{id}`          | PUT    | Update a node                               |
| `/nodes/{id}`          | DELETE | Delete a node                               |
| `/nodes/batch`         | POST   | Batch create/update nodes                   |
| `/query`               | POST   | Execute a complex query                     |
| `/query/spatial`       | POST   | Execute a spatial-only query                |
| `/query/temporal`      | POST   | Execute a temporal-only query               |
| `/history/{id}`        | GET    | Get version history of a node               |
| `/history/{id}/{ver}`  | GET    | Get specific version of a node              |
| `/stats`               | GET    | Get system statistics and health info       |

### HTTP Status Codes

| Code | Description                                           |
|------|-------------------------------------------------------|
| 200  | Success                                               |
| 201  | Resource created                                      |
| 400  | Bad request (invalid parameters)                      |
| 401  | Unauthorized (authentication required)                |
| 403  | Forbidden (insufficient permissions)                  |
| 404  | Resource not found                                    |
| 409  | Conflict (e.g., duplicate ID)                         |
| 422  | Unprocessable entity (validation failed)              |
| 429  | Too many requests (rate limit exceeded)               |
| 500  | Server error                                          |

## Client SDK

### Installation

```bash
pip install tsdb-client
```

### Initialization

```python
from tsdb_client import TemporalSpatialClient

# Basic initialization
client = TemporalSpatialClient(
    base_url="http://localhost:8000",
    username="demo",
    password="password"
)

# Advanced initialization with custom settings
client = TemporalSpatialClient(
    base_url="http://localhost:8000",
    username="demo",
    password="password",
    timeout=30.0,
    retry_attempts=3,
    cache_enabled=True,
    cache_ttl=300  # seconds
)
```

### Core Methods

#### Node Management

```python
# Create a node
node_data = {...}  # Node JSON structure
result = client.create_node(node_data)

# Get a node
node = client.get_node("node123")

# Update a node
updated_data = {...}  # Updated node JSON
result = client.update_node("node123", updated_data)

# Delete a node
result = client.delete_node("node123")

# Batch operations
nodes = [...]  # List of node objects
results = client.batch_create_nodes(nodes)
```

#### Querying

```python
# Simple query builder pattern
results = client.query()
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=5000)
    .temporal_range(start="2023-06-01T00:00:00Z", end="2023-06-30T23:59:59Z")
    .property_filter("category", "meeting")
    .limit(20)
    .execute()

# Advanced spatial query
results = client.query()
    .spatial_polygon([
        {"lat": 40.712, "lon": -74.006},
        {"lat": 40.714, "lon": -74.002},
        {"lat": 40.710, "lon": -74.001},
        {"lat": 40.708, "lon": -74.005}
    ])
    .execute()

# Nearest neighbor query
results = client.query()
    .nearest_neighbors(
        center={"lat": 40.7128, "lon": -74.0060},
        k=5
    )
    .execute()

# Time-travel query (data as it existed at a specific time)
results = client.query()
    .as_of("2023-05-01T12:00:00Z")
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=5000)
    .execute()
```

#### Version History

```python
# Get version history of a node
history = client.get_node_history("node123")

# Get specific version of a node
v2_node = client.get_node_version("node123", 2)

# Compare versions
diff = client.compare_versions("node123", 1, 3)
```

## Query Language

### Spatial Queries

The system supports several types of spatial queries:

#### Radius Search

```json
{
  "spatial": {
    "type": "radius",
    "center": {"lat": 40.7128, "lon": -74.0060},
    "radius": 5000
  }
}
```

#### Bounding Box

```json
{
  "spatial": {
    "type": "bbox",
    "min_coords": {"lat": 40.70, "lon": -74.02},
    "max_coords": {"lat": 40.75, "lon": -73.98}
  }
}
```

#### Polygon

```json
{
  "spatial": {
    "type": "polygon",
    "points": [
      {"lat": 40.712, "lon": -74.006},
      {"lat": 40.714, "lon": -74.002},
      {"lat": 40.710, "lon": -74.001},
      {"lat": 40.708, "lon": -74.005},
      {"lat": 40.712, "lon": -74.006}
    ]
  }
}
```

#### k-Nearest Neighbors

```json
{
  "spatial": {
    "type": "knn",
    "center": {"lat": 40.7128, "lon": -74.0060},
    "k": 5
  }
}
```

### Temporal Queries

#### Time Range

```json
{
  "temporal": {
    "type": "range",
    "start": "2023-06-01T00:00:00Z",
    "end": "2023-06-30T23:59:59Z"
  }
}
```

#### Before

```json
{
  "temporal": {
    "type": "before",
    "timestamp": "2023-06-15T12:00:00Z"
  }
}
```

#### After

```json
{
  "temporal": {
    "type": "after",
    "timestamp": "2023-06-15T12:00:00Z"
  }
}
```

#### As-Of (Time Travel)

```json
{
  "temporal": {
    "type": "as_of",
    "timestamp": "2023-05-01T12:00:00Z"
  }
}
```

### Property Filters

```json
{
  "filters": [
    {
      "field": "category",
      "operator": "eq",
      "value": "meeting"
    },
    {
      "field": "attendance",
      "operator": "gt",
      "value": 100
    }
  ]
}
```

Supported operators:
- `eq`: Equal to
- `neq`: Not equal to
- `gt`: Greater than
- `gte`: Greater than or equal to
- `lt`: Less than
- `lte`: Less than or equal to
- `in`: In list
- `contains`: String contains
- `starts_with`: String starts with
- `ends_with`: String ends with

### Combined Queries

```json
{
  "spatial": {
    "type": "radius",
    "center": {"lat": 40.7128, "lon": -74.0060},
    "radius": 5000
  },
  "temporal": {
    "type": "range",
    "start": "2023-06-01T00:00:00Z",
    "end": "2023-06-30T23:59:59Z"
  },
  "filters": [
    {
      "field": "category",
      "operator": "eq",
      "value": "meeting"
    }
  ],
  "sort": {
    "field": "timestamp",
    "order": "desc"
  },
  "limit": 20,
  "offset": 0
}
```

## Advanced Features

### Bulk Operations

For high-throughput scenarios, use the batch endpoints:

```python
# Python SDK
nodes = []
for i in range(1000):
    nodes.append({
        "id": f"batch_node_{i}",
        "coordinates": {
            "lat": 40.7128 + (random.random() - 0.5) * 0.1,
            "lon": -74.0060 + (random.random() - 0.5) * 0.1
        },
        "timestamp": f"2023-06-{random.randint(1, 30):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00Z",
        "properties": {
            "batch_id": i,
            "category": random.choice(["meeting", "event", "appointment"])
        }
    })

# Process in chunks of 100
for i in range(0, len(nodes), 100):
    chunk = nodes[i:i+100]
    results = client.batch_create_nodes(chunk)
    print(f"Processed batch {i//100 + 1}: {len(results)} nodes")
```

### Time Travel

The system's delta storage allows querying data as it existed at a specific point in time:

```python
# Get a node as it existed on May 1st
node_v1 = client.get_node("node123", as_of="2023-05-01T12:00:00Z")

# Query all nodes in an area as they existed in the past
historical_results = client.query()
    .as_of("2023-05-01T12:00:00Z")
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=5000)
    .execute()
```

### Analytical Queries

For analytical use cases, the system provides aggregation queries:

```python
# Count nodes by category in a region
count_by_category = client.analyze()
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=5000)
    .temporal_range(start="2023-06-01T00:00:00Z", end="2023-06-30T23:59:59Z")
    .group_by("category")
    .count()
    .execute()

# Average property value by time period
avg_attendance = client.analyze()
    .spatial_radius(center={"lat": 40.7128, "lon": -74.0060}, radius=5000)
    .temporal_range(start="2023-06-01T00:00:00Z", end="2023-06-30T23:59:59Z")
    .group_by("day")  # Groups by day of the timestamp
    .average("properties.attendance")
    .execute()
```

### Streaming Updates

For applications that need real-time updates, the system provides a WebSocket endpoint:

```python
# Python SDK
async def handle_updates():
    async for update in client.stream_updates():
        print(f"Node {update['id']} was {update['action']}")
        # update['action'] can be 'created', 'updated', or 'deleted'
        # update['data'] contains the new node data for 'created' and 'updated'

# Start streaming in the background
client.start_streaming(handle_updates)
```

## Best Practices

### Query Optimization

1. **Combine spatial and temporal criteria** whenever possible to leverage the combined index
2. **Add appropriate limits** to prevent retrieving too many results
3. **Use the most specific spatial query type** for your needs:
   - Use radius search for proximity queries
   - Use bounding box for rectangular regions
   - Use polygon for complex shapes
4. **Include property filters** to further reduce result sets
5. **Consider indexing important properties** (contact system administrator)

### Data Modeling

1. **Choose appropriate IDs** that are meaningful for your application
2. **Structure properties consistently** to simplify querying
3. **Use ISO 8601 format for any date/time fields** in properties
4. **Consider data versioning needs** when designing update patterns
5. **Batch related updates together** for better performance

### Performance Considerations

1. **Use batch operations** for bulk inserts/updates
2. **Consider temporal partitioning** for very large datasets
3. **Query recent data** more frequently than historical data
4. **Cache frequently accessed data** at the application level
5. **Monitor query performance** using the stats endpoint

## Examples

### Tracking Vehicle Locations

```python
# Insert vehicle position
vehicle_position = {
    "id": f"vehicle_123",
    "coordinates": {
        "lat": 37.7749,
        "lon": -122.4194
    },
    "timestamp": "2023-06-15T14:30:00Z",
    "properties": {
        "vehicle_id": "truck_abc123",
        "speed": 65,
        "direction": 270,
        "status": "in_transit"
    }
}
client.create_node(vehicle_position)

# Query all vehicles in an area
vehicles_in_area = client.query()
    .spatial_radius(center={"lat": 37.7749, "lon": -122.4194}, radius=10000)
    .temporal_range(start="2023-06-15T14:00:00Z", end="2023-06-15T15:00:00Z")
    .property_filter("properties.status", "in_transit")
    .execute()

# Get historical route of a vehicle
vehicle_route = client.query()
    .property_filter("properties.vehicle_id", "truck_abc123")
    .temporal_range(start="2023-06-15T00:00:00Z", end="2023-06-15T23:59:59Z")
    .sort("timestamp", "asc")
    .execute()
```

### Event Management

```python
# Create an event
event = {
    "id": "concert_123",
    "coordinates": {
        "lat": 34.1018,
        "lon": -118.3271
    },
    "timestamp": "2023-07-15T19:30:00Z",
    "properties": {
        "name": "Summer Concert Series",
        "venue": "Hollywood Bowl",
        "capacity": 17500,
        "ticket_price": 75.00,
        "status": "scheduled"
    }
}
client.create_node(event)

# Find nearby events
nearby_events = client.query()
    .spatial_radius(center={"lat": 34.0522, "lon": -118.2437}, radius=15000)
    .temporal_range(start="2023-07-01T00:00:00Z", end="2023-07-31T23:59:59Z")
    .property_filter("properties.status", "scheduled")
    .execute()

# Update event status
client.update_property("concert_123", "properties.status", "sold_out")
```

### Environmental Monitoring

```python
# Record sensor reading
sensor_reading = {
    "id": f"sensor_reading_{int(time.time())}",
    "coordinates": {
        "lat": 37.8651,
        "lon": -119.5383
    },
    "timestamp": "2023-06-15T14:30:00Z",
    "properties": {
        "sensor_id": "yosemite_air_01",
        "temperature": 72.5,
        "humidity": 45.2,
        "air_quality": 85,
        "wind_speed": 8.3
    }
}
client.create_node(sensor_reading)

# Get readings from all sensors in a region
region_readings = client.query()
    .spatial_bbox(
        min_coords={"lat": 37.70, "lon": -119.70},
        max_coords={"lat": 38.00, "lon": -119.40}
    )
    .temporal_range(start="2023-06-15T00:00:00Z", end="2023-06-15T23:59:59Z")
    .execute()

# Analyze average temperature by hour
hourly_temps = client.analyze()
    .spatial_bbox(
        min_coords={"lat": 37.70, "lon": -119.70},
        max_coords={"lat": 38.00, "lon": -119.40}
    )
    .temporal_range(start="2023-06-15T00:00:00Z", end="2023-06-15T23:59:59Z")
    .group_by("hour")
    .average("properties.temperature")
    .execute()
```

## Reference

### Configuration Options

| Option | Description | Default | Environment Variable |
|--------|-------------|---------|---------------------|
| API Port | Port for the API server | 8000 | `API_PORT` |
| Database Path | Path to RocksDB storage | `data/temporal_spatial_db` | `DB_PATH` |
| Delta Store Path | Path to delta storage | `data/delta_store` | `DELTA_PATH` |
| Log Level | Logging verbosity | `INFO` | `LOG_LEVEL` |
| JWT Secret | Secret for token generation | `default_secret_change_me` | `JWT_SECRET` |
| Token Expiry | JWT token expiry time in minutes | 1440 (24h) | `TOKEN_EXPIRY` |
| Cache Size | Maximum nodes in memory cache | 10000 | `CACHE_SIZE` |
| Query Timeout | Maximum query execution time (s) | 30 | `QUERY_TIMEOUT` |

### Data Type Specifications

#### Coordinates

```json
{
  "lat": 40.7128,      // Latitude (WGS84)
  "lon": -74.0060      // Longitude (WGS84)
}
```

Alternative 3D coordinates:

```json
{
  "x": 100.5,          // X coordinate
  "y": 200.3,          // Y coordinate
  "z": 15.0            // Z coordinate (optional)
}
```

#### Timestamp Format

ISO 8601 format: `YYYY-MM-DDThh:mm:ssZ`

Examples:
- `2023-06-15T14:30:00Z` (UTC)
- `2023-06-15T10:30:00-04:00` (EDT)

#### Distance Units

All distances are specified in meters unless otherwise noted.

### Error Handling

The system uses standard HTTP status codes and returns error details in the response body:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid coordinates: latitude must be between -90 and 90",
    "details": {
      "field": "coordinates.lat",
      "value": 100,
      "constraint": "range[-90, 90]"
    }
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `DUPLICATE_ID`: Node ID already exists
- `INTERNAL_ERROR`: Unexpected server error
- `QUERY_TIMEOUT`: Query execution exceeded time limit
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `RATE_LIMITED`: Too many requests 
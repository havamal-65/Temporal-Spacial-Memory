# Temporal-Spatial Memory Database API Reference

## Overview

This document provides a comprehensive reference for the Temporal-Spatial Memory Database REST API. The API enables applications to store, retrieve, and query data with both temporal and spatial dimensions.

Base URL: `http://your-server:8000`

## Authentication

### Obtain Authentication Token

```
POST /token
```

**Request Body:**
```
username=<username>&password=<password>
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

All subsequent requests must include this token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Node Management

### Create Node

```
POST /nodes
```

**Request Body:**
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "timestamp": "2023-06-15T14:30:00Z",
  "properties": {
    "name": "Example Node",
    "category": "test"
  }
}
```

**Response:**
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "timestamp": "2023-06-15T14:30:00Z",
  "properties": {
    "name": "Example Node",
    "category": "test"
  },
  "metadata": {
    "created_at": "2023-06-15T14:35:22Z",
    "version": 1
  }
}
```

### Get Node

```
GET /nodes/{id}
```

**Parameters:**
- `as_of` (optional): ISO timestamp for historical version

**Response:**
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "timestamp": "2023-06-15T14:30:00Z",
  "properties": {
    "name": "Example Node",
    "category": "test"
  },
  "metadata": {
    "created_at": "2023-06-15T14:35:22Z",
    "version": 1
  }
}
```

### Update Node

```
PUT /nodes/{id}
```

**Request Body:**
```json
{
  "coordinates": {
    "lat": 37.7750,
    "lon": -122.4195
  },
  "timestamp": "2023-06-15T14:45:00Z",
  "properties": {
    "name": "Updated Node",
    "category": "test"
  }
}
```

**Response:**
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7750,
    "lon": -122.4195
  },
  "timestamp": "2023-06-15T14:45:00Z",
  "properties": {
    "name": "Updated Node",
    "category": "test"
  },
  "metadata": {
    "created_at": "2023-06-15T14:35:22Z",
    "updated_at": "2023-06-15T14:50:12Z",
    "version": 2
  }
}
```

### Delete Node

```
DELETE /nodes/{id}
```

**Response:**
```json
{
  "success": true,
  "message": "Node deleted successfully"
}
```

### Batch Create/Update Nodes

```
POST /nodes/batch
```

**Request Body:**
```json
{
  "nodes": [
    {
      "id": "node124",
      "coordinates": {
        "lat": 37.7749,
        "lon": -122.4194
      },
      "timestamp": "2023-06-15T14:30:00Z",
      "properties": {
        "name": "Node 1",
        "category": "test"
      }
    },
    {
      "id": "node125",
      "coordinates": {
        "lat": 37.7750,
        "lon": -122.4195
      },
      "timestamp": "2023-06-15T14:45:00Z",
      "properties": {
        "name": "Node 2",
        "category": "test"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "nodes": [
    {"id": "node124", "status": "created"},
    {"id": "node125", "status": "created"}
  ],
  "errors": []
}
```

## Query Operations

### Basic Query

```
POST /query
```

**Request Body:**
```json
{
  "spatial": {
    "type": "radius",
    "center": {"lat": 37.7749, "lon": -122.4194},
    "radius": 5000
  },
  "temporal": {
    "type": "range",
    "start": "2023-06-01T00:00:00Z",
    "end": "2023-06-30T23:59:59Z"
  },
  "filters": [
    {
      "field": "properties.category",
      "operator": "eq",
      "value": "test"
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

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": "node125",
      "coordinates": {
        "lat": 37.7750,
        "lon": -122.4195
      },
      "timestamp": "2023-06-15T14:45:00Z",
      "properties": {
        "name": "Node 2",
        "category": "test"
      },
      "metadata": {
        "created_at": "2023-06-15T14:35:22Z",
        "version": 1
      }
    },
    {
      "id": "node124",
      "coordinates": {
        "lat": 37.7749,
        "lon": -122.4194
      },
      "timestamp": "2023-06-15T14:30:00Z",
      "properties": {
        "name": "Node 1",
        "category": "test"
      },
      "metadata": {
        "created_at": "2023-06-15T14:35:22Z",
        "version": 1
      }
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 2
  }
}
```

### Spatial Query

```
POST /query/spatial
```

**Request Body:**
```json
{
  "type": "radius",
  "center": {"lat": 37.7749, "lon": -122.4194},
  "radius": 5000,
  "limit": 20,
  "offset": 0
}
```

Alternative spatial query types:

```json
{
  "type": "bbox",
  "min_coords": {"lat": 37.70, "lon": -122.50},
  "max_coords": {"lat": 37.80, "lon": -122.40}
}
```

```json
{
  "type": "polygon",
  "points": [
    {"lat": 37.78, "lon": -122.45},
    {"lat": 37.75, "lon": -122.45},
    {"lat": 37.75, "lon": -122.40},
    {"lat": 37.78, "lon": -122.40},
    {"lat": 37.78, "lon": -122.45}
  ]
}
```

```json
{
  "type": "knn",
  "center": {"lat": 37.7749, "lon": -122.4194},
  "k": 5
}
```

**Response format is the same as the basic query.**

### Temporal Query

```
POST /query/temporal
```

**Request Body:**
```json
{
  "type": "range",
  "start": "2023-06-01T00:00:00Z",
  "end": "2023-06-30T23:59:59Z",
  "limit": 20,
  "offset": 0
}
```

Alternative temporal query types:

```json
{
  "type": "before",
  "timestamp": "2023-06-15T00:00:00Z"
}
```

```json
{
  "type": "after",
  "timestamp": "2023-06-15T00:00:00Z"
}
```

```json
{
  "type": "as_of",
  "timestamp": "2023-06-15T00:00:00Z"
}
```

**Response format is the same as the basic query.**

## Version History

### Get Node History

```
GET /history/{id}
```

**Response:**
```json
{
  "id": "node123",
  "versions": [
    {
      "version": 1,
      "timestamp": "2023-06-15T14:35:22Z",
      "coordinates": {
        "lat": 37.7749,
        "lon": -122.4194
      },
      "timestamp": "2023-06-15T14:30:00Z"
    },
    {
      "version": 2,
      "timestamp": "2023-06-15T14:50:12Z",
      "coordinates": {
        "lat": 37.7750,
        "lon": -122.4195
      },
      "timestamp": "2023-06-15T14:45:00Z"
    }
  ]
}
```

### Get Specific Version

```
GET /history/{id}/{version}
```

**Response:**
```json
{
  "id": "node123",
  "coordinates": {
    "lat": 37.7749,
    "lon": -122.4194
  },
  "timestamp": "2023-06-15T14:30:00Z",
  "properties": {
    "name": "Example Node",
    "category": "test"
  },
  "metadata": {
    "created_at": "2023-06-15T14:35:22Z",
    "version": 1
  }
}
```

### Compare Versions

```
GET /history/{id}/compare?v1=1&v2=2
```

**Response:**
```json
{
  "id": "node123",
  "changes": {
    "coordinates": {
      "from": {
        "lat": 37.7749,
        "lon": -122.4194
      },
      "to": {
        "lat": 37.7750,
        "lon": -122.4195
      }
    },
    "timestamp": {
      "from": "2023-06-15T14:30:00Z",
      "to": "2023-06-15T14:45:00Z"
    },
    "properties.name": {
      "from": "Example Node",
      "to": "Updated Node"
    }
  },
  "metadata": {
    "v1_timestamp": "2023-06-15T14:35:22Z",
    "v2_timestamp": "2023-06-15T14:50:12Z"
  }
}
```

## Analytics

### Property Aggregation

```
POST /analytics/aggregate
```

**Request Body:**
```json
{
  "spatial": {
    "type": "radius",
    "center": {"lat": 37.7749, "lon": -122.4194},
    "radius": 5000
  },
  "temporal": {
    "type": "range",
    "start": "2023-06-01T00:00:00Z",
    "end": "2023-06-30T23:59:59Z"
  },
  "group_by": "properties.category",
  "aggregation": "count"
}
```

**Response:**
```json
{
  "results": [
    {"key": "test", "value": 25},
    {"key": "event", "value": 42},
    {"key": "location", "value": 13}
  ],
  "total": 80
}
```

### Time Series Analysis

```
POST /analytics/timeseries
```

**Request Body:**
```json
{
  "spatial": {
    "type": "radius",
    "center": {"lat": 37.7749, "lon": -122.4194},
    "radius": 5000
  },
  "temporal": {
    "type": "range",
    "start": "2023-06-01T00:00:00Z",
    "end": "2023-06-30T23:59:59Z"
  },
  "interval": "day",
  "aggregation": "count"
}
```

**Response:**
```json
{
  "results": [
    {"key": "2023-06-01", "value": 5},
    {"key": "2023-06-02", "value": 8},
    {"key": "2023-06-03", "value": 12},
    // ...
    {"key": "2023-06-30", "value": 7}
  ],
  "total": 80
}
```

## System Management

### Get Statistics

```
GET /stats
```

**Response:**
```json
{
  "system": {
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "start_time": "2023-06-14T00:00:00Z"
  },
  "storage": {
    "total_nodes": 15000,
    "disk_usage_bytes": 1234567890,
    "index_size_bytes": 98765432
  },
  "performance": {
    "avg_query_time_ms": 12.5,
    "queries_per_minute": 350,
    "inserts_per_minute": 120
  },
  "cache": {
    "size": 10000,
    "hit_ratio": 0.85,
    "miss_ratio": 0.15
  }
}
```

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "index": "ok",
    "api": "ok"
  },
  "timestamp": "2023-06-15T15:00:00Z"
}
```

## Streaming API

### WebSocket Connection

Connect to: `ws://your-server:8000/stream`

Required query parameters:
- `token`: Your JWT authentication token
- `events` (optional): Comma-separated list of event types to receive (default: all)

### Message Format

```json
{
  "type": "node_created",
  "timestamp": "2023-06-15T15:10:22Z",
  "data": {
    "id": "node126",
    "coordinates": {
      "lat": 37.7751,
      "lon": -122.4196
    },
    "timestamp": "2023-06-15T15:00:00Z",
    "properties": {
      "name": "New Node",
      "category": "test"
    }
  }
}
```

Event types:
- `node_created`
- `node_updated`
- `node_deleted`
- `system_alert`

## Error Responses

All API errors follow this standard format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional context-specific error details
    }
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Invalid input
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `CONFLICT`: Resource already exists
- `INTERNAL_ERROR`: Server error
- `QUERY_TIMEOUT`: Query timed out
- `RATE_LIMITED`: Too many requests

## Rate Limits

Default rate limits:
- Authentication: 10 requests per minute
- Read operations: 1000 requests per hour
- Write operations: 500 requests per hour
- Query operations: 100 requests per minute
- Batch operations: 50 requests per minute

Rate limit headers:
- `X-RateLimit-Limit`: Total allowed requests in the current period
- `X-RateLimit-Remaining`: Remaining requests in the current period
- `X-RateLimit-Reset`: Time until the rate limit resets (in seconds)

When exceeded:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Please try again after 35 seconds",
    "details": {
      "limit": 100,
      "reset_seconds": 35
    }
  }
}
``` 
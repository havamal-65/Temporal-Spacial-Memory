"""
RESTful API server for the Temporal-Spatial Memory Database.

This module provides HTTP endpoints for accessing and manipulating the database.
"""

import os
import time
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, Header, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.query.query_engine import QueryEngine
from src.query.query import Query
from src.core.node import Node
from src.core.coordinates import Coordinates
from src.storage.rocksdb_store import RocksDBStore
from src.indexing.combined_index import TemporalSpatialIndex
from src.indexing.rtree import SpatialIndex

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Temporal-Spatial Memory Database API",
    description="API for querying and manipulating temporal-spatial data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Data models
class NodeCreate(BaseModel):
    """Schema for creating a new node."""
    content: Any
    spatial_coordinates: Optional[List[float]] = Field(None, description="Spatial coordinates (x, y, z)")
    temporal_coordinate: Optional[float] = Field(None, description="Temporal coordinate (Unix timestamp)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class NodeResponse(BaseModel):
    """Schema for node response."""
    id: str
    content: Any
    coordinates: Dict[str, Any]
    created_at: float
    updated_at: Optional[float] = None
    version: int = 1
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    """Schema for query request."""
    spatial_criteria: Optional[Dict[str, Any]] = None
    temporal_criteria: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"

class QueryResponse(BaseModel):
    """Schema for query response."""
    results: List[NodeResponse]
    count: int
    total: int
    page: int
    pages: int
    execution_time: float

class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str
    expires_at: int

# Database instance (initialized in startup event)
db = None
query_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize database connection and indices on startup."""
    global db, query_engine
    
    logger.info("Initializing database connection...")
    
    # Database path from environment or default
    db_path = os.environ.get("DB_PATH", "data/temporal_spatial_db")
    
    # Initialize storage
    db = RocksDBStore(db_path)
    
    # Initialize indices
    spatial_index = SpatialIndex(dimension=3)
    temporal_spatial_index = TemporalSpatialIndex()
    
    # Load existing data into indices
    nodes = db.get_all_nodes()
    spatial_index.bulk_load(nodes)
    temporal_spatial_index.bulk_load(nodes)
    
    # Create index manager
    class IndexManager:
        def __init__(self, spatial_idx, combined_idx):
            self.indices = {
                "spatial": spatial_idx,
                "combined": combined_idx
            }
        
        def get_index(self, name):
            return self.indices.get(name)
        
        def has_index(self, name):
            return name in self.indices
    
    index_manager = IndexManager(spatial_index, temporal_spatial_index)
    
    # Initialize query engine
    query_engine = QueryEngine(db, index_manager)
    
    logger.info(f"Database initialized with {len(nodes)} nodes")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    global db
    if db:
        logger.info("Closing database connection...")
        db.close()

# Authentication endpoints
@app.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate authentication token."""
    # In production, validate credentials against database
    if form_data.username != "demo" or form_data.password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token (use a proper JWT library in production)
    token = str(uuid.uuid4())
    expires_at = int(time.time()) + 3600  # 1 hour expiration
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at
    }

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token."""
    # In production, validate token and retrieve user
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Mock user for demo
    return {"username": "demo", "permissions": ["read", "write"]}

# Node endpoints
@app.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    node_data: NodeCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new node."""
    # Generate ID and timestamps
    node_id = str(uuid.uuid4())
    timestamp = time.time()
    
    # Create coordinates
    coordinates = Coordinates(
        spatial=node_data.spatial_coordinates,
        temporal=node_data.temporal_coordinate or timestamp
    )
    
    # Create node
    node = Node(
        id=node_id,
        content=node_data.content,
        coordinates=coordinates,
        metadata={
            "created_at": timestamp,
            "created_by": current_user["username"],
            **node_data.metadata
        }
    )
    
    # Store node
    db.store_node(node)
    
    # Update indices
    query_engine.index_manager.get_index("spatial").insert(node)
    query_engine.index_manager.get_index("combined").insert(node)
    
    # Format response
    return {
        "id": node.id,
        "content": node.content,
        "coordinates": {
            "spatial": node.coordinates.spatial,
            "temporal": node.coordinates.temporal
        },
        "created_at": timestamp,
        "updated_at": None,
        "version": 1,
        "metadata": node.metadata
    }

@app.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get a node by ID."""
    node = db.get_node(node_id)
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with ID {node_id} not found"
        )
    
    return {
        "id": node.id,
        "content": node.content,
        "coordinates": {
            "spatial": node.coordinates.spatial,
            "temporal": node.coordinates.temporal
        },
        "created_at": node.metadata.get("created_at", 0),
        "updated_at": node.metadata.get("updated_at"),
        "version": node.metadata.get("version", 1),
        "metadata": node.metadata
    }

@app.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a node by ID."""
    node = db.get_node(node_id)
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with ID {node_id} not found"
        )
    
    # Remove from indices
    query_engine.index_manager.get_index("spatial").remove(node_id)
    query_engine.index_manager.get_index("combined").remove(node_id)
    
    # Remove from storage
    db.delete_node(node_id)
    
    return None

@app.put("/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: str,
    node_data: NodeCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Update a node by ID."""
    existing_node = db.get_node(node_id)
    
    if not existing_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with ID {node_id} not found"
        )
    
    # Update timestamps and version
    timestamp = time.time()
    version = existing_node.metadata.get("version", 1) + 1
    
    # Create coordinates
    coordinates = Coordinates(
        spatial=node_data.spatial_coordinates or existing_node.coordinates.spatial,
        temporal=node_data.temporal_coordinate or existing_node.coordinates.temporal
    )
    
    # Create updated metadata
    metadata = {
        **existing_node.metadata,
        **node_data.metadata,
        "created_at": existing_node.metadata.get("created_at", 0),
        "updated_at": timestamp,
        "updated_by": current_user["username"],
        "version": version
    }
    
    # Create updated node
    updated_node = Node(
        id=node_id,
        content=node_data.content,
        coordinates=coordinates,
        metadata=metadata
    )
    
    # Store delta if enabled
    if os.environ.get("ENABLE_DELTA", "false").lower() == "true":
        # Store delta (implementation in delta optimizer)
        pass
    
    # Store updated node
    db.store_node(updated_node)
    
    # Update indices
    query_engine.index_manager.get_index("spatial").update(updated_node)
    query_engine.index_manager.get_index("combined").update(updated_node)
    
    return {
        "id": updated_node.id,
        "content": updated_node.content,
        "coordinates": {
            "spatial": updated_node.coordinates.spatial,
            "temporal": updated_node.coordinates.temporal
        },
        "created_at": metadata.get("created_at", 0),
        "updated_at": timestamp,
        "version": version,
        "metadata": metadata
    }

# Query endpoints
@app.post("/query", response_model=QueryResponse)
async def execute_query(
    query_request: QueryRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Execute a query against the database."""
    start_time = time.time()
    
    # Build query criteria
    criteria = {}
    query_type = Query.BASIC
    
    if query_request.spatial_criteria and query_request.temporal_criteria:
        query_type = Query.COMBINED
        criteria = {
            "spatial": query_request.spatial_criteria,
            "temporal": query_request.temporal_criteria
        }
    elif query_request.spatial_criteria:
        query_type = Query.SPATIAL
        criteria = query_request.spatial_criteria
    elif query_request.temporal_criteria:
        query_type = Query.TEMPORAL
        criteria = query_request.temporal_criteria
    
    # Create query
    query = Query(type=query_type, criteria=criteria)
    
    # Execute query
    result = query_engine.execute(query)
    
    # Apply sorting if requested
    if query_request.sort_by:
        from operator import attrgetter
        
        # Custom sort key function
        def sort_key(node):
            """Extract sort key from node."""
            if query_request.sort_by == "temporal":
                return node.coordinates.temporal
            elif query_request.sort_by == "distance" and query_request.spatial_criteria:
                # Calculate distance if point provided
                if "point" in query_request.spatial_criteria:
                    point = query_request.spatial_criteria["point"]
                    node_point = node.coordinates.spatial
                    if point and node_point:
                        import math
                        return math.sqrt(sum((a - b) ** 2 for a, b in zip(point, node_point)))
                return 0
            else:
                # Try to extract attribute
                try:
                    return attrgetter(query_request.sort_by)(node)
                except (AttributeError, TypeError):
                    # Try metadata
                    return node.metadata.get(query_request.sort_by, 0)
        
        # Sort results
        result.items.sort(
            key=sort_key,
            reverse=query_request.sort_order.lower() == "desc"
        )
    
    # Apply pagination
    total = result.count()
    limit = query_request.limit or 100
    offset = query_request.offset or 0
    
    paginated_items = result.items[offset:offset + limit]
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Format response
    response_items = []
    for node in paginated_items:
        response_items.append({
            "id": node.id,
            "content": node.content,
            "coordinates": {
                "spatial": node.coordinates.spatial,
                "temporal": node.coordinates.temporal
            },
            "created_at": node.metadata.get("created_at", 0),
            "updated_at": node.metadata.get("updated_at"),
            "version": node.metadata.get("version", 1),
            "metadata": node.metadata
        })
    
    return {
        "results": response_items,
        "count": len(paginated_items),
        "total": total,
        "page": (offset // limit) + 1 if limit else 1,
        "pages": (total + limit - 1) // limit if limit else 1,
        "execution_time": execution_time
    }

# Statistics endpoints
@app.get("/stats")
async def get_statistics(
    current_user: Dict = Depends(get_current_user)
):
    """Get database statistics."""
    stats = {
        "node_count": len(db.get_all_nodes()),
        "query_engine": query_engine.stats,
        "indices": {
            "spatial": {
                "node_count": len(query_engine.index_manager.get_index("spatial").get_all_ids())
            },
            "combined": query_engine.index_manager.get_index("combined").get_statistics()
        },
        "uptime": int(time.time() - startup_time)
    }
    
    return stats

# Main application
startup_time = time.time()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
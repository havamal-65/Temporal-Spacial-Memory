"""
Query Module for Temporal-Spatial Memory Database.

This module provides interfaces and implementations for constructing and executing queries
against the temporal-spatial database. The query system supports:

1. Temporal queries (before, after, between timepoints)
2. Spatial queries (near, within regions)
3. Content-based filtering
4. Composite queries with logical operations (AND, OR)

Main components:
- query_builder: Fluent interface for building queries
- query: Query representation and serialization
- query_engine: Query execution and optimization (Sprint 2)
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging

# Configure module logger
logger = logging.getLogger(__name__)

# Import key components 
from .query import (
    Query, 
    QueryCriteria,
    TemporalCriteria,
    SpatialCriteria,
    ContentCriteria,
    CompositeCriteria,
    QueryType,
    QueryOperator
)
from .query_builder import (
    QueryBuilder,
    TemporalQueryBuilder,
    SpatialQueryBuilder,
    ContentQueryBuilder,
    CompoundQueryBuilder,
    query,
    temporal_query,
    spatial_query,
    content_query
)

# Version info
__version__ = "0.1.0"

# Public API exports
__all__ = [
    "Query",
    "QueryCriteria",
    "TemporalCriteria",
    "SpatialCriteria",
    "ContentCriteria",
    "CompositeCriteria",
    "QueryType",
    "QueryOperator",
    "QueryBuilder",
    "TemporalQueryBuilder",
    "SpatialQueryBuilder",
    "ContentQueryBuilder",
    "CompoundQueryBuilder",
    "query",
    "temporal_query",
    "spatial_query",
    "content_query",
    "initialize_query_system"
]

# Module initialization code
def initialize_query_system():
    """Initialize the query system and register available query types."""
    logger.info("Initializing query system")
    # Placeholder for initialization logic
    return True 
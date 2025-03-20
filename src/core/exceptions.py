"""
Custom exceptions for the Temporal-Spatial Knowledge Database.

This module defines the exception hierarchy used throughout the codebase.
"""

class TemporalSpatialError(Exception):
    """Base exception for all Temporal-Spatial Database errors."""
    pass

class CoordinateError(TemporalSpatialError):
    """Base exception for coordinate-related errors."""
    pass

class SpatialError(CoordinateError):
    """Exception for spatial coordinate-related errors."""
    pass

class TemporalError(CoordinateError):
    """Exception for temporal coordinate-related errors."""
    pass

class NodeError(TemporalSpatialError):
    """Exception for node-related errors."""
    pass

class StorageError(TemporalSpatialError):
    """Base exception for storage-related errors."""
    pass

class SerializationError(StorageError):
    """Exception for serialization/deserialization errors."""
    pass

class IndexError(TemporalSpatialError):
    """Base exception for indexing-related errors."""
    pass

class SpatialIndexError(IndexError):
    """Exception for spatial indexing-related errors."""
    pass

class TemporalIndexError(IndexError):
    """Exception for temporal indexing-related errors."""
    pass

class DeltaError(TemporalSpatialError):
    """Base exception for delta-related errors."""
    pass

class DeltaChainError(DeltaError):
    """Exception for delta chain-related errors."""
    pass

class ReconstructionError(DeltaError):
    """Exception for state reconstruction errors."""
    pass

class QueryError(TemporalSpatialError):
    """Base exception for query-related errors."""
    pass

class SpatialQueryError(QueryError):
    """Exception for spatial query-related errors."""
    pass

class TemporalQueryError(QueryError):
    """Exception for temporal query-related errors."""
    pass 
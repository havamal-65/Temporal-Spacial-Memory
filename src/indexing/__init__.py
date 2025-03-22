"""
Indexing module for the Temporal-Spatial Knowledge Database.

This module provides indexing mechanisms for efficient spatial and temporal queries.
"""

# Import components that don't depend on external libraries first
try:
    from .rectangle import Rectangle
    RECTANGLE_AVAILABLE = True
except ImportError:
    RECTANGLE_AVAILABLE = False

# Import temporal index
try:
    from .temporal_index import TemporalIndex
    TEMPORAL_INDEX_AVAILABLE = True
except ImportError:
    TEMPORAL_INDEX_AVAILABLE = False
    class TemporalIndex:
        def __init__(self, *args, **kwargs):
            raise ImportError("TemporalIndex implementation not available")

# Import rtree components with graceful degradation
try:
    # Check if rtree module is available
    import rtree
    
    # Import rtree components
    from .rtree import SpatialIndex
    from .rtree_node import RTreeNode, RTreeEntry, RTreeNodeRef
    from .rtree_impl import RTree
    
    # Import combined index
    from .combined_index import CombinedIndex
    
    # Flag that rtree is available
    RTREE_AVAILABLE = True
    
except ImportError as e:
    # Define placeholder classes if rtree is not available
    RTREE_AVAILABLE = False
    
    class SpatialIndex:
        def __init__(self, *args, **kwargs):
            raise ImportError("SpatialIndex requires rtree library: pip install rtree")
    
    class RTreeNode:
        def __init__(self, *args, **kwargs):
            raise ImportError("RTreeNode requires rtree library: pip install rtree")
    
    class RTreeEntry:
        def __init__(self, *args, **kwargs):
            raise ImportError("RTreeEntry requires rtree library: pip install rtree")
    
    class RTreeNodeRef:
        def __init__(self, *args, **kwargs):
            raise ImportError("RTreeNodeRef requires rtree library: pip install rtree")
    
    class RTree:
        def __init__(self, *args, **kwargs):
            raise ImportError("RTree requires rtree library: pip install rtree")
    
    class CombinedIndex:
        def __init__(self, *args, **kwargs):
            raise ImportError("CombinedIndex requires rtree library: pip install rtree")

# Export all components
__all__ = [
    'SpatialIndex',
    'TemporalIndex',
    'CombinedIndex',
    'Rectangle',
    'RTreeNode',
    'RTreeEntry',
    'RTreeNodeRef',
    'RTree',
    'RTREE_AVAILABLE',
    'TEMPORAL_INDEX_AVAILABLE',
    'RECTANGLE_AVAILABLE'
] 
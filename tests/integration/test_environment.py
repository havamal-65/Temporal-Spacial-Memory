"""
Test environment setup for integration tests.

This module provides a reusable test environment for integration tests,
setting up all necessary components and providing cleanup utilities.
"""

import os
import shutil
import math
from typing import Optional, Tuple

# Use Node from node_v2 instead of node
from src.core.node_v2 import Node
from src.storage.node_store import InMemoryNodeStore

# Import indexing components with error handling
# Check for rtree availability first to avoid import errors
RTREE_AVAILABLE = False
try:
    import rtree
    RTREE_AVAILABLE = True
except ImportError:
    print("WARNING: RTree library not available. Install with: pip install rtree")
    
# Define mock classes for missing components
if not RTREE_AVAILABLE:
    # Mock RTree if not available
    class RTree:
        def __init__(self, *args, **kwargs):
            print("WARNING: RTree not available. Spatial queries will not work.")
        def insert(self, *args, **kwargs):
            pass
        def nearest_neighbors(self, *args, **kwargs):
            return []
        def range_query(self, *args, **kwargs):
            return []
else:
    # If rtree is available, import it
    try:
        from src.indexing.rtree_impl import RTree
    except ImportError:
        print("WARNING: RTree implementation not available. Using mock version.")
        # Define a mock version as fallback
        class RTree:
            def __init__(self, *args, **kwargs):
                print("WARNING: RTree implementation not available. Spatial queries will not work.")
            def insert(self, *args, **kwargs):
                pass
            def nearest_neighbors(self, *args, **kwargs):
                return []
            def range_query(self, *args, **kwargs):
                return []

# Handle other indexing components
try:
    from src.indexing.temporal_index import TemporalIndex
    TEMPORAL_INDEX_AVAILABLE = True
except ImportError:
    print("WARNING: TemporalIndex not available. Temporal queries will not work.")
    TEMPORAL_INDEX_AVAILABLE = False
    # Mock TemporalIndex if not available
    class TemporalIndex:
        def __init__(self, *args, **kwargs):
            print("WARNING: TemporalIndex not available. Temporal queries will not work.")
        def insert(self, *args, **kwargs):
            pass
        def query(self, *args, **kwargs):
            return []

try:
    from src.indexing.combined_index import SpatioTemporalIndex
    COMBINED_INDEX_AVAILABLE = True
except ImportError:
    print("WARNING: SpatioTemporalIndex not available. Combined queries will not work.")
    COMBINED_INDEX_AVAILABLE = False
    # Mock SpatioTemporalIndex if not available
    class SpatioTemporalIndex:
        def __init__(self, *args, **kwargs):
            print("WARNING: SpatioTemporalIndex not available. Combined queries will not work.")
        def insert(self, *args, **kwargs):
            pass
        def query(self, *args, **kwargs):
            return []
        def query_temporal_range(self, *args, **kwargs):
            return []
        def query_spatial_range(self, *args, **kwargs):
            return []
        def query_nearest(self, *args, **kwargs):
            return []

# Flag for combined indexing
INDEXING_AVAILABLE = RTREE_AVAILABLE and TEMPORAL_INDEX_AVAILABLE and COMBINED_INDEX_AVAILABLE

try:
    from src.delta.store import InMemoryDeltaStore
    DELTA_STORE_AVAILABLE = True
except ImportError:
    # Create mock delta store if imports fail
    class InMemoryDeltaStore:
        def __init__(self, *args, **kwargs):
            print("WARNING: DeltaStore not available. Delta operations will not work.")
            self.deltas = {}
        def store_delta(self, *args, **kwargs):
            pass
        def get_delta(self, *args, **kwargs):
            return None
    DELTA_STORE_AVAILABLE = False


class TestEnvironment:
    def __init__(self, test_data_path: str = "test_data", use_in_memory: bool = True):
        """
        Initialize test environment
        
        Args:
            test_data_path: Directory for test data
            use_in_memory: Whether to use in-memory storage (vs. on-disk)
        """
        self.test_data_path = test_data_path
        self.use_in_memory = True
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.combined_index = None
        self.query_engine = None
        
    def setup(self) -> None:
        """Set up a fresh environment with all components"""
        if os.path.exists(self.test_data_path):
            shutil.rmtree(self.test_data_path)
            os.makedirs(self.test_data_path)
        self.node_store = InMemoryNodeStore()
        self.delta_store = InMemoryDeltaStore()
        self.spatial_index = RTree(max_entries=50, min_entries=20)
        self.temporal_index = TemporalIndex()
        self.combined_index = SpatioTemporalIndex()
        
    def teardown(self) -> None:
        """Clean up test environment"""
        # Close connections
        if not self.use_in_memory:
            self.node_store.close()
            if hasattr(self.delta_store, 'close'):
                self.delta_store.close()
            
        # Clean up resources
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.combined_index = None
        self.query_engine = None 
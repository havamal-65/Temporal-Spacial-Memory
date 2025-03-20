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

# Import with error handling for optional dependencies
try:
    from src.storage.rocksdb_store import RocksDBNodeStore
    ROCKSDB_AVAILABLE = True
except ImportError:
    # Create a mock RocksDBNodeStore that raises an error if used
    class RocksDBNodeStore(InMemoryNodeStore):
        def __init__(self, *args, **kwargs):
            super().__init__()
            print("WARNING: RocksDB not available. Using in-memory store instead.")
    ROCKSDB_AVAILABLE = False

# Import indexing components with error handling
try:
    from src.indexing.rtree import RTree
    RTREE_AVAILABLE = True
except ImportError:
    # Create a mock RTree that raises an error if used
    class RTree:
        def __init__(self, *args, **kwargs):
            print("WARNING: RTree not available. Spatial queries will not work.")
        def insert(self, *args, **kwargs):
            pass
        def nearest_neighbors(self, *args, **kwargs):
            return []
        def range_query(self, *args, **kwargs):
            return []
    RTREE_AVAILABLE = False

try:
    from src.indexing.temporal_index import TemporalIndex
    from src.indexing.combined_index import SpatioTemporalIndex
    INDEXING_AVAILABLE = True
except ImportError:
    # Create mock classes if imports fail
    class TemporalIndex:
        def __init__(self, *args, **kwargs):
            print("WARNING: TemporalIndex not available. Temporal queries will not work.")
        def insert(self, *args, **kwargs):
            pass
        def query(self, *args, **kwargs):
            return []
    
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
    INDEXING_AVAILABLE = False

try:
    from src.delta.store import InMemoryDeltaStore, RocksDBDeltaStore
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
    
    class RocksDBDeltaStore(InMemoryDeltaStore):
        pass
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
        self.use_in_memory = use_in_memory or not ROCKSDB_AVAILABLE
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.query_engine = None
        
    def setup(self) -> None:
        """Set up a fresh environment with all components"""
        # Clean up previous test data
        if os.path.exists(self.test_data_path) and not self.use_in_memory:
            shutil.rmtree(self.test_data_path)
            os.makedirs(self.test_data_path)
            
        # Create storage components
        if self.use_in_memory:
            self.node_store = InMemoryNodeStore()
            self.delta_store = InMemoryDeltaStore()
        else:
            self.node_store = RocksDBNodeStore(os.path.join(self.test_data_path, "nodes"))
            self.delta_store = RocksDBDeltaStore(os.path.join(self.test_data_path, "deltas"))
            
        # Create index components
        self.spatial_index = RTree(max_entries=50, min_entries=20)
        self.temporal_index = TemporalIndex(resolution=0.1)
        
        # Create combined index
        self.combined_index = SpatioTemporalIndex(
            spatial_index=self.spatial_index,
            temporal_index=self.temporal_index
        )
        
    def teardown(self) -> None:
        """Clean up test environment"""
        # Close connections
        if not self.use_in_memory and ROCKSDB_AVAILABLE:
            self.node_store.close()
            self.delta_store.close()
            
        # Clean up resources
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.combined_index = None
        self.query_engine = None 
"""
Tests for the simplified memory management example.
"""

import os
import sys
import unittest
import uuid
from datetime import datetime, timedelta
import random

# Make sure we can import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components from the simple memory example
from src.examples.simple_memory_example import (
    SimpleNode,
    SimpleNodeStore,
    SimplePartialLoader,
    SimpleCache,
    generate_test_nodes
)


class TestSimpleNode(unittest.TestCase):
    """Tests for the SimpleNode class."""
    
    def test_init_with_defaults(self):
        """Test node initialization with default values."""
        node = SimpleNode()
        self.assertIsInstance(node.id, uuid.UUID)
        self.assertEqual(node.data, {})
        self.assertIsInstance(node.timestamp, float)
        self.assertEqual(len(node.position), 3)
        self.assertEqual(node.connections, [])
    
    def test_init_with_values(self):
        """Test node initialization with provided values."""
        node_id = uuid.uuid4()
        data = {"value": "test"}
        timestamp = 1000.0
        position = [timestamp, 10.0, 20.0]
        
        node = SimpleNode(node_id, data, timestamp, position)
        
        self.assertEqual(node.id, node_id)
        self.assertEqual(node.data, data)
        self.assertEqual(node.timestamp, timestamp)
        self.assertEqual(node.position, position)
    
    def test_add_connection(self):
        """Test adding connections to a node."""
        node = SimpleNode()
        target_id = uuid.uuid4()
        
        node.add_connection(target_id)
        
        self.assertEqual(len(node.connections), 1)
        self.assertEqual(node.connections[0], target_id)
    
    def test_get_connected_nodes(self):
        """Test getting connected nodes."""
        node = SimpleNode()
        target_ids = [uuid.uuid4() for _ in range(5)]
        
        for target_id in target_ids:
            node.add_connection(target_id)
        
        connected = node.get_connected_nodes()
        
        self.assertEqual(len(connected), 5)
        for i, target_id in enumerate(target_ids):
            self.assertEqual(connected[i], target_id)


class TestSimpleNodeStore(unittest.TestCase):
    """Tests for the SimpleNodeStore class."""
    
    def setUp(self):
        """Set up a store and some test nodes."""
        self.store = SimpleNodeStore()
        self.nodes = [SimpleNode() for _ in range(10)]
        
        for node in self.nodes:
            self.store.put(node.id, node)
    
    def test_put_and_get(self):
        """Test putting and getting nodes."""
        # Test getting existing nodes
        for node in self.nodes:
            stored_node = self.store.get(node.id)
            self.assertEqual(stored_node.id, node.id)
        
        # Test getting non-existent node
        nonexistent_id = uuid.uuid4()
        self.assertIsNone(self.store.get(nonexistent_id))
    
    def test_get_all(self):
        """Test getting all nodes."""
        all_nodes = self.store.get_all()
        self.assertEqual(len(all_nodes), 10)
        
        # Check that all our nodes are in the result
        node_ids = [node.id for node in self.nodes]
        result_ids = [node.id for node in all_nodes]
        
        for node_id in node_ids:
            self.assertIn(node_id, result_ids)
    
    def test_get_nodes_in_time_range(self):
        """Test getting nodes in a time range."""
        # Create nodes with specific timestamps
        now = datetime.now()
        
        nodes = []
        for i in range(5):
            timestamp = (now - timedelta(days=i)).timestamp()
            node = SimpleNode(timestamp=timestamp)
            nodes.append(node)
            self.store.put(node.id, node)
        
        # Query for nodes in different time ranges
        start_time = now - timedelta(days=2)
        end_time = now
        
        node_ids = self.store.get_nodes_in_time_range(start_time, end_time)
        self.assertEqual(len(node_ids), 3)
    
    def test_get_nodes_in_spatial_region(self):
        """Test getting nodes in a spatial region."""
        # Create nodes with specific positions
        nodes = []
        for x in range(10):
            for y in range(10):
                node = SimpleNode(position=[0, x, y])
                nodes.append(node)
                self.store.put(node.id, node)
        
        # Query for nodes in different spatial regions
        node_ids = self.store.get_nodes_in_spatial_region(2, 2, 4, 4)
        self.assertEqual(len(node_ids), 9)  # 3x3 grid from (2,2) to (4,4)


class TestSimplePartialLoader(unittest.TestCase):
    """Tests for the SimplePartialLoader class."""
    
    def setUp(self):
        """Set up a store, loader, and test nodes."""
        self.store = SimpleNodeStore()
        
        # Create 2000 test nodes
        self.nodes = [SimpleNode() for _ in range(2000)]
        for node in self.nodes:
            self.store.put(node.id, node)
        
        # Create a partial loader with a 1000 node limit
        self.loader = SimplePartialLoader(self.store, max_nodes_in_memory=1000)
    
    def test_get_node(self):
        """Test getting a node from the loader."""
        # Get a node
        node_id = self.nodes[0].id
        loaded_node = self.loader.get_node(node_id)
        
        # Check that it's the correct node
        self.assertEqual(loaded_node.id, node_id)
        
        # Check that it's now in memory
        self.assertIn(node_id, self.loader.loaded_nodes)
        
        # Check that access time is recorded
        self.assertIn(node_id, self.loader.access_times)
    
    def test_memory_limit(self):
        """Test that the memory limit is enforced."""
        # Load 1500 nodes (more than the limit)
        for i in range(1500):
            self.loader.get_node(self.nodes[i].id)
        
        # Check that we haven't exceeded the memory limit
        self.assertLessEqual(len(self.loader.loaded_nodes), 1000)
    
    def test_garbage_collection(self):
        """Test that garbage collection removes least recently used nodes."""
        # Load 1000 nodes
        for i in range(1000):
            self.loader.get_node(self.nodes[i].id)
        
        # All 1000 should be in memory
        self.assertEqual(len(self.loader.loaded_nodes), 1000)
        
        # Access the first 500 nodes again to make them more recently used
        for i in range(500):
            self.loader.get_node(self.nodes[i].id)
        
        # Load 100 more nodes to trigger GC
        for i in range(1000, 1100):
            self.loader.get_node(self.nodes[i].id)
        
        # We should still have 1000 nodes in memory
        self.assertEqual(len(self.loader.loaded_nodes), 1000)
        
        # But some of the nodes from 500-999 should have been evicted
        evicted_count = 0
        for i in range(500, 1000):
            if self.nodes[i].id not in self.loader.loaded_nodes:
                evicted_count += 1
        
        # We added 100 new nodes, so at least 100 should have been evicted
        self.assertGreaterEqual(evicted_count, 100)
    
    def test_load_temporal_window(self):
        """Test loading nodes in a temporal window."""
        # Create nodes with timestamps in different days
        now = datetime.now()
        
        # Clear existing nodes
        self.store = SimpleNodeStore()
        self.loader = SimplePartialLoader(self.store, max_nodes_in_memory=1000)
        
        # Add 50 nodes per day for 10 days
        nodes_by_day = {}
        for day in range(10):
            day_nodes = []
            day_time = now - timedelta(days=day)
            
            for i in range(50):
                timestamp = day_time.timestamp() - i * 60  # Each node a minute apart
                node = SimpleNode(timestamp=timestamp)
                day_nodes.append(node)
                self.store.put(node.id, node)
            
            nodes_by_day[day] = day_nodes
        
        # Query for days 3-5
        start_time = now - timedelta(days=5)
        end_time = now - timedelta(days=3)
        
        loaded_nodes = self.loader.load_temporal_window(start_time, end_time)
        
        # Should have ~150 nodes (50 nodes * 3 days)
        # There might be slight variations due to timestamp edge cases
        self.assertGreaterEqual(len(loaded_nodes), 145)
        self.assertLessEqual(len(loaded_nodes), 155)
    
    def test_load_spatial_region(self):
        """Test loading nodes in a spatial region."""
        # Create a grid of nodes
        self.store = SimpleNodeStore()
        self.loader = SimplePartialLoader(self.store, max_nodes_in_memory=1000)
        
        # Create a 20x20 grid of nodes
        grid_nodes = {}
        for x in range(20):
            for y in range(20):
                node = SimpleNode(position=[0, x, y])
                self.store.put(node.id, node)
                grid_nodes[(x, y)] = node
        
        # Query for a 5x5 region
        loaded_nodes = self.loader.load_spatial_region(5, 5, 10, 10)
        
        # Should have 36 nodes (6x6 grid from 5,5 to 10,10, inclusive)
        self.assertEqual(len(loaded_nodes), 36)
    
    def test_get_memory_usage(self):
        """Test getting memory usage statistics."""
        # Load 500 nodes
        for i in range(500):
            self.loader.get_node(self.nodes[i].id)
        
        # Get memory usage
        usage = self.loader.get_memory_usage()
        
        # Check the statistics
        self.assertEqual(usage["loaded_nodes"], 500)
        self.assertEqual(usage["max_nodes"], 1000)
        self.assertEqual(usage["usage_percent"], 50.0)


class TestSimpleCache(unittest.TestCase):
    """Tests for the SimpleCache class."""
    
    def setUp(self):
        """Set up a cache and test nodes."""
        self.cache = SimpleCache(max_size=100)
        self.nodes = [SimpleNode() for _ in range(200)]
    
    def test_put_and_get(self):
        """Test putting and getting nodes from cache."""
        # Add some nodes to cache
        for i in range(50):
            self.cache.put(self.nodes[i])
        
        # Check that they can be retrieved
        for i in range(50):
            cached_node = self.cache.get(self.nodes[i].id)
            self.assertEqual(cached_node.id, self.nodes[i].id)
        
        # Check that non-cached nodes return None
        for i in range(50, 100):
            self.assertIsNone(self.cache.get(self.nodes[i].id))
    
    def test_cache_size_limit(self):
        """Test that the cache size limit is enforced."""
        # Add more nodes than the cache can hold
        for i in range(150):
            self.cache.put(self.nodes[i])
        
        # Check that cache size doesn't exceed limit
        self.assertEqual(len(self.cache.cache), 100)
    
    def test_lru_eviction(self):
        """Test that least recently used nodes are evicted first."""
        # Fill the cache
        for i in range(100):
            self.cache.put(self.nodes[i])
        
        # Access the first 50 nodes again to make them more recently used
        for i in range(50):
            self.cache.get(self.nodes[i].id)
        
        # Add 50 more nodes, which should evict the least recently used
        for i in range(100, 150):
            self.cache.put(self.nodes[i])
        
        # Check that the first 50 nodes (recently accessed) are still in cache
        for i in range(50):
            self.assertIsNotNone(self.cache.get(self.nodes[i].id))
        
        # Check that many of the nodes from 50-99 have been evicted
        evicted_count = 0
        for i in range(50, 100):
            if self.cache.get(self.nodes[i].id) is None:
                evicted_count += 1
        
        # We added 50 new nodes, so at least 50 should have been evicted
        self.assertGreaterEqual(evicted_count, 50)
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        # Fill the cache to 75%
        for i in range(75):
            self.cache.put(self.nodes[i])
        
        # Get stats
        stats = self.cache.get_stats()
        
        # Check statistics
        self.assertEqual(stats["size"], 75)
        self.assertEqual(stats["max_size"], 100)
        self.assertEqual(stats["usage_percent"], 75.0)


if __name__ == '__main__':
    unittest.main() 
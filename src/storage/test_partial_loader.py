"""
Tests for the partial loading system.

This module tests the memory management capabilities of the partial loader.
"""

import unittest
import uuid
from datetime import datetime, timedelta
import time
import threading
from unittest.mock import Mock, patch

from ..core.node_v2 import Node
from .partial_loader import PartialLoader, MemoryMonitor, StreamingQueryResult


class TestPartialLoader(unittest.TestCase):
    """Tests for the PartialLoader class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock node store
        self.mock_store = Mock()
        
        # Create a partial loader with a small memory limit for testing
        self.loader = PartialLoader(
            store=self.mock_store,
            max_nodes_in_memory=10,
            prefetch_size=2,
            gc_interval=0.1  # Short interval for testing
        )
        
        # Create some test nodes
        self.test_nodes = {}
        for i in range(20):
            node_id = uuid.uuid4()
            node = Mock(spec=Node)
            node.id = node_id
            
            # Add time position for half the nodes
            if i % 2 == 0:
                node.position = [datetime(2023, 1, i+1).timestamp(), 0, 0]
            else:
                node.position = None
                
            # Add connections between nodes
            connected_ids = []
            for j in range(3):
                if i + j + 1 < 20:
                    connected_ids.append(uuid.uuid4())
            
            node.get_connected_nodes = Mock(return_value=connected_ids)
            self.test_nodes[node_id] = node
        
        # Set up the mock store's get method
        self.mock_store.get = Mock(side_effect=lambda node_id: self.test_nodes.get(node_id))
    
    def tearDown(self):
        """Clean up after the test."""
        # Stop the garbage collection thread
        self.loader.close()
    
    def test_get_node(self):
        """Test getting a node from the partial loader."""
        # Get a node ID from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        
        # Get the node
        node = self.loader.get_node(node_id)
        
        # Verify it's the correct node
        self.assertEqual(node, self.test_nodes[node_id])
        
        # Verify it was loaded into memory
        self.assertIn(node_id, self.loader.loaded_nodes)
    
    def test_memory_limit(self):
        """Test that the memory limit is enforced."""
        # Get more nodes than the memory limit
        node_ids = list(self.test_nodes.keys())[:15]
        
        # Load each node
        for node_id in node_ids:
            node = self.loader.get_node(node_id)
            self.assertEqual(node, self.test_nodes[node_id])
        
        # Verify that we haven't exceeded the memory limit
        # There might be slightly more nodes if GC hasn't run yet
        time.sleep(0.2)  # Give GC a chance to run
        self.assertLessEqual(len(self.loader.loaded_nodes), self.loader.max_nodes_in_memory + 5)
    
    def test_pin_node(self):
        """Test pinning a node to keep it in memory."""
        # Get a node ID from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        
        # Pin the node
        success = self.loader.pin_node(node_id)
        
        # Verify it was pinned
        self.assertTrue(success)
        self.assertIn(node_id, self.loader.pinned_nodes)
        
        # Load many other nodes to trigger garbage collection
        other_ids = list(self.test_nodes.keys())[1:15]
        for other_id in other_ids:
            self.loader.get_node(other_id)
        
        # Wait for GC to run
        time.sleep(0.2)
        
        # Verify the pinned node is still in memory
        self.assertIn(node_id, self.loader.loaded_nodes)
    
    def test_unpin_node(self):
        """Test unpinning a node."""
        # Get a node ID from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        
        # Pin and then unpin the node
        self.loader.pin_node(node_id)
        self.loader.unpin_node(node_id)
        
        # Verify it was unpinned
        self.assertNotIn(node_id, self.loader.pinned_nodes)
    
    def test_streaming_iterator(self):
        """Test the streaming iterator."""
        # Get some node IDs from our test nodes
        node_ids = list(self.test_nodes.keys())[:5]
        
        # Create a streaming iterator
        iterator = self.loader.get_streaming_iterator(node_ids, batch_size=2)
        
        # Collect nodes from the iterator
        streamed_nodes = list(iterator)
        
        # Verify we got the expected nodes
        self.assertEqual(len(streamed_nodes), len(node_ids))
        for node in streamed_nodes:
            self.assertIn(node.id, node_ids)
    
    @patch('src.storage.partial_loader.datetime')
    def test_load_temporal_window(self, mock_datetime):
        """Test loading nodes in a time window."""
        # Set up mock datetime
        mock_now = datetime(2023, 1, 15)
        mock_datetime.now.return_value = mock_now
        
        # Set up mock for get_nodes_in_time_range
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 10)
        node_ids = list(self.test_nodes.keys())[:5]
        self.mock_store.get_nodes_in_time_range = Mock(return_value=node_ids)
        
        # Load nodes in the time window
        nodes = self.loader.load_temporal_window(start_time, end_time)
        
        # Verify the correct nodes were loaded
        self.assertEqual(len(nodes), len(node_ids))
        for node in nodes:
            self.assertIn(node.id, node_ids)
        
        # Verify the time window was tracked
        self.assertIn((start_time, end_time), self.loader.recent_time_windows)
    
    def test_load_spatial_region(self):
        """Test loading nodes in a spatial region."""
        # Set up mock for get_nodes_in_spatial_region
        x_min, y_min, x_max, y_max = 0, 0, 10, 10
        node_ids = list(self.test_nodes.keys())[5:10]
        self.mock_store.get_nodes_in_spatial_region = Mock(return_value=node_ids)
        
        # Load nodes in the spatial region
        nodes = self.loader.load_spatial_region(x_min, y_min, x_max, y_max)
        
        # Verify the correct nodes were loaded
        self.assertEqual(len(nodes), len(node_ids))
        for node in nodes:
            self.assertIn(node.id, node_ids)
        
        # Verify the spatial region was tracked
        self.assertIn([x_min, y_min, x_max, y_max], self.loader.recent_spatial_regions)
    
    def test_reference_counting(self):
        """Test reference counting for node usage."""
        # Get a node ID
        node_id = next(iter(self.test_nodes.keys()))
        node = self.loader.get_node(node_id)
        
        # Begin using the node
        self.loader.begin_node_usage(node)
        
        # Verify the reference count was incremented
        self.assertEqual(self.loader.node_ref_count[node_id], 1)
        
        # Begin using the node again
        self.loader.begin_node_usage(node)
        self.assertEqual(self.loader.node_ref_count[node_id], 2)
        
        # End using the node
        self.loader.end_node_usage(node)
        self.assertEqual(self.loader.node_ref_count[node_id], 1)
        
        self.loader.end_node_usage(node)
        self.assertEqual(self.loader.node_ref_count[node_id], 0)
    
    def test_close(self):
        """Test closing the partial loader."""
        # Load some nodes
        for node_id in list(self.test_nodes.keys())[:5]:
            self.loader.get_node(node_id)
            
        # Close the loader
        self.loader.close()
        
        # Verify collections were cleared
        self.assertEqual(len(self.loader.loaded_nodes), 0)
        self.assertEqual(len(self.loader.access_times), 0)
        self.assertEqual(len(self.loader.recent_time_windows), 0)
        self.assertEqual(len(self.loader.recent_spatial_regions), 0)
        self.assertEqual(len(self.loader.pinned_nodes), 0)
        self.assertEqual(len(self.loader.node_ref_count), 0)


class TestMemoryMonitor(unittest.TestCase):
    """Tests for the MemoryMonitor class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.monitor = MemoryMonitor(
            warning_threshold_mb=100,
            critical_threshold_mb=200,
            check_interval=0.1  # Short interval for testing
        )
    
    def tearDown(self):
        """Clean up after the test."""
        self.monitor.stop_monitoring()
    
    @patch('src.storage.partial_loader.psutil')
    def test_memory_usage_tracking(self, mock_psutil):
        """Test tracking memory usage."""
        # Set up mock for process memory info
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=150 * 1024 * 1024)  # 150MB
        mock_psutil.Process.return_value = mock_process
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Give the monitoring thread a chance to run
        time.sleep(0.2)
        
        # Check memory usage
        usage = self.monitor.get_memory_usage()
        
        # Verify the usage was recorded
        self.assertAlmostEqual(usage["current_mb"], 150, delta=1)
    
    @patch('src.storage.partial_loader.psutil')
    def test_warning_callback(self, mock_psutil):
        """Test warning callback."""
        # Set up mock for process memory info
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=150 * 1024 * 1024)  # 150MB
        mock_psutil.Process.return_value = mock_process
        
        # Create a callback to track if it was called
        callback_called = False
        
        def warning_callback():
            nonlocal callback_called
            callback_called = True
        
        # Add the callback
        self.monitor.add_warning_callback(warning_callback)
        
        # Run the memory check directly
        self.monitor._check_memory()
        
        # Verify the callback was called
        self.assertTrue(callback_called)
    
    @patch('src.storage.partial_loader.psutil')
    def test_critical_callback(self, mock_psutil):
        """Test critical callback."""
        # Set up mock for process memory info
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=250 * 1024 * 1024)  # 250MB
        mock_psutil.Process.return_value = mock_process
        
        # Create a callback to track if it was called
        callback_called = False
        
        def critical_callback():
            nonlocal callback_called
            callback_called = True
        
        # Add the callback
        self.monitor.add_critical_callback(critical_callback)
        
        # Run the memory check directly
        self.monitor._check_memory()
        
        # Verify the callback was called
        self.assertTrue(callback_called)


class TestStreamingQueryResult(unittest.TestCase):
    """Tests for the StreamingQueryResult class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock partial loader
        self.mock_loader = Mock(spec=PartialLoader)
        
        # Create test nodes
        self.test_nodes = {}
        node_ids = []
        for i in range(10):
            node_id = uuid.uuid4()
            node = Mock(spec=Node)
            node.id = node_id
            self.test_nodes[node_id] = node
            node_ids.append(node_id)
        
        # Set up the mock loader's get_streaming_iterator method
        def mock_iterator(ids, batch_size=None):
            for node_id in ids:
                yield self.test_nodes[node_id]
        
        self.mock_loader.get_streaming_iterator = mock_iterator
        
        # Create the streaming result
        self.node_ids = list(self.test_nodes.keys())
        self.result = StreamingQueryResult(
            node_ids=self.node_ids,
            partial_loader=self.mock_loader,
            batch_size=3
        )
    
    def test_count(self):
        """Test getting the count of results."""
        self.assertEqual(self.result.count(), len(self.node_ids))
    
    def test_iterator(self):
        """Test iterating over the results."""
        # Collect nodes from the iterator
        nodes = list(self.result)
        
        # Verify we got all the expected nodes
        self.assertEqual(len(nodes), len(self.node_ids))
        for node in nodes:
            self.assertIn(node.id, self.node_ids)
    
    def test_get_batch(self):
        """Test getting a batch of results."""
        # Get a batch from the middle
        batch = self.result.get_batch(3, 4)
        
        # Verify the batch has the expected size
        self.assertEqual(len(batch), 4)
        
        # Verify the nodes are the ones we expected
        batch_ids = [node.id for node in batch]
        expected_ids = self.node_ids[3:7]
        self.assertEqual(set(batch_ids), set(expected_ids))


if __name__ == '__main__':
    unittest.main() 
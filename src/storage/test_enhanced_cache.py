"""
Tests for the enhanced caching implementations.

This module tests the enhanced caching functionality including predictive prefetching
and temporal-aware frequency caching.
"""

import unittest
import uuid
from datetime import datetime, timedelta
import time
import threading
from unittest.mock import Mock, patch

from ..core.node_v2 import Node
from .cache import PredictivePrefetchCache, TemporalFrequencyCache


class TestPredictivePrefetchCache(unittest.TestCase):
    """Tests for the PredictivePrefetchCache class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a cache with a small size for testing
        self.cache = PredictivePrefetchCache(
            max_size=10,
            prefetch_count=3,
            prefetch_threshold=0.5
        )
        
        # Create a mock node store
        self.mock_store = Mock()
        self.cache.set_node_store(self.mock_store)
        
        # Create some test nodes
        self.test_nodes = {}
        for i in range(20):
            node_id = uuid.uuid4()
            node = Mock(spec=Node)
            node.id = node_id
            
            # Set connected nodes
            connected_ids = []
            for j in range(3):
                if i + j + 1 < 20:
                    connected_id = uuid.uuid4()
                    connected_ids.append(connected_id)
            
            node.get_connected_nodes = Mock(return_value=connected_ids)
            
            self.test_nodes[node_id] = node
        
        # Set up the mock store's get method
        self.mock_store.get = Mock(side_effect=lambda node_id: self.test_nodes.get(node_id))
    
    def tearDown(self):
        """Clean up after the test."""
        # Stop the prefetch thread
        self.cache.close()
    
    def test_put_and_get(self):
        """Test putting and getting nodes from the cache."""
        # Get a node from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        node = self.test_nodes[node_id]
        
        # Put the node in the cache
        self.cache.put(node)
        
        # Get the node from cache
        cached_node = self.cache.get(node_id)
        
        # Verify it's the correct node
        self.assertEqual(cached_node, node)
    
    def test_access_pattern_tracking(self):
        """Test that access patterns are tracked."""
        # Get two nodes from our test nodes
        node_ids = list(self.test_nodes.keys())[:2]
        nodes = [self.test_nodes[node_id] for node_id in node_ids]
        
        # Put the nodes in the cache
        for node in nodes:
            self.cache.put(node)
        
        # Access the nodes in sequence
        self.cache.get(node_ids[0])
        self.cache.get(node_ids[1])
        
        # Verify the access sequence was recorded
        self.assertEqual(self.cache.access_sequence, [node_ids[0], node_ids[1]])
        
        # Verify the transition was recorded
        self.assertIn(node_ids[0], self.cache.transitions)
        self.assertIn(node_ids[1], self.cache.transitions[node_ids[0]])
        self.assertEqual(self.cache.transitions[node_ids[0]][node_ids[1]], 1)
    
    def test_connection_tracking(self):
        """Test that connections between nodes are tracked."""
        # Get a node from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        node = self.test_nodes[node_id]
        
        # Put the node in the cache
        self.cache.put(node)
        
        # Verify the connections were recorded
        self.assertIn(node_id, self.cache.connections)
        self.assertEqual(self.cache.connections[node_id], set(node.get_connected_nodes()))
    
    def test_node_prediction(self):
        """Test prediction of which nodes will be accessed next."""
        # Create a sequence of accesses
        node_ids = list(self.test_nodes.keys())[:5]
        nodes = [self.test_nodes[node_id] for node_id in node_ids]
        
        # Put all nodes in the cache
        for node in nodes:
            self.cache.put(node)
        
        # Access nodes in a pattern: A -> B -> C -> B -> A -> B
        # This should make B highly likely after A
        self.cache.get(node_ids[0])  # A
        self.cache.get(node_ids[1])  # B
        self.cache.get(node_ids[2])  # C
        self.cache.get(node_ids[1])  # B
        self.cache.get(node_ids[0])  # A
        self.cache.get(node_ids[1])  # B
        
        # Get predictions after A
        predictions = self.cache._predict_next_nodes(node_ids[0])
        
        # Verify that B is predicted with high probability
        predicted_ids = [node_id for node_id, _ in predictions]
        self.assertIn(node_ids[1], predicted_ids)
        self.assertEqual(predicted_ids[0], node_ids[1])  # B should be first
    
    def test_prefetch_queueing(self):
        """Test that nodes are queued for prefetching."""
        # Create a mock for the prefetch thread
        # Access nodes in a pattern: A -> B -> C -> B -> A -> B
        node_ids = list(self.test_nodes.keys())[:5]
        nodes = [self.test_nodes[node_id] for node_id in node_ids]
        
        # Put all nodes in the cache
        for node in nodes:
            self.cache.put(node)
        
        # Access nodes in a pattern: A -> B -> C -> B -> A -> B
        # This should make B highly likely after A
        self.cache.get(node_ids[0])  # A
        self.cache.get(node_ids[1])  # B
        self.cache.get(node_ids[2])  # C
        self.cache.get(node_ids[1])  # B
        self.cache.get(node_ids[0])  # A
        self.cache.get(node_ids[1])  # B
        
        # Reset the prefetch queue
        with self.cache.prefetch_lock:
            self.cache.prefetch_queue = []
        
        # Now access A again, which should queue B for prefetching
        self.cache.get(node_ids[0])  # A
        
        # Wait for the prefetch queue to be processed
        time.sleep(0.2)
        
        # Verify that B was queued for prefetching
        # Since the thread processes the queue, it might be empty now
        # so we check if get was called with the right node_id
        self.mock_store.get.assert_any_call(node_ids[1])


class TestTemporalFrequencyCache(unittest.TestCase):
    """Tests for the TemporalFrequencyCache class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a cache with a small size for testing
        self.cache = TemporalFrequencyCache(
            max_size=10,
            time_weight=0.5,
            frequency_weight=0.3,
            recency_weight=0.2
        )
        
        # Create some test nodes with different temporal coordinates
        self.test_nodes = {}
        for i in range(20):
            node_id = uuid.uuid4()
            node = Mock(spec=Node)
            node.id = node_id
            
            # Set a temporal position for the node
            timestamp = datetime(2023, 1, i+1).timestamp()
            node.position = [timestamp, 0, 0]  # time, x, y
            
            self.test_nodes[node_id] = node
    
    def test_put_and_get(self):
        """Test putting and getting nodes from the cache."""
        # Get a node from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        node = self.test_nodes[node_id]
        
        # Put the node in the cache
        self.cache.put(node)
        
        # Get the node from cache
        cached_node = self.cache.get(node_id)
        
        # Verify it's the correct node
        self.assertEqual(cached_node, node)
    
    def test_frequency_tracking(self):
        """Test that access frequency is tracked by time window."""
        # Get a node from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        node = self.test_nodes[node_id]
        
        # Put the node in the cache
        self.cache.put(node)
        
        # Get the current time window
        current_time = datetime.now()
        window_start = datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour
        )
        
        # Access the node multiple times
        for _ in range(3):
            self.cache.get(node_id)
        
        # Verify the access frequency was recorded
        self.assertIn(window_start, self.cache.time_window_access)
        self.assertIn(node_id, self.cache.time_window_access[window_start])
        self.assertEqual(self.cache.time_window_access[window_start][node_id], 3)
    
    def test_frequency_score(self):
        """Test calculation of the frequency score."""
        # Get a node from our test nodes
        node_id = next(iter(self.test_nodes.keys()))
        node = self.test_nodes[node_id]
        
        # Put the node in the cache
        self.cache.put(node)
        
        # Access the node multiple times
        for _ in range(5):
            self.cache.get(node_id)
        
        # Get the frequency score
        score = self.cache._calculate_frequency_score(node)
        
        # Verify the score is positive (since we accessed the node)
        self.assertGreater(score, 0)
    
    def test_recency_score(self):
        """Test calculation of the recency score."""
        # Get two nodes from our test nodes
        node_ids = list(self.test_nodes.keys())[:2]
        nodes = [self.test_nodes[node_id] for node_id in node_ids]
        
        # Put both nodes in the cache
        for node in nodes:
            self.cache.put(node)
        
        # Access the first node
        self.cache.get(node_ids[0])
        
        # Calculate recency scores
        score0 = self.cache._calculate_recency_score(nodes[0])
        score1 = self.cache._calculate_recency_score(nodes[1])
        
        # The first node should have a higher recency score
        self.assertGreater(score0, score1)
    
    def test_cleaning_old_windows(self):
        """Test that old time windows are cleaned up."""
        # Create more time windows than the maximum
        now = datetime.now()
        for i in range(30):
            window_start = datetime(
                now.year,
                now.month,
                now.day,
                now.hour
            ) - timedelta(hours=i)
            
            self.cache.time_window_access[window_start] = {uuid.uuid4(): i}
        
        # Manually call the cleanup method
        self.cache._clean_old_windows()
        
        # Verify that we have at most max_time_windows
        self.assertLessEqual(len(self.cache.time_window_access), self.cache.max_time_windows)
    
    def test_clear(self):
        """Test clearing the cache."""
        # Put some nodes in the cache
        for node_id, node in list(self.test_nodes.items())[:5]:
            self.cache.put(node)
            
        # Access each node
        for node_id in list(self.test_nodes.keys())[:5]:
            self.cache.get(node_id)
            
        # Clear the cache
        self.cache.clear()
        
        # Verify everything is cleared
        self.assertEqual(len(self.cache.cache), 0)
        self.assertEqual(len(self.cache.time_window_access), 0)


if __name__ == '__main__':
    unittest.main() 
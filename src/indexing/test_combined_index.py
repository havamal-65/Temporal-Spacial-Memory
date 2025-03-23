"""
Unit tests for the combined temporal-spatial index.
"""

import unittest
from unittest.mock import MagicMock, patch
import time
import random
import math
from datetime import datetime, timedelta

from src.indexing.combined_index import TemporalIndex, TemporalSpatialIndex
from src.core.node import Node
from src.core.coordinates import Coordinates
from src.core.exceptions import IndexingError

class TestTemporalIndex(unittest.TestCase):
    """Tests for the TemporalIndex class."""
    
    def setUp(self):
        """Set up test cases."""
        self.index = TemporalIndex(bucket_size_minutes=10)
        
        # Create test timestamps
        self.timestamp1 = time.time()
        self.timestamp2 = self.timestamp1 + 600  # 10 minutes later
        self.timestamp3 = self.timestamp1 + 1200  # 20 minutes later
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.index.bucket_size, 600)  # 10 minutes in seconds
        self.assertIsInstance(self.index.buckets, dict)
        self.assertIsInstance(self.index.node_timestamps, dict)
    
    def test_get_bucket_key(self):
        """Test bucket key calculation."""
        key1 = self.index._get_bucket_key(self.timestamp1)
        key2 = self.index._get_bucket_key(self.timestamp2)
        key3 = self.index._get_bucket_key(self.timestamp3)
        
        self.assertIsInstance(key1, int)
        self.assertEqual(key1, int(self.timestamp1 // 600))
        self.assertEqual(key2, int(self.timestamp2 // 600))
        self.assertEqual(key3, int(self.timestamp3 // 600))
        
        # Different bucket keys for different time buckets
        self.assertNotEqual(key1, key2)
        self.assertNotEqual(key2, key3)
    
    def test_insert(self):
        """Test node insertion."""
        # Insert nodes
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp2)
        self.index.insert("node3", self.timestamp3)
        
        # Verify node timestamps
        self.assertEqual(self.index.node_timestamps["node1"], self.timestamp1)
        self.assertEqual(self.index.node_timestamps["node2"], self.timestamp2)
        self.assertEqual(self.index.node_timestamps["node3"], self.timestamp3)
        
        # Verify bucket contents
        bucket1 = self.index._get_bucket_key(self.timestamp1)
        bucket2 = self.index._get_bucket_key(self.timestamp2)
        bucket3 = self.index._get_bucket_key(self.timestamp3)
        
        self.assertIn("node1", self.index.buckets[bucket1])
        self.assertIn("node2", self.index.buckets[bucket2])
        self.assertIn("node3", self.index.buckets[bucket3])
    
    def test_update_existing_node(self):
        """Test updating an existing node."""
        # Insert node
        self.index.insert("node1", self.timestamp1)
        bucket1 = self.index._get_bucket_key(self.timestamp1)
        
        # Verify initial state
        self.assertIn("node1", self.index.buckets[bucket1])
        self.assertEqual(self.index.node_timestamps["node1"], self.timestamp1)
        
        # Update node timestamp
        self.index.insert("node1", self.timestamp2)
        bucket2 = self.index._get_bucket_key(self.timestamp2)
        
        # Verify node moved to new bucket
        self.assertNotIn("node1", self.index.buckets[bucket1])
        self.assertIn("node1", self.index.buckets[bucket2])
        self.assertEqual(self.index.node_timestamps["node1"], self.timestamp2)
    
    def test_remove(self):
        """Test node removal."""
        # Insert nodes
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp2)
        
        bucket1 = self.index._get_bucket_key(self.timestamp1)
        
        # Verify initial state
        self.assertIn("node1", self.index.buckets[bucket1])
        self.assertIn("node1", self.index.node_timestamps)
        
        # Remove node
        result = self.index.remove("node1")
        
        # Verify node removed
        self.assertTrue(result)
        self.assertNotIn("node1", self.index.buckets[bucket1])
        self.assertNotIn("node1", self.index.node_timestamps)
        
        # Try removing non-existent node
        result = self.index.remove("nonexistent")
        self.assertFalse(result)
    
    def test_query_range(self):
        """Test time range query."""
        # Insert nodes at different times
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp2)
        self.index.insert("node3", self.timestamp3)
        
        # Query full range
        result = self.index.query_range(self.timestamp1, self.timestamp3)
        
        # Should include all nodes
        self.assertEqual(len(result), 3)
        self.assertIn("node1", result)
        self.assertIn("node2", result)
        self.assertIn("node3", result)
        
        # Query partial range
        result = self.index.query_range(self.timestamp1, self.timestamp2 - 1)
        
        # Should include only node1
        self.assertEqual(len(result), 1)
        self.assertIn("node1", result)
        self.assertNotIn("node2", result)
        self.assertNotIn("node3", result)
    
    def test_query_time_series(self):
        """Test time series query."""
        # Insert nodes at different times
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp2)
        self.index.insert("node3", self.timestamp3)
        
        # Query with 10-minute intervals
        result = self.index.query_time_series(self.timestamp1, self.timestamp3, 600)
        
        # Should have 3 intervals with one node in each
        self.assertEqual(len(result), 3)
        self.assertIn(0, result)  # First interval
        self.assertIn(1, result)  # Second interval
        self.assertIn(2, result)  # Third interval
        
        self.assertIn("node1", result[0])
        self.assertIn("node2", result[1])
        self.assertIn("node3", result[2])
    
    def test_get_node_count(self):
        """Test getting node count."""
        # Empty index
        self.assertEqual(self.index.get_node_count(), 0)
        
        # Add nodes
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp2)
        
        self.assertEqual(self.index.get_node_count(), 2)
        
        # Remove node
        self.index.remove("node1")
        self.assertEqual(self.index.get_node_count(), 1)
    
    def test_get_bucket_distribution(self):
        """Test getting bucket distribution."""
        # Insert nodes in different buckets
        self.index.insert("node1", self.timestamp1)
        self.index.insert("node2", self.timestamp1 + 10)  # Same bucket as node1
        self.index.insert("node3", self.timestamp2)       # Different bucket
        
        bucket1 = self.index._get_bucket_key(self.timestamp1)
        bucket2 = self.index._get_bucket_key(self.timestamp2)
        
        # Get distribution
        distribution = self.index.get_bucket_distribution()
        
        # Should have 2 buckets
        self.assertEqual(len(distribution), 2)
        self.assertIn(bucket1, distribution)
        self.assertIn(bucket2, distribution)
        
        # First bucket should have 2 nodes, second should have 1
        self.assertEqual(distribution[bucket1], 2)
        self.assertEqual(distribution[bucket2], 1)

class TestTemporalSpatialIndex(unittest.TestCase):
    """Tests for the TemporalSpatialIndex class."""
    
    def setUp(self):
        """Set up test cases."""
        self.config = {
            "temporal_bucket_size": 15,  # 15 minutes
            "spatial_dimension": 3,
            "auto_tuning": True
        }
        self.index = TemporalSpatialIndex(config=self.config)
        
        # Create test nodes
        self.node1 = Node(
            id="node1",
            content="Test 1",
            coordinates=Coordinates(spatial=(1, 2, 3), temporal=time.time())
        )
        
        self.node2 = Node(
            id="node2",
            content="Test 2",
            coordinates=Coordinates(spatial=(4, 5, 6), temporal=time.time() + 600)
        )
        
        self.node3 = Node(
            id="node3",
            content="Test 3",
            coordinates=Coordinates(spatial=(7, 8, 9), temporal=time.time() + 1200)
        )
        
        # Node with only spatial coordinates
        self.spatial_node = Node(
            id="spatial",
            content="Spatial only",
            coordinates=Coordinates(spatial=(10, 11, 12))
        )
        
        # Node with only temporal coordinates
        self.temporal_node = Node(
            id="temporal",
            content="Temporal only",
            coordinates=Coordinates(temporal=time.time() + 1800)
        )
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.index.temporal_bucket_size, 15)
        self.assertEqual(self.index.spatial_dimension, 3)
        self.assertTrue(self.index.auto_tuning)
        
        self.assertIsInstance(self.index.spatial_index, object)
        self.assertIsInstance(self.index.temporal_index, TemporalIndex)
        self.assertIsInstance(self.index.nodes, dict)
    
    def test_insert(self):
        """Test node insertion."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.spatial_node)
        self.index.insert(self.temporal_node)
        
        # Verify nodes stored
        self.assertIn(self.node1.id, self.index.nodes)
        self.assertIn(self.node2.id, self.index.nodes)
        self.assertIn(self.spatial_node.id, self.index.nodes)
        self.assertIn(self.temporal_node.id, self.index.nodes)
        
        # Verify correct node objects stored
        self.assertEqual(self.index.nodes[self.node1.id], self.node1)
        self.assertEqual(self.index.nodes[self.node2.id], self.node2)
        
        # Try inserting node without coordinates
        invalid_node = Node(id="invalid", content="Invalid")
        with self.assertRaises(IndexingError):
            self.index.insert(invalid_node)
    
    def test_bulk_load(self):
        """Test bulk loading nodes."""
        nodes = [self.node1, self.node2, self.node3, self.spatial_node, self.temporal_node]
        
        # Bulk load
        self.index.bulk_load(nodes)
        
        # Verify all nodes stored
        for node in nodes:
            self.assertIn(node.id, self.index.nodes)
            self.assertEqual(self.index.nodes[node.id], node)
    
    def test_remove(self):
        """Test node removal."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        
        # Verify initial state
        self.assertIn(self.node1.id, self.index.nodes)
        
        # Remove node
        result = self.index.remove(self.node1.id)
        
        # Verify node removed
        self.assertTrue(result)
        self.assertNotIn(self.node1.id, self.index.nodes)
        
        # Try removing non-existent node
        result = self.index.remove("nonexistent")
        self.assertFalse(result)
    
    def test_update(self):
        """Test node update."""
        # Insert node
        self.index.insert(self.node1)
        
        # Create updated node
        updated_node = Node(
            id=self.node1.id,
            content="Updated",
            coordinates=Coordinates(spatial=(10, 20, 30), temporal=time.time() + 3600)
        )
        
        # Update node
        self.index.update(updated_node)
        
        # Verify node updated
        self.assertEqual(self.index.nodes[self.node1.id], updated_node)
        self.assertEqual(self.index.nodes[self.node1.id].content, "Updated")
    
    def test_query_spatial(self):
        """Test spatial query."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.spatial_node)
        
        # Create spatial criteria for nearest neighbor query
        spatial_criteria = {
            "point": (1, 2, 3),
            "distance": 1.0
        }
        
        # Mock the spatial index nearest method
        self.index.spatial_index.nearest = MagicMock(return_value=[self.node1])
        
        # Query using only spatial criteria
        result = self.index.query(spatial_criteria=spatial_criteria)
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.node1)
        
        # Verify mock called
        self.index.spatial_index.nearest.assert_called_once_with(
            point=(1, 2, 3),
            num_results=1000,
            max_distance=1.0
        )
    
    def test_query_temporal(self):
        """Test temporal query."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.temporal_node)
        
        # Create temporal criteria
        start_time = time.time()
        end_time = time.time() + 1800
        temporal_criteria = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        # Mock the temporal index query_range method
        self.index.temporal_index.query_range = MagicMock(
            return_value={"node1", "node2"}
        )
        
        # Query using only temporal criteria
        result = self.index.query(temporal_criteria=temporal_criteria)
        
        # Verify result contains nodes with the right IDs
        self.assertEqual(len(result), 2)
        result_ids = {node.id for node in result}
        self.assertIn("node1", result_ids)
        self.assertIn("node2", result_ids)
        
        # Verify mock called
        self.index.temporal_index.query_range.assert_called_once_with(start_time, end_time)
    
    def test_query_combined(self):
        """Test combined spatial and temporal query."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.node3)
        
        # Create criteria
        spatial_criteria = {
            "point": (1, 2, 3),
            "distance": 10.0
        }
        temporal_criteria = {
            "start_time": time.time(),
            "end_time": time.time() + 900
        }
        
        # Mock the indices
        self.index.spatial_index.nearest = MagicMock(
            return_value=[self.node1, self.node2]
        )
        self.index.temporal_index.query_range = MagicMock(
            return_value={"node1", "node3"}
        )
        
        # Query using both criteria
        result = self.index.query(
            spatial_criteria=spatial_criteria,
            temporal_criteria=temporal_criteria
        )
        
        # Only node1 should be in both result sets
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "node1")
    
    def test_query_time_series(self):
        """Test time series query."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.node3)
        
        # Mock the temporal index query_time_series method
        self.index.temporal_index.query_time_series = MagicMock(
            return_value={
                0: {"node1"},
                1: {"node2"},
                2: {"node3"}
            }
        )
        
        # Mock spatial query result
        self.index.query = MagicMock(
            return_value=[self.node1, self.node2]
        )
        
        # Query time series with spatial filtering
        start_time = time.time()
        end_time = start_time + 1800
        interval = 600
        spatial_criteria = {"point": (1, 2, 3), "distance": 10.0}
        
        result = self.index.query_time_series(
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            spatial_criteria=spatial_criteria
        )
        
        # Verify mock calls
        self.index.temporal_index.query_time_series.assert_called_once_with(
            start_time, end_time, interval
        )
        self.index.query.assert_called_once_with(
            spatial_criteria=spatial_criteria
        )
    
    def test_get_statistics(self):
        """Test getting statistics."""
        # Insert some nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        
        # Get statistics
        stats = self.index.get_statistics()
        
        # Verify basic stats
        self.assertIn("inserts", stats)
        self.assertEqual(stats["inserts"], 2)
        self.assertIn("spatial_node_count", stats)
        self.assertIn("temporal_node_count", stats)
        self.assertIn("total_node_count", stats)
        self.assertEqual(stats["total_node_count"], 2)
    
    @patch('src.indexing.combined_index.TemporalIndex')
    def test_tune_parameters(self, mock_temporal_index):
        """Test parameter tuning."""
        # Create a mock temporal index with bucket distribution
        bucket_distribution = {1: 1000, 2: 100, 3: 50}
        mock_temporal_instance = MagicMock()
        mock_temporal_instance.get_bucket_distribution.return_value = bucket_distribution
        mock_temporal_instance.node_timestamps = {"node1": 100, "node2": 200}
        mock_temporal_index.return_value = mock_temporal_instance
        
        # Set up the index with high query counts to trigger tuning
        self.index.temporal_index = mock_temporal_instance
        self.index.stats["temporal_queries"] = 100
        self.index.stats["combined_queries"] = 50
        
        # Call tune_parameters
        self.index.tune_parameters()
        
        # Verify new temporal index created
        mock_temporal_index.assert_called_once()
    
    def test_rebuild(self):
        """Test index rebuild."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        self.index.insert(self.spatial_node)
        
        # Mock the indices
        original_spatial_index = self.index.spatial_index
        original_temporal_index = self.index.temporal_index
        
        # Patch the index classes
        with patch('src.indexing.combined_index.SpatialIndex') as mock_spatial, \
             patch('src.indexing.combined_index.TemporalIndex') as mock_temporal:
            
            # Setup mocks
            mock_spatial_instance = MagicMock()
            mock_temporal_instance = MagicMock()
            mock_spatial.return_value = mock_spatial_instance
            mock_temporal.return_value = mock_temporal_instance
            
            # Rebuild index
            self.index.rebuild()
            
            # Verify new indices created
            mock_spatial.assert_called_once_with(dimension=3)
            mock_temporal.assert_called_once_with(bucket_size_minutes=15)
            
            # Verify bulk load called
            mock_spatial_instance.bulk_load.assert_called_once()
            
            # Verify nodes transferred to temporal index
            self.assertEqual(
                mock_temporal_instance.insert.call_count,
                sum(1 for node in self.index.nodes.values() if node.coordinates.temporal)
            )
    
    def test_visualize_distribution(self):
        """Test visualization data generation."""
        # Insert nodes
        self.index.insert(self.node1)
        self.index.insert(self.node2)
        
        # Mock the temporal index bucket distribution
        bucket_distribution = {1: 1, 2: 1}
        self.index.temporal_index.get_bucket_distribution = MagicMock(
            return_value=bucket_distribution
        )
        
        # Get visualization data
        vis_data = self.index.visualize_distribution()
        
        # Verify data structure
        self.assertIn("temporal", vis_data)
        self.assertIn("spatial", vis_data)
        self.assertIn("bucket_distribution", vis_data["temporal"])
        self.assertEqual(vis_data["temporal"]["bucket_distribution"], bucket_distribution)

if __name__ == "__main__":
    unittest.main() 
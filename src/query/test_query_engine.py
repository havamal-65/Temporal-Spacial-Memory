"""
Unit tests for the query execution engine.
"""

import unittest
from datetime import datetime
import time
from unittest.mock import MagicMock, patch
import tempfile
import shutil
import os

from src.query.query_engine import (
    QueryEngine, ExecutionPlan, ExecutionStep, ExecutionMode,
    IndexScanStrategy, FullScanStrategy, FilterStrategy, JoinStrategy,
    QueryOptimizer, QueryResult, ResultPagination, ResultTransformer
)
from src.query.query import Query, FilterCriteria, QueryType
from src.core.node import Node
from src.core.coordinates import Coordinates
from src.core.exceptions import QueryExecutionError

class TestExecutionStep(unittest.TestCase):
    """Tests for the ExecutionStep class."""
    
    def test_create_execution_step(self):
        """Test creating an execution step."""
        step = ExecutionStep(operation="test", parameters={"param": "value"}, estimated_cost=10.0)
        self.assertEqual(step.operation, "test")
        self.assertEqual(step.parameters, {"param": "value"})
        self.assertEqual(step.estimated_cost, 10.0)
    
    def test_step_string_representation(self):
        """Test string representation of an execution step."""
        step = ExecutionStep(operation="test", parameters={"a": 1, "b": "test"}, estimated_cost=5.0)
        str_rep = str(step)
        self.assertIn("test", str_rep)
        self.assertIn("a=1", str_rep)
        self.assertIn("b=test", str_rep)

class TestExecutionPlan(unittest.TestCase):
    """Tests for the ExecutionPlan class."""
    
    def setUp(self):
        """Set up test cases."""
        self.query = MagicMock(spec=Query)
        self.plan = ExecutionPlan(self.query, estimated_cost=5.0)
    
    def test_add_step(self):
        """Test adding a step to the plan."""
        step = ExecutionStep(operation="test", parameters={}, estimated_cost=10.0)
        self.plan.add_step(step)
        
        self.assertEqual(len(self.plan.steps), 1)
        self.assertEqual(self.plan.steps[0], step)
        self.assertEqual(self.plan.estimated_cost, 15.0)  # 5.0 + 10.0
    
    def test_get_estimated_cost(self):
        """Test getting the estimated cost."""
        self.assertEqual(self.plan.get_estimated_cost(), 5.0)
        
        # Add a step to increase cost
        step = ExecutionStep(operation="test", parameters={}, estimated_cost=7.5)
        self.plan.add_step(step)
        
        self.assertEqual(self.plan.get_estimated_cost(), 12.5)  # 5.0 + 7.5
    
    def test_plan_string_representation(self):
        """Test string representation of the plan."""
        step1 = ExecutionStep(operation="step1", parameters={"p1": "v1"}, estimated_cost=2.0)
        step2 = ExecutionStep(operation="step2", parameters={"p2": "v2"}, estimated_cost=3.0)
        
        self.plan.add_step(step1)
        self.plan.add_step(step2)
        
        str_rep = str(self.plan)
        self.assertIn("ExecutionPlan", str_rep)
        self.assertIn("cost=10.00", str_rep)  # 5.0 + 2.0 + 3.0
        self.assertIn("step1", str_rep)
        self.assertIn("step2", str_rep)
        self.assertIn("p1=v1", str_rep)
        self.assertIn("p2=v2", str_rep)

class TestExecutionStrategies(unittest.TestCase):
    """Tests for execution strategies."""
    
    def setUp(self):
        """Set up test cases."""
        self.node1 = Node(id="1", content="Test 1", coordinates=Coordinates(spatial=(1, 2, 3), temporal=time.time()))
        self.node2 = Node(id="2", content="Test 2", coordinates=Coordinates(spatial=(4, 5, 6), temporal=time.time()))
        
        # Mock context
        self.context = {
            "node_store": MagicMock(),
            "index_manager": MagicMock()
        }
        
        # Setup node store mock
        self.context["node_store"].get_all_nodes.return_value = [self.node1, self.node2]
    
    def test_index_scan_strategy(self):
        """Test index scan strategy."""
        strategy = IndexScanStrategy()
        
        # Setup index manager mock
        index_mock = MagicMock()
        index_mock.query.return_value = [self.node1]
        self.context["index_manager"].get_index.return_value = index_mock
        
        # Test execution
        step = ExecutionStep(
            operation="index_scan",
            parameters={"index_name": "test_index", "criteria": {"test": "value"}}
        )
        result = strategy.execute(step, self.context)
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.node1)
        
        # Verify mock calls
        self.context["index_manager"].get_index.assert_called_once_with("test_index")
        index_mock.query.assert_called_once_with({"test": "value"})
    
    def test_full_scan_strategy(self):
        """Test full scan strategy."""
        strategy = FullScanStrategy()
        
        # Without filter
        step = ExecutionStep(
            operation="full_scan",
            parameters={}
        )
        result = strategy.execute(step, self.context)
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.assertIn(self.node1, result)
        self.assertIn(self.node2, result)
        
        # With filter
        step = ExecutionStep(
            operation="full_scan",
            parameters={"filter_func": lambda node: node.id == "1"}
        )
        result = strategy.execute(step, self.context)
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.node1)
    
    def test_filter_strategy(self):
        """Test filter strategy."""
        strategy = FilterStrategy()
        
        # Create a mock criteria that matches node1
        criteria_mock = MagicMock(spec=FilterCriteria)
        criteria_mock.matches.side_effect = lambda node: node.id == "1"
        
        # Test execution
        step = ExecutionStep(
            operation="filter",
            parameters={"nodes": [self.node1, self.node2], "criteria": criteria_mock}
        )
        result = strategy.execute(step, self.context)
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.node1)
        
        # Verify mock calls
        self.assertEqual(criteria_mock.matches.call_count, 2)
    
    def test_join_strategy(self):
        """Test join strategy."""
        strategy = JoinStrategy()
        
        # Setup nodes
        node3 = Node(id="1", content="Test 3", coordinates=Coordinates(spatial=(7, 8, 9), temporal=time.time()))
        node4 = Node(id="3", content="Test 4", coordinates=Coordinates(spatial=(10, 11, 12), temporal=time.time()))
        
        left_nodes = [self.node1, self.node2]
        right_nodes = [node3, node4]
        
        # Test inner join
        step = ExecutionStep(
            operation="join",
            parameters={"left_nodes": left_nodes, "right_nodes": right_nodes, "join_type": "inner"}
        )
        result = strategy.execute(step, self.context)
        
        # Should return node3 (id="1") which matches self.node1 (id="1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[0].content, "Test 3")
        
        # Test union join
        step = ExecutionStep(
            operation="join",
            parameters={"left_nodes": left_nodes, "right_nodes": right_nodes, "join_type": "union"}
        )
        result = strategy.execute(step, self.context)
        
        # Should return 3 nodes (node1, node2, node4), with node3 merged with node1 due to same ID
        self.assertEqual(len(result), 3)
        
        # Test intersection join
        step = ExecutionStep(
            operation="join",
            parameters={"left_nodes": left_nodes, "right_nodes": right_nodes, "join_type": "intersection"}
        )
        result = strategy.execute(step, self.context)
        
        # Should return node3 (id="1") which matches self.node1 (id="1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[0].content, "Test 3")

class TestQueryOptimizer(unittest.TestCase):
    """Tests for the QueryOptimizer class."""
    
    def setUp(self):
        """Set up test cases."""
        self.index_manager = MagicMock()
        self.optimizer = QueryOptimizer(self.index_manager)
        
        # Create a mock query
        self.query = MagicMock(spec=Query)
        
        # Setup index manager
        self.index_manager.has_index.return_value = True
    
    def test_create_initial_plan(self):
        """Test creating an initial execution plan."""
        # Query with no criteria
        self.query.criteria = None
        plan = self.optimizer._create_initial_plan(self.query)
        
        # Should have one step (full scan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].operation, "full_scan")
        
        # Query with criteria
        self.query.criteria = MagicMock()
        plan = self.optimizer._create_initial_plan(self.query)
        
        # Should have two steps (full scan + filter)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].operation, "full_scan")
        self.assertEqual(plan.steps[1].operation, "filter")
    
    def test_select_indexes_spatial(self):
        """Test selecting spatial index."""
        # Setup query
        self.query.has_spatial_criteria.return_value = True
        self.query.has_temporal_criteria.return_value = False
        self.query.has_other_criteria.return_value = False
        self.query.get_spatial_criteria.return_value = {"test": "value"}
        
        # Create plan
        plan = ExecutionPlan(self.query)
        plan.add_step(ExecutionStep(operation="full_scan", parameters={}, estimated_cost=100.0))
        
        # Optimize plan
        optimized_plan = self.optimizer.select_indexes(plan)
        
        # Should have one step (index scan)
        self.assertEqual(len(optimized_plan.steps), 1)
        self.assertEqual(optimized_plan.steps[0].operation, "index_scan")
        self.assertEqual(optimized_plan.steps[0].parameters["index_name"], "spatial")
        
        # Verify mock calls
        self.index_manager.has_index.assert_called_with("spatial")
    
    def test_select_indexes_combined(self):
        """Test selecting combined index."""
        # Setup query
        self.query.has_spatial_criteria.return_value = True
        self.query.has_temporal_criteria.return_value = True
        self.query.has_other_criteria.return_value = True
        self.query.get_spatial_criteria.return_value = {"spatial": "value"}
        self.query.get_temporal_criteria.return_value = {"temporal": "value"}
        self.query.get_other_criteria.return_value = {"other": "value"}
        
        # Create plan
        plan = ExecutionPlan(self.query)
        plan.add_step(ExecutionStep(operation="full_scan", parameters={}, estimated_cost=100.0))
        
        # Optimize plan
        optimized_plan = self.optimizer.select_indexes(plan)
        
        # Should have two steps (index scan + filter)
        self.assertEqual(len(optimized_plan.steps), 2)
        self.assertEqual(optimized_plan.steps[0].operation, "index_scan")
        self.assertEqual(optimized_plan.steps[0].parameters["index_name"], "combined")
        self.assertEqual(optimized_plan.steps[1].operation, "filter")
        
        # Verify mock calls
        self.index_manager.has_index.assert_any_call("combined")

class TestQueryResult(unittest.TestCase):
    """Tests for the QueryResult class."""
    
    def setUp(self):
        """Set up test cases."""
        self.node1 = Node(id="1", content="Test 1", coordinates=Coordinates(spatial=(1, 2, 3), temporal=time.time()))
        self.node2 = Node(id="2", content="Test 2", coordinates=Coordinates(spatial=(4, 5, 6), temporal=time.time()))
        self.items = [self.node1, self.node2]
    
    def test_query_result_basics(self):
        """Test basic query result functionality."""
        result = QueryResult(items=self.items, metadata={"test": "value"})
        
        self.assertEqual(result.count(), 2)
        self.assertEqual(result.items, self.items)
        self.assertEqual(result.metadata, {"test": "value"})
        self.assertFalse(result.is_paginated())
    
    def test_pagination(self):
        """Test pagination functionality."""
        # Create a paginated result
        pagination = ResultPagination(total_items=10, page_size=5, current_page=1)
        result = QueryResult(items=self.items, pagination=pagination)
        
        self.assertTrue(result.is_paginated())
        self.assertEqual(result.pagination.total_items, 10)
        self.assertEqual(result.pagination.page_size, 5)
        self.assertEqual(result.pagination.current_page, 1)
        
        # Test getting a page
        page_result = result.get_page(1, page_size=1)
        self.assertEqual(page_result.count(), 1)
        self.assertEqual(page_result.items, [self.node1])
        
        # Test invalid page number
        with self.assertRaises(ValueError):
            result.get_page(3)  # Only 2 items, can't get page 3

class TestResultTransformer(unittest.TestCase):
    """Tests for the ResultTransformer class."""
    
    def setUp(self):
        """Set up test cases."""
        self.node1 = Node(id="1", content="B", coordinates=Coordinates(spatial=(1, 2, 3), temporal=100))
        self.node2 = Node(id="2", content="A", coordinates=Coordinates(spatial=(4, 5, 6), temporal=200))
        self.node3 = Node(id="3", content="C", coordinates=Coordinates(spatial=(7, 8, 9), temporal=300))
        self.items = [self.node1, self.node2, self.node3]
        
        self.result = QueryResult(items=self.items.copy())
        self.transformer = ResultTransformer(self.result)
    
    def test_sort(self):
        """Test sorting functionality."""
        # Sort by content
        sorted_result = self.transformer.sort(key=lambda node: node.content).get_result()
        
        self.assertEqual(sorted_result.items[0].content, "A")
        self.assertEqual(sorted_result.items[1].content, "B")
        self.assertEqual(sorted_result.items[2].content, "C")
        
        # Sort by timestamp in reverse
        sorted_result = self.transformer.sort(
            key=lambda node: node.coordinates.temporal,
            reverse=True
        ).get_result()
        
        self.assertEqual(sorted_result.items[0].coordinates.temporal, 300)
        self.assertEqual(sorted_result.items[1].coordinates.temporal, 200)
        self.assertEqual(sorted_result.items[2].coordinates.temporal, 100)
    
    def test_filter(self):
        """Test filtering functionality."""
        # Filter by ID
        filtered_result = self.transformer.filter(
            predicate=lambda node: node.id in {"1", "3"}
        ).get_result()
        
        self.assertEqual(filtered_result.count(), 2)
        self.assertEqual(filtered_result.items[0].id, "1")
        self.assertEqual(filtered_result.items[1].id, "3")
        
        # Filter by content
        filtered_result = self.transformer.filter(
            predicate=lambda node: node.content == "A"
        ).get_result()
        
        self.assertEqual(filtered_result.count(), 1)
        self.assertEqual(filtered_result.items[0].content, "A")
    
    def test_map(self):
        """Test mapping functionality."""
        # Transform nodes to simple objects
        transformed_result = self.transformer.map(
            transformation=lambda node: {"id": node.id, "content": node.content}
        ).get_result()
        
        self.assertEqual(transformed_result.count(), 3)
        self.assertEqual(transformed_result.items[0], {"id": "1", "content": "B"})
        self.assertEqual(transformed_result.items[1], {"id": "3", "content": "C"})
    
    def test_method_chaining(self):
        """Test method chaining."""
        # Filter, sort, then map
        transformed_result = self.transformer.filter(
            predicate=lambda node: node.coordinates.temporal > 100
        ).sort(
            key=lambda node: node.content
        ).map(
            transformation=lambda node: node.content
        ).get_result()
        
        self.assertEqual(transformed_result.count(), 2)
        self.assertEqual(transformed_result.items, ["A", "C"])

class TestQueryEngine(unittest.TestCase):
    """Tests for the QueryEngine class."""
    
    def setUp(self):
        """Set up test cases."""
        self.node_store = MagicMock()
        self.index_manager = MagicMock()
        self.query = MagicMock(spec=Query)
        
        # Setup node store with test nodes
        self.node1 = Node(id="1", content="Test 1", coordinates=Coordinates(spatial=(1, 2, 3), temporal=100))
        self.node2 = Node(id="2", content="Test 2", coordinates=Coordinates(spatial=(4, 5, 6), temporal=200))
        
        self.node_store.get_all_nodes.return_value = [self.node1, self.node2]
        
        # Setup index manager
        self.index_manager.has_index.return_value = True
        self.index_manager.get_index.return_value = MagicMock()
        
        # Create engine
        self.engine = QueryEngine(self.node_store, self.index_manager)
        
        # Mock optimizer
        self.engine.optimizer = MagicMock()
        execution_plan = ExecutionPlan(self.query)
        execution_plan.add_step(ExecutionStep(operation="full_scan", parameters={}))
        self.engine.optimizer.optimize.return_value = execution_plan
    
    def test_execute_basic_query(self):
        """Test executing a basic query."""
        # Setup strategies
        self.engine.strategies["full_scan"] = MagicMock()
        self.engine.strategies["full_scan"].execute.return_value = [self.node1, self.node2]
        
        # Execute query
        result = self.engine.execute(self.query)
        
        # Verify results
        self.assertEqual(result.count(), 2)
        self.assertEqual(result.items, [self.node1, self.node2])
        
        # Verify mock calls
        self.engine.optimizer.optimize.assert_called_once_with(self.query)
        self.engine.strategies["full_scan"].execute.assert_called_once()
    
    def test_cache_functionality(self):
        """Test query result caching."""
        # Setup strategies
        self.engine.strategies["full_scan"] = MagicMock()
        self.engine.strategies["full_scan"].execute.return_value = [self.node1, self.node2]
        
        # Execute query with caching
        self.query.__str__.return_value = "test_query"
        result1 = self.engine.execute(self.query, options={"use_cache": True})
        
        # Execute again - should use cache
        result2 = self.engine.execute(self.query, options={"use_cache": True})
        
        # Verify results
        self.assertEqual(result1.count(), 2)
        self.assertEqual(result2.count(), 2)
        
        # Verify mock calls - strategy should be called only once
        self.assertEqual(self.engine.strategies["full_scan"].execute.call_count, 1)
        
        # Verify statistics
        self.assertEqual(self.engine.stats["cache_hits"], 1)
        self.assertEqual(self.engine.stats["cache_misses"], 1)
    
    def test_statistics_collection(self):
        """Test statistics collection."""
        # Setup strategies
        self.engine.strategies["full_scan"] = MagicMock()
        self.engine.strategies["full_scan"].execute.return_value = [self.node1, self.node2]
        
        # Execute query
        result = self.engine.execute(self.query)
        
        # Verify statistics
        self.assertEqual(self.engine.stats["queries_executed"], 1)
        self.assertGreater(self.engine.stats["total_execution_time"], 0)
        self.assertEqual(self.engine.stats["avg_execution_time"], 
                         self.engine.stats["total_execution_time"])
        
        # Verify result metadata
        self.assertIn("execution_time", result.metadata)
        self.assertEqual(result.metadata["result_count"], 2)

if __name__ == "__main__":
    unittest.main() 
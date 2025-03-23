"""
Query execution engine for the Temporal-Spatial Knowledge Database.

This module implements the query execution engine, including execution strategies,
optimization rules, and result handling mechanisms.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any, Callable, Union
import time
import logging
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass

from src.query.query import Query, FilterCriteria, QueryType
from src.storage.node_store import NodeStore
from src.indexing.rtree import SpatialIndex
from src.core.node import Node
from src.core.exceptions import QueryExecutionError

# Configure logger
logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    """Enumeration of query execution modes."""
    SYNC = "sync"      # Synchronous execution (blocking)
    ASYNC = "async"    # Asynchronous execution (non-blocking)
    BATCH = "batch"    # Batch execution (for multiple queries)

@dataclass
class ExecutionStep:
    """Represents a single step in the query execution plan."""
    operation: str
    parameters: Dict[str, Any]
    estimated_cost: float = 0.0
    
    def __str__(self) -> str:
        """Return a string representation of the execution step."""
        return f"{self.operation}({', '.join(f'{k}={v}' for k, v in self.parameters.items())})"

class ExecutionPlan:
    """Represents a query execution plan with multiple steps."""
    
    def __init__(self, query: Query, estimated_cost: float = 0.0):
        """
        Initialize a new execution plan.
        
        Args:
            query: The query to execute
            estimated_cost: The estimated cost of the plan
        """
        self.query = query
        self.steps: List[ExecutionStep] = []
        self.estimated_cost = estimated_cost
        
    def add_step(self, step: ExecutionStep) -> None:
        """
        Add an execution step to the plan.
        
        Args:
            step: The step to add
        """
        self.steps.append(step)
        self.estimated_cost += step.estimated_cost
    
    def get_estimated_cost(self) -> float:
        """
        Get the estimated cost of the execution plan.
        
        Returns:
            The estimated cost
        """
        return self.estimated_cost
    
    def __str__(self) -> str:
        """Return a string representation of the execution plan."""
        return (f"ExecutionPlan(cost={self.estimated_cost:.2f}, steps=[\n  " + 
                "\n  ".join(str(step) for step in self.steps) + "\n])")

class ExecutionStrategy:
    """Base class for execution strategies."""
    
    def execute(self, step: ExecutionStep, context: Dict[str, Any]) -> List[Node]:
        """
        Execute the strategy.
        
        Args:
            step: The execution step
            context: The execution context
            
        Returns:
            The result nodes
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement execute()")

class IndexScanStrategy(ExecutionStrategy):
    """Strategy for scanning an index."""
    
    def execute(self, step: ExecutionStep, context: Dict[str, Any]) -> List[Node]:
        """
        Execute an index scan.
        
        Args:
            step: The execution step
            context: The execution context
            
        Returns:
            The result nodes
        """
        index_name = step.parameters.get("index_name")
        criteria = step.parameters.get("criteria")
        index_manager = context.get("index_manager")
        
        if not index_name or not index_manager:
            raise QueryExecutionError("Missing index name or index manager")
        
        index = index_manager.get_index(index_name)
        if not index:
            raise QueryExecutionError(f"Index {index_name} not found")
        
        return index.query(criteria)

class FullScanStrategy(ExecutionStrategy):
    """Strategy for performing a full scan of nodes."""
    
    def execute(self, step: ExecutionStep, context: Dict[str, Any]) -> List[Node]:
        """
        Execute a full scan.
        
        Args:
            step: The execution step
            context: The execution context
            
        Returns:
            The result nodes
        """
        node_store = context.get("node_store")
        filter_func = step.parameters.get("filter_func")
        
        if not node_store:
            raise QueryExecutionError("Missing node store")
        
        nodes = node_store.get_all_nodes()
        
        if filter_func:
            nodes = [node for node in nodes if filter_func(node)]
            
        return nodes

class FilterStrategy(ExecutionStrategy):
    """Strategy for filtering nodes based on criteria."""
    
    def execute(self, step: ExecutionStep, context: Dict[str, Any]) -> List[Node]:
        """
        Execute a filter operation.
        
        Args:
            step: The execution step
            context: The execution context
            
        Returns:
            The filtered nodes
        """
        nodes = step.parameters.get("nodes", [])
        criteria = step.parameters.get("criteria")
        
        if not criteria:
            return nodes
        
        return [node for node in nodes if self._matches_criteria(node, criteria)]
    
    def _matches_criteria(self, node: Node, criteria: FilterCriteria) -> bool:
        """
        Check if a node matches the filter criteria.
        
        Args:
            node: The node to check
            criteria: The filter criteria
            
        Returns:
            True if the node matches, False otherwise
        """
        # Implementation depends on the specific criteria structure
        return criteria.matches(node)

class JoinStrategy(ExecutionStrategy):
    """Strategy for joining results from multiple sources."""
    
    def execute(self, step: ExecutionStep, context: Dict[str, Any]) -> List[Node]:
        """
        Execute a join operation.
        
        Args:
            step: The execution step
            context: The execution context
            
        Returns:
            The joined nodes
        """
        left_nodes = step.parameters.get("left_nodes", [])
        right_nodes = step.parameters.get("right_nodes", [])
        join_type = step.parameters.get("join_type", "inner")
        
        if join_type == "inner":
            # Inner join - only nodes that appear in both sets
            left_ids = {node.id for node in left_nodes}
            return [node for node in right_nodes if node.id in left_ids]
        elif join_type == "left":
            # Left join - all nodes from left set
            return left_nodes
        elif join_type == "right":
            # Right join - all nodes from right set
            return right_nodes
        elif join_type == "union":
            # Union - all nodes from both sets (deduplicated)
            result_dict = {node.id: node for node in left_nodes}
            for node in right_nodes:
                if node.id not in result_dict:
                    result_dict[node.id] = node
            return list(result_dict.values())
        elif join_type == "intersection":
            # Intersection - only nodes that appear in both sets
            left_ids = {node.id for node in left_nodes}
            return [node for node in right_nodes if node.id in left_ids]
        else:
            raise QueryExecutionError(f"Unsupported join type: {join_type}")

class QueryOptimizer:
    """Optimizer for query execution plans."""
    
    def __init__(self, index_manager: Any, statistics_manager: Any = None):
        """
        Initialize a new query optimizer.
        
        Args:
            index_manager: The index manager
            statistics_manager: Optional statistics manager
        """
        self.index_manager = index_manager
        self.statistics_manager = statistics_manager
        self.optimization_rules = [
            self.select_indexes,
            self.push_down_filters,
            self.optimize_join_order
        ]
    
    def optimize(self, query: Query) -> ExecutionPlan:
        """
        Optimize a query execution plan.
        
        Args:
            query: The query to optimize
            
        Returns:
            The optimized execution plan
        """
        # Create initial plan
        plan = self._create_initial_plan(query)
        
        # Apply optimization rules
        for rule in self.optimization_rules:
            plan = rule(plan)
        
        return plan
    
    def _create_initial_plan(self, query: Query) -> ExecutionPlan:
        """
        Create an initial execution plan for a query.
        
        Args:
            query: The query to create a plan for
            
        Returns:
            The initial execution plan
        """
        plan = ExecutionPlan(query)
        
        # Add a simple full scan step for now
        plan.add_step(ExecutionStep(
            operation="full_scan",
            parameters={"filter_func": lambda node: True},
            estimated_cost=100.0  # High cost for full scan
        ))
        
        # Add a filter step if the query has criteria
        if query.criteria:
            plan.add_step(ExecutionStep(
                operation="filter",
                parameters={"criteria": query.criteria},
                estimated_cost=10.0
            ))
        
        return plan
    
    def select_indexes(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply index selection optimization rule.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        query = plan.query
        
        # Create a new plan
        optimized_plan = ExecutionPlan(query)
        
        # Check if we can use the spatial index
        if query.has_spatial_criteria() and self.index_manager.has_index("spatial"):
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "spatial",
                    "criteria": query.get_spatial_criteria()
                },
                estimated_cost=10.0  # Lower cost for index scan
            ))
        # Check if we can use the temporal index
        elif query.has_temporal_criteria() and self.index_manager.has_index("temporal"):
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "temporal",
                    "criteria": query.get_temporal_criteria()
                },
                estimated_cost=10.0
            ))
        # Check if we can use a combined index
        elif (query.has_spatial_criteria() and query.has_temporal_criteria() and 
              self.index_manager.has_index("combined")):
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "combined",
                    "criteria": {
                        "spatial": query.get_spatial_criteria(),
                        "temporal": query.get_temporal_criteria()
                    }
                },
                estimated_cost=5.0  # Even lower cost for combined index
            ))
        else:
            # Fall back to the full scan approach
            return plan
        
        # If we have other criteria, add a filter step
        if query.has_other_criteria():
            optimized_plan.add_step(ExecutionStep(
                operation="filter",
                parameters={"criteria": query.get_other_criteria()},
                estimated_cost=5.0
            ))
        
        # If the optimized plan has a lower cost, use it
        if optimized_plan.get_estimated_cost() < plan.get_estimated_cost():
            return optimized_plan
        
        return plan
    
    def push_down_filters(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply filter pushdown optimization rule.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        # For simplicity, just return the original plan for now
        return plan
    
    def optimize_join_order(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply join order optimization rule.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        # For simplicity, just return the original plan for now
        return plan

class QueryResult:
    """Represents the result of a query execution."""
    
    def __init__(self, items: List[Node] = None, pagination: Optional['ResultPagination'] = None, 
                 metadata: Dict[str, Any] = None):
        """
        Initialize a new query result.
        
        Args:
            items: The result items
            pagination: Optional pagination information
            metadata: Optional metadata
        """
        self.items = items or []
        self.pagination = pagination
        self.metadata = metadata or {}
    
    def count(self) -> int:
        """
        Get the number of items in the result.
        
        Returns:
            The number of items
        """
        return len(self.items)
    
    def is_paginated(self) -> bool:
        """
        Check if the result is paginated.
        
        Returns:
            True if the result is paginated, False otherwise
        """
        return self.pagination is not None
    
    def get_page(self, page_number: int, page_size: Optional[int] = None) -> 'QueryResult':
        """
        Get a specific page of results.
        
        Args:
            page_number: The page number (1-based)
            page_size: The page size (default is the current page size)
            
        Returns:
            A new QueryResult object with the requested page
            
        Raises:
            ValueError: If the page number is invalid
        """
        if not self.is_paginated():
            # Create pagination if it doesn't exist
            page_size = page_size or len(self.items)
            self.pagination = ResultPagination(len(self.items), page_size)
        
        page_size = page_size or self.pagination.page_size
        
        total_pages = (len(self.items) + page_size - 1) // page_size
        if page_number < 1 or page_number > total_pages:
            raise ValueError(f"Invalid page number: {page_number}, total pages: {total_pages}")
        
        start_idx = (page_number - 1) * page_size
        end_idx = min(start_idx + page_size, len(self.items))
        
        # Create a new pagination object for the new page
        new_pagination = ResultPagination(
            total_items=len(self.items),
            page_size=page_size,
            current_page=page_number
        )
        
        return QueryResult(
            items=self.items[start_idx:end_idx],
            pagination=new_pagination,
            metadata=self.metadata.copy()
        )

class ResultPagination:
    """Represents pagination information for query results."""
    
    def __init__(self, total_items: int, page_size: int, current_page: int = 1):
        """
        Initialize pagination information.
        
        Args:
            total_items: The total number of items
            page_size: The page size
            current_page: The current page number (1-based)
        """
        self.total_items = total_items
        self.page_size = page_size
        self.current_page = current_page
    
    @property
    def total_pages(self) -> int:
        """
        Get the total number of pages.
        
        Returns:
            The total number of pages
        """
        return (self.total_items + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """
        Check if there is a next page.
        
        Returns:
            True if there is a next page, False otherwise
        """
        return self.current_page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """
        Check if there is a previous page.
        
        Returns:
            True if there is a previous page, False otherwise
        """
        return self.current_page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """
        Get the next page number.
        
        Returns:
            The next page number, or None if there is no next page
        """
        return self.current_page + 1 if self.has_next else None
    
    @property
    def previous_page(self) -> Optional[int]:
        """
        Get the previous page number.
        
        Returns:
            The previous page number, or None if there is no previous page
        """
        return self.current_page - 1 if self.has_previous else None

class ResultTransformer:
    """Utility for transforming query results."""
    
    def __init__(self, result: QueryResult):
        """
        Initialize a new result transformer.
        
        Args:
            result: The query result to transform
        """
        self.result = result
    
    def sort(self, key: Callable[[Node], Any], reverse: bool = False) -> 'ResultTransformer':
        """
        Sort the result items.
        
        Args:
            key: The sort key function
            reverse: Whether to sort in reverse order
            
        Returns:
            self, for method chaining
        """
        self.result.items.sort(key=key, reverse=reverse)
        return self
    
    def filter(self, predicate: Callable[[Node], bool]) -> 'ResultTransformer':
        """
        Filter the result items.
        
        Args:
            predicate: The filter predicate
            
        Returns:
            self, for method chaining
        """
        self.result.items = [item for item in self.result.items if predicate(item)]
        return self
    
    def map(self, transformation: Callable[[Node], Any]) -> 'ResultTransformer':
        """
        Transform each result item.
        
        Args:
            transformation: The transformation function
            
        Returns:
            self, for method chaining
        """
        self.result.items = [transformation(item) for item in self.result.items]
        return self
    
    def get_result(self) -> QueryResult:
        """
        Get the transformed result.
        
        Returns:
            The transformed query result
        """
        return self.result

class QueryEngine:
    """Main query execution engine for the database."""
    
    def __init__(self, node_store: NodeStore, index_manager: Any, config: Dict[str, Any] = None):
        """
        Initialize a new query engine.
        
        Args:
            node_store: The node store
            index_manager: The index manager
            config: Optional configuration options
        """
        self.node_store = node_store
        self.index_manager = index_manager
        self.config = config or {}
        
        # Create optimizer
        self.optimizer = QueryOptimizer(index_manager)
        
        # Create execution strategies
        self.strategies = {
            "index_scan": IndexScanStrategy(),
            "full_scan": FullScanStrategy(),
            "filter": FilterStrategy(),
            "join": JoinStrategy()
        }
        
        # Statistics
        self.stats = {
            "queries_executed": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Result cache
        self.result_cache: Dict[str, Tuple[QueryResult, float]] = {}
        self.cache_ttl = self.config.get("cache_ttl", 60.0)  # Cache TTL in seconds
        
        logger.info("Query engine initialized")
    
    def execute(self, query: Query, options: Dict[str, Any] = None) -> QueryResult:
        """
        Execute a query.
        
        Args:
            query: The query to execute
            options: Optional execution options
            
        Returns:
            The query result
            
        Raises:
            QueryExecutionError: If there's an error executing the query
        """
        options = options or {}
        execution_mode = options.get("mode", ExecutionMode.SYNC)
        use_cache = options.get("use_cache", True)
        
        # Check cache if enabled
        if use_cache:
            cache_key = str(query)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                return cached_result
        
        try:
            # Record start time
            start_time = time.time()
            
            # Generate and optimize execution plan
            plan = self.optimizer.optimize(query)
            
            logger.debug(f"Execution plan: {plan}")
            
            # Execute the plan
            if execution_mode == ExecutionMode.SYNC:
                result = self._execute_sync(plan)
            elif execution_mode == ExecutionMode.ASYNC:
                # For simplicity, we'll just execute synchronously for now
                result = self._execute_sync(plan)
            else:
                raise QueryExecutionError(f"Unsupported execution mode: {execution_mode}")
            
            # Record execution time
            duration = time.time() - start_time
            
            # Update statistics
            self._update_statistics(query, result, duration)
            
            # Cache result if caching is enabled
            if use_cache:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            raise QueryExecutionError(f"Error executing query: {e}") from e
    
    def _execute_sync(self, plan: ExecutionPlan) -> QueryResult:
        """
        Execute a plan synchronously.
        
        Args:
            plan: The execution plan
            
        Returns:
            The query result
        """
        # Execution context
        context = {
            "node_store": self.node_store,
            "index_manager": self.index_manager,
            "intermediate_results": {}
        }
        
        # Execute each step
        results = None
        for i, step in enumerate(plan.steps):
            strategy = self.strategies.get(step.operation)
            if not strategy:
                raise QueryExecutionError(f"Unknown operation: {step.operation}")
            
            # Add previous results to step parameters if needed
            if i > 0 and results is not None:
                step.parameters["nodes"] = results
            
            # Execute the step
            results = strategy.execute(step, context)
            
            # Store intermediate results
            context["intermediate_results"][i] = results
        
        # Create result object
        result = QueryResult(items=results or [])
        
        return result
    
    def _check_cache(self, cache_key: str) -> Optional[QueryResult]:
        """
        Check if a query result is in the cache.
        
        Args:
            cache_key: The cache key
            
        Returns:
            The cached result, or None if not found or expired
        """
        if cache_key not in self.result_cache:
            self.stats["cache_misses"] += 1
            return None
        
        result, timestamp = self.result_cache[cache_key]
        
        # Check if the result has expired
        if time.time() - timestamp > self.cache_ttl:
            del self.result_cache[cache_key]
            self.stats["cache_misses"] += 1
            return None
        
        self.stats["cache_hits"] += 1
        return result
    
    def _cache_result(self, cache_key: str, result: QueryResult) -> None:
        """
        Cache a query result.
        
        Args:
            cache_key: The cache key
            result: The query result
        """
        self.result_cache[cache_key] = (result, time.time())
        
        # Prune cache if it gets too large
        max_cache_size = self.config.get("max_cache_size", 100)
        if len(self.result_cache) > max_cache_size:
            # Remove oldest entries
            sorted_keys = sorted(
                self.result_cache.keys(),
                key=lambda k: self.result_cache[k][1]
            )
            for key in sorted_keys[:len(sorted_keys) // 2]:
                del self.result_cache[key]
    
    def _update_statistics(self, query: Query, result: QueryResult, duration: float) -> None:
        """
        Update execution statistics.
        
        Args:
            query: The executed query
            result: The query result
            duration: The execution duration in seconds
        """
        self.stats["queries_executed"] += 1
        self.stats["total_execution_time"] += duration
        self.stats["avg_execution_time"] = (
            self.stats["total_execution_time"] / self.stats["queries_executed"]
        )
        
        # Add execution statistics to result metadata
        result.metadata["execution_time"] = duration
        result.metadata["result_count"] = len(result.items) 
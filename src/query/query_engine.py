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
from datetime import datetime, timedelta
import uuid

from src.query.query import Query, FilterCriteria, QueryType
from src.storage.node_store import NodeStore
from src.indexing.rtree import SpatialIndex
from src.core.node import Node
from src.core.exceptions import QueryExecutionError
from .statistics import QueryStatistics, QueryCostModel, QueryMonitor

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
    
    def __init__(self, index_manager: Any, statistics_manager: Optional[QueryStatistics] = None):
        """
        Initialize a new query optimizer.
        
        Args:
            index_manager: The index manager
            statistics_manager: Optional statistics manager
        """
        self.index_manager = index_manager
        self.statistics = statistics_manager or QueryStatistics()
        self.cost_model = QueryCostModel(self.statistics)
        
        # Cache config - these can be tuned
        self.plan_cache_size = 100
        self.plan_cache: Dict[str, Tuple[ExecutionPlan, datetime]] = {}
        self.plan_cache_ttl = timedelta(minutes=10)
        
        # Register optimization rules with estimated execution order
        self.optimization_rules = [
            (self.select_indexes, 10),
            (self.push_down_filters, 20),
            (self.optimize_join_order, 30),
            (self.estimate_costs, 40),
            (self.apply_result_size_limits, 50)
        ]
        
        # Sort rules by execution order
        self.optimization_rules.sort(key=lambda x: x[1])
    
    def optimize(self, query: Query) -> ExecutionPlan:
        """
        Optimize a query execution plan.
        
        Args:
            query: The query to optimize
            
        Returns:
            The optimized execution plan
        """
        # Check the plan cache first
        cache_key = str(query)
        cached_plan = self._check_plan_cache(cache_key)
        if cached_plan:
            return cached_plan
        
        # Create initial plan
        plan = self._create_initial_plan(query)
        
        # Apply optimization rules in order
        for rule_func, _ in self.optimization_rules:
            plan = rule_func(plan)
        
        # Cache the optimized plan
        self._cache_plan(cache_key, plan)
        
        # Set optimization statistics on the plan
        plan.statistics = {
            "optimized": True,
            "rules_applied": [rule[0].__name__ for rule in self.optimization_rules],
            "estimated_cost": plan.estimated_cost
        }
        
        return plan
    
    def _check_plan_cache(self, cache_key: str) -> Optional[ExecutionPlan]:
        """Check if we have a cached execution plan for this query."""
        if cache_key in self.plan_cache:
            plan, timestamp = self.plan_cache[cache_key]
            
            # Check if plan is still valid
            if datetime.now() - timestamp < self.plan_cache_ttl:
                # Update timestamp to keep it fresh
                self.plan_cache[cache_key] = (plan, datetime.now())
                return plan
            
            # Plan is stale, remove it
            del self.plan_cache[cache_key]
        
        return None
    
    def _cache_plan(self, cache_key: str, plan: ExecutionPlan) -> None:
        """Cache an execution plan."""
        # Ensure cache doesn't grow too large
        if len(self.plan_cache) >= self.plan_cache_size:
            # Remove oldest entry
            oldest_key = min(self.plan_cache.keys(), 
                            key=lambda k: self.plan_cache[k][1])
            del self.plan_cache[oldest_key]
        
        # Add to cache
        self.plan_cache[cache_key] = (plan, datetime.now())
    
    def _create_initial_plan(self, query: Query) -> ExecutionPlan:
        """
        Create an initial execution plan for a query.
        
        Args:
            query: The query to create a plan for
            
        Returns:
            The initial execution plan
        """
        plan = ExecutionPlan(query)
        
        # Estimate the collection size
        collection_size = self._estimate_collection_size()
        
        # Add a simple full scan step for now
        full_scan_cost = self.cost_model.estimate_full_scan_cost(collection_size)
        plan.add_step(ExecutionStep(
            operation="full_scan",
            parameters={"filter_func": lambda node: True},
            estimated_cost=full_scan_cost
        ))
        
        # Add a filter step if the query has criteria
        if query.criteria:
            filter_cost = self.cost_model.estimate_filter_cost(
                collection_size, 
                0.5,  # Default selectivity
                collection_size
            )
            plan.add_step(ExecutionStep(
                operation="filter",
                parameters={"criteria": query.criteria},
                estimated_cost=filter_cost
            ))
        
        return plan
    
    def _estimate_collection_size(self) -> int:
        """Estimate the size of the data collection."""
        # Use statistics if available
        # For now, use a default size
        return 10000
    
    def select_indexes(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply index selection optimization rule.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        query = plan.query
        collection_size = self._estimate_collection_size()
        
        # Create a new plan
        optimized_plan = ExecutionPlan(query)
        
        # Check if we can use the spatial index
        if query.has_spatial_criteria() and self.index_manager.has_index("spatial"):
            # Estimate the number of nodes that will match the spatial criteria
            spatial_criteria = query.get_spatial_criteria()
            spatial_matches = self._estimate_spatial_matches(spatial_criteria, collection_size)
            
            # Calculate the cost of using the spatial index
            index_cost = self.cost_model.estimate_index_scan_cost(
                "spatial", 
                spatial_matches, 
                collection_size
            )
            
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "spatial",
                    "criteria": spatial_criteria
                },
                estimated_cost=index_cost
            ))
            
            # Record index usage
            if self.statistics:
                self.statistics.record_index_usage("spatial", True)
        
        # Check if we can use the temporal index
        elif query.has_temporal_criteria() and self.index_manager.has_index("temporal"):
            # Estimate the number of nodes that will match the temporal criteria
            temporal_criteria = query.get_temporal_criteria()
            temporal_matches = self._estimate_temporal_matches(temporal_criteria, collection_size)
            
            # Calculate the cost of using the temporal index
            index_cost = self.cost_model.estimate_index_scan_cost(
                "temporal", 
                temporal_matches, 
                collection_size
            )
            
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "temporal",
                    "criteria": temporal_criteria
                },
                estimated_cost=index_cost
            ))
            
            # Record index usage
            if self.statistics:
                self.statistics.record_index_usage("temporal", True)
                
        # Check if we can use a combined index
        elif (query.has_spatial_criteria() and query.has_temporal_criteria() and 
              self.index_manager.has_index("combined")):
            # Estimate the number of nodes that will match the combined criteria
            spatial_criteria = query.get_spatial_criteria()
            temporal_criteria = query.get_temporal_criteria()
            
            # Estimate for combined criteria
            combined_matches = self._estimate_combined_matches(
                spatial_criteria, 
                temporal_criteria, 
                collection_size
            )
            
            # Calculate the cost of using the combined index
            index_cost = self.cost_model.estimate_index_scan_cost(
                "combined", 
                combined_matches, 
                collection_size
            )
            
            optimized_plan.add_step(ExecutionStep(
                operation="index_scan",
                parameters={
                    "index_name": "combined",
                    "criteria": {
                        "spatial": spatial_criteria,
                        "temporal": temporal_criteria
                    }
                },
                estimated_cost=index_cost
            ))
            
            # Record index usage
            if self.statistics:
                self.statistics.record_index_usage("combined", True)
        else:
            # Fall back to the full scan approach
            return plan
        
        # If we have other criteria, add a filter step
        if query.has_other_criteria():
            # Get remaining criteria
            other_criteria = query.get_other_criteria()
            
            # Estimate number of results after index scan
            # This will be the input to the filter step
            result_size_after_index = optimized_plan.steps[0].estimated_output_size
            if result_size_after_index is None:
                # Use an estimate based on the index
                if "index_name" in optimized_plan.steps[0].parameters:
                    index_name = optimized_plan.steps[0].parameters["index_name"]
                    
                    if index_name == "spatial":
                        result_size_after_index = self._estimate_spatial_matches(
                            spatial_criteria, 
                            collection_size
                        )
                    elif index_name == "temporal":
                        result_size_after_index = self._estimate_temporal_matches(
                            temporal_criteria, 
                            collection_size
                        )
                    elif index_name == "combined":
                        result_size_after_index = self._estimate_combined_matches(
                            spatial_criteria, 
                            temporal_criteria, 
                            collection_size
                        )
                    else:
                        result_size_after_index = collection_size // 2
                else:
                    result_size_after_index = collection_size // 2
            
            # Estimate the selectivity of other criteria
            selectivity = self._estimate_filter_selectivity(other_criteria)
            
            # Calculate the cost of the filter
            filter_cost = self.cost_model.estimate_filter_cost(
                collection_size, 
                selectivity, 
                result_size_after_index
            )
            
            # Calculate the estimated output size
            estimated_output_size = int(result_size_after_index * selectivity)
            
            # Add the filter step
            filter_step = ExecutionStep(
                operation="filter",
                parameters={"criteria": other_criteria},
                estimated_cost=filter_cost
            )
            filter_step.estimated_output_size = estimated_output_size
            
            optimized_plan.add_step(filter_step)
        
        # If the optimized plan has a lower cost, use it
        if optimized_plan.get_estimated_cost() < plan.get_estimated_cost():
            return optimized_plan
        
        # If we get here, the original plan was better
        if self.statistics:
            # Record that we didn't use indexes
            if query.has_spatial_criteria():
                self.statistics.record_index_usage("spatial", False)
            if query.has_temporal_criteria():
                self.statistics.record_index_usage("temporal", False)
            if query.has_spatial_criteria() and query.has_temporal_criteria():
                self.statistics.record_index_usage("combined", False)
        
        return plan
    
    def _estimate_spatial_matches(self, 
                                 spatial_criteria: Dict[str, Any], 
                                 collection_size: int) -> int:
        """Estimate the number of nodes that will match spatial criteria."""
        # For now, use a simple estimate based on the area
        # In a real implementation, you'd use statistics and spatial calculations
        
        # Default selectivity if we can't calculate
        default_selectivity = 0.1
        
        # Extract bounded area if available
        if "bounds" in spatial_criteria:
            bounds = spatial_criteria["bounds"]
            
            # Calculate area of bounds
            try:
                x_min, y_min, x_max, y_max = bounds
                area = (x_max - x_min) * (y_max - y_min)
                
                # Assume data is in a space from 0 to 1
                total_area = 1.0 
                
                # Calculate selectivity based on the relative area
                selectivity = min(1.0, max(0.01, area / total_area))
                
                return int(collection_size * selectivity)
            except (ValueError, TypeError):
                pass
        
        # For nearest-neighbor queries, estimate based on limit
        if "nearest" in spatial_criteria and "limit" in spatial_criteria:
            limit = spatial_criteria["limit"]
            return min(collection_size, limit)
        
        # Default estimate
        return int(collection_size * default_selectivity)
    
    def _estimate_temporal_matches(self, 
                                  temporal_criteria: Dict[str, Any], 
                                  collection_size: int) -> int:
        """Estimate the number of nodes that will match temporal criteria."""
        # Default selectivity if we can't calculate
        default_selectivity = 0.2
        
        # Extract time range if available
        if "range" in temporal_criteria:
            time_range = temporal_criteria["range"]
            
            # Calculate duration of range
            try:
                start_time, end_time = time_range
                
                # Convert to timestamps if needed
                if isinstance(start_time, datetime):
                    start_time = start_time.timestamp()
                if isinstance(end_time, datetime):
                    end_time = end_time.timestamp()
                
                # Calculate duration in seconds
                duration = end_time - start_time
                
                # Assume data spans about 1 year
                # This should be based on actual statistics
                total_duration = 60 * 60 * 24 * 365  # seconds in a year
                
                # Calculate selectivity based on the relative duration
                selectivity = min(1.0, max(0.01, duration / total_duration))
                
                return int(collection_size * selectivity)
            except (ValueError, TypeError):
                pass
        
        # Default estimate
        return int(collection_size * default_selectivity)
    
    def _estimate_combined_matches(self, 
                                 spatial_criteria: Dict[str, Any],
                                 temporal_criteria: Dict[str, Any],
                                 collection_size: int) -> int:
        """Estimate the number of nodes that will match combined criteria."""
        # Estimate matches for individual criteria
        spatial_matches = self._estimate_spatial_matches(spatial_criteria, collection_size)
        temporal_matches = self._estimate_temporal_matches(temporal_criteria, collection_size)
        
        # For combined index, we need to estimate the intersection
        # A simple estimate is to assume independence and multiply the probabilities
        spatial_selectivity = spatial_matches / collection_size
        temporal_selectivity = temporal_matches / collection_size
        
        # Calculate combined selectivity
        combined_selectivity = spatial_selectivity * temporal_selectivity
        
        # Apply a correction factor based on observed correlation
        # This should ideally come from statistics
        correlation_factor = 1.5  # > 1 means positively correlated, < 1 means negatively correlated
        
        adjusted_selectivity = min(1.0, combined_selectivity * correlation_factor)
        
        return int(collection_size * adjusted_selectivity)
    
    def _estimate_filter_selectivity(self, criteria: Dict[str, Any]) -> float:
        """Estimate the selectivity of filter criteria."""
        # Default selectivity
        default_selectivity = 0.5
        
        # If no criteria, everything passes
        if not criteria:
            return 1.0
            
        # In a real implementation, you'd use statistics about field distributions
        # and combine the selectivity of each criterion
        
        # For now, just use the number of criteria to estimate selectivity
        # More criteria usually means more selective
        num_criteria = len(criteria)
        
        # Assume each criterion is equally selective
        per_criterion_selectivity = 0.7  # 70% of records pass each criterion
        
        # Combine selectivity assuming independence
        combined_selectivity = per_criterion_selectivity ** num_criteria
        
        # Ensure we don't get too close to zero
        return max(0.01, combined_selectivity)
    
    def push_down_filters(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply filter pushdown optimization rule.
        
        This moves filters earlier in the execution plan to reduce
        the number of records processed by later operations.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        # For now, we'll just handle the simple case of pushing a filter
        # before a join or aggregation
        
        # Check if the plan has both a scan and a filter
        scan_index = next((i for i, step in enumerate(plan.steps) 
                           if step.operation in ["full_scan", "index_scan"]), -1)
        filter_index = next((i for i, step in enumerate(plan.steps) 
                            if step.operation == "filter"), -1)
        
        # If no scan or filter, or filter is already before other operations, return as is
        if scan_index == -1 or filter_index == -1 or scan_index + 1 == filter_index:
            return plan
            
        # Check if there are operations between scan and filter that we can push past
        intervening_ops = [step.operation for step in plan.steps[scan_index+1:filter_index]]
        
        # Operations that filter can be pushed before
        pushable_ops = ["sort", "limit"]
        
        # If all intervening operations are pushable, move the filter
        if all(op in pushable_ops for op in intervening_ops):
            # Create a new plan with the filter pushed down
            optimized_plan = ExecutionPlan(plan.query)
            
            # Add the scan first
            optimized_plan.add_step(plan.steps[scan_index])
            
            # Add the filter next
            optimized_plan.add_step(plan.steps[filter_index])
            
            # Add the intervening steps
            for i in range(scan_index + 1, filter_index):
                optimized_plan.add_step(plan.steps[i])
            
            # Add any remaining steps
            for i in range(filter_index + 1, len(plan.steps)):
                optimized_plan.add_step(plan.steps[i])
            
            return optimized_plan
        
        # If we couldn't push the filter, return the original plan
        return plan
    
    def optimize_join_order(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply join order optimization rule.
        
        Determines the best order to join tables based on estimated sizes.
        
        Args:
            plan: The execution plan to optimize
            
        Returns:
            The optimized execution plan
        """
        # Get join steps
        join_steps = [(i, step) for i, step in enumerate(plan.steps) 
                      if step.operation == "join"]
        
        # If there are no joins or only one join, no reordering is needed
        if len(join_steps) <= 1:
            return plan
        
        # For more complex join ordering (beyond this example), you would:
        # 1. Build a join graph
        # 2. Estimate cardinalities for different join orders
        # 3. Use a search algorithm (dynamic programming, greedy) to find the optimal order
        
        # For simplicity in this example, we'll just reorder based on estimated costs
        # This would need to be much more sophisticated in a real system
        
        # Check if we have all the required information to reorder
        for _, step in join_steps:
            if "left_source" not in step.parameters or "right_source" not in step.parameters:
                # Skip optimization if joins are not properly specified
                return plan
        
        # For a real implementation, you would estimate sizes and costs for different orderings
        # and choose the best one
        
        # We'll just return the original plan for now
        return plan
    
    def estimate_costs(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Estimate costs for all steps in the plan.
        
        This updates the estimated output size and memory requirements for each step.
        
        Args:
            plan: The execution plan to update
            
        Returns:
            The updated execution plan
        """
        # Make a copy of the plan
        updated_plan = ExecutionPlan(plan.query)
        for step in plan.steps:
            updated_plan.add_step(step)
        
        # Current estimated size (output from previous step)
        current_size = self._estimate_collection_size()
        
        # Update estimates for each step
        for i, step in enumerate(updated_plan.steps):
            # Update input size based on previous step's output
            step.estimated_input_size = current_size
            
            # Calculate estimated output size based on operation type
            if step.operation == "full_scan":
                # Full scan returns all nodes
                step.estimated_output_size = current_size
                
            elif step.operation == "index_scan":
                # Index scan returns a subset
                index_name = step.parameters.get("index_name")
                criteria = step.parameters.get("criteria", {})
                
                if index_name == "spatial":
                    step.estimated_output_size = self._estimate_spatial_matches(
                        criteria, current_size
                    )
                elif index_name == "temporal":
                    step.estimated_output_size = self._estimate_temporal_matches(
                        criteria, current_size
                    )
                elif index_name == "combined":
                    spatial_criteria = criteria.get("spatial", {})
                    temporal_criteria = criteria.get("temporal", {})
                    step.estimated_output_size = self._estimate_combined_matches(
                        spatial_criteria, temporal_criteria, current_size
                    )
                else:
                    # Default estimate
                    step.estimated_output_size = current_size // 2
                    
            elif step.operation == "filter":
                # Filter returns a subset
                criteria = step.parameters.get("criteria", {})
                selectivity = self._estimate_filter_selectivity(criteria)
                step.estimated_output_size = int(current_size * selectivity)
                
            elif step.operation == "join":
                # Join can increase or decrease size
                # Estimate based on join selectivity
                left_size = step.parameters.get("left_estimated_size", current_size)
                right_size = step.parameters.get("right_estimated_size", current_size)
                join_selectivity = 0.1  # Default
                
                step.estimated_output_size = int(
                    (left_size * right_size) * join_selectivity
                )
                
            elif step.operation == "sort":
                # Sort doesn't change size
                step.estimated_output_size = current_size
                
            elif step.operation == "limit":
                # Limit caps the size
                limit = step.parameters.get("limit", current_size)
                step.estimated_output_size = min(current_size, limit)
                
            else:
                # Default: assume no change
                step.estimated_output_size = current_size
            
            # Update the memory requirement estimate
            record_size_kb = 1  # Approximate size of each record in KB
            step.estimated_memory = (
                self.cost_model.estimate_memory_cost(step.estimated_output_size, record_size_kb)
            )
            
            # Update current size for the next step
            current_size = step.estimated_output_size
        
        return updated_plan
    
    def apply_result_size_limits(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply limits to result sizes to manage memory usage.
        
        For queries that could produce very large results, this adds
        limits or pagination to keep memory usage under control.
        
        Args:
            plan: The execution plan to update
            
        Returns:
            The updated execution plan
        """
        # Check if the final estimated result size is large
        if len(plan.steps) > 0:
            final_step = plan.steps[-1]
            estimated_results = final_step.estimated_output_size or 0
            
            # If results could be very large, add a limit
            memory_limit_mb = 500  # Example memory limit
            record_size_kb = 1  # Approximate size of each record in KB
            
            max_results = (memory_limit_mb * 1024) // record_size_kb
            
            # If the estimated results exceed our limit and there's no limit already
            has_limit = any(step.operation == "limit" for step in plan.steps)
            
            if estimated_results > max_results and not has_limit:
                # Add a limit step
                plan.add_step(ExecutionStep(
                    operation="limit",
                    parameters={"limit": max_results},
                    estimated_cost=1.0  # Limit operations are cheap
                ))
                
                # Update the estimated output size
                plan.steps[-1].estimated_output_size = max_results
        
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
        
        # Create statistics manager
        stats_file = self.config.get("statistics_file")
        self.statistics = QueryStatistics(stats_file=stats_file)
        
        # Create optimizer with statistics
        self.optimizer = QueryOptimizer(index_manager, self.statistics)
        
        # Create query monitor
        self.monitor = QueryMonitor(self.statistics)
        
        # Create execution strategies
        self.strategies = {
            "index_scan": IndexScanStrategy(),
            "full_scan": FullScanStrategy(),
            "filter": FilterStrategy(),
            "join": JoinStrategy(),
            "sort": SortStrategy(),
            "limit": LimitStrategy()
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
        
        # Generate a query ID
        query_id = str(uuid.uuid4())
        
        # Extract query type
        query_type = query.__class__.__name__
        
        # Extract query details for monitoring
        query_details = {
            "type": query_type,
            "filters": getattr(query, "criteria", {}),
            "options": options
        }
        
        # Check cache if enabled
        if use_cache:
            cache_key = str(query)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                self.stats["cache_hits"] += 1
                return cached_result
            self.stats["cache_misses"] += 1
        
        try:
            # Start monitoring the query
            self.monitor.start_query(query_id, query_type, query_details)
            
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
            
            # End monitoring
            self.monitor.end_query(query_id, result.count())
            
            # Cache result if caching is enabled
            if use_cache:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            # End monitoring with error
            try:
                self.monitor.end_query(query_id, 0)
            except:
                pass
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
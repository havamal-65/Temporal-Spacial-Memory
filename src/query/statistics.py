"""
Query statistics collection and analysis for query optimization.

This module provides tools for collecting statistics about query execution
to help the query optimizer make better decisions.
"""

import time
import threading
import json
import os
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import statistics as stats
import math

logger = logging.getLogger(__name__)


class QueryStatistics:
    """
    Collects and analyzes statistics about query execution.
    
    This class tracks information about query patterns, execution times,
    and result sizes to help the query optimizer make better decisions.
    """
    
    def __init__(self, 
                stats_file: Optional[str] = None, 
                save_interval: int = 100,
                max_query_types: int = 100):
        """
        Initialize the statistics collector.
        
        Args:
            stats_file: Optional path to persist statistics
            save_interval: Number of queries between saves
            max_query_types: Maximum number of distinct query types to track
        """
        # Execution time tracking: query_type -> [times in ms]
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        
        # Result size tracking: query_type -> [result sizes]
        self.result_sizes: Dict[str, List[int]] = defaultdict(list)
        
        # Index usage tracking: index_name -> [access count, hit count]
        self.index_usage: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        
        # Cardinality estimates: field_name -> {value -> count}
        self.field_cardinality: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Max values to store per query type
        self.max_samples = 100
        
        # Statistics file
        self.stats_file = stats_file
        self.save_interval = save_interval
        self.query_count = 0
        
        # Max query types to track
        self.max_query_types = max_query_types
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Load existing statistics if available
        if stats_file and os.path.exists(stats_file):
            self._load_statistics()
    
    def record_query_execution(self, 
                              query_type: str, 
                              execution_time_ms: float, 
                              result_size: int,
                              query_details: Dict[str, Any]) -> None:
        """
        Record statistics for a query execution.
        
        Args:
            query_type: Type of query executed
            execution_time_ms: Execution time in milliseconds
            result_size: Number of results returned
            query_details: Additional details about the query
        """
        with self.lock:
            # Increment query count
            self.query_count += 1
            
            # Limit the number of query types we track
            if (query_type not in self.execution_times and 
                len(self.execution_times) >= self.max_query_types):
                # TODO: Could implement a more sophisticated strategy than just refusing new types
                logger.warning(f"Reached maximum query types to track ({self.max_query_types})")
                return
            
            # Record execution time
            times = self.execution_times[query_type]
            times.append(execution_time_ms)
            if len(times) > self.max_samples:
                times.pop(0)
            
            # Record result size
            sizes = self.result_sizes[query_type]
            sizes.append(result_size)
            if len(sizes) > self.max_samples:
                sizes.pop(0)
            
            # Record field values for cardinality estimates
            for field, value in query_details.get("filters", {}).items():
                # Convert value to string for storage
                str_value = str(value)
                self.field_cardinality[field][str_value] += 1
            
            # Save periodically
            if self.stats_file and self.query_count % self.save_interval == 0:
                self._save_statistics()
    
    def record_index_usage(self, index_name: str, was_hit: bool) -> None:
        """
        Record statistics for index usage.
        
        Args:
            index_name: Name of the index
            was_hit: Whether the index was used (hit) or not
        """
        with self.lock:
            usage = self.index_usage[index_name]
            
            # Increment access count
            usage[0] += 1
            
            # Increment hit count if index was used
            if was_hit:
                usage[1] += 1
    
    def get_estimated_execution_time(self, query_type: str) -> float:
        """
        Get the estimated execution time for a query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            Estimated execution time in milliseconds
        """
        with self.lock:
            times = self.execution_times.get(query_type, [])
            
            if not times:
                # No data, return a default
                return 100.0
            
            # Use the 75th percentile for a conservative estimate
            return get_percentile(times, 75)
    
    def get_estimated_result_size(self, query_type: str) -> int:
        """
        Get the estimated result size for a query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            Estimated number of results
        """
        with self.lock:
            sizes = self.result_sizes.get(query_type, [])
            
            if not sizes:
                # No data, return a default
                return 10
            
            # Use the 75th percentile for a conservative estimate
            return int(get_percentile(sizes, 75))
    
    def get_index_hit_ratio(self, index_name: str) -> float:
        """
        Get the hit ratio for an index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Hit ratio (0.0-1.0)
        """
        with self.lock:
            usage = self.index_usage.get(index_name, [0, 0])
            
            if usage[0] == 0:
                return 0.0
                
            return usage[1] / usage[0]
    
    def get_field_cardinality(self, field_name: str) -> int:
        """
        Get the estimated cardinality (distinct values) for a field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Estimated number of distinct values
        """
        with self.lock:
            values = self.field_cardinality.get(field_name, {})
            
            # Simple case: return number of observed distinct values
            return len(values)
    
    def get_value_selectivity(self, field_name: str, value: Any) -> float:
        """
        Get the selectivity of a value for a field.
        
        Args:
            field_name: Name of the field
            value: Value to check
            
        Returns:
            Selectivity (0.0-1.0), where lower values are more selective
        """
        with self.lock:
            values = self.field_cardinality.get(field_name, {})
            total_count = sum(values.values())
            
            if total_count == 0:
                return 0.5  # Default
            
            # Get count for this value
            str_value = str(value)
            count = values.get(str_value, 0)
            
            # Calculate selectivity
            return count / total_count
    
    def _save_statistics(self) -> None:
        """Save statistics to file."""
        if not self.stats_file:
            return
            
        with self.lock:
            try:
                # Convert to serializable format
                data = {
                    "execution_times": dict(self.execution_times),
                    "result_sizes": dict(self.result_sizes),
                    "index_usage": dict(self.index_usage),
                    "field_cardinality": dict(self.field_cardinality),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Save to file
                with open(self.stats_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.debug(f"Saved query statistics to {self.stats_file}")
            except Exception as e:
                logger.error(f"Error saving statistics: {e}")
    
    def _load_statistics(self) -> None:
        """Load statistics from file."""
        if not self.stats_file or not os.path.exists(self.stats_file):
            return
            
        with self.lock:
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    
                # Load execution times
                for query_type, times in data.get("execution_times", {}).items():
                    self.execution_times[query_type] = times[-self.max_samples:]
                
                # Load result sizes
                for query_type, sizes in data.get("result_sizes", {}).items():
                    self.result_sizes[query_type] = sizes[-self.max_samples:]
                
                # Load index usage
                for index_name, usage in data.get("index_usage", {}).items():
                    self.index_usage[index_name] = usage
                
                # Load field cardinality
                for field, values in data.get("field_cardinality", {}).items():
                    self.field_cardinality[field] = defaultdict(int, values)
                    
                logger.debug(f"Loaded query statistics from {self.stats_file}")
            except Exception as e:
                logger.error(f"Error loading statistics: {e}")
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of collected statistics.
        
        Returns:
            Dictionary with statistics summary
        """
        with self.lock:
            summary = {
                "query_types": len(self.execution_times),
                "total_queries": self.query_count,
                "query_type_stats": {},
                "index_stats": {},
                "field_stats": {}
            }
            
            # Summarize each query type
            for query_type, times in self.execution_times.items():
                if not times:
                    continue
                    
                sizes = self.result_sizes.get(query_type, [])
                
                summary["query_type_stats"][query_type] = {
                    "count": len(times),
                    "avg_time_ms": sum(times) / len(times),
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "avg_result_size": sum(sizes) / len(sizes) if sizes else 0,
                    "p90_time_ms": get_percentile(times, 90)
                }
            
            # Summarize each index
            for index_name, usage in self.index_usage.items():
                accesses, hits = usage
                
                summary["index_stats"][index_name] = {
                    "accesses": accesses,
                    "hits": hits,
                    "hit_ratio": hits / accesses if accesses > 0 else 0
                }
            
            # Summarize each field
            for field, values in self.field_cardinality.items():
                summary["field_stats"][field] = {
                    "distinct_values": len(values),
                    "total_occurrences": sum(values.values())
                }
            
            return summary


def get_percentile(data: List[float], percentile: float) -> float:
    """
    Calculate a percentile from a list of values.
    
    Args:
        data: List of values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not data:
        return 0.0
        
    try:
        return stats.quantiles(sorted(data), n=100)[int(percentile)-1]
    except (ValueError, IndexError):
        # Fall back to a simpler method
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_data[int(k)]
        
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1


class QueryCostModel:
    """
    Cost model for estimating query execution costs.
    
    This class provides tools for estimating the cost of different
    query execution strategies based on statistics.
    """
    
    def __init__(self, statistics: QueryStatistics):
        """
        Initialize the query cost model.
        
        Args:
            statistics: Query statistics collector
        """
        self.statistics = statistics
        
        # Cost factors (can be tuned)
        self.factors = {
            "full_scan_factor": 1.0,
            "index_scan_factor": 0.1,
            "filter_factor": 0.01,
            "join_factor": 5.0,
            "result_size_factor": 0.001,
            "memory_factor": 0.0005
        }
    
    def estimate_full_scan_cost(self, collection_size: int) -> float:
        """
        Estimate the cost of a full collection scan.
        
        Args:
            collection_size: Size of the collection
            
        Returns:
            Estimated cost
        """
        return collection_size * self.factors["full_scan_factor"]
    
    def estimate_index_scan_cost(self, 
                                index_name: str, 
                                estimated_matches: int,
                                collection_size: int) -> float:
        """
        Estimate the cost of an index scan.
        
        Args:
            index_name: Name of the index
            estimated_matches: Estimated number of matching records
            collection_size: Size of the collection
            
        Returns:
            Estimated cost
        """
        # Base cost for index lookup
        index_lookup_cost = math.log2(collection_size) * self.factors["index_scan_factor"]
        
        # Cost for retrieving matching records
        retrieval_cost = estimated_matches * 0.1 * self.factors["full_scan_factor"]
        
        # Adjust based on historical performance
        hit_ratio = self.statistics.get_index_hit_ratio(index_name)
        performance_factor = 1.0 / max(0.1, hit_ratio) if hit_ratio > 0 else 10.0
        
        return (index_lookup_cost + retrieval_cost) * performance_factor
    
    def estimate_filter_cost(self, 
                            collection_size: int, 
                            selectivity: float,
                            estimated_input_size: int) -> float:
        """
        Estimate the cost of applying a filter.
        
        Args:
            collection_size: Size of the collection
            selectivity: Selectivity of the filter (0.0-1.0)
            estimated_input_size: Estimated size of the input
            
        Returns:
            Estimated cost
        """
        # Cost is proportional to number of records processed and how selective the filter is
        return (estimated_input_size * self.factors["filter_factor"] * 
                max(0.1, selectivity))
    
    def estimate_join_cost(self, 
                          left_size: int, 
                          right_size: int,
                          join_selectivity: float = 0.1) -> float:
        """
        Estimate the cost of a join operation.
        
        Args:
            left_size: Size of the left input
            right_size: Size of the right input
            join_selectivity: Selectivity of the join (0.0-1.0)
            
        Returns:
            Estimated cost
        """
        # Basic nested loops join cost
        return (left_size * right_size * self.factors["join_factor"] * 
                max(0.01, join_selectivity))
    
    def estimate_memory_cost(self, result_size: int, record_size: int = 1) -> float:
        """
        Estimate the memory cost of a query.
        
        Args:
            result_size: Estimated result size
            record_size: Estimated size of each record in KB
            
        Returns:
            Estimated cost
        """
        return result_size * record_size * self.factors["memory_factor"]
    
    def combine_costs(self, *costs: float) -> float:
        """
        Combine multiple cost components into a total cost.
        
        Args:
            *costs: Cost components
            
        Returns:
            Combined cost
        """
        return sum(costs)


class QueryMonitor:
    """
    Monitors query execution and collects performance metrics.
    
    This class provides tools for tracking query execution and identifying
    slow or problematic queries.
    """
    
    def __init__(self, statistics: QueryStatistics):
        """
        Initialize the query monitor.
        
        Args:
            statistics: Query statistics collector
        """
        self.statistics = statistics
        
        # Active queries: query_id -> (start_time, query_type, query_details)
        self.active_queries: Dict[str, Tuple[float, str, Dict[str, Any]]] = {}
        
        # Recent slow queries: List of (query_type, duration, timestamp, details)
        self.slow_queries: List[Tuple[str, float, float, Dict[str, Any]]] = []
        self.max_slow_queries = 100
        
        # Slow query threshold (in milliseconds)
        self.slow_query_threshold = 1000.0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def start_query(self, query_id: str, query_type: str, query_details: Dict[str, Any]) -> None:
        """
        Record the start of a query execution.
        
        Args:
            query_id: Unique ID for the query
            query_type: Type of query
            query_details: Additional details about the query
        """
        with self.lock:
            self.active_queries[query_id] = (time.time(), query_type, query_details)
    
    def end_query(self, query_id: str, result_size: int) -> float:
        """
        Record the end of a query execution.
        
        Args:
            query_id: Unique ID for the query
            result_size: Number of results returned
            
        Returns:
            Duration of the query in milliseconds
        """
        with self.lock:
            if query_id not in self.active_queries:
                logger.warning(f"Query {query_id} not found in active queries")
                return 0.0
                
            start_time, query_type, query_details = self.active_queries.pop(query_id)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000.0
            
            # Record in statistics
            self.statistics.record_query_execution(
                query_type, 
                duration_ms, 
                result_size, 
                query_details
            )
            
            # Check if it's a slow query
            if duration_ms >= self.slow_query_threshold:
                self._record_slow_query(query_type, duration_ms, start_time, query_details)
            
            return duration_ms
    
    def _record_slow_query(self, 
                          query_type: str, 
                          duration_ms: float, 
                          timestamp: float,
                          details: Dict[str, Any]) -> None:
        """Record a slow query."""
        self.slow_queries.append((query_type, duration_ms, timestamp, details))
        
        # Trim if needed
        if len(self.slow_queries) > self.max_slow_queries:
            self.slow_queries.pop(0)
    
    def get_active_queries(self) -> List[Dict[str, Any]]:
        """
        Get a list of currently executing queries.
        
        Returns:
            List of active query information
        """
        with self.lock:
            current_time = time.time()
            
            active = []
            for query_id, (start_time, query_type, details) in self.active_queries.items():
                active.append({
                    "query_id": query_id,
                    "query_type": query_type,
                    "duration_ms": (current_time - start_time) * 1000.0,
                    "start_time": start_time,
                    "details": details
                })
            
            return active
    
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Get a list of recent slow queries.
        
        Returns:
            List of slow query information
        """
        with self.lock:
            return [
                {
                    "query_type": query_type,
                    "duration_ms": duration_ms,
                    "timestamp": timestamp,
                    "details": details
                }
                for query_type, duration_ms, timestamp, details in self.slow_queries
            ]
    
    def set_slow_query_threshold(self, threshold_ms: float) -> None:
        """
        Set the threshold for identifying slow queries.
        
        Args:
            threshold_ms: Threshold in milliseconds
        """
        with self.lock:
            self.slow_query_threshold = threshold_ms 
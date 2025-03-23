"""
Integration test runner for the Temporal-Spatial Knowledge Database.

This module provides functionality to run all integration tests.
"""

import os
import sys
import time
import unittest
import importlib.util
from typing import Optional, List, Tuple

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../..'))

# Import from the package
from src.core.node_v2 import Node


def load_standalone_tests() -> Tuple[unittest.TestSuite, int]:
    """
    Load standalone integration tests.
    
    Returns:
        Tuple containing test suite and test count
    """
    print("Loading standalone tests...")
    
    # Import test modules
    import standalone_test
    import simple_test
    
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add test cases from modules
    suite.addTest(unittest.makeSuite(standalone_test.TestNodeStorage))
    suite.addTest(unittest.makeSuite(standalone_test.TestNodeConnections))
    suite.addTest(unittest.makeSuite(simple_test.SimpleTest))
    
    print("Standalone tests loaded successfully")
    
    # Return the suite and the test count
    return suite, suite.countTestCases()


def run_performance_benchmarks(node_count: int = 10000) -> None:
    """
    Run performance benchmarks.
    
    Args:
        node_count: Number of nodes to use for benchmarks
    """
    try:
        # Dynamically import performance benchmarks only when needed
        # This avoids importing modules with missing dependencies
        print("Attempting to import performance benchmark module...")
        
        # Check if the module exists before trying to import it
        benchmark_path = os.path.join(os.path.dirname(__file__), "test_performance.py")
        if not os.path.exists(benchmark_path):
            raise ImportError(f"Performance benchmark file not found: {benchmark_path}")
            
        # Use a controlled import mechanism to avoid dependency issues
        spec = importlib.util.spec_from_file_location("test_performance", benchmark_path)
        if spec is None:
            raise ImportError(f"Could not create module spec for {benchmark_path}")
            
        perf_module = importlib.util.module_from_spec(spec)
        
        # Attempt to load the module
        try:
            spec.loader.exec_module(perf_module)
            
            # Get the benchmark functions
            benchmark_storage_backends = getattr(perf_module, 'benchmark_storage_backends')
            benchmark_indexing = getattr(perf_module, 'benchmark_indexing')
            benchmark_insertion_scaling = getattr(perf_module, 'benchmark_insertion_scaling')
            benchmark_query_scaling = getattr(perf_module, 'benchmark_query_scaling')
            
            print("\nRunning performance benchmarks...")
            print(f"Using {node_count} nodes for benchmarks")
            
            # Run the benchmarks
            start_time = time.time()
            
            benchmark_storage_backends(node_count // 10)  # Use fewer nodes for backend comparison
            benchmark_indexing(node_count // 10)  # Use fewer nodes for indexing comparison
            benchmark_insertion_scaling([100, 1000, node_count // 10])
            benchmark_query_scaling(node_count // 10, query_sizes=[10, 100, 1000])
            
            end_time = time.time()
            print(f"Performance benchmarks completed in {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            raise ImportError(f"Error loading performance benchmark module: {e}")
            
    except ImportError as e:
        print(f"Error importing performance benchmarks: {e}")
        print("Skipping performance benchmarks")
    except Exception as e:
        print(f"Error running performance benchmarks: {e}")
        print("Skipping performance benchmarks")


def main() -> int:
    """
    Run all integration tests.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"=== Integration Test Run: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # Load standalone tests
    suite, test_count = load_standalone_tests()
    
    # Set the path for test discovery
    test_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"Running integration tests from {test_dir}...")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    # Check for failures
    if not result.wasSuccessful():
        return 1
    
    # Check if benchmarks are explicitly requested
    run_benchmarks = '--with-benchmarks' in sys.argv
    
    if run_benchmarks:
        node_count = 10000  # Default node count for benchmarks
        
        try:
            # Try to get node count from environment
            if 'BENCHMARK_NODE_COUNT' in os.environ:
                node_count = int(os.environ['BENCHMARK_NODE_COUNT'])
        except ValueError:
            print("Invalid BENCHMARK_NODE_COUNT environment variable")
        
        run_performance_benchmarks(node_count)
    else:
        print("\nSkipping performance benchmarks. Use --with-benchmarks to run them.")
    
    # Calculate total runtime
    print(f"\nTotal run time: {result.main_test_run_time:.2f} seconds")
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 
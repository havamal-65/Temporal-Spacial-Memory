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

print("Starting integration test runner...")

# Add the parent directory to sys.path to allow imports
print(f"Adding parent directories to sys.path: {os.path.abspath('..')}, {os.path.abspath('../..')}")
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../..'))

# Import from the package
try:
    print("Importing Node from src.core.node_v2...")
    from src.core.node_v2 import Node
    print("Successfully imported Node")
except Exception as e:
    print(f"Error importing Node: {e}")
    sys.exit(1)


def load_standalone_tests() -> unittest.TestSuite:
    """
    Load standalone integration tests.
    
    Returns:
        Test suite containing all standalone tests
    """
    print("Loading standalone tests...")
    
    try:
        # Import test modules (use direct imports to avoid issues)
        print("Importing test modules...")
        from standalone_test import TestNodeStorage, TestNodeConnections
        from simple_test import SimpleTest
        
        # Create a test suite
        suite = unittest.TestSuite()
        
        # Add test cases from modules
        print("Adding test cases to suite...")
        suite.addTest(unittest.makeSuite(TestNodeStorage))
        suite.addTest(unittest.makeSuite(TestNodeConnections))
        suite.addTest(unittest.makeSuite(SimpleTest))
        
        print("Standalone tests loaded successfully")
        
        # Return the suite
        return suite
    except Exception as e:
        print(f"Error loading tests: {e}")
        raise


def run_performance_benchmarks(node_count: int = 10000) -> None:
    """
    Run performance benchmarks.
    
    Args:
        node_count: Number of nodes to use for benchmarks
    """
    try:
        # Dynamically import performance benchmarks only when needed
        print("Attempting to import performance benchmark module...")
        
        # Check if the module exists before trying to import it
        benchmark_path = os.path.join(os.path.dirname(__file__), "test_performance.py")
        print(f"Looking for benchmark file at: {benchmark_path}")
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
    try:
        suite = load_standalone_tests()
        
        # Set the path for test discovery
        test_dir = os.path.abspath(os.path.dirname(__file__))
        print(f"Running integration tests from {test_dir}...")
        
        # Run the tests
        runner = unittest.TextTestRunner(verbosity=2)  # Increased verbosity
        result = runner.run(suite)
        
        # Check for failures
        if not result.wasSuccessful():
            print("Integration tests failed!")
            return 1
        
        # Check if benchmarks are explicitly requested
        run_benchmarks = '--with-benchmarks' in sys.argv
        print(f"Run benchmarks flag: {run_benchmarks}")
        
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
        try:
            print(f"\nTotal run time: {result.timeTaken:.2f} seconds")
        except AttributeError:
            print("\nTotal run time: Not available")
        
        print("All tests passed successfully!")
        
        return 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


print("Calling main function...")
if __name__ == '__main__':
    exit_code = main()
    print(f"Exiting with code: {exit_code}")
    sys.exit(exit_code) 
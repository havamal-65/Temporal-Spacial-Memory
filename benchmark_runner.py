#!/usr/bin/env python3
"""
Benchmark runner for the Temporal-Spatial Memory Database.

This script runs comprehensive benchmarks and generates visual reports.
"""

import os
import sys
import argparse
import traceback
import importlib.util

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Flag to track if any benchmarks are available
ANY_BENCHMARKS_AVAILABLE = False

# Define a function to safely import benchmarks
def safe_import_benchmark(module_name, function_name):
    """Safely import a benchmark module.
    
    Args:
        module_name: The name of the module to import
        function_name: The name of the function to import from the module
        
    Returns:
        Tuple of (function, success_flag)
    """
    try:
        # Check if the file exists
        module_path = os.path.join(os.path.dirname(__file__), f"{module_name}.py")
        if not os.path.exists(module_path):
            module_path = os.path.join(os.path.dirname(__file__), module_name, "__init__.py")
            if not os.path.exists(module_path):
                return None, False
        
        # Try to import the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            return None, False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the function
        if hasattr(module, function_name):
            return getattr(module, function_name), True
        else:
            return None, False
    except Exception as e:
        print(f"Warning: Could not import {module_name}.{function_name}: {e}")
        return None, False

# Import benchmarks
print("Loading benchmarks...")

# Import the simple benchmark for testing - this should always work
run_simple_benchmarks, SIMPLE_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/simple_benchmark", "run_benchmarks")
if SIMPLE_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Simple benchmarks: Available")
else:
    print("  - Simple benchmarks: Not available")
    # Create a fallback simple benchmark
    def run_simple_benchmarks():
        print("Running fallback simple benchmark...")
        print("This is a fallback benchmark that doesn't depend on any project code.")
        print("It only tests if the benchmark runner works.")
        
        # Create benchmark dir
        os.makedirs("benchmark_results/fallback", exist_ok=True)
        
        print("Benchmark complete!")
        print("No results were generated because this is a fallback benchmark.")
    
    SIMPLE_BENCHMARKS_AVAILABLE = True
    print("    Created fallback benchmark")

# Import the database benchmark
run_database_benchmarks, DATABASE_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/database_benchmark", "run_benchmarks")
if DATABASE_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Database benchmarks: Available")
else:
    print("  - Database benchmarks: Not available")

# Import the comprehensive benchmarks
run_full_benchmarks, FULL_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/temporal_benchmarks", "run_benchmarks")
if FULL_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Full benchmarks: Available")
else:
    print("  - Full benchmarks: Not available")

# Import the range query benchmarks
run_range_benchmarks, RANGE_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/range_query_benchmark", "run_benchmarks")
if RANGE_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Range query benchmarks: Available")
else:
    print("  - Range query benchmarks: Not available")

# Import the concurrent operation benchmarks
run_concurrent_benchmarks, CONCURRENT_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/concurrent_benchmark", "run_benchmarks")
if CONCURRENT_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Concurrent operation benchmarks: Available")
else:
    print("  - Concurrent operation benchmarks: Not available")

# Import the memory usage benchmarks
run_memory_benchmarks, MEMORY_BENCHMARKS_AVAILABLE = safe_import_benchmark("benchmarks/memory_benchmark", "run_benchmarks")
if MEMORY_BENCHMARKS_AVAILABLE:
    ANY_BENCHMARKS_AVAILABLE = True
    print("  - Memory usage benchmarks: Available")
else:
    print("  - Memory usage benchmarks: Not available")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run database benchmarks")
    
    parser.add_argument(
        "--output", 
        default="benchmark_results",
        help="Directory to save benchmark results"
    )
    
    parser.add_argument(
        "--data-sizes", 
        nargs="+", 
        type=int, 
        default=[100, 500, 1000, 5000, 10000],
        help="Data sizes to benchmark"
    )
    
    parser.add_argument(
        "--queries-only", 
        action="store_true",
        help="Run only query benchmarks (assumes data is already loaded)"
    )
    
    # Build choices based on available benchmarks
    component_choices = ["simple"]
    default_component = "simple"
    
    if DATABASE_BENCHMARKS_AVAILABLE:
        component_choices.append("database")
        default_component = "database"
    
    if FULL_BENCHMARKS_AVAILABLE:
        component_choices.extend(["temporal", "spatial", "combined", "all"])
    
    if RANGE_BENCHMARKS_AVAILABLE:
        component_choices.append("range")
    
    if CONCURRENT_BENCHMARKS_AVAILABLE:
        component_choices.append("concurrent")
    
    if MEMORY_BENCHMARKS_AVAILABLE:
        component_choices.append("memory")
    
    parser.add_argument(
        "--component", 
        choices=component_choices,
        default=default_component,
        help="Which component to benchmark"
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    
    # Make sure the output directory exists
    os.makedirs(args.output, exist_ok=True)
    
    print(f"=== Temporal-Spatial Database Benchmark Suite ===")
    print(f"Output directory: {args.output}")
    print(f"Data sizes: {args.data_sizes}")
    print(f"Component: {args.component}")
    print(f"Queries only: {args.queries_only}")
    print(f"==============================")
    
    # Run the benchmarks
    print("Starting benchmarks...")
    try:
        if args.component == "simple":
            run_simple_benchmarks()
        elif args.component == "database" and DATABASE_BENCHMARKS_AVAILABLE:
            run_database_benchmarks()
        elif args.component == "range" and RANGE_BENCHMARKS_AVAILABLE:
            run_range_benchmarks()
        elif args.component == "concurrent" and CONCURRENT_BENCHMARKS_AVAILABLE:
            run_concurrent_benchmarks()
        elif args.component == "memory" and MEMORY_BENCHMARKS_AVAILABLE:
            run_memory_benchmarks()
        elif FULL_BENCHMARKS_AVAILABLE and args.component in ["temporal", "spatial", "combined", "all"]:
            run_full_benchmarks()
        else:
            print(f"Requested benchmark '{args.component}' not available. Running simple benchmarks instead.")
            run_simple_benchmarks()
            
        print("Benchmarks complete!")
        print(f"Results saved to {args.output}")
        print("You can view the generated charts to analyze performance.")
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        print("\nDetailed error information:")
        traceback.print_exc()
        sys.exit(1) 
#!/usr/bin/env python3
"""
Benchmark runner for the Temporal-Spatial Memory Database.

This script runs comprehensive benchmarks and generates visual reports.
"""

import os
import sys
import argparse
import traceback

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the simple benchmark first (this should always work)
try:
    from benchmarks.simple_benchmark import run_benchmarks as run_simple_benchmarks
except ImportError as e:
    print(f"Error importing simple benchmark module: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Try to import the comprehensive benchmarks but don't fail if they're not available
FULL_BENCHMARKS_AVAILABLE = False
try:
    from benchmarks.temporal_benchmarks import run_benchmarks as run_full_benchmarks
    FULL_BENCHMARKS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Full benchmarks not available: {e}")
    print("Using simple benchmarks only.")

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
    
    parser.add_argument(
        "--component", 
        choices=["temporal", "spatial", "combined", "all", "simple"],
        default="simple",
        help="Which component to benchmark"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Make sure the output directory exists
    os.makedirs(args.output, exist_ok=True)
    
    print(f"=== Temporal-Spatial Database Benchmark Suite ===")
    print(f"Output directory: {args.output}")
    print(f"Data sizes: {args.data_sizes}")
    print(f"Component: {args.component}")
    print(f"Queries only: {args.queries_only}")
    print(f"==============================")
    
    # Check if the requested component is available
    if args.component != "simple" and not FULL_BENCHMARKS_AVAILABLE:
        print(f"Warning: Requested component '{args.component}' requires full benchmarks, which are not available.")
        print("Falling back to simple benchmarks.")
        args.component = "simple"
    
    # Run the benchmarks
    print("Starting benchmarks...")
    try:
        if args.component == "simple":
            run_simple_benchmarks()
        else:
            run_full_benchmarks()
        print("Benchmarks complete!")
        print(f"Results saved to {args.output}")
        print("You can view the generated charts to analyze performance.")
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        print("\nDetailed error information:")
        traceback.print_exc()
        sys.exit(1) 
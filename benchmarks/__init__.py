"""
Benchmarks package for the Temporal-Spatial Memory Database.

This package contains benchmarking tools and visualization utilities
to evaluate the performance of the database components.
"""

# Only import the simple benchmark by default
from .simple_benchmark import run_benchmarks

# Expose the simple benchmarks
__all__ = ['run_benchmarks']

# The full benchmarks are imported explicitly when needed 
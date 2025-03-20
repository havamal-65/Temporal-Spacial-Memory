# Temporal-Spatial Database Benchmarks

This directory contains benchmarking tools for measuring and visualizing the performance of the Temporal-Spatial Database components.

## Available Benchmarks

The following components can be benchmarked:

1. **Temporal Index** - Measures performance of temporal indexing and querying operations
2. **Spatial Index (RTree)** - Measures performance of spatial indexing and querying operations
3. **Combined Spatio-Temporal Index** - Measures performance of combined queries

## Running Benchmarks

To run all benchmarks:

```bash
python benchmark_runner.py
```

### Command Line Options

- `--output DIR` - Directory to save benchmark results (default: `benchmark_results`)
- `--data-sizes N1 N2 ...` - Data sizes to benchmark (default: `100 500 1000 5000 10000`)
- `--queries-only` - Run only query benchmarks (assumes data is already loaded)
- `--component COMP` - Which component to benchmark (`temporal`, `spatial`, `combined`, or `all`)

Example:

```bash
python benchmark_runner.py --output my_benchmark_results --component spatial
```

## Visualization

The benchmarks automatically generate visualizations in the output directory:

- **Bar charts** comparing different operations
- **Line graphs** showing scaling behavior with data size
- **Dimensionality impact** analysis

## Example Output

After running the benchmarks, you'll find visualization files like:

- `temporal_index_insertion_scaling.png` - Shows how temporal index insertion performance scales with data size
- `temporal_range_query_performance_comparison.png` - Compares performance of different temporal range query spans
- `spatial_nearest_query_performance_comparison.png` - Compares performance of spatial nearest neighbor queries
- `combined_index_query_performance_comparison.png` - Compares combined vs. individual index operations
- `dimensionality_impact.png` - Shows how dimensionality affects performance

## Key Performance Metrics

Each benchmark reports:

- **Min/Max Times** - Minimum and maximum operation times
- **Average (avg)** - Mean operation time
- **Median** - Middle value of operation times
- **95th Percentile (p95)** - 95% of operations complete within this time
- **99th Percentile (p99)** - 99% of operations complete within this time
- **Standard Deviation (stddev)** - Measure of time variance

## Extending Benchmarks

To add new benchmarks:

1. Create a new benchmark class that extends `BenchmarkSuite`
2. Implement the benchmark methods
3. Update the `run_benchmarks()` function to include your new benchmarks 
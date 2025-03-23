"""
Performance benchmark framework for the Temporal-Spatial Memory Database.

This module provides tools for running and visualizing performance benchmarks
to evaluate the database's performance characteristics.
"""

import time
import logging
import json
import os
import re
import statistics
from typing import Dict, List, Any, Callable, Tuple, Optional, Union
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass, field, asdict

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Represents the result of a benchmark run."""
    name: str
    start_time: float
    end_time: float
    duration: float
    iterations: int
    operations_per_second: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkResult':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BenchmarkSuite:
    """A collection of related benchmarks with common setup."""
    name: str
    description: str
    results: List[BenchmarkResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the suite."""
        self.results.append(result)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkSuite':
        """Create from dictionary."""
        results = [BenchmarkResult.from_dict(r) for r in data.pop("results", [])]
        suite = cls(**data)
        suite.results = results
        return suite
    
    def save_to_file(self, filename: str) -> None:
        """Save benchmark suite to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'BenchmarkSuite':
        """Load benchmark suite from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

class BenchmarkRunner:
    """Runs benchmarks and collects results."""
    
    def __init__(self, name: str, description: str = "", metadata: Dict[str, Any] = None):
        """
        Initialize a benchmark runner.
        
        Args:
            name: The name of the benchmark suite
            description: An optional description of the suite
            metadata: Optional metadata about the benchmark environment
        """
        self.suite = BenchmarkSuite(
            name=name,
            description=description,
            metadata=metadata or {}
        )
        
        # Set default metadata
        if "timestamp" not in self.suite.metadata:
            self.suite.metadata["timestamp"] = datetime.now().isoformat()
        if "platform" not in self.suite.metadata:
            import platform
            self.suite.metadata["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "processor": platform.processor()
            }
    
    def run_benchmark(self, 
                    name: str, 
                    func: Callable[[], Any], 
                    setup: Optional[Callable[[], Any]] = None,
                    teardown: Optional[Callable[[Any], None]] = None,
                    iterations: int = 1,
                    warmup_iterations: int = 0,
                    metadata: Dict[str, Any] = None) -> BenchmarkResult:
        """
        Run a benchmark and record its performance.
        
        Args:
            name: The name of the benchmark
            func: The function to benchmark
            setup: Optional setup function to run before each iteration
            teardown: Optional teardown function to run after each iteration
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations (not counted in results)
            metadata: Optional metadata about the benchmark
            
        Returns:
            The benchmark result
        """
        logger.info(f"Running benchmark: {name}")
        
        # Run warmup iterations
        if warmup_iterations > 0:
            logger.info(f"Running {warmup_iterations} warmup iterations...")
            for _ in range(warmup_iterations):
                setup_data = setup() if setup else None
                func()
                if teardown:
                    teardown(setup_data)
        
        # Prepare for timed iterations
        durations = []
        
        # Record start time
        start_time = time.time()
        
        # Run iterations
        for i in range(iterations):
            logger.debug(f"Iteration {i+1}/{iterations}")
            
            # Run setup if provided
            setup_data = setup() if setup else None
            
            # Time the function execution
            iter_start = time.time()
            func()
            iter_end = time.time()
            
            # Run teardown if provided
            if teardown:
                teardown(setup_data)
            
            # Record duration
            durations.append(iter_end - iter_start)
        
        # Record end time
        end_time = time.time()
        
        # Calculate statistics
        total_duration = end_time - start_time
        avg_duration = statistics.mean(durations)
        operations_per_second = iterations / total_duration
        
        # Create result
        result = BenchmarkResult(
            name=name,
            start_time=start_time,
            end_time=end_time,
            duration=total_duration,
            iterations=iterations,
            operations_per_second=operations_per_second,
            metadata=metadata or {}
        )
        
        # Add additional statistics
        result.metadata["avg_iteration_duration"] = avg_duration
        result.metadata["min_iteration_duration"] = min(durations)
        result.metadata["max_iteration_duration"] = max(durations)
        result.metadata["std_dev_duration"] = statistics.stdev(durations) if len(durations) > 1 else 0
        
        # Add result to suite
        self.suite.add_result(result)
        
        logger.info(f"Benchmark completed: {name}")
        logger.info(f"  Duration: {total_duration:.4f}s")
        logger.info(f"  Iterations: {iterations}")
        logger.info(f"  Ops/sec: {operations_per_second:.2f}")
        
        return result
    
    def save_results(self, filename: str) -> None:
        """
        Save benchmark results to a file.
        
        Args:
            filename: The filename to save to
        """
        self.suite.save_to_file(filename)
        logger.info(f"Saved benchmark results to {filename}")
    
    def generate_report(self, output_dir: str = "benchmark_reports") -> str:
        """
        Generate an HTML report from the benchmark results.
        
        Args:
            output_dir: Directory to save the report
            
        Returns:
            The path to the generated report
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'\W+', '_', self.suite.name).lower()
        filename = f"{safe_name}_{timestamp}.html"
        report_path = os.path.join(output_dir, filename)
        
        # Create performance charts
        chart_path = self._generate_charts(output_dir, timestamp)
        
        # Generate HTML report
        with open(report_path, 'w') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Report: {self.suite.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .benchmark {{ background-color: #fff; padding: 15px; border: 1px solid #ddd; margin-bottom: 15px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Benchmark Report: {self.suite.name}</h1>
        <p>{self.suite.description}</p>
        <p><strong>Date:</strong> {self.suite.metadata.get("timestamp")}</p>
        <p><strong>Platform:</strong> {self.suite.metadata.get("platform", {}).get("system")} {self.suite.metadata.get("platform", {}).get("release")}</p>
    </div>
""")
            
            # Add chart image if available
            if chart_path:
                rel_chart_path = os.path.relpath(chart_path, output_dir)
                f.write(f"""
    <div class="chart">
        <h2>Performance Comparison</h2>
        <img src="{rel_chart_path}" alt="Performance Chart" width="800">
    </div>
""")
            
            # Add summary table
            f.write("""
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Benchmark</th>
            <th>Duration (s)</th>
            <th>Iterations</th>
            <th>Ops/sec</th>
            <th>Min Time (s)</th>
            <th>Max Time (s)</th>
            <th>Avg Time (s)</th>
        </tr>
""")
            
            for result in self.suite.results:
                f.write(f"""
        <tr>
            <td>{result.name}</td>
            <td>{result.duration:.4f}</td>
            <td>{result.iterations}</td>
            <td>{result.operations_per_second:.2f}</td>
            <td>{result.metadata.get("min_iteration_duration", "N/A"):.4f}</td>
            <td>{result.metadata.get("max_iteration_duration", "N/A"):.4f}</td>
            <td>{result.metadata.get("avg_iteration_duration", "N/A"):.4f}</td>
        </tr>
""")
            
            f.write("""
    </table>
""")
            
            # Add detailed results
            f.write("""
    <h2>Detailed Results</h2>
""")
            
            for result in self.suite.results:
                f.write(f"""
    <div class="benchmark">
        <h3>{result.name}</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Start Time</td>
                <td>{datetime.fromtimestamp(result.start_time).isoformat()}</td>
            </tr>
            <tr>
                <td>End Time</td>
                <td>{datetime.fromtimestamp(result.end_time).isoformat()}</td>
            </tr>
            <tr>
                <td>Duration</td>
                <td>{result.duration:.4f} seconds</td>
            </tr>
            <tr>
                <td>Iterations</td>
                <td>{result.iterations}</td>
            </tr>
            <tr>
                <td>Operations per Second</td>
                <td>{result.operations_per_second:.2f}</td>
            </tr>
            <tr>
                <td>Average Iteration Duration</td>
                <td>{result.metadata.get("avg_iteration_duration", "N/A"):.4f} seconds</td>
            </tr>
            <tr>
                <td>Min Iteration Duration</td>
                <td>{result.metadata.get("min_iteration_duration", "N/A"):.4f} seconds</td>
            </tr>
            <tr>
                <td>Max Iteration Duration</td>
                <td>{result.metadata.get("max_iteration_duration", "N/A"):.4f} seconds</td>
            </tr>
            <tr>
                <td>Standard Deviation</td>
                <td>{result.metadata.get("std_dev_duration", "N/A"):.4f} seconds</td>
            </tr>
        </table>
""")
                
                # Add any additional metadata
                other_metadata = {k: v for k, v in result.metadata.items() 
                                if k not in ["avg_iteration_duration", "min_iteration_duration",
                                           "max_iteration_duration", "std_dev_duration"]}
                if other_metadata:
                    f.write("""
        <h4>Additional Metadata</h4>
        <table>
            <tr>
                <th>Key</th>
                <th>Value</th>
            </tr>
""")
                    
                    for key, value in other_metadata.items():
                        f.write(f"""
            <tr>
                <td>{key}</td>
                <td>{value}</td>
            </tr>
""")
                    
                    f.write("""
        </table>
""")
                
                f.write("""
    </div>
""")
            
            f.write("""
</body>
</html>
""")
        
        logger.info(f"Generated benchmark report: {report_path}")
        return report_path
    
    def _generate_charts(self, output_dir: str, timestamp: str) -> Optional[str]:
        """
        Generate charts for the benchmark results.
        
        Args:
            output_dir: Directory to save the charts
            timestamp: Timestamp string for the filename
            
        Returns:
            The path to the chart image, or None if no chart was generated
        """
        if not self.suite.results:
            return None
        
        try:
            # Create bar chart of operations per second
            plt.figure(figsize=(12, 6))
            
            benchmarks = [r.name for r in self.suite.results]
            ops_per_sec = [r.operations_per_second for r in self.suite.results]
            
            # Create bars
            bars = plt.bar(benchmarks, ops_per_sec)
            
            # Add labels and title
            plt.xlabel('Benchmark')
            plt.ylabel('Operations per Second')
            plt.title(f'Performance Comparison: {self.suite.name}')
            
            # Add value labels above bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.2f}', ha='center', va='bottom')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to file
            safe_name = re.sub(r'\W+', '_', self.suite.name).lower()
            chart_path = os.path.join(output_dir, f"{safe_name}_{timestamp}_chart.png")
            plt.savefig(chart_path)
            plt.close()
            
            return chart_path
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            return None

class BenchmarkComparer:
    """Compares results from multiple benchmark runs."""
    
    def __init__(self):
        """Initialize a benchmark comparer."""
        self.suites: List[BenchmarkSuite] = []
    
    def add_suite(self, suite: BenchmarkSuite) -> None:
        """
        Add a benchmark suite for comparison.
        
        Args:
            suite: The benchmark suite to add
        """
        self.suites.append(suite)
    
    def load_suite_from_file(self, filename: str) -> None:
        """
        Load a benchmark suite from a file.
        
        Args:
            filename: The filename to load from
        """
        suite = BenchmarkSuite.load_from_file(filename)
        self.suites.append(suite)
        logger.info(f"Loaded benchmark suite '{suite.name}' from {filename}")
    
    def compare(self, output_file: str = None) -> Dict[str, Any]:
        """
        Compare benchmark results across suites.
        
        Args:
            output_file: Optional file to save comparison results
            
        Returns:
            Dictionary of comparison results
        """
        if not self.suites:
            return {}
        
        # Group by benchmark name
        benchmarks = {}
        
        for suite in self.suites:
            suite_name = suite.name
            for result in suite.results:
                bench_name = result.name
                if bench_name not in benchmarks:
                    benchmarks[bench_name] = []
                
                benchmarks[bench_name].append({
                    "suite": suite_name,
                    "ops_per_sec": result.operations_per_second,
                    "duration": result.duration,
                    "iterations": result.iterations,
                    "timestamp": suite.metadata.get("timestamp", "unknown")
                })
        
        # Create comparison report
        comparison = {
            "suites": [s.name for s in self.suites],
            "benchmarks": {},
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "suite_count": len(self.suites)
            }
        }
        
        # Analyze each benchmark
        for bench_name, results in benchmarks.items():
            # Get ops_per_sec data
            ops_data = [r["ops_per_sec"] for r in results]
            
            # Calculate statistics
            comparison["benchmarks"][bench_name] = {
                "results": results,
                "summary": {
                    "min_ops_per_sec": min(ops_data),
                    "max_ops_per_sec": max(ops_data),
                    "avg_ops_per_sec": statistics.mean(ops_data),
                    "std_dev_ops_per_sec": statistics.stdev(ops_data) if len(ops_data) > 1 else 0,
                    "range_pct": (max(ops_data) - min(ops_data)) / min(ops_data) * 100 if min(ops_data) > 0 else 0
                }
            }
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(comparison, f, indent=2)
            logger.info(f"Saved comparison results to {output_file}")
        
        return comparison
    
    def generate_comparison_report(self, output_dir: str = "benchmark_reports") -> str:
        """
        Generate an HTML comparison report.
        
        Args:
            output_dir: Directory to save the report
            
        Returns:
            The path to the generated report
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate comparison data
        comparison = self.compare()
        
        if not comparison:
            logger.warning("No data available for comparison report")
            return ""
        
        # Generate report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_comparison_{timestamp}.html"
        report_path = os.path.join(output_dir, filename)
        
        # Create performance charts
        chart_paths = self._generate_comparison_charts(comparison, output_dir, timestamp)
        
        # Generate HTML report
        with open(report_path, 'w') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .benchmark {{ background-color: #fff; padding: 15px; border: 1px solid #ddd; margin-bottom: 15px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Benchmark Comparison Report</h1>
        <p><strong>Date:</strong> {datetime.now().isoformat()}</p>
        <p><strong>Suites:</strong> {", ".join(comparison["suites"])}</p>
    </div>
""")
            
            # Add chart images if available
            for chart_path in chart_paths:
                rel_chart_path = os.path.relpath(chart_path, output_dir)
                chart_name = os.path.basename(chart_path).split('_')[0].capitalize()
                f.write(f"""
    <div class="chart">
        <h2>{chart_name} Comparison</h2>
        <img src="{rel_chart_path}" alt="{chart_name} Chart" width="800">
    </div>
""")
            
            # Add summary table
            f.write("""
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Benchmark</th>
            <th>Min Ops/sec</th>
            <th>Max Ops/sec</th>
            <th>Avg Ops/sec</th>
            <th>Std Dev</th>
            <th>Range %</th>
        </tr>
""")
            
            for bench_name, data in comparison["benchmarks"].items():
                summary = data["summary"]
                f.write(f"""
        <tr>
            <td>{bench_name}</td>
            <td>{summary["min_ops_per_sec"]:.2f}</td>
            <td>{summary["max_ops_per_sec"]:.2f}</td>
            <td>{summary["avg_ops_per_sec"]:.2f}</td>
            <td>{summary["std_dev_ops_per_sec"]:.2f}</td>
            <td>{summary["range_pct"]:.2f}%</td>
        </tr>
""")
            
            f.write("""
    </table>
""")
            
            # Add detailed results
            f.write("""
    <h2>Detailed Results</h2>
""")
            
            for bench_name, data in comparison["benchmarks"].items():
                f.write(f"""
    <div class="benchmark">
        <h3>{bench_name}</h3>
        <table>
            <tr>
                <th>Suite</th>
                <th>Timestamp</th>
                <th>Ops/sec</th>
                <th>Duration (s)</th>
                <th>Iterations</th>
            </tr>
""")
                
                for result in data["results"]:
                    f.write(f"""
            <tr>
                <td>{result["suite"]}</td>
                <td>{result["timestamp"]}</td>
                <td>{result["ops_per_sec"]:.2f}</td>
                <td>{result["duration"]:.4f}</td>
                <td>{result["iterations"]}</td>
            </tr>
""")
                
                f.write("""
        </table>
    </div>
""")
            
            f.write("""
</body>
</html>
""")
        
        logger.info(f"Generated comparison report: {report_path}")
        return report_path
    
    def _generate_comparison_charts(self, comparison: Dict[str, Any], output_dir: str, timestamp: str) -> List[str]:
        """
        Generate charts for comparing benchmark results.
        
        Args:
            comparison: The comparison data
            output_dir: Directory to save the charts
            timestamp: Timestamp string for the filename
            
        Returns:
            List of paths to the generated charts
        """
        if not comparison or not comparison.get("benchmarks"):
            return []
        
        chart_paths = []
        
        try:
            # Create a bar chart comparing ops/sec across suites for each benchmark
            plt.figure(figsize=(12, 8))
            
            # Get data
            bench_names = list(comparison["benchmarks"].keys())
            suite_names = comparison["suites"]
            
            # Prepare data structure: benchmark -> suite -> ops_per_sec
            data = {}
            for bench_name, bench_data in comparison["benchmarks"].items():
                data[bench_name] = {r["suite"]: r["ops_per_sec"] for r in bench_data["results"]}
            
            # Bar width and positions
            bar_width = 0.8 / len(suite_names)
            indices = np.arange(len(bench_names))
            
            # Plot bars for each suite
            for i, suite_name in enumerate(suite_names):
                values = [data.get(bench, {}).get(suite_name, 0) for bench in bench_names]
                offset = (i - len(suite_names) / 2 + 0.5) * bar_width
                bars = plt.bar(indices + offset, values, bar_width, label=suite_name)
                
                # Add values on top of bars
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                               f'{height:.1f}', ha='center', va='bottom', fontsize=8)
            
            # Add labels and legend
            plt.xlabel('Benchmark')
            plt.ylabel('Operations per Second')
            plt.title('Performance Comparison Across Suites')
            plt.xticks(indices, bench_names, rotation=45, ha='right')
            plt.legend()
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to file
            chart_path = os.path.join(output_dir, f"performance_{timestamp}_chart.png")
            plt.savefig(chart_path)
            plt.close()
            
            chart_paths.append(chart_path)
            
            # Create another chart showing relative performance
            plt.figure(figsize=(12, 8))
            
            # Use first suite as baseline
            baseline_suite = suite_names[0] if suite_names else None
            
            if baseline_suite:
                # Calculate relative performance
                relative_data = {}
                for bench_name, bench_data in data.items():
                    baseline = bench_data.get(baseline_suite, 1)  # Avoid division by zero
                    if baseline == 0:
                        baseline = 1
                    relative_data[bench_name] = {
                        suite: (ops / baseline) * 100 - 100  # Percentage difference from baseline
                        for suite, ops in bench_data.items()
                        if suite != baseline_suite  # Skip baseline
                    }
                
                # Plot bars for each non-baseline suite
                for i, suite_name in enumerate(suite_names):
                    if suite_name == baseline_suite:
                        continue
                    
                    values = [relative_data.get(bench, {}).get(suite_name, 0) for bench in bench_names]
                    offset = (i - len(suite_names) / 2 + 0.5) * bar_width
                    bars = plt.bar(indices + offset, values, bar_width, label=f"{suite_name} vs {baseline_suite}")
                    
                    # Add values on top of bars
                    for bar in bars:
                        height = bar.get_height()
                        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1 if height >= 0 else height - 0.1,
                               f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
                
                # Add labels and legend
                plt.xlabel('Benchmark')
                plt.ylabel('Performance Difference (%)')
                plt.title(f'Relative Performance Compared to {baseline_suite}')
                plt.xticks(indices, bench_names, rotation=45, ha='right')
                plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
                plt.legend()
                
                # Adjust layout
                plt.tight_layout()
                
                # Save to file
                chart_path = os.path.join(output_dir, f"relative_{timestamp}_chart.png")
                plt.savefig(chart_path)
                plt.close()
                
                chart_paths.append(chart_path)
            
            return chart_paths
        except Exception as e:
            logger.error(f"Error generating comparison charts: {e}")
            return chart_paths

# Main example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a benchmark runner
    runner = BenchmarkRunner(
        name="Example Benchmark Suite",
        description="Example benchmark suite to demonstrate the framework"
    )
    
    # Define a simple benchmark function
    def bench_func():
        # Simulate some work
        result = 0
        for i in range(1000000):
            result += i
        return result
    
    # Run a benchmark
    runner.run_benchmark(
        name="Simple Computation",
        func=bench_func,
        iterations=5,
        warmup_iterations=2
    )
    
    # Save results
    runner.save_results("example_benchmark_results.json")
    
    # Generate report
    report_path = runner.generate_report()
    print(f"Report generated: {report_path}") 
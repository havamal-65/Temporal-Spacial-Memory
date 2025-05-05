"""
Test Runner for Temporal-Spatial Memory System.

This script runs all test suites and generates a consolidated report.
"""

import os
import sys
import argparse
import time
import json
import unittest
import logging
from datetime import datetime
from pathlib import Path
import importlib
import matplotlib.pyplot as plt
import numpy as np

# Add src directory to path to allow importing atlas components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("TestRunner")


def run_unit_tests(output_dir: str) -> bool:
    """
    Run all unit tests.
    
    Args:
        output_dir: Directory to save test results
        
    Returns:
        True if all tests passed, False otherwise
    """
    logger.info("Running unit tests")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    
    # Create result output file
    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, "unit_test_results.txt")
    
    # Run tests with text output
    with open(result_path, 'w') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)
    
    # Log summary
    logger.info(f"Unit tests: {result.testsRun} tests run, {len(result.errors)} errors, {len(result.failures)} failures")
    logger.info(f"Results saved to {result_path}")
    
    # Return success/failure
    return len(result.errors) == 0 and len(result.failures) == 0


def run_regression_tests(output_dir: str) -> bool:
    """
    Run regression tests.
    
    Args:
        output_dir: Directory to save test results
        
    Returns:
        True if all tests passed, False otherwise
    """
    logger.info("Running regression tests")
    
    # Import regression test module
    try:
        regression_module = importlib.import_module("regression_test")
    except ImportError:
        logger.error("Could not import regression_test module")
        return False
    
    # Create result output file
    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, "regression_test_results.txt")
    
    # Redirect stdout to capture results
    original_stdout = sys.stdout
    with open(result_path, 'w') as f:
        sys.stdout = f
        
        # Run regression tests
        try:
            success = regression_module.run_regression_tests()
        finally:
            # Restore stdout
            sys.stdout = original_stdout
    
    # Log summary
    logger.info(f"Regression tests: {'passed' if success else 'failed'}")
    logger.info(f"Results saved to {result_path}")
    
    return success


def run_comparison_tests(output_dir: str) -> dict:
    """
    Run comparison tests.
    
    Args:
        output_dir: Directory to save test results
        
    Returns:
        Dictionary with comparison test results
    """
    logger.info("Running comparison tests")
    
    # Import comparison test module
    try:
        comparison_module = importlib.import_module("comparison_test")
    except ImportError:
        logger.error("Could not import comparison_test module")
        return {}
    
    # Create comparison tests output directory
    comparison_output_dir = os.path.join(output_dir, "comparison_tests")
    os.makedirs(comparison_output_dir, exist_ok=True)
    
    # Run comparison tests
    try:
        # Run with smaller test set for quicker execution
        result = comparison_module.run_comparative_tests(
            output_dir=comparison_output_dir,
            num_test_nodes=50
        )
        
        # Extract basic metrics
        metrics = {}
        if hasattr(result, 'metrics'):
            metrics = result.metrics
        elif hasattr(result, 'to_dict'):
            metrics = result.to_dict().get('metrics', {})
        
        # Log summary
        logger.info(f"Comparison tests completed, results saved to {comparison_output_dir}")
        
        return metrics
    except Exception as e:
        logger.error(f"Error running comparison tests: {e}")
        return {}


def run_performance_tests(output_dir: str) -> dict:
    """
    Run performance tests.
    
    Args:
        output_dir: Directory to save test results
        
    Returns:
        Dictionary with performance test results
    """
    logger.info("Running performance tests")
    
    # Import performance optimization module
    try:
        performance_module = importlib.import_module("performance_optimization")
    except ImportError:
        logger.error("Could not import performance_optimization module")
        return {}
    
    # Create performance tests output directory
    performance_output_dir = os.path.join(output_dir, "performance_tests")
    os.makedirs(performance_output_dir, exist_ok=True)
    
    # Run performance tests
    try:
        results = performance_module.run_optimization_analysis(
            output_dir=performance_output_dir
        )
        
        # Log summary
        logger.info(f"Performance tests completed, results saved to {performance_output_dir}")
        
        return results
    except Exception as e:
        logger.error(f"Error running performance tests: {e}")
        return {}


def generate_report(
    output_dir: str,
    unit_test_success: bool,
    regression_test_success: bool,
    comparison_results: dict,
    performance_results: dict
) -> str:
    """
    Generate a consolidated test report.
    
    Args:
        output_dir: Directory to save test results
        unit_test_success: Whether unit tests passed
        regression_test_success: Whether regression tests passed
        comparison_results: Results from comparison tests
        performance_results: Results from performance tests
        
    Returns:
        Path to the generated report
    """
    logger.info("Generating consolidated test report")
    
    # Create report output directory
    report_dir = os.path.join(output_dir, "report")
    os.makedirs(report_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create report data
    report = {
        "timestamp": timestamp,
        "tests": {
            "unit_tests": {
                "success": unit_test_success,
                "details": "See unit_test_results.txt for details"
            },
            "regression_tests": {
                "success": regression_test_success,
                "details": "See regression_test_results.txt for details"
            },
            "comparison_tests": comparison_results,
            "performance_tests": performance_results
        }
    }
    
    # Save report data
    report_path = os.path.join(report_dir, "test_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Generate HTML report
    html_report_path = os.path.join(report_dir, "test_report.html")
    generate_html_report(report, html_report_path)
    
    # Generate visualizations
    generate_report_visualizations(report, report_dir)
    
    logger.info(f"Report generated at {html_report_path}")
    return html_report_path


def generate_html_report(report: dict, output_path: str):
    """Generate HTML report from test results."""
    # Simple HTML report template
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Temporal-Spatial Memory Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .section {{ margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Temporal-Spatial Memory Test Report</h1>
    <p>Generated: {report["timestamp"]}</p>
    
    <div class="section">
        <h2>Test Results Summary</h2>
        <table>
            <tr>
                <th>Test Suite</th>
                <th>Result</th>
            </tr>
            <tr>
                <td>Unit Tests</td>
                <td class="{'success' if report['tests']['unit_tests']['success'] else 'failure'}">
                    {'Passed' if report['tests']['unit_tests']['success'] else 'Failed'}
                </td>
            </tr>
            <tr>
                <td>Regression Tests</td>
                <td class="{'success' if report['tests']['regression_tests']['success'] else 'failure'}">
                    {'Passed' if report['tests']['regression_tests']['success'] else 'Failed'}
                </td>
            </tr>
        </table>
    </div>
    """
    
    # Add comparison test results if available
    if report['tests'].get('comparison_tests'):
        comparison = report['tests']['comparison_tests']
        html_content += f"""
    <div class="section">
        <h2>Comparison Test Results</h2>
        <p>Standard vs. Polar-Temporal Coordinates</p>
        <img src="comparison_chart.png" alt="Comparison Chart" class="chart">
    </div>
    """
    
    # Add performance test results if available
    if report['tests'].get('performance_tests'):
        performance = report['tests']['performance_tests']
        metrics = performance.get('metrics', {})
        bottlenecks = performance.get('bottlenecks', [])
        
        html_content += f"""
    <div class="section">
        <h2>Performance Test Results</h2>
        <h3>Key Metrics</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
    """
        
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                html_content += f"""
            <tr>
                <td>{key}</td>
                <td>{value:.4f if isinstance(value, float) else value}</td>
            </tr>
                """
        
        html_content += """
        </table>
        
        <h3>Identified Bottlenecks</h3>
        <table>
            <tr>
                <th>Issue</th>
                <th>Metric</th>
                <th>Recommendation</th>
            </tr>
        """
        
        for bottleneck in bottlenecks:
            html_content += f"""
            <tr>
                <td>{bottleneck.get('issue', '')}</td>
                <td>{bottleneck.get('metric', '')}</td>
                <td>{bottleneck.get('recommendation', '')}</td>
            </tr>
            """
        
        html_content += """
        </table>
        <img src="performance_chart.png" alt="Performance Chart" class="chart">
    </div>
        """
    
    # Close HTML document
    html_content += """
</body>
</html>
    """
    
    # Write HTML to file
    with open(output_path, 'w') as f:
        f.write(html_content)


def generate_report_visualizations(report: dict, output_dir: str):
    """Generate visualizations for the report."""
    # Generate comparison chart if comparison results are available
    if report['tests'].get('comparison_tests'):
        try:
            create_comparison_chart(report['tests']['comparison_tests'], os.path.join(output_dir, "comparison_chart.png"))
        except Exception as e:
            logger.error(f"Error creating comparison chart: {e}")
    
    # Generate performance chart if performance results are available
    if report['tests'].get('performance_tests') and report['tests']['performance_tests'].get('metrics'):
        try:
            create_performance_chart(report['tests']['performance_tests'], os.path.join(output_dir, "performance_chart.png"))
        except Exception as e:
            logger.error(f"Error creating performance chart: {e}")


def create_comparison_chart(comparison_results: dict, output_path: str):
    """Create a visualization of comparison test results."""
    # Extract metrics based on available data format
    metrics = {}
    if isinstance(comparison_results, dict):
        metrics = comparison_results.get('metrics', {})
    
    # Check if we have any timing/accuracy data to plot
    has_timing_data = False
    has_accuracy_data = False
    
    standard_times = []
    polar_times = []
    k_values = []
    
    standard_precision = []
    polar_precision = []
    
    # Look for timing and precision metrics in various formats
    for key in metrics:
        if 'standard_avg_query_time' in key and 'k' in key:
            k = key.split('k')[-1]
            k_values.append(k)
            standard_times.append(metrics[key])
            polar_times.append(metrics.get(f'polar_avg_query_time_k{k}', 0))
            has_timing_data = True
        
        elif 'standard_precision_k' in key:
            k = key.split('k')[-1]
            standard_precision.append(metrics[key])
            polar_precision.append(metrics.get(f'polar_precision_k{k}', 0))
            has_accuracy_data = True
    
    # Create figure with subplots
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot timing data if available
    if has_timing_data:
        axs[0].bar([i-0.2 for i in range(len(k_values))], standard_times, width=0.4, label='Standard')
        axs[0].bar([i+0.2 for i in range(len(k_values))], polar_times, width=0.4, label='Polar')
        axs[0].set_xlabel('k Value')
        axs[0].set_ylabel('Query Time (s)')
        axs[0].set_title('Query Performance Comparison')
        axs[0].set_xticks(range(len(k_values)))
        axs[0].set_xticklabels(k_values)
        axs[0].legend()
    
    # Plot accuracy data if available
    if has_accuracy_data:
        axs[1].bar([i-0.2 for i in range(len(k_values))], standard_precision, width=0.4, label='Standard')
        axs[1].bar([i+0.2 for i in range(len(k_values))], polar_precision, width=0.4, label='Polar')
        axs[1].set_xlabel('k Value')
        axs[1].set_ylabel('Precision')
        axs[1].set_title('Retrieval Accuracy Comparison')
        axs[1].set_xticks(range(len(k_values)))
        axs[1].set_xticklabels(k_values)
        axs[1].legend()
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def create_performance_chart(performance_results: dict, output_path: str):
    """Create a visualization of performance test results."""
    metrics = performance_results.get('metrics', {})
    
    # Select relevant metrics to plot
    selected_metrics = [
        ('nodes_per_second', 'Nodes/s'),
        ('avg_standard_query_time', 'Query Time (s)'),
        ('memory_per_node_kb', 'Memory/Node (KB)')
    ]
    
    # Filter to metrics that exist
    available_metrics = [(key, label) for key, label in selected_metrics if key in metrics]
    
    if not available_metrics:
        logger.warning("No metrics available for performance chart")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create bar positions
    positions = range(len(available_metrics))
    
    # Create bars with metric values
    bars = ax.bar(positions, [metrics[key] for key, _ in available_metrics])
    
    # Set labels
    ax.set_xticks(positions)
    ax.set_xticklabels([label for _, label in available_metrics])
    ax.set_title("Performance Metrics")
    
    # Add value labels on top of bars
    for i, bar in enumerate(bars):
        key, _ = available_metrics[i]
        value = metrics[key]
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (bar.get_height() * 0.05),
            f"{value:.2f}",
            ha='center',
            va='bottom'
        )
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def run_all_tests(output_dir: str = "output/tests") -> bool:
    """
    Run all test suites and generate report.
    
    Args:
        output_dir: Directory to save test results
        
    Returns:
        True if all required tests passed, False otherwise
    """
    logger.info(f"Running all tests, results will be saved to {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Run unit tests
    unit_success = run_unit_tests(output_dir)
    
    # Run regression tests
    regression_success = run_regression_tests(output_dir)
    
    # Run comparison tests
    comparison_results = run_comparison_tests(output_dir)
    
    # Run performance tests
    performance_results = run_performance_tests(output_dir)
    
    # Generate report
    report_path = generate_report(
        output_dir,
        unit_success,
        regression_success,
        comparison_results,
        performance_results
    )
    
    # Open report in browser if running in interactive mode
    if sys.stdout.isatty():
        try:
            import webbrowser
            webbrowser.open('file://' + os.path.abspath(report_path))
        except Exception:
            pass
    
    # Return overall success/failure (based on required tests)
    required_success = unit_success and regression_success
    
    logger.info(f"All tests completed. Overall result: {'Passed' if required_success else 'Failed'}")
    logger.info(f"Full report available at {report_path}")
    
    return required_success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all test suites for Temporal-Spatial Memory System")
    parser.add_argument("--output-dir", type=str, default="output/tests", 
                     help="Directory to save test results")
    
    args = parser.parse_args()
    
    success = run_all_tests(output_dir=args.output_dir)
    
    # Use exit code based on test results
    sys.exit(0 if success else 1) 
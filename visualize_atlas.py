"""
Visualization runner for Temporal-Spatial Memory System.

This script provides an easy way to run the visualization tools on an existing atlas.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import local modules
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service
from src.visualization.coordinate_visualizer import CoordinateVisualizer
from src.visualization.dashboard import Dashboard
from src.visualization.exporters import NetworkExporter, HeatmapExporter
from src.visualization.analytics import ClusterAnalyzer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Visualize")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Visualize a Temporal-Spatial Memory Atlas')
    
    parser.add_argument('--atlas-path', type=str, required=True,
                       help='Path to the Narrative Atlas storage directory')
    
    parser.add_argument('--output-dir', type=str, default='output/visualizations',
                       help='Directory to save visualization outputs')
    
    parser.add_argument('--embedding-service', type=str, default='langchain',
                       choices=['mock', 'langchain', 'cascading'],
                       help='Embedding service used by the Atlas')
    
    # Visualization type
    parser.add_argument('--type', type=str, default='dashboard',
                       choices=['dashboard', 'static', 'network', 'heatmap', 'analysis', 'all'],
                       help='Type of visualization to generate')
    
    # Dashboard options
    parser.add_argument('--port', type=int, default=8050,
                       help='Port to run the dashboard server on')
    
    parser.add_argument('--debug', action='store_true',
                       help='Run dashboard in debug mode')
    
    # Static visualization options
    parser.add_argument('--color-by', type=str, default='type',
                       choices=['type', 't', 'r', 'theta', 'z'],
                       help='Node attribute to use for coloring')
    
    parser.add_argument('--view', type=str, default='all',
                       choices=['polar', 'temporal', '3d', 'heatmap', 'all'],
                       help='Type of static visualization to generate')
    
    # Network export options
    parser.add_argument('--network-formats', type=str, nargs='+', 
                       default=['gephi', 'cytoscape', 'd3'],
                       choices=['gephi', 'cytoscape', 'd3'],
                       help='Network export formats')
    
    parser.add_argument('--link-type', type=str, default='combined',
                       choices=['similarity', 'temporal', 'combined'],
                       help='Type of links to create between nodes')
    
    # Analysis options
    parser.add_argument('--cluster-algorithm', type=str, default='kmeans',
                       choices=['kmeans', 'dbscan', 'hierarchical'],
                       help='Clustering algorithm to use for analysis')
    
    parser.add_argument('--n-clusters', type=int, default=None,
                       help='Number of clusters (auto-detected if not specified)')
    
    return parser.parse_args()


def load_atlas(atlas_path, embedding_service_type):
    """Load a NarrativeAtlas from disk."""
    logger.info(f"Loading atlas from {atlas_path}")
    
    # Create embedding service
    embedding_service = create_embedding_service(service_type=embedding_service_type)
    
    # Load atlas
    atlas = NarrativeAtlas(storage_path=atlas_path, embedding_service=embedding_service)
    
    # Check if atlas has nodes
    if not atlas.db.nodes:
        logger.error(f"No nodes found in atlas at {atlas_path}")
        sys.exit(1)
    
    logger.info(f"Loaded atlas with {len(atlas.db.nodes)} nodes")
    return atlas


def run_dashboard(atlas, port=8050, debug=False, output_dir='output/visualizations'):
    """Run the interactive dashboard."""
    logger.info(f"Starting dashboard on port {port}")
    dashboard = Dashboard(
        narrative_atlas=atlas,
        port=port,
        debug=debug
    )
    # Open browser and run server
    dashboard.run(open_browser=True)


def generate_static_visualizations(atlas, view_type='all', color_by='type', output_dir='output/visualizations'):
    """Generate static visualizations."""
    logger.info(f"Generating static {view_type} visualizations")
    visualizer = CoordinateVisualizer(output_dir=output_dir, interactive=True)
    visualizations = visualizer.visualize_atlas(
        atlas=atlas,
        view_type=view_type,
        color_by=color_by
    )
    
    # Generate a static HTML report
    report_path = os.path.join(output_dir, "atlas_report.html")
    logger.info(f"Generating static HTML report at {report_path}")
    
    # Create dashboard just for the report generation
    dashboard = Dashboard(
        narrative_atlas=atlas,
        port=0,  # Don't actually run the server
        debug=False
    )
    report_path = dashboard.generate_static_report(report_path)
    
    logger.info(f"Generated static report at {report_path}")
    return report_path


def export_network(atlas, formats, link_type, output_dir='output/network_exports'):
    """Export atlas network for visualization in other tools."""
    logger.info(f"Exporting network in {formats} formats with {link_type} links")
    exporter = NetworkExporter(output_dir=output_dir)
    exports = exporter.export_atlas_network(
        atlas=atlas,
        formats=formats,
        link_type=link_type
    )
    
    logger.info(f"Exported {len(exports)} network files:")
    for fmt, path in exports.items():
        logger.info(f"  {fmt}: {path}")
    
    return exports


def export_heatmaps(atlas, output_dir='output/heatmap_exports'):
    """Export heatmaps for the atlas."""
    logger.info("Exporting heatmaps")
    exporter = HeatmapExporter(output_dir=output_dir)
    exports = exporter.export_atlas_heatmaps(
        atlas=atlas,
        dimensions_list=[
            ("theta", "t"),
            ("r", "t"),
            ("theta", "r"),
            ("r", "z")
        ],
        formats=["json", "csv"]
    )
    
    logger.info(f"Exported {len(exports)} heatmap files:")
    for key, path in list(exports.items())[:5]:  # Show just the first 5
        logger.info(f"  {key}: {path}")
    if len(exports) > 5:
        logger.info(f"  ... and {len(exports) - 5} more")
    
    return exports


def run_analysis(atlas, algorithm='kmeans', n_clusters=None, output_dir='output/analytics'):
    """Run analysis on the atlas."""
    logger.info(f"Running cluster analysis with {algorithm} algorithm")
    analyzer = ClusterAnalyzer(output_dir=output_dir)
    results = analyzer.analyze_atlas(atlas)
    
    # Save analysis results to JSON
    import json
    from datetime import datetime
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to JSON
    output_path = os.path.join(output_dir, f"analysis_{timestamp}.json")
    
    # We need to make results serializable by replacing numpy arrays, etc.
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(make_serializable(item) for item in obj)
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, OverflowError):
                return str(obj)
    
    serializable_results = make_serializable(results)
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    logger.info(f"Saved analysis results to {output_path}")
    
    # Print summary of analysis
    logger.info("Analysis Summary:")
    logger.info(f"  Node count: {results['node_count']}")
    logger.info(f"  Node types: {', '.join(results['node_types'].keys())}")
    
    if 'clustering' in results and 'n_clusters' in results['clustering']:
        logger.info(f"  Detected {results['clustering']['n_clusters']} clusters")
    
    if 'temporal' in results and 'temporal_clusters' in results['temporal']:
        logger.info(f"  Detected {len(results['temporal']['temporal_clusters'])} temporal clusters")
    
    if 'distribution' in results and 'overall_entropy' in results['distribution']:
        entropy = results['distribution']['overall_entropy']
        logger.info(f"  Information entropy: {entropy['total']:.4f}")
    
    return output_path


def main():
    """Main function."""
    args = parse_args()
    
    # Load atlas
    atlas = load_atlas(args.atlas_path, args.embedding_service)
    
    # Create output directories if they don't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run visualizations based on the requested type
    if args.type == 'dashboard' or args.type == 'all':
        run_dashboard(atlas, args.port, args.debug)
    
    if args.type == 'static' or args.type == 'all':
        report_path = generate_static_visualizations(
            atlas, 
            args.view, 
            args.color_by, 
            os.path.join(args.output_dir, 'static')
        )
        logger.info(f"Static visualizations generated. Report: {report_path}")
    
    if args.type == 'network' or args.type == 'all':
        network_exports = export_network(
            atlas, 
            args.network_formats, 
            args.link_type, 
            os.path.join(args.output_dir, 'network')
        )
    
    if args.type == 'heatmap' or args.type == 'all':
        heatmap_exports = export_heatmaps(
            atlas,
            os.path.join(args.output_dir, 'heatmaps')
        )
    
    if args.type == 'analysis' or args.type == 'all':
        analysis_path = run_analysis(
            atlas,
            args.cluster_algorithm,
            args.n_clusters,
            os.path.join(args.output_dir, 'analytics')
        )
        logger.info(f"Analysis completed. Results saved to: {analysis_path}")
    
    logger.info("Visualization completed successfully.")


if __name__ == '__main__':
    main() 
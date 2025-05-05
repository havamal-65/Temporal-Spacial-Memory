#!/usr/bin/env python3
"""
Query System Integration Example

This script demonstrates the complete integration of the Temporal-Spatial Memory System,
showcasing how to use various query capabilities together for advanced information retrieval.
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import system components
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service
from src.data_models import PolarTemporalCoordinate, Z_TYPES
from src.nl_parser import CoordinateFilters
from src.visualization.coordinate_visualizer import CoordinateVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QuerySystem")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Temporal-Spatial Memory System Query Integration Example"
    )
    
    parser.add_argument("--atlas-path", type=str, required=True,
                        help="Path to the Narrative Atlas storage directory")
    
    parser.add_argument("--query", type=str, default=None,
                        help="Natural language query to execute (if not provided, runs all demos)")
    
    parser.add_argument("--temporal-focus", type=float, default=None,
                        help="Temporal coordinate to focus on (0-based page number plus chunk position)")
    
    parser.add_argument("--decay-rate", type=float, default=0.15,
                        help="Temporal decay rate (higher values = stronger decay)")
    
    parser.add_argument("--directional-bias", type=float, default=None,
                        help="Angular direction bias in radians (0 to 2π)")
    
    parser.add_argument("--directional-strength", type=float, default=0.3,
                        help="Strength of directional bias (0.0 to 1.0)")
    
    parser.add_argument("--r-min", type=float, default=None,
                        help="Minimum radius for filtering")
    
    parser.add_argument("--r-max", type=float, default=None,
                        help="Maximum radius for filtering")
    
    parser.add_argument("--t-min", type=float, default=None,
                        help="Minimum temporal coordinate for filtering")
    
    parser.add_argument("--t-max", type=float, default=None,
                        help="Maximum temporal coordinate for filtering")
    
    parser.add_argument("--k", type=int, default=5,
                        help="Number of results to return")
    
    parser.add_argument("--visualize", action="store_true",
                        help="Generate visualizations of results")
    
    parser.add_argument("--viz-output", type=str, default="output/query_viz",
                        help="Directory for visualization output")
    
    parser.add_argument("--no-demos", action="store_true",
                        help="Skip running demos if no query is provided")
    
    return parser.parse_args()

def load_atlas(atlas_path):
    """Load the Narrative Atlas from the specified path."""
    logger.info(f"Loading Narrative Atlas from {atlas_path}")
    
    # Create embedding service
    embedding_service = create_embedding_service(service_type="langchain")
    
    # Initialize and load atlas
    atlas = NarrativeAtlas(
        storage_path=atlas_path,
        embedding_service=embedding_service
    )
    
    # Verify atlas has loaded successfully
    if not atlas.db.nodes:
        logger.warning(f"Atlas at {atlas_path} contains no nodes. Results may be empty.")
    else:
        logger.info(f"Successfully loaded atlas with {len(atlas.db.nodes)} nodes")
        
        # Log some stats about the atlas
        t_values = [node.coordinates.t for node in atlas.db.nodes.values()]
        t_min, t_max = min(t_values), max(t_values)
        logger.info(f"Temporal range: t_min={t_min:.2f}, t_max={t_max:.2f}")
        
        r_values = [node.coordinates.r for node in atlas.db.nodes.values()]
        r_min, r_max = min(r_values), max(r_values)
        logger.info(f"Radius range: r_min={r_min:.2f}, r_max={r_max:.2f}")
        
        node_types = set(node.type for node in atlas.db.nodes.values())
        logger.info(f"Node types: {', '.join(node_types)}")
    
    return atlas

def run_basic_query(atlas, query_text, k=5):
    """Run a basic semantic search query without coordinate enhancements."""
    logger.info(f"Running basic semantic search: '{query_text}'")
    
    results = atlas.find_similar_nodes(query_text, k=k)
    
    print("\n=== Basic Semantic Search Results ===")
    print(f"Query: '{query_text}'")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        print(f"\n{i+1}. Score: {score:.4f}")
        print(f"   Node ID: {node.id}")
        print(f"   Type: {node.type}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content (handle different content formats)
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_nl_query(atlas, nl_query, k=5):
    """Run a natural language query with automatic coordinate filtering."""
    logger.info(f"Running natural language query: '{nl_query}'")
    
    results = atlas.search_with_nl_query(nl_query, k=k)
    
    print("\n=== Natural Language Query Results ===")
    print(f"Query: '{nl_query}'")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        print(f"\n{i+1}. Score: {score:.4f}")
        print(f"   Node ID: {node.id}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_temporal_focus_query(atlas, query_text, temporal_focus, decay_rate=0.15, k=5):
    """Run a query with temporal focus to prioritize specific time points."""
    logger.info(f"Running temporal focus query: '{query_text}' (t={temporal_focus}, decay={decay_rate})")
    
    results = atlas.search_with_temporal_focus(
        query_text=query_text,
        temporal_focus=temporal_focus,
        decay_rate=decay_rate,
        k=k
    )
    
    print("\n=== Temporal Focus Query Results ===")
    print(f"Query: '{query_text}'")
    print(f"Temporal Focus: t={temporal_focus}, Decay Rate: {decay_rate}")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        # Calculate temporal distance for display
        t_distance = abs(node.coordinates.t - temporal_focus)
        
        print(f"\n{i+1}. Score: {score:.4f} (temporal distance: {t_distance:.2f})")
        print(f"   Node ID: {node.id}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_directional_query(atlas, query_text, direction, strength=0.3, k=5):
    """Run a query with directional bias to favor a specific semantic direction."""
    logger.info(f"Running directional query: '{query_text}' (θ={direction}, strength={strength})")
    
    results = atlas.search_with_directional_bias(
        query_text=query_text,
        direction=direction,
        strength=strength,
        k=k
    )
    
    print("\n=== Directional Bias Query Results ===")
    print(f"Query: '{query_text}'")
    print(f"Direction: θ={direction}, Strength: {strength}")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        # Calculate angular distance for display (considering circular nature)
        angular_dist = min(
            abs(node.coordinates.theta - direction),
            2 * 3.14159 - abs(node.coordinates.theta - direction)
        )
        
        print(f"\n{i+1}. Score: {score:.4f} (angular distance: {angular_dist:.2f})")
        print(f"   Node ID: {node.id}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_custom_filter_query(atlas, query_text, r_min=None, r_max=None, t_min=None, t_max=None, k=5):
    """Run a query with custom coordinate filters."""
    logger.info(f"Running custom filter query: '{query_text}' (r_min={r_min}, r_max={r_max}, t_min={t_min}, t_max={t_max})")
    
    # Create coordinate filters
    filters = CoordinateFilters(
        r_min=r_min,
        r_max=r_max,
        t_min=t_min,
        t_max=t_max
    )
    
    # Get matching IDs first (for validation)
    matching_ids = atlas._get_ids_matching_filters(filters)
    
    if matching_ids:
        logger.info(f"Filter matches {len(matching_ids)} nodes")
    else:
        logger.warning("No nodes match the specified filters")
    
    # Run filtered query
    results = atlas.search_with_retrieval_params(
        query_text=query_text,
        retrieval_params={
            "filters": filters,
            "search_type": "filtered"
        },
        k=k
    )
    
    print("\n=== Custom Filter Query Results ===")
    print(f"Query: '{query_text}'")
    print(f"Filters: r_min={r_min}, r_max={r_max}, t_min={t_min}, t_max={t_max}")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        print(f"\n{i+1}. Score: {score:.4f}")
        print(f"   Node ID: {node.id}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_all_in_one_query(atlas, query_text, temporal_focus, directional_bias, r_min, r_max, t_min, t_max, k=5):
    """Run a query using all coordinate-based features together."""
    logger.info(f"Running comprehensive query with all features")
    
    # Prepare retrieval parameters
    retrieval_params = {
        "search_type": "comprehensive"
    }
    
    # Add temporal focus if specified
    if temporal_focus is not None:
        retrieval_params["temporal_focus"] = temporal_focus
        retrieval_params["temporal_decay_rate"] = 0.15
    
    # Add directional bias if specified
    if directional_bias is not None:
        retrieval_params["directional_bias"] = directional_bias
        retrieval_params["directional_strength"] = 0.3
    
    # Add coordinate filters if specified
    filters = {}
    if r_min is not None or r_max is not None or t_min is not None or t_max is not None:
        filters = CoordinateFilters(
            r_min=r_min,
            r_max=r_max,
            t_min=t_min,
            t_max=t_max
        )
        retrieval_params["filters"] = filters
    
    # Run the query
    results = atlas.search_with_retrieval_params(
        query_text=query_text,
        retrieval_params=retrieval_params,
        k=k
    )
    
    print("\n=== Comprehensive Query Results ===")
    print(f"Query: '{query_text}'")
    print(f"Parameters:")
    print(f"  - Temporal Focus: {temporal_focus}")
    print(f"  - Directional Bias: {directional_bias}")
    print(f"  - Filters: r_min={r_min}, r_max={r_max}, t_min={t_min}, t_max={t_max}")
    print(f"Found {len(results)} results:")
    
    for i, (node, score) in enumerate(results):
        print(f"\n{i+1}. Score: {score:.4f}")
        print(f"   Node ID: {node.id}")
        print(f"   Coordinates: r={node.coordinates.r:.2f}, θ={node.coordinates.theta:.2f}, t={node.coordinates.t:.2f}, z={node.coordinates.z:.2f}")
        
        # Print content
        if isinstance(node.content, dict) and 'text' in node.content:
            text = node.content['text']
            print(f"   Content: {text[:150]}..." if len(text) > 150 else f"   Content: {text}")
        else:
            print(f"   Content: {str(node.content)[:150]}...")
    
    return results

def run_rag_query(atlas, query_text):
    """Run a RAG query to generate context-enhanced prompt."""
    logger.info(f"Running RAG query: '{query_text}'")
    
    context_prompt = atlas.answer_query_with_context(
        user_query=query_text,
        k=3  # Include 3 context elements
    )
    
    print("\n=== RAG Context Generation ===")
    print(f"Query: '{query_text}'")
    print(f"\nGenerated Context Prompt:")
    print("-" * 80)
    print(context_prompt)
    print("-" * 80)
    
    return context_prompt

def visualize_query_results(atlas, results, query_text, output_dir):
    """Generate visualizations for query results."""
    logger.info(f"Generating visualizations for query results")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize visualizer
    visualizer = CoordinateVisualizer(output_dir=output_dir)
    
    # Get node IDs from results
    result_ids = [node.id for node, _ in results]
    
    # Generate visualizations highlighting query results
    vis_paths = visualizer.visualize_atlas(
        atlas=atlas,
        view_type="all",
        color_by="query_result",
        highlight_nodes=result_ids,
        title=f"Query Results: {query_text}"
    )
    
    print(f"\nVisualizations generated at:")
    for view_type, path in vis_paths.items():
        print(f"- {view_type}: {path}")
    
    return vis_paths

def run_demos(atlas, k=5, viz_output=None):
    """Run a series of demo queries to showcase different query types."""
    print("\n" + "="*80)
    print("TEMPORAL-SPATIAL MEMORY SYSTEM - DEMO QUERIES")
    print("="*80)
    
    # Get some atlas statistics for better demos
    t_values = [node.coordinates.t for node in atlas.db.nodes.values()]
    t_min, t_max = min(t_values), max(t_values)
    t_middle = (t_min + t_max) / 2
    
    # 1. Basic Semantic Search
    basic_results = run_basic_query(
        atlas=atlas,
        query_text="Tell me about the main character",
        k=k
    )
    
    if viz_output and basic_results:
        visualize_query_results(
            atlas=atlas,
            results=basic_results,
            query_text="Basic: Main Character",
            output_dir=os.path.join(viz_output, "basic_query")
        )
    
    # 2. Natural Language Query with Temporal Hints
    nl_results = run_nl_query(
        atlas=atlas,
        nl_query="What happens at the beginning of the story?",
        k=k
    )
    
    if viz_output and nl_results:
        visualize_query_results(
            atlas=atlas,
            results=nl_results,
            query_text="NL: Beginning of Story",
            output_dir=os.path.join(viz_output, "nl_query")
        )
    
    # 3. Temporal Focus Query (early in document)
    early_results = run_temporal_focus_query(
        atlas=atlas,
        query_text="What is happening here?",
        temporal_focus=t_min + (t_max - t_min) * 0.2,  # 20% into the document
        decay_rate=0.15,
        k=k
    )
    
    if viz_output and early_results:
        visualize_query_results(
            atlas=atlas,
            results=early_results,
            query_text="Temporal: Early Events",
            output_dir=os.path.join(viz_output, "early_query")
        )
    
    # 4. Temporal Focus Query (late in document)
    late_results = run_temporal_focus_query(
        atlas=atlas,
        query_text="What is happening here?",
        temporal_focus=t_min + (t_max - t_min) * 0.8,  # 80% into the document
        decay_rate=0.15,
        k=k
    )
    
    if viz_output and late_results:
        visualize_query_results(
            atlas=atlas,
            results=late_results,
            query_text="Temporal: Late Events",
            output_dir=os.path.join(viz_output, "late_query")
        )
    
    # 5. Directional Query (if we have some nodes)
    if atlas.db.nodes:
        # Get a sample node's theta as direction
        sample_node = list(atlas.db.nodes.values())[len(atlas.db.nodes) // 3]
        direction = sample_node.coordinates.theta
        
        directional_results = run_directional_query(
            atlas=atlas,
            query_text="Find conceptually similar content",
            direction=direction,
            strength=0.4,
            k=k
        )
        
        if viz_output and directional_results:
            visualize_query_results(
                atlas=atlas,
                results=directional_results,
                query_text=f"Directional: θ={direction:.2f}",
                output_dir=os.path.join(viz_output, "directional_query")
            )
    
    # 6. Custom Filter Query
    filter_results = run_custom_filter_query(
        atlas=atlas,
        query_text="Find specific content",
        r_min=0.1,
        r_max=0.9,
        t_min=t_middle - (t_max - t_min) * 0.25,
        t_max=t_middle + (t_max - t_min) * 0.25,
        k=k
    )
    
    if viz_output and filter_results:
        visualize_query_results(
            atlas=atlas,
            results=filter_results,
            query_text="Filtered: Middle Section",
            output_dir=os.path.join(viz_output, "filter_query")
        )
    
    # 7. All-in-One Comprehensive Query
    comprehensive_results = run_all_in_one_query(
        atlas=atlas,
        query_text="Find important events",
        temporal_focus=t_middle,
        directional_bias=None if not atlas.db.nodes else list(atlas.db.nodes.values())[0].coordinates.theta,
        r_min=0.0,
        r_max=0.5,  # Focus on more important nodes
        t_min=None,
        t_max=None,
        k=k
    )
    
    if viz_output and comprehensive_results:
        visualize_query_results(
            atlas=atlas,
            results=comprehensive_results,
            query_text="Comprehensive: Important Events",
            output_dir=os.path.join(viz_output, "comprehensive_query")
        )
    
    # 8. RAG Context Generation
    rag_prompt = run_rag_query(
        atlas=atlas,
        query_text="Summarize the main events in chronological order"
    )
    
    print("\n" + "="*80)
    print("DEMO QUERIES COMPLETE")
    print("="*80)

def main():
    """Main function to run the query system integration example."""
    # Parse command line arguments
    args = parse_args()
    
    # Load the Narrative Atlas
    atlas = load_atlas(args.atlas_path)
    
    # If a specific query was provided, run it
    if args.query:
        if args.temporal_focus is not None:
            # Run temporal focus query
            results = run_temporal_focus_query(
                atlas=atlas,
                query_text=args.query,
                temporal_focus=args.temporal_focus,
                decay_rate=args.decay_rate,
                k=args.k
            )
        elif args.directional_bias is not None:
            # Run directional bias query
            results = run_directional_query(
                atlas=atlas,
                query_text=args.query,
                direction=args.directional_bias,
                strength=args.directional_strength,
                k=args.k
            )
        elif args.r_min is not None or args.r_max is not None or args.t_min is not None or args.t_max is not None:
            # Run custom filter query
            results = run_custom_filter_query(
                atlas=atlas,
                query_text=args.query,
                r_min=args.r_min,
                r_max=args.r_max,
                t_min=args.t_min,
                t_max=args.t_max,
                k=args.k
            )
        else:
            # Run natural language query
            results = run_nl_query(
                atlas=atlas,
                nl_query=args.query,
                k=args.k
            )
        
        # Generate visualizations if requested
        if args.visualize and results:
            visualize_query_results(
                atlas=atlas,
                results=results,
                query_text=args.query,
                output_dir=args.viz_output
            )
            
        # Also generate RAG prompt
        rag_prompt = run_rag_query(atlas=atlas, query_text=args.query)
        
    # If no query was provided, run the demos (unless --no-demos was specified)
    elif not args.no_demos:
        run_demos(
            atlas=atlas,
            k=args.k,
            viz_output=args.viz_output if args.visualize else None
        )
    else:
        print("No query provided and --no-demos specified. Nothing to do.")

if __name__ == "__main__":
    main() 
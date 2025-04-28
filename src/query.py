"""
Query script for the 4D polar-temporal database system.

This module provides functionality to query the database based on
text or coordinate constraints.
"""

import os
import sys
import json
import logging
import argparse
import time
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import local modules
from src.models.narrative_atlas import NarrativeAtlas, Node
from src.utils.embedding_service import create_embedding_service
from src.models.coordinate_system import PolarTemporalCoordinate, PolarTemporalSpace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Query')


class QueryEngine:
    """
    Engine for querying the 4D polar-temporal database using NarrativeAtlas.
    """
    
    def __init__(self, narrative_atlas: NarrativeAtlas):
        """
        Initialize the query engine.
        
        Args:
            narrative_atlas: Instance of NarrativeAtlas containing the data and index
        """
        # Store NarrativeAtlas instance
        self.narrative_atlas = narrative_atlas
        
        # Keep coordinate space for coordinate queries
        self.coordinate_space = PolarTemporalSpace()
    
    def query_by_text(self, 
                     query_text: str, 
                     max_results: int = 10,
                     min_relevance: float = 0.0) -> List[Dict[str, Any]]:
        """
        Query the database by text similarity using FAISS via NarrativeAtlas.
        
        Args:
            query_text: Text to search for
            max_results: Maximum number of results to return
            min_relevance: Minimum relevance score (Note: FAISS L2 score is distance, lower=better. Set to 0 to disable filtering by score for now).
            
        Returns:
            List of matching chunk nodes with scores
        """
        logger.info(f"Querying by text using NarrativeAtlas: '{query_text}'")
        
        # --- Use NarrativeAtlas for efficient search --- 
        # This directly uses the FAISS index
        similar_nodes_with_scores = self.narrative_atlas.find_similar_nodes(
            query_text=query_text, 
            k=max_results
        )
        
        # Format results
        results = []
        for node, score in similar_nodes_with_scores:
            # FAISS L2 distance score: lower is more similar.
            # We can convert to a 0-1 similarity if needed, but for now, just return the node and score.
            # Example conversion (not implemented): similarity = 1 / (1 + score)
            
            # Basic filtering example (optional, based on distance)
            # if min_relevance > 0 and score > some_distance_threshold: # Adjust threshold logic if using score filtering
            #    continue
                
            results.append({
                'item': node, # The Node object itself
                'score': score # The FAISS distance score (lower is better)
            })
        # --- End efficient search section --- 
        
        logger.info(f"Found {len(results)} results for text query via NarrativeAtlas")
        
        return results
    
    def query_by_coordinates(self,
                          coordinate: PolarTemporalCoordinate,
                          max_distance: float = 5.0,
                          max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Query the database by proximity to a coordinate.
        (Accesses nodes via narrative_atlas.db)
        
        Args:
            coordinate: Coordinate to search around
            max_distance: Maximum distance for matches
            max_results: Maximum number of results to return
            
        Returns:
            List of matching items with distances
        """
        logger.info(f"Querying by coordinate: {coordinate}")
        
        # Get all nodes from the narrative atlas DB
        results = []
        # Iterate through nodes in the underlying SpatialTemporalDB
        for node_id, node in self.narrative_atlas.db.nodes.items(): 
            
            # Check if node has coordinates (should always have, but check anyway)
            if not hasattr(node, 'spatial_coordinates') or not hasattr(node, 'temporal_coordinate'):
                continue
            
            # Create coordinate from node
            # Assuming spatial_coordinates = [r, theta, z]
            if len(node.spatial_coordinates) != 3:
                 logger.warning(f"Node {node_id} has unexpected spatial_coordinates format: {node.spatial_coordinates}")
                 continue

            item_coordinate = PolarTemporalCoordinate(
                r=node.spatial_coordinates[0],
                theta=node.spatial_coordinates[1],
                t=node.temporal_coordinate,
                z=node.spatial_coordinates[2]
            )
            
            # Calculate distance
            distance = self.coordinate_space.distance(coordinate, item_coordinate)
            
            # Add to results if within threshold
            if distance <= max_distance:
                results.append({
                    # Return the Node object directly
                    'item': node, 
                    'distance': distance
                })
        
        # Sort by distance (lowest first)
        results.sort(key=lambda x: x['distance'])
        
        # Limit results
        results = results[:max_results]
        
        logger.info(f"Found {len(results)} results for coordinate query")
        
        return results
    
    def format_result(self, result: Dict[str, Any], include_content: bool = True) -> Dict[str, Any]:
        """
        Format a result item for display.
        
        Args:
            result: Result item containing 'item' (a Node object) and 'score' or 'distance'
            include_content: Whether to include the full content in the result
            
        Returns:
            Formatted result dictionary
        """
        # Access dictionary using keys, not tuple unpacking
        item_node = result.get('item') 
        score = result.get('score')
        
        if not item_node or score is None:
            print(f"Skipping invalid result item: {result}")
            return None # Indicate skipping

        # Convert score before adding to dict
        try:
            formatted_score = float(score)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not convert score '{score}' to float for node {item_node.id if item_node else 'N/A'}. Error: {e}")
            formatted_score = -1.0 # Assign default/error value

        formatted = {
            'id': item_node.id,
            'score': formatted_score, 
            # Access coordinate dict correctly
            'temporal_coordinate': item_node.coordinates.get('t', None), 
            'node_type': item_node.type, # Use correct attribute name
            'coordinates': item_node.coordinates, # Include full coordinates dict
            # Include relevant metadata directly from the node's metadata field
            'metadata': item_node.metadata 
        }

        # Optionally include content
        if include_content:
            # Assuming content is stored under 'text' key in node.content dict
            formatted['content'] = item_node.content.get('text', json.dumps(item_node.content))

        return formatted

    def print_results(self, results: List[Dict]):
        """Print formatted query results."""
        if not results:
            print("No results found.")
            return
            
        print("\n--- Query Results ---")
        for i, res in enumerate(results):
            if res is None: continue # Skip if format_result returned None
            
            print(f"--- Result {i+1} ---")
            print(f"ID: {res.get('id')}")
            print(f"Type: {res.get('node_type')}")
            if 'score' in res: print(f"Score: {res['score']:.4f}")
            print(f"Temporal Coordinate (t): {res.get('temporal_coordinate', 'N/A')}")
            print(f"Coordinates: {res.get('coordinates', {})}")
            print(f"Metadata: {res.get('metadata', {})}")
            if 'content' in res:
                 print(f"Content: {res['content']}")
            print("-" * 20)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Query the 4D Polar-Temporal Database')
    
    parser.add_argument('--storage-path', type=str, required=True,
                        help='Path to the Narrative Atlas storage directory')
    
    parser.add_argument('--text-query', type=str,
                        help='Query by text similarity')
    
    parser.add_argument('--coord-query', type=str,
                        help='Query by coordinate proximity (format: r,theta,t,z)')
    
    parser.add_argument('--max-distance', type=float, default=5.0,
                        help='Maximum distance for coordinate query (default: 5.0)')
    
    parser.add_argument('--max-results', type=int, default=10,
                        help='Maximum number of results to return (default: 10)')
    
    # --- Add embedding service argument --- 
    parser.add_argument('--embedding-service', type=str, default='mock',
                        choices=['mock', 'langchain', 'cascading'],
                        help='Embedding service to use for query embedding (default: mock)')
    # --- End Add --- 

    parser.add_argument('--output-format', type=str, default='json',
                        choices=['json', 'pretty'],
                        help='Output format for results (default: json)')

    parser.add_argument('--hide-content', action='store_true',
                        help='Do not include full content in the output')

    return parser.parse_args()


def main():
    """Main function to run queries."""
    args = parse_args()
    
    # --- Initialize NarrativeAtlas --- 
    # NarrativeAtlas needs the embedding service only if it needs to *load* an index 
    # created by a specific service OR if it needs to embed the query text itself.
    # Since FAISS stores the index, loading might not require the exact service obj,
    # but embedding the query *does*. We need an embedding service instance here.
    
    # --- Use embedding service specified in args --- 
    # Let's use the factory, defaulting to 'mock' if not specified via env vars.
    # This assumes the index was created with a compatible embedding dimension.
    # embedding_service_type = os.getenv('EMBEDDING_SERVICE_TYPE', 'mock') # Or get from args if we add it back
    embedding_service_type = args.embedding_service # Use the argument directly
    # --- End Use Args --- 
    
    embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2') # Default
    
    logger.info(f"Initializing query with embedding service type: {embedding_service_type}")
    kwargs = {}
    if embedding_service_type == 'langchain':
        kwargs['model_name'] = embedding_model_name
        # Note: API key needs to be in environment for OpenAI models
        
    embedding_service = create_embedding_service(
        service_type=embedding_service_type, 
        **kwargs
    )

    try:
        narrative_atlas = NarrativeAtlas(
            storage_path=args.storage_path,
            embedding_service=embedding_service 
        )
    except Exception as e:
         logger.error(f"Failed to initialize NarrativeAtlas from {args.storage_path}: {e}")
         sys.exit(1)
    # --- End NarrativeAtlas Initialization --- 
    
    query_engine = QueryEngine(narrative_atlas=narrative_atlas)
    
    results_data = []
    query_type = "None"
    
    # Perform query based on arguments
    if args.text_query:
        query_type = "Text"
        raw_results = query_engine.query_by_text(args.text_query, args.max_results)
        results_data = raw_results
    elif args.coord_query:
        query_type = "Coordinate"
        try:
            coords = [float(c.strip()) for c in args.coord_query.split(',')]
            if len(coords) != 4:
                raise ValueError("Coordinate query must have 4 values: r,theta,t,z")
            target_coord = PolarTemporalCoordinate(r=coords[0], theta=coords[1], t=coords[2], z=coords[3])
            results_data = query_engine.query_by_coordinates(
                coordinate=target_coord,
                max_distance=args.max_distance,
                max_results=args.max_results
            )
        except ValueError as e:
            logger.error(f"Invalid coordinate query format: {e}")
            sys.exit(1)
    else:
        logger.warning("No query specified (--text-query or --coord-query)")
        return

    # Format and print results
    formatted_results = []
    if results_data:
         for result_dict in results_data: # Iterate through result dictionaries
             formatted = query_engine.format_result(result_dict, include_content=not args.hide_content)
             if formatted and 'error' not in formatted: # Check for errors from format_result
                 formatted_results.append(formatted)
        
    query_engine.print_results(formatted_results)


if __name__ == '__main__':
    main() 
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
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import asdict

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import local modules
from src.models.narrative_atlas import NarrativeAtlas, Node
from src.utils.embedding_service import create_embedding_service
from src.coordinates import PolarTemporalCoordinate

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
        self.narrative_atlas = narrative_atlas
    
    def query_by_natural_language(self, nl_query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """ 
        Query the Narrative Atlas using a natural language query string.
        Leverages the atlas's NL parsing, filtering, and search capabilities.
        
        Args:
            nl_query: The natural language query.
            max_results: The maximum number of final results desired.
            
        Returns:
            List of formatted result dictionaries.
        """
        logger.info(f"Querying by natural language: '{nl_query}' (k={max_results})")
        
        # Call the new search method in NarrativeAtlas
        results_with_scores: List[Tuple[Node, float]] = \
            self.narrative_atlas.search_with_nl_query(nl_query=nl_query, k=max_results)
            
        # Format the results
        formatted_results = []
        for node, score in results_with_scores:
            # Prepare dict structure expected by format_result
            result_item = {'item': node, 'score': score}
            formatted = self.format_result(result_item, include_content=True) # Include content by default
            if formatted:
                formatted_results.append(formatted)
                
        logger.info(f"Formatted {len(formatted_results)} results for NL query.")
        return formatted_results
        
    def format_result(self, result: Dict[str, Any], include_content: bool = True) -> Optional[Dict[str, Any]]:
        """
        Format a result item for display.
        (Modified to handle potential None coordinates and use direct Node attributes)
        """
        item_node: Node = result.get('item')
        score = result.get('score')

        if not isinstance(item_node, Node) or score is None:
            print(f"Skipping invalid result item: {result}")
            return None

        try:
            formatted_score = float(score)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not convert score '{score}' to float for node {item_node.id}. Error: {e}")
            formatted_score = -1.0 # Assign default/error value

        formatted = {
            'id': item_node.id,
            'score': formatted_score,
            'node_type': item_node.type,
             # Directly access coordinates from the Node object
            'coordinates': asdict(item_node.coordinates) if item_node.coordinates else None, 
            'temporal_coordinate': item_node.coordinates.t if item_node.coordinates else None, 
            'metadata': item_node.metadata
        }

        if include_content:
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
    
    parser.add_argument('--query', type=str, required=True,
                        help='Natural language query string to process')
    
    parser.add_argument('--max-results', type=int, default=10,
                        help='Maximum number of results to return (default: 10)')
    
    parser.add_argument('--embedding-service', type=str, default='langchain', # Default to langchain for real embeddings
                        choices=['mock', 'langchain', 'cascading'],
                        help='Embedding service used by the Atlas (ensure consistency with ingestion)')

    return parser.parse_args()


def main():
    """Main function to load Atlas and run query."""
    args = parse_args()
    print(f"--- QUERY.PY Running with Args: {args} ---")

    # Check if storage path exists
    if not os.path.exists(args.storage_path):
        logger.error(f"Storage path '{args.storage_path}' does not exist. Cannot load Narrative Atlas.")
        return

    # --- Load Narrative Atlas ---
    try:
        print(f"--- QUERY.PY Creating embedding service: {args.embedding_service} ---")
        # Create embedding service based on args (ensure consistency with ingested data)
        # We need the service mainly for NarrativeAtlas initialization, not query embedding here.
        embedding_service = create_embedding_service(service_type=args.embedding_service)
        
        print(f"--- QUERY.PY Initializing NarrativeAtlas from: {args.storage_path} ---")
        narrative_atlas = NarrativeAtlas(storage_path=args.storage_path, embedding_service=embedding_service)
        # Loading happens within NarrativeAtlas.__init__
        print("--- QUERY.PY NarrativeAtlas initialized and loaded. ---")
    except Exception as e:
        logger.error(f"Failed to initialize or load Narrative Atlas: {e}", exc_info=True)
        return

    # Create Query Engine
    query_engine = QueryEngine(narrative_atlas)

    # --- Execute Natural Language Query --- 
    start_time = time.time()
    print(f"--- QUERY.PY Executing NL Query: '{args.query}' ---")
    try:
         results = query_engine.query_by_natural_language(
             nl_query=args.query,
             max_results=args.max_results
         )
         end_time = time.time()
         print(f"--- QUERY.PY NL Query finished in {end_time - start_time:.2f} seconds ---")
         
         # Print results
         query_engine.print_results(results)
         
    except Exception as e:
         logger.error(f"An error occurred during the natural language query: {e}", exc_info=True)


if __name__ == '__main__':
    main() 
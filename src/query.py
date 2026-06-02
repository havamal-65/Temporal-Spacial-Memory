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

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import local modules
from src.models.narrative_atlas import NarrativeAtlas, Node
from src.models.sequence_retrieval import SequenceRetriever
from src.utils.embedding_service import create_embedding_service
from src.coordinates import PolarTemporalCoordinate

# Explicitly configure root logger and handler
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger() # Get root logger
root_logger.setLevel(logging.DEBUG) # Set root logger level

# Ensure there is a handler and set its level
if not root_logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout) # Use stdout
    root_logger.addHandler(console_handler)
else:
    # Assume the first handler is the one we want to configure
    console_handler = root_logger.handlers[0] 

console_handler.setLevel(logging.DEBUG) # Set handler level explicitly
console_handler.setFormatter(log_formatter)

logger = logging.getLogger('Query') # Get the specific logger for this module


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
    
    def query_by_natural_language(self, nl_query: str, max_results: int = 10,
                                 temporal_focus: float = None,
                                 temporal_decay_rate: float = 0.1,
                                 directional_bias: float = None,
                                 directional_bias_strength: float = 0.3,
                                 relevance_preference: float = None,
                                 use_hyde: bool = False,
                                 use_hybrid_search: bool = False,
                                 keyword_weight: float = 0.3,
                                 retrieval_method: str = None,
                                 diversity_lambda: float = 0.7) -> List[Dict[str, Any]]:
        """ 
        Query the Narrative Atlas using a natural language query string with advanced retrieval parameters.
        
        Args:
            nl_query: The natural language query.
            max_results: The maximum number of final results desired.
            temporal_focus: Optional temporal coordinate to focus results around.
            temporal_decay_rate: Rate of decay for temporal distance from focus point.
            directional_bias: Optional directional bias in radians to favor specific angular regions.
            directional_bias_strength: Strength of the directional bias (0-1).
            relevance_preference: Optional radial distance to prefer (lower is more relevant).
            use_hyde: Whether to use Hypothetical Document Embeddings for retrieval.
            use_hybrid_search: Whether to use hybrid search (semantic + keyword).
            keyword_weight: Weight to give to keyword matches in hybrid search (0-1).
            retrieval_method: Advanced retrieval method to use:
                - None or "standard": Use standard retrieval.
                - "colbert": Use ColBERT token-level retrieval.
                - "rerank": Use Cohere reranking.
                - "mmr": Use Maximal Marginal Relevance for diverse results.
                - "rag_fusion": Use RAG-Fusion to combine retrieval methods.
                - "ensemble": Use weighted ensemble of multiple retrieval methods.
            diversity_lambda: Trade-off parameter for MMR (0-1), higher values favor relevance.
            
        Returns:
            List of formatted result dictionaries.
        """
        logger.info(f"Querying by natural language: '{nl_query}' with advanced parameters")
        
        # Set up retrieval parameters
        retrieval_params = {}
        
        if temporal_focus is not None:
            retrieval_params['time_preference'] = temporal_focus
            retrieval_params['temporal_decay_rate'] = temporal_decay_rate
            
        if directional_bias is not None:
            retrieval_params['directional_bias'] = {
                'direction': directional_bias,
                'strength': directional_bias_strength
            }
            
        if relevance_preference is not None:
            retrieval_params['radial_preference'] = {
                'radius': relevance_preference,
                'strength': 0.2
            }
        
        # Get preprocessed query and enhanced parameters
        processed_query, enhanced_params = self.narrative_atlas.preprocess_query(nl_query, {
            'extract_keywords': True,
            'decompose_query': True,
            'estimate_theta': directional_bias is None  # Only estimate if not provided
        })
        
        # Merge user-specified and enhanced parameters
        merged_params = {**enhanced_params, **retrieval_params}
        
        # Determine which search method to use
        results_with_scores = []
        
        # Choose retrieval method based on parameters
        if retrieval_method == "colbert":
            # Use ColBERT search
            logger.info(f"Using ColBERT search for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_colbert(nl_query, k=max_results)
        elif retrieval_method == "rerank":
            # Use Cohere reranking
            logger.info(f"Using Cohere reranking for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_reranking(nl_query, k=max_results)
        elif retrieval_method == "mmr":
            # Use MMR for diverse results
            logger.info(f"Using MMR for diverse results for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_mmr(nl_query, k=max_results, lambda_param=diversity_lambda)
        elif retrieval_method == "rag_fusion":
            # Use RAG-Fusion
            logger.info(f"Using RAG-Fusion for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_rag_fusion(nl_query, k=max_results)
        elif retrieval_method == "ensemble":
            # Use weighted ensemble
            logger.info(f"Using weighted ensemble for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_weighted_ensemble(nl_query, k=max_results)
        elif use_hyde:
            # Use HyDE search
            logger.info(f"Using HyDE search for query: '{nl_query}'")
            results_with_scores = self.narrative_atlas.search_with_hyde(nl_query, k=max_results)
        elif use_hybrid_search:
            # Use hybrid search
            logger.info(f"Using hybrid search for query: '{nl_query}' with keyword_weight={keyword_weight}")
            results_with_scores = self.narrative_atlas.search_with_hybrid(
                nl_query, 
                keyword_weight=keyword_weight, 
                k=max_results
            )
        else:
            # Standard NL query: detect sequence intent so plain queries like
            # "events in chronological order" or "what happened before X" return
            # time-ordered results instead of similarity-ranked ones.
            intent = SequenceRetriever.detect_sequence_intent(nl_query)
            if intent["mode"] == "timeline":
                logger.info(f"Using timeline (sequence) retrieval for query: '{nl_query}'")
                results_with_scores = self.narrative_atlas.search_timeline(
                    query=processed_query, k=max_results
                )
            elif intent["mode"] == "neighbors":
                logger.info(
                    f"Using neighbor ({intent['direction']}) retrieval for query: '{nl_query}'"
                )
                results_with_scores = self.narrative_atlas.search_neighbors(
                    intent["anchor"], direction=intent["direction"], k=max_results
                )
            else:
                # Use standard search with retrieval parameters
                results_with_scores = self.narrative_atlas.search_with_retrieval_params(
                    processed_query,
                    merged_params,
                    k=max_results
                )
            
        # Format the results
        formatted_results = []
        for node, score in results_with_scores:
            # Prepare dict structure expected by format_result
            result_item = {'item': node, 'score': score}
            formatted = self.format_result(result_item, include_content=True)
            if formatted:
                formatted_results.append(formatted)
                
        logger.info(f"Formatted {len(formatted_results)} results for NL query.")
        return formatted_results
    
    def query_with_temporal_focus(self, query_text: str, temporal_focus: float, 
                                decay_rate: float = 0.1, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Query with focus on a specific temporal coordinate.
        
        Args:
            query_text: The query text.
            temporal_focus: The temporal coordinate to focus around.
            decay_rate: Rate of temporal decay (higher = faster decay).
            max_results: Maximum number of results.
            
        Returns:
            List of formatted result dictionaries.
        """
        results = self.narrative_atlas.search_with_temporal_focus(
            query_text, temporal_focus, decay_rate, max_results
        )
        
        formatted_results = []
        for node, score in results:
            result_item = {'item': node, 'score': score}
            formatted = self.format_result(result_item, include_content=True)
            if formatted:
                formatted_results.append(formatted)
                
        return formatted_results
    
    def query_with_directional_bias(self, query_text: str, direction: float, 
                                  strength: float = 0.3, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Query with bias toward a specific direction in the polar coordinate space.
        
        Args:
            query_text: The query text.
            direction: Preferred direction in radians.
            strength: Strength of the directional bias (0-1).
            max_results: Maximum number of results.
            
        Returns:
            List of formatted result dictionaries.
        """
        results = self.narrative_atlas.search_with_directional_bias(
            query_text, direction, strength, max_results
        )
        
        formatted_results = []
        for node, score in results:
            result_item = {'item': node, 'score': score}
            formatted = self.format_result(result_item, include_content=True)
            if formatted:
                formatted_results.append(formatted)
                
        return formatted_results
        
    def format_result(self, result: Dict[str, Any], include_content: bool = True) -> Optional[Dict[str, Any]]:
        """
        Format a result item for display.
        (Modified to handle potential None coordinates and both dict and object coordinates)
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

        # Safe handling of coordinates - handle both object and dict types
        coordinates_dict = None
        temporal_coordinate = None
        
        if item_node.coordinates:
            if hasattr(item_node.coordinates, 'model_dump'):
                # Pydantic model - use model_dump() method
                coordinates_dict = item_node.coordinates.model_dump()
                temporal_coordinate = item_node.coordinates.t
            elif isinstance(item_node.coordinates, dict):
                # Already a dictionary
                coordinates_dict = item_node.coordinates
                temporal_coordinate = item_node.coordinates.get('t')
            elif hasattr(item_node.coordinates, 't'):
                # Regular object with attributes but no model_dump
                coordinates_dict = {
                    'r': getattr(item_node.coordinates, 'r', 0.0),
                    'theta': getattr(item_node.coordinates, 'theta', 0.0),
                    't': getattr(item_node.coordinates, 't', 0.0),
                    'z': getattr(item_node.coordinates, 'z', 0.0),
                    'z_type': getattr(item_node.coordinates, 'z_type', 'DEFAULT')
                }
                temporal_coordinate = item_node.coordinates.t

        formatted = {
            'id': item_node.id,
            'score': formatted_score,
            'node_type': item_node.type,
            'coordinates': coordinates_dict,
            'temporal_coordinate': temporal_coordinate,
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
            
            # Enhanced coordinate display
            coords = res.get('coordinates', {})
            if coords:
                print(f"Coordinates: r={coords.get('r', 'N/A'):.3f}, theta={coords.get('theta', 'N/A'):.3f} rad")
                
                # Convert theta to degrees and approximate direction
                if 'theta' in coords:
                    theta_degrees = (coords['theta'] * 180 / np.pi) % 360
                    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                    direction_idx = int(((theta_degrees + 22.5) % 360) / 45)
                    print(f"Direction: {directions[direction_idx]} ({theta_degrees:.1f}°)")
                
                if 'z' in coords and 'z_type' in coords:
                    print(f"Z-coordinate: {coords.get('z', 'N/A'):.2f} ({coords.get('z_type', 'N/A')})")
            
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
    
    # Phase 3: Temporal Decay parameters
    parser.add_argument('--temporal-focus', type=float, default=None,
                        help='Temporal coordinate to focus results around (e.g., 5.0)')
    
    parser.add_argument('--temporal-decay-rate', type=float, default=0.1,
                        help='Rate of decay for temporal distance (default: 0.1, higher = faster decay)')
    
    # Phase 3: Directional Bias parameters
    parser.add_argument('--directional-bias', type=float, default=None,
                        help='Directional bias in radians to favor specific angular regions (0-6.28)')
    
    parser.add_argument('--directional-bias-strength', type=float, default=0.3,
                        help='Strength of the directional bias (default: 0.3, range: 0-1)')
    
    # Phase 3: Relevance preference
    parser.add_argument('--relevance-preference', type=float, default=None,
                        help='Radial distance to prefer (lower = more relevant, e.g., 0.5)')
    
    # Phase 3: Query pre-processing options
    parser.add_argument('--decompose-query', action='store_true',
                        help='Enable query decomposition for complex queries')
    
    parser.add_argument('--extract-keywords', action='store_true', default=True,
                        help='Extract and boost keywords from query (default: True)')
    
    parser.add_argument('--estimate-theta', action='store_true',
                        help='Estimate theta angle from query embedding (if no explicit directional-bias)')
    
    # Phase 7: Advanced retrieval options
    parser.add_argument('--use-hyde', action='store_true',
                        help='Use Hypothetical Document Embeddings (HyDE) retrieval')
    
    parser.add_argument('--use-hybrid-search', action='store_true',
                        help='Use hybrid search combining semantic and keyword-based retrieval')
    
    parser.add_argument('--keyword-weight', type=float, default=0.3,
                        help='Weight to give keyword matches in hybrid search (default: 0.3, range: 0-1)')
    
    # Phase 3: Visualization option (placeholder for future)
    parser.add_argument('--visualize-results', action='store_true',
                        help='Generate a visualization of the results in coordinate space (not implemented yet)')

    parser.add_argument('--answer', action='store_true',
                        help='Generate a grounded LLM answer with citations (requires local/Ollama LLM)')

    parser.add_argument('--show-context', action='store_true',
                        help='When using --answer, also print retrieved context passages')

    parser.add_argument('--max-context-tokens', type=int, default=1500,
                        help='Max tokens of retrieved context sent to the LLM (default: 1500)')

    return parser.parse_args()


def create_coordinate_mapper(embedding_service, config=None):
    """
    Create a coordinate mapper with consistent settings across the system.
    Ensures coordinate parameters match between ingestion and retrieval.
    
    Args:
        embedding_service: The embedding service to use
        config: Optional configuration override
        
    Returns:
        Configured CoordinateMapper instance
    """
    from src.utils.coordinate_mapper import CoordinateMapper
    
    # Default configuration that matches ingestion settings
    default_config = {
        "use_embedding_for_coords": True,  # Always use embedding coordinates
        "embedding_r_scale": 1.0,
        "embedding_theta_scale": 3.14159,
        "max_radius": 100.0,
        "min_radius": 0.1,
        "normalize_embeddings": True
    }
    
    # Merge with provided config if any
    if config:
        for key, value in config.items():
            default_config[key] = value
    
    logger.info(f"Creating coordinate mapper with config: {default_config}")
    
    # Create the mapper with the merged configuration
    return CoordinateMapper(
        embedding_service=embedding_service,
        use_embedding_for_coords=default_config["use_embedding_for_coords"],
        embedding_r_scale=default_config["embedding_r_scale"],
        embedding_theta_scale=default_config["embedding_theta_scale"],
        max_radius=default_config["max_radius"],
        min_radius=default_config["min_radius"],
        normalize_embeddings=default_config["normalize_embeddings"]
    )


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
        embedding_service = create_embedding_service(service_type=args.embedding_service)
        
        # Create the coordinate mapper configuration that uses embedding coordinates
        coordinate_config = {
            "use_embedding_for_coords": True,  # CRITICAL: Must match ingestion
            "embedding_r_scale": 1.0,
            "embedding_theta_scale": 3.14159
        }
        
        print(f"--- QUERY.PY Initializing NarrativeAtlas from: {args.storage_path} ---")
        narrative_atlas = NarrativeAtlas(storage_path=args.storage_path, embedding_service=embedding_service)
        
        # Validate the coordinate configuration against what's already in the atlas
        # This prevents parameter mismatch between ingestion and query
        validated_config = narrative_atlas.validate_coordinate_config(coordinate_config)
        logger.info(f"Using validated coordinate config: {validated_config}")
        
        # CRITICAL FIX: Apply the validated configuration to the narrative_atlas.coordinate_mapper
        # This ensures consistent coordinate mapping between storage and query
        if hasattr(narrative_atlas, 'coordinate_mapper') and validated_config:
            # Get existing CoordinateMapper
            mapper = narrative_atlas.coordinate_mapper
            
            # Update critical parameters if they exist in the validated config
            if 'use_embedding_coords' in validated_config and hasattr(mapper, 'use_embedding_for_coords'):
                mapper.use_embedding_for_coords = validated_config['use_embedding_coords']
                logger.info(f"Updated coordinate_mapper.use_embedding_for_coords = {validated_config['use_embedding_coords']}")
                
            if 'embedding_r_scale' in validated_config and hasattr(mapper, 'embedding_r_scale'):
                mapper.embedding_r_scale = validated_config['embedding_r_scale']
                logger.info(f"Updated coordinate_mapper.embedding_r_scale = {validated_config['embedding_r_scale']}")
                
            if 'embedding_theta_scale' in validated_config and hasattr(mapper, 'embedding_theta_scale'):
                mapper.embedding_theta_scale = validated_config['embedding_theta_scale']
                logger.info(f"Updated coordinate_mapper.embedding_theta_scale = {validated_config['embedding_theta_scale']}")
        
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
        if args.answer:
            result = narrative_atlas.answer_query(
                args.query,
                k=args.max_results,
                max_context_tokens=args.max_context_tokens,
            )
            end_time = time.time()
            print(f"--- QUERY.PY Answer finished in {end_time - start_time:.2f} seconds ---")
            print("\n=== Answer ===")
            print(result.get("answer", ""))
            if result.get("context_tokens") is not None:
                print(f"\n(context: {result.get('context_tokens')} tokens, "
                      f"{result.get('context_chars', 0)} chars)")
            citations = result.get("citations") or []
            if citations:
                print("\n=== Citations ===")
                for c in citations:
                    print(f"  - {c}")
            if args.show_context and result.get("context"):
                print("\n=== Context ===")
                print(result["context"])
        else:
            results = query_engine.query_by_natural_language(
                nl_query=args.query,
                max_results=args.max_results,
                temporal_focus=args.temporal_focus,
                temporal_decay_rate=args.temporal_decay_rate,
                directional_bias=args.directional_bias,
                directional_bias_strength=args.directional_bias_strength,
                relevance_preference=args.relevance_preference,
                use_hyde=args.use_hyde,
                use_hybrid_search=args.use_hybrid_search,
                keyword_weight=args.keyword_weight
            )
            end_time = time.time()
            print(f"--- QUERY.PY NL Query finished in {end_time - start_time:.2f} seconds ---")
            query_engine.print_results(results)
         
        if args.visualize_results:
            print("Result visualization is not implemented yet.")
         
    except Exception as e:
        logger.error(f"An error occurred during the natural language query: {e}", exc_info=True)


if __name__ == '__main__':
    main() 
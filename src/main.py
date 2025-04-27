"""
Main application script for the 4D polar-temporal database system.

This module provides the main entry point for ingesting documents
and interacting with the 4D polar-temporal database.
"""
print("--- SRC/MAIN.PY STARTING ---") # DEBUG

import os
import sys
import logging
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
print("--- SRC/MAIN.PY Loading .env ---") # DEBUG
load_dotenv()

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import local modules
# Remove SimpleStorageManager, add NarrativeAtlas
# from src.services.storage_manager import SimpleStorageManager
from src.models.narrative_atlas import NarrativeAtlas
from src.services.ingestion_pipeline import IngestionPipeline
from src.utils.embedding_service import create_embedding_service # Keep factory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Main')


def parse_args():
    print("--- SRC/MAIN.PY PARSING ARGS ---") # DEBUG
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='4D Polar-Temporal Database System')
    
    parser.add_argument('--input-dir', type=str, default='input',
                        help='Directory containing input documents (default: input)')
    
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory for processing output (default: output)')
    
    parser.add_argument('--storage-path', type=str, default='output/db',
                        help='Path for database storage (default: output/db)')
    
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Maximum size of text chunks in characters (default: 1000)')
    
    parser.add_argument('--chunk-overlap', type=int, default=200,
                        help='Overlap between chunks in characters (default: 200)')
    
    parser.add_argument('--embedding-service', type=str, default='mock',
                        choices=['mock', 'langchain'],
                        help='Type of embedding service to use (default: mock)')
    
    parser.add_argument('--clear-db', action='store_true',
                        help='Clear the database before ingestion')
    
    return parser.parse_args()


def main():
    """Main function to run the 4D polar-temporal database system."""
    print("--- SRC/MAIN.PY MAIN START ---") # DEBUG
    args = parse_args()
    print(f"--- SRC/MAIN.PY ARGS: {args} ---") # DEBUG
    
    # --- Create Embedding Service --- 
    print("--- SRC/MAIN.PY Creating Embedding Service ---") # DEBUG
    logger.info(f"Initializing ingestion with embedding service type: {args.embedding_service}")
    kwargs = {}
    if args.embedding_service == 'langchain':
        # If using langchain, allow specifying model name via env var or default
        embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
        embedding_cache_size = int(os.getenv('EMBEDDING_CACHE_SIZE', 1000))
        kwargs['model_name'] = embedding_model_name
        kwargs['cache_size'] = embedding_cache_size
        logger.info(f"Langchain embedding model: {embedding_model_name}, Cache: {embedding_cache_size}")
        # Note: API key needs to be in environment for OpenAI models
        
    embedding_service = create_embedding_service(
        service_type=args.embedding_service, 
        **kwargs
    )
    # --- End Embedding Service --- 
    
    # --- Initialize NarrativeAtlas --- 
    print("--- SRC/MAIN.PY Initializing Narrative Atlas ---") # DEBUG
    logger.info(f"Initializing Narrative Atlas at: {args.storage_path}")
    try:
        # Initialize first without loading to potentially clear before load
        # We might need to adjust NarrativeAtlas.__init__ or this flow
        # depending on whether clear() should happen before or after initial load attempt.
        # For now, initialize which attempts load, then clear if flag is set.
        narrative_atlas = NarrativeAtlas(
            storage_path=args.storage_path,
            embedding_service=embedding_service 
        )
    except Exception as e:
         logger.error(f"Failed to initialize NarrativeAtlas: {e}")
         # Print traceback for more details
         import traceback
         traceback.print_exc()
         sys.exit(1)
    # --- End NarrativeAtlas Initialization --- 

    # --- Remove SimpleStorageManager Initialization ---
    # storage_manager = SimpleStorageManager(storage_path=args.storage_path)
    
    # Clear database if requested
    if args.clear_db:
        logger.warning(f"Clearing existing data in Narrative Atlas at {args.storage_path}...")
        try:
            # Call the new clear method
            narrative_atlas.clear() 
        except Exception as e:
             logger.error(f"Failed to clear Narrative Atlas: {e}")
             import traceback
             traceback.print_exc()
             # Exit if clearing fails, as state might be inconsistent
             sys.exit(1) 
    else:
        # Loading happens implicitly during NarrativeAtlas init if files exist
        logger.info(f"Loaded existing atlas. DB nodes: {len(narrative_atlas.db.nodes)}, FAISS index entries: {narrative_atlas.vector_store.index.ntotal if narrative_atlas.vector_store else 0}")

    # Initialize ingestion pipeline with NarrativeAtlas
    print("--- SRC/MAIN.PY Initializing Pipeline ---") # DEBUG
    logger.info("Initializing ingestion pipeline...")
    pipeline = IngestionPipeline(
        # Pass narrative_atlas instance
        narrative_atlas=narrative_atlas,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        # Pass embedding service type for pipeline's internal use (e.g., logging)
        embedding_service_type=args.embedding_service 
        # embedding_model_name/cache_size are handled when creating embedding_service above
    )
    
    # Process all documents in the input directory
    print("--- SRC/MAIN.PY Starting Ingestion ---") # DEBUG
    start_time = time.time()
    logger.info(f"Starting ingestion from directory: {args.input_dir}")
    
    try:
        stats = pipeline.ingest_directory()
        elapsed_time = time.time() - start_time
        logger.info(f"Completed ingestion in {elapsed_time:.2f} seconds")
        logger.info(f"Ingestion Stats: {stats}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        # Print traceback for more details during failure
        import traceback
        traceback.print_exc()
        # Decide if we should save partial progress or exit
        # For now, let's try saving anyway
        pass
        
    # --- Save the updated Narrative Atlas --- 
    print("--- SRC/MAIN.PY Saving Atlas ---") # DEBUG
    logger.info("Saving Narrative Atlas...")
    try:
        narrative_atlas.save()
        logger.info("Narrative Atlas saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save Narrative Atlas: {e}")
        import traceback
        traceback.print_exc()
    # --- End Save --- 
    
    # --- Remove SimpleStorageManager Stats ---
    # storage_stats = storage_manager.get_stats()
    # logger.info(f"Storage stats: {storage_stats}")
    # Log final atlas stats
    print("--- SRC/MAIN.PY Logging Stats ---") # DEBUG
    logger.info(f"Final Atlas state - DB nodes: {len(narrative_atlas.db.nodes)}, FAISS index entries: {narrative_atlas.vector_store.index.ntotal if narrative_atlas.vector_store else 0}")
    print("--- SRC/MAIN.PY MAIN END ---") # DEBUG

if __name__ == '__main__':
    print("--- SRC/MAIN.PY __main__ GUARD ---") # DEBUG
    main()
    print("--- SRC/MAIN.PY END ---") # DEBUG 
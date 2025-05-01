#!/usr/bin/env python3
"""
Run script for the 4D polar-temporal database system.

This script provides a convenient way to run the system.
"""
print("--- RUN.PY STARTING ---") # DEBUG

import os
import sys
import logging
import argparse
from datetime import datetime  # for run-specific output folder
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
print("--- RUN.PY .env LOADED ---") # DEBUG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Run')


def parse_args():
    print("--- RUN.PY PARSING ARGS ---") # DEBUG
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='4D Polar-Temporal Database System Runner')
    
    parser.add_argument('--mode', type=str, default='ingest',
                        choices=['ingest', 'query', 'all'],
                        help='Mode to run (default: ingest)')
    
    parser.add_argument('--input-dir', type=str, default='input',
                        help='Directory containing input documents (default: input)')
    
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory for processing output (default: output)')
    
    parser.add_argument('--storage-path', type=str, default='output/db',
                        help='Path for database storage (default: output/db)')
    
    parser.add_argument('--clear-db', action='store_true',
                        help='Clear the database before ingestion')
    
    parser.add_argument('--nl-query', type=str, default="What is the story about?",
                        help='Natural language query to run in query or all mode (default: What is the story about?)')
    
    parser.add_argument('--max-results', type=int, default=10,
                        help='Maximum number of results to return (default: 10)')
    
    parser.add_argument('--embedding-service', type=str, default='mock',
                        choices=['mock', 'langchain', 'cascading'],
                        help='Embedding backend to use for ingestion (default: mock)')
    
    # Descriptor for this run's output subfolder
    parser.add_argument('--run-name', type=str, default='run',
                        help='Descriptor to append to the date for this run; used to name the output subfolder')
    
    return parser.parse_args()


def main():
    """Main function to run the system."""
    print("--- RUN.PY MAIN START ---") # DEBUG
    # Parse command line arguments
    args = parse_args()
    print(f"--- RUN.PY ARGS: {args} ---") # DEBUG
    
    # Compute a timestamped subfolder under output_dir for this run
    timestamp = datetime.now().strftime('%Y%m%d')
    run_folder = f"{timestamp}_{args.run_name}"
    # Use output_dir + run_folder as the storage path for this run
    storage_path = os.path.join(args.output_dir, run_folder)
    os.makedirs(storage_path, exist_ok=True)
    
    # Check if input directory exists
    if not os.path.exists(args.input_dir):
        logger.error(f"Input directory '{args.input_dir}' does not exist")
        return
    
    # Run in the specified mode
    if args.mode in ['ingest', 'all']:
        print("--- RUN.PY ENTERING INGEST MODE ---") # DEBUG
        logger.info("Running ingestion pipeline...")
        
        # Build command: override storage-path with our timestamped folder
        cmd = [
            sys.executable,
            "src/main.py",
            "--input-dir", args.input_dir,
            "--output-dir", args.output_dir,
            "--storage-path", storage_path
        ]
        
        # Add clear-db flag if specified
        if args.clear_db:
            cmd.append("--clear-db")
        
        # Pass through embedding service selection
        cmd.extend(["--embedding-service", args.embedding_service])
        
        print(f"--- RUN.PY SUBPROCESS CMD (Ingest): {cmd} ---") # DEBUG
        # Run ingestion
        subprocess.run(cmd, check=True)
        print("--- RUN.PY SUBPROCESS CMD (Ingest) DONE ---") # DEBUG
    
    if args.mode in ['query', 'all']:
        print("--- RUN.PY ENTERING QUERY MODE ---") # DEBUG
        logger.info("Running query engine...")
        
        # Use the --nl-query argument
        query_text = args.nl_query 
        # No need to check if it's None in 'all' mode because it has a default
        if query_text is None and args.mode == 'query': # Still require it if only running query mode
            logger.error("Natural language query (--nl-query) is required in query mode")
            return
        
        # Build query command using the same storage_path
        cmd = [
            sys.executable,
            "src/query.py",
            "--storage-path", storage_path,
            "--max-results", str(args.max_results),
            "--embedding-service", args.embedding_service
        ]
        
        # Add the natural language query using the correct argument name for src/query.py
        if query_text:
            cmd.extend(["--query", query_text]) # Use --query here
        
        print(f"--- RUN.PY SUBPROCESS CMD (Query): {cmd} ---") # DEBUG
        # Run query
        subprocess.run(cmd, check=True)
        print("--- RUN.PY SUBPROCESS CMD (Query) DONE ---") # DEBUG


if __name__ == '__main__':
    print("--- RUN.PY __main__ GUARD ---") # DEBUG
    main()
    print("--- RUN.PY END ---") # DEBUG 
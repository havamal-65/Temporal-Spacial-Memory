import subprocess
import os
import sys
import shutil
from pathlib import Path
import argparse

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.resolve()
INPUT_PDF = PROJECT_ROOT / "input" / "the_hobbit_tolkien.pdf"
ATLAS_PATH = PROJECT_ROOT / "output" / "db_debug_all"
LLM_MODEL = "gpt-4o-mini"
QUERY_TEXT = "Hobbit"
PYTHON_EXECUTABLE = sys.executable # Use the same python interpreter running this script

# --- Helper Function ---
def run_command(command_args: list[str], step_name: str) -> bool:
    """Runs a command as a subprocess and checks the return code."""
    print(f"\n--- Running Step: {step_name} ---")
    print(f"Executing: {' '.join(command_args)}")
    try:
        # Use shell=False (more secure), pass args as a list
        process = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit
            cwd=PROJECT_ROOT, # Ensure commands run from project root
            encoding='utf-8' # Specify UTF-8 encoding
        )
        print(f"--- {step_name} STDOUT ---")
        print(process.stdout)
        print(f"--- {step_name} STDERR ---")
        print(process.stderr)
        print(f"--- {step_name} Exit Code: {process.returncode} ---")
        
        if process.returncode != 0:
            print(f"*** ERROR: {step_name} failed with exit code {process.returncode}. ***")
            return False
        
        print(f"--- Step {step_name} completed successfully. ---")
        return True
        
    except FileNotFoundError:
        print(f"*** ERROR: Python executable not found at {PYTHON_EXECUTABLE}. Cannot run {step_name}. ***")
        return False
    except Exception as e:
        print(f"*** ERROR: An unexpected error occurred during {step_name}: {e} ***")
        return False

# --- Main Execution ---

# 1. Delete existing atlas (optional, uncomment if needed)
# print(f"\n--- Preparing: Deleting existing atlas at {ATLAS_PATH} ---")
# if ATLAS_PATH.exists():
#     try:
#         shutil.rmtree(ATLAS_PATH)
#         print(f"Successfully deleted {ATLAS_PATH}")
#     except Exception as e:
#         print(f"*** ERROR: Could not delete existing atlas: {e} ***")
#         # Decide if you want to exit or continue
#         # sys.exit(1) 

# 2. Run Ingestion
ingest_command = [
    PYTHON_EXECUTABLE,
    str(PROJECT_ROOT / "ingest_structured_atlas.py"),
    "--input-pdf", str(INPUT_PDF),
    "--output-atlas-path", str(ATLAS_PATH),
    "--llm-model", LLM_MODEL,
    # Add --overwrite if you always want to rebuild
    # "--overwrite" 
]
ingestion_successful = run_command(ingest_command, "Ingestion")

# 3. Check if Ingestion *actually* created the output directory
if ingestion_successful:
    if not ATLAS_PATH.exists() or not os.listdir(ATLAS_PATH):
        print(f"*** ERROR: Ingestion command finished, but output path {ATLAS_PATH} is missing or empty. ***")
        ingestion_successful = False
    else:
         print(f"--- Verified: Atlas path {ATLAS_PATH} exists and is not empty. ---")

# 4. Run Query (only if ingestion was successful)
if ingestion_successful:
    query_command = [
        PYTHON_EXECUTABLE,
        str(PROJECT_ROOT / "src" / "query.py"),
        "--storage-path", str(ATLAS_PATH),
        "--query", QUERY_TEXT,
        # Add hybrid search with increased keyword weight for better "Hobbit" results
        "--use-hybrid-search",
        "--keyword-weight", "0.5"
        # Alternatively, use one of these methods for different scenarios:
        # "--retrieval-method", "colbert"  # For token-level matching
        # "--retrieval-method", "rerank"   # When you have COHERE_API_KEY set
        # "--retrieval-method", "mmr"      # For diverse results
        # "--retrieval-method", "ensemble" # For combined approach
    ]
    query_successful = run_command(query_command, "Query")
else:
    print("\n--- Skipping Query step because Ingestion failed or did not produce output. ---")

print("\n--- End-to-End Script Finished. ---")

# Query arguments
parser = argparse.ArgumentParser(description="Run a query against the database")
parser.add_argument("--query", type=str, help="Natural language query to run against the database")
parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results to return for queries")
parser.add_argument("--use-hyde", action="store_true", help="Use Hypothetical Document Embeddings for retrieval")
parser.add_argument("--use-hybrid", action="store_true", help="Use hybrid search (semantic + keyword)")
parser.add_argument("--keyword-weight", type=float, default=0.3, help="Weight for keyword matches in hybrid search (0-1)")
parser.add_argument("--temporal-focus", type=float, help="Optional temporal coordinate to focus results around")
parser.add_argument("--temporal-decay", type=float, default=0.1, help="Rate of decay for temporal distance from focus")
parser.add_argument("--directional-bias", type=float, help="Optional directional bias in radians (0-2π)")
parser.add_argument("--directional-strength", type=float, default=0.3, help="Strength of directional bias (0-1)")
parser.add_argument("--relevance-preference", type=float, help="Optional radial distance to prefer (0-1, lower is more relevant)")

# Advanced Retrieval Method arguments (Phase 8)
parser.add_argument("--retrieval-method", type=str, choices=["standard", "colbert", "rerank", "mmr", "rag_fusion", "ensemble"],
                  help="Advanced retrieval method to use")
parser.add_argument("--diversity-lambda", type=float, default=0.7, 
                  help="Trade-off parameter for MMR (0-1), higher values favor relevance")

args = parser.parse_args()

# Set up the database and retrieval
# ... (existing code)

# If we're querying the database
if args.query:
    # Validate query parameters
    # ... (existing code)
    
    try:
        # Execute the query with specified parameters
        results = query_engine.query_by_natural_language(
            args.query,
            max_results=args.max_results,
            temporal_focus=args.temporal_focus,
            temporal_decay_rate=args.temporal_decay,
            directional_bias=args.directional_bias,
            directional_bias_strength=args.directional_strength,
            relevance_preference=args.relevance_preference,
            use_hyde=args.use_hyde,
            use_hybrid_search=args.use_hybrid,
            keyword_weight=args.keyword_weight,
            retrieval_method=args.retrieval_method,
            diversity_lambda=args.diversity_lambda
        )
        
        # Display results
        print(f"\nQuery Results for: {args.query}")
        print("-" * 80)
        for i, result in enumerate(results):
            print(f"Result {i+1} (Score: {result['score']:.4f}):")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Content: {result.get('content', '')[:200]}...")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error during query execution: {e}") 
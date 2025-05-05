"""
Ingestion script to process a PDF, extract structured entities (Characters, Events, Locations) 
using an LLM, and populate a NarrativeAtlas instance.
"""

import os
import sys
import argparse
import logging
import json
import time
from typing import Dict, List, Optional, Union
from tqdm import tqdm
from pathlib import Path

# --- Logging Configuration (Top Level) ---
# Configure logging as early as possible
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Create a logger instance for use throughout the script
logger = logging.getLogger('StructuredIngestion')
# --- End Logging Configuration ---

from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
# Remove the deprecated import if it exists
# from langchain_core.runnables import create_structured_output_runnable 
# Output parsers no longer explicitly needed in main script due to .with_structured_output
# from langchain_core.output_parsers import JsonOutputParser, StrOutputParser 
from pydantic.v1 import BaseModel, Field, validator
from langchain_community.document_loaders import PyPDFLoader
# from langchain.output_parsers.pydantic import PydanticOutputParser # No longer needed
# from langchain.prompts import PromptTemplate # ChatPromptTemplate is used
# from langchain.chains import LLMChain # Replaced by LCEL
from src.utils.embedding_service import LangchainEmbeddingService
from src.utils.steward_analyzer import StewardAnalyzer
from src.models.narrative_atlas import NarrativeAtlas
from src.data_models import PolarTemporalCoordinate
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Add the src directory to the path to enable imports
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))) # Old line
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__))) # Add project root

# Import local modules
try:
    from src.models.narrative_atlas import NarrativeAtlas
    from src.utils.embedding_service import EmbeddingService # Use base class for type hint if needed, but instance is LangchainEmbeddingService
    # Ensure this matches the actual file name - assuming steward_analyzer.py
    from src.utils.steward_analyzer import StewardAnalyzer 
    from src.data_models import PolarTemporalCoordinate
except ImportError as e:
    # Provide more specific error logging
    # Use a temporary basic logger if the main one isn't configured yet
    temp_logger = logging.getLogger('ImportCheck')
    temp_logger.error(f"ImportError: Could not import a required module. Error: {e}. Check module existence and sys.path.", exc_info=True)
    sys.exit(1)

# --- Configuration ---
# --- Debug: Check .env file existence ---
# Setup logging early to capture this
logger.debug(f"Found .env file at: {find_dotenv()}") # Use logger
# --- End Debug ---

load_dotenv(find_dotenv(usecwd=True)) # Load .env file from CWD explicitly

# Add imports for caching
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

PROJECT_ROOT = Path(__file__).parent.resolve()
INPUT_PDF = PROJECT_ROOT / "input" / "the_hobbit_tolkien.pdf"

# --- LLM and Prompting Setup ---

# Pydantic model for structured LLM output
class ExtractedEntities(BaseModel):
    characters: List[str] = Field(default_factory=list, description="List of character names mentioned on the page.")
    # Use Union[] for Python < 3.10 compatibility
    events: List[Dict[str, Union[str, List[str]]]] = Field(default_factory=list, description="List of events. Each event should have a 'description' (string) and optionally 'participant_names' (list of strings).")
    locations: List[str] = Field(default_factory=list, description="List of location names mentioned on the page.")

    @validator('events')
    def check_event_structure(cls, v):
        for event in v:
            if 'description' not in event or not isinstance(event['description'], str):
                raise ValueError("Each event must have a string 'description'.")
            if 'participant_names' in event and not isinstance(event['participant_names'], list):
                 raise ValueError("Event 'participant_names' must be a list of strings.")
        return v

EXTRACTION_PROMPT_TEMPLATE = """
Analyze the following text from a page of a document:

--- TEXT START ---
{page_text}
--- TEXT END ---

Identify the key entities mentioned ON THIS PAGE ONLY. Extract the following:
1.  **Characters:** List the full names of any distinct characters mentioned.
2.  **Events:** List the key events or actions described. For each event, provide a concise 'description' and, if mentioned *in direct relation to that event on this page*, list the names of characters participating ('participant_names').
3.  **Locations:** List the names of any specific locations mentioned.

Format your response strictly as a JSON object with the keys "characters", "events", and "locations".
- "characters" should be a list of strings.
- "events" should be a list of objects, where each object has a string key "description" and optionally a list-of-strings key "participant_names".
- "locations" should be a list of strings.

Example JSON format:
{{
  "characters": ["Character Name 1", "Character Name 2"],
  "events": [
    {{"description": "A brief event description", "participant_names": ["Character Name 1"]}},
    {{"description": "Another event description"}}
  ],
  "locations": ["Location Name 1", "Location Name 2"]
}}

If no entities of a certain type are found on the page, provide an empty list for that key (e.g., "characters": []).

Provide ONLY the JSON object in your response, without any introductory text or explanations.
"""

def get_llm_client(model_name: str = "gpt-3.5-turbo") -> Optional[ChatOpenAI]:
    """Initializes the LLM client, checking for API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return None
    try:
        # Explicitly pass the API key if needed, otherwise rely on environment variable
        # Add a request timeout (e.g., 60 seconds)
        llm = ChatOpenAI(model=model_name, temperature=0, openai_api_key=api_key, request_timeout=60)
        # Test connection briefly
        llm.invoke("Hello") 
        logger.info(f"Successfully initialized OpenAI client with model: {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize or test OpenAI client: {e}", exc_info=True)
        return None

def extract_entities_from_page(page_text: str, llm: ChatOpenAI, page_num: int) -> Optional[ExtractedEntities]:
    """Uses LLM to extract structured entities from page text."""
    if not page_text or not page_text.strip():
        logger.info(f"Skipping empty or invalid page text for page {page_num}.")
        return None

    prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT_TEMPLATE)
    
    # --- Reverted to recommended method: .with_structured_output --- 
    # Create the structured LLM first by calling the method on the llm object
    try:
        structured_llm = llm.with_structured_output(ExtractedEntities)
    except AttributeError:
         logger.error(f"LLM object (type: {type(llm)}) does not support .with_structured_output. Check Langchain version compatibility.", exc_info=True)
         return None
    except Exception as e:
        logger.error(f"Error calling .with_structured_output: {e}", exc_info=True)
        return None

    # Now create the chain using the structured LLM
    chain = prompt | structured_llm 
    # --- END Reverted Method ---
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Invoke the chain directly
            logger.debug(f"Attempt {attempt + 1}: Invoking structured LLM chain for page {page_num}...")
            start_invoke_time = time.time()
            structured_output = chain.invoke({"page_text": page_text})
            end_invoke_time = time.time()
            logger.debug(f"Attempt {attempt + 1}: LLM chain invocation finished for page {page_num}. Time: {end_invoke_time - start_invoke_time:.2f}s")

            # Basic validation: check if it's the expected Pydantic type
            if isinstance(structured_output, ExtractedEntities):
                return structured_output # Return the parsed Pydantic model
            else:
                logger.warning(f"Attempt {attempt + 1}: Output was not the expected ExtractedEntities type, was {type(structured_output)}. Output: {structured_output}")
                # Treat unexpected type as failure for retry purposes
                raise TypeError("Output type mismatch")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to extract/parse entities: {e}", exc_info=(attempt == max_retries - 1)) # Log full traceback on last attempt
            if attempt == max_retries - 1:
                logger.error(f"Extraction failed after {max_retries} attempts.")
                return None
            # Consider adding a check for specific API errors (like rate limits) that might warrant longer waits
            time.sleep(2 ** attempt) # Exponential backoff
    return None # Should not be reached if logic is correct

# --- Main Ingestion Logic ---

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Ingest PDF into Narrative Atlas using LLM extraction.')
    parser.add_argument('--input-pdf', type=str, required=True, help='Path to the input PDF file.')
    parser.add_argument('--output-atlas-path', type=str, required=True, help='Directory path to save the Narrative Atlas data.')
    parser.add_argument('--llm-model', type=str, default='gpt-3.5-turbo', help='OpenAI model name for extraction (default: gpt-3.5-turbo).')
    parser.add_argument('--start-page', type=int, default=1, help='Page number to start processing from (1-indexed).')
    parser.add_argument('--end-page', type=int, default=None, help='Page number to end processing at (inclusive). Default is process all pages.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing atlas data in the output path.')
    return parser.parse_args()

def main():
    args = parse_args()
    start_time = time.time()

    # --- Initialize SQLite Cache ---
    cache_db_path = ".langchain.db" # Creates the cache file in the project root
    logger.info(f"Setting up SQLite LLM cache at: {cache_db_path}")
    set_llm_cache(SQLiteCache(database_path=cache_db_path))
    # --- End Cache Setup ---

    # --- Initialize dependencies ---
    logger.info(f"Initializing LLM: {args.llm_model}")
    llm = get_llm_client(args.llm_model)
    if llm is None:
        logger.error("Failed to initialize LLM client. Exiting.")
        sys.exit(1)

    # Initialize Embedding Service
    logger.info("Initializing Embedding Service...")
    try:
        # Instantiate directly using the constructor
        embedding_service = LangchainEmbeddingService(
            model_provider='sentence_transformer', # CORRECTED: Use model_provider parameter
            model_name=None, # Allow default model for the provider
            cache_folder=str(PROJECT_ROOT / "cache" / "embeddings")
        )
        logger.info(f"Using embedding service provider: {embedding_service.model_provider} with model: {embedding_service.model_name}")
    except Exception as e:
        logger.error(f"Failed to initialize EmbeddingService: {e}", exc_info=True)
        sys.exit(1)

    # Initialize Steward Analyzer
    logger.info(f"Initializing Steward Analyzer with model: {args.llm_model}")
    try:
        steward_analyzer = StewardAnalyzer(llm_model=args.llm_model) # Use same model for now
        # Simple check if initialization seems okay (assumes reduce_llm exists if successful)
        if not hasattr(steward_analyzer, 'reduce_llm'): 
             logger.warning("Steward Analyzer initialized but might be missing expected attributes (e.g., reduce_llm).")
    except Exception as e:
        logger.error(f"Failed to initialize Steward Analyzer: {e}", exc_info=True)
        steward_analyzer = None # Ensure it's None if init fails

    logger.info(f"Initializing Narrative Atlas at: {args.output_atlas_path}")
    # Ensure parent directory exists for the atlas path
    try:
        os.makedirs(os.path.dirname(args.output_atlas_path), exist_ok=True) 
    except OSError as e:
         logger.error(f"Could not create directory for atlas path {args.output_atlas_path}: {e}")
         # Decide if fatal or can continue (e.g., if path is just a filename in CWD)
         # For now, assume it might be okay if it's just a filename, but log clearly.
         logger.warning("Proceeding despite directory creation error. Ensure path is valid.")
         
    if args.overwrite and os.path.exists(args.output_atlas_path):
        logger.warning(f"Overwriting existing data in {args.output_atlas_path}")
        # Consider more robust overwrite like shutil.rmtree if it's a directory
        pass 
        
    try:
        atlas = NarrativeAtlas(storage_path=args.output_atlas_path, embedding_service=embedding_service)
        # Load existing data if not overwriting, otherwise it starts fresh
        if not args.overwrite and os.path.exists(args.output_atlas_path): # Check existence again *before* loading
            atlas.load()
            logger.info(f"Loaded existing atlas with {len(atlas.db.nodes)} nodes.")
        else:
            logger.info("Starting with a fresh atlas.")
    except Exception as e:
        logger.error(f"Failed to initialize or load Narrative Atlas from {args.output_atlas_path}: {e}", exc_info=True)
        sys.exit(1)


    logger.info(f"Loading PDF: {args.input_pdf}")
    if not os.path.exists(args.input_pdf):
         logger.error(f"Input PDF not found at: {args.input_pdf}")
         sys.exit(1)
         
    try:
        loader = PyPDFLoader(args.input_pdf)
        pages = loader.load() # Loads all pages
    except Exception as e:
        logger.error(f"Failed to load PDF {args.input_pdf}: {e}", exc_info=True)
        sys.exit(1)

    logger.info(f"PDF loaded with {len(pages)} pages.")
    
    # --- Process Pages ---
    total_pages_processed = 0
    successful_extractions = 0
    llm_calls = 0
    start_page_idx = args.start_page - 1
    end_page_idx = args.end_page if args.end_page else len(pages)
    
    if start_page_idx < 0 or start_page_idx >= len(pages):
         logger.error(f"Invalid start page number {args.start_page}. Must be between 1 and {len(pages)}.")
         sys.exit(1)
         
    end_page_idx = min(end_page_idx, len(pages)) # Ensure end_page is not out of bounds

    logger.info(f"Processing pages from {args.start_page} to {end_page_idx}...")

    # Wrap the range with tqdm for a progress bar
    for i in tqdm(range(start_page_idx, end_page_idx), desc="Processing Pages", unit="page"):
        page_doc = pages[i]
        page_num = i + 1
        page_text = page_doc.page_content

        logger.info(f"--- Processing Page {page_num}/{len(pages)} ---")

        # Pass page_text, llm, and page_num
        extracted_data = extract_entities_from_page(page_text, llm, page_num) 
        llm_calls += 1 # Increment even if extraction fails after retries

        if extracted_data:
            successful_extractions += 1
            logger.debug(f"Extracted: {extracted_data}")
            temporal_coord = float(page_num) # Simple temporal coordinate
            
            # Add characters
            for name in extracted_data.characters:
                try:
                    atlas._get_or_create_character(name, temporal_coord)
                    logger.debug(f"Added/found character: {name}")
                except Exception as e:
                    logger.error(f"Error adding character '{name}' from page {page_num}: {e}")

            # Add events
            for event in extracted_data.events:
                description = event.get("description")
                participants = event.get("participant_names", []) # Default to empty list
                if description:
                    try:
                        atlas._create_event(description, temporal_coord, participants)
                        logger.debug(f"Added event: {description[:50]}...")
                    except Exception as e:
                         logger.error(f"Error adding event '{description[:50]}...' from page {page_num}: {e}")

            # Add locations
            for name in extracted_data.locations:
                 try:
                    atlas._get_or_create_location(name, temporal_coord)
                    logger.debug(f"Added/found location: {name}")
                 except Exception as e:
                     logger.error(f"Error adding location '{name}' from page {page_num}: {e}")
            
            total_pages_processed += 1
        else:
            logger.warning(f"Skipping atlas update for page {page_num} due to extraction failure.")

        # --- ADDED LOGGING ---
        logger.debug(f"Finished processing page {page_num}. Nodes in atlas: {len(atlas.db.nodes)}")
        # --- END ADDED LOGGING ---

    # --- Steward Refinement Step ---
    # Added check for steward_analyzer being not None
    if steward_analyzer and hasattr(steward_analyzer, 'reduce_llm') and steward_analyzer.reduce_llm: 
        logger.info("Starting Steward LLM refinement process...")
        # Collect node data needed by Steward (ensure coordinates are serializable if needed, but objects should be fine)
        # Steward expects dicts with 'node_id' and 'coordinate' (PolarTemporalCoordinate obj)
        steward_input_data = []
        for node_id, node_obj in atlas.db.nodes.items():
            if hasattr(node_obj, 'coordinate') and isinstance(node_obj.coordinate, PolarTemporalCoordinate):
                 steward_input_data.append({
                     "node_id": node_id, 
                     "coordinate": node_obj.coordinate # Pass the Pydantic object directly
                })
            else:
                 logger.warning(f"Node {node_id} (type: {type(node_obj).__name__}) missing valid coordinate object for Steward input.")
                 
        if steward_input_data:
            logger.info(f"Sending {len(steward_input_data)} nodes to Steward for analysis.")
            try:
                steward_updates_dict = steward_analyzer.analyze_and_recommend_updates(steward_input_data)
                
                if steward_updates_dict and isinstance(steward_updates_dict, dict) and 'updates' in steward_updates_dict and isinstance(steward_updates_dict['updates'], list):
                    updates_applied = 0
                    for update_info in steward_updates_dict['updates']:
                        if isinstance(update_info, dict) and 'node_id' in update_info and 'new_coordinates' in update_info:
                            node_id = update_info['node_id']
                            new_coords_data = update_info['new_coordinates']
                            
                            # Important: Convert dict back to Pydantic model before updating atlas
                            try:
                                # Ensure all fields are present, provide defaults if necessary for robustness
                                # Note: Steward *should* provide all fields including 't'
                                required_fields = {'r', 'theta', 't', 'z', 'z_type'}
                                if isinstance(new_coords_data, dict) and required_fields.issubset(new_coords_data.keys()):
                                    new_coordinates = PolarTemporalCoordinate(**new_coords_data)
                                    atlas.update_node_coordinates(node_id, new_coordinates)
                                    logger.debug(f"Applied Steward update for node {node_id}")
                                    updates_applied += 1
                                else:
                                    logger.warning(f"Skipping Steward update for node {node_id}: new_coordinates missing required fields or not a dict. Got: {new_coords_data}")
                            except Exception as coord_err:
                                logger.error(f"Error creating PolarTemporalCoordinate from Steward output for node {node_id}: {coord_err} - Data: {new_coords_data}", exc_info=True)
                        else:
                            logger.warning(f"Skipping invalid update item from Steward: {update_info}")
                    logger.info(f"Steward refinement complete. Applied {updates_applied} updates.")
                else:
                    logger.info(f"Steward analysis returned no updates or an invalid format. Received: {type(steward_updates_dict)}")

            except Exception as steward_err:
                logger.error(f"Error during Steward refinement process: {steward_err}", exc_info=True)
        else:
             logger.info("No valid node data with coordinates found to send to Steward.")
    else:
        if not steward_analyzer:
             logger.warning("Steward Analyzer was not initialized successfully. Skipping refinement step.")
        else:
             logger.warning("Steward Analyzer not configured for refinement (missing reduce_llm?). Skipping refinement step.")

    # --- Final Save and Summary ---
    logger.info("Finalizing ingestion and saving atlas...")
    try:
        # --- ADDED LOGGING ---
        logger.info(f"Attempting to save atlas with {len(atlas.db.nodes)} nodes to {atlas.storage_path}...")
        # --- END ADDED LOGGING ---
        atlas.save()
        logger.info("Narrative Atlas saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save final atlas to {atlas.storage_path}: {e}", exc_info=True)

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"--- Ingestion Summary ---")
    logger.info(f"Processed pages: {total_pages_processed} (Range attempted: {args.start_page} to {end_page_idx})")
    logger.info(f"Successful LLM extractions: {successful_extractions}")
    logger.info(f"LLM calls made (extraction attempts): {llm_calls}")
    logger.info(f"Final node count in atlas DB: {len(atlas.db.nodes)}")
    logger.info(f"Total elapsed time: {elapsed_time:.2f} seconds")
    logger.info(f"-------------------------")

if __name__ == "__main__":
    try:
        # Basic check for OPENAI_API_KEY before even starting main logic
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
             # Use logger now since it's configured at the top
             logger.critical("CRITICAL ERROR: OPENAI_API_KEY environment variable not set. Cannot proceed.")
             sys.exit(1)
        else:
             # Optional: Log partial key for confirmation, be careful with security
             logger.info(f"Found OPENAI_API_KEY starting with: {api_key[:5]}...") 
             
        main()
    except Exception as e:
        # Catch any other unexpected errors during initial setup or main() execution
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        sys.exit(1) # Exit with error code 

# [End of file after this line]

   
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
from typing import Dict, List, Optional

from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_community.document_loaders import PyPDFLoader

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import local modules
try:
    from models.narrative_atlas import NarrativeAtlas
except ImportError:
    print("Error: Could not import NarrativeAtlas. Ensure it's in src/models/")
    sys.exit(1)

# --- Configuration ---
# --- Debug: Check .env file existence ---
dotenv_path = find_dotenv()
if dotenv_path:
    print(f"DEBUG: Found .env file at: {dotenv_path}")
else:
    print("DEBUG: .env file not found by find_dotenv().")
# --- End Debug ---

load_dotenv(find_dotenv(usecwd=True)) # Load .env file from CWD explicitly

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StructuredIngestion')

# --- LLM and Prompting Setup ---

# Pydantic model for structured LLM output
class ExtractedEntities(BaseModel):
    characters: List[str] = Field(default_factory=list, description="List of character names mentioned on the page.")
    events: List[Dict[str, str | List[str]]] = Field(default_factory=list, description="List of events. Each event should have a 'description' (string) and optionally 'participant_names' (list of strings).")
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
        llm = ChatOpenAI(model=model_name, temperature=0, openai_api_key=api_key)
        # Test connection briefly
        llm.invoke("Hello") 
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize or test OpenAI client: {e}")
        return None

def extract_entities_from_page(page_text: str, llm: ChatOpenAI, parser) -> Optional[ExtractedEntities]:
    """Uses LLM to extract structured entities from page text."""
    if not page_text.strip():
        logger.info("Skipping empty page text.")
        return None

    prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT_TEMPLATE)
    chain = prompt | llm | parser # Using PydanticOutputParser implicitly via .with_structured_output
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Use with_structured_output for reliable JSON parsing
            structured_output = chain.with_structured_output(ExtractedEntities).invoke({"page_text": page_text})
            logger.debug(f"Successfully extracted: {structured_output}")
            return structured_output # Return the parsed Pydantic model
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to extract/parse entities: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Extraction failed after {max_retries} attempts.")
                return None
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

    # --- Initialize dependencies ---
    logger.info(f"Initializing LLM: {args.llm_model}")
    llm = get_llm_client(args.llm_model)
    if llm is None:
        sys.exit(1)

    # Initialize Pydantic parser (though used implicitly via with_structured_output)
    pydantic_parser = None # Not strictly needed for invocation but good practice

    logger.info(f"Initializing Narrative Atlas at: {args.output_atlas_path}")
    if args.overwrite and os.path.exists(args.output_atlas_path):
        logger.warning(f"Overwriting existing data in {args.output_atlas_path}")
        # Simple overwrite: just proceed. Atlas init handles loading/creating.
        # More robust would be to delete folder contents.
        pass 
    atlas = NarrativeAtlas(storage_path=args.output_atlas_path)
    # Load existing data if not overwriting, otherwise it starts fresh
    if not args.overwrite:
        atlas.load()
        logger.info(f"Loaded existing atlas with {len(atlas.db.nodes)} nodes.")

    logger.info(f"Loading PDF: {args.input_pdf}")
    try:
        loader = PyPDFLoader(args.input_pdf)
        pages = loader.load() # Loads all pages
    except Exception as e:
        logger.error(f"Failed to load PDF {args.input_pdf}: {e}")
        sys.exit(1)

    logger.info(f"PDF loaded with {len(pages)} pages.")
    
    # --- Process Pages ---
    total_pages_processed = 0
    llm_calls = 0
    start_page_idx = args.start_page - 1
    end_page_idx = args.end_page if args.end_page else len(pages)
    end_page_idx = min(end_page_idx, len(pages)) # Ensure end_page is not out of bounds

    logger.info(f"Processing pages from {args.start_page} to {end_page_idx}...")

    for i in range(start_page_idx, end_page_idx):
        page_doc = pages[i]
        page_num = i + 1
        page_text = page_doc.page_content

        logger.info(f"--- Processing Page {page_num}/{len(pages)} ---")

        extracted_data = extract_entities_from_page(page_text, llm, pydantic_parser)
        llm_calls += 1 # Increment even if extraction fails after retries

        if extracted_data:
            logger.debug(f"Extracted: {extracted_data}")
            temporal_coord = float(page_num)
            
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

        # Optional: Save progress periodically
        if page_num % 10 == 0:
            logger.info(f"Saving intermediate progress at page {page_num}...")
            try:
                 atlas.save()
                 logger.info("Intermediate save successful.")
            except Exception as e:
                 logger.error(f"Failed to save intermediate progress: {e}")

    # --- Final Save and Summary ---
    logger.info("Finalizing ingestion and saving atlas...")
    try:
        atlas.save()
        logger.info("Narrative Atlas saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save final atlas: {e}")

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"--- Ingestion Summary ---")
    logger.info(f"Processed pages: {total_pages_processed} ({args.start_page} to {end_page_idx}) out of {len(pages)} total")
    logger.info(f"LLM calls made: {llm_calls}")
    logger.info(f"Final node count in atlas DB: {len(atlas.db.nodes)}")
    logger.info(f"Total elapsed time: {elapsed_time:.2f} seconds")
    logger.info(f"-------------------------")

if __name__ == "__main__":
    main() 
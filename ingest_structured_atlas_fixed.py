"""
Fixed ingestion script to process a PDF, extract structured entities (Characters, Events, Locations) 
using an LLM, and populate a NarrativeAtlas instance with proper page tracking and coordinates.
"""

import os
import sys
import argparse
import logging
import json
import time
import re
from typing import Dict, List, Optional, Union, Tuple
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
from pydantic.v1 import BaseModel, Field, validator
from langchain_community.document_loaders import PyPDFLoader
import numpy as np
from src.utils.embedding_service import LangchainEmbeddingService
from src.utils.steward_analyzer import StewardAnalyzer
from src.models.narrative_atlas import NarrativeAtlas
from src.data_models import PolarTemporalCoordinate
from src.utils.semantic_compass import SemanticCompassMapper
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Add the src directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__))) # Add project root

# Import local modules
try:
    from src.models.narrative_atlas import NarrativeAtlas
    from src.utils.embedding_service import EmbeddingService
    from src.utils.steward_analyzer import StewardAnalyzer 
    from src.data_models import PolarTemporalCoordinate
except ImportError as e:
    temp_logger = logging.getLogger('ImportCheck')
    temp_logger.error(f"ImportError: Could not import a required module. Error: {e}. Check module existence and sys.path.", exc_info=True)
    sys.exit(1)

# --- Configuration ---
logger.debug(f"Found .env file at: {find_dotenv()}")
load_dotenv(find_dotenv(usecwd=True))

PROJECT_ROOT = Path(__file__).parent.resolve()
INPUT_PDF = PROJECT_ROOT / "input" / "the_hobbit_tolkien.pdf"

# --- Enhanced Pydantic model for structured LLM output ---
class ExtractedEntities(BaseModel):
    characters: List[str] = Field(default_factory=list, description="List of character names mentioned on the page.")
    events: List[Dict[str, Union[str, List[str]]]] = Field(default_factory=list, description="List of events. Each event should have a 'description' (string) and optionally 'participant_names' (list of strings).")
    locations: List[str] = Field(default_factory=list, description="List of location names mentioned on the page.")
    chapter_info: Optional[str] = Field(None, description="Chapter title or number if found on this page")
    
    @validator('events')
    def check_event_structure(cls, v):
        for event in v:
            if 'description' not in event or not isinstance(event['description'], str):
                raise ValueError("Each event must have a string 'description'.")
            if 'participant_names' in event and not isinstance(event['participant_names'], list):
                 raise ValueError("Event 'participant_names' must be a list of strings.")
        return v

EXTRACTION_PROMPT_TEMPLATE = """
Analyze the following text from page {page_number} of "The Hobbit":

--- TEXT START ---
{page_text}
--- TEXT END ---

Identify the key entities mentioned ON THIS PAGE ONLY. Extract the following:
1.  **Characters:** List the full names of any distinct characters mentioned.
2.  **Events:** List the key events or actions described. For each event, provide a concise 'description' and, if mentioned *in direct relation to that event on this page*, list the names of characters participating ('participant_names').
3.  **Locations:** List the names of any specific locations mentioned.
4.  **Chapter Info:** If this page contains a chapter title or number, extract it.

Format your response strictly as a JSON object with the keys "characters", "events", "locations", and "chapter_info".
- "characters" should be a list of strings.
- "events" should be a list of objects, where each object has a string key "description" and optionally a list-of-strings key "participant_names".
- "locations" should be a list of strings.
- "chapter_info" should be a string or null if no chapter information is found.

Example JSON format:
{{
  "characters": ["Bilbo Baggins", "Gandalf"],
  "events": [
    {{"description": "Bilbo finds the ring", "participant_names": ["Bilbo Baggins"]}},
    {{"description": "The dwarves arrive at Bag End"}}
  ],
  "locations": ["Bag End", "The Shire"],
  "chapter_info": "Chapter 1: An Unexpected Party"
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
        llm = ChatOpenAI(model=model_name, temperature=0, openai_api_key=api_key, request_timeout=60)
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
    
    try:
        structured_llm = llm.with_structured_output(ExtractedEntities)
    except AttributeError:
         logger.error(f"LLM object (type: {type(llm)}) does not support .with_structured_output. Check Langchain version compatibility.", exc_info=True)
         return None
    except Exception as e:
        logger.error(f"Error calling .with_structured_output: {e}", exc_info=True)
        return None

    chain = prompt | structured_llm 
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}: Invoking structured LLM chain for page {page_num}...")
            start_invoke_time = time.time()
            structured_output = chain.invoke({"page_text": page_text, "page_number": page_num})
            end_invoke_time = time.time()
            logger.debug(f"Attempt {attempt + 1}: LLM chain invocation finished for page {page_num}. Time: {end_invoke_time - start_invoke_time:.2f}s")

            if isinstance(structured_output, ExtractedEntities):
                return structured_output
            else:
                logger.warning(f"Attempt {attempt + 1}: Output was not the expected ExtractedEntities type, was {type(structured_output)}. Output: {structured_output}")
                raise TypeError("Output type mismatch")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to extract/parse entities: {e}", exc_info=(attempt == max_retries - 1))
            if attempt == max_retries - 1:
                logger.error(f"Extraction failed after {max_retries} attempts.")
                return None
            time.sleep(2 ** attempt) # Exponential backoff
    return None

def estimate_book_page_from_pdf(pdf_page: int, pdf_total_pages: int) -> Tuple[int, str]:
    """
    Estimate the actual book page number from PDF page number.
    Returns (estimated_page, confidence_note)
    
    This is a heuristic approach - in production, you'd want to:
    1. Extract actual page numbers from the PDF text
    2. Build a mapping table
    3. Handle front matter, appendices, etc.
    """
    # Typical PDF structure assumptions:
    # - First ~10 pages might be front matter (title, copyright, TOC, etc.)
    # - Main content starts around page 10-15
    # - The Hobbit has approximately 300-320 pages in most editions
    
    FRONT_MATTER_PAGES = 10  # Estimate
    BOOK_PAGES = 310  # Approximate page count of The Hobbit
    
    if pdf_page <= FRONT_MATTER_PAGES:
        # Front matter
        return 0, "front_matter"
    
    # Calculate proportion through the main content
    content_pdf_pages = pdf_total_pages - FRONT_MATTER_PAGES
    pdf_position = pdf_page - FRONT_MATTER_PAGES
    
    # Estimate book page
    estimated_page = int((pdf_position / content_pdf_pages) * BOOK_PAGES)
    
    return estimated_page, "estimated"

def calculate_narrative_position(pdf_page: int, pdf_total_pages: int, chapter_info: Optional[str] = None) -> float:
    """
    Calculate a narrative position (0.0 to 1.0) based on progression through the story.
    This is used for temporal coordinate calculation.
    """
    # Simple linear progression for now
    # Could be enhanced with chapter-based weighting
    return pdf_page / pdf_total_pages

def generate_coordinates_for_entity(entity_type: str, entity_name: str, narrative_position: float,
                                    page_num: int, chapter_info: Optional[str] = None,
                                    embedding: Optional[np.ndarray] = None,
                                    semantic_compass: Optional['SemanticCompassMapper'] = None) -> PolarTemporalCoordinate:
    """
    Generate coordinates for an entity.  theta is assigned by the SemanticCompassMapper
    (cosine similarity to sector centroids) when an embedding is provided; otherwise falls
    back to 0.0.

    Args:
        entity_type: 'character', 'event', or 'location'
        entity_name: Name/description of the entity
        narrative_position: Position in narrative (0.0 to 1.0)
        page_num: Page number where entity appears
        chapter_info: Chapter information if available
        embedding: Pre-computed embedding for the entity text (used for theta)
        semantic_compass: Initialised SemanticCompassMapper instance

    Returns:
        PolarTemporalCoordinate with meaningful values
    """
    # Base temporal coordinate on narrative position
    t = narrative_position * 100.0  # Scale to 0-100 range
    
    # Calculate radius based on entity type and importance
    # Characters and major locations get higher relevance
    if entity_type == "character":
        # Major characters get higher radius
        major_characters = ["bilbo", "gandalf", "thorin", "smaug", "gollum", "elrond", "beorn", "bard"]
        if any(char in entity_name.lower() for char in major_characters):
            r = 0.8 + (narrative_position * 0.2)  # 0.8-1.0 range
        else:
            r = 0.5 + (narrative_position * 0.3)  # 0.5-0.8 range
    elif entity_type == "location":
        # Major locations get higher radius
        major_locations = ["shire", "rivendell", "mirkwood", "lake-town", "lonely mountain", "erebor"]
        if any(loc in entity_name.lower() for loc in major_locations):
            r = 0.7 + (narrative_position * 0.2)  # 0.7-0.9 range
        else:
            r = 0.4 + (narrative_position * 0.3)  # 0.4-0.7 range
    else:  # events
        r = 0.3 + (narrative_position * 0.4)  # 0.3-0.7 range
    
    # Assign theta via SemanticCompassMapper (cosine similarity to sector centroids).
    # Falls back to 0.0 only when no embedding is available.
    if embedding is not None and semantic_compass is not None:
        _, theta = semantic_compass.embedding_to_sector(embedding)
    else:
        theta = 0.0
    
    # Z coordinate for structural information
    z = float(page_num)
    z_type = "DEFAULT"
    
    return PolarTemporalCoordinate(
        r=r,
        theta=theta,
        t=t,
        z=z,
        z_type=z_type
    )

# --- Main Ingestion Logic ---

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Ingest PDF into Narrative Atlas using LLM extraction with proper page tracking.')
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
    cache_db_path = ".langchain.db"
    logger.info(f"Setting up SQLite LLM cache at: {cache_db_path}")
    set_llm_cache(SQLiteCache(database_path=cache_db_path))

    # --- Initialize dependencies ---
    logger.info(f"Initializing LLM: {args.llm_model}")
    llm = get_llm_client(args.llm_model)
    if llm is None:
        logger.error("Failed to initialize LLM client. Exiting.")
        sys.exit(1)

    # Initialize Embedding Service
    logger.info("Initializing Embedding Service...")
    try:
        embedding_service = LangchainEmbeddingService(
            model_provider='sentence_transformer',
            model_name=None,
            cache_folder=str(PROJECT_ROOT / "cache" / "embeddings")
        )
        logger.info(f"Using embedding service provider: {embedding_service.model_provider} with model: {embedding_service.model_name}")
    except Exception as e:
        logger.error(f"Failed to initialize EmbeddingService: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Initializing Semantic Compass Mapper (computes reference centroids once)...")
    try:
        semantic_compass = SemanticCompassMapper(embedding_service)
        logger.info("Semantic compass ready.")
    except Exception as e:
        logger.error(f"Failed to initialize SemanticCompassMapper: {e}", exc_info=True)
        sys.exit(1)

    # Initialize Steward Analyzer
    logger.info(f"Initializing Steward Analyzer with model: {args.llm_model}")
    try:
        steward_analyzer = StewardAnalyzer(llm_model=args.llm_model)
        if not hasattr(steward_analyzer, 'reduce_llm'): 
             logger.warning("Steward Analyzer initialized but might be missing expected attributes (e.g., reduce_llm).")
    except Exception as e:
        logger.error(f"Failed to initialize Steward Analyzer: {e}", exc_info=True)
        steward_analyzer = None

    logger.info(f"Initializing Narrative Atlas at: {args.output_atlas_path}")
    try:
        os.makedirs(os.path.dirname(args.output_atlas_path), exist_ok=True) 
    except OSError as e:
         logger.error(f"Could not create directory for atlas path {args.output_atlas_path}: {e}")
         logger.warning("Proceeding despite directory creation error. Ensure path is valid.")
         
    if args.overwrite and os.path.exists(args.output_atlas_path):
        logger.warning(f"Overwriting existing data in {args.output_atlas_path}")
        
    try:
        atlas = NarrativeAtlas(storage_path=args.output_atlas_path, embedding_service=embedding_service)
        if not args.overwrite and os.path.exists(args.output_atlas_path):
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
        pages = loader.load()
    except Exception as e:
        logger.error(f"Failed to load PDF {args.input_pdf}: {e}", exc_info=True)
        sys.exit(1)

    logger.info(f"PDF loaded with {len(pages)} pages.")
    
    # --- Process Pages ---
    total_pages_processed = 0
    successful_extractions = 0
    llm_calls = 0
    current_chapter = None
    chapter_page_map = {}  # Track which pages belong to which chapters
    
    start_page_idx = args.start_page - 1
    end_page_idx = args.end_page if args.end_page else len(pages)
    
    if start_page_idx < 0 or start_page_idx >= len(pages):
         logger.error(f"Invalid start page number {args.start_page}. Must be between 1 and {len(pages)}.")
         sys.exit(1)
         
    end_page_idx = min(end_page_idx, len(pages))

    logger.info(f"Processing pages from {args.start_page} to {end_page_idx}...")

    # First pass: Extract all entities and build chapter map
    extracted_data_by_page = {}
    
    for i in tqdm(range(start_page_idx, end_page_idx), desc="Processing Pages", unit="page"):
        page_doc = pages[i]
        pdf_page_num = i + 1
        page_text = page_doc.page_content

        logger.info(f"--- Processing Page {pdf_page_num}/{len(pages)} ---")

        extracted_data = extract_entities_from_page(page_text, llm, pdf_page_num) 
        llm_calls += 1

        if extracted_data:
            successful_extractions += 1
            logger.debug(f"Extracted: {extracted_data}")
            
            # Update current chapter if found
            if extracted_data.chapter_info:
                current_chapter = extracted_data.chapter_info
                logger.info(f"Found chapter marker on page {pdf_page_num}: {current_chapter}")
            
            # Store extracted data with page context
            extracted_data_by_page[pdf_page_num] = {
                'data': extracted_data,
                'chapter': current_chapter,
                'text': page_text
            }
            
            if current_chapter:
                chapter_page_map[pdf_page_num] = current_chapter
            
            total_pages_processed += 1
        else:
            logger.warning(f"Skipping page {pdf_page_num} due to extraction failure.")

    # Second pass: Create nodes with proper coordinates and metadata
    logger.info("Creating nodes with enhanced metadata and coordinates...")
    
    for pdf_page_num, page_info in extracted_data_by_page.items():
        extracted_data = page_info['data']
        chapter = page_info['chapter']
        
        # Calculate narrative position and book page
        narrative_position = calculate_narrative_position(pdf_page_num, len(pages), chapter)
        book_page, page_confidence = estimate_book_page_from_pdf(pdf_page_num, len(pages))
        
        # Common metadata for all entities on this page
        page_metadata = {
            "pdf_page": pdf_page_num,
            "book_page": book_page,
            "page_confidence": page_confidence,
            "chapter": chapter,
            "total_pdf_pages": len(pages),
            "narrative_position": narrative_position
        }
        
        # Add characters
        for name in extracted_data.characters:
            try:
                char_embedding = np.array(embedding_service.embed_query(name), dtype=np.float32)
                coordinates = generate_coordinates_for_entity(
                    "character", name, narrative_position, book_page, chapter,
                    embedding=char_embedding, semantic_compass=semantic_compass
                )

                node_id = f"character_{name.lower().replace(' ', '_')}"

                atlas.add_node(
                    node_id=node_id,
                    content={"name": name, "type": "character"},
                    embedding=char_embedding,
                    metadata={
                        **page_metadata,
                        "node_type": "character",
                        "entity_name": name,
                        "first_appearance_page": book_page
                    },
                    coordinates=coordinates,
                    keywords=[name.lower()] + name.lower().split()
                )
                logger.debug(f"Added character: {name} with coordinates r={coordinates.r:.3f}, theta={coordinates.theta:.3f}")
            except Exception as e:
                logger.error(f"Error adding character '{name}' from page {pdf_page_num}: {e}")

        # Add events
        for event in extracted_data.events:
            description = event.get("description")
            participants = event.get("participant_names", [])
            if description:
                try:
                    event_embedding = np.array(embedding_service.embed_query(description), dtype=np.float32)
                    coordinates = generate_coordinates_for_entity(
                        "event", description, narrative_position, book_page, chapter,
                        embedding=event_embedding, semantic_compass=semantic_compass
                    )

                    node_id = f"event_{description.lower().replace(' ', '_')[:50]}_{pdf_page_num}"

                    atlas.add_node(
                        node_id=node_id,
                        content={
                            "description": description,
                            "participant_names": participants,
                            "type": "event"
                        },
                        embedding=event_embedding,
                        metadata={
                            **page_metadata,
                            "node_type": "event",
                            "participants": participants
                        },
                        coordinates=coordinates,
                        keywords=[word.lower() for word in description.split() if len(word) > 3]
                    )
                    logger.debug(f"Added event: {description[:50]}... with coordinates r={coordinates.r:.3f}, theta={coordinates.theta:.3f}")
                except Exception as e:
                    logger.error(f"Error adding event '{description[:50]}...' from page {pdf_page_num}: {e}")

        # Add locations
        for name in extracted_data.locations:
            try:
                loc_embedding = np.array(embedding_service.embed_query(name), dtype=np.float32)
                coordinates = generate_coordinates_for_entity(
                    "location", name, narrative_position, book_page, chapter,
                    embedding=loc_embedding, semantic_compass=semantic_compass
                )

                node_id = f"location_{name.lower().replace(' ', '_')}"

                atlas.add_node(
                    node_id=node_id,
                    content={"name": name, "type": "location"},
                    embedding=loc_embedding,
                    metadata={
                        **page_metadata,
                        "node_type": "location",
                        "entity_name": name,
                        "first_mention_page": book_page
                    },
                    coordinates=coordinates,
                    keywords=[name.lower()] + name.lower().split()
                )
                logger.debug(f"Added location: {name} with coordinates r={coordinates.r:.3f}, theta={coordinates.theta:.3f}")
            except Exception as e:
                logger.error(f"Error adding location '{name}' from page {pdf_page_num}: {e}")

        logger.debug(f"Finished processing page {pdf_page_num}. Nodes in atlas: {len(atlas.db.nodes)}")

    # --- Steward Refinement Step ---
    if steward_analyzer and hasattr(steward_analyzer, 'reduce_llm') and steward_analyzer.reduce_llm: 
        logger.info("Starting Steward LLM refinement process...")
        steward_input_data = []
        for node_id, node_obj in atlas.db.nodes.items():
            if hasattr(node_obj, 'coordinates') and isinstance(node_obj.coordinates, PolarTemporalCoordinate):
                 steward_input_data.append({
                     "node_id": node_id, 
                     "coordinate": node_obj.coordinates
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
                            
                            try:
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
        logger.info(f"Attempting to save atlas with {len(atlas.db.nodes)} nodes to {atlas.storage_path}...")
        atlas.save()
        logger.info("Narrative Atlas saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save final atlas to {atlas.storage_path}: {e}", exc_info=True)

    # --- Generate summary report ---
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Count nodes with page numbers
    nodes_with_pages = sum(1 for node in atlas.db.nodes.values() 
                          if hasattr(node, 'metadata') and node.metadata.get('book_page', 0) > 0)
    
    # Count nodes by type
    node_types = {}
    for node in atlas.db.nodes.values():
        node_type = node.metadata.get('node_type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    logger.info(f"--- Ingestion Summary ---")
    logger.info(f"Processed pages: {total_pages_processed} (Range attempted: {args.start_page} to {end_page_idx})")
    logger.info(f"Successful LLM extractions: {successful_extractions}")
    logger.info(f"LLM calls made (extraction attempts): {llm_calls}")
    logger.info(f"Final node count in atlas DB: {len(atlas.db.nodes)}")
    logger.info(f"Nodes with page numbers: {nodes_with_pages}")
    logger.info(f"Chapters found: {len(set(chapter_page_map.values()))}")
    logger.info(f"Node breakdown by type: {node_types}")
    logger.info(f"Total elapsed time: {elapsed_time:.2f} seconds")
    logger.info(f"-------------------------")

if __name__ == "__main__":
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
             logger.critical("CRITICAL ERROR: OPENAI_API_KEY environment variable not set. Cannot proceed.")
             sys.exit(1)
        else:
             logger.info(f"Found OPENAI_API_KEY starting with: {api_key[:5]}...") 
             
        main()
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        sys.exit(1) 
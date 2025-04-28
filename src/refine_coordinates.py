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
from pydantic import BaseModel, Field # For structured LLM output
import traceback
import pickle # For saving updated nodes

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Project Imports
from models.narrative_atlas import NarrativeAtlas, Node # Node class needed for type hints
from utils.embedding_service import create_embedding_service # Needed for NarrativeAtlas init
from models.coordinate_system import PolarTemporalCoordinate # Might be needed for type hints

# LangChain / LLM Imports
from langchain_openai import ChatOpenAI # Or other LLM provider
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

# Logging & Env Vars Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RefineCoordinates')


# --- LLM Setup Components (Plan Section 3.3) ---

class CoordinateRefinementOutput(BaseModel):
    relevance_score: float = Field(description="Relevance score (0.0 most relevant, 1.0 least relevant) based on narrative importance.")
    topic_category: str = Field(description="Primary topic category of the text chunk.")
    reasoning: Optional[str] = Field(default=None, description="Brief reasoning for the score and category.")

# Create the parser
parser = PydanticOutputParser(pydantic_object=CoordinateRefinementOutput)

# Prompt Template
prompt_template = """
Analyze the following text chunk, considering its content and metadata, to determine its semantic coordinates within a larger narrative structure.

**Context:**
The text chunk comes from a larger document.
Page Number: {page_number}
Chunk Index on Page: {chunk_index_on_page}
Total Chunks on Page: {total_chunks_on_page}
Extracted Keywords: {keywords}
Current Structural Coordinates (t, z): t={t_coord}, z={z_coord}

**Text Chunk Content:**
```
{node_content}
```

**Instructions:**

1.  **Determine Relevance Score (0.0 to 1.0):**
    - Evaluate the chunk's importance to the main narrative flow or understanding key characters/events.
    - Score 0.0 for highly critical information, plot points, or character introductions/developments.
    - Score 1.0 for highly tangential details, repetitive descriptions, or boilerplate text.
    - Assign scores between 0.0 and 1.0 based on this scale. Provide a `relevance_score`.

2.  **Determine Topic Category:**
    - Identify the primary topic or theme discussed in the text chunk.
    - Choose the *single most fitting* category from the following list:
        - Character Introduction/Description
        - Character Interaction/Dialogue
        - Plot Development/Action Sequence
        - World Building/Setting Description
        - Internal Monologue/Reflection
        - Backstory/Exposition
        - Transition/Travel
        - Meta/Narrative Device (e.g., chapter breaks, author notes if applicable)
        - Other (Use only if none of the above fit well)
    - Provide this as the `topic_category`.

3.  **Provide Reasoning:** Briefly explain your choices for the score and category.

**Output Format:**
{format_instructions}
"""

prompt = ChatPromptTemplate.from_template(
    template=prompt_template,
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

# LLM Instantiation and Chain (to be done in main after args are parsed)
# llm = ChatOpenAI(model=args.llm_model, temperature=0.1)
# refinement_chain = prompt | llm | parser

# --- End LLM Setup Components ---

# --- Topic-to-Theta Mapping (Plan Section 3.4) ---
TOPIC_TO_THETA_MAP = {
    "Character Introduction/Description": np.radians(0),
    "Character Interaction/Dialogue": np.radians(45),
    "Plot Development/Action Sequence": np.radians(90),
    "World Building/Setting Description": np.radians(135),
    "Internal Monologue/Reflection": np.radians(180),
    "Backstory/Exposition": np.radians(225),
    "Transition/Travel": np.radians(270),
    "Meta/Narrative Device": np.radians(315),
    "Other": np.radians(359) # Default slightly off 0
}

def get_theta_for_topic(topic: str) -> float:
    return TOPIC_TO_THETA_MAP.get(topic, TOPIC_TO_THETA_MAP["Other"]) # Default to 'Other' angle
# --- End Topic-to-Theta Mapping ---


def parse_args():
    parser = argparse.ArgumentParser(description='Refine Narrative Atlas coordinates using LLM.')
    parser.add_argument('--storage-path', type=str, required=True,
                        help='Path to the existing Narrative Atlas storage directory (e.g., output/db)')
    parser.add_argument('--output-storage-path', type=str, default=None,
                        help='Optional: Path to save the refined atlas nodes pkl (defaults to overwriting storage-path)')
    parser.add_argument('--llm-model', type=str, default='gpt-4o-mini', # Use a cost-effective model
                        help='Name of the LLM model to use (e.g., gpt-4o-mini, gpt-3.5-turbo)')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='Number of nodes to process before potentially saving intermediate results (optional)')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Node index to start processing from (for resuming)')
    parser.add_argument('--max-nodes', type=int, default=None,
                        help='Maximum number of nodes to process in this run')
    # Add API key arguments or rely solely on environment variables
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("Starting coordinate refinement process...")
    logger.info(f"Arguments: {args}")

    # Load Existing Atlas
    logger.info(f"Loading Narrative Atlas from: {args.storage_path}")
    # Need an embedding service instance just to initialize NarrativeAtlas
    # Use mock or the service used during ingestion if dimensions need to match loading process
    embedding_service = create_embedding_service(service_type=os.getenv('EMBEDDING_SERVICE_TYPE', 'mock'))
    try:
        narrative_atlas = NarrativeAtlas(
            storage_path=args.storage_path,
            embedding_service=embedding_service
        )
        logger.info(f"Loaded atlas with {len(narrative_atlas.db.nodes)} nodes.")
    except Exception as e:
        logger.error(f"Failed to load NarrativeAtlas: {e}", exc_info=True)
        sys.exit(1)

    # Initialize LLM and Chain here, using parsed args
    logger.info(f"Initializing LLM: {args.llm_model}")
    llm = ChatOpenAI(model=args.llm_model, temperature=0.1) # Low temp for consistency
    refinement_chain = prompt | llm | parser
    logger.info("LLM and refinement chain initialized.")

    # --- Node Iteration and Processing (Plan Section 3.5) ---
    node_ids = list(narrative_atlas.db.nodes.keys())
    # Apply start_index and max_nodes slicing *before* creating batches
    start_node_index = args.start_index
    end_node_index = len(node_ids)
    if args.max_nodes is not None:
        end_node_index = min(start_node_index + args.max_nodes, len(node_ids))

    node_ids_to_process = node_ids[start_node_index:end_node_index]

    processed_count = 0
    updated_count = 0
    errors_count = 0
    start_time_proc = time.time()

    logger.info(f"Starting batch processing for {len(node_ids_to_process)} nodes (Index {start_node_index} to {end_node_index - 1}). Batch size: {args.batch_size}")

    # Process nodes in batches
    for i in range(0, len(node_ids_to_process), args.batch_size):
        batch_node_ids = node_ids_to_process[i : i + args.batch_size]
        batch_inputs = []
        batch_nodes_valid = [] # Keep track of valid nodes for this batch

        logger.info(f"Processing batch {i // args.batch_size + 1}: Nodes {start_node_index + i} to {start_node_index + i + len(batch_node_ids) - 1}")

        # 1. Prepare inputs for the current batch
        for node_id in batch_node_ids:
            actual_index = node_ids.index(node_id) # Get original index for logging
            node = narrative_atlas.db.nodes.get(node_id)

            # Check node validity
            is_valid_node = (node is not None and
                             hasattr(node, 'id') and
                             hasattr(node, 'content') and
                             isinstance(node.content, dict) and
                             hasattr(node, 'metadata') and
                             hasattr(node, 'coordinates'))

            if not is_valid_node:
                invalid_id = getattr(node, 'id', node_id)
                logger.warning(f"[{actual_index + 1}/{len(node_ids)}] Skipping invalid node data for ID: {invalid_id} (Object: {node})")
                errors_count += 1
                continue

            # Prepare input data if node is valid
            metadata = node.metadata or {}
            coordinates = node.coordinates or {}
            input_data = {
                "page_number": metadata.get("page_number", "N/A"),
                "chunk_index_on_page": metadata.get("chunk_index", "N/A"),
                "total_chunks_on_page": metadata.get("total_chunks_on_page", "N/A"),
                "keywords": metadata.get("keywords", []), # Assuming keywords is a list
                "t_coord": coordinates.get("t", "N/A"),
                "z_coord": coordinates.get("z", "N/A"),
                "node_content": node.content.get("text", "") if node.content else ""
            }
            batch_inputs.append(input_data)
            batch_nodes_valid.append(node) # Store the valid node object

        # Skip batch if no valid nodes were found
        if not batch_inputs:
            logger.info("Skipping empty batch.")
            continue

        # 2. Call the LLM refinement chain in batch
        try:
            start_time_batch_llm = time.time()
            # Use refinement_chain.batch() instead of invoke()
            # The `config` argument can specify how errors are handled, e.g., return exceptions
            batch_results = refinement_chain.batch(batch_inputs, config={"return_exceptions": True})
            batch_llm_time = time.time() - start_time_batch_llm
            logger.info(f"Batch LLM call completed in {batch_llm_time:.2f}s for {len(batch_inputs)} nodes.")

            # 3. Process the results for the batch
            for node, result in zip(batch_nodes_valid, batch_results):
                actual_index = node_ids.index(node.id) # Get original index for logging
                processed_count += 1

                # Check if the result for this node is an exception
                if isinstance(result, Exception):
                    logger.error(f"[{actual_index + 1}/{len(node_ids)}] Error processing node {node.id} in batch: {result}", exc_info=(isinstance(result, OutputParserException)))
                    errors_count += 1
                    continue

                # Process successful result
                try:
                    new_r = result.relevance_score
                    topic = result.topic_category
                    new_theta = get_theta_for_topic(topic)

                    # Update the node's coordinates dictionary
                    if node.coordinates is None:
                        node.coordinates = {}
                    node.coordinates['r'] = new_r
                    node.coordinates['theta'] = new_theta

                    logger.info(f"[{actual_index + 1}/{len(node_ids)}] Updated node {node.id}: r={new_r:.2f}, theta={np.degrees(new_theta):.1f} ({topic}).")
                    if result.reasoning:
                        logger.debug(f"Reasoning: {result.reasoning}")
                    updated_count += 1
                except Exception as e: # Catch potential errors accessing result attributes
                    logger.error(f"[{actual_index + 1}/{len(node_ids)}] Error processing successful LLM result for node {node.id}: {e}")
                    logger.debug(f"LLM Result object: {result}") # Log the problematic result object
                    errors_count += 1

        except Exception as e: # Catch errors during the batch call itself
            logger.error(f"Fatal error during batch LLM call for nodes {start_node_index + i} to {start_node_index + i + len(batch_node_ids) - 1}: {e}", exc_info=True)
            # Mark all nodes in this specific batch attempt as errored
            errors_count += len(batch_inputs)

        # Optional: Intermediate saving could be added here if needed, but saving at the end is usually fine.

    # --- End Node Iteration and Processing ---

    # Final Summary
    total_time = time.time() - start_time_proc
    logger.info(f"Processing finished in {total_time:.2f} seconds.")
    logger.info(f"Processed: {processed_count}, Updated: {updated_count}, Errors: {errors_count}")

    # --- Saving Updated Atlas ---
    output_path = args.output_storage_path if args.output_storage_path else args.storage_path
    output_file = os.path.join(output_path, 'spatial_temporal_db.pkl')
    logger.info(f"Attempting to save updated node data to: {output_file}")

    try:
        # We only need to save the nodes dictionary, as NarrativeAtlas reloads it
        nodes_to_save = narrative_atlas.db.nodes
        # Ensure parent directory exists
        Path(output_path).mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            pickle.dump(nodes_to_save, f)
        logger.info(f"Successfully saved updated node data to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save updated node data: {e}", exc_info=True)

    # --- End Saving ---

    logger.info("Coordinate refinement process finished.") 
## Phase 2: LLM Coordinate Refinement - Next Steps Document

**1. Goal:**

*   To enhance the semantic representation within the `NarrativeAtlas` by refining the `r` (relevance) and `theta` (topic/category) coordinates for existing nodes using Large Language Model (LLM) analysis.
*   Phase 1 established the structural backbone (`t` and `z` coordinates). Phase 2 adds semantic depth.

**2. Overall Approach:**

*   Implement a **post-ingestion batch processing script** (`refine_coordinates.py`).
*   This script will load an existing `NarrativeAtlas` (created in Phase 1).
*   It will iterate through the nodes, using an LLM to analyze each node's content and metadata.
*   Based on the LLM's analysis, it will calculate refined `r` and `theta` values.
*   It will update the `coordinates` dictionary within the corresponding `Node` objects in the loaded atlas.
*   Finally, it will save the updated `NarrativeAtlas` (specifically the modified node data in `spatial_temporal_db.pkl`).

**3. Implementation Details (`refine_coordinates.py`):**

*   **3.1. Script Setup:**
    *   **File:** Create `src/refine_coordinates.py`.
    *   **Imports:**
        ```python
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
        ```
    *   **Argument Parsing:**
        ```python
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
        ```
    *   **Logging & Env Vars:** Standard setup.
        ```python
        load_dotenv()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger = logging.getLogger('RefineCoordinates')
        ```

*   **3.2. Load Existing Atlas:**
    ```python
    # In main function after parsing args:
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
    ```

*   **3.3. LLM Setup:**
    *   **Pydantic Output Schema:** Define the desired structure for the LLM's response.
        ```python
        class CoordinateRefinementOutput(BaseModel):
            relevance_score: float = Field(description="Relevance score (0.0 most relevant, 1.0 least relevant) based on narrative importance.")
            topic_category: str = Field(description="Primary topic category of the text chunk.")
            reasoning: Optional[str] = Field(default=None, description="Brief reasoning for the score and category.")

        # Create the parser
        parser = PydanticOutputParser(pydantic_object=CoordinateRefinementOutput)
        ```
    *   **Prompt Template:** Craft a detailed prompt.
        ```python
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
        ```
    *   **LLM Instantiation:**
        ```python
        llm = ChatOpenAI(model=args.llm_model, temperature=0.1) # Low temp for consistency
        refinement_chain = prompt | llm | parser
        ```

*   **3.4. Topic-to-Theta Mapping:** Define the mapping.
    ```python
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
    ```

*   **3.5. Node Iteration and Processing:**
    ```python
    # In main function:
    node_ids = list(narrative_atlas.db.nodes.keys())
    nodes_to_process = node_ids[args.start_index:]
    if args.max_nodes is not None:
        nodes_to_process = nodes_to_process[:args.max_nodes]

    processed_count = 0
    errors_count = 0
    start_time_proc = time.time()

    for i, node_id in enumerate(nodes_to_process):
        actual_index = args.start_index + i
        logger.info(f"Processing node {actual_index + 1}/{len(node_ids)}: {node_id}")
        node = narrative_atlas.db.nodes.get(node_id)

        if not node or not isinstance(node, Node):
            logger.warning(f"Skipping invalid node data for ID: {node_id}")
            continue

        # Prepare input for LLM
        try:
            content_text = node.content.get('text', '')
            if not content_text:
                 logger.warning(f"Node {node_id} has no text content. Skipping refinement.")
                 continue

            input_data = {
                "node_content": content_text,
                "page_number": node.metadata.get('page_number', 'N/A'),
                "chunk_index_on_page": node.metadata.get('chunk_index_on_page', 'N/A'),
                "total_chunks_on_page": node.metadata.get('total_chunks_on_page', 'N/A'),
                "keywords": ", ".join(node.keywords) if node.keywords else "None",
                "t_coord": node.coordinates.get('t', 'N/A'),
                "z_coord": node.coordinates.get('z', 'N/A')
            }

            # Invoke LLM Chain
            llm_response = refinement_chain.invoke(input_data)

            # Validate and Update Node Coordinates
            if isinstance(llm_response, CoordinateRefinementOutput):
                new_r = max(0.0, min(1.0, llm_response.relevance_score)) # Clamp score
                new_theta = get_theta_for_topic(llm_response.topic_category)

                # --- Direct Update in the dictionary ---
                node.coordinates['r'] = new_r
                node.coordinates['theta'] = new_theta
                # Optionally add LLM reasoning to metadata if desired
                # node.metadata['refinement_reasoning'] = llm_response.reasoning
                # node.metadata['refinement_topic'] = llm_response.topic_category
                # --- End Direct Update ---

                logger.debug(f"Updated node {node_id}: r={new_r:.2f}, theta={new_theta:.2f} (Topic: {llm_response.topic_category})")
                processed_count += 1

            else:
                 logger.error(f"LLM response for node {node_id} was not the expected Pydantic object: {llm_response}")
                 errors_count += 1

        except OutputParserException as ope:
            logger.error(f"Output parsing failed for node {node_id}: {ope}", exc_info=False) # Avoid huge tracebacks for parsing errors
            errors_count += 1
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}", exc_info=True)
            errors_count += 1
            # Optional: Add delay and retry logic for transient API errors

        # Optional: Intermediate save based on batch size
        if args.batch_size > 0 and (i + 1) % args.batch_size == 0:
            logger.info(f"Processed batch of {args.batch_size}. Saving intermediate results...")
            db_path = os.path.join(args.storage_path, "spatial_temporal_db.pkl")
            try:
                with open(db_path, 'wb') as f:
                     pickle.dump(narrative_atlas.db.nodes, f)
                logger.info(f"Intermediate nodes saved to {db_path}")
            except Exception as e:
                logger.error(f"Failed to save intermediate nodes: {e}", exc_info=True)

    # Final summary
    end_time_proc = time.time()
    logger.info(f"Coordinate refinement completed in {end_time_proc - start_time_proc:.2f} seconds.")
    logger.info(f"Successfully processed: {processed_count} nodes.")
    logger.info(f"Errors encountered: {errors_count} nodes.")
    ```

*   **3.6. Save Final Atlas Nodes:**
    ```python
    # In main function, after loop:
    final_save_path = args.output_storage_path if args.output_storage_path else args.storage_path
    final_db_path = os.path.join(final_save_path, "spatial_temporal_db.pkl")
    logger.info(f"Saving final refined Narrative Atlas nodes to {final_db_path}...")
    try:
        # Overwrite the node database pickle file
        with open(final_db_path, 'wb') as f:
            pickle.dump(narrative_atlas.db.nodes, f)
        # Note: FAISS index and ID maps are NOT updated here, only node coordinates.
        logger.info("Final refined atlas node data saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save final Narrative Atlas nodes: {e}", exc_info=True)
    ```

**4. Key Considerations & Refinements:**

*   **Cost/Time:** This process will be slow and potentially expensive due to LLM calls for each node. Use efficient models (e.g., `gpt-4o-mini`), consider batching if the LLM API allows, and test on a small subset first (`--max-nodes`).
*   **Relevance (`r`) Prompting:** The definition of "relevance" needs careful crafting in the prompt. Start simple, perhaps focusing only on `theta` refinement initially.
*   **Theta Mapping:** The predefined `TOPIC_TO_THETA_MAP` provides stability. Decide how to handle the "Other" category or unexpected LLM outputs.
*   **Error Handling:** Implement robust error handling for LLM API calls (e.g., retries for rate limits) and output parsing.
*   **Idempotency:** The script should ideally be runnable multiple times. The current update logic overwrites existing `r` and `theta`, which achieves this.
*   **Saving:** Ensure the updated `db.nodes` dictionary is correctly saved back to `spatial_temporal_db.pkl`, overwriting the previous version. The FAISS index and ID maps don't need saving as they weren't modified. 
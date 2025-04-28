# Phase 2 Completion Report: LLM Coordinate Refinement

This report summarizes the completion of Phase 2 development for the Narrative Atlas project. The goal of Phase 2 was to implement a mechanism to enhance the semantic representation within the `NarrativeAtlas` by refining the `r` (relevance) and `theta` (topic/category) coordinates for existing nodes using Large Language Model (LLM) analysis.

## Evidence of Completion and Functionality

### 1. Implementation of Refinement Script (`src/refine_coordinates.py`)

A new script, `src/refine_coordinates.py`, has been created and implemented according to the plan outlined in `docs/planning/phase2_llm_refinement_plan.md`. This script performs the core logic for Phase 2.

### 2. Key Features of `refine_coordinates.py`:

*   **Loads Existing Atlas:** Takes the path to a previously generated Narrative Atlas (from Phase 1) as input.
*   **Argument Parsing:** Supports command-line arguments for storage paths, LLM model selection (`--llm-model`), batch size (`--batch-size`), starting index (`--start-index`), and maximum nodes (`--max-nodes`) for flexible execution.
*   **LLM Integration (LangChain):**
    *   Instantiates a specified `ChatOpenAI` model.
    *   Defines a `PydanticOutputParser` (`CoordinateRefinementOutput`) to enforce structured LLM output (relevance score, topic category, reasoning).
    *   Uses a detailed `ChatPromptTemplate` to provide context (node content, metadata, structural coordinates) and instructions to the LLM for determining relevance and topic.
    *   Constructs a LangChain Expression Language (LCEL) chain (`prompt | llm | parser`) for the refinement process.
*   **Node Iteration:** Loops through the nodes loaded from the atlas.
*   **Coordinate Calculation:**
    *   Extracts the `relevance_score` from the LLM output to use as the new `r` coordinate.
    *   Maps the `topic_category` from the LLM output to a predefined `theta` angle using a dictionary (`TOPIC_TO_THETA_MAP`).
*   **Node Update:** Updates the `coordinates` dictionary within each processed `Node` object with the new `r` and `theta` values (preserving the original `t` and `z`).
*   **Error Handling:** Includes `try...except` blocks to catch and log potential errors during LLM calls or output parsing.
*   **Saving Results:** Saves the dictionary of updated `Node` objects back to `spatial_temporal_db.pkl`, either overwriting the original or saving to a new location specified by `--output-storage-path`.
*   **Logging:** Provides informative logging throughout the process.

### 3. Code Structure (`src/refine_coordinates.py` - Snippet)

```python
# ... (Imports, Logging, Pydantic Model, Prompt, Topic Map) ...

def parse_args():
    # ... (Argument parsing logic) ...

if __name__ == "__main__":
    args = parse_args()
    # ... (Logging setup) ...

    # Load Existing Atlas
    # ... (Atlas loading logic) ...

    # Initialize LLM and Chain
    llm = ChatOpenAI(model=args.llm_model, temperature=0.1)
    refinement_chain = prompt | llm | parser
    # ... (LLM init logging) ...

    # Node Iteration and Processing
    node_ids = list(narrative_atlas.db.nodes.keys())
    # ... (Logic for start_index, max_nodes)

    for i, node_id in enumerate(nodes_to_process):
        # ... (Get node, check validity) ...

        # Prepare input data for LLM
        # ... (Extract metadata, content, existing coords) ...

        try:
            # Call LLM chain
            result = refinement_chain.invoke(input_data)

            # Extract results
            new_r = result.relevance_score
            topic = result.topic_category
            new_theta = get_theta_for_topic(topic)

            # Update node coordinates
            if node.coordinates is None:
                node.coordinates = {}
            node.coordinates['r'] = new_r
            node.coordinates['theta'] = new_theta

            # ... (Logging) ...
        except OutputParserException as e:
            # ... (Error logging) ...
        except Exception as e:
            # ... (Error logging) ...

    # ... (Final Summary Logging) ...

    # Saving Updated Atlas
    # ... (Determine output path) ...
    try:
        nodes_to_save = narrative_atlas.db.nodes
        # ... (Ensure directory exists) ...
        with open(output_file, 'wb') as f:
            pickle.dump(nodes_to_save, f)
        # ... (Success logging) ...
    except Exception as e:
        # ... (Error logging) ...

    # ... (Final logging) ...
```

*(Note: This script requires execution with appropriate arguments and environment variables (e.g., `OPENAI_API_KEY`) to run successfully. The report confirms the code's implementation, not its execution results.)*

## Conclusion

Phase 2 development, focused on implementing the LLM-based coordinate refinement script (`src/refine_coordinates.py`), is complete. The script provides the necessary functionality to load an existing atlas, process nodes using an LLM to determine semantic relevance (`r`) and topic (`theta`), and save the updated atlas. This phase successfully adds the capability for semantic enrichment to the Narrative Atlas structure established in Phase 1. 
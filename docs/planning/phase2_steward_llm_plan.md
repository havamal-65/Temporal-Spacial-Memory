# Feature Plan Phase 2: Steward LLM for Structural Reconfiguration

**Date:** 2024-07-26 <!-- Update date as needed -->

**Status:** Planned

**Related Plan:** [Feature Plan 002: Flexible Z Coordinate](./feature_plan_002_flexible_z_coordinate.md)

## 1. Goal

Implement a "Steward LLM" process within the ingestion pipeline. This process will run after the initial chunking and per-chunk structural analysis (Phase 1). Its purpose is to analyze the structural assignments (`z`, `z_type`) across a larger context (e.g., the entire document or significant sections) and potentially reconfigure or refine these assignments based on global patterns, inconsistencies, or a more holistic understanding of the narrative structure. This aims to improve the accuracy and consistency of the structural representation in the Narrative Atlas.

## 2. Rationale

- **Global Context:** Phase 1 analysis is local to each chunk. A global view can identify larger patterns (e.g., consistent perspectives, overall document sections) that local analysis might miss or misinterpret.
- **Consistency:** Ensure that similar structures are assigned consistent `z`/`z_type` values throughout the document.
- **Error Correction:** Correct potential errors or suboptimal assignments made by the Phase 1 local analysis LLM.
- **Richer Representation:** Enable a more accurate and nuanced structural model of the document, improving subsequent filtering and querying.

## 3. Proposed Implementation Strategy (High-Level)

1.  **Trigger Point:** Determine when the Steward LLM process runs. Options:
    *   After all chunks for a *single document* have been processed by Phase 1 but *before* final saving/committing. (Most likely)
    *   As a separate, post-ingestion batch process. (Less integrated)
2.  **Context Gathering:** How does the Steward LLM get the necessary global context?
    *   Collect all chunk texts and their Phase 1 structural metadata (`structural_perspective`, `structural_layer_type`, etc., and the initially assigned `z`/`z_type`) for the document.
    *   Potentially summarize or sample the chunk data if the full text exceeds LLM context limits.
3.  **Steward LLM Prompting:** Design the prompt for the Steward LLM.
    *   Provide the collected context (Phase 1 outputs, potentially summarized text).
    *   Instruct the LLM to identify global patterns, inconsistencies, or necessary refinements.
    *   Define the desired output schema: This could be a list of updates, mapping old `z`/`z_type` to new ones, or identifying specific nodes needing changes.
4.  **Applying Reconfiguration:** How are the Steward LLM's recommendations applied?
    *   Parse the Steward LLM's output.
    *   Iterate through the affected nodes (stored temporarily or retrieved from the `NarrativeAtlas` instance).
    *   Update the `PolarTemporalCoordinate` (`z`, `z_type`) for each relevant node.
    *   **Crucially:** Update the corresponding metadata (`coord_z`, `coord_z_type`) stored in the FAISS docstore (`_add_or_update_embedding` might need modification or a new method for batch updates).

## 4. Potential Codebase Changes

-   **`src/services/ingestion_pipeline.py` (`IngestionPipeline`):**
    *   Add logic to collect Phase 1 results for a document.
    *   Instantiate and configure the Steward LLM (potentially a different model/prompt than Phase 1).
    *   Add a new method (e.g., `_run_steward_reconfiguration`) called at the appropriate point in `ingest_document`.
    *   Implement logic to apply the Steward LLM's output, potentially calling methods on `NarrativeAtlas` to update nodes.
-   **`src/models/narrative_atlas.py` (`NarrativeAtlas`):**
    *   May need a new method to efficiently update coordinates and associated metadata for multiple nodes based on Steward LLM output (e.g., `batch_update_coordinates(updates: List[Tuple[str, PolarTemporalCoordinate]])`). This method would need to update both `self.db.nodes` and the FAISS `docstore` metadata.
-   **New Module/Utilities (Optional):**
    *   A dedicated `StewardAnalyzer` class could encapsulate the LLM interaction, context preparation, and output parsing logic.

## 5. Open Questions & Design Decisions

-   **Steward LLM Model Choice:** Decision: Use OpenAI's `gpt-4o` model, leveraging the existing API key setup. It offers a large context window (128k tokens) and strong reasoning capabilities suitable for global analysis.
-   **Context Window Handling:** Decision: Use a Map-Reduce style approach. Combine Phase 1 structural metadata for all chunks. If needed (i.e., combined metadata exceeds context window), summarize this *metadata overview* before passing to the Steward LLM. Consider enhancing the overview with keywords or brief text snippets for better context if needed.
-   **Output Schema & Parsing:** Decision: Use structured JSON output from the Steward LLM (`gpt-4o`), specifying a list of updates, each containing `node_id` and `new_coordinates` (including refined `z` and `z_type`). Example:
    ```json
    {
      "updates": [
        {"node_id": "...", "new_coordinates": {"r": ..., "theta": ..., "t": ..., "z": ..., "z_type": "..."}},
        ...
      ]
    }
    ```
-   **Triggering and Granularity:** Decision: Run reconfiguration per-document, after all Phase 1 chunk processing is complete for that document, before the final save.
-   **Update Efficiency:** Investigation Required: Verify if `FAISS.docstore.add` efficiently handles updates to existing keys in the `InMemoryDocstore`. Plan: If yes, use iterative updates. If no, implement a `batch_update_coordinates` method in `NarrativeAtlas` to handle updates more efficiently.
-   **Complexity vs. Benefit:** Decision: Defer evaluation until after Phase 2 implementation.
-   **Error Handling:** Decision: Implement robust logging. On Steward LLM failure (API error, invalid output), skip the reconfiguration step for the affected document (use Phase 1 results as fallback). Implement retries for transient LLM API errors.

## 6. Next Steps (Planning)

-   Refine the implementation strategy based on answers to open questions.
-   Detail the required code changes in each module.
-   Define the specific prompts and LLM output schemas.
-   Consider evaluation metrics for Phase 2 effectiveness. 
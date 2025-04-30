# Phase 3 Plan: Querying Mechanisms

Date: 2025-04-28

## 1. Goal

Develop and implement querying functionalities for the Narrative Atlas that leverage the refined semantic coordinates (r, theta) alongside the existing structural (t, z) and vector (embedding) information. This phase focuses on enabling coordinate-based filtering via natural language queries.

## 2. Background & Reviewed Snippets

- Phase 1 established the structural backbone (t, z) and basic vector search (`src/narrative_atlas.py`, `src/query.py`).
- Phase 2 added LLM-refined semantic coordinates (r - relevance, theta - topic).
- Reviewed snippets (`4D Polar-Temporal Coordinate Claude Code Snippets/`) provide complex examples of coordinate definition, NL parsing (regex), FAISS integration (filter-then-search), hybrid relevance calculation, and advanced angular mapping. We will adopt the core concepts but simplify the initial implementation.

## 3. Proposed Querying Capabilities (Phase 3 Scope)

*   **Must-Haves:**
    1.  **LLM-Powered Natural Language Query Parsing:** Implement a parser using an LLM (e.g., via function calling or structured output tools) to extract:
        *   Core semantic concept(s) for vector search.
        *   Coordinate constraints (`r`, `theta`, `t`, `z`) based on natural language descriptions (e.g., "highly relevant nodes about 'machine learning' from last month in the technical context").
        ```python
        # Conceptual Example of NL Parser Output
        # Input: "Find highly relevant technical documents about machine learning from last month"
        parsed_query = {
            "query_text": "machine learning", # For vector search
            "filters": {
                "r_max": 0.5, # Example threshold for "highly relevant"
                "theta_topic": "machine learning", # To be mapped to angle range later
                "t_min": datetime.now().timestamp() - 30*86400, # Example timestamp
                "t_max": datetime.now().timestamp(),
                "z": 1 # Example layer for "technical"
            },
            "limit": 10 # Default or parsed limit
        }
        ```
    2.  **Coordinate Filtering:** Filter search results based on the parsed coordinate constraints. This will use the static `r`, `theta`, `t`, `z` values associated with each node (ingested in Phase 2 or stored alongside).
    3.  **Combined Filtering:** Support simultaneous filtering across multiple coordinate dimensions specified in the NL query.
    4.  **Filter-then-Search:** Implement the search logic where coordinate filtering happens *before* the final (potentially reduced) set of IDs are passed to FAISS for vector similarity ranking.

*   **Deferred (Nice-to-Haves for Future Phases):**
    *   Complex hybrid relevance calculations (semantic + graph + temporal).
    *   Advanced/dynamic angular mapping strategies (LDA, Hierarchy).
    *   Explicit graph-based querying or temporal relevance weighting.
    *   Coordinate-based navigation (`navigate` functionality).
    *   User-defined weighting of coordinate importance.

## 4. Implementation Plan (Phase 3)

*(Detailed steps for implementing the capabilities defined above)*

1.  **Setup Environment Configuration:**
    *   Create a `.env` file in the project root.
    *   Add necessary environment variables (e.g., `OPENAI_API_KEY` for the LLM parser).
    *   Add `.env` to `.gitignore`.
    *   Integrate `python-dotenv` (`load_dotenv()`) into the application entry points (e.g., `run.py`, `server.py`, potentially `src/query.py`) to load these variables.
2.  **Define Coordinate Representation:**
    *   Introduce a clear way to represent the 4D coordinates. Either:
        *   Adapt the `PolarTemporalCoordinate` class from the snippet (`core-coordinate-system.py`) and place it in `src/coordinates.py` (or similar).
        *   Or use simple tuples/dictionaries within `NarrativeAtlas` if the class feels too heavy initially.
    *   *Decision:* Start with adapting the `PolarTemporalCoordinate` class for clarity and potential future use of its methods (like distance, though not strictly needed for filtering).
3.  **Adapt Storage for Coordinates:**
    *   Modify `NarrativeAtlas.add_node` (and underlying `SpatialTemporalDB` if necessary) to accept and store `r`, `theta`, `t`, `z` coordinates alongside content and embeddings.
    *   *Decision:* Store coordinates as **metadata** associated with the FAISS index ID, similar to the `faiss-integration.py` snippet's approach. This avoids needing a separate database structure for coordinates initially, but acknowledge potential performance limitations for filtering large datasets (address in testing/future phases).
    ```python
    # Conceptual Change in NarrativeAtlas / FaissAdapter
    # self.faiss_adapter.add_item_with_coordinates(
    #    item_id=node_id,
    #    embedding=embedding,
    #    r=r_coord, # From Phase 2
    #    theta=theta_coord, # From Phase 2
    #    t=t_coord, # From Phase 1/Ingestion
    #    z=z_coord, # From Phase 1/Ingestion
    #    metadata={'r': r_coord, 'theta': theta_coord, 't': t_coord, 'z': z_coord, 'content_preview': ...}
    # )
    ```
4.  **Implement LLM-Based NL Parser:**
    *   Create a new module, e.g., `src/nl_parser.py`.
    *   Use an LLM (e.g., OpenAI's API via Langchain or direct calls) with function calling/structured output capabilities.
    *   Define the desired output schema (like the conceptual example in Section 3).
    *   Develop prompts to guide the LLM to extract the core query and coordinate constraints (`r`, `theta`, `t`, `z`) from the natural language input.
    *   Handle mapping of textual topic descriptions (e.g., "machine learning") to target `theta` values or ranges (initially, this might involve a simple lookup or perhaps another LLM call if the `AngularMapper` logic is too complex for now).
5.  **Implement Coordinate Filtering Logic:**
    *   In `NarrativeAtlas` (or an adapted `FaissPolarTemporalAdapter`), implement methods to filter item IDs based on coordinate ranges stored in metadata (similar to `get_items_in_..._range` methods in `faiss-integration.py`). Ensure efficient handling of angular wrap-around for `theta`.
6.  **Implement Filter-then-Search in `NarrativeAtlas`:**
    *   Create a new search method (e.g., `search_with_nl_query`) or modify the existing `search` method.
    *   This method will:
        *   Call the NL Parser (Step 4) to get structured query parameters.
        *   Use the coordinate filtering logic (Step 5) to get a candidate set of item IDs matching the `r`, `theta`, `t`, `z` constraints.
        *   Perform a FAISS vector search using the core `query_text` embedding, but *restricted to the candidate set of IDs*.
        *   Return the top `k` results from the restricted FAISS search.
    ```python
    # Conceptual Flow in NarrativeAtlas.search_with_nl_query
    # 1. parsed_params = self.nl_parser.parse(nl_query_text)
    # 2. query_embedding = self.embedding_service.get_embedding(parsed_params['query_text'])
    # 3. candidate_ids = self.coordinate_filter.get_ids_matching_constraints(parsed_params['filters'])
    # 4. final_results = self.faiss_adapter.search_within_ids(query_embedding, candidate_ids, k=parsed_params['limit'])
    # 5. return self._format_results(final_results)
    ```
7.  **Update Query Interface (`src/query.py`):**
    *   Modify the script to accept a natural language query string instead of just a keyword.
    *   Call the new `NarrativeAtlas.search_with_nl_query` method.
    *   Display the results.
8.  **Testing:**
    *   Add unit tests for the NL parser (mocking LLM calls).
    *   Add unit tests for coordinate storage and filtering logic.
    *   Add integration tests for the end-to-end NL query process via `src/query.py`.

## 5. Potential Challenges

*   **NL Parser Accuracy/Robustness:** Ensuring the LLM parser correctly interprets various NL inputs and extracts constraints reliably. Prompt engineering will be key.
*   **Coordinate Filtering Performance:** Filtering based on metadata iteration might become slow with very large datasets. May need optimization (e.g., secondary indexing) in later phases.
*   **Theta Mapping:** Mapping arbitrary text topics to `theta` values/ranges effectively without the full `AngularMapper` complexity might require careful design (e.g., prompt design for the parser LLM, or a simple pre-defined topic-to-angle map).
*   Balancing vector similarity score with the hard coordinate filters.

## 6. Success Criteria

*   `NarrativeAtlas` stores and retrieves 4D coordinates for nodes via metadata.
*   A natural language query can be processed via `src/query.py`.
*   The NL parser successfully extracts core concepts and coordinate constraints (`r`, `theta`, `t`, `z`).
*   Search results are demonstrably filtered based on the extracted coordinate constraints before FAISS ranking.
*   End-to-end querying from NL input to filtered results is functional.

## 7. Instructions for Next Session (Phase 3 Kick-off)

*   **Goal:** Begin implementation of Phase 3 based on the plan above.
*   **Starting Point:** The current state of the codebase after Phase 2 completion.
*   **Context:** This finalized plan document (`docs/planning/phase3_querying_mechanisms_plan.md`).
*   **First Steps:**
    1.  Implement Step 1: Setup `.env` file, add to `.gitignore`, integrate `python-dotenv`.
    2.  Implement Step 2: Create `src/coordinates.py` with the `PolarTemporalCoordinate` class (adapted from the snippet).
    3.  Begin Step 3: Modify `NarrativeAtlas` and `SpatialTemporalDB` (if needed) to handle storage of coordinates as metadata. Add coordinate parameters to `add_node`. 
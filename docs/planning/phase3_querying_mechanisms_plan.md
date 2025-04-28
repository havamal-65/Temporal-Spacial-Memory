# Phase 3 Plan: Querying Mechanisms

Date: 2025-04-28

## 1. Goal

Develop and implement querying functionalities for the Narrative Atlas that leverage the refined semantic coordinates (r, theta) alongside the existing structural (t, z) and vector (embedding) information.

## 2. Background

- Phase 1 established the structural backbone (t, z) and basic vector search.
- Phase 2 added LLM-refined semantic coordinates (r - relevance, theta - topic).
- The `src/query.py` script currently handles basic vector similarity search.
- The `NarrativeAtlas` class manages node storage (`SpatialTemporalDB`) and the FAISS index.

## 3. Proposed Querying Capabilities

*(To be detailed - brainstorm potential query types)*

*   Query by semantic topic (theta ranges).
*   Query by relevance (r thresholds).
*   Query by time range (t).
*   Combined queries (e.g., find relevant nodes on topic X within a specific time window).
*   Nearest neighbor search filtered/weighted by semantic coordinates.
*   Ability to specify coordinate importance/weighting in queries.
*   ... (add more ideas)

## 4. Implementation Plan

*(To be detailed - outline steps for modifying code)*

1.  **Review `src/query.py` and `NarrativeAtlas`:** Identify integration points for coordinate-based filtering/ranking.
2.  **Design Coordinate Filtering Logic:** Determine how to efficiently filter nodes based on r, theta, t, z ranges.
3.  **Modify `NarrativeAtlas.search()`:** Update the search method (or add new methods) to accept coordinate constraints.
    *   Option A: Pre-filter nodes by coordinates before FAISS search.
    *   Option B: Post-filter FAISS results based on coordinates.
    *   Option C: Explore weighting results based on coordinate proximity.
4.  **Update `src/query.py`:** Modify the script to accept new command-line arguments for coordinate-based queries and call the updated `NarrativeAtlas` methods.
5.  **Develop Query Parsing/Interpretation:** (If needed) Create logic to translate user query intents (e.g., "highly relevant dialogue about X") into coordinate constraints.
6.  **Testing:** Add unit/integration tests for the new querying functionalities.

## 5. Potential Challenges

*   Efficiently filtering/querying based on multiple coordinate dimensions.
*   Balancing vector similarity with coordinate filtering.
*   Defining intuitive user interfaces/arguments for complex queries.

## 6. Success Criteria

*   Ability to perform queries filtering by r, theta, and t coordinates individually and in combination.
*   Demonstrable improvement in query relevance/specificity compared to pure vector search.
*   `src/query.py` updated with new query capabilities. 
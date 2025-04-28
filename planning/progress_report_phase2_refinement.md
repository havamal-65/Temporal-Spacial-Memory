# Progress Report: Coordinate Refinement (Phase 2)

Date: 2025-04-27

## Summary

This report details the debugging and enhancement process for the `refine_coordinates.py` script, which is responsible for enriching the Narrative Atlas nodes with semantic coordinates (r, theta) using an LLM.

## Key Activities & Findings

1.  **Initial Errors:** Running the script initially resulted in `Skipping invalid node data` warnings for all nodes.
2.  **Pickle Inspection:** Added temporary debug code to load the `spatial_temporal_db.pkl` directly.
3.  **Root Cause Identified:** Debug logs revealed that the pickled `Node` objects had attribute names `id` and `content` (a dictionary containing `text`), while the script was expecting `node_id` and `text_content`.
4.  **Attribute Correction:** Modified `refine_coordinates.py` to use the correct attribute names (`id`, `content['text']`) when accessing node data.
5.  **Performance Bottleneck:** Identified that sequential LLM calls for each node would be slow.
6.  **Batch Processing Implemented:** Refactored the script to use `refinement_chain.batch()` with a configurable `--batch-size`, significantly improving potential throughput.
7.  **Rate Limiting Encountered:** Running the batch processing with the default size (50) resulted in OpenAI `RateLimitError (429 Too Many Requests)` for the TPM (Tokens Per Minute) limit, preventing full processing. The internal retry mechanism in the OpenAI library was insufficient on its own.
8.  **Partial Success:** The script successfully processed and saved updates for the nodes completed *before* the rate limit was hit.

## Current Status

*   The `refine_coordinates.py` script now correctly loads and identifies nodes from the pickle file created by the ingestion process.
*   Batch processing via LangChain's `.batch()` method is implemented.
*   The script is functional but reliably hits OpenAI rate limits with the current batch size.

## Next Steps

*   Implement a retry mechanism with exponential backoff specifically for `RateLimitError` around the `refinement_chain.batch()` call.
*   Alternatively, experiment with a smaller `--batch-size` argument as a temporary workaround.
*   Once rate limiting is handled, run the script to fully process all nodes and generate the complete set of refined coordinates.
*   Proceed to Phase 3 (Querying and Visualization). 
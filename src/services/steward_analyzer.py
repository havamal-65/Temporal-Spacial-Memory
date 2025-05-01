import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
# import tiktoken # Keep for potential future use, but not primary for map-reduce logic now

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from src.data_models import PolarTemporalCoordinate

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
STEWARD_BATCH_SIZE = 50 # Number of chunk metadata items per batch in Map step
# MAX_CONTEXT_TOKENS = 100_000 # No longer the primary mechanism, Map-Reduce handles size

# --- LLM Output Schema Definitions ---

# Schema for the final "Reduce" step output
class CoordinateUpdate(BaseModel):
    """Defines the structure for a single coordinate update suggested by the Steward LLM."""
    node_id: str = Field(description="The unique identifier of the node to update.")
    new_coordinates: PolarTemporalCoordinate = Field(description="The new PolarTemporalCoordinate values for the node.")

    # Add Pydantic Config to allow the custom PolarTemporalCoordinate type
    class Config:
        arbitrary_types_allowed = True

class StewardUpdates(BaseModel):
    """Defines the overall structure for the list of updates from the Steward LLM."""
    updates: List[CoordinateUpdate] = Field(description="A list of coordinate updates to be applied.")

# Schema for the intermediate "Map" step output
class BatchAnalysisResult(BaseModel):
    """Result of analyzing a single batch of chunk metadata in the Map step."""
    batch_summary: str = Field(description="A concise summary of structural patterns, potential inconsistencies, or notable observations within this batch.")
    potentially_problematic_nodes: List[str] = Field(description="List of node_ids within this batch that might require attention in the final review.", default=[])

# --- Steward Analyzer Class ---
class StewardAnalyzer:
    """
    Analyzes structural assignments (z, z_type) across a document's chunks
    using a Map-Reduce approach with an LLM to identify global patterns and suggest refinements.
    """
    def __init__(self, llm_model: str = "gpt-4o", map_llm_model: Optional[str] = None):
        """
        Initializes the StewardAnalyzer.

        Args:
            llm_model: The name of the OpenAI model for the final Reduce step (default: "gpt-4o").
            map_llm_model: Optional. The name of the model for the Map step. If None, uses llm_model.
        """
        self.reduce_model_name = llm_model
        self.map_model_name = map_llm_model or llm_model # Use reduce model if map not specified
        self.reduce_llm = None
        self.reduce_parser = None
        self.reduce_chain = None
        self.map_llm = None
        self.map_parser = None
        self.map_chain = None # Will hold the chain for the Map step

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Steward analysis will be skipped.")
            return

        try:
            # --- Initialize Reduce Chain (for final analysis) ---
            self.reduce_llm = ChatOpenAI(
                openai_api_key=api_key,
                model=self.reduce_model_name,
                temperature=0.1,
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            self.reduce_parser = JsonOutputParser(pydantic_object=StewardUpdates)
            self.reduce_chain = self.reduce_llm | self.reduce_parser
            logger.info(f"StewardAnalyzer Reduce chain initialized with model: {self.reduce_model_name}")

            # --- Initialize Map Chain (for batch analysis) ---
            # Use a separate parser for the BatchAnalysisResult
            self.map_parser = JsonOutputParser(pydantic_object=BatchAnalysisResult)
            # For now, use the same LLM instance, but could be different
            self.map_llm = ChatOpenAI(
                openai_api_key=api_key,
                model=self.map_model_name,
                temperature=0.2, # Slightly higher temp might be ok for batch summary
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            self.map_chain = self.map_llm | self.map_parser
            logger.info(f"StewardAnalyzer Map chain initialized with model: {self.map_model_name}")

        except Exception as e:
             logger.error(f"Error initializing StewardAnalyzer LLM chains or Parsers: {e}", exc_info=True)
             self.reduce_llm = self.reduce_parser = self.reduce_chain = None
             self.map_llm = self.map_parser = self.map_chain = None

    # --- Map Step ---
    def _create_map_prompt(self, batch_context: List[Dict[str, Any]]) -> List[SystemMessage | HumanMessage]:
        """Creates the prompt for the Map step (analyzing a single batch)."""
        formatted_batch_context = json.dumps(batch_context, indent=2)

        # Updated system prompt to include r and theta analysis
        system_prompt = f"""
You are an assistant analyzing a batch of coordinate metadata (node_id, r, theta, z, z_type) from chunks of a larger document.
Your task is to provide a concise summary of the semantic AND structural patterns observed *within this batch* and identify any node_ids that seem potentially inconsistent or problematic *relative to others in this batch*.
Consider both:
- Semantic relationships: Look at `r` (distance from origin/center) and `theta` (angle). Are there clusters? Outliers? Unexpectedly large/small `r` values? Nodes with similar `theta` that might be related?
- Structural patterns: Look at `z` (layer/perspective) and `z_type` (type). Are there abrupt changes? Inconsistencies? Unusual assignments?

Output ONLY a JSON object adhering to the following schema:

{{
  "batch_summary": "A concise text summary (1-2 sentences) covering BOTH semantic and structural patterns or notable points in this batch.",
  "potentially_problematic_nodes": ["list_of_node_ids", "within_this_batch", "that_warrant_closer_look_semantically_or_structurally"]
}}

{self.map_parser.get_format_instructions()}

Do not suggest final coordinate changes here. Just summarize and flag potential issues for later review based on this batch's context.
"""

        human_prompt_content = f"""
Analyze the following batch of coordinate metadata:

```json
{formatted_batch_context}
```

Provide your analysis in the specified JSON format, considering both semantic (r, theta) and structural (z, z_type) aspects.
"""
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt_content)
        ]

    def _analyze_batch(self, batch_context: List[Dict[str, Any]], batch_number: int) -> Optional[BatchAnalysisResult]:
        """Analyzes a single batch of chunk metadata (Map step)."""
        if not self.map_chain:
            logger.warning("Map chain not initialized. Skipping batch analysis.")
            return None

        logger.debug(f"Analyzing batch {batch_number} ({len(batch_context)} items)...")
        try:
            prompt = self._create_map_prompt(batch_context)
            result = self.map_chain.invoke(prompt)
            logger.debug(f"Batch {batch_number} analysis result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error analyzing batch {batch_number}: {e}", exc_info=True)
            return None # Indicate failure for this batch

    # --- Reduce Step ---
    def _create_reduce_prompt(self, batch_analyses: List[BatchAnalysisResult], original_document_context: List[Dict[str, Any]]) -> List[SystemMessage | HumanMessage]:
        """Creates the prompt for the Reduce step (final global analysis)."""

        # We need the original coordinates to include in the final output,
        # so let's create a quick lookup map.
        original_coords_map = {
            item['node_id']: item['coordinate']
            for item in original_document_context if 'node_id' in item and 'coordinate' in item
        } # This map is less critical now as LLM generates all dynamic coords

        # Dump the list of dictionaries directly, as map_parser seems to return dicts
        formatted_batch_summaries = json.dumps(batch_analyses, indent=2)

        # Updated system prompt for comprehensive coordinate refinement
        system_prompt = f"""
You are the final Steward LLM responsible for analyzing and potentially refining the semantic (r, theta) and structural (z, z_type) coordinates for text chunks from a single document, based on preliminary batch analyses.
You previously analyzed the document chunks in batches, considering both semantic and structural aspects locally. You will now be given the summaries and lists of potentially problematic nodes identified in each batch.
Your goal is to synthesize these batch analyses to perform a GLOBAL refinement of the coordinates (r, theta, z, z_type) for any nodes requiring updates. The 't' coordinate must remain unchanged.

Analyze the provided batch summaries holistically. Consider the following refinement goals:
1.  **Semantic Cohesion (r, theta):**
    *   Identify major themes or topics suggested by the batch summaries and flagged nodes.
    *   Nodes belonging to the same core theme should ideally be positioned closer together. Adjust `r` and `theta` to group related nodes.
    *   Nodes identified as outliers or transitions might need their `r` or `theta` adjusted to reflect their relationship (or lack thereof) to main clusters.
    *   Ensure `r` (distance) and `theta` (angle) reflect the node's semantic role in the global context.
2.  **Structural Consistency (z, z_type):**
    *   Identify consistent structural layers (e.g., main narrative, dialogue, footnotes, technical sections) spanning across batches based on summaries and flagged nodes.
    *   Ensure nodes within the same logical structural layer have consistent `z` and `z_type` values.
    *   Correct any inconsistencies in `z` or `z_type` identified during batch analysis, considering the global structure.

Based on your global synthesis, identify nodes requiring coordinate updates.
Output ONLY a JSON object containing a single key \"updates\".
The value of \"updates\" should be a list of objects. Each object must have:
- \"node_id\": The unique identifier of the node requiring an update.
- \"new_coordinates\": A JSON object representing the complete **NEW** PolarTemporalCoordinate, containing the refined `r`, `theta`, `z`, `z_type` values you determined. You MUST also include the original, unchanged `t` value for completeness. **You must provide all five coordinate fields (r, theta, t, z, z_type).**

{self.reduce_parser.get_format_instructions()}

**Important:** For the \"new_coordinates\", you are defining the final `r`, `theta`, `z`, `z_type`. You will need the original `t` value. For any node you update, assume its original `t` value is `[ORIGINAL_T_VALUE_PLACEHOLDER]`. You must include this placeholder or determine the actual original `t` value based on implicit context if possible, and place it in the `t` field of the `new_coordinates` object.

If no updates are necessary based on your global analysis, return an empty list for \"updates\": {{\"updates\": []}}.
Do not explain your reasoning in the output, only provide the JSON.
"""

        human_prompt_content = f"""
Here are the summaries (covering semantic and structural aspects) and potentially problematic nodes identified from analyzing the document structure in batches:

```json
{formatted_batch_summaries}
```

Please synthesize these findings globally. Determine the final refined coordinates (`r`, `theta`, `z`, `z_type`) for any nodes needing updates.
Provide the necessary updates in the specified JSON format. Remember to include the original `t` value (using the placeholder `[ORIGINAL_T_VALUE_PLACEHOLDER]` or inferring it) in the `new_coordinates` object for each update.
"""
        # We still don't pass the full original context to the LLM to save tokens.
        # The placeholder mechanism for 't' is a workaround because the LLM doesn't have direct access
        # to the original 't' values unless we pass the full context.
        # The actual pipeline code will need to replace this placeholder when applying updates.

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt_content)
        ]

    # Method to replace placeholder 't' values after LLM response
    def _inject_original_t_values(self, steward_result: Dict, original_context: List[Dict[str, Any]]) -> Dict:
        """Replaces placeholder 't' values in the LLM output dictionary with actual original values."""
        # Work directly with the dictionary result from the LLM/parser
        if not steward_result or not isinstance(steward_result, dict):
            logger.warning(f"_inject_original_t_values received invalid input: {steward_result}")
            return steward_result or {} # Return input or empty dict

        updates_list = steward_result.get('updates')
        if not updates_list or not isinstance(updates_list, list):
             logger.debug("No 'updates' list found in steward result dict, or it's not a list.")
             return steward_result # No updates to process or invalid format

        original_t_map = {
            item['node_id']: item.get('coordinate', {}).get('t')
            for item in original_context if 'node_id' in item and 'coordinate' in item
        }

        processed_updates = []
        for update_dict in updates_list:
            if not isinstance(update_dict, dict):
                logger.warning(f"Skipping non-dictionary item in updates list: {update_dict}")
                continue
                
            node_id = update_dict.get('node_id')
            new_coordinates_dict = update_dict.get('new_coordinates')

            if not node_id or not isinstance(new_coordinates_dict, dict):
                logger.warning(f"Skipping update due to missing node_id or invalid new_coordinates: {update_dict}")
                continue

            original_t = original_t_map.get(node_id)
            if original_t is None:
                logger.warning(f"Could not find original 't' value for node {node_id}. Skipping this update.")
                continue # Skip update if original 't' is missing

            # Check if 't' key exists and if it's the placeholder
            current_t = new_coordinates_dict.get('t')
            if current_t == '[ORIGINAL_T_VALUE_PLACEHOLDER]':
                new_coordinates_dict['t'] = original_t # Set the actual t value
                logger.debug(f"Injected original t={original_t} for node {node_id}")
            elif current_t is not None:
                # If 't' exists but isn't the placeholder, log a warning but keep it
                logger.warning(f"LLM provided a 't' value ({current_t}) instead of placeholder for node {node_id}. Using LLM's value, but this is unexpected.")
            else:
                # If 't' key is missing, add it
                new_coordinates_dict['t'] = original_t
                logger.debug(f"Set original t={original_t} for node {node_id} ('t' key was missing)")
            
            # Update the dictionary in the original update object (if needed, but modifying in place)
            update_dict['new_coordinates'] = new_coordinates_dict 
            processed_updates.append(update_dict) # Add the processed dict to the new list

        # Replace the old list with the processed one
        steward_result['updates'] = processed_updates
        return steward_result

    def _reduce_batch_analyses(self, batch_analyses: List[Dict[str, Any]], original_document_context: List[Dict[str, Any]]) -> Optional[Dict]:
        """Combines batch analyses results (dictionaries) to get final coordinate updates (Reduce step). Returns dict."""
        if not self.reduce_chain:
            logger.warning("Reduce chain not initialized. Skipping final analysis.")
            return {"updates": []} # Return empty dict if chain fails

        if not batch_analyses:
             logger.warning("No successful batch analyses results to reduce. Skipping.")
             return {"updates": []}

        logger.info(f"Reducing results from {len(batch_analyses)} batch analyses...")
        try:
            prompt = self._create_reduce_prompt(batch_analyses, original_document_context)
            # Invoke LLM to get potential updates (with placeholder 't')
            llm_result_dict = self.reduce_chain.invoke(prompt) # Result is expected to be a dict
            logger.debug(f"Reduce step LLM raw output (parsed dict): {llm_result_dict}")

            # Ensure llm_result_dict is actually a dict before proceeding
            if not isinstance(llm_result_dict, dict):
                logger.error(f"Reduce step LLM output was not a dictionary: {type(llm_result_dict)}. Cannot inject 't' values.")
                return None # Indicate failure

            # Inject the actual 't' values into the result dictionary
            final_result_dict_with_t = self._inject_original_t_values(llm_result_dict, original_document_context)

            updates_count = len(final_result_dict_with_t.get('updates', []))
            logger.info(f"Reduce step complete. Suggested {updates_count} final updates (with original 't' values injected).")
            return final_result_dict_with_t
        except Exception as e:
            logger.error(f"Error during Reduce step (including t-value injection): {e}", exc_info=True)
            return None # Indicate failure

    # --- Main Orchestration Method ---
    def analyze_and_recommend_updates(self, document_context: List[Dict[str, Any]]) -> Optional[Dict]:
        """
        Analyzes Phase 1 metadata using Map-Reduce and suggests coordinate updates.
        Returns the result as a dictionary conforming to StewardUpdates structure, or None.
        """
        if not document_context:
            logger.warning("Received empty document context for Steward analysis. Skipping.")
            return {"updates": []}

        if not self.map_chain or not self.reduce_chain:
            logger.warning("StewardAnalyzer chains not fully initialized. Skipping analysis.")
            return {"updates": []}

        logger.info(f"Starting Steward Map-Reduce analysis for {len(document_context)} chunks using batch size {STEWARD_BATCH_SIZE}.")

        # --- Prepare simplified context for mapping ---
        simplified_map_context = []
        for item in document_context:
            coords = item.get('coordinate', {}) # Get coordinate dict directly
            simplified_map_context.append({
                "node_id": item.get("node_id"),
                "r": coords.get("r"),         # <-- Include r
                "theta": coords.get("theta"), # <-- Include theta
                "z": coords.get("z"),
                "z_type": coords.get("z_type"),
                # 't' is fixed, no need to pass to steward for analysis
            })

        # --- Map Step ---
        batch_analyses_results: List[Dict] = [] # Expecting list of dicts now
        num_batches = (len(simplified_map_context) + STEWARD_BATCH_SIZE - 1) // STEWARD_BATCH_SIZE
        for i in range(num_batches):
            start_index = i * STEWARD_BATCH_SIZE
            end_index = start_index + STEWARD_BATCH_SIZE
            batch = simplified_map_context[start_index:end_index]
            # _analyze_batch likely returns dict now, even if technically Optional[BatchAnalysisResult]
            # due to how JsonOutputParser handles failures.
            batch_result = self._analyze_batch(batch, batch_number=i + 1)
            if batch_result and isinstance(batch_result, dict): # Ensure it's a dict
                batch_analyses_results.append(batch_result)
            else:
                logger.warning(f"Batch {i+1} analysis failed or returned non-dict: {batch_result}. Excluding from Reduce step.")

        # --- Reduce Step ---
        if not batch_analyses_results:
            logger.warning("No successful batch analyses were completed. Steward analysis cannot proceed.")
            return {"updates": []}

        # Pass the original context to reduce step
        # _reduce_batch_analyses now returns Optional[Dict]
        final_result_dict = self._reduce_batch_analyses(batch_analyses_results, document_context)

        if final_result_dict is None:
             logger.error("Steward Reduce step failed.")
             return None # Propagate failure

        logger.info("Steward Map-Reduce analysis finished.")
        return final_result_dict

    # --- Helper methods like _get_token_count can be removed or kept for debugging ---
    # def _get_token_count(self, text: str) -> int: ...
    # def _simplify_context(self, document_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]: ... # No longer used directly by analyze_and_recommend_updates
    # def _create_prompt(self, document_context: List[Dict[str, Any]]) -> List[SystemMessage | HumanMessage]: ... # Replaced by map/reduce prompts 
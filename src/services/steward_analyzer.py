import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import tiktoken

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from src.coordinates import PolarTemporalCoordinate

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- LLM Output Schema Definition ---
class CoordinateUpdate(BaseModel):
    """Defines the structure for a single coordinate update suggested by the Steward LLM."""
    node_id: str = Field(description="The unique identifier of the node to update.")
    new_coordinates: PolarTemporalCoordinate = Field(description="The new PolarTemporalCoordinate values for the node.")

class StewardUpdates(BaseModel):
    """Defines the overall structure for the list of updates from the Steward LLM."""
    updates: List[CoordinateUpdate] = Field(description="A list of coordinate updates to be applied.")

# --- Steward Analyzer Class ---
class StewardAnalyzer:
    """
    Analyzes structural assignments (z, z_type) across a document's chunks
    using an LLM to identify global patterns and suggest refinements.
    """
    def __init__(self, llm_model: str = "gpt-4o"):
        """
        Initializes the StewardAnalyzer.

        Args:
            llm_model: The name of the OpenAI model to use (default: "gpt-4o").
        """
        self.model_name = llm_model
        self.llm = None
        self.parser = None
        self.chain = None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Steward analysis via LLM will be skipped.")
            # Keep self.llm and self.chain as None
            return # Stop initialization here if no key

        try:
            self.llm = ChatOpenAI(
                openai_api_key=api_key,
                model=self.model_name,
                temperature=0.1, # Lower temperature for more deterministic structural analysis
                model_kwargs={"response_format": {"type": "json_object"}} # Enforce JSON output
            )
            self.parser = JsonOutputParser(pydantic_object=StewardUpdates)
            self.chain = self.llm | self.parser # Define the chain here
            logger.info(f"StewardAnalyzer initialized with model: {self.model_name}")
        except Exception as e:
             logger.error(f"Error initializing StewardAnalyzer LLM or Parser: {e}", exc_info=True)
             # Ensure chain is None if initialization fails
             self.llm = None
             self.parser = None
             self.chain = None

    # Define a constant for the token limit threshold
    MAX_CONTEXT_TOKENS = 100_000 # Set a safe margin below the model's limit (e.g., 128k for gpt-4o)

    def _get_token_count(self, text: str) -> int:
        """Estimates the token count for a given text using tiktoken."""
        try:
            # Assuming encoding for gpt-4o, adjust if model changes
            # Using cl100k_base as it's common for GPT-4/3.5
            encoding = tiktoken.get_encoding("cl100k_base") 
            num_tokens = len(encoding.encode(text))
            return num_tokens
        except Exception as e:
            logger.warning(f"Could not estimate token count with tiktoken: {e}. Returning char count.")
            # Fallback to character count if tiktoken fails
            return len(text)

    def _simplify_context(self, document_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Creates a simplified version of the context, keeping essential fields."""
        simplified = []
        for item in document_context:
            # Extract coordinate details safely
            coords = item.get('metadata', {}).get('coordinates', {})
            z = coords.get('z')
            z_type = coords.get('z_type')

            simplified.append({
                "node_id": item.get("node_id"),
                "z": z, # Directly include z
                "z_type": z_type, # Directly include z_type
                "content_snippet": item.get("content_snippet", "") # Include snippet if available
            })
        return simplified

    def _create_prompt(self, document_context: List[Dict[str, Any]]) -> List[SystemMessage | HumanMessage]:
        """
        Creates the system and human prompts for the Steward LLM based on Phase 1 results.

        Args:
            document_context: A list of dictionaries, each representing a chunk's Phase 1
                              output (e.g., node_id, text_summary, coordinate).

        Returns:
            A list containing the SystemMessage and HumanMessage for the LLM.
        """
        # TODO: Implement Map-Reduce summarization if context exceeds limits.
        # For now, assume the context fits and format it directly.
        # --- START: Context Size Check & Simplification ---
        initial_formatted_context = json.dumps(document_context, indent=2)
        initial_token_count = self._get_token_count(initial_formatted_context)
        logger.debug(f"Initial Steward context token count estimate: {initial_token_count}")

        final_formatted_context = initial_formatted_context
        context_was_simplified = False

        if initial_token_count > self.MAX_CONTEXT_TOKENS:
            context_was_simplified = True
            logger.warning(
                f"Initial context token count ({initial_token_count}) exceeds threshold ({self.MAX_CONTEXT_TOKENS}). "
                f"Simplifying context for Steward LLM."
            )
            simplified_context_data = self._simplify_context(document_context)
            final_formatted_context = json.dumps(simplified_context_data, indent=2)
            simplified_token_count = self._get_token_count(final_formatted_context)
            logger.info(f"Simplified context token count estimate: {simplified_token_count}")
            # Optional: Check if simplification was sufficient
            if simplified_token_count > self.MAX_CONTEXT_TOKENS:
                 logger.error(
                     f"Simplified context ({simplified_token_count} tokens) still exceeds threshold. "
                     f"Steward analysis might fail or be inaccurate. Consider Map-Reduce."
                 )
        # --- END: Context Size Check & Simplification ---

        # formatted_context = json.dumps(document_context, indent=2)
        # Use the potentially simplified context for the prompt
        formatted_context_for_prompt = final_formatted_context

        system_prompt = f"""
You are a Steward LLM responsible for analyzing the structural narrative assignments across multiple text chunks from a single document.
Your goal is to identify global patterns, inconsistencies, or suboptimal assignments related to the 'z' (structural perspective/layer) and 'z_type' (type of structure) coordinates assigned in a previous phase (Phase 1).
You will be given a list of JSON objects, each representing a chunk with its initial structural coordinates (`z`, `z_type`) and potentially other metadata.
Analyze the provided context holistically. Look for:
- Consistent narrative perspectives that should share the same 'z' value.
- Sections or layers (e.g., dialogue, description, internal thought) that should have consistent 'z_type' values.
- Potential misclassifications or inconsistencies based on the global document structure.
- Opportunities to refine the assigned 'z' values to better reflect the overall narrative flow or distinct structural sections.

Based on your analysis, identify nodes whose `z` or `z_type` coordinates should be updated for better global consistency and accuracy.
Output ONLY a JSON object containing a single key "updates".
The value of "updates" should be a list of objects. Each object must have:
- "node_id": The unique identifier of the node requiring an update.
- "new_coordinates": A JSON object representing the complete PolarTemporalCoordinate, including the *original* 'r', 'theta', 't' values, but with the *updated* 'z' and 'z_type'. You MUST provide all coordinate fields (r, theta, t, z, z_type).

{self.parser.get_format_instructions()}

If no updates are necessary based on your global analysis, return an empty list for "updates": {{"updates": []}}.
Do not explain your reasoning in the output, only provide the JSON.
"""

        human_prompt_content = f"""
Here is the structural metadata collected from Phase 1 analysis for the document chunks:

```json
{formatted_context_for_prompt}
```

Please analyze this metadata globally and provide the necessary coordinate updates in the specified JSON format. Remember to include the original r, theta, and t values along with the updated z and z_type in the 'new_coordinates' object for each update.
"""

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt_content)
        ]

    def analyze_and_recommend_updates(self, document_context: List[Dict[str, Any]]) -> Optional[StewardUpdates]:
        """
        Analyzes the collected Phase 1 structural metadata for a document and suggests
        coordinate updates using the Steward LLM.

        Args:
            document_context: A list of dictionaries, each containing Phase 1 metadata
                              for a chunk (must include 'node_id' and 'coordinate' which
                              is a dict representation of PolarTemporalCoordinate).
                              Example: [{"node_id": "...", "coordinate": {"r": ..., "theta": ..., "t": ..., "z": ..., "z_type": "..."}}]

        Returns:
            A StewardUpdates object containing the list of suggested updates,
            or None if an error occurs during processing.
        """
        if not document_context:
            logger.warning("Received empty document context for Steward analysis. Skipping.")
            return StewardUpdates(updates=[]) # Return empty updates if context is empty

        # Check if LLM/chain was initialized successfully
        if not self.chain:
            logger.warning("StewardAnalyzer chain not initialized (likely missing API key or init error). Skipping analysis.")
            return StewardUpdates(updates=[]) # Return empty updates
            
        logger.info(f"Starting Steward analysis for {len(document_context)} chunks.")

        # --- Context Size Check & Potential Summarization (Map-Reduce) ---
        # TODO: Implement token counting and summarization logic if necessary.
        # For now, proceed assuming context fits.

        # --- Prompt Creation ---
        try:
            prompt_messages = self._create_prompt(document_context)
        except Exception as e:
            logger.error(f"Error creating Steward LLM prompt: {e}", exc_info=True)
            return None

        # --- LLM Invocation & Parsing ---
        try:
            # Use the chain defined in __init__
            logger.debug("Invoking Steward LLM chain...")
            result = self.chain.invoke(prompt_messages)
            logger.info(f"Steward LLM analysis complete. Suggested {len(result.updates)} updates.")
            logger.debug(f"Steward LLM raw output (parsed): {result}")
            return result
        except Exception as e:
            # TODO: Implement retries for transient API errors as per plan.
            logger.error(f"Error during Steward LLM invocation or parsing: {e}", exc_info=True)
            # Consider inspecting the failed output if possible (e.g., if parsing failed)
            return None # Return None on failure to indicate the step should be skipped 
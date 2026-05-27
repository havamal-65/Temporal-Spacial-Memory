import logging
from typing import List, Dict, Any, Optional
import os

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator # Use v1 for Langchain compatibility

# Local imports (assuming data_models.py defines PolarTemporalCoordinate)
# If PolarTemporalCoordinate is defined elsewhere, adjust the import
try:
    from src.data_models import PolarTemporalCoordinate
except ImportError:
    # Fallback or placeholder if data_models isn't accessible directly
    # This is just for type hinting in this file if needed
    class PolarTemporalCoordinate(BaseModel):
        r: float
        theta: float
        t: float
        z: float
        z_type: str

# Configure logging for this module
logger = logging.getLogger('StewardAnalyzer')
# Ensure handler is configured by the main script's basicConfig
# (Avoid calling basicConfig here)

# --- Pydantic Models for LLM Output ---

class RecommendedCoordinates(BaseModel):
    """Represents the recommended new coordinates for a node."""
    r: float = Field(description="Recommended radial coordinate (relevance/distance).")
    theta: float = Field(description="Recommended angular coordinate (topic angle).")
    t: float = Field(description="Recommended temporal coordinate (sequence/time).")
    z: float = Field(description="Recommended structural coordinate (layer/depth).")
    z_type: str = Field(description="Recommended structural type.")

class StewardUpdate(BaseModel):
    """Represents a single recommended update for a node."""
    node_id: str = Field(description="The ID of the node to update.")
    new_coordinates: RecommendedCoordinates = Field(description="The recommended new coordinates.")
    reasoning: str = Field(..., description="Brief explanation for the recommendation.") # Make reasoning required

class StewardUpdateList(BaseModel):
    """Represents the list of updates recommended by the Steward."""
    updates: List[StewardUpdate] = Field(default_factory=list, description="List of recommended coordinate updates.")

# --- Prompt Template ---

STEWARD_PROMPT_TEMPLATE = """
You are an expert data steward analyzing the spatial and temporal coordinates of information nodes extracted from a document.
The coordinate system is 4D Polar-Temporal (r, theta, t, z, z_type):
- 't': Represents the sequence or time (e.g., page number or chunk index). Lower 't' is earlier.
- 'r': Represents relevance or distance from a central concept (derived from embedding distance). Lower 'r' is typically more relevant. Range [0, inf).
- 'theta': Represents a topic angle (derived from embedding). Range [0, 2*pi).
- 'z': Represents a structural layer or depth.
- 'z_type': Categorical type of the structural layer (e.g., 'DEFAULT', 'PERSPECTIVE', 'LAYER_MAIN').

You are given the following list of nodes with their current coordinates:
--- NODE LIST START ---
{node_list_formatted}
--- NODE LIST END ---

Analyze this distribution of coordinates. Identify any nodes whose coordinates appear anomalous, inconsistent, or could be adjusted for better overall coherence within the 4D space based *only* on the coordinate values provided.
For example, look for outliers in 'r' or 't' for nodes that might be expected to be sequential/related, or unusual 'theta' values compared to neighbours in 't'. Consider the relationship between 'z'/'z_type' and other coordinates if applicable.

Return a list of recommended updates. For each node you recommend updating, provide its 'node_id', the 'new_coordinates' (including all fields: r, theta, t, z, z_type), and a brief 'reasoning' for the change.

Strictly adhere to the following JSON format for your response, using the exact field names specified in the schema:
{{
  "updates": [
    {{
      "node_id": "string",
      "new_coordinates": {{
            "r": float,
            "theta": float,
            "t": float,
            "z": float,
            "z_type": "string"
      }},
      "reasoning": "string"
    }}
    // ... more updates (or empty list if none)
  ]
}}

If no updates are needed, return an empty list: {{"updates": []}}.
Do not include any explanations outside the JSON structure.
"""

# --- StewardAnalyzer Class ---

class StewardAnalyzer:
    """
    Analyzes node coordinates using an LLM and recommends updates
    for consistency and coherence within the 4D space.
    """
    def __init__(self, llm_model: str = "gpt-4o"):
        """
        Initialize the Steward Analyzer.

        Args:
            llm_model: The language model to use for analysis.
        """
        logger.info(f"Initializing StewardAnalyzer with model: {llm_model}")
        self.llm_model_name = llm_model
        self.llm_client = None
        self.reduce_llm = False # Flag indicating successful LLM init

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment. StewardAnalyzer cannot function.")
            return # Keep self.llm_client as None

        try:
            self.llm_client = ChatOpenAI(model=self.llm_model_name, temperature=0, openai_api_key=api_key)
            # Perform a quick test call (optional, but good practice)
            self.llm_client.invoke("Test prompt")
            logger.info("StewardAnalyzer LLM client initialized and tested successfully.")
            self.reduce_llm = True # Set flag on successful init
        except Exception as e:
            logger.error(f"Failed to initialize or test StewardAnalyzer LLM client: {e}", exc_info=True)
            self.llm_client = None # Ensure client is None if init fails

    def _format_node_data_for_prompt(self, node_data: List[Dict[str, Any]]) -> str:
        """Formats the node data into a string suitable for the LLM prompt."""
        formatted_lines = []
        for node_info in node_data:
            node_id = node_info.get('node_id')
            coord_obj = node_info.get('coordinate')
            if node_id and isinstance(coord_obj, PolarTemporalCoordinate):
                # Use model_dump() if it's a Pydantic model, otherwise access attributes
                try:
                    coord_dict = coord_obj.model_dump() # Assumes Pydantic v2+ style
                    formatted_lines.append(f"- Node ID: {node_id}, Coordinates: {coord_dict}")
                except AttributeError: # Fallback for potential older Pydantic or plain objects
                     formatted_lines.append(
                         f"- Node ID: {node_id}, Coordinates: (r={coord_obj.r}, theta={coord_obj.theta}, t={coord_obj.t}, z={coord_obj.z}, z_type='{coord_obj.z_type}')"
                     )

            else:
                logger.warning(f"Skipping node in prompt formatting due to missing ID or invalid coordinate: {node_info}")
        return "\n".join(formatted_lines)


    def analyze_and_recommend_updates(self, node_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyzes node coordinates using an LLM and recommends updates.

        Args:
            node_data: A list of dictionaries, each containing at least
                       'node_id' and 'coordinate' (PolarTemporalCoordinate object).

        Returns:
            A dictionary containing a list of updates under the key 'updates'.
            Each update is a dictionary with 'node_id' and 'new_coordinates' (as a dict).
        """
        logger.info(f"StewardAnalyzer received {len(node_data)} nodes for analysis.")

        if not self.llm_client:
            logger.error("StewardAnalyzer LLM client not initialized. Cannot perform analysis. Returning no updates.")
            return {"updates": []}

        if not node_data:
            logger.info("No node data provided to StewardAnalyzer. Returning no updates.")
            return {"updates": []}

        # Format node data for the prompt
        formatted_nodes = self._format_node_data_for_prompt(node_data)
        if not formatted_nodes:
             logger.warning("Formatted node data for prompt is empty. Returning no updates.")
             return {"updates": []}

        # Create the chain
        prompt = ChatPromptTemplate.from_template(STEWARD_PROMPT_TEMPLATE)
        # Use with_structured_output for parsing based on StewardUpdateList Pydantic model
        structured_llm = self.llm_client.with_structured_output(StewardUpdateList)
        chain = prompt | structured_llm

        try:
            logger.info("Invoking StewardAnalyzer LLM chain...")
            llm_response: StewardUpdateList = chain.invoke({"node_list_formatted": formatted_nodes})
            logger.info(f"StewardAnalyzer LLM call successful. Received {len(llm_response.updates)} potential updates.")

            # Convert Pydantic models back to simple dicts for the return value,
            # as expected by ingest_structured_atlas.py
            final_updates = []
            for update in llm_response.updates:
                 # Convert RecommendedCoordinates Pydantic model to dict
                 try:
                     new_coords_dict = update.new_coordinates.model_dump()  # Pydantic v2 style
                 except AttributeError:
                     new_coords_dict = update.new_coordinates.dict()  # Fallback for Pydantic v1

                 final_updates.append({
                     "node_id": update.node_id,
                     "new_coordinates": new_coords_dict,
                     # Optionally include reasoning if needed downstream,
                     # but current ingest script doesn't use it
                     # "reasoning": update.reasoning
                 })

            return {"updates": final_updates}

        except Exception as e:
            logger.error(f"Error during StewardAnalyzer LLM chain execution: {e}", exc_info=True)
            return {"updates": []} # Return empty list on error 
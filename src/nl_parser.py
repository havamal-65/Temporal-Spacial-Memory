"""
Natural Language Query Parser for Narrative Atlas

Uses an LLM with function calling to parse natural language queries into
structured search parameters, including semantic query text and coordinate filters (r, theta, t).
"""

import os
import datetime
import time
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, validator
import math
from langchain_core.prompts import ChatPromptTemplate
from pydantic.v1 import BaseModel as V1BaseModel, Field as V1Field, validator as V1Validator
from dataclasses import dataclass
from src.data_models import Z_TYPES
from src.utils.llm_factory import create_llm_service, create_structured_llm, llm_is_available


# --- Define Output Schema using Pydantic V1 (as used previously) ---

class CoordinateFilters(V1BaseModel):
    """Represents the coordinate filters extracted from the query (r, theta, t, z, z_type)."""
    r_min: Optional[float] = V1Field(None, description="Minimum relevance (radial distance, lower is more relevant). E.g., 0.0")
    r_max: Optional[float] = V1Field(None, description="Maximum relevance (radial distance). E.g., interpret 'highly relevant' as r_max=0.5")
    t_min: Optional[float] = V1Field(None, description="Minimum temporal coordinate (sequence value). E.g., interpret 'beginning of document' as t_min=0.0")
    t_max: Optional[float] = V1Field(None, description="Maximum temporal coordinate (sequence value). E.g., interpret 'middle of document' as t_max=<estimated midpoint>")
    theta_min: Optional[float] = V1Field(None, description="Minimum topic angle (radians, [0, 2*pi)). Not derived from topic text in this phase.")
    theta_max: Optional[float] = V1Field(None, description="Maximum topic angle (radians, [0, 2*pi)). Not derived from topic text in this phase.")
    z_min: Optional[float] = V1Field(None, description="Minimum structural coordinate (z). E.g., filter for specific layers or perspectives mapped to z-values.")
    z_max: Optional[float] = V1Field(None, description="Maximum structural coordinate (z).")
    z_type: Optional[Z_TYPES] = V1Field(None, description=f"Specific structural type to filter for. Allowed values: {list(Z_TYPES.__args__)}")

    def has_filters(self) -> bool:
        """Check if any coordinate filters are set."""
        return any([
            self.r_min is not None,
            self.r_max is not None,
            self.t_min is not None,
            self.t_max is not None,
            self.theta_min is not None,
            self.theta_max is not None,
            self.z_min is not None,
            self.z_max is not None,
            self.z_type is not None,
        ])

    @V1Validator('r_min', 'r_max')
    def validate_relevance(cls, v):
        if v is not None and v < 0:
            raise ValueError("Relevance 'r' cannot be negative")
        return v

    @V1Validator('theta_min', 'theta_max')
    def validate_angle(cls, v):
        if v is not None:
            # Normalize to [0, 2*pi)
            v = v % (2 * math.pi)
        return v

    @V1Validator('t_max')
    def validate_time_order(cls, v, values):
        t_min = values.get('t_min')
        if v is not None and t_min is not None and v < t_min:
            raise ValueError("t_max cannot be earlier than t_min")
        return v

    @V1Validator('z_max')
    def validate_z_order(cls, v, values):
        z_min = values.get('z_min')
        if v is not None and z_min is not None and v < z_min:
            raise ValueError("z_max cannot be less than z_min")
        return v

class ParsedQuery(V1BaseModel):
    """Structured representation of the parsed natural language query."""
    query_text: str = None
    filters: CoordinateFilters = None
    limit: int = 10


# --- Placeholder for Parser Class/Function ---

class NlQueryParser:
    def __init__(self, llm: Optional[Any] = None):
        """
        Initializes the parser with an LLM instance.
        Defaults to ChatOpenAI if not provided.
        """
        if llm is None:
            # Provider (local/openai) controlled by LLM_PROVIDER; see src/utils/llm_factory.py
            if not llm_is_available():
                raise ValueError(
                    "LLM provider not available. Set LLM_PROVIDER=local with a running "
                    "local server, or LLM_PROVIDER=openai with OPENAI_API_KEY."
                )
            self.llm = create_llm_service(model="gpt-4o", temperature=0)
        else:
             self.llm = llm

        # Create the extraction chain using the Pydantic schema (provider-aware).
        self.extraction_runnable = create_structured_llm(self.llm, ParsedQuery)


    def parse(self, query: str) -> ParsedQuery:
        """
        Parses a natural language query string into a ParsedQuery object.
        """
        print(f"--- NL PARSER: Parsing query: '{query}' ---") # DEBUG
        
        # Modified system message to be less aggressive on z_type filtering
        system_message = f"""You are an expert query analyst. Parse the user's query about documents.
        Extract the core semantic meaning into 'query_text'.
        Extract any specified filters for coordinates (r, theta, t, z, z_type).
        Interpret relative terms:
        - 'highly relevant' means r_max=0.5 (lower r is more relevant).
        - 'somewhat relevant' means r_max=1.0.
        - 'low relevance' means r_min=1.5.
        - Interpret positional terms like 'start', 'beginning', 'middle', 'end' for the temporal/sequence coordinate 't'. Assume 't' ranges from 0 upwards. E.g., 'beginning' -> t_max=1.0, 'middle' -> t_min=1.0, t_max=10.0 (estimate). 'Near page X' -> derive approximate t value.
        - Interpret time expressions like 'last month', 'yesterday', 'today', 'specific dates' relative to the current date ({datetime.date.today()}). These might inform 't' filters IF the document has timestamps, otherwise focus on sequence (page/chunk) based 't'.
        
        - **IMPORTANT**: Only extract a `z_type` filter if the query explicitly mentions structural document parts using keywords like 'perspective', 'footnote', 'commentary', 'appendix', 'version', 'summary', 'abstract', 'document ID', or 'layer'. Do NOT infer a `z_type` from general descriptive terms like 'technical layer' or 'narrative flow'. If no explicit structural term is mentioned, leave `z_type` as null/None. Allowed z_types: {list(Z_TYPES.__args__)}.
        - If a structural term IS mentioned (e.g., 'Character A perspective', 'version 2'), try to map it to a specific `z` value filter (z_min/z_max) or the corresponding `z_type`.
        
        - Do NOT attempt to derive theta (topic angle) filters from the topic words in the query for now. Set theta_min/theta_max only if explicit angles/directions (e.g., 'topics around 90 degrees') are mentioned.
        - If a single value is given for a coordinate (e.g., 'relevance 0.2', 'layer 1' mapped to z=1.0), set both min and max for that coordinate filter (e.g., r_min=0.2, r_max=0.2 or z_min=1.0, z_max=1.0).
        Return the extracted information as a JSON object structured according to the ParsedQuery schema."""
        
        try:
            # Pass the query and the system message (if the runnable supports it directly,
            # otherwise, you might need to format it into the user message or use a chain)
            # Assuming .invoke() takes a simple string for now, need to check Langchain docs for best way
            # to include system message with with_structured_output
            # ---> For now, we rely on the LLM understanding the instructions within the query itself
            # ---> or implicitly via the Pydantic descriptions. Adjusting the system message *might* work
            # ---> depending on the exact Langchain implementation details.
            
            # Let's try prepending a simplified instruction to the user query for the LLM
            # This is a less robust way than a proper system message but might work.
            prompt_for_llm = f"{system_message}\n\nUser Query: {query}"
            
            # structured_output = self.extraction_runnable.invoke(query) # Original call
            structured_output = self.extraction_runnable.invoke(prompt_for_llm) # Call with combined prompt
            
            print(f"--- NL PARSER: Raw LLM Output: {structured_output} ---") # DEBUG
            
            # Langchain's with_structured_output should directly return the Pydantic object
            if isinstance(structured_output, ParsedQuery):
                 print(f"--- NL PARSER: Parsed Output: {structured_output} ---") # DEBUG
                 return structured_output
            else:
                 # This case might indicate an issue with the Langchain version or method
                 print(f"--- NL PARSER: ERROR: Unexpected output type: {type(structured_output)} ---") # DEBUG
                 # Attempt to manually parse if it looks like a dict (fallback)
                 if isinstance(structured_output, dict):
                     try:
                         parsed_obj = ParsedQuery(**structured_output)
                         print(f"--- NL PARSER: Fallback Parsed Output: {parsed_obj} ---") # DEBUG
                         return parsed_obj
                     except Exception as e:
                          raise ValueError(f"Failed to parse LLM dictionary output into ParsedQuery: {e}") from e
                 raise TypeError(f"Expected ParsedQuery output, got {type(structured_output)}")

        except Exception as e:
            print(f"--- NL PARSER: ERROR: Failed to parse query '{query}': {e} ---") # DEBUG
            # Log the error properly
            # logger.error(f"Failed to parse query '{query}': {e}", exc_info=True)
            # Re-raise or return a default/error object depending on desired behavior
            raise ValueError(f"Query parsing failed: {e}") from e

# --- Example Usage ---
if __name__ == '__main__':
    # Ensure dotenv is loaded if running directly (might be needed for API key)
    from dotenv import load_dotenv
    load_dotenv() 
    
    parser = NlQueryParser()
    
    test_queries = [
        "Find documents about machine learning",
        "Search for highly relevant articles on transformer models from the start of the document",
        "What discussions happened near page 5 regarding vector databases?",
        "Retrieve information about project status updated towards the end",
        "Show me low relevance items about cloud computing before page 10",
        # "documents related to financial planning in layer 3" # Removed z-based query
        # Add Z-related queries
        "Find information about databases mentioned in footnotes",
        "What were the main points from Character A's perspective?",
        "Show the summary sections related to AI.",
        "Get version 2 of the design document."
    ]
    
    for q in test_queries:
        print(f"\n--- Testing Query: '{q}' ---")
        try:
            parsed = parser.parse(q)
            print(f"Parsed Result: {parsed.json(indent=2)}")
        except Exception as e:
            print(f"Error parsing query: {e}")

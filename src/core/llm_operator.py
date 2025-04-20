import os
import json
from openai import OpenAI

# Remove global client initialization
# client = OpenAI()

class LLMOperator:
    def __init__(self, model="gpt-4.1"):
        # Initialize client here, after main script likely loaded .env
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Fatal: OPENAI_API_KEY not found in environment. Cannot initialize LLMOperator.")
            # Optionally raise an error or handle appropriately
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def extract_entities(self, text, context=None):
        prompt = self._build_entity_prompt(text, context)
        # Use instance client
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}]
        )
        return self._parse_response(response)

    def segment_text(self, text, context=None):
        prompt = self._build_segmentation_prompt(text, context)
        # Use instance client
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}]
        )
        return self._parse_response(response)

    def _build_entity_prompt(self, text, context):
        return f"""Extract all characters, locations, events, and themes from the following text. Return as JSON.\nText:\n'''{text}'''
"""

    def _build_segmentation_prompt(self, text, context):
        return f"""Segment the following text into chapters, scenes, and paragraphs. Return as JSON with start/end indices.\nText:\n'''{text}'''
"""

    def _parse_response(self, response):
        # Try to extract JSON from the LLM response
        try:
            # Use dot notation for pydantic models from OpenAI v1.x+
            content = response.choices[0].message.content
            
            # Attempt to find and parse JSON within the content string
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
            
            # Fallback: If the entire content string might be JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                 # If content is not JSON but extraction is needed, handle here
                 # For now, assume it should be JSON and log if not.
                 print(f"LLMOperator: Content is not valid JSON. Content: {content}")
                 return None # Or handle non-JSON content appropriately

        except (AttributeError, IndexError, TypeError) as e:
            print(f"LLMOperator: Error accessing response content: {e}")
            print("Raw response object:", response)
            return None
        except json.JSONDecodeError as e:
            print(f"LLMOperator: Failed to parse extracted JSON string: {e}")
            print(f"Extracted string: {json_str if 'json_str' in locals() else 'N/A'}")
            print(f"Original content: {content if 'content' in locals() else 'N/A'}")
            return None
        except Exception as e:
            # Catch any other unexpected errors during parsing
            print(f"LLMOperator: Unexpected error parsing LLM response: {e}")
            print("Raw response object:", response)
            return None 
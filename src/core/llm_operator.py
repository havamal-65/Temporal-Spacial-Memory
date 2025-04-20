import os
import json
from openai import OpenAI

# Remove global client initialization
# client = OpenAI()

class LLMOperator:
    def __init__(self, model="gemma-3-27b-it"): # Default to specified local model
        # Point client to LM Studio default endpoint
        # API key is often ignored by local servers, but pass dummy value if required
        self.client = OpenAI(base_url="http://localhost:1234/v1", api_key="ignored")
        self.model = model
        print(f"LLMOperator initialized to use model '{self.model}' via {self.client.base_url}")

    def extract_entities(self, text, context=None):
        prompt = self._build_entity_prompt(text, context)
        print(f"    [LLM Call] Requesting entity extraction from local model...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "You are a helpful assistant skilled in extracting structured information from text."}, 
                          {"role": "user", "content": prompt}],
                temperature=0.7 # Adjust temperature if needed for local model creativity/consistency
            )
            print(f"    [LLM Call] Received response.")
            return self._parse_response(response)
        except Exception as e:
            print(f"LLMOperator: Error during API call to local model: {e}")
            return None

    def segment_text(self, text, context=None):
        # Note: Segmentation might be less reliable with some local models
        # Consider deterministic methods first if results are poor.
        prompt = self._build_segmentation_prompt(text, context)
        print(f"    [LLM Call] Requesting segmentation from local model...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                 messages=[{"role": "system", "content": "You are a helpful assistant skilled in segmenting text."}, 
                          {"role": "user", "content": prompt}],
                temperature=0.7
            )
            print(f"    [LLM Call] Received response.")
            return self._parse_response(response)
        except Exception as e:
            print(f"LLMOperator: Error during API call to local model: {e}")
            return None

    def _build_entity_prompt(self, text, context):
        # Keep prompt simple for local models initially
        return f"Extract characters, locations, events, and themes from the text below. Output ONLY as JSON.\n\nText:\n{text}"

    def _build_segmentation_prompt(self, text, context):
        return f"Segment the text below into chapters, scenes, and paragraphs. Output ONLY as JSON with start/end indices.\n\nText:\n{text}"

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
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e_inner:
                    print(f"LLMOperator: Failed to parse extracted JSON substring: {e_inner}")
                    print(f"Substring: {json_str}")
                    print(f"Original content: {content}")
                    return None # Indicate parsing failure
            else:
                # Try parsing the whole content if no braces found, or only partial
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"LLMOperator: Content is not valid JSON and braces not found/matched. Content: {content}")
                    return None

        except (AttributeError, IndexError, TypeError) as e:
            print(f"LLMOperator: Error accessing response structure: {e}")
            print("Raw response object:", response)
            return None
        except Exception as e:
            # Catch any other unexpected errors during parsing
            print(f"LLMOperator: Unexpected error parsing LLM response: {e}")
            print("Raw response object:", response)
            return None 
import openai
import os
import json

class LLMOperator:
    def __init__(self, api_key=None, model="gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key
        self.model = model

    def extract_entities(self, text, context=None):
        prompt = self._build_entity_prompt(text, context)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}]
        )
        return self._parse_response(response)

    def segment_text(self, text, context=None):
        prompt = self._build_segmentation_prompt(text, context)
        response = openai.ChatCompletion.create(
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
            content = response["choices"][0]["message"]["content"]
            # Find the first and last curly braces to extract JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
            return json.loads(content)
        except Exception as e:
            print("LLMOperator: Failed to parse LLM response as JSON:", e)
            print("Raw response:", response)
            return None 
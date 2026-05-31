import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src directory to path to allow importing nl_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nl_parser import NlQueryParser, ParsedQuery, CoordinateFilters

class TestNlQueryParser(unittest.TestCase):

    @patch('nl_parser.create_llm_service') # Mock the LLM factory used by nl_parser
    def test_simple_query_parsing(self, MockCreateLlm):
        """Test parsing a simple query with no filters."""
        # Configure the mock LLM's structured output runnable
        mock_llm_instance = MockCreateLlm.return_value
        mock_runnable = MagicMock()
        # Simulate the LLM returning a ParsedQuery object
        expected_output = ParsedQuery(
            query_text="machine learning",
            filters=CoordinateFilters(), # No filters expected
            limit=10
        )
        mock_runnable.invoke.return_value = expected_output
        mock_llm_instance.with_structured_output.return_value = mock_runnable

        # Instantiate the parser (it will use the mocked LLM)
        parser = NlQueryParser()
        
        query = "Find documents about machine learning"
        result = parser.parse(query)
        
        # Assertions
        self.assertEqual(result.query_text, "machine learning")
        self.assertIsNone(result.filters.r_min)
        self.assertIsNone(result.filters.r_max)
        self.assertIsNone(result.filters.t_min)
        self.assertIsNone(result.filters.t_max)
        self.assertIsNone(result.filters.z_min)
        self.assertIsNone(result.filters.z_max)
        self.assertEqual(result.limit, 10) # Default limit
        
        # Verify the mock was called correctly
        # Parser injects a system prompt before the query; verify invoke was called once
        # and the raw query text appears somewhere in the argument passed.
        mock_runnable.invoke.assert_called_once()
        call_arg = mock_runnable.invoke.call_args[0][0]
        self.assertIn(query, call_arg)

    @patch('nl_parser.create_llm_service')
    def test_query_with_filters_parsing(self, MockCreateLlm):
        """Test parsing a query with various filters."""
        mock_llm_instance = MockCreateLlm.return_value
        mock_runnable = MagicMock()
        # Simulate LLM output based on instructions (assuming it followed them)
        expected_output = ParsedQuery(
            query_text="transformer models",
            filters=CoordinateFilters(
                r_max=0.5, # From "highly relevant"
                t_min=1700000000.0, # Placeholder timestamp for "last week"
                t_max=1700604800.0, # Placeholder timestamp for "last week"
                z_min=1,         # From "technical"
                z_max=1          # From "technical"
            ),
            limit=5 # Example limit parsed from query
        )
        mock_runnable.invoke.return_value = expected_output
        mock_llm_instance.with_structured_output.return_value = mock_runnable

        parser = NlQueryParser()
        
        query = "Search for 5 highly relevant technical articles on transformer models from last week"
        result = parser.parse(query)
        
        # Assertions (checking if the mocked output was passed through)
        self.assertEqual(result.query_text, "transformer models")
        self.assertIsNone(result.filters.r_min)
        self.assertEqual(result.filters.r_max, 0.5)
        self.assertEqual(result.filters.t_min, 1700000000.0) # Check against mock output
        self.assertEqual(result.filters.t_max, 1700604800.0) # Check against mock output
        self.assertEqual(result.filters.z_min, 1)
        self.assertEqual(result.filters.z_max, 1)
        self.assertEqual(result.limit, 5)
        
        # Parser injects a system prompt before the query; verify invoke was called once
        # and the raw query text appears somewhere in the argument passed.
        mock_runnable.invoke.assert_called_once()
        call_arg = mock_runnable.invoke.call_args[0][0]
        self.assertIn(query, call_arg)

    # TODO: Add more test cases:
    # - Test different filter combinations
    # - Test edge cases (e.g., queries that are hard to parse)
    # - Test validator logic in CoordinateFilters (if possible via mocked LLM output)
    # - Test error handling if LLM fails

if __name__ == '__main__':
    unittest.main() 
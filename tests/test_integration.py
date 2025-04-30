import unittest
import sys
import os
import subprocess
import time # Added for timestamp in filter test
import json # Added for parsing potential JSON in output
from unittest.mock import patch, MagicMock

# Add src directory to path to allow importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Imports needed for mocking or setup (adjust as needed)
from nl_parser import NlQueryParser, ParsedQuery, CoordinateFilters 


class TestNarrativeAtlasIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up prerequisites for integration tests (runs once)."""
        print("\n--- Setting up Integration Test Environment ---")
        # 1. Create a dedicated test Atlas (using ingestion script)
        cls.test_storage_path = "./test_integration_atlas_storage"
        cls.test_fixtures_path = "tests/fixtures"
        cls.test_input_path = os.path.join(cls.test_fixtures_path, "sample_doc.txt")
        cls.embedding_service_type = "mock" # Use mock for predictable testing
        
        # Ensure fixture dir/file exist
        if not os.path.exists(cls.test_fixtures_path): os.makedirs(cls.test_fixtures_path)
        if not os.path.exists(cls.test_input_path):
             with open(cls.test_input_path, "w") as f:
                 f.write("This is the first sentence for integration testing.\n") # Chunk 1
                 f.write("This is the second sentence, relevant to topic A.\n") # Chunk 2
                 f.write("This final sentence is about topic B, from yesterday.\n") # Chunk 3
                 
        # Corrected command to run ingestion using src/main.py as a module
        ingest_cmd = [
            sys.executable, 
            "-m", "src.main", # Run main as a module
            "--input-dir", cls.test_fixtures_path, # Use the fixtures directory
            "--storage-path", cls.test_storage_path,
            "--embedding-service", cls.embedding_service_type,
            "--clear-db" # Start fresh for test
        ]
        print(f"Running ingestion for integration test: {' '.join(ingest_cmd)}")
        try:
            # Execute the actual ingestion command
            # Set CWD or use absolute paths if necessary
            print("--- Executing Ingestion Subprocess --- ")
            # Uncomment to run actual ingestion
            ingest_result = subprocess.run(ingest_cmd, check=True, capture_output=True, text=True, timeout=60)
            print(f"Ingestion stdout:\n{ingest_result.stdout}")
            if ingest_result.stderr:
                 print(f"Ingestion stderr:\n{ingest_result.stderr}")
            # print("--- (Simulated Ingestion - Replace with actual subprocess call if needed) ---")
            # Ensure storage dir exists for subsequent steps even if subprocess is commented out
            # if not os.path.exists(cls.test_storage_path): os.makedirs(cls.test_storage_path)
            
        except subprocess.CalledProcessError as e:
            print(f"Integration test setup failed during ingestion command: {e}")
            print(f"Ingestion stdout: {e.stdout}")
            print(f"Ingestion stderr: {e.stderr}")
            raise
        except Exception as e:
            print(f"Integration test setup failed during ingestion: {e}")
            raise
            
        print("--- Integration Test Environment Setup Complete ---")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all integration tests (runs once)."""
        print("\n--- Tearing Down Integration Test Environment ---")
        # Remove the test atlas storage directory
        import shutil
        if os.path.exists(cls.test_storage_path):
            try:
                shutil.rmtree(cls.test_storage_path)
                print(f"Removed test storage: {cls.test_storage_path}")
            except OSError as e:
                print(f"Error removing test storage directory {cls.test_storage_path}: {e}")
        # Remove fixtures if created dynamically
        # if os.path.exists(cls.test_input_path): os.remove(cls.test_input_path)
        # if os.path.exists("tests/fixtures"): os.rmdir("tests/fixtures") # Only if empty
        print("--- Integration Test Environment Teardown Complete ---")

    def _run_query_script(self, nl_query: str, max_results: int = 5) -> str:
        """Helper method to run the query script and return stdout."""
        query_cmd = [
            sys.executable,
            "src/query.py",
            "--storage-path", self.test_storage_path,
            "--embedding-service", self.embedding_service_type,
            "--query", nl_query,
            "--max-results", str(max_results)
        ]
        print(f"Running query script: {' '.join(query_cmd)}")
        try:
            result = subprocess.run(query_cmd, check=True, capture_output=True, text=True, timeout=30)
            print(f"Query script stdout:\n{result.stdout}")
            if result.stderr:
                 print(f"Query script stderr:\n{result.stderr}")
            return result.stdout
        except subprocess.CalledProcessError as e:
             self.fail(f"Query script execution failed: {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
        except Exception as e:
            self.fail(f"Query script execution failed: {e}")
        return "" # Should not be reached if fail works

    @patch('src.models.narrative_atlas.NlQueryParser.parse')
    def test_nl_query_end_to_end_simple(self, mock_parse):
        """Test the end-to-end flow with a simple query and mocked parser."""
        print("\n--- Running Test: End-to-End Simple Query ---")
        # 1. Configure Mock Parser Output for this test case
        mock_parse.return_value = ParsedQuery(
            query_text="topic A", # Core concept to search for
            filters=CoordinateFilters(), # No coordinate filters
            limit=5
        )
        
        # 2. Prepare the query script command
        nl_query = "Tell me about topic A"
        result_stdout = self._run_query_script(nl_query, max_results=5)
        
        # 3. Assertions on the Output
        mock_parse.assert_called_once_with(nl_query)
        # Check if output likely contains the node related to topic A
        self.assertIn("topic A", result_stdout, "Expected output to contain 'topic A'")
        # Check if output does NOT contain topic B (since query was for A)
        self.assertNotIn("topic B", result_stdout, "Expected output not to contain 'topic B' for this query")
        self.assertIn("--- Query Results ---", result_stdout)
        self.assertIn("Content:", result_stdout) # Check for content field
        print("--- Test Complete: End-to-End Simple Query ---")

    @patch('src.models.narrative_atlas.NlQueryParser.parse')
    def test_nl_query_with_filters(self, mock_parse):
        """Test end-to-end flow with filters active (mocked parser)."""
        print("\n--- Running Test: End-to-End Query with Filters ---")
        # 1. Configure Mock Parser Output - query for topic B, but filter for high relevance (r_max=0.1) 
        # and maybe a time filter that excludes it (depending on ingested coords)
        # Let's assume high relevance excludes the node based on mock ingestion (r>0.1)
        mock_parse.return_value = ParsedQuery(
            query_text="topic B",
            filters=CoordinateFilters(
                r_max=0.1, # Assume this is very strict and excludes the topic B node
                t_min=time.time() - 86400 # Example: within last day
            ),
            limit=5
        )
        
        # 2. Prepare query script command
        nl_query = "Find highly relevant info on topic B from today"
        result_stdout = self._run_query_script(nl_query, max_results=5)
        
        # 3. Assertions
        mock_parse.assert_called_once_with(nl_query)
        # Check that the output indicates no results were found due to filtering
        self.assertIn("No results found", result_stdout, "Expected no results due to filtering")
        self.assertNotIn("topic B", result_stdout, "Expected 'topic B' node to be filtered out")
        print("--- Test Complete: End-to-End Query with Filters ---")
        
    @patch('src.models.narrative_atlas.NlQueryParser.parse')
    def test_nl_query_time_filter_only(self, mock_parse):
        """Test end-to-end flow with only a time filter (mocked parser)."""
        print("\n--- Running Test: End-to-End Query with Time Filter ---")
        # Assume ingestion assigns timestamps close to now.
        # Filter for results strictly older than 1 day ago - should exclude all/most.
        # Note: This relies on mock embedding similarity possibly returning something.
        very_old_timestamp = time.time() - (2 * 86400) # 2 days ago
        
        nl_query = "Find info about anything older than yesterday"
        mock_parse.return_value = ParsedQuery(
            query_text="anything", # Broad query text
            filters=CoordinateFilters(
                t_max=very_old_timestamp # Only allow results older than 2 days ago
            ),
            limit=5
        )
        
        result_stdout = self._run_query_script(nl_query, max_results=5)
        
        mock_parse.assert_called_once_with(nl_query)
        # We expect no results from the fixture based on this time filter
        self.assertIn("No results found", result_stdout, "Expected no results due to time filtering")
        print("--- Test Complete: End-to-End Query with Time Filter ---")
        
    # TODO: Add more integration tests...


if __name__ == '__main__':
    unittest.main() 
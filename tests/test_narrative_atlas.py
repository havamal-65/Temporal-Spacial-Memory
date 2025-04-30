import unittest
import sys
import os
import numpy as np
from unittest.mock import MagicMock, PropertyMock

# Add src directory to path to allow importing atlas and coordinates
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from models.narrative_atlas import NarrativeAtlas, Node
from coordinates import PolarTemporalCoordinate
from nl_parser import CoordinateFilters
from utils.embedding_service import MockEmbeddingService # Use mock service for testing
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document

# Mock FAISS class (enough for basic interaction testing)
class MockFAISS:
    def __init__(self):
        self.index = MagicMock()
        self.docstore = InMemoryDocstore() # Use the real InMemoryDocstore
        self.index_to_docstore_id = {}

    def save_local(self, folder_path, index_name):
        pass # Mock save

    @classmethod
    def load_local(cls, folder_path, embeddings, index_name, allow_dangerous_deserialization):
        # Return a new mock instance on load for simplicity
        print(f"MockFAISS.load_local called in {folder_path}")
        # In a real test, you might want to load pre-saved mock data here
        mock_instance = cls()
        # Simulate loading some dummy data if needed for specific tests
        # mock_instance.docstore.add({"doc_id_1": Document(...)})
        return mock_instance

    def add_embeddings(self, texts, embeddings, metadatas, ids):
        # Mock adding to docstore and mappings
        added_ids = []
        for i, doc_id in enumerate(ids):
             doc = Document(page_content=texts[i], metadata=metadatas[i])
             self.docstore.add({doc_id: doc})
             # Simulate mapping (index_to_docstore_id not critical for this test)
             added_ids.append(doc_id)
        return added_ids

    def delete(self, ids):
        # Mock deletion (actual InMemoryDocstore has no delete, so just pass)
        print(f"MockFAISS delete called with ids: {ids}")
        return True
        
    def similarity_search_by_vector_with_relevance_scores(self, embedding, k):
        # Return dummy results for testing search flow
        print(f"MockFAISS similarity_search called with k={k}")
        # In a real test, you'd return mock Document objects with scores
        return []


class TestNarrativeAtlasFiltering(unittest.TestCase):

    def setUp(self):
        """Set up a mock NarrativeAtlas instance for testing filtering."""
        # Use a mock embedding service
        self.mock_embedding_service = MockEmbeddingService(dimension=4) # Small dimension for testing
        
        # Patch the FAISS class used by NarrativeAtlas
        self.patcher = patch('src.models.narrative_atlas.FAISS', new=MockFAISS)
        self.MockFAISSClass = self.patcher.start()
        
        # Create NarrativeAtlas instance (will use MockFAISS)
        self.atlas = NarrativeAtlas(storage_path="./test_atlas_storage", embedding_service=self.mock_embedding_service)
        
        # Clean up any previous test storage if needed (optional)
        # self.atlas.clear() 
        
        # --- Add some mock documents directly to the mock docstore for testing filtering --- 
        # Note: We bypass atlas.add_node for simpler setup here, focusing only on filtering logic
        self.doc_meta_list = [
            {'node_id': 'node1', 'node_type': 'chunk', 'r': 0.1, 'theta': 1.0, 't': 100, 'z': 1}, # Matches filters below
            {'node_id': 'node2', 'node_type': 'chunk', 'r': 0.6, 'theta': 2.0, 't': 150, 'z': 1}, # Fails r_max
            {'node_id': 'node3', 'node_type': 'chunk', 'r': 0.2, 'theta': 3.0, 't': 50,  'z': 1}, # Fails t_min
            {'node_id': 'node4', 'node_type': 'chunk', 'r': 0.3, 'theta': 4.0, 't': 250, 'z': 1}, # Fails t_max
            {'node_id': 'node5', 'node_type': 'chunk', 'r': 0.4, 'theta': 5.0, 't': 180, 'z': 2}, # Fails z_max
            {'node_id': 'node6', 'node_type': 'chunk', 'r': 0.15, 'theta': 0.5, 't': 120, 'z': 1},# Matches filters below
            {'node_id': 'node7', 'node_type': 'summary', 'r': 0.05, 'theta': 1.5, 't': 110, 'z': 0}, # Fails z_min
            {'node_id': 'node8', 'node_type': 'chunk', 'r': 0.9, 'theta': 1.0, 't': 100, 'z': 1} # Fails r_max
        ]
        
        docs_to_add = {}
        test_doc_ids = []
        for i, meta in enumerate(self.doc_meta_list):
            doc_id = f"doc_{meta['node_id']}"
            test_doc_ids.append(doc_id)
            docs_to_add[doc_id] = Document(page_content=f"Content for {meta['node_id']}", metadata=meta)
            # Manually populate the atlas mappings needed by the filter function
            self.atlas.node_id_to_doc_id[meta['node_id']] = doc_id
            self.atlas.doc_id_to_node_id[doc_id] = meta['node_id']
            
        # Add documents directly to the docstore of the mocked vector_store
        if hasattr(self.atlas.vector_store, 'docstore') and hasattr(self.atlas.vector_store.docstore, 'add'):
             self.atlas.vector_store.docstore.add(docs_to_add)
        else:
             print("Warning: Could not directly add mock docs to docstore in setup.")
        print(f"Setup: Added {len(docs_to_add)} mock docs to docstore for filtering test.")

    def tearDown(self):
        """Stop the patcher after each test."""
        self.patcher.stop()
        # Clean up test directory (optional)
        # import shutil
        # if os.path.exists("./test_atlas_storage"):
        #     shutil.rmtree("./test_atlas_storage")

    def test_coordinate_filtering(self):
        """Test the _get_ids_matching_filters method."""
        # Define filters
        filters = CoordinateFilters(
            r_max=0.5, # Max relevance distance
            t_min=100, # Min time
            t_max=200, # Max time
            z_min=1,   # Min layer
            z_max=1    # Max layer
        )
        
        # Expected matching doc IDs based on self.doc_meta_list
        expected_doc_ids = ["doc_node1", "doc_node6"]
        
        # Call the method under test
        matching_ids = self.atlas._get_ids_matching_filters(filters)
        
        # Assertions
        self.assertIsNotNone(matching_ids)
        self.assertIsInstance(matching_ids, list)
        # Use assertCountEqual for order-independent comparison
        self.assertCountEqual(matching_ids, expected_doc_ids)

    def test_filtering_no_filters(self):
         """Test filtering when no filters are specified."""
         filters = CoordinateFilters() # Empty filters
         matching_ids = self.atlas._get_ids_matching_filters(filters)
         # Expect None when no filters are applied (signal to use all IDs)
         self.assertIsNone(matching_ids)
         
    def test_filtering_no_matches(self):
         """Test filtering when filters result in no matches."""
         filters = CoordinateFilters(r_max=0.01) # Very strict filter
         matching_ids = self.atlas._get_ids_matching_filters(filters)
         self.assertEqual(matching_ids, []) # Expect empty list
         
    def test_filtering_only_one_filter(self):
         """Test filtering with only a single filter active."""
         filters = CoordinateFilters(z_min=2) # Only nodes at layer 2 or higher
         expected_doc_ids = ["doc_node5"]
         matching_ids = self.atlas._get_ids_matching_filters(filters)
         self.assertCountEqual(matching_ids, expected_doc_ids)
         
    # TODO: Add tests for theta filtering if/when implemented.
    # TODO: Add tests for edge cases like missing coordinate values in metadata.


if __name__ == '__main__':
    unittest.main() 
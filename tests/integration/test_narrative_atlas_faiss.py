import os
import shutil
import pytest
from dotenv import load_dotenv
from src.models.narrative_atlas import NarrativeAtlas

load_dotenv()

def test_faiss_integration(tmp_path):
    """Test the FAISS integration by verifying add → save → load → search workflow."""
    
    # Initialize NarrativeAtlas with temporary path
    atlas = NarrativeAtlas(storage_path=str(tmp_path))
    
    # Add test nodes
    gandalf_id = atlas._get_or_create_character("Gandalf the Grey", 1.0)
    party_id = atlas._create_event("A long-expected party", 2.0, [])
    shire_id = atlas._get_or_create_location("The Shire", 0.0)
    
    # Verify initial state
    assert len(atlas.vector_store.index_to_docstore_id) == 3, "Vector store should contain 3 documents"
    assert gandalf_id in atlas.node_id_to_doc_id, "Gandalf should be in node_id_to_doc_id"
    assert party_id in atlas.node_id_to_doc_id, "Party should be in node_id_to_doc_id"
    assert shire_id in atlas.node_id_to_doc_id, "Shire should be in node_id_to_doc_id"
    
    # Save the atlas
    atlas.save()
    
    # Create new instance and load
    atlas_reloaded = NarrativeAtlas(storage_path=str(tmp_path))
    atlas_reloaded.load()
    
    # Verify reloaded state
    assert len(atlas_reloaded.vector_store.index_to_docstore_id) == 3, "Reloaded vector store should contain 3 documents"
    assert len(atlas_reloaded.node_id_to_doc_id) == 3, "Reloaded node_id_to_doc_id should have 3 entries"
    assert len(atlas_reloaded.doc_id_to_node_id) == 3, "Reloaded doc_id_to_node_id should have 3 entries"
    
    # Test search functionality
    results = atlas_reloaded.find_similar_nodes("wizard", k=1)
    assert len(results) == 1, "Should find one result for 'wizard'"
    assert results[0][0].content["name"] == "Gandalf the Grey", "Top result should be Gandalf"
    
    # Test deletion
    deleted_node_id = party_id # Choose one node to delete
    deleted_doc_id = atlas_reloaded.node_id_to_doc_id.get(deleted_node_id)
    
    assert atlas_reloaded.delete_node(deleted_node_id), f"Deletion of node {deleted_node_id} should return True"
    
    # Verify deletion state
    assert len(atlas_reloaded.vector_store.index_to_docstore_id) == 2, "Vector store should now contain 2 documents"
    assert deleted_node_id not in atlas_reloaded.db.nodes, "Deleted node should be removed from DB"
    assert deleted_node_id not in atlas_reloaded.node_id_to_doc_id, "Deleted node ID should be removed from node_id_to_doc_id map"
    if deleted_doc_id:
        assert deleted_doc_id not in atlas_reloaded.doc_id_to_node_id, "Deleted doc ID should be removed from doc_id_to_node_id map"
    
    # Try searching for the deleted node content
    results_after_delete = atlas_reloaded.find_similar_nodes("party", k=2)
    found_deleted = any(res[0].id == deleted_node_id for res in results_after_delete)
    assert not found_deleted, "Deleted node should not appear in search results"
    
    # Cleanup is handled by pytest's tmp_path fixture 
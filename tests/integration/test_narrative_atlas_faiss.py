import shutil
from pathlib import Path

import numpy as np
import pytest

from src.models.narrative_atlas import NarrativeAtlas


@pytest.fixture()
def temp_storage(tmp_path_factory):
    path = tmp_path_factory.mktemp("atlas_test_data")
    yield path
    # Cleanup after test run
    shutil.rmtree(path, ignore_errors=True)


def test_faiss_add_save_load_search(temp_storage):
    # 1-3. Initialise NarrativeAtlas with temp dir
    atlas = NarrativeAtlas(storage_path=str(temp_storage), embed_dim=64)

    # 4. Add nodes
    char_id = atlas._get_or_create_character("Gandalf the Grey", 1.0)
    evt_id = atlas._create_event("A long expected party", 2.0, [])
    loc_id = atlas._get_or_create_location("The Shire", 0.0)

    # 5-6. Assert index count & mappings
    assert atlas.faiss_index.ntotal == 3
    assert len(atlas.faiss_id_to_node_id) == 3

    # 7. Save state
    atlas.save()

    # 8. Reload into new instance
    atlas_reloaded = NarrativeAtlas(storage_path=str(temp_storage), embed_dim=64)
    atlas_reloaded.load()

    # 10. Check counts after load
    assert atlas_reloaded.faiss_index.ntotal == 3
    assert len(atlas_reloaded.faiss_id_to_node_id) == 3

    # 11. Perform similarity search queries
    # Query for a wizard; we expect Gandalf to appear in the top-k results
    results_gandalf = atlas_reloaded.find_similar_nodes("wizard", k=3)
    assert results_gandalf  # ensure non-empty
    ids_returned = {nid for nid, _ in results_gandalf}
    assert char_id in ids_returned  # Gandalf should be among the returned nodes

    # Search for unrelated term should not error and may return empty or different ids
    results_unrelated = atlas_reloaded.find_similar_nodes("satellite in orbit", k=1)
    # 13. Just ensure the call returns without error; no strict assertion on content
    assert isinstance(results_unrelated, list)

    # --- Deletion flow ---
    # Delete Gandalf node
    deleted_ok = atlas_reloaded.delete_node(char_id)
    assert deleted_ok is True

    # After deletion, node should not be in DB or FAISS index
    assert char_id not in atlas_reloaded.db
    assert char_id not in atlas_reloaded.node_id_to_faiss_id
    # Mapping length should be 2 after deletion
    assert len(atlas_reloaded.faiss_id_to_node_id) == 2

    # Search for wizard should now NOT return Gandalf
    results_after_del = atlas_reloaded.find_similar_nodes("wizard", k=3)
    ids_after = {nid for nid, _ in results_after_del}
    assert char_id not in ids_after 
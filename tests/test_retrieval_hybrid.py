"""Tests for hybrid retrieval and full-node similarity search."""

import os
import sys
import shutil
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.narrative_atlas import NarrativeAtlas
from src.data_models import PolarTemporalCoordinate
from src.utils.embedding_service import MockEmbeddingService


def _coord(t, r=0.2, theta=0.5):
    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=1.0, z_type="DEFAULT")


class TestRetrievalHybrid(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="tsm_hybrid_")
        cls.emb = MockEmbeddingService(dimension=4)
        cls.atlas = NarrativeAtlas(storage_path=cls.test_dir, embedding_service=cls.emb)

        seg_emb = np.array(cls.emb.embed_query("Beorn is a skin-changer who lives in a wooden hall."), dtype=np.float32)
        char_emb = np.array(cls.emb.embed_query("Beorn"), dtype=np.float32)
        cls.atlas.add_node(
            node_id="segment:book:10:1",
            content={"text": "Beorn is a skin-changer who lives in a wooden hall.", "ref": "book:10:1"},
            embedding=seg_emb,
            metadata={"node_type": "segment", "ref": "book:10:1"},
            coordinates=_coord(125.0),
        )
        cls.atlas.db.nodes["segment:book:10:1"].type = "segment"

        # Entity nodes from ingest are DB-only (not added to FAISS).
        from src.models.narrative_atlas import Node
        import time
        char_node = Node(
            id="character_beorn",
            type="character",
            content={"name": "Beorn", "source_refs": ["book:10:1"]},
            coordinates=_coord(125.0),
            embedding=char_emb,
            keywords=None,
            metadata={"node_type": "character", "source_refs": ["book:10:1"]},
            parent_node_id=None,
            timestamp=time.time(),
            mapping_details={},
        )
        cls.atlas.db.add_node(char_node)

        far_emb = np.array(cls.emb.embed_query("unrelated distant place"), dtype=np.float32)
        cls.atlas.add_node(
            node_id="segment:book:200:1",
            content={"text": "unrelated distant place far away", "ref": "book:200:1"},
            embedding=far_emb,
            metadata={"node_type": "segment", "ref": "book:200:1"},
            coordinates=_coord(200.0),
        )
        cls.atlas.db.nodes["segment:book:200:1"].type = "segment"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_find_similar_nodes_sees_entity_when_faiss_is_partial(self):
        """Entity nodes must be searchable when FAISS only indexes a subset."""
        ntotal = self.atlas.vector_store.index.ntotal
        self.assertLess(ntotal, len(self.atlas.db.nodes))
        hits = self.atlas.find_similar_nodes("Beorn skin-changer", k=5)
        ids = [n.id for n, _ in hits]
        self.assertIn("character_beorn", ids)

    def test_hybrid_search_keyword_hits_entity_name(self):
        hits = self.atlas.search_with_hybrid("Who is Beorn?", keyword_weight=0.5, k=5)
        ids = [n.id for n, _ in hits]
        self.assertIn("character_beorn", ids)

    def test_hybrid_search_respects_t_window_for_keywords(self):
        """Keyword scan is region-scoped; semantic hits may fall outside the window."""
        hits = self.atlas.search_with_hybrid(
            "Beorn",
            keyword_weight=1.0,
            k=10,
            t_min=100.0,
            t_max=150.0,
        )
        keyword_hits = [
            n for n, _ in hits
            if "beorn" in self.atlas._node_search_text(n).lower()
        ]
        self.assertTrue(keyword_hits, "expected at least one keyword hit for Beorn")
        for node in keyword_hits:
            self.assertGreaterEqual(node.coordinates.t, 100.0)
            self.assertLessEqual(node.coordinates.t, 150.0)
        self.assertNotIn(
            "segment:book:200:1",
            [n.id for n in keyword_hits],
            "distant segment must not match keyword scan inside t window",
        )

    def test_retrieve_for_query_expands_entity_to_segment(self):
        results = self.atlas._retrieve_for_query("Who is Beorn?", k=5)
        expanded = self.atlas.sequence_retriever.expand_results_with_refs(results)
        blob = " ".join(
            self.atlas.sequence_retriever._extract_text(n).lower() for n, _ in expanded
        )
        self.assertIn("skin-changer", blob)


class TestMountainEnumerationRetrieval(unittest.TestCase):
    """Integration check on full atlas: mountain query spans multiple t regions."""

    @classmethod
    def setUpClass(cls):
        atlas_path = os.path.join(
            os.path.dirname(__file__), "..", "output", "hobbit_local_full"
        )
        if not os.path.exists(os.path.join(atlas_path, "nodes.sqlite")):
            raise unittest.SkipTest("Full atlas not built")
        from src.models.narrative_atlas import NarrativeAtlas
        from src.utils.embedding_service import create_embedding_service

        cls.atlas = NarrativeAtlas(
            atlas_path, embedding_service=create_embedding_service("langchain")
        )

    def test_mountain_query_spreads_across_peril_passages(self):
        q = "What does the party meet and have to avoid while traveling through the mountains?"
        results = self.atlas._retrieve_for_query(q, k=12)
        segments = [
            n for n, _ in results
            if getattr(n, "type", None) == "segment"
        ]
        self.assertGreaterEqual(len(segments), 4)
        pages = {int((n.content or {}).get("page", n.coordinates.t)) for n in segments}
        # Goblins (~67-75) and storm/giants (~62-68) should both appear
        low = pages.intersection(range(55, 96))
        self.assertGreaterEqual(len(low), 2, f"expected early-mountain pages, got {pages}")
        for n, _ in results:
            self.assertLessEqual(n.coordinates.t, 110.0, "mountain query should stay in region")
        blob = " ".join(
            self.atlas.sequence_retriever._extract_text(n).lower() for n in segments
        )
        self.assertIn("goblin", blob)
        has_storm_or_giant = any(
            term in blob for term in ("giant", "thunder", "storm", "crash", "lightning")
        )
        self.assertTrue(has_storm_or_giant, "expected storm/giant prose in retrieved context")


class TestBeornRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        atlas_path = os.path.join(
            os.path.dirname(__file__), "..", "output", "hobbit_local_full"
        )
        if not os.path.exists(os.path.join(atlas_path, "nodes.sqlite")):
            raise unittest.SkipTest("Full atlas not built")
        from src.models.narrative_atlas import NarrativeAtlas
        from src.utils.embedding_service import create_embedding_service

        cls.atlas = NarrativeAtlas(
            atlas_path, embedding_service=create_embedding_service("langchain")
        )

    def test_beorn_query_includes_skin_changer_definition(self):
        q = "Who is Beorn and what is a skin-changer?"
        results = self.atlas._retrieve_for_query(q, k=12)
        blob = " ".join(
            self.atlas.sequence_retriever._extract_text(n).lower() for n, _ in results
        )
        self.assertIn("skin-changer", blob)
        pages = {int(n.coordinates.t) for n, _ in results}
        self.assertIn(126, pages)
        for n, _ in results:
            self.assertLessEqual(n.coordinates.t, 150.0)


class TestArkenstoneRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        atlas_path = os.path.join(
            os.path.dirname(__file__), "..", "output", "hobbit_local_full"
        )
        if not os.path.exists(os.path.join(atlas_path, "nodes.sqlite")):
            raise unittest.SkipTest("Full atlas not built")
        from src.models.narrative_atlas import NarrativeAtlas
        from src.utils.embedding_service import create_embedding_service

        cls.atlas = NarrativeAtlas(
            atlas_path, embedding_service=create_embedding_service("langchain")
        )

    def test_arkenstone_query_stays_in_erebor_arc(self):
        q = "What is the Arkenstone and what role does it play with Smaug and the jewel?"
        results = self.atlas._retrieve_for_query(q, k=12)
        blob = " ".join(
            self.atlas.sequence_retriever._extract_text(n).lower() for n, _ in results
        )
        self.assertIn("arkenstone", blob)
        for n, _ in results:
            self.assertGreaterEqual(n.coordinates.t, 200.0)
            self.assertLessEqual(n.coordinates.t, 305.0)
        pages = {int(n.coordinates.t) for n, _ in results}
        self.assertTrue(pages.intersection(range(245, 290)), f"expected late-erebor pages, got {pages}")


class TestJewelQuestionRetrieval(unittest.TestCase):
    """Original user question: jewel + mountain + guardian must cite Erebor arc."""

    @classmethod
    def setUpClass(cls):
        atlas_path = os.path.join(
            os.path.dirname(__file__), "..", "output", "hobbit_local_full"
        )
        if not os.path.exists(os.path.join(atlas_path, "nodes.sqlite")):
            raise unittest.SkipTest("Full atlas not built")
        from src.models.narrative_atlas import NarrativeAtlas
        from src.utils.embedding_service import create_embedding_service

        cls.atlas = NarrativeAtlas(
            atlas_path, embedding_service=create_embedding_service("langchain")
        )

    def test_jewel_question_retrieval_in_erebor_region(self):
        q = (
            "What was the prized jewel that the dwarves were seeking, "
            "which mountain was it in and what was it being guarded by?"
        )
        results = self.atlas._retrieve_for_query(q, k=12)
        for n, _ in results:
            self.assertGreaterEqual(n.coordinates.t, 200.0)
            self.assertLessEqual(n.coordinates.t, 305.0)
        blob = " ".join(
            self.atlas.sequence_retriever._extract_text(n).lower() for n, _ in results
        )
        self.assertTrue(
            any(term in blob for term in ("smaug", "arkenstone", "erebor", "lonely mountain")),
            "expected Erebor/treasure vocabulary in retrieved context",
        )


if __name__ == "__main__":
    unittest.main()

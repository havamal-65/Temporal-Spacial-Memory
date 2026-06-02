"""
Unit tests for sequence-aware retrieval (SequenceRetriever).

These tests are deterministic and require no LLM: they build a tiny synthetic
atlas with a MockEmbeddingService and assert the core sequence guarantees:
- fetch_timeline returns passages in strictly t-ascending (story) order
- t-range filtering is respected
- get_neighbors returns the correct before/after window, in t order, anchor included
- assemble_sequence_context emits monotonic page labels and bounds passage size
- detect_sequence_intent classifies timeline / neighbor / point queries
"""

import os
import sys
import shutil
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from models.narrative_atlas import NarrativeAtlas
from models.sequence_retrieval import SequenceRetriever
from data_models import PolarTemporalCoordinate
from utils.embedding_service import MockEmbeddingService


def _coord(t, r=0.2, theta=0.5, z=1.0, z_type="DEFAULT"):
    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=z, z_type=z_type)


class TestSequenceRetriever(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="tsm_sequence_")
        cls.embedding_service = MockEmbeddingService(dimension=4)
        cls.atlas = NarrativeAtlas(
            storage_path=cls.test_dir,
            embedding_service=cls.embedding_service,
        )
        # Ten "events" at integer t = 1..10, inserted out of order to prove sorting.
        cls.t_values = [5, 1, 8, 3, 10, 2, 7, 4, 9, 6]
        for t in cls.t_values:
            nid = f"event_{t}"
            text = f"Event happening at sequence position {t}."
            emb = np.array(cls.embedding_service.embed_query(text), dtype=np.float32)
            cls.atlas.add_node(
                node_id=nid,
                content={"description": text},
                embedding=emb,
                metadata={"node_type": "event"},
                coordinates=_coord(float(t)),
            )
        cls.sr = SequenceRetriever(cls.atlas)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # --- intent detection (pure function) ------------------------------

    def test_detect_intent_timeline(self):
        for q in [
            "Summarize the main events in chronological order",
            "Give me a timeline of what happened",
            "List the events in order",
        ]:
            intent = SequenceRetriever.detect_sequence_intent(q)
            self.assertEqual(intent["mode"], "timeline", f"query: {q}")

    def test_detect_intent_neighbors_before_after(self):
        before = SequenceRetriever.detect_sequence_intent("What happened before the trolls?")
        self.assertEqual(before["mode"], "neighbors")
        self.assertEqual(before["direction"], "before")
        self.assertEqual(before["anchor"], "trolls")

        after = SequenceRetriever.detect_sequence_intent("What happened after Bilbo found the ring")
        self.assertEqual(after["mode"], "neighbors")
        self.assertEqual(after["direction"], "after")
        self.assertIn("bilbo", after["anchor"].lower())

    def test_detect_intent_point(self):
        intent = SequenceRetriever.detect_sequence_intent("Who is Gandalf?")
        self.assertEqual(intent["mode"], "point")

    # --- fetch_timeline ------------------------------------------------

    def test_fetch_timeline_orders_by_t(self):
        results = self.sr.fetch_timeline(k=20)
        ts = [node.coordinates.t for node, _ in results]
        self.assertEqual(len(ts), 10)
        self.assertEqual(ts, sorted(ts), "timeline must be t-ascending")
        self.assertEqual(ts, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_fetch_timeline_range_filter(self):
        results = self.sr.fetch_timeline(t_min=3.0, t_max=6.0, k=20)
        ts = [node.coordinates.t for node, _ in results]
        self.assertEqual(ts, [3, 4, 5, 6])

    def test_fetch_timeline_with_query_is_t_ordered(self):
        # Even when a semantic query selects/re-ranks candidates, the returned
        # passages must come back in narrative (t-ascending) order.
        results = self.sr.fetch_timeline(query="event at sequence position", k=20)
        ts = [node.coordinates.t for node, _ in results]
        self.assertGreater(len(ts), 0)
        self.assertEqual(ts, sorted(ts), "query timeline must still be t-ascending")

    # --- get_neighbors -------------------------------------------------

    def test_get_neighbors_before(self):
        results = self.sr.get_neighbors("event_5", direction="before", window=2.0, k=10)
        ts = [node.coordinates.t for node, _ in results]
        self.assertEqual(ts, [3, 4, 5], "before window [t0-2, t0] in t order, anchor included")

    def test_get_neighbors_after(self):
        results = self.sr.get_neighbors("event_5", direction="after", window=2.0, k=10)
        ts = [node.coordinates.t for node, _ in results]
        self.assertEqual(ts, [5, 6, 7], "after window [t0, t0+2] in t order, anchor included")

    def test_get_neighbors_both_includes_anchor(self):
        results = self.sr.get_neighbors("event_5", direction="both", window=2.0, k=10)
        ts = [node.coordinates.t for node, _ in results]
        self.assertEqual(ts, [3, 4, 5, 6, 7])
        # Anchor is flagged with score 1.0
        anchor_scores = [s for node, s in results if node.id == "event_5"]
        self.assertEqual(anchor_scores, [1.0])

    def test_resolve_anchor_by_id(self):
        node = self.sr.resolve_anchor("event_7")
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "event_7")

    # --- assemble_sequence_context -------------------------------------

    def test_assemble_context_monotonic_pages(self):
        results = self.sr.fetch_timeline(t_min=1.0, t_max=4.0, k=10)
        context = self.sr.assemble_sequence_context(results)
        # t=1 -> page 1 (int(t), not int(t)+1)
        self.assertIn("[Passage 1 of 4 - page 1", context)
        pages = [int(p) for p in __import__("re").findall(r"page (\d+)", context)]
        self.assertEqual(pages, sorted(pages))

    def test_assemble_context_truncates_long_passage(self):
        long_text = "x" * 5000
        node = self.atlas.db.nodes["event_1"]
        # Build a one-off result with an oversized content node (does not mutate store)
        from copy import copy
        big = copy(node)
        big.content = {"description": long_text}
        context = self.sr.assemble_sequence_context([(big, 0.0)], max_chars_per_passage=400)
        self.assertIn("...", context)
        self.assertLess(len(context), 700, "passage should be trimmed to the per-passage cap")

    def test_assemble_context_respects_token_budget(self):
        from src.utils.token_budget import count_tokens

        nodes = []
        for i in range(8):
            n = self.atlas.db.nodes.get(f"event_{i + 1}")
            if n is not None:
                nodes.append((n, 1.0 - i * 0.05))
        context = self.sr.assemble_sequence_context(nodes, max_total_tokens=100)
        self.assertLessEqual(count_tokens(context), 110)

    def test_parse_ref(self):
        self.assertEqual(SequenceRetriever.parse_ref("hobbit:40:3"), ("hobbit", 40, 3))
        self.assertEqual(SequenceRetriever.parse_ref("doc:with:colons:10:2"), ("doc:with:colons", 10, 2))
        self.assertIsNone(SequenceRetriever.parse_ref("bad-ref"))


class TestAddressableRetrieval(unittest.TestCase):
    """Isolated atlas for segment ref / text-window / expansion tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="tsm_addressable_")
        cls.embedding_service = MockEmbeddingService(dimension=4)
        cls.atlas = NarrativeAtlas(
            storage_path=cls.test_dir,
            embedding_service=cls.embedding_service,
        )
        cls.sr = SequenceRetriever(cls.atlas)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_resolve_ref_and_text_window(self):
        emb = np.array(self.embedding_service.embed_query("segment text"), dtype=np.float32)
        specs = [
            ("segment:test:5:1", 5.0, "First segment on page five.", "test:5:1"),
            ("segment:test:5:2", 5.25, "Second segment on page five.", "test:5:2"),
            ("segment:test:5:3", 5.5, "Third segment on page five.", "test:5:3"),
        ]
        for nid, t, text, ref in specs:
            self.atlas.add_node(
                node_id=nid,
                content={"text": text, "ref": ref},
                embedding=emb,
                metadata={"node_type": "segment", "ref": ref},
                coordinates=_coord(t),
            )
            self.atlas.db.nodes[nid].type = "segment"

        resolved = self.sr.resolve_ref("test:5:2")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, "segment:test:5:2")

        window = self.sr.get_text_window("test:5:2", before=1, after=1)
        ids = [n.id for n, _ in window]
        self.assertEqual(ids, ["segment:test:5:1", "segment:test:5:2", "segment:test:5:3"])
        ts = [n.coordinates.t for n, _ in window]
        self.assertEqual(ts, sorted(ts))

    def test_expand_results_with_refs_replaces_entity_with_segments(self):
        """Entity hits with source_refs expand into surrounding segment prose."""
        emb = np.array(self.embedding_service.embed_query("segment text"), dtype=np.float32)
        for nid, t, text, ref in [
            ("segment:test:8:1", 8.0, "Bilbo lived in a hole.", "test:8:1"),
            ("segment:test:8:2", 8.5, "He was a hobbit.", "test:8:2"),
        ]:
            self.atlas.add_node(
                node_id=nid,
                content={"text": text, "ref": ref},
                embedding=emb,
                metadata={"node_type": "segment", "ref": ref},
                coordinates=_coord(t),
            )
            self.atlas.db.nodes[nid].type = "segment"

        char_emb = np.array(self.embedding_service.embed_query("Bilbo Baggins"), dtype=np.float32)
        self.atlas.add_node(
            node_id="char_bilbo",
            content={"name": "Bilbo Baggins", "source_refs": ["test:8:1"]},
            embedding=char_emb,
            metadata={"node_type": "character", "source_refs": ["test:8:1"]},
            coordinates=_coord(8.0),
        )
        char_node = self.atlas.db.nodes["char_bilbo"]
        char_node.type = "character"

        entity_hit = [(char_node, 0.9)]
        expanded = self.sr.expand_results_with_refs(entity_hit, before=0, after=1)
        ids = [n.id for n, _ in expanded]
        self.assertIn("segment:test:8:1", ids)
        self.assertIn("segment:test:8:2", ids)
        self.assertNotIn("char_bilbo", ids)
        texts = " ".join(SequenceRetriever._extract_text(n) for n, _ in expanded)
        self.assertIn("hole", texts.lower())


if __name__ == "__main__":
    unittest.main()

"""
Integration smoke tests for addressable text ingest (Phase 6).

Validates output/addressable_test built by:
  python ingest_structured_atlas.py --input-pdf input/the_hobbit_tolkien.pdf \\
      --output-atlas-path output/addressable_test --start-page 1 --end-page 10 --overwrite

Skips automatically when the smoke atlas is not present (CI-friendly).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SMOKE_ATLAS = os.path.join(PROJECT_ROOT, "output", "addressable_test")


def _smoke_atlas_available() -> bool:
    return os.path.exists(os.path.join(SMOKE_ATLAS, "nodes.sqlite"))


@unittest.skipUnless(_smoke_atlas_available(), "Smoke atlas not found at output/addressable_test")
class TestAddressableSmoke(unittest.TestCase):
    """Assert segment store, FAISS index, and entity source_refs after pages 1-10 ingest."""

    @classmethod
    def setUpClass(cls):
        from src.models.narrative_atlas import NarrativeAtlas
        from src.utils.embedding_service import create_embedding_service

        cls.atlas = NarrativeAtlas(
            storage_path=SMOKE_ATLAS,
            embedding_service=create_embedding_service("langchain"),
        )

    def test_segment_nodes_exist(self):
        segments = [
            n for n in self.atlas.db.nodes.values()
            if getattr(n, "type", None) == "segment"
            or (n.metadata or {}).get("node_type") == "segment"
        ]
        self.assertGreater(len(segments), 0, "expected paragraph segment nodes")

    def test_faiss_index_populated(self):
        self.assertIsNotNone(self.atlas.vector_store)
        ntotal = self.atlas.vector_store.index.ntotal
        self.assertGreater(ntotal, 0, "FAISS index should contain segment embeddings")

    def test_entities_have_source_refs(self):
        with_refs = [
            n for n in self.atlas.db.nodes.values()
            if (n.content or {}).get("source_refs") or (n.metadata or {}).get("source_refs")
        ]
        self.assertGreater(len(with_refs), 0, "at least one entity should link to a segment ref")

    def test_segment_refs_are_parseable(self):
        from src.models.sequence_retrieval import SequenceRetriever

        segments = [
            n for n in self.atlas.db.nodes.values()
            if getattr(n, "type", None) == "segment"
        ]
        self.assertGreater(len(segments), 0)
        ref = (segments[0].content or {}).get("ref")
        self.assertIsNotNone(ref)
        parsed = SequenceRetriever.parse_ref(ref)
        self.assertIsNotNone(parsed)
        doc_id, page, para = parsed
        self.assertGreater(page, 0)
        self.assertGreater(para, 0)
        resolved = self.atlas.resolve_ref(ref)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, segments[0].id)

    def test_text_window_returns_prose(self):
        segments = [n for n in self.atlas.db.nodes.values() if getattr(n, "type", None) == "segment"]
        ref = segments[0].content.get("ref")
        window = self.atlas.get_text_window(ref, before=0, after=0)
        self.assertGreater(len(window), 0)
        from src.models.sequence_retrieval import SequenceRetriever
        text = SequenceRetriever._extract_text(window[0][0])
        self.assertGreater(len(text), 20, "segment window should return real prose")


if __name__ == "__main__":
    unittest.main()

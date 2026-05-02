"""
Integration tests for NarrativeAtlas end-to-end search pipeline.

Tests run entirely in-process (no subprocess calls) for reliability and speed.
They exercise the full chain: node ingestion → NL query parsing (mocked) → search.
"""

import os
import sys
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from models.narrative_atlas import NarrativeAtlas
from data_models import PolarTemporalCoordinate
from nl_parser import CoordinateFilters, ParsedQuery
from utils.embedding_service import MockEmbeddingService


def _coord(r, theta, t, z=1.0, z_type="DEFAULT"):
    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=z, z_type=z_type)


class TestNarrativeAtlasIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="tsm_integration_")
        cls.embedding_service = MockEmbeddingService(dimension=4)

        cls.atlas = NarrativeAtlas(
            storage_path=cls.test_dir,
            embedding_service=cls.embedding_service,
        )

        # Ingest three simple "documents" with distinct content and coordinates.
        docs = [
            ("node_A", {"text": "This is sample content about topic A."}, _coord(0.1, 0.2, 10.0)),
            ("node_B", {"text": "This is content related to topic B from yesterday."}, _coord(0.2, 1.5, 20.0)),
            ("node_C", {"text": "Completely different unique text about topic C."}, _coord(0.3, 3.0, 30.0)),
        ]
        for nid, content, coords in docs:
            text = content["text"]
            emb = np.array(cls.embedding_service.embed_query(text), dtype=np.float32)
            cls.atlas.add_node(
                node_id=nid,
                content=content,
                embedding=emb,
                metadata={"node_type": "chunk", "source": "integration_test"},
                coordinates=coords,
            )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------

    def _mocked_parse(self, query_text, filters=None, limit=5):
        """Return a ParsedQuery as if the NL parser processed the input."""
        return ParsedQuery(
            query_text=query_text,
            filters=filters or CoordinateFilters(),
            limit=limit,
        )

    # ------------------------------------------------------------------

    def test_nl_query_end_to_end_simple(self):
        """Simple query with no filters should return nodes."""
        parsed = self._mocked_parse("topic A")
        with patch.object(self.atlas.nl_parser, "parse", return_value=parsed):
            results = self.atlas.search_with_nl_query("Tell me about topic A", k=3)

        self.assertGreater(len(results), 0, "Expected at least one result")
        node_ids = {node.id for node, _ in results}
        # node_A should be among the top results (its embedding was generated from topic A text)
        self.assertIn("node_A", node_ids, "node_A should appear in results for topic A query")

    def test_nl_query_with_filters(self):
        """Strict r_max filter should exclude nodes with r > threshold."""
        # Only node_A has r=0.1; nodes B and C have r=0.2 and 0.3
        filters = CoordinateFilters(r_max=0.15)
        parsed = self._mocked_parse("topic B", filters=filters)
        with patch.object(self.atlas.nl_parser, "parse", return_value=parsed):
            results = self.atlas.search_with_nl_query("Find highly relevant info on topic B", k=10)

        # With r_max=0.15, only node_A (r=0.1) qualifies
        node_ids = {node.id for node, _ in results}
        self.assertNotIn("node_B", node_ids, "node_B (r=0.2) should be excluded")
        self.assertNotIn("node_C", node_ids, "node_C (r=0.3) should be excluded")

    def test_nl_query_time_filter_only(self):
        """t_max filter should exclude nodes with t > threshold."""
        # node_A: t=10, node_B: t=20, node_C: t=30
        filters = CoordinateFilters(t_max=15.0)
        parsed = self._mocked_parse("anything", filters=filters)
        with patch.object(self.atlas.nl_parser, "parse", return_value=parsed):
            results = self.atlas.search_with_nl_query("Find info about anything older", k=10)

        node_ids = {node.id for node, _ in results}
        self.assertIn("node_A", node_ids, "node_A (t=10) should pass t_max=15 filter")
        self.assertNotIn("node_B", node_ids, "node_B (t=20) should fail t_max=15 filter")
        self.assertNotIn("node_C", node_ids, "node_C (t=30) should fail t_max=15 filter")


if __name__ == "__main__":
    unittest.main()

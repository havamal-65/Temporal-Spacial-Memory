"""
Tests for NarrativeAtlas coordinate filtering.

Covers _get_ids_matching_filters() — the SQL-backed pre-filter that
narrows candidates before vector similarity scoring.

No FAISS index or embedding service is required for these tests because
filtering operates entirely on the SQLite coordinate store.
"""

import sys
import os
import time
import unittest
import numpy as np
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.narrative_atlas import NarrativeAtlas, Node
from src.data_models import PolarTemporalCoordinate
from src.nl_parser import CoordinateFilters
from src.utils.embedding_service import MockEmbeddingService


def _coord(r: float, theta: float, t: float, z: float = 1.0,
           z_type: str = "DEFAULT") -> PolarTemporalCoordinate:
    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=z, z_type=z_type)


def _node(node_id: str, coords: PolarTemporalCoordinate, dim: int = 4) -> Node:
    return Node(
        id=node_id,
        type="chunk",
        content={"text": f"content for {node_id}"},
        coordinates=coords,
        embedding=np.zeros(dim, dtype=np.float32),
        keywords=None,
        metadata={},
        parent_node_id=None,
        timestamp=time.time(),
        mapping_details={},
    )


class TestNarrativeAtlasFiltering(unittest.TestCase):

    def setUp(self):
        self.emb_svc = MockEmbeddingService(dimension=4)

        # Patch FAISS so no real index is created
        self._patcher = patch("src.models.narrative_atlas.FAISS")
        mock_faiss_cls = self._patcher.start()
        mock_faiss_cls.load_local.side_effect = Exception("no index on disk")
        mock_faiss_inst = MagicMock()
        mock_faiss_inst.index.d = 4
        mock_faiss_cls.return_value = mock_faiss_inst

        self.atlas = NarrativeAtlas(
            storage_path="./test_atlas_storage",
            embedding_service=self.emb_svc,
        )

        # Nodes — 8 entries mirroring the original test intent:
        # node1:  r=0.10, theta=1.0, t=100, z=1   → matches (r<=0.5, 100<=t<=200, 1<=z<=1)
        # node2:  r=0.60, theta=2.0, t=150, z=1   → fails r_max
        # node3:  r=0.20, theta=3.0, t=50,  z=1   → fails t_min
        # node4:  r=0.30, theta=4.0, t=250, z=1   → fails t_max
        # node5:  r=0.40, theta=5.0, t=180, z=2   → fails z_max (z=2 > 1)
        # node6:  r=0.15, theta=0.5, t=120, z=1   → matches
        # node7:  r=0.05, theta=1.5, t=110, z=0   → fails z_min (z=0 < 1)
        # node8:  r=0.90, theta=1.0, t=100, z=1   → fails r_max
        self._nodes = {
            "node1": _node("node1", _coord(0.10, 1.0, 100, 1.0)),
            "node2": _node("node2", _coord(0.60, 2.0, 150, 1.0)),
            "node3": _node("node3", _coord(0.20, 3.0,  50, 1.0)),
            "node4": _node("node4", _coord(0.30, 4.0, 250, 1.0)),
            "node5": _node("node5", _coord(0.40, 5.0, 180, 2.0)),
            "node6": _node("node6", _coord(0.15, 0.5, 120, 1.0)),
            "node7": _node("node7", _coord(0.05, 1.5, 110, 0.0)),
            "node8": _node("node8", _coord(0.90, 1.0, 100, 1.0)),
        }
        for node in self._nodes.values():
            self.atlas.db.add_node(node)

    def tearDown(self):
        self._patcher.stop()
        self.atlas.db.clear_all()

    # ------------------------------------------------------------------

    def test_coordinate_filtering(self):
        filters = CoordinateFilters(r_max=0.5, t_min=100, t_max=200, z_min=1, z_max=1)
        result = self.atlas._get_ids_matching_filters(filters)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, set)
        self.assertEqual(result, {"node1", "node6"})

    def test_filtering_no_filters(self):
        filters = CoordinateFilters()
        result = self.atlas._get_ids_matching_filters(filters)
        self.assertIsNone(result)

    def test_filtering_no_matches(self):
        filters = CoordinateFilters(r_max=0.01)
        result = self.atlas._get_ids_matching_filters(filters)
        self.assertIsNotNone(result)
        self.assertEqual(result, set())

    def test_filtering_only_one_filter(self):
        # Only nodes with z >= 2
        filters = CoordinateFilters(z_min=2)
        result = self.atlas._get_ids_matching_filters(filters)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"node5"})

    def test_theta_wrap_around_N_sector(self):
        # N sector: theta_min > theta_max (wraps around 0/2π boundary)
        # Nodes node1 (theta=1.0) and node8 (theta=1.0) should NOT match;
        # a node near theta≈0 or theta≈6.28 should match.
        import math
        half = math.pi / 8
        theta_min = 2 * math.pi - half  # ≈ 5.89
        theta_max = half                # ≈ 0.39

        # Add a node near theta=0.1 (inside N sector)
        n_node = _node("node_n", _coord(0.5, 0.1, 100, 1.0))
        self.atlas.db.add_node(n_node)

        filters = CoordinateFilters(theta_min=theta_min, theta_max=theta_max)
        result = self.atlas._get_ids_matching_filters(filters)
        self.assertIn("node_n", result)
        # node1 has theta=1.0 which is between 0.39 and 5.89 — not in N sector
        self.assertNotIn("node1", result)


if __name__ == "__main__":
    unittest.main()

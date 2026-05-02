"""
Regression Test Suite for Temporal-Spatial Memory System.

Tests verify that core NarrativeAtlas operations continue to work correctly
after code changes.  Run after every significant change.
"""

import os
import sys
import shutil
import tempfile
import unittest
import numpy as np
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from models.narrative_atlas import NarrativeAtlas, Node
from data_models import PolarTemporalCoordinate
from nl_parser import CoordinateFilters
from utils.embedding_service import MockEmbeddingService

logger = logging.getLogger("RegressionTest")


def _coord(r, theta, t, z=1.0, z_type="DEFAULT") -> PolarTemporalCoordinate:
    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=z, z_type=z_type)


class RegressionTestSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="tsm_regression_")
        cls.embedding_service = MockEmbeddingService(dimension=4)

        cls.sample_coordinates = [
            _coord(r=0.1, theta=0.2, t=10, z=1.0, z_type="DEFAULT"),
            _coord(r=0.3, theta=1.5, t=20, z=2.0, z_type="LAYER_MAIN"),
            _coord(r=0.7, theta=3.0, t=30, z=3.0, z_type="PERSPECTIVE"),
        ]
        cls.sample_content = [
            {"text": "Sample content for node 0 — adventure and action."},
            {"text": "Sample content for node 1 — technical details and how-to."},
            {"text": "Sample content for node 2 — unique historical analysis text."},
        ]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        self.atlas_path = os.path.join(self.test_dir, f"atlas_{self._testMethodName}")
        os.makedirs(self.atlas_path, exist_ok=True)
        self.atlas = NarrativeAtlas(
            storage_path=self.atlas_path,
            embedding_service=self.embedding_service,
        )
        self.test_nodes = []
        for i in range(3):
            node_id = f"test_node_{i}"
            text = self.sample_content[i]["text"]
            emb = np.array(self.embedding_service.embed_query(text), dtype=np.float32)
            self.atlas.add_node(
                node_id=node_id,
                content=self.sample_content[i],
                embedding=emb,
                metadata={"node_type": "test"},
                coordinates=self.sample_coordinates[i],
            )
            self.test_nodes.append(node_id)

    def tearDown(self):
        self.atlas = None

    # ------------------------------------------------------------------

    def test_node_retrieval(self):
        for node_id in self.test_nodes:
            node = self.atlas.get_node(node_id)
            self.assertIsNotNone(node, f"Node {node_id} not found")
            self.assertEqual(node.id, node_id)

    def test_coordinate_properties(self):
        for i, node_id in enumerate(self.test_nodes):
            node = self.atlas.get_node(node_id)
            self.assertIsNotNone(node.coordinates)
            expected = self.sample_coordinates[i]
            self.assertAlmostEqual(node.coordinates.r, expected.r, places=6)
            self.assertAlmostEqual(node.coordinates.theta, expected.theta, places=6)
            self.assertAlmostEqual(node.coordinates.z, expected.z, places=6)
            self.assertAlmostEqual(node.coordinates.t, expected.t, places=6)
            self.assertEqual(node.coordinates.z_type, expected.z_type)

    def test_node_update(self):
        node_id = self.test_nodes[0]
        new_coords = _coord(r=0.9, theta=4.5, t=10)
        self.atlas.update_node_coordinates(node_id, new_coords)
        updated = self.atlas.get_node(node_id)
        self.assertAlmostEqual(updated.coordinates.r, 0.9, places=6)
        self.assertAlmostEqual(updated.coordinates.theta, 4.5, places=6)

    def test_node_removal(self):
        node_id = self.test_nodes[0]
        result = self.atlas.remove_node(node_id)
        self.assertTrue(result)
        self.assertIsNone(self.atlas.get_node(node_id))
        # Other nodes must still exist
        for nid in self.test_nodes[1:]:
            self.assertIsNotNone(self.atlas.get_node(nid))

    def test_similarity_search(self):
        results = self.atlas.find_similar_nodes("sample content", k=2)
        self.assertEqual(len(results), 2)
        for node, score in results:
            self.assertIsInstance(node, Node)
            self.assertIsInstance(score, (float, np.floating))

    def test_filter_search(self):
        filters = CoordinateFilters(r_max=0.5, t_min=5, t_max=25)
        ids = self.atlas._get_ids_matching_filters(filters)
        self.assertIsNotNone(ids)
        # node 0: r=0.1, t=10 → matches; node 1: r=0.3, t=20 → matches; node 2: r=0.7 > 0.5 → fails
        self.assertIn("test_node_0", ids)
        self.assertIn("test_node_1", ids)
        self.assertNotIn("test_node_2", ids)

    def test_persistence(self):
        new_atlas = NarrativeAtlas(
            storage_path=self.atlas_path,
            embedding_service=self.embedding_service,
        )
        for node_id in self.test_nodes:
            self.assertIsNotNone(new_atlas.get_node(node_id), f"{node_id} missing after reload")

    def test_large_atlas_operations(self):
        large_path = os.path.join(self.test_dir, "large_atlas")
        os.makedirs(large_path, exist_ok=True)
        large_atlas = NarrativeAtlas(storage_path=large_path, embedding_service=self.embedding_service)

        num_nodes = 50
        for i in range(num_nodes):
            coords = _coord(
                r=0.1 + (i % 10) * 0.09,
                theta=(i % 8) * np.pi / 4,
                t=float(i * 5),
                z=float(1 + (i % 3)),
            )
            large_atlas.add_node(
                node_id=f"large_node_{i}",
                content={"text": f"Content for large node {i}"},
                embedding=None,
                metadata={"node_type": "large_test"},
                coordinates=coords,
            )

        self.assertEqual(len(large_atlas.db.nodes), num_nodes)

        # Update coordinates for first 5 nodes
        for i in range(5):
            nid = f"large_node_{i}"
            new_c = _coord(r=0.99, theta=0.0, t=0.0)
            large_atlas.update_node_coordinates(nid, new_c)
            updated = large_atlas.get_node(nid)
            self.assertAlmostEqual(updated.coordinates.r, 0.99, places=4)


def run_regression_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(RegressionTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    run_regression_tests()

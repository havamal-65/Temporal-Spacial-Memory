"""
Unit tests for the sector-based query layer.

Tests cover three concerns:
  1. TestSectorToThetaRange  — _sectors_to_theta_range() conversion formula
  2. TestDeriveSectorsFromQuery — _derive_sectors_from_query() via SectorLegend
  3. TestCategoryMapping — CATEGORY_TO_SECTOR completeness / uniqueness

No NarrativeAtlas instance is required; all tested symbols are module-level.
"""

import math
import sys
import os
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.narrative_atlas import (
    CATEGORY_TO_SECTOR,
    Node,
    _sectors_to_theta_range,
    _sectors_to_theta_ranges,
    _derive_sectors_from_query,
)
from src.models.spatial_temporal_db import SpatialTemporalDB
from src.data_models import PolarTemporalCoordinate
from src.utils.semantic_compass import SemanticCompassMapper

SECTOR_ANGLES = SemanticCompassMapper.SECTOR_ANGLES
TWO_PI = 2 * math.pi
HALF = math.pi / 8  # expected half-width for each 8-sector


class TestSectorToThetaRange(unittest.TestCase):

    def test_N_wrap_around(self):
        lo, hi = _sectors_to_theta_range(["N"])
        self.assertGreater(lo, hi, "N sector should produce theta_min > theta_max (wrap-around)")
        self.assertAlmostEqual(lo, TWO_PI - HALF, places=10)
        self.assertAlmostEqual(hi, HALF, places=10)

    def test_non_N_sectors_symmetric(self):
        for sector in ("NE", "E", "SE", "S", "SW", "W", "NW"):
            with self.subTest(sector=sector):
                lo, hi = _sectors_to_theta_range([sector])
                self.assertAlmostEqual(hi - lo, math.pi / 4, places=10,
                                       msg=f"{sector}: full width should be π/4")
                center = SECTOR_ANGLES[sector]
                self.assertAlmostEqual((lo + hi) / 2, center, places=10,
                                       msg=f"{sector}: midpoint should equal sector center")

    def test_empty_returns_none(self):
        self.assertIsNone(_sectors_to_theta_range([]))

    def test_invalid_names_returns_none(self):
        self.assertIsNone(_sectors_to_theta_range(["NbE", "ZZZ", "Northeast"]))

    def test_multi_sector_uses_first_valid(self):
        result_e_se = _sectors_to_theta_range(["E", "SE"])
        result_e = _sectors_to_theta_range(["E"])
        self.assertEqual(result_e_se, result_e,
                         "Multiple sectors should use only the first valid entry")

    def test_first_invalid_skipped_to_second(self):
        result = _sectors_to_theta_range(["ZZZ", "W"])
        expected = _sectors_to_theta_range(["W"])
        self.assertEqual(result, expected,
                         "Invalid leading entries should be skipped; first valid sector is used")


class TestDeriveSectorsFromQuery(unittest.TestCase):

    def test_adventure_query_yields_N(self):
        sectors = _derive_sectors_from_query("heroic quest adventure journey battle")
        self.assertIn("N", sectors, f"Expected 'N' in {sectors}")

    def test_technical_query_yields_NE(self):
        sectors = _derive_sectors_from_query("how to install and configure the application")
        self.assertIn("NE", sectors, f"Expected 'NE' in {sectors}")

    def test_scientific_query_yields_E(self):
        sectors = _derive_sectors_from_query("statistical analysis experimental data research results")
        self.assertIn("E", sectors, f"Expected 'E' in {sectors}")

    def test_historical_query_yields_W(self):
        sectors = _derive_sectors_from_query("ancient history chronicles past events civilization")
        self.assertIn("W", sectors, f"Expected 'W' in {sectors}")

    def test_below_threshold_returns_empty(self):
        # Single common word — no keyword match, well below 0.3
        sectors = _derive_sectors_from_query("the", confidence_threshold=0.3)
        self.assertEqual(sectors, [], f"Expected empty list, got {sectors}")

    def test_returns_list_of_strings(self):
        sectors = _derive_sectors_from_query("adventure quest")
        self.assertIsInstance(sectors, list)
        for s in sectors:
            self.assertIsInstance(s, str)

    def test_no_duplicates(self):
        sectors = _derive_sectors_from_query("adventure quest journey battle warriors")
        self.assertEqual(len(sectors), len(set(sectors)), "Returned sectors should be unique")


class TestCategoryMapping(unittest.TestCase):

    def test_all_eight_sectors_covered(self):
        expected = set(SECTOR_ANGLES.keys())
        mapped = set(CATEGORY_TO_SECTOR.values())
        self.assertEqual(mapped, expected,
                         f"Missing sectors: {expected - mapped}, extra: {mapped - expected}")

    def test_unique_mapping(self):
        values = list(CATEGORY_TO_SECTOR.values())
        self.assertEqual(len(values), len(set(values)),
                         f"Duplicate sector assignments: {values}")

    def test_eight_categories(self):
        self.assertEqual(len(CATEGORY_TO_SECTOR), 8,
                         "Should have exactly 8 category-to-sector mappings")

    def test_all_keys_are_lowercase(self):
        for key in CATEGORY_TO_SECTOR:
            self.assertEqual(key, key.lower(), f"Key '{key}' is not lowercase")


class TestSectorsToThetaRanges(unittest.TestCase):
    """Tests for _sectors_to_theta_ranges (plural) — returns all sector ranges."""

    def test_single_sector_returns_one_range(self):
        ranges = _sectors_to_theta_ranges(["E"])
        self.assertEqual(len(ranges), 1)
        lo, hi = ranges[0]
        expected_lo, expected_hi = _sectors_to_theta_range(["E"])
        self.assertAlmostEqual(lo, expected_lo)
        self.assertAlmostEqual(hi, expected_hi)

    def test_multi_sector_returns_all_ranges(self):
        ranges = _sectors_to_theta_ranges(["W", "S"])
        self.assertEqual(len(ranges), 2)
        w_range = _sectors_to_theta_range(["W"])
        s_range = _sectors_to_theta_range(["S"])
        self.assertAlmostEqual(ranges[0][0], w_range[0])
        self.assertAlmostEqual(ranges[0][1], w_range[1])
        self.assertAlmostEqual(ranges[1][0], s_range[0])
        self.assertAlmostEqual(ranges[1][1], s_range[1])

    def test_N_wrap_around_in_list(self):
        ranges = _sectors_to_theta_ranges(["N"])
        self.assertEqual(len(ranges), 1)
        lo, hi = ranges[0]
        self.assertGreater(lo, hi, "N sector should produce lo > hi (wrap-around)")
        self.assertAlmostEqual(lo, TWO_PI - HALF, places=10)
        self.assertAlmostEqual(hi, HALF, places=10)

    def test_empty_returns_empty_list(self):
        self.assertEqual(_sectors_to_theta_ranges([]), [])

    def test_invalid_sectors_skipped(self):
        ranges = _sectors_to_theta_ranges(["ZZZ", "W", "INVALID"])
        self.assertEqual(len(ranges), 1)
        w_range = _sectors_to_theta_range(["W"])
        self.assertAlmostEqual(ranges[0][0], w_range[0])
        self.assertAlmostEqual(ranges[0][1], w_range[1])

    def test_all_eight_sectors_produce_ranges(self):
        all_sectors = list(SECTOR_ANGLES.keys())
        ranges = _sectors_to_theta_ranges(all_sectors)
        self.assertEqual(len(ranges), 8)

    def test_plural_differs_from_singular_on_multi(self):
        # singular uses only first valid; plural returns both
        singular = _sectors_to_theta_range(["W", "S"])
        plural = _sectors_to_theta_ranges(["W", "S"])
        w_range = _sectors_to_theta_range(["W"])
        self.assertEqual(singular, w_range)   # singular → first sector only
        self.assertEqual(len(plural), 2)       # plural → both sectors


def _make_node(node_id: str, theta: float) -> Node:
    coords = PolarTemporalCoordinate(r=0.5, theta=theta, t=1.0, z=1.0, z_type="DEFAULT")
    return Node(
        id=node_id,
        type="event",
        content={"text": node_id},
        coordinates=coords,
        embedding=None,
        keywords=None,
        metadata={},
        parent_node_id=None,
        timestamp=time.time(),
        mapping_details={},
    )


class TestMultiRangeQuery(unittest.TestCase):
    """Tests for SpatialTemporalDB.query_by_coordinate_range with theta_ranges."""

    def setUp(self):
        self.db = SpatialTemporalDB(":memory:")
        angles = SemanticCompassMapper.SECTOR_ANGLES
        # Insert one node near the centre of each sector
        for name, center in angles.items():
            self.db.add_node(_make_node(f"node_{name}", center))

    def tearDown(self):
        self.db.close()

    def _sector_theta_ranges(self, *sectors):
        return _sectors_to_theta_ranges(list(sectors))

    def test_single_range_returns_one_sector(self):
        ranges = self._sector_theta_ranges("E")
        ids = self.db.query_by_coordinate_range(theta_ranges=ranges)
        self.assertIn("node_E", ids)
        self.assertNotIn("node_W", ids)

    def test_two_ranges_return_both_sectors(self):
        ranges = self._sector_theta_ranges("W", "S")
        ids = self.db.query_by_coordinate_range(theta_ranges=ranges)
        self.assertIn("node_W", ids, "W sector node should be included")
        self.assertIn("node_S", ids, "S sector node should be included")
        self.assertNotIn("node_E", ids, "E sector node should be excluded")
        self.assertNotIn("node_NE", ids, "NE sector node should be excluded")

    def test_N_sector_wrap_around(self):
        ranges = self._sector_theta_ranges("N")
        ids = self.db.query_by_coordinate_range(theta_ranges=ranges)
        self.assertIn("node_N", ids)
        self.assertNotIn("node_S", ids)

    def test_empty_theta_ranges_returns_all(self):
        ids = self.db.query_by_coordinate_range(theta_ranges=[])
        self.assertEqual(ids, set(self.db.nodes.keys()))

    def test_none_theta_ranges_falls_back_to_single(self):
        w_range = _sectors_to_theta_range(["W"])
        ids = self.db.query_by_coordinate_range(
            theta_min=w_range[0], theta_max=w_range[1]
        )
        self.assertIn("node_W", ids)
        self.assertNotIn("node_E", ids)

    def test_theta_ranges_excludes_out_of_band(self):
        # Query only W and E — every other sector should be absent
        ranges = self._sector_theta_ranges("W", "E")
        ids = self.db.query_by_coordinate_range(theta_ranges=ranges)
        self.assertIn("node_W", ids)
        self.assertIn("node_E", ids)
        for sector in ("N", "NE", "SE", "S", "SW", "NW"):
            self.assertNotIn(f"node_{sector}", ids,
                             f"node_{sector} should not be in W+E result")


if __name__ == "__main__":
    unittest.main()

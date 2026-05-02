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
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.narrative_atlas import (
    CATEGORY_TO_SECTOR,
    _sectors_to_theta_range,
    _derive_sectors_from_query,
)
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


if __name__ == "__main__":
    unittest.main()

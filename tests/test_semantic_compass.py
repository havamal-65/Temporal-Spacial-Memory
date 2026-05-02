"""
Tests for SemanticCompassMapper — real embedding validation.

Three test layers:
  1. TestSemanticCompassUnit       — individual sentences → expected sector
  2. TestSemanticCompassDistribution — diverse corpus spreads across ≥4 sectors
  3. TestSemanticCompassQueryAlignment — query lands in same sector as matching docs

All tests use the real sentence-transformer model (all-MiniLM-L6-v2), not mocks.
Deterministic: same text → same embedding → same sector every run.
"""

import unittest
import sys
import os
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.embedding_service import LangchainEmbeddingService
from src.utils.semantic_compass import SemanticCompassMapper


def _make_compass() -> SemanticCompassMapper:
    """Shared helper: real sentence-transformer, shared across test classes."""
    svc = LangchainEmbeddingService(
        model_provider='sentence_transformer',
        model_name='all-MiniLM-L6-v2',
        cache_dir='./cache/embeddings',
    )
    return SemanticCompassMapper(svc)


# Build once at module load so all test classes share the same model instance.
_COMPASS: SemanticCompassMapper = _make_compass()


def _embed(text: str) -> np.ndarray:
    return np.array(_COMPASS.embedding_service.embed_query(text))


class TestSemanticCompassUnit(unittest.TestCase):
    """
    Each test verifies that a clearly domain-specific sentence is assigned
    to its expected compass sector.

    Test sentences use concrete proper nouns / domain vocabulary intentionally
    different from the generic reference sentences inside SemanticCompassMapper,
    so the classifier must generalise rather than pattern-match surface words.
    """

    def _assert_sector(self, text: str, expected: str, msg: str = ""):
        embedding = _embed(text)
        sector, theta = _COMPASS.embedding_to_sector(embedding)
        self.assertEqual(
            sector, expected,
            msg=f"{msg}\n  text: {text!r}\n  expected: {expected}, got: {sector}\n"
                f"  similarities: {_COMPASS.get_sector_similarities(embedding)}",
        )

    def test_action_adventure_lands_in_N(self):
        # Clear combat/quest narrative — should be North (action/adventure)
        self._assert_sector(
            "Aragorn raised Andúril and charged through the ranks of Mordor's army",
            "N",
        )

    def test_scientific_measurement_lands_in_E(self):
        # Laboratory measurement with numerical result — East (scientific/analytical)
        self._assert_sector(
            "The gel electrophoresis confirmed a 450 base-pair amplicon at 0.8% agarose concentration",
            "E",
        )

    def test_historical_chronicle_lands_in_W(self):
        # Named historical event with date — West (historical/reflective)
        self._assert_sector(
            "The fall of Constantinople in 1453 ended twelve centuries of Byzantine rule",
            "W",
        )

    def test_creative_artistic_lands_in_S(self):
        # Musical performance / emotional description — South (creative/expressive)
        self._assert_sector(
            "Beethoven's Ninth Symphony builds to a transcendent choral climax in the final movement",
            "S",
        )

    def test_technical_instructional_lands_in_NE(self):
        # Step-by-step procedural guide — Northeast (technical/how-to)
        self._assert_sector(
            "Open the settings panel, follow the on-screen installation wizard, and click Finish to complete the setup",
            "NE",
        )

    def test_philosophical_abstract_lands_in_NW(self):
        # Abstract argument about free will — Northwest (philosophical/theoretical)
        self._assert_sector(
            "Kant's categorical imperative grounds moral obligation in pure practical reason",
            "NW",
        )


class TestSemanticCompassDistribution(unittest.TestCase):
    """
    Passes a diverse corpus through the mapper and verifies that content
    spreads across multiple sectors — not all piling into one bucket.

    The minimum bar is 4 distinct sectors from 8 clearly different topics.
    """

    CORPUS = [
        # N — action
        "The knight unsheathed his sword and spurred his horse into the fray",
        # NE — instructional
        "Run pip install -r requirements.txt then copy config.env.example to .env",
        # E — scientific
        "Spectroscopic analysis revealed an absorption peak at 532 nm wavelength",
        # SE — educational reference
        "This chapter introduces the key terminology and foundational concepts of thermodynamics",
        # S — creative
        "The cellist drew a long bow across the strings filling the hall with melancholy",
        # SW — personal lifestyle
        "Meal prep on Sundays makes it easier to stick to a balanced diet during the week",
        # W — historical
        "Roman legions withdrew from Britain in 410 AD leaving the province to defend itself",
        # NW — philosophical
        "Wittgenstein argued that the limits of language are the limits of one's world",
    ]

    def test_at_least_four_sectors_assigned(self):
        sectors_seen = set()
        for text in self.CORPUS:
            emb = _embed(text)
            sector, _ = _COMPASS.embedding_to_sector(emb)
            sectors_seen.add(sector)

        self.assertGreaterEqual(
            len(sectors_seen),
            4,
            msg=f"Only {len(sectors_seen)} unique sectors seen: {sectors_seen}. "
                "Content is over-clustering — reference centroids may not be discriminative enough.",
        )

    def test_no_single_sector_takes_majority(self):
        counts: dict = {}
        for text in self.CORPUS:
            emb = _embed(text)
            sector, _ = _COMPASS.embedding_to_sector(emb)
            counts[sector] = counts.get(sector, 0) + 1

        total = len(self.CORPUS)
        for sector, count in counts.items():
            self.assertLess(
                count / total,
                0.5,
                msg=f"Sector {sector!r} claimed {count}/{total} items ({count/total:.0%}). "
                    "This suggests degenerate sector assignment.",
            )


class TestSemanticCompassQueryAlignment(unittest.TestCase):
    """
    Verifies that a natural-language query lands in the same sector as the
    documents it should retrieve.

    This is the most important functional test: if a user asks about "heroic battles",
    the system should route that query toward North-sector content, not
    East (science) or W (history).
    """

    def _sector_of(self, text: str) -> str:
        emb = _embed(text)
        sector, _ = _COMPASS.embedding_to_sector(emb)
        return sector

    def test_adventure_query_matches_adventure_docs(self):
        query = "heroic battle sword fighting warriors quest"

        # Documents that clearly belong to the same category as the query
        matching_docs = [
            "Thorin Oakenshield drew his axe and led the dwarves into battle against the goblins",
            "The hero fought through wave after wave of enemies to reach the fortress gate",
        ]
        # Documents that belong to a different category
        non_matching_docs = [
            "Atmospheric CO2 concentrations reached 420 ppm in 2023",
            "The collapse of the Western Roman Empire began in the 3rd century AD",
        ]

        query_sector = self._sector_of(query)

        for doc in matching_docs:
            doc_sector = self._sector_of(doc)
            self.assertEqual(
                query_sector, doc_sector,
                msg=f"Adventure query landed in {query_sector!r} but matching doc landed in "
                    f"{doc_sector!r}.\n  Query: {query!r}\n  Doc: {doc!r}",
            )

        for doc in non_matching_docs:
            doc_sector = self._sector_of(doc)
            self.assertNotEqual(
                query_sector, doc_sector,
                msg=f"Adventure query and non-matching doc both landed in {query_sector!r} — "
                    f"compass is not discriminating enough.\n  Doc: {doc!r}",
            )

    def test_science_query_matches_science_docs(self):
        query = "experimental data statistical analysis laboratory measurement results"

        matching_docs = [
            "The researchers recorded voltage and current at 100 ms intervals and computed resistance",
            "Chromatography confirmed a retention time of 4.2 minutes for the compound at 254 nm UV detection",
        ]
        non_matching_docs = [
            "She whispered verses beneath the olive tree as the sun sank into the sea",
            "Clean your cast-iron skillet with coarse salt and a paper towel after cooking",
        ]

        query_sector = self._sector_of(query)

        for doc in matching_docs:
            self.assertEqual(
                query_sector, self._sector_of(doc),
                msg=f"Science query ({query_sector}) and doc disagree.\n  Doc: {doc!r}",
            )

        for doc in non_matching_docs:
            self.assertNotEqual(
                query_sector, self._sector_of(doc),
                msg=f"Science query and non-matching doc both in {query_sector!r}.\n  Doc: {doc!r}",
            )

    def test_get_sector_similarities_returns_all_eight(self):
        emb = _embed("a neutral test sentence")
        sims = _COMPASS.get_sector_similarities(emb)
        self.assertEqual(set(sims.keys()), {"N", "NE", "E", "SE", "S", "SW", "W", "NW"})
        for sector, score in sims.items():
            self.assertGreaterEqual(score, -1.0)
            self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()

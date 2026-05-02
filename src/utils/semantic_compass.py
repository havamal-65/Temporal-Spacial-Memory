"""
Semantic Compass Mapper

Maps document embeddings to compass directions using cosine similarity
against precomputed reference centroids. This gives theta a real semantic
meaning instead of the arbitrary arctan2(emb[1], emb[0]) calculation.

Each of the 8 directions represents a broad content category. The theta
value stored is the center angle of the matched sector — 8 discrete values.
This is a v1 tradeoff: loses within-sector gradient in exchange for clean
queryability ("find all N-sector content").

Existing atlas data encoded with the old arctan2 approach needs re-ingestion
to benefit from semantic sectors.
"""

import numpy as np
import math
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger('SemanticCompass')


class SemanticCompassMapper:
    """
    Assigns a compass sector to a document embedding by finding the
    reference centroid with the highest cosine similarity.
    """

    # Archetypal reference sentences — one group per direction.
    # These intentionally use generic/abstract phrasing so the classifier
    # generalises to specific examples without overfitting.
    REFERENCE_SENTENCES: Dict[str, List[str]] = {
        "N": [
            "The warrior drew his sword and charged into the fray",
            "Heroes set out on a perilous quest through unknown lands",
            "A fierce battle erupted as the armies clashed at dawn",
            "She leaped across the rooftop in pursuit of the thief",
        ],
        "NE": [
            "Follow these steps to install and configure the application",
            "The manual describes how to operate the device correctly",
            "Troubleshooting guide for resolving common system errors",
            "Procedures for setting up network infrastructure and services",
        ],
        "E": [
            "The experiment recorded measurements at controlled intervals",
            "Statistical analysis confirmed a significant correlation",
            "The compound was synthesised and characterised by spectroscopy",
            "Sensor data was collected and processed to validate the model",
        ],
        "SE": [
            "An introductory overview of the subject for new learners",
            "Background reading covering the key concepts and terminology",
            "Reference material summarising foundational knowledge in the field",
            "A glossary and index to support further study",
        ],
        "S": [
            "The poet wrote of longing, beauty, and the passage of time",
            "Vivid imagery painted the scene with colour and emotion",
            "The story unfolded through dialogue rich with meaning",
            "Music filled the hall as the performers brought the work to life",
        ],
        "SW": [
            "Practical advice for maintaining a balanced and healthy lifestyle",
            "Tips for managing finances and household responsibilities",
            "Personal reflections on family, community, and daily habits",
            "A guide to cooking nutritious meals at home",
        ],
        "W": [
            "Ancient civilisations built empires that eventually crumbled",
            "Chronicles of the events that shaped a pivotal era",
            "Historians examined the causes of a long-forgotten conflict",
            "The ruins stood as testimony to a world that had passed away",
        ],
        "NW": [
            "Philosophers debated the nature of consciousness and free will",
            "Abstract principles underlying the foundations of knowledge",
            "A theoretical framework for understanding moral reasoning",
            "The paradox reveals deep tensions in our conceptual assumptions",
        ],
    }

    # Center angle for each 8-point sector (radians, clockwise from North = 0)
    SECTOR_ANGLES: Dict[str, float] = {
        "N":  0.0,
        "NE": math.pi / 4,
        "E":  math.pi / 2,
        "SE": 3 * math.pi / 4,
        "S":  math.pi,
        "SW": 5 * math.pi / 4,
        "W":  3 * math.pi / 2,
        "NW": 7 * math.pi / 4,
    }

    def __init__(self, embedding_service) -> None:
        """
        Args:
            embedding_service: Any EmbeddingService with an embed_query method.
                               Reference centroids are computed once at init time.
        """
        self.embedding_service = embedding_service
        logger.info("Computing semantic compass reference centroids (runs once)...")
        self._centroids: Dict[str, np.ndarray] = self._compute_centroids()
        logger.info("Semantic compass ready — %d sectors", len(self._centroids))

    def _compute_centroids(self) -> Dict[str, np.ndarray]:
        centroids: Dict[str, np.ndarray] = {}
        for sector, sentences in self.REFERENCE_SENTENCES.items():
            vecs = [np.array(self.embedding_service.embed_query(s)) for s in sentences]
            centroid = np.mean(vecs, axis=0)
            norm = np.linalg.norm(centroid)
            centroids[sector] = centroid / norm if norm > 0 else centroid
            logger.debug("Computed centroid for sector %s (norm=%.4f)", sector, float(norm))
        return centroids

    def embedding_to_sector(self, embedding: np.ndarray) -> Tuple[str, float]:
        """
        Returns the best-matching sector name and its center angle in radians.

        Args:
            embedding: Document embedding vector (any length matching references).

        Returns:
            (sector_name, theta_radians) e.g. ("N", 0.0) or ("SW", 3.927)
        """
        norm = np.linalg.norm(embedding)
        vec = embedding / norm if norm > 0 else embedding

        best_sector = max(
            self._centroids,
            key=lambda s: float(np.dot(vec, self._centroids[s]))
        )
        return best_sector, self.SECTOR_ANGLES[best_sector]

    def get_sector_similarities(self, embedding: np.ndarray) -> Dict[str, float]:
        """
        Returns cosine similarity to every sector centroid.
        Useful for debugging and for ranking ambiguous content.
        """
        norm = np.linalg.norm(embedding)
        vec = embedding / norm if norm > 0 else embedding
        return {
            sector: float(np.dot(vec, centroid))
            for sector, centroid in self._centroids.items()
        }

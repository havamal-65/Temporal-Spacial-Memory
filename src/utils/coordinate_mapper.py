"""
Coordinate Mapper Utility

This module maps text entities, events, and locations to
coordinates in the 4D polar-temporal space, prioritizing document structure.
"""

import numpy as np
import logging
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer

# Local imports
from src.models.coordinate_system import PolarTemporalCoordinate
from src.utils.embedding_service import EmbeddingService # Keep for potential use

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CoordinateMapper')


class CoordinateMapper:
    """
    Maps text content and structural information to 4D polar-temporal coordinates.
    Prioritizes structural sequence for 't' and provides placeholders for 'r', 'theta', 'z'.
    LLM-based refinement for r, theta, z is intended for a later phase.
    """

    def __init__(self,
                 embedding_service: EmbeddingService, # Keep for potential semantic analysis later
                 # Define structural layers (example)
                 default_chunk_layer: int = 2,
                 # Parameters for future fractal growth logic
                 base_radius: float = 0.9, # Default radius for initial chunks
                 base_angle_spread: float = np.pi / 180, # Small spread based on page?
                ):
        """
        Initialize the coordinate mapper.

        Args:
            embedding_service: Service for generating embeddings (used later).
            default_chunk_layer: Default Z-layer for text chunks.
            base_radius: Default radial distance for new chunks.
            base_angle_spread: Factor for spreading angles based on structure.
        """
        self.embedding_service = embedding_service
        self.default_chunk_layer = default_chunk_layer
        self.base_radius = base_radius
        self.base_angle_spread = base_angle_spread
        # TF-IDF for keywords can remain if desired - removing instance variable
        # self.tfidf = TfidfVectorizer(
        #     max_features=1000,
        #     stop_words='english',
        #     ngram_range=(1, 2)
        # )

    def map_to_coordinates(self,
                         content: str,
                         metadata: Dict[str, Any],
                         # extracted_entities: Optional[Dict[str, List[Any]]] = None # Keep if needed for keywords
                         embedding: Optional[np.ndarray] = None # Embedding passed in
                        ) -> Dict[str, Any]:
        """
        Map text content and structural metadata to 4D coordinates and keywords.
        This version focuses on Phase 1: Structural mapping.

        Args:
            content: Text content of the chunk.
            metadata: Metadata including structural info ('page_number', 'chunk_index_on_page').
            embedding: Pre-computed embedding (optional, not used for coords in this phase).

        Returns:
            Dictionary containing coordinates, keywords, embedding, and mapping details.
        """

        # --- Calculate Coordinates (Phase 1: Structure-based) ---
        coordinates = self._calculate_structural_coordinates(metadata)

        # --- Generate Keywords (Using local TF calculation) ---
        keywords = self._extract_keywords(content)

        # --- Prepare Mapping Details ---
        mapping_details = {
            'calculation_phase': 1,
            'temporal_basis': f"page {metadata.get('page_number', 0)} chunk {metadata.get('chunk_index_on_page', 0)}",
            'radial_basis': f"fixed base radius {self.base_radius}",
            'angular_basis': f"page number mod 360",
            'layer_basis': f"default layer {self.default_chunk_layer}"
        }

        # --- Construct Result ---
        return {
            'coordinate': coordinates,
            'keywords': keywords,
            'embedding': embedding, # Pass through the embedding
            'mapping_details': mapping_details
        }

    def _calculate_structural_coordinates(self, metadata: Dict[str, Any]) -> PolarTemporalCoordinate:
        """
        Calculates coordinates based primarily on structural metadata (Phase 1).
        Args:
            metadata: Chunk metadata containing 'page_number', 'chunk_index_on_page',
                      and potentially 'total_chunks_on_page' (if added).
        Returns:
            A PolarTemporalCoordinate object.
        """
        page_number = metadata.get('page_number', 1) # Default to 1 if missing
        chunk_index = metadata.get('chunk_index_on_page', 0) # Default to 0
        # Ideally, we'd know the total chunks on the page for normalization
        # --- Get total_chunks_on_page from metadata --- 
        total_chunks_on_page = metadata.get('total_chunks_on_page', 1) # Default to 1 if missing
        if total_chunks_on_page <= 0:
            logger.warning(f"Invalid total_chunks_on_page ({total_chunks_on_page}) in metadata for page {page_number}, defaulting to 1.")
            total_chunks_on_page = 1 # Ensure it's at least 1
        # --- End Get --- 

        # --- 1. Temporal Coordinate (t) ---
        # Maps page number and chunk index to a continuous time value.
        # Add a small fraction for chunk index to ensure order within page.
        # Avoid division by zero, ensure fraction < 1
        # Use the retrieved total_chunks_on_page
        t = float(page_number - 1) + (float(chunk_index) / float(total_chunks_on_page))

        # --- 2. Context Layer (z) ---
        # Use the default layer defined during initialization.
        z = float(self.default_chunk_layer)

        # --- 3. Radial Distance (r) ---
        # Assign the fixed base radius for Phase 1.
        r = float(self.base_radius)

        # --- 4. Angular Position (theta) ---
        # Simple mapping based on page number for initial spread.
        # Add tiny offset based on chunk index to avoid exact overlap.
        base_angle_deg = (page_number -1) % 360
        # Use base_angle_spread for the offset magnitude
        chunk_offset_rad = (float(chunk_index) / float(max(1, total_chunks_on_page))) * self.base_angle_spread
        base_angle_rad = np.radians(base_angle_deg)
        theta_rad = (base_angle_rad + chunk_offset_rad) % (2 * np.pi) # Ensure stays within 0-2pi

        return PolarTemporalCoordinate(r=r, theta=theta_rad, t=t, z=z)

    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """
        Extracts top terms based on Term Frequency (TF) within the given text.
        Uses a local TfidfVectorizer instance for calculation on the single text.
        Note: This simplification uses TF only, as fitting IDF requires a broader corpus context.

        Args:
            text: The input text content.
            top_n: The maximum number of keywords to return.

        Returns:
            A list of the top N keywords based on TF score, or an empty list if errors occur.
        """
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            logger.debug("Skipping keyword extraction for empty or non-string content.")
            return []

        try:
            # Use a local vectorizer for TF calculation on the single document
            # Set use_idf=False to calculate only Term Frequency.
            # Add other parameters like max_features if needed.
            local_tfidf = TfidfVectorizer(
                stop_words='english',
                use_idf=False,
                ngram_range=(1, 2), # Keep ngram range if desired
                max_features=1000   # Keep max features if desired
            )
            response = local_tfidf.fit_transform([text])
            feature_names = local_tfidf.get_feature_names_out()

            # Check if any features were generated (might be empty after stop words)
            if not feature_names.any():
                logger.debug(f"No features found after TF vectorization for content: '{text[:50]}...'")
                return []

            # Get TF scores for the single document
            # response is a sparse matrix (1, num_features)
            tf_scores = response.toarray().flatten() # Convert sparse matrix row to dense numpy array

            # Ensure feature_names and tf_scores align correctly
            if len(feature_names) != len(tf_scores):
                 logger.error(f"Keyword Extraction: Mismatch between feature names ({len(feature_names)}) and scores ({len(tf_scores)}).")
                 return []

            # Sort indices by score in descending order
            sorted_indices = np.argsort(tf_scores)[::-1]

            # Get top N keywords with score > 0
            keywords = [
                feature_names[i]
                for i in sorted_indices[:top_n]
                if i < len(feature_names) and tf_scores[i] > 0 # Check bounds and score
            ]

            logger.debug(f"Extracted TF keywords: {keywords}")
            return keywords
        except ValueError as ve:
            # Catch specific TF-IDF errors like empty vocabulary after stop words
            if "empty vocabulary" in str(ve):
                logger.debug(f"Skipping keyword extraction due to empty vocabulary for content: '{text[:50]}...'")
                return []
            else:
                logger.warning(f"TF ValueError extracting keywords: {ve} for content: '{text[:50]}...'")
                return []
        except Exception as e:
            logger.error(f"Unexpected error extracting keywords: {e}", exc_info=True)
            return [] 
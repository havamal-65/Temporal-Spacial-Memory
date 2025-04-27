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
        # TF-IDF for keywords can remain if desired
        self.tfidf = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )

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

        # --- Generate Keywords (Optional, can remain) ---
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
        total_chunks_on_page = metadata.get('total_chunks_on_page', 10) # Estimate if missing

        # --- 1. Temporal Coordinate (t) --- 
        # Maps page number and chunk index to a continuous time value.
        # Add a small fraction for chunk index to ensure order within page.
        t = float(page_number - 1) + (float(chunk_index) / float(total_chunks_on_page + 1)) # Avoid division by zero, ensure fraction < 1

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
        chunk_offset_deg = (float(chunk_index) / float(total_chunks_on_page + 1)) * self.base_angle_spread
        theta_deg = (base_angle_deg + chunk_offset_deg) % 360
        theta_rad = np.radians(theta_deg)

        return PolarTemporalCoordinate(r=r, theta=theta_rad, t=t, z=z)


    # Keep keyword extraction if needed
    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from content using TF-IDF.

        Args:
            content: Text content
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of extracted keywords
        """
        if not content:
            return []
        try:
            # Ensure the vectorizer is fitted, even if just on this single doc
            try:
                self.tfidf.vocabulary_
            except AttributeError:
                 logger.debug("Fitting TF-IDF vectorizer on first call.")
                 self.tfidf.fit([content]) # Fit on the first piece of content it sees

            # Check again if vocabulary exists after trying to fit
            if not hasattr(self.tfidf, 'vocabulary_') or not self.tfidf.vocabulary_:
                 # Handle case where fitting might fail on very short/weird content
                 logger.warning(f"TF-IDF vocabulary empty after fitting on content: '{content[:50]}...'")
                 return []

            # Transform the content
            tfidf_matrix = self.tfidf.transform([content])

            # Check if the matrix is empty (can happen with stop words only)
            if tfidf_matrix.nnz == 0:
                return []

            feature_names = self.tfidf.get_feature_names_out()
            # Handle potential index out of bounds if matrix is weird
            if tfidf_matrix.shape[1] != len(feature_names):
                 logger.warning(f"TF-IDF shape mismatch: matrix columns {tfidf_matrix.shape[1]}, features {len(feature_names)}")
                 # Try to refit, maybe? Or just return empty
                 self.tfidf.fit([content]) # Attempt refit
                 if not hasattr(self.tfidf, 'vocabulary_') or not self.tfidf.vocabulary_:
                     return []
                 tfidf_matrix = self.tfidf.transform([content])
                 if tfidf_matrix.nnz == 0: return []
                 feature_names = self.tfidf.get_feature_names_out()
                 if tfidf_matrix.shape[1] != len(feature_names): return [] # Give up if refit didn't fix it


            # Get the top terms
            scores = tfidf_matrix.toarray()[0]
            top_indices = np.argsort(scores)[-max_keywords:][::-1]
            # Filter out indices that might be out of bounds after checks
            valid_indices = [i for i in top_indices if i < len(feature_names)]
            top_terms = [feature_names[i] for i in valid_indices if scores[i] > 0] # Only include terms with score > 0

            return top_terms
        except ValueError as ve:
            # Catch specific TF-IDF errors like empty vocabulary after stop words
            if "empty vocabulary" in str(ve):
                logger.debug(f"Skipping keyword extraction due to empty vocabulary for content: '{content[:50]}...'")
                return []
            else:
                logger.warning(f"TF-IDF ValueError extracting keywords: {ve}")
                return []
        except Exception as e:
            logger.warning(f"Error extracting keywords: {e}", exc_info=True)
            return [] 
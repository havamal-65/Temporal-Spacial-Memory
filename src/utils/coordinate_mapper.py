"""
Coordinate Mapper Utility

This module maps text entities, events, and locations to
coordinates in the 3D polar-temporal space (r, theta, t), prioritizing document structure for 't'.
"""

import numpy as np
import logging
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import math # Added for potential future angle calculations
from sklearn.feature_extraction.text import TfidfVectorizer

# Local imports
from src.data_models import PolarTemporalCoordinate, Z_TYPES # Updated import path if data_models is top level
from src.utils.embedding_service import EmbeddingService # Keep for potential use

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CoordinateMapper')


class CoordinateMapper:
    """
    Maps text content and structural information to 4D polar-temporal coordinates (r, theta, t, z).
    Phase 1: Prioritizes structural sequence for 't', structural metadata for 'z'/'z_type',
             and provides placeholders for 'r', 'theta'.
    """

    def __init__(self,
                 embedding_service: EmbeddingService, # Keep for potential semantic analysis later
                 # Parameters for placeholder/future fractal growth logic
                 base_radius: float = 0.9, # Default radius for initial chunks
                 base_angle_spread: float = np.pi / 180, # Small spread based on page?
                 # --- Parameters for z-mapping (Examples) ---
                 perspective_z_range: Tuple[float, float] = (100.0, 200.0),
                 layer_z_map: Dict[str, float] = {'MAIN': 0.0, 'FOOTNOTE': 1.0, 'COMMENTARY': 2.0, 'APPENDIX': 3.0}, # Example mapping
                 version_z_multiplier: float = 10.0, # Example scaling factor
                 abstraction_z_map: Dict[str, float] = {'DETAILED': 0.0, 'SUMMARY': 5.0, 'ABSTRACT': 6.0}, # Example mapping
                 doc_id_z_multiplier: float = 1000.0 # Example scaling factor
                ):
        """
        Initialize the coordinate mapper.

        Args:
            embedding_service: Service for generating embeddings (used later).
            base_radius: Default radial distance for new chunks.
            base_angle_spread: Factor for spreading angles based on structure.
            perspective_z_range: Min/Max z-values for perspective mapping.
            layer_z_map: Dictionary mapping layer types to specific z-values.
            version_z_multiplier: Factor to scale version numbers for z-value.
            abstraction_z_map: Dictionary mapping abstraction levels to z-values.
            doc_id_z_multiplier: Factor to scale document IDs (if numeric) for z-value.
        """
        self.embedding_service = embedding_service
        self.base_radius = base_radius
        self.base_angle_spread = base_angle_spread
        # Store z-mapping parameters
        self.perspective_z_range = perspective_z_range
        self.layer_z_map = layer_z_map
        self.version_z_multiplier = version_z_multiplier
        self.abstraction_z_map = abstraction_z_map
        self.doc_id_z_multiplier = doc_id_z_multiplier

    def map_to_coordinates(self,
                         content: str,
                         metadata: Dict[str, Any],
                         embedding: Optional[np.ndarray] = None # Embedding passed in
                        ) -> Dict[str, Any]:
        """
        Map text content and structural metadata to 4D coordinates and keywords.
        Phase 1: Structural mapping for 't', 'z', 'z_type'; placeholders for 'r', 'theta'.

        Args:
            content: Text content of the chunk.
            metadata: Metadata including structural info (page, chunk index, LLM analysis results).
            embedding: Pre-computed embedding (optional, not used for coords in this phase).

        Returns:
            Dictionary containing coordinates, keywords, embedding, and mapping details.
        """

        # --- Calculate Coordinates (Phase 1: Structure-based 't', 'z', 'z_type', Placeholders 'r','theta') ---
        coordinates = self._calculate_structural_coordinates(metadata)

        # --- Generate Keywords (Using local TF calculation) ---
        keywords = self._extract_keywords(content)

        # --- Prepare Mapping Details ---
        mapping_details = {
            'calculation_phase': 1,
            'temporal_basis': f"page {metadata.get('page_number', 0)} chunk {metadata.get('chunk_index_on_page', 0)}",
            'radial_basis': f"fixed placeholder radius {self.base_radius}",
            'angular_basis': f"fixed placeholder angle {coordinates.theta}",
            'z_basis': f"{coordinates.z_type} -> z={coordinates.z}" # Add z basis info
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
        't' is based on sequence, 'r' and 'theta' are placeholders.
        'z' and 'z_type' are derived from LLM-extracted structural metadata.

        Args:
            metadata: Chunk metadata potentially containing 'page_number', 'chunk_index_on_page',
                      'total_chunks_on_page', 'structural_perspective', 'structural_layer_type',
                      'structural_version', 'structural_abstraction_level', 'doc_id'.

        Returns:
            A PolarTemporalCoordinate object (r, theta, t, z, z_type).
        """
        # --- Import the correct class INSIDE the method ---
        # Already imported at the top level now
        # from src.data_models import PolarTemporalCoordinate, Z_TYPES
        # --- End Import ---

        page_number = metadata.get('page_number', 1) # Default to 1 if missing
        chunk_index = metadata.get('chunk_index_on_page', 0) # Default to 0
        total_chunks_on_page = metadata.get('total_chunks_on_page', 1) # Default to 1 if missing
        if total_chunks_on_page <= 0:
            logger.warning(f"Invalid total_chunks_on_page ({total_chunks_on_page}) in metadata for page {page_number}, defaulting to 1.")
            total_chunks_on_page = 1 # Ensure it's at least 1

        # --- 1. Temporal Coordinate (t) ---
        # Maps page number and chunk index to a continuous time value.
        t = float(page_number - 1) + (float(chunk_index) / float(total_chunks_on_page))

        # --- 2. Radial Distance (r) ---
        # Assign the fixed placeholder radius for Phase 1.
        r = float(self.base_radius) # Using base_radius as placeholder

        # --- 3. Angular Position (theta) ---
        # Assign a fixed placeholder angle for Phase 1.
        theta_rad = 0.0 # Simple placeholder

        # --- 4. Structural Coordinate (z) and Type (z_type) ---
        # Derive z and z_type from structural metadata (LLM analysis results)
        # **NOTE: This mapping logic is a placeholder based on the plan's examples.**
        # **It needs careful design and refinement based on actual LLM outputs and desired structural representation.**
        perspective = metadata.get("structural_perspective")
        layer_type = metadata.get("structural_layer_type", 'MAIN') # Default added here
        version = metadata.get("structural_version")
        abstraction_level = metadata.get("structural_abstraction_level", 'DETAILED') # Default added here
        doc_id = metadata.get("doc_id") # Get doc_id for potential mapping

        z: float = 0.0
        z_type: Z_TYPES = 'DEFAULT' # Default value

        # --- Apply mapping rules based on priority (example priority: perspective > layer > version > abstraction > doc_id) ---
        # **DESIGN DECISION: Define the priority/combination strategy for multiple struct_ fields.**
        if perspective:
            # Example: Map perspective name hash to a float range
            z = self._map_perspective_to_z(perspective)
            z_type = 'PERSPECTIVE'
        elif layer_type and layer_type != 'MAIN': # Check against default
            # Example: Map predefined layers to specific z values
            z = self._map_layer_to_z(layer_type)
            # Construct z_type string, ensuring it's in Z_TYPES
            potential_z_type = f'LAYER_{layer_type.upper().replace(" ", "_")}'
            if potential_z_type in Z_TYPES.__args__:
                 z_type = potential_z_type # Type: ignore[assignment]
            else:
                 logger.warning(f"Mapped layer '{layer_type}' resulted in unrecognized Z_TYPE '{potential_z_type}'. Defaulting z_type.")
                 z_type = 'DEFAULT' # Fallback if generated type isn't valid
        elif version:
             # Example: Use version directly (or mapped)
             numeric_part = None
             try:
                 # Attempt to extract a year or number from the version string
                 match = re.search(r'\b(\d{4}|\d+\.?\d*)\b', version)
                 if match:
                     numeric_part = float(match.group(1))
                     
                 if numeric_part is not None:
                     z = numeric_part * self.version_z_multiplier # Scale extracted number
                     logger.debug(f"Mapped version '{version}' to z={z} based on numeric part {numeric_part}")
                 else:
                     # If no number found, fall back to hashing the whole string
                     logger.debug(f"No clear numeric part in version '{version}'. Using hash for z-mapping.")
                     z = self._hash_to_z(f"version_{version}", (200.0, 300.0))
                 z_type = 'VERSION'
             except Exception as e: # Catch potential errors during regex or float conversion
                 logger.warning(f"Error processing version '{version}' for z-mapping: {e}. Falling back to hash.")
                 # Fallback to hashing the whole string on any error
                 z = self._hash_to_z(f"version_{version}", (200.0, 300.0))
                 z_type = 'VERSION'
        elif abstraction_level and abstraction_level != 'DETAILED': # Check against default
             z = self._map_abstraction_to_z(abstraction_level)
             potential_z_type = f'ABSTRACTION_{abstraction_level.upper().replace(" ", "_")}'
             if potential_z_type in Z_TYPES.__args__:
                 z_type = potential_z_type # Type: ignore[assignment]
             else:
                 logger.warning(f"Mapped abstraction '{abstraction_level}' resulted in unrecognized Z_TYPE '{potential_z_type}'. Defaulting z_type.")
                 z_type = 'DEFAULT' # Fallback
        elif doc_id:
            # Example: Map doc_id hash or a numeric part to z
            # Attempt to convert to numeric first, then hash
            try:
                # Try to extract a number for scaling
                doc_id_num_str = re.sub(r'\D', '', doc_id)
                if doc_id_num_str:
                     z = float(doc_id_num_str) * self.doc_id_z_multiplier
                else:
                     # Fallback to hashing the string doc_id if no number found
                    z = self._hash_to_z(f"docid_{doc_id}", (300.0, 400.0))
                z_type = 'DOC_ID'
            except ValueError:
                 logger.warning(f"Could not process doc_id '{doc_id}' for numeric z-mapping, hashing instead.")
                 z = self._hash_to_z(f"docid_{doc_id}", (300.0, 400.0))
                 z_type = 'DOC_ID'
        # If none of the above matched, z remains 0.0 and z_type remains 'DEFAULT'

        # Final coordinate (r, theta, t, z, z_type)
        final_coordinate = PolarTemporalCoordinate(
            r=r,
            theta=theta_rad,
            t=t,
            z=z,
            z_type=z_type
        )

        return final_coordinate

    # --- Helper methods for z-mapping (Placeholders/Examples) ---

    def _map_perspective_to_z(self, perspective: str) -> float:
        """Example: Map perspective string to z using hashing within a defined range."""
        return self._hash_to_z(f"perspective_{perspective}", self.perspective_z_range)

    def _map_layer_to_z(self, layer_type: str) -> float:
        """Example: Map layer type string to z using a predefined dictionary."""
        # Case-insensitive lookup
        return self.layer_z_map.get(layer_type.upper(), 0.0) # Default to 0.0 if not found

    def _map_abstraction_to_z(self, abstraction_level: str) -> float:
        """Example: Map abstraction level string to z using a predefined dictionary."""
        # Case-insensitive lookup
        return self.abstraction_z_map.get(abstraction_level.upper(), 0.0) # Default to 0.0 if not found

    def _hash_to_z(self, input_string: str, z_range: Tuple[float, float]) -> float:
        """Helper to hash a string and map it to a float within a given range."""
        hash_object = hashlib.sha256(input_string.encode())
        hash_hex = hash_object.hexdigest()
        hash_int = int(hash_hex, 16)
        # Normalize the hash integer to a 0-1 range
        normalized_hash = (hash_int % (2**32)) / (2**32 - 1) # Using lower bits for simplicity
        # Scale to the desired z_range
        z_min, z_max = z_range
        z_value = z_min + normalized_hash * (z_max - z_min)
        return z_value

    # --- End Helper methods ---

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
            local_tfidf = TfidfVectorizer(
                stop_words='english',
                use_idf=False,
                ngram_range=(1, 2),
                max_features=1000
            )
            response = local_tfidf.fit_transform([text])
            feature_names = local_tfidf.get_feature_names_out()

            if not feature_names.any():
                logger.debug(f"No features found after TF vectorization for content: '{text[:50]}...'")
                return []

            tf_scores = response.toarray().flatten()

            if len(feature_names) != len(tf_scores):
                 logger.error(f"Keyword Extraction: Mismatch between feature names ({len(feature_names)}) and scores ({len(tf_scores)}).")
                 return []

            sorted_indices = np.argsort(tf_scores)[::-1]

            keywords = [
                feature_names[i]
                for i in sorted_indices[:top_n]
                if i < len(feature_names) and tf_scores[i] > 0
            ]

            logger.debug(f"Extracted TF keywords: {keywords}")
            return keywords
        except ValueError as ve:
            if "empty vocabulary" in str(ve):
                logger.debug(f"Skipping keyword extraction due to empty vocabulary for content: '{text[:50]}...'")
                return []
            else:
                logger.warning(f"TF ValueError extracting keywords: {ve} for content: '{text[:50]}...'")
                return []
        except Exception as e:
            logger.error(f"Unexpected error extracting keywords: {e}", exc_info=True)
            return [] 
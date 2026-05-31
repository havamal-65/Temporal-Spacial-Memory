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
import json
import os
from collections import defaultdict

# Local imports
from src.data_models import PolarTemporalCoordinate, Z_TYPES # Updated import path if data_models is top level
from src.utils.embedding_service import EmbeddingService # Keep for potential use
from .angular_sector_system import AngularSectorSystem, SectorSystem, create_compass_32_system
from .semantic_compass import SemanticCompassMapper

# Configure logging
log_level = os.getenv('COORDINATE_MAPPER_LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CoordinateMapper')

# Create a separate logger for coordinate transformations if detailed logging is needed
coord_logger = logging.getLogger('CoordinateMapper.Transformations')
coord_logger.setLevel(getattr(logging, os.getenv('COORDINATE_TRANSFORM_LOG_LEVEL', 'DEBUG')))

# Add file handler for coordinate transformations if LOG_TO_FILE is enabled
if os.getenv('LOG_COORDINATES_TO_FILE', 'False').lower() in ('true', '1', 'yes'):
    log_dir = os.getenv('COORDINATE_LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(f"{log_dir}/coordinate_transforms.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    coord_logger.addHandler(file_handler)


class CoordinateMapper:
    """
    Maps text content and structural information to 4D polar-temporal coordinates (r, theta, t, z).
    Phase 1: Prioritizes structural sequence for 't', structural metadata for 'z'/'z_type',
             and provides placeholders for 'r', 'theta'.
    """

    def __init__(self,
                 embedding_service: EmbeddingService, # Keep for potential semantic analysis later
                 # Angular sector system parameters
                 sector_system: SectorSystem = SectorSystem.COMPASS_32,
                 use_sector_quantization: bool = True,
                 # Parameters for placeholder/future fractal growth logic
                 base_radius: float = 0.9, # Default radius for initial chunks
                 base_angle_spread: float = np.pi / 180, # Small spread based on page?
                 # --- Parameters for z-mapping (Examples) ---
                 perspective_z_range: Tuple[float, float] = (100.0, 200.0),
                 layer_z_map: Dict[str, float] = {'MAIN': 0.0, 'FOOTNOTE': 1.0, 'COMMENTARY': 2.0, 'APPENDIX': 3.0}, # Example mapping
                 version_z_multiplier: float = 10.0, # Example scaling factor
                 abstraction_z_map: Dict[str, float] = {'DETAILED': 0.0, 'SUMMARY': 5.0, 'ABSTRACT': 6.0}, # Example mapping
                 doc_id_z_multiplier: float = 1000.0, # Example scaling factor
                 # --- Parameters for embedding-based coordinates ---
                 use_embedding_for_coords: bool = False,  # Flag to use embedding-based coordinates
                 use_semantic_compass: bool = True,  # Use SemanticCompassMapper for theta (requires use_embedding_for_coords=True)
                 embedding_r_scale: float = 1.0,  # Scaling factor for radial distance
                 embedding_theta_scale: float = math.pi,  # Scaling factor for angular position (legacy arctan2 path)
                 # --- Parameters for normalization ---
                 max_radius: float = 100.0,
                 min_radius: float = 0.1,
                 normalize_embeddings: bool = True,
                 # --- Parameters for logging ---
                 log_coordinates: bool = True
                ):
        """
        Initialize the coordinate mapper.

        Args:
            embedding_service: Service for generating embeddings (used later).
            sector_system: Angular sector system to use
            use_sector_quantization: Whether to quantize angles to sector centers
            base_radius: Default radial distance for new chunks.
            base_angle_spread: Factor for spreading angles based on structure.
            perspective_z_range: Min/Max z-values for perspective mapping.
            layer_z_map: Dictionary mapping layer types to specific z-values.
            version_z_multiplier: Factor to scale version numbers for z-value.
            abstraction_z_map: Dictionary mapping abstraction levels to z-values.
            doc_id_z_multiplier: Factor to scale document IDs (if numeric) for z-value.
            use_embedding_for_coords: Whether to use embedding vectors for coordinate transformation.
            use_semantic_compass: When True (and use_embedding_for_coords=True), assigns theta via
                cosine similarity to precomputed sector centroids instead of arctan2.
            embedding_r_scale: Scaling factor for radial distance from embeddings.
            embedding_theta_scale: Scaling factor for angular position (legacy arctan2 path only).
            max_radius: Maximum allowed radius for normalization.
            min_radius: Minimum allowed radius for normalization.
            normalize_embeddings: Whether to normalize embeddings before coordinate calculation.
            log_coordinates: Whether to log coordinate transformations in detail.
        """
        self.embedding_service = embedding_service
        
        # Initialize angular sector system
        self.sector_system = AngularSectorSystem(sector_system)
        self.use_sector_quantization = use_sector_quantization
        
        # Store base parameters
        self.base_radius = base_radius
        self.base_angle_spread = base_angle_spread
        
        # Store z-mapping parameters
        self.perspective_z_range = perspective_z_range
        self.layer_z_map = layer_z_map
        self.version_z_multiplier = version_z_multiplier
        self.abstraction_z_map = abstraction_z_map
        self.doc_id_z_multiplier = doc_id_z_multiplier
        
        # Store embedding-based coordinate parameters
        self.use_embedding_for_coords = use_embedding_for_coords
        self.use_semantic_compass = use_semantic_compass
        self.embedding_r_scale = embedding_r_scale
        self.embedding_theta_scale = embedding_theta_scale

        # Initialize semantic compass if both embedding-based coords and semantic compass are enabled
        self.semantic_compass: Optional[SemanticCompassMapper] = None
        if use_embedding_for_coords and use_semantic_compass:
            logger.info("Initializing SemanticCompassMapper (computes reference centroids once)...")
            self.semantic_compass = SemanticCompassMapper(embedding_service)
        
        # Store normalization parameters
        self.max_radius = max_radius
        self.min_radius = min_radius
        self.normalize_embeddings = normalize_embeddings
        
        # Store logging parameters
        self.log_coordinates = log_coordinates
        
        # Track sector usage for analytics
        self.sector_usage = defaultdict(int)
        
        # Log initialization parameters
        init_params = {
            "use_embedding_coords": use_embedding_for_coords,
            "embedding_r_scale": embedding_r_scale,
            "embedding_theta_scale": embedding_theta_scale,
            "max_radius": max_radius,
            "min_radius": min_radius,
            "normalize_embeddings": normalize_embeddings
        }
        logger.info(f"CoordinateMapper initialized with params: {json.dumps(init_params)}")

    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration of the CoordinateMapper.
        
        Returns:
            Dictionary containing the current configuration parameters
        """
        config = {
            "sector_system": self.sector_system.system.value,
            "sector_count": len(self.sector_system.sectors),
            "use_sector_quantization": self.use_sector_quantization,
            "use_embedding_coords": self.use_embedding_for_coords,
            "use_semantic_compass": self.use_semantic_compass,
            "semantic_compass_active": self.semantic_compass is not None,
            "embedding_r_scale": self.embedding_r_scale,
            "embedding_theta_scale": self.embedding_theta_scale,
            "base_radius": self.base_radius,
            "base_angle_spread": self.base_angle_spread,
            "max_radius": self.max_radius,
            "min_radius": self.min_radius,
            "normalize_embeddings": self.normalize_embeddings,
            "perspective_z_range": self.perspective_z_range,
            "layer_z_map": self.layer_z_map,
            "version_z_multiplier": self.version_z_multiplier,
            "abstraction_z_map": self.abstraction_z_map,
            "doc_id_z_multiplier": self.doc_id_z_multiplier
        }
        return config

    def map_to_coordinates(self,
                         content: str,
                         metadata: Dict[str, Any],
                         embedding: Optional[np.ndarray] = None # Embedding passed in
                        ) -> Dict[str, Any]:
        """
        Map text content and structural metadata to 4D coordinates and keywords.
        Uses embeddings for r and theta if available and enabled.

        Args:
            content: Text content of the chunk.
            metadata: Metadata including structural info (page, chunk index, LLM analysis results).
            embedding: Pre-computed embedding (optional, used for coords if available and enabled).

        Returns:
            Dictionary containing coordinates, keywords, embedding, and mapping details.
        """
        # Extract document and chunk identifiers for logging
        doc_id = metadata.get('doc_id', 'unknown_doc')
        chunk_id = metadata.get('chunk_id', f"chunk_{time.time()}")
        logger.debug(f"Mapping coordinates for {doc_id}/{chunk_id}")
        
        # Log summary of input metadata for traceability
        if self.log_coordinates:
            coord_logger.debug(f"Input metadata for {doc_id}/{chunk_id}: " +
                               f"page={metadata.get('page_number', 'N/A')}, " +
                               f"chunk_idx={metadata.get('chunk_index_on_page', 'N/A')}, " +
                               f"has_embedding={embedding is not None}")
        
        # Get embedding shape for logging
        embedding_shape = None
        if embedding is not None:
            embedding_shape = embedding.shape
            if self.log_coordinates:
                coord_logger.debug(f"Input embedding shape for {doc_id}/{chunk_id}: {embedding_shape}")
        
        # --- Calculate Coordinates ---
        start_time = time.time()
        if self.use_embedding_for_coords and embedding is not None:
            # Use embedding-based coordinates with structural t and z
            coords = self._calculate_embedding_based_coordinates(embedding, metadata)
            mapping_basis = "embedding-based"
        else:
            # Use structural coordinates (placeholder r, theta)
            coords = self._calculate_structural_coordinates(metadata)
            mapping_basis = "structure-based"
            
        calculation_time = time.time() - start_time
        
        # --- Generate Keywords (Using local TF calculation) ---
        keywords = self._extract_keywords(content)

        # --- Prepare Mapping Details ---
        mapping_details = {
            'calculation_method': mapping_basis,
            'calculation_time_ms': round(calculation_time * 1000, 2),
            'embedding_shape': str(embedding_shape) if embedding_shape else "None",
            'temporal_basis': f"page {metadata.get('page_number', 0)} chunk {metadata.get('chunk_index_on_page', 0)}",
            'radial_basis': f"{'embedding magnitude' if mapping_basis == 'embedding-based' else 'fixed placeholder'} radius {coords.r}",
            'angular_basis': f"{'embedding direction' if mapping_basis == 'embedding-based' else 'fixed placeholder'} angle {coords.theta}",
            'z_basis': f"{coords.z_type} -> z={coords.z}", # Add z basis info
            'metadata_keys': list(metadata.keys())
        }
        
        # Log the resulting coordinates
        if self.log_coordinates:
            coord_log = {
                "doc_id": doc_id,
                "chunk_id": chunk_id, 
                "coordinates": {
                    "r": float(coords.r),
                    "theta": float(coords.theta),
                    "t": float(coords.t),
                    "z": float(coords.z),
                    "z_type": coords.z_type
                },
                "mapping_basis": mapping_basis,
                "calculation_time_ms": mapping_details['calculation_time_ms']
            }
            coord_logger.info(f"Coordinate mapping: {json.dumps(coord_log)}")

        # --- Apply Sector Quantization ---
        if self.use_sector_quantization:
            original_theta = coords.theta
            sector_info = self.sector_system.angle_to_sector(original_theta)
            quantized_theta = sector_info.center_angle
            
            # Update coordinates with quantized theta
            coords = PolarTemporalCoordinate(
                r=coords.r,
                theta=quantized_theta,
                t=coords.t,
                z=coords.z,
                z_type=getattr(coords, 'z_type', 'unknown')
            )
            
            # Track sector usage
            self.sector_usage[sector_info.id] += 1
            
            # Log sector assignment
            if self.log_coordinates:
                coord_logger.debug(f"Sector assignment: {math.degrees(original_theta):.1f}° → "
                                 f"{sector_info.name} ({math.degrees(quantized_theta):.1f}°)")
        else:
            sector_info = self.sector_system.angle_to_sector(coords.theta)
        
        # Handle edge cases
        coords = self._handle_edge_case_coordinates(coords)
        
        # --- Construct Result ---
        result = {
            'coordinates': coords,
            'keywords': keywords,
            'embedding': embedding, # Pass through the embedding
            'mapping_details': mapping_details,
            'sector': {
                'id': sector_info.id,
                'name': sector_info.name,
                'center_angle_deg': math.degrees(sector_info.center_angle),
                'center_angle_rad': sector_info.center_angle,
                'quantized': self.use_sector_quantization
            },
            'system_info': self.sector_system.get_system_info()
        }
        
        if self.log_coordinates:
            coord_logger.info(f"Mapped to coordinates: {coords} in sector {sector_info.name}")

        return result

    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        Normalize an embedding vector to unit length.
        
        Args:
            embedding: The embedding vector to normalize
            
        Returns:
            Normalized embedding vector
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            normalized = embedding / norm
            if self.log_coordinates:
                coord_logger.debug(f"Normalized embedding: original norm={norm:.4f}")
            return normalized
        return embedding
        
    def _normalize_radius(self, radius: float) -> float:
        """
        Normalize radius to be within the allowed range.
        
        Args:
            radius: The calculated radius
            
        Returns:
            Normalized radius within min_radius and max_radius
        """
        original = radius
        if radius < self.min_radius:
            logger.debug(f"Normalizing small radius: {radius:.6f} -> {self.min_radius}")
            radius = self.min_radius
        if radius > self.max_radius:
            logger.debug(f"Normalizing large radius: {radius:.6f} -> {self.max_radius}")
            radius = self.max_radius
            
        if self.log_coordinates and original != radius:
            coord_logger.debug(f"Radius normalization: {original:.6f} -> {radius:.6f}")
            
        return radius
        
    def _normalize_theta(self, theta: float) -> float:
        """
        Normalize theta to be within [0, 2π) range.
        
        Args:
            theta: The calculated angle in radians
            
        Returns:
            Normalized angle in [0, 2π) range
        """
        original = theta
        normalized = theta % (2 * np.pi)
        if normalized < 0:
            normalized += 2 * np.pi
            
        if self.log_coordinates and abs(original - normalized) > 1e-6:
            coord_logger.debug(f"Theta normalization: {original:.6f} -> {normalized:.6f}")
            
        return normalized
        
    def _handle_edge_case_coordinates(self, coords: PolarTemporalCoordinate) -> PolarTemporalCoordinate:
        """
        Handle edge cases in coordinate values.
        
        Args:
            coords: The original coordinates
            
        Returns:
            Corrected coordinates with handled edge cases
        """
        # Store original values for logging
        original = {
            "r": coords.r,
            "theta": coords.theta,
            "t": coords.t,
            "z": coords.z
        }
        
        # Normalize r and theta
        r = self._normalize_radius(coords.r)
        theta = self._normalize_theta(coords.theta)
        
        # Handle potential NaN or infinite values in t and z
        t = coords.t
        if not np.isfinite(t):
            logger.warning(f"Invalid temporal coordinate (t={t}), setting to 0")
            t = 0.0
            
        z = coords.z
        if not np.isfinite(z):
            logger.warning(f"Invalid z coordinate (z={z}), setting to 0")
            z = 0.0
            
        # Log corrections if any were made
        if self.log_coordinates and (
            original["r"] != r or
            original["theta"] != theta or
            original["t"] != t or
            original["z"] != z
        ):
            coord_logger.info(f"Edge case handling: Original={json.dumps(original)}, " +
                             f"Corrected={{r:{r}, theta:{theta}, t:{t}, z:{z}}}")
            
        # Return corrected coordinates
        return PolarTemporalCoordinate(
            r=r,
            theta=theta,
            t=t,
            z=z,
            z_type=coords.z_type
        )

    def _calculate_embedding_based_coordinates(self, embedding: np.ndarray, metadata: Dict[str, Any]) -> PolarTemporalCoordinate:
        """
        Calculate polar-temporal coordinates using embedding vector properties for r and theta,
        while maintaining structural mapping for t and z.
        
        Args:
            embedding: The embedding vector to transform
            metadata: Structural metadata for t and z calculation
            
        Returns:
            PolarTemporalCoordinate with embedding-derived r and theta values
        """
        # First get the structural t and z values
        structural_coords = self._calculate_structural_coordinates(metadata)
        
        # Extract identifiers for logging
        doc_id = metadata.get('doc_id', 'unknown_doc')
        chunk_id = metadata.get('chunk_id', f"chunk_{time.time()}")
        
        # Log embedding stats before normalization if logging is enabled
        if self.log_coordinates:
            pre_norm_stats = {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "embedding_shape": embedding.shape,
                "embedding_mean": float(np.mean(embedding)),
                "embedding_std": float(np.std(embedding)),
                "embedding_min": float(np.min(embedding)),
                "embedding_max": float(np.max(embedding)),
                "embedding_norm": float(np.linalg.norm(embedding))
            }
            coord_logger.debug(f"Pre-normalization embedding stats: {json.dumps(pre_norm_stats)}")
        
        # Normalize embedding if configured to do so
        if self.normalize_embeddings and embedding is not None and embedding.size > 0:
            embedding = self._normalize_embedding(embedding)
            
            # Log post-normalization stats
            if self.log_coordinates:
                post_norm_stats = {
                    "embedding_mean": float(np.mean(embedding)),
                    "embedding_std": float(np.std(embedding)),
                    "embedding_norm": float(np.linalg.norm(embedding))
                }
                coord_logger.debug(f"Post-normalization embedding stats: {json.dumps(post_norm_stats)}")
        
        # --- Radial distance (r) and angular position (theta) ---
        # When the SemanticCompass is active, BOTH coordinates are derived from
        # cosine similarity to the reference centroids:
        #   theta = centre angle of the best-matching sector (semantic direction)
        #   r     = strength of that match (semantic centrality / relevance)
        # This is necessary because sentence-transformer embeddings are L2-normalised
        # (constant magnitude 1.0), which makes the legacy magnitude-based r degenerate
        # (every node would collapse to the same radius). Configs without the compass
        # keep the legacy magnitude/arctan2 behaviour.
        if self.semantic_compass is not None:
            similarities = self.semantic_compass.get_sector_similarities(embedding)
            sector_name = max(similarities, key=similarities.get)
            theta = self.semantic_compass.SECTOR_ANGLES[sector_name]
            theta_source = f"semantic_compass:{sector_name}"
            r = float(similarities[sector_name]) * self.embedding_r_scale
            r_source = "semantic_centrality"
            if self.log_coordinates:
                coord_logger.debug(f"Semantic compass assigned sector {sector_name} "
                                   f"(theta={theta:.4f}, r={r:.4f}) for {doc_id}/{chunk_id}")
        else:
            # Legacy path: radial distance from raw embedding magnitude.
            r = np.linalg.norm(embedding) * self.embedding_r_scale
            r_source = "embedding_magnitude"
            if embedding.size >= 2:
                theta_source = "projection"
                pre_norm_theta = np.arctan2(embedding[1], embedding[0]) * self.embedding_theta_scale
                theta = self._normalize_theta(pre_norm_theta)
            else:
                theta = 0.0
                theta_source = "fallback"

        # Log pre-normalization r value
        if self.log_coordinates:
            coord_logger.debug(f"Pre-normalized r value for {doc_id}/{chunk_id}: {r:.6f} ({r_source})")

        r = self._normalize_radius(r)
            
        # Log detailed coordinate derivation
        if self.log_coordinates:
            derivation = {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "r_calculation": {
                    "embedding_norm": float(np.linalg.norm(embedding)),
                    "scale_factor": self.embedding_r_scale,
                    "final_r": float(r)
                },
                "theta_calculation": {
                    "source": theta_source,
                    "value": float(theta)
                },
                "t_value": float(structural_coords.t),
                "z_calculation": {
                    "value": float(structural_coords.z),
                    "type": structural_coords.z_type
                }
            }
            coord_logger.debug(f"Coordinate derivation: {json.dumps(derivation)}")
            
        logger.debug(f"Calculated embedding-based coordinates: r={r:.4f}, theta={theta:.4f} rad, t={structural_coords.t:.4f}, z={structural_coords.z:.4f}")
            
        # Create coordinate with embedding-based r and theta, structural t and z
        coords = PolarTemporalCoordinate(
            r=float(r),
            theta=float(theta),
            t=structural_coords.t,
            z=structural_coords.z,
            z_type=structural_coords.z_type
        )
        
        # Handle any potential edge cases
        return self._handle_edge_case_coordinates(coords)

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
        # Extract identifiers for logging
        doc_id = metadata.get('doc_id', 'unknown_doc')
        chunk_id = metadata.get('chunk_id', f"chunk_{time.time()}")
        
        # Log start of structural coordinate calculation
        if self.log_coordinates:
            coord_logger.debug(f"Computing structural coordinates for {doc_id}/{chunk_id}")

        page_number = metadata.get('page_number', 1) # Default to 1 if missing
        chunk_index = metadata.get('chunk_index_on_page', 0) # Default to 0
        total_chunks_on_page = metadata.get('total_chunks_on_page', 1) # Default to 1 if missing
        if total_chunks_on_page <= 0:
            logger.warning(f"Invalid total_chunks_on_page ({total_chunks_on_page}) in metadata for page {page_number}, defaulting to 1.")
            total_chunks_on_page = 1 # Ensure it's at least 1

        # --- 1. Temporal Coordinate (t) ---
        # Maps page number and chunk index to a continuous time value.
        t = float(page_number - 1) + (float(chunk_index) / float(total_chunks_on_page))
        
        # Log t calculation details
        if self.log_coordinates:
            t_calc = {
                "page_number": page_number,
                "chunk_index": chunk_index, 
                "total_chunks": total_chunks_on_page,
                "resulting_t": t
            }
            coord_logger.debug(f"Temporal coordinate calculation: {json.dumps(t_calc)}")

        # --- 2. Radial Distance (r) ---
        # Assign the fixed placeholder radius for Phase 1.
        r = float(self.base_radius) # Using base_radius as placeholder

        # --- 3. Angular Position (theta) ---
        # Assign a fixed placeholder angle for Phase 1.
        theta_rad = 0.0 # Simple placeholder

        # --- 4. Structural Coordinate (z) and Type (z_type) ---
        # Derive z and z_type from structural metadata (LLM analysis results)
        perspective = metadata.get("structural_perspective")
        layer_type = metadata.get("structural_layer_type", 'MAIN')
        version = metadata.get("structural_version")
        abstraction_level = metadata.get("structural_abstraction_level", 'DETAILED')
        doc_id = metadata.get("doc_id")

        z: float = 0.0
        z_type: Z_TYPES = 'DEFAULT'
        
        # Log available structural metadata fields
        if self.log_coordinates:
            structural_fields = {
                "perspective": perspective is not None,
                "layer_type": layer_type if layer_type != 'MAIN' else None,
                "version": version is not None,
                "abstraction_level": abstraction_level if abstraction_level != 'DETAILED' else None,
                "doc_id": doc_id is not None
            }
            coord_logger.debug(f"Structural metadata fields for z calculation: {json.dumps(structural_fields)}")

        # --- Apply mapping rules based on priority ---
        z_source = "default"
        if perspective:
            # Map perspective name hash to a float range
            z = self._map_perspective_to_z(perspective)
            z_type = 'PERSPECTIVE'
            z_source = "perspective"
        elif layer_type and layer_type != 'MAIN':
            # Map predefined layers to specific z values
            z = self._map_layer_to_z(layer_type)
            potential_z_type = f'LAYER_{layer_type.upper().replace(" ", "_")}'
            if potential_z_type in Z_TYPES.__args__:
                 z_type = potential_z_type # Type: ignore[assignment]
            else:
                 logger.warning(f"Mapped layer '{layer_type}' resulted in unrecognized Z_TYPE '{potential_z_type}'. Defaulting z_type.")
                 z_type = 'DEFAULT'
            z_source = "layer_type"
        elif version:
             # Try to extract numeric part from version string
             numeric_part = None
             try:
                 match = re.search(r'\b(\d{4}|\d+\.?\d*)\b', version)
                 if match:
                     numeric_part = float(match.group(1))
                     
                 if numeric_part is not None:
                     z = numeric_part * self.version_z_multiplier
                     logger.debug(f"Mapped version '{version}' to z={z} based on numeric part {numeric_part}")
                     z_source = "version_numeric"
                 else:
                     # If no number found, fall back to hashing the whole string
                     logger.debug(f"No clear numeric part in version '{version}'. Using hash for z-mapping.")
                     z = self._hash_to_z(f"version_{version}", (200.0, 300.0))
                     z_source = "version_hash"
                 z_type = 'VERSION'
             except Exception as e:
                 logger.warning(f"Error processing version '{version}' for z-mapping: {e}. Falling back to hash.")
                 # Fallback to hashing the whole string on any error
                 z = self._hash_to_z(f"version_{version}", (200.0, 300.0))
                 z_type = 'VERSION'
                 z_source = "version_hash_fallback"
        elif abstraction_level and abstraction_level != 'DETAILED':
             z = self._map_abstraction_to_z(abstraction_level)
             potential_z_type = f'ABSTRACTION_{abstraction_level.upper().replace(" ", "_")}'
             if potential_z_type in Z_TYPES.__args__:
                 z_type = potential_z_type # Type: ignore[assignment]
             else:
                 logger.warning(f"Mapped abstraction '{abstraction_level}' resulted in unrecognized Z_TYPE '{potential_z_type}'. Defaulting z_type.")
                 z_type = 'DEFAULT'
             z_source = "abstraction_level"
        elif doc_id:
            # Map doc_id hash or a numeric part to z
            try:
                # Try to extract a number for scaling
                doc_id_num_str = re.sub(r'\D', '', doc_id)
                if doc_id_num_str:
                     z = float(doc_id_num_str) * self.doc_id_z_multiplier
                     z_source = "doc_id_numeric"
                else:
                     # Fallback to hashing the string doc_id if no number found
                    z = self._hash_to_z(f"docid_{doc_id}", (300.0, 400.0))
                    z_source = "doc_id_hash"
                z_type = 'DOC_ID'
            except ValueError:
                 logger.warning(f"Could not process doc_id '{doc_id}' for numeric z-mapping, hashing instead.")
                 z = self._hash_to_z(f"docid_{doc_id}", (300.0, 400.0))
                 z_type = 'DOC_ID'
                 z_source = "doc_id_hash_fallback"
        
        # Log z calculation details
        if self.log_coordinates:
            z_calc = {
                "z_source": z_source,
                "z_type": z_type,
                "z_value": z
            }
            coord_logger.debug(f"Z coordinate calculation: {json.dumps(z_calc)}")

        # Final coordinate (r, theta, t, z, z_type)
        coords = PolarTemporalCoordinate(
            r=r,
            theta=theta_rad,
            t=t,
            z=z,
            z_type=z_type
        )
        
        # Log final structural coordinates
        if self.log_coordinates:
            final = coords.to_dict()
            coord_logger.debug(f"Final structural coordinates for {doc_id}/{chunk_id}: {json.dumps(final)}")

        # Handle any potential edge cases
        return self._handle_edge_case_coordinates(coords)

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
        
        # Log hash calculation if detailed logging is enabled
        if self.log_coordinates:
            hash_calc = {
                "input": input_string,
                "normalized_hash": normalized_hash,
                "z_range": f"{z_min}-{z_max}",
                "result": z_value
            }
            coord_logger.debug(f"Hash-to-Z calculation: {json.dumps(hash_calc)}")
            
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
            
    def transform_vector_to_polar_temporal(self, embedding: np.ndarray, metadata: Dict[str, Any]) -> PolarTemporalCoordinate:
        """
        Public method to transform a vector embedding to polar-temporal coordinates.
        Useful for external coordinate transformation without the full mapping process.
        
        Args:
            embedding: Vector embedding to transform
            metadata: Structural metadata for temporal and z mapping
            
        Returns:
            PolarTemporalCoordinate object with transformed coordinates
        """
        logger.info(f"Transforming vector to polar-temporal coordinates (embedding shape: {embedding.shape})")
        return self._calculate_embedding_based_coordinates(embedding, metadata)

    def get_sector_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about sector usage patterns.
        
        Returns:
            Dictionary with sector usage statistics
        """
        total_items = sum(self.sector_usage.values())
        
        analytics = {
            "total_items_mapped": total_items,
            "unique_sectors_used": len(self.sector_usage),
            "total_sectors_available": len(self.sector_system.sectors),
            "sector_coverage_percent": (len(self.sector_usage) / len(self.sector_system.sectors)) * 100,
            "sector_usage": dict(self.sector_usage),
            "most_used_sectors": [],
            "unused_sectors": []
        }
        
        if total_items > 0:
            # Calculate usage percentages and find most used
            sector_percentages = []
            for sector_id, count in self.sector_usage.items():
                percentage = (count / total_items) * 100
                sector_info = self.sector_system.get_sector_info(sector_id)
                sector_percentages.append({
                    "sector_id": sector_id,
                    "sector_name": sector_info.name if sector_info else "Unknown",
                    "count": count,
                    "percentage": percentage
                })
            
            # Sort by usage
            sector_percentages.sort(key=lambda x: x['count'], reverse=True)
            analytics["most_used_sectors"] = sector_percentages[:5]  # Top 5
        
        # Find unused sectors
        all_sector_ids = set(self.sector_system.sectors.keys())
        used_sector_ids = set(self.sector_usage.keys())
        unused_ids = all_sector_ids - used_sector_ids
        
        analytics["unused_sectors"] = [
            {
                "sector_id": sector_id,
                "sector_name": self.sector_system.get_sector_info(sector_id).name
            }
            for sector_id in unused_ids
        ]
        
        return analytics
    
    def get_items_in_sector(self, sector_id: str) -> List[str]:
        """
        Get items that have been mapped to a specific sector.
        Note: This requires maintaining an item-to-sector mapping.
        """
        # This would need to be implemented with proper item tracking
        # For now, return placeholder
        return []
    
    def suggest_sector_for_content(self, content: str) -> Dict[str, Any]:
        """
        Suggest the best sector for given content without full coordinate mapping.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with suggested sector information
        """
        # Get embedding for content
        embedding = np.array(self.embedding_service.embed_query(content))

        # Determine theta via semantic compass or legacy arctan2
        if self.semantic_compass is not None:
            sector_name, raw_theta = self.semantic_compass.embedding_to_sector(embedding)
        elif embedding.size >= 2:
            raw_theta = self._normalize_theta(
                np.arctan2(embedding[1], embedding[0]) * self.embedding_theta_scale
            )
        else:
            raw_theta = 0.0

        # Find corresponding sector
        sector_info = self.sector_system.angle_to_sector(raw_theta)
        
        # Get adjacent sectors for alternatives
        adjacent_sectors = self.sector_system.get_adjacent_sectors(sector_info.id)
        
        return {
            "suggested_sector": {
                "id": sector_info.id,
                "name": sector_info.name,
                "center_angle_deg": math.degrees(sector_info.center_angle),
                "confidence": "high"  # Could implement confidence scoring
            },
            "raw_angle_deg": math.degrees(raw_theta),
            "alternative_sectors": [
                {
                    "id": adj.id,
                    "name": adj.name,
                    "center_angle_deg": math.degrees(adj.center_angle)
                }
                for adj in adjacent_sectors
            ]
        }
    
    def change_sector_system(self, new_system: SectorSystem) -> None:
        """
        Change the angular sector system used by this mapper.
        
        Args:
            new_system: New sector system to use
        """
        old_system = self.sector_system.system
        self.sector_system = AngularSectorSystem(new_system)
        
        # Reset sector usage tracking
        self.sector_usage.clear()
        
        if self.log_coordinates:
            coord_logger.info(f"Changed sector system from {old_system.value} to {new_system.value}") 
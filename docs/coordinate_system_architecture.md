# Coordinate System Architecture: Temporal-Spatial Memory with Polar Coordinates

## Overview

The Temporal-Spatial Memory System utilizes a 4D polar-temporal coordinate system to spatially organize information in a way that enhances retrieval based on temporal, semantic, and structural relationships. This document describes the architecture of this coordinate system and how it transforms traditional vector embeddings into a more nuanced representation.

## Coordinate System Definition

The system uses a 4-dimensional coordinate space defined as:

- **r (radius)**: Represents semantic importance or relevance, derived from embedding magnitude
- **θ (theta)**: Represents directional semantic meaning, derived from embedding angular projection
- **t (temporal)**: Represents sequential/chronological position, derived from document structure
- **z (vertical)**: Represents structural layer or perspective, with various z-types

This 4D coordinate system allows for rich representation of information that combines both semantic meaning and document structure.

## Transformation Process

### From Embeddings to Polar Coordinates

The system transforms standard vector embeddings into polar-temporal coordinates through:

1. **Radius (r) Calculation**:
   - Based on the L2 norm (magnitude) of the embedding vector
   - Scaled by `embedding_r_scale` parameter
   - Normalized to fall within allowed range (`min_radius` to `max_radius`)

2. **Theta (θ) Calculation**:
   - Derived from the angular position in the 2D projection of embeddings
   - Calculated using arctan2 of the first two principal dimensions
   - Normalized to [0, 2π) range
   - Scaled by `embedding_theta_scale` parameter

3. **Temporal (t) Calculation**:
   - Based on document structure: page number and position within page
   - Calculated as: `t = (page_number - 1) + (chunk_index / total_chunks_on_page)`
   - Provides chronological sequence independent of semantic meaning

4. **Z-coordinate (z) Calculation**:
   - Based on structural metadata such as document layer, perspective, or abstraction level
   - Different `z_type` values determine interpretation (e.g., LAYER, PERSPECTIVE, VERSION)
   - Allows for representation of different information layers or viewpoints

## Edge Case Handling

The system implements several normalization functions to handle edge cases:

- **Radius Normalization**: Ensures r values stay within defined bounds
- **Theta Normalization**: Wraps angles to the [0, 2π) range
- **NaN/Infinity Handling**: Replaces invalid values with defaults
- **Embedding Normalization**: Optional unit vector normalization before coordinate calculation

## Impact on Retrieval

The polar-temporal coordinate system enhances retrieval methods through:

1. **Temporal Decay Functions**: Reduce relevance of documents based on temporal distance
2. **Directional Bias**: Favor information in certain semantic directions
3. **Radial Preference**: Prioritize information at specific importance levels
4. **Z-layer Filtering**: Filter information based on structural layers or perspectives

## Visualization

The coordinate system is visualized through:

- **2D Polar Views**: Shows r-θ relationships
- **Temporal Projections**: Shows t-dimension relationship to other coordinates
- **3D Views**: Combines multiple dimensions for comprehensive visualization
- **Heatmaps**: Shows information density across different coordinate planes

## Configuration Parameters

The coordinate mapper is highly configurable through parameters:

- `base_radius`: Default radius for structurally mapped coordinates
- `embedding_r_scale`: Scaling factor for embedding-based radius
- `embedding_theta_scale`: Scaling factor for embedding-based angle
- `normalize_embeddings`: Whether to normalize embeddings to unit length
- `max_radius`/`min_radius`: Bounds for radius values
- Various z-mapping parameters (perspective_z_range, layer_z_map, etc.)

## Integration with Narrative Atlas

The coordinate system is integrated with the Narrative Atlas through:

- Storage of coordinates alongside embeddings in nodes
- Coordinate-based filtering in queries
- Coordinate-adjusted relevance scoring
- Coordinate-based visualization and analysis tools 
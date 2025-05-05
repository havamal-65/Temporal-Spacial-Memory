# Phase 7: Embedding Coordinate System Alignment

## Overview

This phase addresses a critical issue where the coordinate system configuration was inconsistent between ingestion and retrieval, causing queries to fail. We also implemented advanced retrieval methods to improve query performance.

## Key Changes

### 1. Fixed Coordinate System Mismatch

- Added validation to ensure that the coordinate system parameters match between ingestion and retrieval
- Modified `NarrativeAtlas` to validate coordinate configurations
- Added a `get_config` method to the `CoordinateMapper` class
- Ensured that `use_embedding_coords` is consistently set to `true` in both contexts
- Applied the validated configuration to new CoordinateMapper instances during query processing

### 2. Implemented Advanced Retrieval Methods

#### Hypothetical Document Embeddings (HyDE)

HyDE is an embedding technique that:
1. Takes the user's query
2. Generates a hypothetical document that would answer the query
3. Embeds the hypothetical document instead of the original query
4. Uses that embedding for similarity search

This approach often yields better search results because the hypothetical document contains more semantic context than the original query.

#### Hybrid Search

Implemented a hybrid search that combines:
- Semantic search using embeddings
- Keyword-based search with exact content matching
- Results fusion with weighted scoring

This addresses limitations of pure semantic search, particularly for explicit keyword queries. In our testing, this allowed us to successfully find "Hobbit" content that was previously not being returned.

### 3. Command Line Interface Enhancements

Added new command line options:
- `--use-hyde`: Use Hypothetical Document Embeddings for retrieval
- `--use-hybrid-search`: Use hybrid search combining semantic and keyword-based retrieval
- `--keyword-weight`: Control the weight given to keyword matches in hybrid search

## Implementation Details

### Coordinate System Consistency

To ensure coordinate system consistency:

1. Fixed `preprocess_query` method in `NarrativeAtlas` to use the same configuration as the main coordinate mapper:
   ```python
   # FIXED: Ensure consistent coordinate parameters with main mapper
   main_config = self.coordinate_mapper.get_config()
   self._coordinate_mapper_for_keywords = CoordinateMapper(
       embedding_service=self.embedding_service,
       use_embedding_for_coords=main_config.get('use_embedding_coords', True),
       embedding_r_scale=main_config.get('embedding_r_scale', 1.0),
       embedding_theta_scale=main_config.get('embedding_theta_scale', 3.14159)
   )
   ```

2. Added code to apply validated configuration to the coordinate mapper in the main query flow:
   ```python
   # Apply the validated configuration to the narrative_atlas.coordinate_mapper
   if hasattr(narrative_atlas, 'coordinate_mapper') and validated_config:
       mapper = narrative_atlas.coordinate_mapper
       
       # Update critical parameters if they exist in the validated config
       if 'use_embedding_coords' in validated_config and hasattr(mapper, 'use_embedding_for_coords'):
           mapper.use_embedding_for_coords = validated_config['use_embedding_coords']
   ```

3. Fixed formatting logic to handle different coordinate representations:
   ```python
   # Safe handling of coordinates - handle both object and dict types
   coordinates_dict = None
   temporal_coordinate = None
   
   if item_node.coordinates:
       if hasattr(item_node.coordinates, 'model_dump'):
           # Pydantic model - use model_dump() method
           coordinates_dict = item_node.coordinates.model_dump()
           temporal_coordinate = item_node.coordinates.t
       elif isinstance(item_node.coordinates, dict):
           # Already a dictionary
           coordinates_dict = item_node.coordinates
           temporal_coordinate = item_node.coordinates.get('t')
   ```

### Hybrid Search Implementation

The hybrid search implementation performs:

1. Standard semantic similarity search
2. Content-based exact keyword matching
3. Combined ranking with weighted scores

Key improvements:
- Searches the full content text, not just the keywords
- Handles single-word queries like "Hobbit" more effectively
- Considers keyword frequency in content
- Provides detailed logging of match scores

## Usage

```bash
python src/query.py --storage-path output/db_debug_all --query "Hobbit" --use-hybrid-search
```

or

```bash
python src/query.py --storage-path output/db_debug_all --query "Tell me about the main character" --use-hyde
```

## Future Work

- Implement caching for HyDE to improve performance for repeated queries
- Add more advanced hybridization strategies for combining semantic and keyword search
- Support personalized retrieval that learns from user interactions 
- Implement a more sophisticated fallback strategy for when embeddings-based search fails 
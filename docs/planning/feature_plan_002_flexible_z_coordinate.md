# Feature Plan 002: Flexible Z Coordinate with LLM-Driven Structure Analysis

**Date:** 2024-07-26

**Status:** Planned

## 1. Goal

Introduce a flexible `z` coordinate and `z_type` classification to the Narrative Atlas coordinate system (`r`, `theta`, `t`, `z`). This system will capture diverse narrative structures (perspectives, layers, versions, abstraction levels, document IDs) identified via LLM analysis during ingestion. This phased approach aims to enable richer modeling and analysis of complex narratives, supporting the ultimate goal of accurate summarization and querying.

## 2. Rationale

- **Flexibility:** Accommodates diverse narrative structures beyond simple sequence.
- **Richness:** Enables filtering, grouping, and analysis based on identified structural roles (`z_type`).
- **Foundation for Summarization:** Accurate structural understanding is crucial for high-quality summarization of complex documents.
- **Automation:** Leverages LLMs to infer structure, reducing reliance on manual metadata or brittle rules.

## 3. Phased Approach Overview

*   **Phase 1 (Current Plan):** Implement initial LLM classification during chunking to assign `z` and `z_type`. Prepare data structures and storage.
*   **Phase 2 (Future):** Implement the "Steward LLM" reconfiguration process to refine the structure based on global context during ingestion.
*   **Phase 3 (Future):** Implement semantic mapping for `r` and `theta` based on embeddings.
*   **Phase 4 (Future):** Implement post-ingestion tuning and summary reconstruction/querying capabilities.

## 4. Phase 1: Planned Steps

1.  **`src/data_models.py` (`PolarTemporalCoordinate`):**
    *   Re-add `z: float` field (using float for flexibility in mapping various structures).
    *   Add `z_type: str` field (e.g., 'DEFAULT', 'PERSPECTIVE', 'LAYER_MAIN', 'LAYER_FOOTNOTE', 'VERSION', 'ABSTRACTION_SUMMARY', 'DOC_ID'). Consider using `typing.Literal` or `enum.Enum` later.
    *   Update `__init__`, `to_dict()`, `from_dict()` accordingly.
    ```python
    # Example Change
    from typing import Literal # Or Enum

    Z_TYPES = Literal[
        'DEFAULT', 'PERSPECTIVE', 'LAYER_MAIN', 'LAYER_FOOTNOTE',
        'LAYER_COMMENTARY', 'VERSION', 'ABSTRACTION_SUMMARY', 'DOC_ID'
    ]

    class PolarTemporalCoordinate(BaseModel):
        r: float = Field(..., description="...")
        theta: float = Field(..., description="...")
        t: float = Field(..., description="Temporal coordinate (sequence)")
        z: float = Field(..., description="Flexible structural coordinate")
        z_type: Z_TYPES = Field(..., description="Type/context of the z coordinate")

        def to_dict(self) -> Dict[str, Any]:
            return {"r": self.r, "theta": self.theta, "t": self.t, "z": self.z, "z_type": self.z_type}

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "PolarTemporalCoordinate":
            # Add validation/defaults if needed
            return cls(r=data["r"], theta=data["theta"], t=data["t"], z=data["z"], z_type=data["z_type"])
    ```

2.  **`src/nl_parser.py` (or new Module `StructuralAnalyzer`):**
    *   **Integrate LLM Call:** Within the chunk processing loop (after getting a chunk from the splitter, before yielding):
        *   Prepare input for LLM: Current chunk text + local context (e.g., preceding N chars/sentences).
        *   Define LLM Prompt: Instruct the LLM to classify the chunk's structural role based on text/context.
        *   Define LLM Output Schema (JSON): e.g., `{"perspective": Optional[str], "layer_type": Optional[str], "version": Optional[str], ...}`. Specify expected values for keys like `layer_type`.
        *   Make LLM call with structured output requirement.
        *   Parse LLM JSON response.
    *   **Augment Metadata:** Add the parsed structural fields from the LLM response to the chunk's existing metadata dictionary.
    *   Yield chunk with augmented metadata.
    *   *Note:* This requires defining the LLM interaction logic (client, prompt template, output parser).

3.  **`src/utils/coordinate_mapper.py` (`CoordinateMapper`):**
    *   Modify `map_to_coordinates` to expect the augmented metadata dictionary.
    *   Implement logic in `_calculate_structural_coordinates` (or similar):
        *   Read structural fields (perspective, layer_type, etc.) from metadata.
        *   Define mapping rules: How to convert structural values to a numerical `z`? (e.g., hash perspective name + map to float range? Assign sequential floats to layers? Use version number directly?). *This mapping needs careful design.*
        *   Assign the calculated `z` value.
        *   Assign the corresponding `z_type` string based on which metadata field drove the calculation (e.g., if `metadata['perspective']` was used, `z_type = 'PERSPECTIVE'`).
        *   Handle default case (no relevant structure metadata found): `z=0.0`, `z_type='DEFAULT'`.
        *   Keep `t` calculation based on sequence.
        *   Keep `r`, `theta` as placeholders (for now).
    ```python
    # Example Logic in _calculate_structural_coordinates
    def _calculate_structural_coordinates(self, metadata: Dict[str, Any]) -> PolarTemporalCoordinate:
        # ... get t, placeholder r, theta ...

        # --- Calculate Z based on augmented metadata ---
        perspective = metadata.get("structural_perspective")
        layer_type = metadata.get("structural_layer_type", 'DEFAULT')
        version = metadata.get("structural_version")
        doc_id_num = metadata.get("structural_doc_id_num") # Assuming doc ID mapped to number

        z = 0.0
        z_type = 'DEFAULT'

        if perspective:
            # Example: Map perspective name hash to a float range
            z = self._map_perspective_to_z(perspective)
            z_type = 'PERSPECTIVE'
        elif layer_type and layer_type != 'DEFAULT':
            # Example: Map predefined layers to specific z values
            z = self._map_layer_to_z(layer_type)
            z_type = f'LAYER_{layer_type.upper()}'
        elif version:
             # Example: Use version directly (or mapped)
            z = float(version) # Or some mapping
            z_type = 'VERSION'
        elif doc_id_num is not None:
            z = float(doc_id_num)
            z_type = 'DOC_ID'
        # Add more logic for other types (abstraction, etc.)

        final_coordinate = PolarTemporalCoordinate(
            r=r, theta=theta_rad, t=t, z=z, z_type=z_type
        )
        return final_coordinate
    ```

4.  **`src/models/narrative_atlas.py` (`NarrativeAtlas`):**
    *   Update `_add_or_update_embedding` to store `coord_z` and `coord_z_type` in the document metadata.
    *   Add method signatures for future updates (Phase 2), e.g., `update_node_coordinates(node_id, new_coords: PolarTemporalCoordinate)`.
    *   Update `_get_ids_matching_filters` to re-introduce `z` filtering and add optional filtering by `z_type`.
    ```python
    # Example Change in _add_or_update_embedding
    metadata_for_doc = {
        # ... other fields ...
        "coord_z": node.coordinates.z,
        "coord_z_type": node.coordinates.z_type,
    }

    # Example Change in _get_ids_matching_filters
    # ... check r, t, theta ...
    if match and filters.z_min is not None and coords.z < filters.z_min:
        match = False
    if match and filters.z_max is not None and coords.z > filters.z_max:
        match = False
    if match and filters.z_type is not None and coords.z_type != filters.z_type:
         match = False
    ```

5.  **`src/nl_parser.py` (Query Parser):**
    *   Re-add `z_min: Optional[float]` and `z_max: Optional[float]` to `CoordinateFilters`.
    *   Add `z_type: Optional[str]` (or Enum/Literal) to `CoordinateFilters`.
    *   Update system prompt to guide LLM on interpreting queries involving structural layers/perspectives/versions and mapping them to `z`/`z_type` filters.

## 5. Open Questions / Design Decisions

- Precise LLM prompt and output schema for structural classification.
- Strategy for handling LLM context limits for classification (how much local context?).
- Specific mapping logic from structural metadata (names, types) to numerical `z` values.
- Definition of the `z_type` enum/literal values.
- Error handling if LLM classification fails.

## 6. Future Phases

- Implement Phase 2: "Steward LLM" logic for reconfiguration.
- Implement Phase 3: Semantic `r`/`theta` mapping.
- Implement Phase 4: Summarization and advanced querying. 
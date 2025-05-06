from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal

Z_TYPES = Literal[
    'DEFAULT', 'PERSPECTIVE', 'LAYER_MAIN', 'LAYER_FOOTNOTE',
    'LAYER_COMMENTARY', 'VERSION', 'ABSTRACTION_SUMMARY', 'DOC_ID'
]

class PolarTemporalCoordinate(BaseModel):
    r: float = Field(..., description="Radial coordinate (distance from origin)")
    theta: float = Field(..., description="Angular coordinate (angle in radians)")
    t: float = Field(..., description="Temporal coordinate (sequence)")
    z: float = Field(..., description="Flexible structural coordinate")
    z_type: Z_TYPES = Field(..., description="Type/context of the z coordinate")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, supporting both Pydantic v1 and v2 styles."""
        try:
            # Try Pydantic v2 approach first
            return self.model_dump()
        except AttributeError:
            # Fallback to v1 approach
            return {"r": self.r, "theta": self.theta, "t": self.t, "z": self.z, "z_type": self.z_type}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolarTemporalCoordinate":
        # Add validation/defaults if needed later
        return cls(r=data["r"], theta=data["theta"], t=data["t"], z=data["z"], z_type=data["z_type"])

class ChunkMetadata(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    embedding: Optional[list[float]] = None
    coordinate: PolarTemporalCoordinate
    page_number: Optional[int] = None
    total_pages: Optional[int] = None
    chunk_index_on_page: Optional[int] = None
    total_chunks_on_page: Optional[int] = None
    file_name: Optional[str] = None
    # Add any other relevant metadata fields 
"""
Temporal Reasoning Module for the Narrative Atlas

This module provides advanced temporal reasoning capabilities for the Narrative Atlas,
including temporal feature extraction, temporal logic, coordinate extensions, and causal detection.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union

# Define module-wide constants and enums
class TemporalGranularity(Enum):
    """Represents the granularity level of temporal expressions."""
    EXACT = "exact"        # Exact timestamp/date
    DAY = "day"            # Day-level granularity
    WEEK = "week"          # Week-level granularity
    MONTH = "month"        # Month-level granularity
    YEAR = "year"          # Year-level granularity
    DECADE = "decade"      # Decade-level granularity
    CENTURY = "century"    # Century-level granularity
    UNKNOWN = "unknown"    # Unknown or unspecified granularity


class TemporalExpression:
    """Base class for extracted temporal expressions."""
    
    def __init__(
        self, 
        text: str, 
        start_offset: int,
        end_offset: int,
        normalized_value: Optional[str] = None,
        confidence: float = 1.0,
        granularity: TemporalGranularity = TemporalGranularity.UNKNOWN
    ):
        self.text = text  # Original text span containing the temporal expression
        self.start_offset = start_offset  # Start character offset in source text
        self.end_offset = end_offset  # End character offset in source text
        self.normalized_value = normalized_value  # ISO-formatted value when available
        self.confidence = confidence  # Confidence score [0.0-1.0]
        self.granularity = granularity  # Temporal granularity
    
    def __repr__(self) -> str:
        return (f"TemporalExpression(text='{self.text}', "
                f"normalized='{self.normalized_value}', "
                f"confidence={self.confidence:.2f})")


# Module exports
from .feature_extractor import TemporalFeatureExtractor
from .coordinate_extension import TemporalCoordinateExtension

__all__ = [
    'TemporalGranularity',
    'TemporalExpression',
    'TemporalFeatureExtractor',
    'TemporalCoordinateExtension',
] 
"""
Temporal Coordinate Extension Module

This module extends the existing coordinate system with temporal dimensions and capabilities.
"""

import math
from typing import Dict, Optional, Any, List, Tuple
import numpy as np
from datetime import datetime, timedelta
import re

from . import TemporalExpression, TemporalGranularity


class TemporalCoordinateExtension:
    """
    Enhances the existing coordinate system with temporal dimensions and capabilities.
    
    This class provides methods for:
    1. Converting temporal expressions to coordinate values
    2. Calculating temporal distance and relevance
    3. Supporting time-aware querying and filtering
    """
    
    def __init__(
        self,
        base_time_scale: float = 1.0,
        decay_rate: float = 0.1,
        reference_time: Optional[datetime] = None
    ):
        """
        Initialize the temporal coordinate extension.
        
        Args:
            base_time_scale: Scaling factor for temporal dimension (default: 1.0)
            decay_rate: Decay rate for temporal relevance (default: 0.1)
            reference_time: Reference time for relative calculations (default: current time)
        """
        self.base_time_scale = base_time_scale
        self.decay_rate = decay_rate
        self.reference_time = reference_time or datetime.now()
    
    def extend_coordinate(
        self,
        base_coordinate: Dict[str, float],
        temporal_expression: Optional[TemporalExpression] = None,
        timestamp: Optional[float] = None,
        sequence_position: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Extend a base coordinate with temporal dimensions.
        
        Args:
            base_coordinate: The base coordinate to extend (r, theta)
            temporal_expression: Optional temporal expression to derive time from
            timestamp: Optional explicit timestamp (epoch time)
            sequence_position: Optional sequence position for ordinal time
            
        Returns:
            Extended coordinate with temporal dimensions
        """
        extended_coordinate = base_coordinate.copy()
        
        # Determine the temporal value, prioritizing explicit timestamp
        if timestamp is not None:
            t_value = timestamp
        elif sequence_position is not None:
            t_value = float(sequence_position)
        elif temporal_expression is not None and temporal_expression.normalized_value:
            try:
                # Check if the normalized value is just a year (4 digits)
                normalized_value = temporal_expression.normalized_value
                if re.match(r"^\d{4}$", normalized_value):
                    # Expand to full date format (YYYY-01-01)
                    full_date = f"{normalized_value}-01-01"
                    dt = datetime.fromisoformat(full_date)
                elif len(normalized_value.split('-')) == 2:
                    # Handle YYYY-MM format
                    full_date = f"{normalized_value}-01"
                    dt = datetime.fromisoformat(full_date)
                else:
                    # Regular case - complete ISO format
                    dt = datetime.fromisoformat(normalized_value)
                t_value = dt.timestamp()
            except (ValueError, TypeError) as e:
                # If parsing fails, use a sequence number based on confidence
                t_value = 0.0
        else:
            # Default to current time if no temporal info is provided
            t_value = self.reference_time.timestamp()
        
        # Add temporal dimension to coordinate
        extended_coordinate['t'] = t_value
        
        # Calculate temporal decay factor based on reference time
        if timestamp is not None:
            time_diff = abs(self.reference_time.timestamp() - timestamp)
            decay_factor = math.exp(-self.decay_rate * time_diff)
            extended_coordinate['temporal_relevance'] = decay_factor
        
        return extended_coordinate
    
    def calculate_temporal_distance(
        self,
        coord1: Dict[str, float],
        coord2: Dict[str, float],
        normalize: bool = True
    ) -> float:
        """
        Calculate the temporal distance between two coordinates.
        
        Args:
            coord1: First coordinate with 't' dimension
            coord2: Second coordinate with 't' dimension
            normalize: Whether to normalize the distance to [0, 1]
            
        Returns:
            Temporal distance between the coordinates
        """
        if 't' not in coord1 or 't' not in coord2:
            return 1.0  # Maximum distance if temporal info missing
        
        # Calculate raw time difference
        time_diff = abs(coord1['t'] - coord2['t'])
        
        if normalize:
            # Normalize using an exponential decay function
            return 1.0 - math.exp(-self.decay_rate * time_diff)
        
        return time_diff
    
    def apply_temporal_weighting(
        self,
        base_score: float,
        coord: Dict[str, float],
        query_time: Optional[float] = None,
        temporal_weight: float = 0.5
    ) -> float:
        """
        Apply temporal weighting to a base similarity score.
        
        Args:
            base_score: Base similarity score (typically from embedding)
            coord: Coordinate with temporal information
            query_time: Query time (default: reference time)
            temporal_weight: Weight of temporal factor in final score
            
        Returns:
            Temporally weighted score
        """
        if 't' not in coord or temporal_weight <= 0:
            return base_score
        
        query_t = query_time or self.reference_time.timestamp()
        
        # Calculate temporal distance (normalized to [0, 1])
        temporal_distance = self.calculate_temporal_distance(
            {'t': query_t},
            {'t': coord['t']},
            normalize=True
        )
        
        # Temporal relevance is inverse of distance
        temporal_relevance = 1.0 - temporal_distance
        
        # Combine base score with temporal relevance
        return (1 - temporal_weight) * base_score + temporal_weight * temporal_relevance
    
    def create_temporal_filter(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        reference_point: Optional[float] = None,
        window_size: Optional[float] = None
    ) -> callable:
        """
        Create a filter function for temporal constraints.
        
        Args:
            start_time: Start of temporal range (inclusive)
            end_time: End of temporal range (inclusive)
            reference_point: Reference time point
            window_size: Window size around reference point
            
        Returns:
            Filter function that takes a coordinate and returns a boolean
        """
        # Handle window-based filtering
        if reference_point is not None and window_size is not None:
            start_time = reference_point - window_size / 2
            end_time = reference_point + window_size / 2
        
        # Create the filter function
        def temporal_filter(coord: Dict[str, float]) -> bool:
            if 't' not in coord:
                return False
            
            t_value = coord['t']
            
            if start_time is not None and t_value < start_time:
                return False
                
            if end_time is not None and t_value > end_time:
                return False
                
            return True
        
        return temporal_filter
    
    def time_to_coordinate_value(self, time_value: Any) -> float:
        """
        Convert a time value to a coordinate value.
        
        Args:
            time_value: Time value (datetime, timestamp, or string)
            
        Returns:
            Coordinate value for the time dimension
        """
        if isinstance(time_value, datetime):
            return time_value.timestamp()
        
        elif isinstance(time_value, (int, float)):
            # Assume it's already a timestamp
            return float(time_value)
        
        elif isinstance(time_value, str):
            try:
                # Try to parse as ISO format
                dt = datetime.fromisoformat(time_value)
                return dt.timestamp()
            except ValueError:
                # If parsing fails, return a default
                return self.reference_time.timestamp()
        
        # Default case
        return self.reference_time.timestamp()
    
    def coordinate_value_to_time(self, coordinate_value: float) -> datetime:
        """
        Convert a coordinate value to a datetime.
        
        Args:
            coordinate_value: Coordinate value for the time dimension
            
        Returns:
            Datetime object
        """
        return datetime.fromtimestamp(coordinate_value)
    
    def get_temporal_metadata(self, coord: Dict[str, float]) -> Dict[str, Any]:
        """
        Get human-readable temporal metadata from a coordinate.
        
        Args:
            coord: Coordinate with temporal information
            
        Returns:
            Dictionary with temporal metadata
        """
        if 't' not in coord:
            return {'has_temporal_info': False}
        
        t_value = coord['t']
        dt = self.coordinate_value_to_time(t_value)
        
        metadata = {
            'has_temporal_info': True,
            'datetime': dt.isoformat(),
            'timestamp': t_value,
            'formatted_date': dt.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add reference to current time
        time_diff = abs(self.reference_time.timestamp() - t_value)
        if time_diff < 86400:  # Less than a day
            hours = time_diff / 3600
            metadata['time_diff_hours'] = round(hours, 1)
        else:
            days = time_diff / 86400
            metadata['time_diff_days'] = round(days, 1)
        
        return metadata 
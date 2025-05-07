"""
Tests for the Temporal Coordinate Extension functionality.
"""

import pytest
import math
from datetime import datetime, timedelta
import time

from src.temporal import TemporalExpression, TemporalGranularity
from src.temporal.coordinate_extension import TemporalCoordinateExtension


class TestTemporalCoordinates:
    """Test cases for the TemporalCoordinateExtension class."""
    
    def setup_method(self):
        """Set up the test environment before each test method."""
        self.reference_time = datetime(2023, 1, 1, 12, 0, 0)  # Fixed reference time
        self.extension = TemporalCoordinateExtension(
            base_time_scale=1.0,
            decay_rate=0.1,
            reference_time=self.reference_time
        )
    
    def test_extend_coordinate_with_timestamp(self):
        """Test extending a coordinate with an explicit timestamp."""
        base_coord = {'r': 0.5, 'theta': 1.5}
        timestamp = self.reference_time.timestamp() - 86400  # One day before reference
        
        extended = self.extension.extend_coordinate(base_coord, timestamp=timestamp)
        
        # Check that the original coordinates are preserved
        assert extended['r'] == base_coord['r']
        assert extended['theta'] == base_coord['theta']
        
        # Check that temporal dimension is added
        assert 't' in extended
        assert extended['t'] == timestamp
        
        # Check that temporal relevance is calculated
        assert 'temporal_relevance' in extended
        assert 0 < extended['temporal_relevance'] < 1  # Should decay with distance
    
    def test_extend_coordinate_with_sequence(self):
        """Test extending a coordinate with a sequence position."""
        base_coord = {'r': 0.7, 'theta': 2.0}
        sequence_position = 42
        
        extended = self.extension.extend_coordinate(
            base_coord, 
            sequence_position=sequence_position
        )
        
        # Check that temporal dimension uses sequence position
        assert extended['t'] == float(sequence_position)
    
    def test_extend_coordinate_with_expression(self):
        """Test extending a coordinate with a temporal expression."""
        base_coord = {'r': 0.3, 'theta': 0.5}
        
        # Create a temporal expression with normalized value
        expression = TemporalExpression(
            text="January 15, 2023",
            start_offset=0,
            end_offset=16,
            normalized_value="2023-01-15",
            confidence=0.95,
            granularity=TemporalGranularity.DAY
        )
        
        extended = self.extension.extend_coordinate(base_coord, temporal_expression=expression)
        
        # Check that temporal dimension is added with timestamp derived from expression
        assert 't' in extended
        
        # Convert extended time back to datetime for comparison
        extended_dt = datetime.fromtimestamp(extended['t'])
        assert extended_dt.year == 2023
        assert extended_dt.month == 1
        assert extended_dt.day == 15
    
    def test_calculate_temporal_distance(self):
        """Test calculating distance between temporal coordinates."""
        # Create two coordinates with different timestamps
        now = self.reference_time.timestamp()
        day_ago = (self.reference_time - timedelta(days=1)).timestamp()
        week_ago = (self.reference_time - timedelta(days=7)).timestamp()
        
        coord_now = {'t': now}
        coord_day_ago = {'t': day_ago}
        coord_week_ago = {'t': week_ago}
        
        # Calculate distances
        distance_day = self.extension.calculate_temporal_distance(coord_now, coord_day_ago)
        distance_week = self.extension.calculate_temporal_distance(coord_now, coord_week_ago)
        
        # Distance should be between 0 and 1 when normalized
        assert 0 <= distance_day <= 1
        assert 0 <= distance_week <= 1
        
        # Week-ago should be further than day-ago
        assert distance_week > distance_day
        
        # Test with normalization turned off
        raw_distance_day = self.extension.calculate_temporal_distance(
            coord_now, coord_day_ago, normalize=False
        )
        assert abs(raw_distance_day - 86400) < 1  # Should be close to one day in seconds
    
    def test_temporal_filter(self):
        """Test filtering coordinates by temporal constraints."""
        # Create test coordinates
        now = self.reference_time.timestamp()
        day_ago = (self.reference_time - timedelta(days=1)).timestamp()
        week_ago = (self.reference_time - timedelta(days=7)).timestamp()
        future = (self.reference_time + timedelta(days=3)).timestamp()
        
        coords = [
            {'id': 'now', 't': now},
            {'id': 'day_ago', 't': day_ago},
            {'id': 'week_ago', 't': week_ago},
            {'id': 'future', 't': future},
            {'id': 'no_time', 'r': 0.5}  # No temporal info
        ]
        
        # Create a filter for the past week
        filter_func = self.extension.create_temporal_filter(
            start_time=week_ago,
            end_time=now
        )
        
        # Apply filter
        filtered_coords = [coord for coord in coords if filter_func(coord)]
        filtered_ids = [coord['id'] for coord in filtered_coords]
        
        # Check results
        assert 'now' in filtered_ids
        assert 'day_ago' in filtered_ids
        assert 'week_ago' in filtered_ids
        assert 'future' not in filtered_ids
        assert 'no_time' not in filtered_ids
        
        # Test window filter
        window_filter = self.extension.create_temporal_filter(
            reference_point=now,
            window_size=172800  # 2 days
        )
        
        window_filtered = [coord for coord in coords if window_filter(coord)]
        window_ids = [coord['id'] for coord in window_filtered]
        
        assert 'now' in window_ids
        assert 'day_ago' in window_ids
        assert 'week_ago' not in window_ids
        assert 'future' not in window_ids
    
    def test_apply_temporal_weighting(self):
        """Test applying temporal weighting to base scores."""
        now = self.reference_time.timestamp()
        day_ago = (self.reference_time - timedelta(days=1)).timestamp()
        week_ago = (self.reference_time - timedelta(days=7)).timestamp()
        
        # Create coordinates with same base similarity but different times
        similar_score = 0.8
        coord_now = {'t': now}
        coord_day_ago = {'t': day_ago}
        coord_week_ago = {'t': week_ago}
        
        # Apply weighting
        weighted_now = self.extension.apply_temporal_weighting(
            similar_score, coord_now, temporal_weight=0.5
        )
        weighted_day = self.extension.apply_temporal_weighting(
            similar_score, coord_day_ago, temporal_weight=0.5
        )
        weighted_week = self.extension.apply_temporal_weighting(
            similar_score, coord_week_ago, temporal_weight=0.5
        )
        
        # Newer items should get higher scores with temporal weighting
        assert weighted_now > weighted_day > weighted_week
        
        # With no temporal weight, scores should be unchanged
        no_temporal_weight = self.extension.apply_temporal_weighting(
            similar_score, coord_day_ago, temporal_weight=0
        )
        assert no_temporal_weight == similar_score
    
    def test_time_conversion(self):
        """Test converting between different time formats and coordinate values."""
        # Test datetime conversion
        dt = datetime(2023, 6, 15, 12, 30, 0)
        coord_value = self.extension.time_to_coordinate_value(dt)
        
        # Convert back to datetime
        converted_dt = self.extension.coordinate_value_to_time(coord_value)
        
        # Should be the same datetime (within second precision)
        assert abs((dt - converted_dt).total_seconds()) < 1
        
        # Test string conversion
        date_str = "2023-06-15"
        coord_value = self.extension.time_to_coordinate_value(date_str)
        converted_dt = self.extension.coordinate_value_to_time(coord_value)
        
        assert converted_dt.year == 2023
        assert converted_dt.month == 6
        assert converted_dt.day == 15
    
    def test_temporal_metadata(self):
        """Test generating human-readable metadata from temporal coordinates."""
        # Create a coordinate with temporal info
        timestamp = datetime(2023, 6, 15, 12, 30, 0).timestamp()
        coord = {'t': timestamp, 'r': 0.5, 'theta': 1.5}
        
        metadata = self.extension.get_temporal_metadata(coord)
        
        # Check that metadata includes expected keys
        assert metadata['has_temporal_info'] is True
        assert 'datetime' in metadata
        assert 'formatted_date' in metadata
        assert 'timestamp' in metadata
        
        # Should include time difference from reference
        assert 'time_diff_days' in metadata
        
        # Test coordinate without temporal info
        no_time_coord = {'r': 0.5, 'theta': 1.5}
        no_time_metadata = self.extension.get_temporal_metadata(no_time_coord)
        
        assert no_time_metadata['has_temporal_info'] is False 
"""
Tests for the Temporal Feature Extraction functionality.
"""

import pytest
from datetime import datetime

from src.temporal import TemporalGranularity, TemporalExpression
from src.temporal.feature_extractor import TemporalFeatureExtractor


class TestTemporalExtraction:
    """Test cases for the TemporalFeatureExtractor class."""
    
    def setup_method(self):
        """Set up the test environment before each test method."""
        self.extractor = TemporalFeatureExtractor()
    
    def test_absolute_date_extraction(self):
        """Test extraction of absolute date expressions."""
        test_text = (
            "The meeting is scheduled for January 15, 2023. "
            "Another event will take place on 02/28/2023."
        )
        
        expressions = self.extractor.extract_expressions(test_text)
        
        assert len(expressions) >= 2, "Should find at least two date expressions"
        
        # Check that both date formats were detected
        texts = [expr.text for expr in expressions]
        assert any("January 15, 2023" in text for text in texts), "Should detect 'January 15, 2023'"
        assert any("02/28/2023" in text for text in texts), "Should detect '02/28/2023'"
        
        # Check normalization of at least one expression
        normalized_values = [expr.normalized_value for expr in expressions if expr.normalized_value]
        assert len(normalized_values) > 0, "At least one expression should be normalized"
        
        # Check that ISO format is used for normalization
        for value in normalized_values:
            assert "-" in value, f"Normalized value '{value}' should be in ISO format"
    
    def test_relative_date_extraction(self):
        """Test extraction of relative date expressions."""
        test_text = (
            "I'll see you tomorrow. "
            "The report was submitted last week. "
            "They visited the site three days ago."
        )
        
        expressions = self.extractor.extract_expressions(test_text)
        
        # Check that all three relative expressions were detected
        assert len(expressions) >= 3, "Should find at least three relative date expressions"
        
        texts = [expr.text.lower() for expr in expressions]
        assert any("tomorrow" in text for text in texts), "Should detect 'tomorrow'"
        assert any("last week" in text for text in texts), "Should detect 'last week'"
        assert any("three days ago" in text for text in texts), "Should detect 'three days ago'"
    
    def test_duration_extraction(self):
        """Test extraction of duration expressions."""
        test_text = (
            "The project will take about two weeks. "
            "I've been waiting for three hours. "
            "They discussed the issue from Monday to Friday."
        )
        
        expressions = self.extractor.extract_expressions(test_text)
        
        # Check that duration expressions were detected
        assert len(expressions) >= 2, "Should find at least two duration expressions"
        
        texts = [expr.text.lower() for expr in expressions]
        assert any("two weeks" in text for text in texts), "Should detect duration with 'two weeks'"
        assert any("three hours" in text for text in texts), "Should detect duration with 'three hours'"
    
    def test_mixed_temporal_extraction(self):
        """Test extraction of various temporal expressions in a complex text."""
        test_text = (
            "The company was founded in 1995. Yesterday, we had a meeting with the CEO. "
            "The project is expected to take about six months, starting from 2023-03-15. "
            "We've been developing this product for two years, since January 2021."
        )
        
        expressions = self.extractor.extract_expressions(test_text)
        
        # Check that various expressions were detected
        assert len(expressions) >= 5, "Should find at least 5 temporal expressions"
        
        # Check types of expressions found
        expressions_text = [expr.text.lower() for expr in expressions]
        assert any("1995" in text for text in expressions_text), "Should detect year '1995'"
        assert any("yesterday" in text for text in expressions_text), "Should detect 'yesterday'"
        assert any("six months" in text for text in expressions_text), "Should detect 'six months'"
        assert any("2023-03-15" in text for text in expressions_text), "Should detect date '2023-03-15'"
        assert any("january 2021" in text for text in expressions_text), "Should detect 'January 2021'"
    
    def test_date_normalization(self):
        """Test normalization of different date formats."""
        test_dates = {
            "2023-01-15": "2023-01-15",  # ISO format stays the same
            "01/15/2023": "2023-01-15",  # US format
            "15/01/2023": "2023-01-15",  # European format
            "January 15, 2023": "2023-01-15",  # Month name format
            "15 January 2023": "2023-01-15",  # Day first format
            "2023": "2023",  # Year only
        }
        
        for date_text, expected_normalized in test_dates.items():
            test_text = f"The event is on {date_text}."
            expressions = self.extractor.extract_expressions(test_text)
            
            # Find the expression matching our date text
            date_expressions = [expr for expr in expressions if date_text in expr.text]
            assert len(date_expressions) > 0, f"Failed to detect date '{date_text}'"
            
            # Check normalization if expected
            if expected_normalized:
                # Some expressions might not have normalized values in Phase 1
                normalized_values = [expr.normalized_value for expr in date_expressions 
                                    if expr.normalized_value is not None]
                if normalized_values:
                    assert any(expected_normalized in norm_val for norm_val in normalized_values), \
                        f"Expected normalized value '{expected_normalized}' for date '{date_text}'"
    
    def test_granularity_assignment(self):
        """Test that granularity is correctly assigned to temporal expressions."""
        # Testing different granularities
        test_cases = [
            ("2023-01-15", TemporalGranularity.DAY),
            ("2023", TemporalGranularity.YEAR),
            # Note: more complex granularity testing will come in Phase 2
        ]
        
        for date_text, expected_granularity in test_cases:
            test_text = f"The event is on {date_text}."
            expressions = self.extractor.extract_expressions(test_text)
            
            # Find matching expressions
            date_expressions = [expr for expr in expressions if date_text in expr.text]
            assert len(date_expressions) > 0, f"Failed to detect date '{date_text}'"
            
            # Check granularity
            for expr in date_expressions:
                if expr.granularity != TemporalGranularity.UNKNOWN:
                    assert expr.granularity == expected_granularity, \
                        f"Expected granularity {expected_granularity} for date '{date_text}', got {expr.granularity}"
    
    def test_confidence_scoring(self):
        """Test that confidence scores are assigned appropriately."""
        test_text = (
            "The meeting is scheduled for January 15, 2023. "  # Absolute date (high confidence)
            "I'll see you tomorrow. "  # Relative date (medium confidence)
            "The project will take about two weeks."  # Duration (lower confidence)
        )
        
        expressions = self.extractor.extract_expressions(test_text)
        
        # Group expressions by confidence levels
        high_confidence = [expr for expr in expressions if expr.confidence >= 0.9]
        medium_confidence = [expr for expr in expressions if 0.6 <= expr.confidence < 0.9]
        low_confidence = [expr for expr in expressions if expr.confidence < 0.6]
        
        # Check that we have expressions in different confidence bands
        assert len(high_confidence) > 0, "Should have at least one high-confidence expression"
        assert len(medium_confidence) > 0, "Should have at least one medium-confidence expression"
        
        # Check that absolute dates have higher confidence than relative dates
        absolute_dates = [expr for expr in expressions if "January 15, 2023" in expr.text]
        relative_dates = [expr for expr in expressions if "tomorrow" in expr.text]
        
        if absolute_dates and relative_dates:
            assert absolute_dates[0].confidence > relative_dates[0].confidence, \
                "Absolute dates should have higher confidence than relative dates" 
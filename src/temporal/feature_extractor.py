"""
Temporal Feature Extractor Module

This module provides functionality for detecting and extracting temporal expressions from text.
"""

import re
import datetime
from typing import List, Dict, Optional, Tuple, Pattern, Any
from dataclasses import dataclass

from . import TemporalExpression, TemporalGranularity


class TemporalFeatureExtractor:
    """
    Extracts temporal expressions from text.
    
    This class implements pattern-based extraction of temporal expressions from
    text, including absolute dates, relative dates, durations, and recurring events.
    """
    
    def __init__(self):
        """Initialize the temporal feature extractor."""
        # Initialize pattern dictionaries for different types of temporal expressions
        self._patterns = {
            "absolute_date": self._compile_absolute_date_patterns(),
            "relative_date": self._compile_relative_date_patterns(),
            "duration": self._compile_duration_patterns(),
            # Additional pattern types can be added here
        }
        
        # Map month names to their numeric values
        self._month_name_to_number = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }
    
    def extract_expressions(self, text: str) -> List[TemporalExpression]:
        """
        Extract all temporal expressions from the given text.
        
        Args:
            text: The input text to analyze.
            
        Returns:
            A list of TemporalExpression objects.
        """
        results = []
        
        # Extract absolute dates (e.g., "January 1, 2023", "01/01/2023")
        absolute_dates = self._extract_absolute_dates(text)
        results.extend(absolute_dates)
        
        # Extract relative dates (e.g., "yesterday", "last week", "two days ago")
        relative_dates = self._extract_relative_dates(text)
        results.extend(relative_dates)
        
        # Extract durations (e.g., "for three hours", "over the span of two weeks")
        durations = self._extract_durations(text)
        results.extend(durations)
        
        # Sort results by start offset
        results.sort(key=lambda expr: expr.start_offset)
        
        return results
    
    def _extract_absolute_dates(self, text: str) -> List[TemporalExpression]:
        """Extract absolute date expressions from text."""
        results = []
        
        for pattern_name, pattern in self._patterns["absolute_date"].items():
            for match in pattern.finditer(text):
                start, end = match.span()
                match_text = match.group(0)
                
                # Try to normalize the date expression to ISO format
                normalized_value = self._normalize_absolute_date(match, pattern_name)
                
                # Determine appropriate granularity
                granularity = self._determine_date_granularity(match, pattern_name)
                
                # Create a temporal expression with high confidence
                expression = TemporalExpression(
                    text=match_text,
                    start_offset=start,
                    end_offset=end,
                    normalized_value=normalized_value,
                    confidence=0.95,  # High confidence for regex matches
                    granularity=granularity
                )
                
                results.append(expression)
        
        return results
    
    def _extract_relative_dates(self, text: str) -> List[TemporalExpression]:
        """Extract relative date expressions from text."""
        results = []
        
        for pattern_name, pattern in self._patterns["relative_date"].items():
            for match in pattern.finditer(text):
                start, end = match.span()
                match_text = match.group(0)
                
                # For Phase 1, we'll assign lower confidence to relative dates
                # and only provide basic normalization
                normalized_value = None  # Full normalization in Phase 2
                
                # Create a temporal expression with medium confidence
                expression = TemporalExpression(
                    text=match_text,
                    start_offset=start,
                    end_offset=end,
                    normalized_value=normalized_value,
                    confidence=0.7,  # Medium confidence for relative dates
                    granularity=TemporalGranularity.UNKNOWN
                )
                
                results.append(expression)
        
        return results
    
    def _extract_durations(self, text: str) -> List[TemporalExpression]:
        """Extract duration expressions from text."""
        results = []
        
        for pattern_name, pattern in self._patterns["duration"].items():
            for match in pattern.finditer(text):
                start, end = match.span()
                match_text = match.group(0)
                
                # For Phase 1, provide basic extraction without full normalization
                expression = TemporalExpression(
                    text=match_text,
                    start_offset=start,
                    end_offset=end,
                    normalized_value=None,  # Will implement normalization in Phase 2
                    confidence=0.6,  # Lower confidence for durations
                    granularity=TemporalGranularity.UNKNOWN
                )
                
                results.append(expression)
        
        return results
    
    def _normalize_absolute_date(self, match: re.Match, pattern_name: str) -> Optional[str]:
        """
        Normalize an absolute date match to ISO format (YYYY-MM-DD).
        
        Args:
            match: A regex match object for an absolute date expression.
            pattern_name: The name of the pattern that matched.
            
        Returns:
            An ISO formatted date string or None if normalization fails.
        """
        try:
            # Extract matched groups
            groups = match.groupdict()
            
            # Handle different date formats based on available groups
            if all(key in groups and groups[key] for key in ["year", "month", "day"]):
                # Format: YYYY-MM-DD
                year = int(groups["year"])
                
                # Convert month name to number if it's a string
                if isinstance(groups["month"], str) and not groups["month"].isdigit():
                    month_name = groups["month"].lower()
                    if month_name in self._month_name_to_number:
                        month = self._month_name_to_number[month_name]
                    else:
                        # If month name is not recognized, return None
                        return None
                else:
                    month = int(groups["month"])
                
                day = int(groups["day"])
                
                # Validate date components
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    return None
                
                return f"{year:04d}-{month:02d}-{day:02d}"
            
            elif all(key in groups and groups[key] for key in ["month", "day"]):
                # Format: MM-DD (current year assumed)
                current_year = datetime.datetime.now().year
                
                # Convert month name to number if it's a string
                if isinstance(groups["month"], str) and not groups["month"].isdigit():
                    month_name = groups["month"].lower()
                    if month_name in self._month_name_to_number:
                        month = self._month_name_to_number[month_name]
                    else:
                        # If month name is not recognized, return None
                        return None
                else:
                    month = int(groups["month"])
                
                day = int(groups["day"])
                
                # Validate date components
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    return None
                
                return f"{current_year:04d}-{month:02d}-{day:02d}"
            
            elif "year" in groups and groups["year"]:
                # Just a year
                year = int(groups["year"])
                return f"{year:04d}"
            
            return None
            
        except (ValueError, KeyError) as e:
            # If normalization fails, return None
            return None
    
    def _determine_date_granularity(self, match: re.Match, pattern_name: str) -> TemporalGranularity:
        """
        Determine the granularity of a date expression based on the pattern and matched groups.
        
        Args:
            match: A regex match object for a date expression.
            pattern_name: The name of the pattern that matched.
            
        Returns:
            A TemporalGranularity value.
        """
        groups = match.groupdict()
        
        if all(key in groups and groups[key] for key in ["year", "month", "day"]):
            if "hour" in groups and groups["hour"]:
                return TemporalGranularity.EXACT
            return TemporalGranularity.DAY
        
        elif all(key in groups and groups[key] for key in ["month", "day"]):
            return TemporalGranularity.DAY
        
        elif "month" in groups and groups["month"]:
            return TemporalGranularity.MONTH
        
        elif "year" in groups and groups["year"]:
            return TemporalGranularity.YEAR
        
        # If we can't determine granularity, return UNKNOWN
        return TemporalGranularity.UNKNOWN
    
    # Pattern compilation methods
    
    def _compile_absolute_date_patterns(self) -> Dict[str, Pattern]:
        """
        Compile regex patterns for absolute date expressions.
        
        Returns:
            A dictionary mapping pattern names to compiled regex patterns.
        """
        patterns = {
            # ISO date format: YYYY-MM-DD
            "iso_date": re.compile(
                r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
            ),
            
            # US date format: MM/DD/YYYY
            "us_date": re.compile(
                r"(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{4}|\d{2})"
            ),
            
            # European date format: DD/MM/YYYY
            "euro_date": re.compile(
                r"(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4}|\d{2})"
            ),
            
            # Month name + day + year: January 1, 2023
            "month_day_year": re.compile(
                r"(?P<month>January|February|March|April|May|June|July|August|September|"
                r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
                r"(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+"
                r"(?P<year>\d{4})"
            ),
            
            # Day + month name + year: 1 January 2023
            "day_month_year": re.compile(
                r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+"
                r"(?P<month>January|February|March|April|May|June|July|August|September|"
                r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?,?\s+"
                r"(?P<year>\d{4})"
            ),
            
            # Year only: 2023
            "year_only": re.compile(
                r"\b(?P<year>(?:19|20)\d{2})\b"
            ),
        }
        
        return patterns
    
    def _compile_relative_date_patterns(self) -> Dict[str, Pattern]:
        """
        Compile regex patterns for relative date expressions.
        
        Returns:
            A dictionary mapping pattern names to compiled regex patterns.
        """
        patterns = {
            # Simple relative expressions
            "simple_relative": re.compile(
                r"\b(today|yesterday|tomorrow)\b",
                re.IGNORECASE
            ),
            
            # Expressions with "ago"
            "ago": re.compile(
                r"\b(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
                r"(?:day|week|month|year)s?\s+ago\b",
                re.IGNORECASE
            ),
            
            # Expressions with "last" or "next"
            "last_next": re.compile(
                r"\b(?:last|next)\s+(?:day|week|month|year|Monday|Tuesday|Wednesday|"
                r"Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",
                re.IGNORECASE
            ),
        }
        
        return patterns
    
    def _compile_duration_patterns(self) -> Dict[str, Pattern]:
        """
        Compile regex patterns for duration expressions.
        
        Returns:
            A dictionary mapping pattern names to compiled regex patterns.
        """
        patterns = {
            # Simple duration expressions
            "simple_duration": re.compile(
                r"\b(?:for|during|over)\s+(?:\d+|a|an|one|two|three|four|five|six|seven|"
                r"eight|nine|ten)\s+(?:minute|hour|day|week|month|year)s?\b",
                re.IGNORECASE
            ),
            
            # From-to expressions
            "from_to": re.compile(
                r"\bfrom\s+\w+\s+to\s+\w+\b",
                re.IGNORECASE
            ),
        }
        
        return patterns 
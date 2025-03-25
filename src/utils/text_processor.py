#!/usr/bin/env python3
"""
Generic text processor for narrative analysis.
Uses configuration to clean and preprocess text without content-specific references.
"""

import re
from typing import Dict, List, Any, Optional
from .config_loader import ConfigLoader

class TextProcessor:
    """
    Text processor for narrative analysis.
    
    Handles cleaning and preprocessing text based on configuration,
    removing the need for content-specific functions.
    """
    
    def __init__(self, config: ConfigLoader):
        """
        Initialize the text processor.
        
        Args:
            config: Configuration loader instance
        """
        self.config = config
        
    def clean_text(self, text: str) -> str:
        """
        Clean and preprocess text for better processing.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text
        """
        # Apply preprocessing steps based on configuration
        if self.config.get_value("text_processing.preprocessing.normalize_whitespace", True):
            text = self._normalize_whitespace(text)
            
        if self.config.get_value("text_processing.preprocessing.clean_headers", True):
            text = self._remove_headers(text)
            
        if self.config.get_value("text_processing.preprocessing.clean_page_numbers", True):
            text = self._remove_page_numbers(text)
        
        # Apply configured text replacements
        replacements = self.config.get_text_replacements()
        for replacement in replacements:
            pattern = replacement.get("pattern", "")
            replacement_text = replacement.get("replacement", "")
            case_sensitive = replacement.get("case_sensitive", False)
            
            if pattern and replacement_text:
                flags = 0 if case_sensitive else re.IGNORECASE
                text = re.sub(pattern, replacement_text, text, flags=flags)
        
        # Apply character name normalization
        text = self._normalize_character_names(text)
        
        # Apply location name normalization
        text = self._normalize_location_names(text)
        
        return text
    
    def preprocess_for_entity_extraction(self, text: str) -> str:
        """
        Add additional preprocessing to improve entity extraction.
        
        Args:
            text: Cleaned text
            
        Returns:
            Text with enhanced entity markers
        """
        # Add markers for dialogue to help with entity extraction
        text = re.sub(r'"([^"]+)" said (\w+)', r'"\1" said CHARACTER:\2', text)
        text = re.sub(r'"([^"]+)" (\w+) said', r'"\1" CHARACTER:\2 said', text)
        
        # Add location markers for known locations
        known_locations = self.config.get_known_locations()
        for location in known_locations:
            pattern = r'\b' + re.escape(location) + r'\b'
            replacement = f"LOCATION:{location}"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace."""
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Clean up spaces
        text = re.sub(r' +', ' ', text)
        
        return text
    
    def _remove_headers(self, text: str) -> str:
        """Remove headers and footers that might appear on multiple pages."""
        # Get title and author from config
        title = self.config.get_value("narrative.title", "")
        author = self.config.get_value("narrative.author", "")
        
        # If title and author are available, try to remove header/footer with them
        if title and author:
            pattern = re.escape(title) + r'\s*' + re.escape(author)
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def _remove_page_numbers(self, text: str) -> str:
        """Remove page numbers."""
        # Remove standalone page numbers (digit sequences at start of line or isolated)
        text = re.sub(r'\n\d+\n', '\n', text)
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        
        return text
    
    def _normalize_character_names(self, text: str) -> str:
        """Apply character name normalization from config."""
        # Get character name mapping
        char_mapping = self.config.get_character_mapping()
        
        # Apply mappings
        for alias, canonical in char_mapping.items():
            pattern = r'\b' + re.escape(alias) + r'\b'
            text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
        
        # Apply consistent capitalization for main characters
        main_characters = self.config.get_main_characters()
        for character in main_characters:
            # Create a pattern that matches the character name case-insensitively with word boundaries
            pattern = r'\b' + re.escape(character) + r'\b'
            # Replace with properly capitalized name
            text = re.sub(pattern, character, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_location_names(self, text: str) -> str:
        """Apply location name normalization from config."""
        # Get location name mapping
        loc_mapping = self.config.get_location_mapping()
        
        # Apply mappings
        for alias, canonical in loc_mapping.items():
            pattern = r'\b' + re.escape(alias) + r'\b'
            text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
        
        return text 
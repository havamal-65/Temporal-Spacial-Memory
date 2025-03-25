#!/usr/bin/env python3
"""
Configuration loader for the narrative processor.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

class ConfigLoader:
    """
    Utility for loading and managing configuration files for the narrative processor.
    Supports template variables in configuration values.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            config_path: Path to the configuration file. If None, uses default.
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        # Load default config if no path provided
        if not config_path:
            default_path = Path("config_examples/default_config.yaml")
            if default_path.exists():
                self.config_path = str(default_path)
            else:
                print("No configuration path provided and no default config found.")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration file.
        
        Returns:
            Configuration dictionary
        """
        if not self.config_path or not os.path.exists(self.config_path):
            print(f"Configuration file not found: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            print(f"Loaded configuration from: {self.config_path}")
            return self.config
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            return {}
    
    def get_value(self, path: str, default: Any = None) -> Any:
        """
        Get a value from the configuration using a dot-notation path.
        
        Args:
            path: Dot-notation path to the configuration value
            default: Default value if path not found
            
        Returns:
            The configuration value or default
        """
        if not self.config:
            return default
        
        # Handle dot notation
        parts = path.split('.')
        value = self.config
        
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_template_value(self, path: str, template_vars: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a value and process any template variables in it.
        
        Args:
            path: Dot-notation path to the configuration value
            template_vars: Additional template variables to use
            
        Returns:
            The processed configuration value
        """
        value = self.get_value(path)
        if not value or not isinstance(value, str):
            return value
        
        # Process template variables using both config values and provided template_vars
        try:
            # Create a context with all config values flattened to top level
            context = self._flatten_dict(self.config)
            
            # Add any additional template variables
            if template_vars:
                context.update(template_vars)
            
            # Format the string
            return value.format(**context)
        except (KeyError, ValueError) as e:
            print(f"Error processing template value for {path}: {str(e)}")
            return value
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """
        Flatten a nested dictionary for use in template formatting.
        
        Args:
            d: The dictionary to flatten
            parent_key: Key of the parent dictionary
            sep: Separator to use between keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                # Recursively flatten nested dictionaries
                items.extend(self._flatten_dict(v, new_key, sep).items())
                
                # Also add the key itself without separator for direct access
                items.append((k, v))
            else:
                items.append((new_key, v))
                
                # Add the key without parent prefix for direct access
                if parent_key:
                    items.append((k, v))
        
        return dict(items)
    
    def get_text_replacements(self) -> List[Dict[str, Any]]:
        """
        Get configured text replacements.
        
        Returns:
            List of replacement configurations
        """
        return self.get_value("text_processing.replacements", [])
    
    def get_character_mapping(self) -> Dict[str, str]:
        """
        Get character name mapping (aliases to canonical names).
        
        Returns:
            Dictionary of name mappings (alias -> canonical)
        """
        mappings = {}
        for mapping in self.get_value("characters.name_mapping", []):
            aliases = mapping.get("aliases", [])
            canonical = mapping.get("canonical", "")
            
            if canonical and aliases:
                for alias in aliases:
                    mappings[alias.lower()] = canonical
        
        return mappings
    
    def get_location_mapping(self) -> Dict[str, str]:
        """
        Get location name mapping (aliases to canonical names).
        
        Returns:
            Dictionary of location mappings (alias -> canonical)
        """
        mappings = {}
        for mapping in self.get_value("locations.name_mapping", []):
            aliases = mapping.get("aliases", [])
            canonical = mapping.get("canonical", "")
            
            if canonical and aliases:
                for alias in aliases:
                    mappings[alias.lower()] = canonical
        
        return mappings
    
    def get_common_words(self) -> List[str]:
        """
        Get list of common words to filter out from character detection.
        
        Returns:
            List of common words
        """
        return self.get_value("characters.common_words_filter", [])
    
    def get_known_locations(self) -> List[str]:
        """
        Get list of known locations.
        
        Returns:
            List of location names
        """
        return self.get_value("locations.known_locations", [])
    
    def get_main_characters(self) -> List[str]:
        """
        Get list of main characters.
        
        Returns:
            List of character names
        """
        return self.get_value("characters.main_characters", [])
    
    def get_narrative_phases(self) -> List[Dict[str, Any]]:
        """
        Get pre-defined narrative phases.
        
        Returns:
            List of narrative phase definitions
        """
        return self.get_value("predefined_elements.narrative_phases", [])
    
    def get_visualization_color(self, node_type: str) -> str:
        """
        Get visualization color for a node type.
        
        Args:
            node_type: Type of node (character, event, location, theme)
            
        Returns:
            Color code for the node type
        """
        default_colors = {
            "character": "#3498db",
            "event": "#e74c3c",
            "location": "#2ecc71",
            "theme": "#9b59b6"
        }
        
        return self.get_value(f"visualization.colors.{node_type}", 
                             default_colors.get(node_type, "#999999"))
    
    def get_node_scaling(self, node_type: str) -> float:
        """
        Get visualization scaling factor for a node type.
        
        Args:
            node_type: Type of node (character, event, location, theme)
            
        Returns:
            Scaling factor for the node type
        """
        default_scales = {
            "character": 3.0,
            "event": 5.0,
            "location": 2.0,
            "theme": 2.0
        }
        
        return self.get_value(f"visualization.node_sizing.{node_type}_scale", 
                             default_scales.get(node_type, 1.0))
    
    @staticmethod
    def to_slug(text: str) -> str:
        """
        Convert text to a slug (for filenames).
        
        Args:
            text: Text to convert
            
        Returns:
            Slug version of the text
        """
        # Convert to lowercase and remove non-alphanumeric characters
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        text = re.sub(r'_+', '_', text)
        text = text.strip('_')
        return text 
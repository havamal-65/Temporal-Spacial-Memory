#!/usr/bin/env python3
"""
NarrativeAtlas - A framework for analyzing and visualizing narrative structures
using the Temporal-Spatial Memory architecture.
"""

import os
import json
import uuid
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import hashlib

from .mesh_tube import MeshTube
from .narrative_nodes import CharacterNode, EventNode, LocationNode, ThemeNode

class NarrativeAtlas:
    """
    A framework for analyzing and visualizing narrative structures.
    
    The NarrativeAtlas extends the MeshTube database to specifically handle
    narrative elements like characters, events, locations, and themes,
    organizing them in a spatial-temporal context.
    """
    
    def __init__(self, name: str = "narrative", storage_path: str = "data"):
        """
        Initialize a new NarrativeAtlas.
        
        Args:
            name: Name of the narrative database
            storage_path: Path to store database files
        """
        self.name = name
        self.storage_path = storage_path
        self.db = MeshTube(name=name, storage_path=storage_path)
        
        # Track narrative elements by type
        self.characters: Dict[str, CharacterNode] = {}
        self.events: Dict[str, EventNode] = {}
        self.locations: Dict[str, LocationNode] = {}
        self.themes: Dict[str, ThemeNode] = {}
        
        # Text segmentation tracking
        self.segments: List[Dict[str, Any]] = []
        self.current_segment_index = 0
        
        # Narrative metrics
        self.metrics: Dict[str, Any] = {
            "character_count": 0,
            "event_count": 0,
            "location_count": 0,
            "theme_count": 0,
            "word_count": 0,
            "segment_count": 0,
            "timeline_start": 0.0,
            "timeline_end": 0.0
        }
    
    def load(self) -> None:
        """Load the narrative database."""
        # Load the underlying MeshTube database
        self.db.load()
        
        # Clear current tracking
        self.characters.clear()
        self.events.clear()
        self.locations.clear()
        self.themes.clear()
        
        # Process loaded nodes by type
        for node_id, node in self.db.nodes.items():
            node_type = node.content.get("node_type", "")
            
            if node_type == "character":
                self.characters[node_id] = CharacterNode.from_dict(node.to_dict())
            elif node_type == "event":
                self.events[node_id] = EventNode.from_dict(node.to_dict())
            elif node_type == "location":
                self.locations[node_id] = LocationNode.from_dict(node.to_dict())
            elif node_type == "theme":
                self.themes[node_id] = ThemeNode.from_dict(node.to_dict())
        
        # Load segments and metrics if available
        segments_path = os.path.join(self.storage_path, f"{self.name}_segments.json")
        if os.path.exists(segments_path):
            try:
                with open(segments_path, 'r') as f:
                    segments_data = json.load(f)
                    self.segments = segments_data.get("segments", [])
                    self.metrics = segments_data.get("metrics", self.metrics)
            except Exception as e:
                print(f"Error loading segments: {str(e)}")
    
    def save(self) -> None:
        """Save the narrative database."""
        # Save all nodes to the underlying MeshTube
        for character in self.characters.values():
            self.db.nodes[character.node_id] = character
            
        for event in self.events.values():
            self.db.nodes[event.node_id] = event
            
        for location in self.locations.values():
            self.db.nodes[location.node_id] = location
            
        for theme in self.themes.values():
            self.db.nodes[theme.node_id] = theme
        
        # Save the MeshTube database
        self.db.save()
        
        # Save segments and metrics
        segments_data = {
            "segments": self.segments,
            "metrics": self.metrics
        }
        
        segments_path = os.path.join(self.storage_path, f"{self.name}_segments.json")
        with open(segments_path, 'w') as f:
            json.dump(segments_data, f, indent=2)
    
    def process_text(self, text: str, title: str, segmentation_level: str = "paragraph") -> None:
        """
        Process a complete text, segmenting it and extracting narrative elements.
        
        Args:
            text: The full text to process
            title: The title of the narrative
            segmentation_level: How to segment the text ('paragraph', 'sentence', 'chapter')
        """
        # Preprocess text to normalize whitespace and remove extra line breaks
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Update word count
        self.metrics["word_count"] = len(text.split())
        
        # Segment the text based on the specified level
        if segmentation_level == "paragraph":
            segments = self._segment_by_paragraphs(text)
        elif segmentation_level == "sentence":
            segments = self._segment_by_sentences(text)
        elif segmentation_level == "chapter":
            segments = self._segment_by_chapters(text)
        else:
            # Default to paragraph segmentation
            segments = self._segment_by_paragraphs(text)
        
        # Update segment count
        self.metrics["segment_count"] = len(segments)
        
        # Process each segment
        timeline_position = 0.0
        segment_data = []
        
        for i, segment in enumerate(segments):
            # Skip empty segments
            if not segment.strip():
                continue
                
            # Generate a unique hash for the segment
            segment_hash = hashlib.md5(segment.encode()).hexdigest()
            
            # Process this segment
            entities = self._extract_entities_from_segment(segment, timeline_position)
            
            # Store segment data
            segment_info = {
                "id": segment_hash,
                "text": segment,
                "position": timeline_position,
                "entities": entities,
                "index": i
            }
            
            segment_data.append(segment_info)
            
            # Increment timeline position
            timeline_position += 1.0
        
        # Update the segments list
        self.segments = segment_data
        
        # Update timeline metrics
        if self.segments:
            self.metrics["timeline_start"] = self.segments[0]["position"]
            self.metrics["timeline_end"] = self.segments[-1]["position"]
        
        # Save changes
        self.save()
    
    def _segment_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double line breaks or multiple blank lines
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _segment_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - can be improved with NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _segment_by_chapters(self, text: str) -> List[str]:
        """Split text into chapters based on common chapter markers."""
        # Look for common chapter headings (Chapter X, CHAPTER X, etc.)
        chapter_pattern = r'(?i)(?:^|\n)\s*(chapter|CHAPTER|Chapter)\s+[IVXLCDM\d]+.*?(?=\n\s*(?:chapter|CHAPTER|Chapter)\s+[IVXLCDM\d]+|\Z)'
        chapters = re.findall(chapter_pattern, text, re.DOTALL)
        
        # If no chapters found, fall back to paragraph segmentation
        if not chapters:
            return self._segment_by_paragraphs(text)
            
        return [c.strip() for c in chapters if c.strip()]
    
    def _extract_entities_from_segment(self, segment: str, position: float) -> Dict[str, List[str]]:
        """
        Extract narrative entities from a text segment.
        
        Args:
            segment: Text segment to process
            position: Timeline position of this segment
            
        Returns:
            Dictionary of entity types and their IDs
        """
        # This is a placeholder for more sophisticated NLP-based entity extraction
        # For a production system, use NER models from spaCy, NLTK, etc.
        
        entities = {
            "characters": [],
            "locations": [],
            "events": [],
            "themes": []
        }
        
        # For now, we'll use simple pattern matching as a demonstration
        # These would be replaced with proper NLP in a real implementation
        
        # Extract potential character names (capitalized words)
        # This is overly simplistic but serves as a placeholder
        potential_names = re.findall(r'\b[A-Z][a-z]+\b', segment)
        
        for name in potential_names:
            # Check if this character already exists
            char_id = self._get_or_create_character(name, position)
            if char_id and char_id not in entities["characters"]:
                entities["characters"].append(char_id)
        
        # Similar simple patterns for locations (for demonstration)
        location_patterns = [r'at\s+the\s+([A-Z][a-z]+)', r'in\s+([A-Z][a-z]+)']
        for pattern in location_patterns:
            locations = re.findall(pattern, segment)
            for loc in locations:
                loc_id = self._get_or_create_location(loc, position)
                if loc_id and loc_id not in entities["locations"]:
                    entities["locations"].append(loc_id)
        
        # Extract potential events
        # In a real implementation, this would use event extraction NLP
        if len(segment) > 50:  # Only consider longer segments as potential events
            # Create a simple event from the segment
            event_desc = segment[:50] + "..." if len(segment) > 50 else segment
            event_id = self._create_event(event_desc, position, entities["characters"])
            entities["events"].append(event_id)
        
        # Update metrics
        self.metrics["character_count"] = len(self.characters)
        self.metrics["location_count"] = len(self.locations)
        self.metrics["event_count"] = len(self.events)
        
        return entities
    
    def _get_or_create_character(self, name: str, position: float) -> str:
        """Get existing character node or create a new one."""
        # Check if character exists by name
        for char_id, character in self.characters.items():
            if character.content.get("name", "").lower() == name.lower():
                # Character exists, update mentions and time if needed
                character.increment_mentions()
                return char_id
        
        # Create new character
        character = CharacterNode(
            content={"name": name},
            time=position,
            distance=0.5,  # Default distance until importance is determined
            angle=len(self.characters) * (360.0 / (len(self.characters) + 1)) if self.characters else 0.0
        )
        
        # Add to database
        self.characters[character.node_id] = character
        return character.node_id
    
    def _get_or_create_location(self, name: str, position: float) -> str:
        """Get existing location node or create a new one."""
        # Check if location exists by name
        for loc_id, location in self.locations.items():
            if location.content.get("name", "").lower() == name.lower():
                # Location exists, update scene count
                location.increment_scene_count()
                return loc_id
        
        # Create new location
        location = LocationNode(
            content={"name": name},
            time=position,
            distance=0.7,  # Default distance
            angle=len(self.locations) * (360.0 / (len(self.locations) + 1)) if self.locations else 0.0
        )
        
        # Add to database
        self.locations[location.node_id] = location
        return location.node_id
    
    def _create_event(self, description: str, position: float, participant_ids: List[str]) -> str:
        """Create a new event node."""
        # Create new event
        event = EventNode(
            content={"description": description},
            time=position,
            distance=0.3,  # Default distance for events (closer to center)
            angle=len(self.events) * (360.0 / (len(self.events) + 1)) if self.events else 0.0,
            participants=participant_ids
        )
        
        # Add to database
        self.events[event.node_id] = event
        return event.node_id
    
    def analyze_character_arc(self, character_id: str) -> Dict[str, Any]:
        """
        Analyze a character's arc throughout the narrative.
        
        Args:
            character_id: ID of the character to analyze
            
        Returns:
            Dictionary with character arc analysis
        """
        character = self.characters.get(character_id)
        if not character:
            return {"error": "Character not found"}
        
        # Get all events involving this character
        character_events = []
        for event_id, event in self.events.items():
            if character_id in event.content.get("participants", []):
                character_events.append({
                    "event_id": event_id,
                    "description": event.content.get("description", ""),
                    "time": event.time
                })
        
        # Sort events by time
        character_events.sort(key=lambda e: e["time"])
        
        # Get locations this character appeared in
        character_locations = []
        for loc_id, location in self.locations.items():
            if character_id in location.content.get("characters", []):
                character_locations.append({
                    "location_id": loc_id,
                    "name": location.content.get("name", "")
                })
        
        # Get themes associated with this character
        character_themes = []
        for theme_id, theme in self.themes.items():
            if character_id in theme.content.get("related_characters", []):
                character_themes.append({
                    "theme_id": theme_id,
                    "name": theme.content.get("name", "")
                })
        
        # Basic character arc analysis
        return {
            "character_id": character_id,
            "name": character.content.get("name", ""),
            "mentions": character.content.get("mentions", 0),
            "first_appearance": character_events[0]["time"] if character_events else 0.0,
            "last_appearance": character_events[-1]["time"] if character_events else 0.0,
            "events": character_events,
            "locations": character_locations,
            "themes": character_themes,
            "attributes": character.content.get("attributes", []),
            "relationships": character.content.get("relationships", {})
        }
    
    def analyze_narrative_structure(self) -> Dict[str, Any]:
        """
        Analyze the overall narrative structure.
        
        Returns:
            Dictionary with narrative structure analysis
        """
        # Find protagonist (character with most mentions or connections)
        protagonist = None
        max_importance = 0
        
        for char_id, character in self.characters.items():
            importance = character.content.get("mentions", 0) + len(character.connections)
            if importance > max_importance:
                max_importance = importance
                protagonist = char_id
        
        # Identify key events (those with highest importance)
        key_events = sorted(
            [(event_id, event.content.get("importance", 0.5)) for event_id, event in self.events.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 events
        
        # Identify central locations (most scenes)
        central_locations = sorted(
            [(loc_id, loc.content.get("scene_count", 0)) for loc_id, loc in self.locations.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]  # Top 3 locations
        
        # Basic narrative arc detection
        narrative_phases = []
        if self.segments:
            total_segments = len(self.segments)
            # Simple 3-act structure
            exposition_end = total_segments // 4
            rising_action_end = total_segments // 2
            climax_end = (total_segments * 3) // 4
            
            narrative_phases = [
                {"name": "Exposition", "start": 0, "end": exposition_end},
                {"name": "Rising Action", "start": exposition_end, "end": rising_action_end},
                {"name": "Climax", "start": rising_action_end, "end": climax_end},
                {"name": "Falling Action", "start": climax_end, "end": total_segments - 1},
                {"name": "Resolution", "start": total_segments - 1, "end": total_segments}
            ]
        
        return {
            "protagonist": protagonist,
            "character_count": len(self.characters),
            "event_count": len(self.events),
            "location_count": len(self.locations),
            "theme_count": len(self.themes),
            "word_count": self.metrics.get("word_count", 0),
            "segment_count": self.metrics.get("segment_count", 0),
            "key_events": key_events,
            "central_locations": central_locations,
            "narrative_phases": narrative_phases
        }
    
    def get_segment(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific text segment by index.
        
        Args:
            index: Index of the segment to retrieve
            
        Returns:
            Segment data or None if not found
        """
        if 0 <= index < len(self.segments):
            return self.segments[index]
        return None
    
    def get_segment_at_position(self, position: float, tolerance: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Get a text segment at a specific timeline position.
        
        Args:
            position: Timeline position to search for
            tolerance: Position tolerance
            
        Returns:
            Segment data or None if not found
        """
        for segment in self.segments:
            if abs(segment["position"] - position) <= tolerance:
                return segment
        return None 
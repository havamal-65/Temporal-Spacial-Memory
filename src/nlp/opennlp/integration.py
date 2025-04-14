"""
Integration of OpenNLP processor with Narrative Atlas framework.
"""

import os
import logging
from typing import Dict, List, Any, Optional

from .processor import OpenNLPProcessor
from src.models.narrative_atlas import NarrativeAtlas

logger = logging.getLogger(__name__)

class OpenNLPIntegration:
    """
    Integration of OpenNLP processor with Narrative Atlas framework.
    
    This class provides methods to process text using OpenNLP and
    populate a NarrativeAtlas instance with the extracted information.
    
    Attributes:
        processor: The OpenNLP processor
        atlas: The NarrativeAtlas instance to populate
    """
    
    def __init__(self, atlas: NarrativeAtlas, models_dir: str = "models/opennlp"):
        """
        Initialize the OpenNLP integration.
        
        Args:
            atlas: The NarrativeAtlas instance to populate
            models_dir: Directory where OpenNLP models are stored
        """
        self.processor = OpenNLPProcessor(models_dir=models_dir)
        self.atlas = atlas
        
        logger.info(f"OpenNLP integration initialized for atlas: {atlas.name}")
    
    def process_text(self, text: str, title: str, segmentation_level: str = "paragraph") -> bool:
        """
        Process text using OpenNLP and populate the NarrativeAtlas.
        
        Args:
            text: The text to process
            title: The title of the text
            segmentation_level: The level at which to segment the text
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # First, use the existing NarrativeAtlas processing
            # This creates the basic structure in the atlas
            self.atlas.process_text(text, title, segmentation_level=segmentation_level)
            
            # Then, enhance it with OpenNLP processing
            self._enhance_entities(text)
            self._enhance_relationships(text)
            self._enhance_events(text)
            
            logger.info(f"Successfully processed '{title}' with OpenNLP integration")
            return True
            
        except Exception as e:
            logger.error(f"Error processing text with OpenNLP: {str(e)}")
            return False
    
    def _enhance_entities(self, text: str) -> None:
        """
        Enhance entity extraction with OpenNLP.
        
        Args:
            text: The text to process
        """
        # Extract entities using OpenNLP
        entities = self.processor.extract_entities(text)
        
        # Enhance character entities
        for character in entities.get("characters", []):
            # Check if the character already exists
            existing_chars = [c for c in self.atlas.characters.values() 
                             if c.content.get("name") == character["name"]]
            
            if existing_chars:
                # Enhance existing character
                char = existing_chars[0]
                char.content["mentions"] = max(
                    char.content.get("mentions", 0),
                    character.get("mentions", 0)
                )
                # Update other attributes as needed
            else:
                # Create new character if not found
                self.atlas.add_character(
                    name=character["name"],
                    time=character.get("first_occurrence", 0.5),
                    distance=0.5,  # Default distance
                    angle=0.0,     # Default angle
                    content={
                        "name": character["name"],
                        "mentions": character.get("mentions", 1),
                        "description": f"Character: {character['name']}"
                    }
                )
        
        # Enhance location entities
        for location in entities.get("locations", []):
            # Check if the location already exists
            existing_locs = [l for l in self.atlas.locations.values() 
                            if l.content.get("name") == location["name"]]
            
            if existing_locs:
                # Enhance existing location
                loc = existing_locs[0]
                loc.content["mentions"] = max(
                    loc.content.get("mentions", 0),
                    location.get("mentions", 0)
                )
                # Update other attributes as needed
            else:
                # Create new location if not found
                self.atlas.add_location(
                    name=location["name"],
                    time=location.get("first_occurrence", 0.5),
                    distance=0.7,  # Default distance for locations
                    angle=0.0,     # Default angle
                    content={
                        "name": location["name"],
                        "mentions": location.get("mentions", 1),
                        "description": f"Location: {location['name']}"
                    }
                )
    
    def _enhance_relationships(self, text: str) -> None:
        """
        Enhance relationship extraction with OpenNLP.
        
        Args:
            text: The text to process
        """
        # Extract relationships using OpenNLP
        relationships = self.processor.analyze_relationships(text)
        
        # Add relationships to the atlas
        for rel in relationships:
            source_name = rel["source"]
            target_name = rel["target"]
            
            # Find source and target entities
            source_entities = [e for e in self.atlas.characters.values() 
                              if e.content.get("name") == source_name]
            target_entities = [e for e in 
                              list(self.atlas.characters.values()) + 
                              list(self.atlas.locations.values())
                              if e.content.get("name") == target_name]
            
            if source_entities and target_entities:
                source = source_entities[0]
                target = target_entities[0]
                
                # Add connection if it doesn't exist
                if target.node_id not in source.connections:
                    source.connections.append(target.node_id)
                    
                    # For bidirectional relationships
                    if rel["type"] == "friend_of" and target.node_id in self.atlas.characters:
                        target.connections.append(source.node_id)
    
    def _enhance_events(self, text: str) -> None:
        """
        Enhance event extraction with OpenNLP.
        
        Args:
            text: The text to process
        """
        # Extract events using OpenNLP
        events = self.processor.extract_events(text)
        
        # Add events to the atlas
        for event in events:
            # Check if a similar event already exists
            similar_events = [e for e in self.atlas.events.values()
                             if e.content.get("description") == event["description"]]
            
            if not similar_events:
                # Create a new event
                event_id = self.atlas.add_event(
                    description=event["description"],
                    time=event.get("time_position", 0.5),
                    distance=0.6,  # Default distance for events
                    angle=0.0,     # Default angle
                    content={
                        "description": event["description"],
                        "importance": event.get("importance", 0.5),
                        "participants": event.get("participants", []),
                        "location": event.get("location")
                    }
                )
                
                # Connect event to participants
                for participant_name in event.get("participants", []):
                    participants = [c for c in self.atlas.characters.values()
                                   if c.content.get("name") == participant_name]
                    
                    if participants:
                        participant = participants[0]
                        if event_id not in participant.connections:
                            participant.connections.append(event_id)
                
                # Connect event to location
                if event.get("location"):
                    locations = [l for l in self.atlas.locations.values()
                               if l.content.get("name") == event["location"]]
                    
                    if locations:
                        location = locations[0]
                        if event_id not in location.connections:
                            location.connections.append(event_id) 
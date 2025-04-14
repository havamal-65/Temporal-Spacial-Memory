#!/usr/bin/env python3
"""
Specialized node classes for narrative analysis within the Temporal-Spatial Memory framework.
"""

from typing import Dict, Any, Optional, List, Set
from .node import Node

class CharacterNode(Node):
    """
    A node representing a character in a narrative.
    
    Additional properties:
    - mentions: count of character mentions
    - attributes: character traits and descriptors
    - relationships: connections to other characters
    """
    
    def __init__(self,
                node_id: Optional[str] = None,
                content: Dict[str, Any] = None,
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None,
                created_at: Optional[str] = None,
                attributes: List[str] = None,
                mentions: int = 1):
        """
        Initialize a character node.
        
        Args:
            node_id: Unique identifier (generated if not provided)
            content: Node content (dictionary with character info)
            time: First appearance time or current focus time
            distance: Importance to narrative (center = protagonist)
            angle: Relationship to other characters (similar angles = related)
            parent_id: Optional ID of parent node
            created_at: Creation timestamp (ISO format)
            attributes: List of character traits/descriptors
            mentions: Count of character mentions
        """
        # Ensure content has required fields
        content = content or {}
        if "name" not in content:
            content["name"] = "Unnamed Character"
            
        # Add specialized fields to content
        content["node_type"] = "character"
        content["attributes"] = attributes or []
        content["mentions"] = mentions
        content["relationships"] = {}
        
        super().__init__(node_id, content, time, distance, angle, parent_id, created_at)
        
    def add_relationship(self, character_id: str, relationship_type: str, strength: float = 1.0) -> None:
        """
        Add or update a relationship to another character.
        
        Args:
            character_id: ID of the related character
            relationship_type: Type of relationship (friend, enemy, family, etc.)
            strength: Strength of relationship (0.0 to 1.0)
        """
        self.content["relationships"][character_id] = {
            "type": relationship_type,
            "strength": strength
        }
        self.connections.add(character_id)
        
    def update_attributes(self, attributes: List[str]) -> None:
        """
        Update character attributes.
        
        Args:
            attributes: List of character traits/descriptors
        """
        # Add new attributes while keeping existing ones
        self.content["attributes"] = list(set(self.content["attributes"] + attributes))
        
    def increment_mentions(self, count: int = 1) -> None:
        """
        Increment the mention count.
        
        Args:
            count: Number of mentions to add
        """
        self.content["mentions"] += count


class EventNode(Node):
    """
    A node representing a narrative event.
    
    Additional properties:
    - duration: time span of the event
    - participants: character IDs involved
    - importance: significance to overall plot
    """
    
    def __init__(self,
                node_id: Optional[str] = None,
                content: Dict[str, Any] = None,
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None,
                created_at: Optional[str] = None,
                duration: float = 0.0,
                importance: float = 0.5,
                participants: List[str] = None):
        """
        Initialize an event node.
        
        Args:
            node_id: Unique identifier (generated if not provided)
            content: Node content (dictionary with event info)
            time: Time of event occurrence
            distance: Centrality to main plot
            angle: Thematic orientation
            parent_id: Optional ID of parent node
            created_at: Creation timestamp (ISO format)
            duration: Time span of the event
            importance: Significance to overall plot (0.0 to 1.0)
            participants: List of character IDs involved
        """
        # Ensure content has required fields
        content = content or {}
        if "description" not in content:
            content["description"] = "Unnamed Event"
            
        # Add specialized fields to content
        content["node_type"] = "event"
        content["duration"] = duration
        content["importance"] = importance
        content["participants"] = participants or []
        
        super().__init__(node_id, content, time, distance, angle, parent_id, created_at)
        
        # Connect to all participants
        for participant_id in content["participants"]:
            self.connections.add(participant_id)
    
    def add_participant(self, character_id: str) -> None:
        """
        Add a character participant to the event.
        
        Args:
            character_id: ID of the participating character
        """
        if character_id not in self.content["participants"]:
            self.content["participants"].append(character_id)
            self.connections.add(character_id)


class LocationNode(Node):
    """
    A node representing a location in the narrative.
    
    Additional properties:
    - scene_count: number of scenes at this location
    - characters: character IDs who appeared at this location
    """
    
    def __init__(self,
                node_id: Optional[str] = None,
                content: Dict[str, Any] = None,
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None,
                created_at: Optional[str] = None,
                coordinates: Optional[Dict[str, float]] = None,
                scene_count: int = 1):
        """
        Initialize a location node.
        
        Args:
            node_id: Unique identifier (generated if not provided)
            content: Node content (dictionary with location info)
            time: First appearance time
            distance: Importance to narrative
            angle: Thematic or geographic orientation
            parent_id: Optional ID of parent node
            created_at: Creation timestamp (ISO format)
            coordinates: Optional geographic coordinates (lat/long)
            scene_count: Number of scenes at this location
        """
        # Ensure content has required fields
        content = content or {}
        if "name" not in content:
            content["name"] = "Unnamed Location"
            
        # Add specialized fields to content
        content["node_type"] = "location"
        content["coordinates"] = coordinates
        content["scene_count"] = scene_count
        content["characters"] = []
        
        super().__init__(node_id, content, time, distance, angle, parent_id, created_at)
    
    def add_character(self, character_id: str) -> None:
        """
        Record a character's presence at this location.
        
        Args:
            character_id: ID of the character
        """
        if character_id not in self.content["characters"]:
            self.content["characters"].append(character_id)
            self.connections.add(character_id)
    
    def increment_scene_count(self, count: int = 1) -> None:
        """
        Increment the scene count.
        
        Args:
            count: Number of scenes to add
        """
        self.content["scene_count"] += count


class ThemeNode(Node):
    """
    A node representing a thematic element in the narrative.
    
    Additional properties:
    - instances: count of theme occurrences
    - related_characters: characters associated with this theme
    - related_events: events that manifest this theme
    """
    
    def __init__(self,
                node_id: Optional[str] = None,
                content: Dict[str, Any] = None,
                time: float = 0.0,
                distance: float = 0.0,
                angle: float = 0.0,
                parent_id: Optional[str] = None,
                created_at: Optional[str] = None,
                instances: int = 1):
        """
        Initialize a theme node.
        
        Args:
            node_id: Unique identifier (generated if not provided)
            content: Node content (dictionary with theme info)
            time: Temporal prominence (when theme is most relevant)
            distance: Centrality to narrative
            angle: Relationship to other themes
            parent_id: Optional ID of parent node
            created_at: Creation timestamp (ISO format)
            instances: Count of theme occurrences
        """
        # Ensure content has required fields
        content = content or {}
        if "name" not in content:
            content["name"] = "Unnamed Theme"
            
        # Add specialized fields to content
        content["node_type"] = "theme"
        content["instances"] = instances
        content["related_characters"] = []
        content["related_events"] = []
        
        super().__init__(node_id, content, time, distance, angle, parent_id, created_at)
    
    def add_related_character(self, character_id: str) -> None:
        """
        Associate a character with this theme.
        
        Args:
            character_id: ID of the related character
        """
        if character_id not in self.content["related_characters"]:
            self.content["related_characters"].append(character_id)
            self.connections.add(character_id)
    
    def add_related_event(self, event_id: str) -> None:
        """
        Associate an event with this theme.
        
        Args:
            event_id: ID of the related event
        """
        if event_id not in self.content["related_events"]:
            self.content["related_events"].append(event_id)
            self.connections.add(event_id)
    
    def increment_instances(self, count: int = 1) -> None:
        """
        Increment the instance count.
        
        Args:
            count: Number of instances to add
        """
        self.content["instances"] += count 
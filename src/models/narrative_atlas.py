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
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from .spatial_temporal_db import SpatialTemporalDB
from .narrative_nodes import CharacterNode, EventNode, LocationNode, ThemeNode

class NarrativeAtlas:
    """
    A framework for analyzing and visualizing narrative structures.
    
    The NarrativeAtlas extends the MeshTube database to specifically handle
    narrative elements like characters, events, locations, and themes,
    organizing them in a spatial-temporal context. It also includes a FAISS index
    for efficient similarity search based on node embeddings.
    """
    
    DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    FAISS_INDEX_FILENAME = "narrative_atlas.faiss"
    FAISS_ID_MAP_FILENAME = "faiss_id_map.json"

    def __init__(self, name: str = "narrative", storage_path: str = "data", embedding_model_name: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initialize a new NarrativeAtlas.
        
        Args:
            name: Name of the narrative database
            storage_path: Path to store database files
            embedding_model_name: Name of the SentenceTransformer model to use
        """
        self.name = name
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True) # Ensure storage path exists
        self.db = SpatialTemporalDB(name=name, storage_path=storage_path)
        
        # Track narrative elements by type (populated during load/processing)
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

        # -- FAISS Initialization --
        self.embedding_model_name = embedding_model_name
        self.faiss_index_path = os.path.join(self.storage_path, self.FAISS_INDEX_FILENAME)
        self.faiss_id_map_path = os.path.join(self.storage_path, self.FAISS_ID_MAP_FILENAME)
        
        # Mappings and ID counter for FAISS IndexIDMap2
        self.node_id_to_faiss_id: Dict[str, int] = {} # Node ID (str) -> FAISS ID (int)
        self.faiss_id_to_node_id: Dict[int, str] = {} # FAISS ID (int) -> Node ID (str) - Renamed from faiss_id_map for clarity
        self.next_faiss_id: int = 0

        # 1. Load SentenceTransformer Model
        try:
            print(f"Loading embedding model: {self.embedding_model_name}...")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            print(f"Embedding model loaded. Dimension: {self.embedding_dim}")
        except Exception as e:
            print(f"Error loading embedding model '{self.embedding_model_name}': {e}")
            print("FAISS indexing will be disabled.")
            self.embedding_model = None
            self.faiss_index = None
            self.faiss_id_to_node_id = {}
            self.node_id_to_faiss_id = {}
            self.next_faiss_id = 0
            # If model fails, don't proceed with FAISS setup
            return 

        # 2. Load or Create ID Map and Next ID
        self.faiss_id_to_node_id = {} 
        self.node_id_to_faiss_id = {}
        self.next_faiss_id = 0
        if os.path.exists(self.faiss_id_map_path):
            try:
                print(f"Loading FAISS ID map from {self.faiss_id_map_path}...")
                with open(self.faiss_id_map_path, 'r') as f:
                    map_data = json.load(f)
                    # Load map with integer keys
                    loaded_map = map_data.get("map", {})
                    self.faiss_id_to_node_id = {int(k): v for k, v in loaded_map.items()}
                    # Load next ID
                    self.next_faiss_id = map_data.get("next_id", 0)
                    # Rebuild the reverse map
                    self.node_id_to_faiss_id = {v: k for k, v in self.faiss_id_to_node_id.items()}
                print("FAISS ID map loaded.")
            except Exception as e:
                print(f"Error loading FAISS ID map: {e}. Starting with an empty map.")
                self.faiss_id_to_node_id = {}
                self.node_id_to_faiss_id = {}
                self.next_faiss_id = 0
        else:
            print("No existing FAISS ID map found. Starting with an empty map.")
            self.faiss_id_to_node_id = {}
            self.node_id_to_faiss_id = {}
            self.next_faiss_id = 0

        # 3. Load or Create FAISS Index
        if os.path.exists(self.faiss_index_path):
            try:
                print(f"Loading FAISS index from {self.faiss_index_path}...")
                self.faiss_index = faiss.read_index(self.faiss_index_path)
                print(f"FAISS index loaded. Contains {self.faiss_index.ntotal} vectors.")
                # Sanity check dimension - though read_index doesn't expose it easily
                # We assume the loaded index matches the current model's dimension
                if self.faiss_index.d != self.embedding_dim:
                     print(f"Warning: Loaded FAISS index dimension ({self.faiss_index.d}) does not match model dimension ({self.embedding_dim}). Re-indexing may be required.")
                     # Optionally, could force re-creation here:
                     # raise ValueError("Dimension mismatch") 
            except Exception as e:
                print(f"Error loading FAISS index: {e}. Creating a new index.")
                # Fallback to creating a new index if loading fails
                self.faiss_index = faiss.IndexIDMap2(faiss.IndexFlatL2(self.embedding_dim))
                # Since index load failed, clear potentially inconsistent maps and reset ID
                self.faiss_id_to_node_id = {}
                self.node_id_to_faiss_id = {}
                self.next_faiss_id = 0
                print("New FAISS index created.")
        else:
            print("No existing FAISS index found. Creating a new index.")
            self.faiss_index = faiss.IndexIDMap2(faiss.IndexFlatL2(self.embedding_dim))
            # Ensure maps are empty and ID is reset if index is new
            self.faiss_id_to_node_id = {}
            self.node_id_to_faiss_id = {}
            self.next_faiss_id = 0
            print("New FAISS index created.")
            
        # -- End FAISS Initialization --
    
    def load(self) -> None:
        """Load the narrative database."""
        # Load the underlying MeshTube database
        self.db.load()
        
        # Clear current tracking (will be repopulated)
        self.characters.clear()
        self.events.clear()
        self.locations.clear()
        self.themes.clear()
        
        # Process loaded nodes by type
        nodes_in_db_count = 0
        for node_id, node in self.db.nodes.items():
            nodes_in_db_count += 1
            node_type = node.content.get("node_type", "")
            
            instance = None
            if node_type == "character":
                instance = CharacterNode.from_dict(node.to_dict())
                self.characters[node_id] = instance
            elif node_type == "event":
                instance = EventNode.from_dict(node.to_dict())
                self.events[node_id] = instance
            elif node_type == "location":
                instance = LocationNode.from_dict(node.to_dict())
                self.locations[node_id] = instance
            elif node_type == "theme":
                instance = ThemeNode.from_dict(node.to_dict())
                self.themes[node_id] = instance
            
            # Potential: Add logic here to re-index nodes if FAISS index was empty or mismatching
            # For now, we assume __init__ handles the initial load/creation.
            # Updates should happen when nodes are modified/added after initial load.

        print(f"Processed {nodes_in_db_count} nodes from MeshTube.")

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

        # Note: FAISS index and map are loaded during __init__, not here.
        # If the index exists, __init__ loads it. If not, it creates an empty one.
        # We might need a separate method to *rebuild* the index from loaded db nodes if needed.

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
        
        # -- Save FAISS Index and ID Map --
        if self.faiss_index is not None and self.embedding_model is not None:
            # Save FAISS Index
            try:
                print(f"Saving FAISS index to {self.faiss_index_path} ({self.faiss_index.ntotal} vectors)...")
                faiss.write_index(self.faiss_index, self.faiss_index_path)
                print("FAISS index saved.")
            except Exception as e:
                print(f"Error saving FAISS index: {e}")
            
            # Save ID Map
            try:
                print(f"Saving FAISS ID map to {self.faiss_id_map_path} ({len(self.faiss_id_to_node_id)} entries)...")
                # Convert int keys to strings for JSON compatibility
                map_data_to_save = {
                    "map": {str(k): v for k, v in self.faiss_id_to_node_id.items()},
                    "next_id": self.next_faiss_id
                }
                with open(self.faiss_id_map_path, 'w') as f:
                    json.dump(map_data_to_save, f, indent=2)
                print("FAISS ID map saved.")
            except Exception as e:
                print(f"Error saving FAISS ID map: {e}")
        else:
            print("FAISS index or embedding model not available, skipping save.")
        # -- End FAISS Save --
        
        # Save segments and metrics
        segments_data = {
            "segments": self.segments,
            "metrics": self.metrics
        }
        
        segments_path = os.path.join(self.storage_path, f"{self.name}_segments.json")
        with open(segments_path, 'w') as f:
            json.dump(segments_data, f, indent=2)
    
    def add_segment(self, text: str, position: float, entities: Dict[str, List[str]]) -> None:
        """
        Add a segment directly to the atlas, used for GraphRAG integration.
        
        Args:
            text: The segment text
            position: Timeline position (float)
            entities: Dict with entity IDs by type (characters, locations, events, themes)
        """
        # Generate a unique hash for the segment
        segment_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Create segment data structure
        segment_info = {
            "id": segment_hash,
            "text": text,
            "position": position,
            "entities": entities,
            "index": len(self.segments)
        }
        
        # Add to segments list
        self.segments.append(segment_info)
        
        # Update timeline metrics
        if len(self.segments) == 1:
            self.metrics["timeline_start"] = position
        self.metrics["timeline_end"] = max(self.metrics["timeline_end"], position)
        self.metrics["segment_count"] = len(self.segments)
        
        # Update entity counts
        self.metrics["character_count"] = len(self.characters)
        self.metrics["location_count"] = len(self.locations)
        self.metrics["event_count"] = len(self.events)
        self.metrics["theme_count"] = len(self.themes)
    
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
                # TODO: Decide if we should update embedding here if content changed?
                # For now, we assume name is the primary searchable text and doesn't change often.
                # self._add_or_update_embedding(char_id, name) # Optionally update
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
        # Add embedding for the new character
        self._add_or_update_embedding(character.node_id, name)
        return character.node_id
    
    def _get_or_create_location(self, name: str, position: float) -> str:
        """Get existing location node or create a new one."""
        # Check if location exists by name
        for loc_id, location in self.locations.items():
            if location.content.get("name", "").lower() == name.lower():
                # Location exists, update scene count
                location.increment_scene_count()
                # Optionally update embedding
                # self._add_or_update_embedding(loc_id, name)
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
        # Add embedding for the new location
        self._add_or_update_embedding(location.node_id, name)
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
        # Add embedding for the new event
        self._add_or_update_embedding(event.node_id, description)
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
    
    def get_core_story(self, threshold: float = None, top_n: int = None) -> str:
        """
        Get the core story as a summary made from the most important parts.

        You can choose how much detail you want:
        - Use 'threshold' to include all story pieces (nodes) that are close enough to the center (more important).
        - Use 'top_n' to include the top N most important pieces.
        - If you don't set either, it uses a default threshold of 0.4 (short summary).
        - If you set both, 'top_n' is used.

        Returns:
            The core story as a single string, with the most important parts in order.

        Example:
            # Get a short core story (default)
            summary = atlas.get_core_story()
            # Get a longer core story
            summary = atlas.get_core_story(threshold=0.7)
            # Get the 10 most important pieces
            summary = atlas.get_core_story(top_n=10)
        """
        # Gather all nodes (characters, events, locations, themes)
        all_nodes = list(self.characters.values()) + list(self.events.values()) + list(self.locations.values()) + list(self.themes.values())
        # Sort nodes by distance (closer = more important)
        sorted_nodes = sorted(all_nodes, key=lambda n: n.distance)

        # Decide which nodes to include
        if top_n is not None:
            selected_nodes = sorted_nodes[:top_n]
        else:
            if threshold is None:
                threshold = 0.4  # Default value
            selected_nodes = [n for n in sorted_nodes if n.distance <= threshold]

        # Get the IDs of selected nodes
        selected_ids = set(n.node_id for n in selected_nodes)

        # Gather all segments that reference these nodes, in order
        core_segments = []
        for segment in sorted(self.segments, key=lambda s: s.get('position', 0)):
            # Check if any of the segment's entities are in selected_ids
            entities = segment.get('entities', {})
            found = False
            for entity_list in entities.values():
                if any(eid in selected_ids for eid in entity_list):
                    found = True
                    break
            if found:
                core_segments.append(segment.get('text', ''))

        # Join the segments to make the core story
        core_story = '\n\n'.join(core_segments)
        return core_story

    def add_nodes_from_extraction(self, segments, all_entities):
        """
        Add nodes to the atlas from hybrid LLM/deterministic extraction results.
        Args:
            segments: List of segment dicts (should include text, and optionally time hierarchy info)
            all_entities: List of entity dicts (one per segment)
        """
        for i, (segment, entities) in enumerate(zip(segments, all_entities)):
            # Extract time hierarchy info from segment if available
            time_hierarchy = segment.get('time_hierarchy', {})
            time_type = segment.get('time_type', None)
            time_value = segment.get('time_value', None)
            position = segment.get('position', i)
            # Add characters
            for char in entities.get('characters', []):
                name = char.get('name') if isinstance(char, dict) else char
                content = {"name": name, "time_type": time_type, "time_value": time_value, "time_hierarchy": time_hierarchy}
                char_id = self._get_or_create_character_with_metadata(content, position)
            # Add locations
            for loc in entities.get('locations', []):
                name = loc.get('name') if isinstance(loc, dict) else loc
                content = {"name": name, "time_type": time_type, "time_value": time_value, "time_hierarchy": time_hierarchy}
                loc_id = self._get_or_create_location_with_metadata(content, position)
            # Add events
            for event in entities.get('events', []):
                desc = event.get('description') if isinstance(event, dict) else str(event)
                content = {"description": desc, "time_type": time_type, "time_value": time_value, "time_hierarchy": time_hierarchy}
                event_id = self._create_event_with_metadata(content, position, [])
            # Add themes
            for theme in entities.get('themes', []):
                name = theme.get('name') if isinstance(theme, dict) else theme
                content = {"name": name, "time_type": time_type, "time_value": time_value, "time_hierarchy": time_hierarchy}
                theme_id = self._get_or_create_theme_with_metadata(content, position)

    def _get_or_create_character_with_metadata(self, content, position):
        name = content.get('name', '')
        if not name:
            return None # Cannot create/index without a name
            
        for char_id, character in self.characters.items():
            if character.content.get("name", "").lower() == name.lower():
                character.increment_mentions()
                # Update existing node content if necessary (merge?)
                # Optionally update embedding if relevant content changed
                self._add_or_update_embedding(char_id, name)
                return char_id
                
        character = CharacterNode(content=content, time=position)
        self.characters[character.node_id] = character
        # Add embedding for new node
        self._add_or_update_embedding(character.node_id, name)
        return character.node_id

    def _get_or_create_location_with_metadata(self, content, position):
        name = content.get('name', '')
        if not name:
            return None # Cannot create/index without a name
            
        for loc_id, location in self.locations.items():
            if location.content.get("name", "").lower() == name.lower():
                location.increment_scene_count()
                # Update existing node content if necessary (merge?)
                # Optionally update embedding if relevant content changed
                self._add_or_update_embedding(loc_id, name)
                return loc_id
                
        location = LocationNode(content=content, time=position)
        self.locations[location.node_id] = location
        # Add embedding for new node
        self._add_or_update_embedding(location.node_id, name)
        return location.node_id

    def _create_event_with_metadata(self, content, position, participant_ids):
        description = content.get('description', '')
        if not description:
            return None # Cannot create/index without a description
            
        event = EventNode(content=content, time=position, participants=participant_ids)
        self.events[event.node_id] = event
        # Add embedding for new node
        self._add_or_update_embedding(event.node_id, description)
        return event.node_id

    def _get_or_create_theme_with_metadata(self, content, position):
        name = content.get('name', '')
        if not name:
            return None # Cannot create/index without a name

        for theme_id, theme in self.themes.items():
            if theme.content.get("name", "").lower() == name.lower():
                theme.increment_instances()
                # Update embedding if name changed (or other relevant content)
                self._add_or_update_embedding(theme_id, name)
                return theme_id
                
        theme = ThemeNode(content=content, time=position)
        self.themes[theme.node_id] = theme
        # Add embedding for new node
        self._add_or_update_embedding(theme.node_id, name) 
        return theme.node_id

    # --- FAISS Helper Methods ---
    def _add_or_update_embedding(self, node_id: str, text_to_embed: str):
        """
        Generates an embedding for the given text and adds/updates it in the FAISS index.
        Assigns a new FAISS ID if the node_id is not already indexed.

        Args:
            node_id: The unique identifier (string) of the node.
            text_to_embed: The text content to be embedded.
        """
        if not self.embedding_model or not self.faiss_index or not text_to_embed:
            # Silently return if embedding is disabled or text is empty
            return

        try:
            # Generate embedding
            embedding = self.embedding_model.encode([text_to_embed], convert_to_numpy=True)
            # FAISS expects a 2D array
            if embedding.ndim == 1:
                embedding = np.expand_dims(embedding, axis=0)

            # Ensure embedding dimension matches index dimension
            if embedding.shape[1] != self.faiss_index.d:
                 print(f"Error: Embedding dimension ({embedding.shape[1]}) does not match FAISS index dimension ({self.faiss_index.d}) for node {node_id}. Skipping.")
                 return

            # Get or assign FAISS ID
            if node_id in self.node_id_to_faiss_id:
                faiss_id = self.node_id_to_faiss_id[node_id]
                # print(f"Updating embedding for node {node_id} (FAISS ID: {faiss_id})")
            else:
                faiss_id = self.next_faiss_id
                self.next_faiss_id += 1
                self.node_id_to_faiss_id[node_id] = faiss_id
                self.faiss_id_to_node_id[faiss_id] = node_id
                # print(f"Adding new embedding for node {node_id} (FAISS ID: {faiss_id})")
            
            # FAISS IDs must be numpy int64
            ids_to_add = np.array([faiss_id], dtype='int64')
            
            # Add/Update vector in FAISS index
            self.faiss_index.add_with_ids(embedding, ids_to_add)

        except Exception as e:
            print(f"Error adding/updating embedding for node {node_id}: {e}")

    def find_similar_nodes(self, query_text: str, k: int = 5) -> List[Tuple[Any, float]]:
        """
        Finds the k most similar nodes in the atlas based on text similarity.

        Args:
            query_text: The text to search for.
            k: The number of similar nodes to return.

        Returns:
            A list of tuples, where each tuple contains the node object 
            and its similarity score (distance). Returns empty list if 
            embedding is disabled or on error.
        """
        if not self.embedding_model or not self.faiss_index:
            print("Embedding model or FAISS index not available for search.")
            return []
        
        if self.faiss_index.ntotal == 0:
            print("FAISS index is empty. No nodes to search.")
            return []

        try:
            # 1. Embed the query
            query_embedding = self.embedding_model.encode([query_text], convert_to_numpy=True)
            if query_embedding.ndim == 1:
                query_embedding = np.expand_dims(query_embedding, axis=0)

            # 2. Search FAISS
            # Returns distances (D) and FAISS IDs (I)
            distances, faiss_ids = self.faiss_index.search(query_embedding, k)
            
            results = []
            if faiss_ids.size > 0:
                # Process results only if any IDs were found
                for i, faiss_id in enumerate(faiss_ids[0]):
                    # A faiss_id of -1 means no neighbor found (if k > ntotal)
                    if faiss_id != -1:
                        # 3. Map FAISS ID back to Node ID
                        node_id = self.faiss_id_to_node_id.get(faiss_id)
                        distance = distances[0][i]
                        
                        if node_id:
                            # 4. Retrieve the actual node object
                            node = self.db.nodes.get(node_id) 
                            if node:
                                # Determine the type and get the specific node object
                                node_type = node.content.get("node_type", "")
                                specific_node = None
                                if node_type == "character":
                                    specific_node = self.characters.get(node_id)
                                elif node_type == "event":
                                    specific_node = self.events.get(node_id)
                                elif node_type == "location":
                                    specific_node = self.locations.get(node_id)
                                elif node_type == "theme":
                                    specific_node = self.themes.get(node_id)
                                
                                if specific_node:
                                     results.append((specific_node, float(distance)))
                                else:
                                    print(f"Warning: Node object for ID {node_id} (FAISS ID {faiss_id}) not found in typed dictionaries.")
                            else:
                                print(f"Warning: Node data for ID {node_id} (FAISS ID {faiss_id}) not found in db.nodes.")
                        else:
                            print(f"Warning: Node ID not found in map for FAISS ID {faiss_id}.")
            
            return results

        except Exception as e:
            print(f"Error during similarity search for query '{query_text}': {e}")
            return [] 
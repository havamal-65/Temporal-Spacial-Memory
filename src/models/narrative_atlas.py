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

from .spatial_temporal_db import SpatialTemporalDB, Node
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

    def __init__(self, name: str = "narrative", storage_path: str = "data", embedding_model_name: str = DEFAULT_EMBEDDING_MODEL, embedding_model: Optional[SentenceTransformer] = None):
        """
        Initialize a new NarrativeAtlas.
        
        Args:
            name: Name of the narrative database
            storage_path: Path to store database files
            embedding_model_name: Name of the SentenceTransformer model to use (if embedding_model is not provided)
            embedding_model: An optional pre-loaded SentenceTransformer model instance.
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

        # 1. Use provided model or load SentenceTransformer Model
        self.embedding_model = embedding_model # Use provided model if available
        self.embedding_dim = None

        if self.embedding_model:
            print(f"Using provided embedding model: {type(self.embedding_model).__name__}")
            try:
                # Attempt to get dimension if it's a standard SentenceTransformer
                if hasattr(self.embedding_model, 'get_sentence_embedding_dimension'):
                    self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                elif hasattr(self.embedding_model, 'dim'): # Handle mock model
                    self.embedding_dim = self.embedding_model.dim
                else:
                    # Attempt a fallback: encode a dummy text
                    print("Attempting to determine embedding dimension by encoding dummy text...")
                    dummy_embedding = self.embedding_model.encode(["test"], convert_to_numpy=True)
                    self.embedding_dim = dummy_embedding.shape[1]
                
                if self.embedding_dim:
                    print(f"Embedding dimension determined: {self.embedding_dim}")
                else:
                     raise ValueError("Could not determine embedding dimension from provided model.")
            except Exception as e:
                print(f"Error determining dimension from provided embedding model: {e}")
                print("FAISS indexing will be disabled.")
                self.embedding_model = None
                self.faiss_index = None
        
        if not self.embedding_model:
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

        # If embedding model failed or dim couldn't be determined, disable FAISS
        if not self.embedding_model or not self.embedding_dim:
            self.faiss_index = None
            self.faiss_id_to_node_id = {}
            self.node_id_to_faiss_id = {}
            self.next_faiss_id = 0
            # Stop FAISS setup
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
                # Using IndexHNSWFlat for scalability
                M = 32 # Number of connections per node (parameter to tune)
                base_index = faiss.IndexHNSWFlat(self.embedding_dim, M, faiss.METRIC_L2)
                self.faiss_index = faiss.IndexIDMap2(base_index)
                # Since index load failed, clear potentially inconsistent maps and reset ID
                self.faiss_id_to_node_id = {}
                self.node_id_to_faiss_id = {}
                self.next_faiss_id = 0
                print("New FAISS index (HNSWFlat) created.")
        else:
            print("No existing FAISS index found. Creating a new index.")
            # Using IndexHNSWFlat for scalability
            M = 32 # Number of connections per node (parameter to tune)
            base_index = faiss.IndexHNSWFlat(self.embedding_dim, M, faiss.METRIC_L2)
            self.faiss_index = faiss.IndexIDMap2(base_index)
            # Ensure maps are empty and ID is reset if index is new
            self.faiss_id_to_node_id = {}
            self.node_id_to_faiss_id = {}
            self.next_faiss_id = 0
            print("New FAISS index (HNSWFlat) created.")
            
        # Optional: Set search parameters for HNSW if needed (can also be done per-query)
        # if isinstance(self.faiss_index.index, faiss.IndexHNSW):
        #    self.faiss_index.index.hnsw.efSearch = 64 
        
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
                # Note: Embedding update logic moved to _get_or_create_character_with_metadata
                # if relevant content changes significantly. Simple get/create only uses name initially.
                return char_id
        
        # Create new character
        content = {"name": name}
        character = CharacterNode(
            content=content,
            time=position,
            distance=0.5,  # Default distance until importance is determined
            angle=len(self.characters) * (360.0 / (len(self.characters) + 1)) if self.characters else 0.0
        )
        
        # Add to database
        self.characters[character.node_id] = character
        # Construct text for embedding (name only for simple creation)
        text_to_embed = f"Character: {name}"
        self._add_or_update_embedding(character.node_id, text_to_embed)
        return character.node_id
    
    def _get_or_create_location(self, name: str, position: float) -> str:
        """Get existing location node or create a new one."""
        # Check if location exists by name
        for loc_id, location in self.locations.items():
            if location.content.get("name", "").lower() == name.lower():
                # Location exists, update scene count
                location.increment_scene_count()
                # Note: Embedding update logic moved to _get_or_create_location_with_metadata
                return loc_id
        
        # Create new location
        content = {"name": name}
        location = LocationNode(
            content=content,
            time=position,
            distance=0.7,  # Default distance
            angle=len(self.locations) * (360.0 / (len(self.locations) + 1)) if self.locations else 0.0
        )
        
        # Add to database
        self.locations[location.node_id] = location
        # Construct text for embedding (name only for simple creation)
        text_to_embed = f"Location: {name}"
        self._add_or_update_embedding(location.node_id, text_to_embed)
        return location.node_id
    
    def _create_event(self, description: str, position: float, participant_ids: List[str]) -> str:
        """Create a new event node."""
        # Create new event
        content = {"description": description, "participants": participant_ids} # Store participant IDs in content
        event = EventNode(
            content=content,
            time=position,
            distance=0.3,  # Default distance for events (closer to center)
            angle=len(self.events) * (360.0 / (len(self.events) + 1)) if self.events else 0.0,
            participants=participant_ids # Also keep direct attribute if needed elsewhere
        )
        
        # Add to database
        self.events[event.node_id] = event
        # Construct text for embedding (description only for simple creation)
        text_to_embed = f"Event: {description}"
        self._add_or_update_embedding(event.node_id, text_to_embed)
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
            
        content["node_type"] = "character" # Explicitly set type in content
        description = content.get('description', '') # Get description if available
        
        # Construct text for embedding (combine name and description)
        text_to_embed_parts = [f"Character: {name}"]
        if description:
            text_to_embed_parts.append(f"Description: {description}")
        text_to_embed = ". ".join(text_to_embed_parts).strip()
            
        for char_id, character in self.characters.items():
            if character.content.get("name", "").lower() == name.lower():
                character.increment_mentions()
                # Update existing node content (simple overwrite/merge needed?)
                # TODO: Implement more sophisticated content merging if needed
                character.content.update(content) 
                # Update embedding as metadata might have changed
                self._add_or_update_embedding(char_id, text_to_embed)
                return char_id
                
        character = CharacterNode(content=content, time=position)
        self.characters[character.node_id] = character
        # Add embedding for new node
        self._add_or_update_embedding(character.node_id, text_to_embed)
        return character.node_id

    def _get_or_create_location_with_metadata(self, content, position):
        name = content.get('name', '')
        if not name:
            return None # Cannot create/index without a name

        content["node_type"] = "location" # Explicitly set type in content
        description = content.get('description', '') # Get description if available

        # Construct text for embedding (combine name and description)
        text_to_embed_parts = [f"Location: {name}"]
        if description:
            text_to_embed_parts.append(f"Description: {description}")
        text_to_embed = ". ".join(text_to_embed_parts).strip()
            
        for loc_id, location in self.locations.items():
            if location.content.get("name", "").lower() == name.lower():
                location.increment_scene_count()
                # Update existing node content
                location.content.update(content)
                # Update embedding as metadata might have changed
                self._add_or_update_embedding(loc_id, text_to_embed)
                return loc_id
                
        location = LocationNode(content=content, time=position)
        self.locations[location.node_id] = location
        # Add embedding for new node
        self._add_or_update_embedding(location.node_id, text_to_embed)
        return location.node_id

    def _create_event_with_metadata(self, content, position, participant_ids):
        description = content.get('description', '')
        if not description:
            return None # Cannot create/index without a description
            
        content["node_type"] = "event" # Explicitly set type in content
        # Ensure participant_ids are in content if not already
        if 'participants' not in content:
            content['participants'] = participant_ids 
            
        # Get participant names (if possible) and location name for embedding
        participant_names = []
        # Use the potentially updated participant list from content
        current_participants = content.get('participants', []) 
        for p_id in current_participants:
            if p_id in self.characters:
                participant_names.append(self.characters[p_id].content.get('name', 'Unknown Character'))
        
        location_name = content.get('location_name', '') # Assuming location name might be in content

        # Construct text for embedding
        text_to_embed_parts = [f"Event: {description}"]
        if participant_names:
            text_to_embed_parts.append(f"Participants: {', '.join(participant_names)}")
        if location_name:
             text_to_embed_parts.append(f"Location: {location_name}")
        text_to_embed = ". ".join(text_to_embed_parts).strip()

        # Use current_participants when creating the EventNode
        event = EventNode(content=content, time=position)
        self.events[event.node_id] = event
        # Add embedding for new node
        self._add_or_update_embedding(event.node_id, text_to_embed)
        return event.node_id

    def _get_or_create_theme_with_metadata(self, content, position):
        name = content.get('name', '')
        if not name:
            return None # Cannot create/index without a name

        content["node_type"] = "theme" # Explicitly set type in content
        keywords = content.get('keywords', []) # Get keywords if available

        # Construct text for embedding
        text_to_embed_parts = [f"Theme: {name}"]
        if keywords:
            # Ensure keywords are strings before joining
            keywords_str = [str(kw) for kw in keywords if kw] 
            if keywords_str:
                text_to_embed_parts.append(f"Keywords: {', '.join(keywords_str)}")
        text_to_embed = ". ".join(text_to_embed_parts).strip()

        for theme_id, theme in self.themes.items():
            if theme.content.get("name", "").lower() == name.lower():
                theme.increment_instances()
                 # Update existing node content
                theme.content.update(content)
                # Update embedding if relevant content changed
                self._add_or_update_embedding(theme_id, text_to_embed)
                return theme_id
                
        theme = ThemeNode(content=content, time=position)
        self.themes[theme.node_id] = theme
        # Add embedding for new node
        self._add_or_update_embedding(theme.node_id, text_to_embed) 
        return theme.node_id

    # --- Node Deletion ---
    def delete_node(self, node_id: str) -> bool:
        """
        Deletes a node from the atlas, including its FAISS embedding and internal references.
        NOTE: With HNSW index, the vector is NOT removed from the underlying FAISS index, 
              only from the lookup maps and DB.

        Args:
            node_id: The unique identifier of the node to delete.

        Returns:
            True if the node was successfully deleted, False otherwise.
        """
        print(f"Attempting to delete node: {node_id}")
        
        # 1. Delete from the underlying database
        if not self.db.delete_node(node_id):
            print(f"Node {node_id} not found in SpatialTemporalDB.")
            return False
        
        print(f"Node {node_id} deleted from SpatialTemporalDB.")

        faiss_id_to_remove = None
        # 2. Get FAISS ID for map cleanup (DO NOT attempt removal from HNSW index)
        if self.faiss_index is not None and self.embedding_model is not None:
            if node_id in self.node_id_to_faiss_id:
                faiss_id_to_remove = self.node_id_to_faiss_id[node_id]
                print(f"Node {node_id} has FAISS ID {faiss_id_to_remove}. It will be removed from maps, but not the HNSW index itself.")
            else:
                print(f"Node {node_id} not found in FAISS ID map. Skipping FAISS map cleanup.")
        else:
            print(f"FAISS index or embedding model not available. Skipping FAISS map cleanup for node {node_id}.")

        # 3. Remove from FAISS ID maps (crucial step)
        if faiss_id_to_remove is not None:
            if faiss_id_to_remove in self.faiss_id_to_node_id:
                del self.faiss_id_to_node_id[faiss_id_to_remove]
                print(f"Removed FAISS ID {faiss_id_to_remove} from faiss_id_to_node_id map.")
                
        if node_id in self.node_id_to_faiss_id:
            del self.node_id_to_faiss_id[node_id]
            print(f"Removed node ID {node_id} from node_id_to_faiss_id map.")
        
        # 4. Remove from typed dictionaries
        deleted_from_typed_dict = False
        if node_id in self.characters:
            del self.characters[node_id]
            deleted_from_typed_dict = True
            print(f"Node {node_id} removed from self.characters.")
        elif node_id in self.events:
            del self.events[node_id]
            deleted_from_typed_dict = True
            print(f"Node {node_id} removed from self.events.")
        elif node_id in self.locations:
            del self.locations[node_id]
            deleted_from_typed_dict = True
            print(f"Node {node_id} removed from self.locations.")
        elif node_id in self.themes:
            del self.themes[node_id]
            deleted_from_typed_dict = True
            print(f"Node {node_id} removed from self.themes.")

        if not deleted_from_typed_dict:
             print(f"Warning: Node {node_id} was deleted from DB but not found in any typed dictionary.")

        # TODO: Consider decrementing metrics? Maybe update on save/load instead.
        print(f"Deletion process completed for node: {node_id}")
        return True
        
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
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text], convert_to_numpy=True)
            if query_embedding.ndim == 1:
                query_embedding = np.expand_dims(query_embedding, axis=0)

            # Ensure query dimension matches index dimension
            if query_embedding.shape[1] != self.faiss_index.d:
                print(f"Error: Query embedding dimension ({query_embedding.shape[1]}) does not match FAISS index dimension ({self.faiss_index.d}).")
                return []

            # Perform search
            distances, faiss_ids = self.faiss_index.search(query_embedding, k)
            
            # Map results back to nodes
            results = []
            for i in range(len(faiss_ids[0])):
                faiss_id = faiss_ids[0][i]
                distance = distances[0][i]
                if faiss_id != -1: # FAISS returns -1 for no result in that slot
                    node_id = self.faiss_id_to_node_id.get(int(faiss_id))
                    if node_id:
                        node = self.db.get_node(node_id)
                        if node:
                            results.append((node, float(distance)))
                    else:
                        print(f"Warning: FAISS ID {faiss_id} found during search but not in faiss_id_to_node_id map.")

            return results

        except Exception as e:
            print(f"Error during FAISS search for '{query_text}': {e}")
            return []

    # --- Basic RAG Functionality ---
    def answer_query_with_context(self, user_query: str, k: int = 3, llm_client: Optional[Any] = None) -> str:
        """
        Retrieves relevant context using semantic search and constructs a prompt
        for an LLM to answer a user query.

        Args:
            user_query: The user's question.
            k: The number of similar nodes to retrieve for context.
            llm_client: (Optional) An LLM client object/function (placeholder).

        Returns:
            A formatted prompt string ready for an LLM, or an error message.
        """
        print(f"Received query: '{user_query}'. Finding {k} relevant nodes...")
        retrieved_nodes = self.find_similar_nodes(query_text=user_query, k=k)

        if not retrieved_nodes:
            print("No relevant context found.")
            return "I could not find any relevant context in the narrative atlas to answer your query."

        print(f"Found {len(retrieved_nodes)} nodes.")
        formatted_context = ""
        for i, (base_node_tuple) in enumerate(retrieved_nodes):
            base_node, score = base_node_tuple # Unpack the tuple
            node_id = base_node.node_id
            
            # Determine type from the base node content first
            node_type = base_node.content.get("node_type", "Unknown")
            
            # Attempt to get the richer typed node from the corresponding atlas dictionary
            typed_node = None
            if node_type == "character" and node_id in self.characters:
                typed_node = self.characters[node_id]
            elif node_type == "event" and node_id in self.events:
                typed_node = self.events[node_id]
            elif node_type == "location" and node_id in self.locations:
                typed_node = self.locations[node_id]
            elif node_type == "theme" and node_id in self.themes:
                typed_node = self.themes[node_id]
            
            # Use the typed node if found, otherwise fallback to the base node from search
            node_to_format = typed_node if typed_node else base_node
            
            # Now use node_to_format.content for details
            node_name = node_to_format.content.get("name", node_to_format.content.get("description", f"Node {node_to_format.node_id}"))
            description = node_to_format.content.get("description", "")
            
            context_piece = f"Context {i+1} (Type: {node_type}, Name: {node_name}, Score: {score:.4f}):\\n"
            if description:
                 context_piece += f"  Description: {description}\\n"
                 
            # Add type-specific details using node_to_format.content
            if isinstance(node_to_format, CharacterNode) and "attributes" in node_to_format.content:
                 context_piece += f"  Attributes: {node_to_format.content['attributes']}\\n"
            elif isinstance(node_to_format, EventNode) and "participants" in node_to_format.content:
                 # print(f"DEBUG [RAG]: Found EventNode. Type: {type(node_to_format)}") # Debug
                 # print(f"DEBUG [RAG]: Event Node Content: {node_to_format.content}") # Debug
                 participant_ids = node_to_format.content["participants"]
                 # print(f"DEBUG [RAG]: Participant IDs from content: {participant_ids}") # Debug
                 participant_names = []
                 for pid in participant_ids:
                     p_node = self.db.get_node(pid) # Still need DB access for participant names
                     if p_node:
                         p_name = p_node.content.get("name", pid)
                         participant_names.append(p_name)
                         # print(f"DEBUG [RAG]: Looked up pid={pid}. Found node. Name='{p_name}'") # Debug
                     # else:
                         # print(f"DEBUG [RAG]: Looked up pid={pid}. Node NOT FOUND in self.db.nodes.") # Debug
                 
                 # print(f"DEBUG [RAG]: Final participant_names list: {participant_names}") # Debug
                 if participant_names:
                     context_piece += f"  Participants: {', '.join(participant_names)}\\n"
                 
            formatted_context += context_piece + "---\\n"

        prompt = f"""
Based ONLY on the following context:
--- CONTEXT START ---
{formatted_context.strip()}
--- CONTEXT END ---

Answer the question: {user_query}
Answer: """

        print("\nConstructed Prompt:\n", prompt)

        # --- LLM Call Placeholder ---
        # if llm_client:
        #     try:
        #         # response = llm_client.generate(prompt) 
        #         # return response 
        #         print("\n(Placeholder: LLM call would happen here)")
        #         return prompt # Return prompt for now
        #     except Exception as e:
        #         print(f"Error calling LLM: {e}")
        #         return f"Error generating response: {e}"
        # else:
        #     print("\n(Placeholder: No LLM client provided)")
        #     return prompt # Return prompt if no LLM client
        # --- End Placeholder ---
            
        # For now, just return the constructed prompt
        return prompt

# Example Usage (can be run separately or in tests)
if __name__ == '__main__':
    # This block is for basic demonstration/testing if the script is run directly
    # Ensure you have a compatible embedding model and FAISS installed
    print("Running basic NarrativeAtlas RAG example...")
    
    # Create a dummy embedding model for testing if needed
    class DummyEmbedder:
        def __init__(self, dim=384):
            self.dim = dim
        def encode(self, texts, convert_to_numpy=True):
            # Generate random embeddings of the correct dimension
            embeddings = np.random.rand(len(texts), self.dim).astype('float32')
            return embeddings if convert_to_numpy else embeddings.tolist()
        def get_sentence_embedding_dimension(self):
             return self.dim

    temp_storage = "./temp_rag_test_data"
    # Use the dummy embedder if a real one causes issues in simple testing
    # atlas = NarrativeAtlas(storage_path=temp_storage, embedding_model=DummyEmbedder()) 
    try:
        atlas = NarrativeAtlas(storage_path=temp_storage) # Tries default 'all-MiniLM-L6-v2'
    except Exception as e:
         print(f"Could not initialize Atlas with default model ({e}), trying dummy.")
         atlas = NarrativeAtlas(storage_path=temp_storage, embedding_model=DummyEmbedder())

    if atlas.embedding_model: # Proceed only if embedding model is loaded
        print("Adding sample nodes...")
        char_id = atlas._get_or_create_character("Bilbo Baggins", 1.0, {"description": "A hobbit who enjoys comfort but goes on an adventure."})
        event_id = atlas._create_event("Unexpected Party", 2.0, [char_id], {"description": "Gandalf and dwarves arrive at Bilbo's home."})
        loc_id = atlas._get_or_create_location("Bag End", 0.5, {"description": "A comfortable hobbit-hole under The Hill."})
        
        atlas.save() # Save including FAISS index

        print("\n--- Testing RAG Function ---")
        query = "Who is Bilbo?"
        generated_prompt = atlas.answer_query_with_context(query)
        # print(f"\nQuery: {query}\nGenerated Prompt:\n{generated_prompt}")

        query2 = "What happened at Bag End?"
        generated_prompt2 = atlas.answer_query_with_context(query2)
        # print(f"\nQuery: {query2}\nGenerated Prompt:\n{generated_prompt2}")

        print("\n--- Cleanup ---")
        # Clean up the temporary directory
        import shutil
        if os.path.exists(temp_storage):
            shutil.rmtree(temp_storage)
            print(f"Removed temporary directory: {temp_storage}")
    else:
        print("Skipping RAG example as embedding model could not be loaded.") 
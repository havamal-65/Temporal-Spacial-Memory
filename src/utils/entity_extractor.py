"""
Entity Extractor Utility

This module provides utilities for extracting entities, events, and locations from text.
It uses spaCy for named entity recognition and custom rules for event detection.
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from datetime import datetime
import spacy
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EntityExtractor')


class EntityExtractor:
    """
    Class for extracting entities from text content.
    """
    
    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """
        Initialize the entity extractor.
        
        Args:
            spacy_model: Name of the spaCy model to load
        """
        try:
            self.nlp = spacy.load(spacy_model)
            logger.info(f"Loaded spaCy model: {spacy_model}")
        except IOError:
            logger.warning(f"Could not load spaCy model: {spacy_model}. Downloading...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "spacy", "download", spacy_model])
            self.nlp = spacy.load(spacy_model)
            logger.info(f"Downloaded and loaded spaCy model: {spacy_model}")
        
        # Event detection patterns
        self.event_verbs = {
            'happened', 'occurred', 'took place', 'began', 'started', 'ended',
            'celebrated', 'announced', 'launched', 'released', 'published',
            'attacked', 'defended', 'won', 'lost', 'defeated', 'elected',
            'married', 'divorced', 'born', 'died', 'killed', 'injured',
            'signed', 'agreed', 'rejected', 'approved', 'met', 'visited'
        }
        
        # Regular expression for date detection
        self.date_pattern = re.compile(
            r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
            r'Dec(?:ember)?)[.,]?\s+\d{1,2}(?:[,.]?\s+\d{2,4})?\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b'
        )
    
    def extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities, events, and locations from text.
        
        Args:
            text: The text content to analyze
            
        Returns:
            Dictionary with keys 'entities', 'events', and 'locations',
            each containing a list of detected items with their properties
        """
        if not text:
            logger.warning("Empty text provided to entity extractor")
            return {
                'entities': [],
                'events': [],
                'locations': []
            }
        
        # Process the text with spaCy
        doc = self.nlp(text)
        
        # Extract different types of entities
        entities = self._extract_people_and_orgs(doc)
        locations = self._extract_locations(doc)
        events = self._extract_events(doc)
        
        # Add temporal information to events
        events = self._enrich_events_with_time(events, doc)
        
        # Add co-occurrence relationships
        self._add_entity_relationships(entities, events, locations, text)
        
        return {
            'entities': entities,
            'events': events,
            'locations': locations
        }
    
    def _extract_people_and_orgs(self, doc) -> List[Dict[str, Any]]:
        """
        Extract people and organizations from the spaCy document.
        
        Args:
            doc: spaCy Doc object
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ in ('PERSON', 'ORG', 'NORP', 'FAC', 'GPE') and ent.text.strip():
                # Skip if already seen (case-insensitive)
                if ent.text.lower() in seen:
                    continue
                
                entity = {
                    'name': ent.text,
                    'type': self._map_entity_type(ent.label_),
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'mentions': 1,
                    'relationships': []
                }
                
                entities.append(entity)
                seen.add(ent.text.lower())
        
        return entities
    
    def _extract_locations(self, doc) -> List[Dict[str, Any]]:
        """
        Extract locations from the spaCy document.
        
        Args:
            doc: spaCy Doc object
            
        Returns:
            List of location dictionaries
        """
        locations = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ in ('GPE', 'LOC', 'FAC') and ent.text.strip():
                # Skip if already seen (case-insensitive)
                if ent.text.lower() in seen:
                    continue
                
                location = {
                    'name': ent.text,
                    'type': self._map_location_type(ent.label_),
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'mentions': 1,
                    'relationships': []
                }
                
                locations.append(location)
                seen.add(ent.text.lower())
        
        return locations
    
    def _extract_events(self, doc) -> List[Dict[str, Any]]:
        """
        Extract events from the spaCy document.
        
        Args:
            doc: spaCy Doc object
            
        Returns:
            List of event dictionaries
        """
        events = []
        seen = set()
        
        # Look for sentences with event verbs
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            # Check if any event verbs are in the sentence
            if any(verb in sent_text for verb in self.event_verbs):
                event_name = sent.text[:50] + ('...' if len(sent.text) > 50 else '')
                
                # Skip if already seen (based on the first 50 chars, case-insensitive)
                if event_name.lower() in seen:
                    continue
                
                event = {
                    'name': event_name,
                    'description': sent.text,
                    'start': sent.start_char,
                    'end': sent.end_char,
                    'participants': [],
                    'location': None,
                    'time': None
                }
                
                events.append(event)
                seen.add(event_name.lower())
        
        return events
    
    def _enrich_events_with_time(self, events: List[Dict[str, Any]], doc) -> List[Dict[str, Any]]:
        """
        Add temporal information to events.
        
        Args:
            events: List of extracted events
            doc: spaCy Doc object
            
        Returns:
            Enriched events list
        """
        # Extract all dates from the document
        dates = []
        for match in self.date_pattern.finditer(doc.text):
            dates.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Try to associate dates with events based on proximity
        for event in events:
            closest_date = None
            min_distance = float('inf')
            
            for date in dates:
                # Calculate the distance between the event and date
                if date['start'] <= event['end'] and date['end'] >= event['start']:
                    # Date is inside the event, distance is 0
                    distance = 0
                elif date['start'] > event['end']:
                    distance = date['start'] - event['end']
                else:
                    distance = event['start'] - date['end']
                
                # Update closest date if this one is closer
                if distance < min_distance:
                    min_distance = distance
                    closest_date = date
            
            # Associate the closest date if it's within 200 characters
            if closest_date and min_distance < 200:
                event['time'] = closest_date['text']
        
        return events
    
    def _add_entity_relationships(self, 
                               entities: List[Dict[str, Any]], 
                               events: List[Dict[str, Any]], 
                               locations: List[Dict[str, Any]], 
                               text: str) -> None:
        """
        Add relationships between entities, events, and locations based on co-occurrence.
        
        Args:
            entities: List of extracted entities
            events: List of extracted events
            locations: List of extracted locations
            text: The original text
        """
        # Create a map of all items by their text spans
        spans = []
        
        for entity in entities:
            spans.append(('entity', entity, entity['start'], entity['end']))
        
        for location in locations:
            spans.append(('location', location, location['start'], location['end']))
        
        for event in events:
            spans.append(('event', event, event['start'], event['end']))
        
        # Sort by start position
        spans.sort(key=lambda x: x[2])
        
        # For each event, find entities and locations in proximity
        for event_type, event, event_start, event_end in spans:
            if event_type != 'event':
                continue
            
            # Look for entities and locations in the same paragraph
            paragraph_start = max(0, text.rfind('\n\n', 0, event_start) + 2)
            paragraph_end = text.find('\n\n', event_end)
            if paragraph_end == -1:
                paragraph_end = len(text)
            
            # Find items in the same paragraph
            for item_type, item, item_start, item_end in spans:
                if item is event:  # Skip the event itself
                    continue
                    
                # Check if the item is in proximity to the event
                if (item_start >= paragraph_start and item_end <= paragraph_end):
                    if item_type == 'entity':
                        # Add entity as participant in the event
                        event['participants'].append(item['name'])
                        
                        # Add event to entity's relationships
                        item['relationships'].append({
                            'type': 'participated_in',
                            'target': event['name']
                        })
                    
                    elif item_type == 'location' and event['location'] is None:
                        # Set location for the event
                        event['location'] = item['name']
                        
                        # Add event to location's relationships
                        item['relationships'].append({
                            'type': 'hosted',
                            'target': event['name']
                        })
    
    def _map_entity_type(self, spacy_type: str) -> str:
        """
        Map spaCy entity types to simplified types.
        
        Args:
            spacy_type: Entity type from spaCy
            
        Returns:
            Simplified entity type
        """
        mapping = {
            'PERSON': 'person',
            'ORG': 'organization',
            'NORP': 'group',  # Nationalities, religious groups
            'FAC': 'facility',
            'GPE': 'administrative',  # Countries, cities, states
        }
        
        return mapping.get(spacy_type, 'unknown')
    
    def _map_location_type(self, spacy_type: str) -> str:
        """
        Map spaCy location types to simplified types.
        
        Args:
            spacy_type: Location type from spaCy
            
        Returns:
            Simplified location type
        """
        mapping = {
            'GPE': 'administrative',  # Countries, cities, states
            'LOC': 'geographical',    # Non-GPE locations, mountain ranges, water bodies
            'FAC': 'facility'         # Buildings, airports, highways, bridges
        }
        
        return mapping.get(spacy_type, 'unknown') 
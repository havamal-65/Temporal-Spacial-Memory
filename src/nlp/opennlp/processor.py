"""
OpenNLP processor for narrative text analysis.
"""

import os
import json
import logging
import urllib.request
from typing import Dict, List, Any, Optional, Tuple

# Import for JPype integration
import jpype
import jpype.imports
from jpype.types import *

logger = logging.getLogger(__name__)

class OpenNLPProcessor:
    """
    Processor for narrative text using Apache OpenNLP.
    
    This class provides integration with Apache OpenNLP for improved
    natural language processing capabilities in the Narrative Atlas framework.
    It uses JPype to interface with the Java-based OpenNLP library.
    
    Attributes:
        models_dir: Directory where OpenNLP models are stored
        initialized: Whether the JVM has been initialized
        tokenizer: OpenNLP tokenizer model
        sentence_detector: OpenNLP sentence detector model
        pos_tagger: OpenNLP POS tagger model
        name_finder: OpenNLP named entity recognition model
        parser: OpenNLP parser model
    """
    
    def __init__(self, models_dir: str = "models/opennlp"):
        """
        Initialize the OpenNLP processor.
        
        Args:
            models_dir: Directory where OpenNLP models are stored
        """
        self.models_dir = models_dir
        self.initialized = False
        self.tokenizer = None
        self.sentence_detector = None
        self.pos_tagger = None
        self.name_finder = None
        self.parser = None
        
        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)
        
        logger.info(f"OpenNLP processor initialized with models directory: {models_dir}")
    
    def initialize(self) -> bool:
        """
        Initialize the JVM and load OpenNLP models.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.initialized:
            logger.info("OpenNLP processor already initialized")
            return True
        
        try:
            # Create lib directory if it doesn't exist
            lib_dir = os.path.abspath("lib")
            os.makedirs(lib_dir, exist_ok=True)
            
            # Define OpenNLP jar path
            opennlp_jar = os.path.join(lib_dir, "opennlp-tools-2.2.0.jar")
            
            # Check if the jar exists, if not download it
            if not os.path.exists(opennlp_jar):
                logger.info("OpenNLP JAR not found. Downloading...")
                url = "https://dlcdn.apache.org/opennlp/opennlp-2.2.0/apache-opennlp-2.2.0-bin.zip"
                self._download_and_extract_opennlp(url, lib_dir)
            
            # Set up classpath
            classpath = opennlp_jar
            
            # Start JVM if not already started
            if not jpype.isJVMStarted():
                logger.info(f"Starting JVM with classpath: {classpath}")
                jpype.startJVM(jpype.getDefaultJVMPath(), f"-Djava.class.path={classpath}")
            
            # Import necessary OpenNLP classes
            from java.io import FileInputStream
            from opennlp.tools.tokenize import TokenizerME, TokenizerModel
            from opennlp.tools.sentdetect import SentenceDetectorME, SentenceModel
            from opennlp.tools.namefind import NameFinderME, TokenNameFinderModel
            from opennlp.tools.postag import POSTaggerME, POSModel
            from opennlp.tools.parser import Parse, ParserFactory, ParserModel
            
            # Download models if they don't exist
            self.download_models()
            
            # Load tokenizer model
            tokenizer_model_path = os.path.join(self.models_dir, "en-token.bin")
            if os.path.exists(tokenizer_model_path):
                logger.info(f"Loading tokenizer model from {tokenizer_model_path}")
                model_in = FileInputStream(tokenizer_model_path)
                model = TokenizerModel(model_in)
                self.tokenizer = TokenizerME(model)
                model_in.close()
            else:
                logger.warning(f"Tokenizer model not found at {tokenizer_model_path}")
            
            # Load sentence detector model
            sentence_model_path = os.path.join(self.models_dir, "en-sent.bin")
            if os.path.exists(sentence_model_path):
                logger.info(f"Loading sentence detector model from {sentence_model_path}")
                model_in = FileInputStream(sentence_model_path)
                model = SentenceModel(model_in)
                self.sentence_detector = SentenceDetectorME(model)
                model_in.close()
            else:
                logger.warning(f"Sentence model not found at {sentence_model_path}")
            
            # Load person name finder model
            name_model_path = os.path.join(self.models_dir, "en-ner-person.bin")
            if os.path.exists(name_model_path):
                logger.info(f"Loading person NER model from {name_model_path}")
                model_in = FileInputStream(name_model_path)
                model = TokenNameFinderModel(model_in)
                self.name_finder = NameFinderME(model)
                model_in.close()
            else:
                logger.warning(f"Person NER model not found at {name_model_path}")
            
            # Load POS tagger model
            pos_model_path = os.path.join(self.models_dir, "en-pos-maxent.bin")
            if os.path.exists(pos_model_path):
                logger.info(f"Loading POS tagger model from {pos_model_path}")
                model_in = FileInputStream(pos_model_path)
                model = POSModel(model_in)
                self.pos_tagger = POSTaggerME(model)
                model_in.close()
            else:
                logger.warning(f"POS tagger model not found at {pos_model_path}")
            
            self.initialized = True
            logger.info("OpenNLP processor initialization successful")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing OpenNLP processor: {str(e)}")
            return False
    
    def _download_and_extract_opennlp(self, url: str, target_dir: str) -> bool:
        """
        Download and extract Apache OpenNLP binaries.
        
        Args:
            url: URL to download OpenNLP from
            target_dir: Directory to extract to
            
        Returns:
            True if successful, False otherwise
        """
        import tempfile
        import zipfile
        import shutil
        
        try:
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                logger.info(f"Downloading OpenNLP from {url} to {temp_file.name}")
                urllib.request.urlretrieve(url, temp_file.name)
                
                # Extract zip file
                with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                    # Extract to temporary directory
                    temp_dir = tempfile.mkdtemp()
                    zip_ref.extractall(temp_dir)
                    
                    # Find the jar file in the extracted directory
                    jar_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('opennlp-tools-2.2.0.jar'):
                                jar_path = os.path.join(root, file)
                                break
                    
                    if jar_path:
                        # Copy jar to target directory
                        dest_path = os.path.join(target_dir, "opennlp-tools-2.2.0.jar")
                        shutil.copy(jar_path, dest_path)
                        logger.info(f"Extracted OpenNLP jar to {dest_path}")
                    else:
                        logger.error("Could not find opennlp-tools jar in the downloaded package")
                        return False
                    
                    # Clean up
                    shutil.rmtree(temp_dir)
            
            # Remove temporary file
            os.unlink(temp_file.name)
            return True
            
        except Exception as e:
            logger.error(f"Error downloading and extracting OpenNLP: {str(e)}")
            return False
    
    def download_models(self) -> bool:
        """
        Download required OpenNLP models if they don't exist.
        
        Returns:
            True if all models downloaded successfully, False otherwise
        """
        # Define model URLs - using Apache OpenNLP 1.9.3 models for compatibility
        model_urls = {
            "en-token.bin": "https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-tokens-1.0-1.9.3.bin",
            "en-sent.bin": "https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-sentence-1.0-1.9.3.bin",
            "en-pos-maxent.bin": "https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-pos-1.0-1.9.3.bin",
            "en-ner-person.bin": "https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin",
            "en-ner-location.bin": "https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin",
            "en-ner-organization.bin": "https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin",
            "en-ner-date.bin": "https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin",
            "en-ner-time.bin": "https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin"
        }
        
        success = True
        for model_name, url in model_urls.items():
            model_path = os.path.join(self.models_dir, model_name)
            
            if not os.path.exists(model_path):
                try:
                    logger.info(f"Downloading model {model_name} from {url}")
                    # Create parent directories if they don't exist
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    # Download the model
                    urllib.request.urlretrieve(url, model_path)
                    logger.info(f"Successfully downloaded {model_name} to {model_path}")
                except Exception as e:
                    logger.error(f"Failed to download {model_name}: {str(e)}")
                    success = False
        
        return success
    
    def extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            Dictionary with entity types as keys and lists of entities as values
        """
        if not self.initialized and not self.initialize():
            logger.error("OpenNLP processor not initialized")
            return {
                "characters": [],
                "locations": [],
                "organizations": [],
                "dates": [],
                "times": []
            }
        
        try:
            # Initialize result structure
            entities = {
                "characters": [],
                "locations": [],
                "organizations": [],
                "dates": [],
                "times": []
            }
            
            # Process text
            if not text.strip():
                return entities
                
            # Split text into sentences
            sentences = self.sentence_detector.sentDetect(text)
            logger.info(f"Split text into {len(sentences)} sentences")
            
            # Track entity counts and first occurrences
            entity_counts = {}
            entity_first_occurrence = {}
            total_sentences = len(sentences)
            
            # Process each sentence
            for i, sentence in enumerate(sentences):
                # Skip empty sentences
                if not sentence.strip():
                    continue
                
                # Calculate progress position (0.0 to 1.0)
                position = i / total_sentences if total_sentences > 0 else 0.0
                
                # Tokenize the sentence
                tokens = self.tokenizer.tokenize(sentence)
                token_array = jpype.JArray(jpype.JString)(tokens)
                
                # Find person names
                if self.name_finder:
                    spans = self.name_finder.find(token_array)
                    
                    # Convert spans to entity information
                    for span in spans:
                        start = span.getStart()
                        end = span.getEnd()
                        prob = span.getProb()
                        
                        # Extract the entity text from tokens
                        entity_text = " ".join(tokens[start:end])
                        
                        # Skip very short entities or those with low probability
                        if len(entity_text) < 2 or prob < 0.5:
                            continue
                            
                        # Normalize entity name (capitalize)
                        entity_text = entity_text.strip().title()
                        
                        # Update entity count
                        if entity_text not in entity_counts:
                            entity_counts[entity_text] = 0
                            entity_first_occurrence[entity_text] = position
                        entity_counts[entity_text] += 1
                        
                        # Categorize entity (for now, all to characters)
                        entity_type = "characters"
                        entities[entity_type] = [e for e in entities[entity_type] if e["name"] != entity_text]
                        entities[entity_type].append({
                            "name": entity_text,
                            "mentions": entity_counts[entity_text],
                            "first_occurrence": entity_first_occurrence[entity_text]
                        })
            
            # Sort entities by mention count
            for entity_type in entities:
                entities[entity_type] = sorted(
                    entities[entity_type], 
                    key=lambda e: e["mentions"], 
                    reverse=True
                )
            
            # Filter out common false positives and very low mention entities
            entities = self._filter_entities(entities)
            
            logger.info(f"Extracted entities: {sum(len(entities[t]) for t in entities)} total")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {
                "characters": [],
                "locations": [],
                "organizations": [],
                "dates": [],
                "times": []
            }
    
    def _filter_entities(self, entities: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter entities to remove common false positives and low-count mentions.
        
        Args:
            entities: Dictionary of extracted entities
            
        Returns:
            Filtered entities dictionary
        """
        # Common words that might be mistakenly identified as entities
        common_words = [
            "the", "and", "but", "he", "she", "it", "they", "there", "here", 
            "in", "of", "to", "a", "an", "was", "had", "have", "would", "could",
            "should", "you", "that", "this", "not", "for", "his", "her", "their",
            "then", "than", "when", "where", "why", "how", "what", "who", "whom",
            "whose", "which", "one", "two", "three", "i", "me", "my", "mine",
            "we", "us", "our", "ours"
        ]
        
        # Filter out common words and entities with very few mentions
        filtered = {}
        for entity_type, entity_list in entities.items():
            filtered[entity_type] = [
                entity for entity in entity_list
                if (
                    entity["name"].lower() not in common_words
                    and len(entity["name"]) > 1
                    and entity["mentions"] >= 3
                )
            ]
            
        return filtered
    
    def analyze_relationships(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze relationships between entities in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of relationships between entities
        """
        if not self.initialized and not self.initialize():
            logger.error("OpenNLP processor not initialized")
            return []
        
        try:
            # First, extract entities to work with
            entities_dict = self.extract_entities(text)
            
            # Extract character names
            character_names = [char["name"] for char in entities_dict.get("characters", [])]
            location_names = [loc["name"] for loc in entities_dict.get("locations", [])]
            
            # Skip if no entities found
            if not character_names:
                return []
                
            # Split text into sentences
            sentences = self.sentence_detector.sentDetect(text)
            
            # Initialize relationship tracking
            relationships = []
            relationship_counts = {}
            
            # Maps to track the first occurrence of each relationship
            first_occurrences = {}
            
            # Process each sentence
            for i, sentence in enumerate(sentences):
                # Skip empty sentences
                if not sentence.strip():
                    continue
                    
                # Calculate position in text (0.0 to 1.0)
                position = i / len(sentences) if sentences else 0.0
                
                # Find entities mentioned in this sentence
                mentioned_characters = []
                mentioned_locations = []
                
                for character in character_names:
                    if character.lower() in sentence.lower():
                        mentioned_characters.append(character)
                        
                for location in location_names:
                    if location.lower() in sentence.lower():
                        mentioned_locations.append(location)
                
                # Create character-character relationships (co-occurrence)
                for i in range(len(mentioned_characters)):
                    for j in range(i+1, len(mentioned_characters)):
                        source = mentioned_characters[i]
                        target = mentioned_characters[j]
                        
                        relationship_key = f"{source}|{target}"
                        relationship_key_reverse = f"{target}|{source}"
                        
                        # Use the alphabetically first ordering for consistent key
                        if relationship_key > relationship_key_reverse:
                            relationship_key = relationship_key_reverse
                            source, target = target, source
                        
                        # Track relationship
                        if relationship_key not in relationship_counts:
                            relationship_counts[relationship_key] = 0
                            first_occurrences[relationship_key] = position
                            
                        relationship_counts[relationship_key] += 1
                        
                # Create character-location relationships
                for character in mentioned_characters:
                    for location in mentioned_locations:
                        relationship_key = f"{character}|{location}"
                        
                        # Track relationship
                        if relationship_key not in relationship_counts:
                            relationship_counts[relationship_key] = 0
                            first_occurrences[relationship_key] = position
                            
                        relationship_counts[relationship_key] += 1
            
            # Convert tracked relationships to output format
            for relationship_key, count in relationship_counts.items():
                # Only include significant relationships (mentioned multiple times)
                if count < 2:
                    continue
                    
                # Parse relationship key
                source, target = relationship_key.split('|')
                
                # Determine relationship type
                rel_type = "appears_with"
                if target in location_names:
                    rel_type = "appears_at"
                
                # Calculate relationship strength based on co-occurrence frequency
                strength = min(1.0, count / 10.0)  # Cap at 1.0
                
                # Add to relationships list
                relationships.append({
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "strength": strength,
                    "first_occurrence": first_occurrences.get(relationship_key, 0.0)
                })
            
            # Sort relationships by strength
            relationships = sorted(relationships, key=lambda r: r["strength"], reverse=True)
            
            logger.info(f"Analyzed {len(relationships)} relationships")
            return relationships
            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {str(e)}")
            return []
    
    def extract_events(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract events from text.
        
        Args:
            text: Input text to extract events from
            
        Returns:
            List of events with associated information
        """
        if not self.initialized and not self.initialize():
            logger.error("OpenNLP processor not initialized")
            return []
        
        try:
            # First, extract entities to work with
            entities_dict = self.extract_entities(text)
            relationships = self.analyze_relationships(text)
            
            # Extract character names
            character_names = [char["name"] for char in entities_dict.get("characters", [])]
            location_names = [loc["name"] for loc in entities_dict.get("locations", [])]
            
            # Skip if no entities found
            if not character_names:
                return []
                
            # Split text into sentences
            sentences = self.sentence_detector.sentDetect(text)
            
            # Analyze sentences to identify potential events
            events = []
            
            # Event detection works by identifying sentences with:
            # 1. Multiple entity mentions (characters and/or locations)
            # 2. Action verbs (indicated by POS tags)
            
            for i, sentence in enumerate(sentences):
                # Skip short or empty sentences
                if len(sentence.strip()) < 10:
                    continue
                    
                # Calculate position in text (0.0 to 1.0)
                position = i / len(sentences) if sentences else 0.0
                
                # Tokenize the sentence
                tokens = self.tokenizer.tokenize(sentence)
                if not tokens:
                    continue
                
                # Skip sentences that are too short
                if len(tokens) < 5:
                    continue
                    
                # Get POS tags for tokens
                token_array = jpype.JArray(jpype.JString)(tokens)
                pos_tags = self.pos_tagger.tag(token_array) if self.pos_tagger else []
                
                # Find entities mentioned in this sentence
                mentioned_characters = []
                mentioned_location = None
                
                for character in character_names:
                    if character.lower() in sentence.lower():
                        mentioned_characters.append(character)
                        
                for location in location_names:
                    if location.lower() in sentence.lower():
                        mentioned_location = location
                        break  # Only use the first location found
                
                # Skip if not enough entities
                if len(mentioned_characters) < 1:
                    continue
                
                # Look for action verbs (VB*)
                has_action_verb = False
                action_verbs = []
                
                for j, tag in enumerate(pos_tags):
                    if tag.startswith("VB") and tag != "VBZ" and j < len(tokens):
                        has_action_verb = True
                        action_verbs.append(tokens[j])
                
                if not has_action_verb:
                    continue
                
                # This sentence might contain an event
                # Create a concise description using the first action verb and entities
                if action_verbs and mentioned_characters:
                    # Use the first 60 characters of the sentence as the description
                    # This is a simplified approach - in a full implementation, 
                    # we would parse the sentence structure to extract a more meaningful event
                    description = f"{sentence[:60]}..." if len(sentence) > 60 else sentence
                    
                    # Create event object
                    event = {
                        "description": description,
                        "participants": mentioned_characters,
                        "location": mentioned_location,
                        "time_position": position,
                        "importance": min(1.0, 0.5 + (len(mentioned_characters) * 0.1))  # Importance based on number of participants
                    }
                    
                    # Check if this is similar to an existing event to avoid duplicates
                    is_duplicate = False
                    for existing_event in events:
                        # Check for similarity in participants and position
                        same_participants = set(existing_event["participants"]) == set(event["participants"])
                        close_position = abs(existing_event["time_position"] - event["time_position"]) < 0.05
                        
                        if same_participants and close_position:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        events.append(event)
            
            # Sort events by position in text
            events = sorted(events, key=lambda e: e["time_position"])
            
            # Limit to most important events
            if len(events) > 20:
                events = sorted(events, key=lambda e: e["importance"], reverse=True)[:20]
                # Re-sort by position
                events = sorted(events, key=lambda e: e["time_position"])
            
            logger.info(f"Extracted {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error extracting events: {str(e)}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not self.initialized and not self.initialize():
            logger.error("OpenNLP processor not initialized")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "positive_score": 0.0,
                "negative_score": 0.0,
                "neutral_score": 1.0
            }
        
        try:
            # Simple lexicon-based sentiment analysis
            # This is a simplified approach as OpenNLP doesn't have a direct sentiment analyzer
            # In a production system, you would use a proper sentiment model
            
            # Define sentiment lexicons
            positive_words = {
                "good", "great", "excellent", "wonderful", "happy", "joy", "love", "like", "best", 
                "beautiful", "nice", "pleasant", "delight", "glad", "triumph", "success", "victory",
                "brave", "heroic", "friend", "friendship", "kind", "kindness", "gentle", "smile",
                "laugh", "win", "treasure", "gift", "magic", "hope", "fantastic", "amazing", "awesome"
            }
            
            negative_words = {
                "bad", "terrible", "awful", "horrible", "sad", "hate", "dislike", "worst", "ugly",
                "unpleasant", "fear", "afraid", "scared", "angry", "anger", "rage", "fail", "failure",
                "defeat", "death", "die", "dead", "kill", "pain", "hurt", "suffer", "cry", "danger",
                "dangerous", "enemy", "evil", "wicked", "cruel", "disaster", "tragedy", "tragic"
            }
            
            # Split text into sentences
            sentences = self.sentence_detector.sentDetect(text) if self.sentence_detector else [text]
            
            # Initialize counters
            positive_count = 0
            negative_count = 0
            total_words = 0
            
            # Process each sentence
            for sentence in sentences:
                # Skip empty sentences
                if not sentence.strip():
                    continue
                
                # Tokenize the sentence
                tokens = self.tokenizer.tokenize(sentence) if self.tokenizer else sentence.split()
                
                # Count sentiment words
                for token in tokens:
                    token_lower = token.lower()
                    if token_lower in positive_words:
                        positive_count += 1
                    elif token_lower in negative_words:
                        negative_count += 1
                    
                    total_words += 1
            
            # Calculate sentiment scores
            if total_words > 0:
                positive_score = positive_count / total_words
                negative_score = negative_count / total_words
                neutral_score = 1.0 - (positive_score + negative_score)
            else:
                positive_score = 0.0
                negative_score = 0.0
                neutral_score = 1.0
            
            # Determine overall sentiment
            if positive_score > negative_score and positive_score > 0.01:
                sentiment = "positive"
                confidence = positive_score
            elif negative_score > positive_score and negative_score > 0.01:
                sentiment = "negative"
                confidence = negative_score
            else:
                sentiment = "neutral"
                confidence = neutral_score
            
            logger.info(f"Analyzed sentiment: {sentiment} (confidence: {confidence:.2f})")
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "positive_score": positive_score,
                "negative_score": negative_score,
                "neutral_score": neutral_score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "positive_score": 0.0,
                "negative_score": 0.0,
                "neutral_score": 1.0
            }
    
    def close(self) -> None:
        """
        Clean up resources used by the OpenNLP processor.
        
        This method should be called when the processor is no longer needed
        to free up resources used by the JVM.
        """
        if self.initialized:
            try:
                # Clear model references
                self.tokenizer = None
                self.sentence_detector = None
                self.pos_tagger = None
                self.name_finder = None
                self.parser = None
                
                # Shutdown JVM if needed (only if we're the ones who started it)
                if jpype.isJVMStarted():
                    # In a real application, you might want to check if other components
                    # are still using the JVM before shutting it down
                    # For simplicity, we're assuming this is the only component using JPype
                    # jpype.shutdownJVM()
                    # Instead of shutting down, we'll log a message
                    logger.info("JVM remains running - will be shut down when process ends")
                
                self.initialized = False
                logger.info("OpenNLP processor resources released")
                
            except Exception as e:
                logger.error(f"Error closing OpenNLP processor: {str(e)}")
        else:
            logger.info("OpenNLP processor was not initialized, nothing to close") 
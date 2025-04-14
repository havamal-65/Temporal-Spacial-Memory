# Automated Narrative Processor

## Overview

The Automated Narrative Processor is a content-agnostic system for analyzing and visualizing narrative structures without requiring manual per-narrative configuration. It uses advanced NLP techniques to automatically identify characters, locations, events, and themes from any narrative text.

## Architectural Goals

1. **Truly Content-Agnostic**: Process any narrative text without manual configuration
2. **Single Universal Configuration**: Replace individual narrative configs with one universal config
3. **Automatic Entity Recognition**: Identify characters, locations, and events without manual labeling
4. **Cross-Narrative Learning**: Improve recognition through learning from previously processed texts

## Implementation Approach

### Core Components

1. **NLP Engine Integration**
   - Replace manual configuration with automated NLP-based entity extraction
   - Use pre-trained language models for entity recognition and relationship analysis
   - Support multiple NLP backends (spaCy, Hugging Face, custom models)

2. **Universal Configuration**
   ```yaml
   # universal_config.yaml - ONE config for ALL narratives
   processing:
     # NLP settings
     nlp_engine: "spacy"  # Options: spacy, huggingface, opennlp
     model: "en_core_web_lg"
     minimum_character_mentions: 5
     
     # Processing options
     extract_relationships: true
     identify_narrative_structure: true
     
     # Optional overrides (empty by default)
     forced_characters: []  # Can add specific characters if needed
     ignored_entities: []   # Entities to ignore
   
   visualization:
     colors:
       character: "#3498db"
       event: "#e74c3c"
       location: "#2ecc71"
       theme: "#9b59b6"
   ```

3. **Adaptive Entity Recognition System**
   - Character detection with coreference resolution
   - Location and setting identification
   - Event extraction with temporal ordering
   - Relationship mapping between entities

4. **Knowledge Base**
   - Cross-narrative learning to improve entity recognition
   - Pattern recognition for narrative structures
   - Storage of successful extraction techniques

### Processing Pipeline

1. **Text Extraction & Cleaning**
   - Extract text from source (PDF, EPUB, etc.)
   - Clean and normalize the text

2. **Automated Entity Recognition**
   - Run NLP processing to identify entities
   - Apply coreference resolution to link pronouns to entities
   - Filter entities by frequency and relevance

3. **Narrative Structure Analysis**
   - Identify key narrative phases (exposition, rising action, climax, etc.)
   - Detect theme and tone changes throughout the text
   - Map character arcs and development

4. **Visualization Generation**
   - Create interactive visualizations of the narrative structure
   - Generate character arc visualizations
   - Produce timeline of events and character relationships

## Technical Implementation

### Code Structure

The implementation replaces content-specific processors with a universal processor:

```python
class AutomaticNarrativeProcessor:
    def __init__(self, config_path="universal_config.yaml"):
        self.config = self._load_config(config_path)
        self.nlp_engine = self._initialize_nlp_engine()
        self.knowledge_base = NarrativeKnowledgeBase()
        
    def process_narrative(self, text, title=None):
        # Cleanup and normalize text
        clean_text = self._preprocess_text(text)
        
        # Extract entities
        entities = self._extract_entities(clean_text)
        
        # Analyze narrative structure
        structure = self._analyze_structure(clean_text, entities)
        
        # Build atlas
        atlas = self._build_atlas(title, entities, structure)
        
        # Update knowledge base
        self.knowledge_base.update_from_narrative(title, entities, structure)
        
        return atlas
```

### Entity Extraction

The system automatically identifies different entity types:

```python
def _extract_entities(self, text):
    """Extract entities from text using NLP"""
    doc = self.nlp_engine.process(text)
    
    # Extract and categorize entities
    characters = self._identify_characters(doc)
    locations = self._identify_locations(doc)
    events = self._identify_events(doc)
    themes = self._identify_themes(doc)
    
    # Resolve coreferences
    entities = self._resolve_coreferences(doc, characters, locations, events)
    
    # Filter by frequency and relevance
    filtered_entities = self._filter_entities(entities)
    
    return filtered_entities
```

### Narrative Knowledge Base

The system learns from each processed narrative to improve future analyses:

```python
class NarrativeKnowledgeBase:
    def __init__(self, db_path="narrative_knowledge.db"):
        self.db_path = db_path
        self.patterns = {}  # Patterns that indicate character importance
        self.narrative_structures = [] # Known narrative structures
        self.relationships = {} # Entity relationship patterns
        
    def update_from_narrative(self, title, entities, structure):
        """Learn from processed narrative to improve future analysis"""
        # Update entity recognition patterns
        self._update_entity_patterns(entities)
        
        # Update narrative structure models
        self._update_structure_models(structure)
        
        # Update relationship patterns
        self._update_relationship_patterns(entities)
        
        # Save knowledge base
        self._save()
```

## Advantages Over Manual Configuration

1. **Scalability**: Process any number of narratives without manual configuration
2. **Adaptability**: Automatically adapt to different narrative styles and structures
3. **Consistency**: Apply the same analysis techniques across all narratives
4. **Improvement Over Time**: System gets better with each processed narrative
5. **Reduced Maintenance**: No need to create and maintain separate configs

## Future Improvements

1. **Fine-tuning on Specific Genres**: Pre-train models for different literary genres
2. **Multi-lingual Support**: Extend beyond English to support multiple languages
3. **Domain-Specific Knowledge**: Add specialized knowledge for specific domains (sci-fi, historical, etc.)
4. **Interactive Learning**: Allow user feedback to improve entity recognition
5. **Advanced Visualization**: Develop more sophisticated visualization techniques

## Usage

```python
# Process a narrative with default settings
processor = AutomaticNarrativeProcessor()
atlas = processor.process_narrative(text, "The Great Gatsby")

# Generate visualizations
processor.generate_visualizations(atlas)

# Export results
processor.export_summary(atlas, "gatsby_summary.html")
```

## Conclusion

The Automated Narrative Processor eliminates the need for content-specific configurations while providing powerful narrative analysis capabilities. By leveraging modern NLP techniques and cross-narrative learning, it delivers rich insights into any narrative text without requiring manual setup for each new work. 
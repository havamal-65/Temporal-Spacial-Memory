# Narrative Atlas: A Spatial-Temporal Framework for Text Analysis

Narrative Atlas is a powerful framework built on top of the Temporal-Spatial Memory architecture that enables advanced analysis and visualization of narrative structures in texts of varying lengths - from short stories to novels.

## Overview

The Narrative Atlas framework maps narrative elements (characters, events, locations, themes) within a spatial-temporal context, allowing for intuitive navigation and visualization of complex textual structures. By leveraging the cylindrical coordinate system of the underlying MeshTube database, the framework can represent:

- **Time dimension**: Chronological progression of the narrative
- **Distance dimension**: Importance or centrality to the narrative
- **Angular dimension**: Thematic or relational grouping

## Key Features

- **Adaptive Text Processing**: Handles texts of any length through flexible segmentation
- **Entity Extraction**: Identifies characters, events, locations, and themes
- **Relationship Mapping**: Tracks connections between narrative elements
- **Multi-resolution Analysis**: Supports different analytical perspectives
- **Interactive Visualization**: Provides intuitive ways to explore narrative structure
- **Character Arc Analysis**: Tracks character development throughout the narrative
- **Narrative Structure Analysis**: Identifies key plot points and structural patterns

## Architecture

The framework consists of several key components:

### Specialized Node Types

- **CharacterNode**: Represents characters with attributes, mentions, and relationships
- **EventNode**: Captures narrative events with participants and importance
- **LocationNode**: Tracks locations with scene counts and character appearances
- **ThemeNode**: Represents thematic elements with related characters and events

### NarrativeAtlas Core

The central `NarrativeAtlas` class manages:
- Text segmentation and processing
- Entity extraction and relationship mapping
- Narrative analysis and metrics
- Database integration with the Temporal-Spatial Memory architecture

### Visualization System

- 3D spatial-temporal visualization of narrative structures
- Character arc visualizations
- Timeline representations
- Interactive navigation and exploration

## Getting Started

### Prerequisites

- Python 3.8+
- Dependencies from the Temporal-Spatial Memory project

### Basic Usage

```python
from src.models.narrative_atlas import NarrativeAtlas
from src.visualization.narrative_visualizer import create_narrative_visualization

# Initialize the framework
atlas = NarrativeAtlas(name="my_narrative", storage_path="data")

# Process a text
with open("my_story.txt", "r") as f:
    text = f.read()

atlas.process_text(text, title="My Story", segmentation_level="paragraph")

# Analyze the narrative structure
structure = atlas.analyze_narrative_structure()
print(f"Protagonist: {structure['protagonist']}")
print(f"Key events: {structure['key_events']}")

# Create visualizations
create_narrative_visualization(atlas, "my_narrative_visualization.html")
```

### Using the Test Script

The project includes a test script for quick experimentation:

```bash
python narrative_test.py --file Input/sample_narrative.txt --title "The Journey of Heroes" --segmentation paragraph
```

This will:
1. Process the provided text file
2. Extract narrative elements
3. Generate visualizations
4. Create a launcher HTML file to explore the results

## Analytical Capabilities

### Character Analysis

- Track mentions and appearances throughout the text
- Map relationships between characters
- Visualize character arcs and development

### Plot Structure

- Identify key events and their importance
- Map the narrative's emotional trajectory
- Detect standard plot structures (e.g., three-act structure)

### Thematic Analysis

- Track themes throughout the narrative
- Identify theme-character and theme-event relationships
- Visualize thematic progression

## Visualization Types

### 3D Narrative Visualization

The main visualization displays all narrative elements in a 3D spatial-temporal context:
- Vertical axis: Time progression
- Radial distance: Importance to narrative
- Angular position: Thematic or relational grouping

### Character Arc Visualization

Character-focused visualizations show:
- Character appearances across the timeline
- Related events and their importance
- Development patterns and relationships

### Narrative Timeline

A linear representation of the narrative showing:
- Key events
- Character introductions
- Narrative phases (exposition, rising action, climax, etc.)

## Future Enhancements

- Advanced NLP integration for better entity extraction
- Sentiment analysis for emotional mapping
- Comparative visualization of multiple narratives
- Machine learning for pattern recognition in narrative structures

## Contributing

Contributions to the Narrative Atlas framework are welcome! Areas that could benefit from development include:
- Improved NLP integration
- Additional visualization types
- Performance optimizations for very large texts
- Integration with additional text analysis tools

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
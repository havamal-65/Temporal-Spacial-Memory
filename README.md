# Temporal-Spatial Memory

A novel memory architecture for AI systems inspired by human cognition, organized along three dimensions:

- **Temporal**: When events occurred
- **Distance**: How important or relevant information is
- **Angular**: The topical or conceptual organization

## What's New: GraphRAG Integration

The system now integrates with GraphRAG for dramatically improved entity recognition and relationship extraction. Benefits include:

- **Better Entity Recognition**: Identify characters, locations, events, and themes with high accuracy
- **Relationship Extraction**: Automatically extract relationships between entities
- **Graph-Based Knowledge**: Structure narrative elements in a knowledge graph
- **Enhanced Visualizations**: Generate more meaningful visualizations of narrative structures

## Overview

Temporal-Spatial Memory offers a unique approach to organizing knowledge in a cylindrical coordinate system:

```
           |  Theme A  /
           |         /
           |        /
 Past      |       /       Future
<----------|------/------------>
           |     /|
           |    / |
           |   /  |
           |  /   |
           | /    |
```

This creates a "mesh tube" that enables:

1. **Temporal navigation**: Moving forward and backward in time
2. **Importance-based filtering**: More important information is closer to the center
3. **Thematic organization**: Angular position represents thematic relationships

## Features

- **Narrative Analysis**: Process literary texts and analyze their structure
- **Character Tracking**: Follow character arcs through narratives
- **Thematic Analysis**: Identify and track themes through texts
- **PDF Processing**: Directly analyze PDF documents
- **Interactive Visualizations**: Explore narratives through interactive HTML interfaces

## Processing the Hobbit with GraphRAG

For a demonstration of the GraphRAG-enhanced system, try processing The Hobbit:

```bash
python process_hobbit_with_graphrag.py
```

This will:
1. Extract text from The Hobbit PDF
2. Process it with GraphRAG to build a knowledge graph
3. Convert the graph to our cylindrical coordinate system
4. Generate enhanced visualizations

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/temporal-spatial-memory.git
cd temporal-spatial-memory
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For GraphRAG integration, additional setup:
```bash
cd graphrag
pip install -e .
cd ..
```

## Usage

### Process a narrative text:

```bash
python process_narrative.py --pdf your_book.pdf --config config_examples/default_config.yaml --use-graphrag --visualize
```

### Configuration

Configure your processing pipeline in YAML:

```yaml
narrative:
  title: "Your Book Title"
  author: "Author Name"

processing:
  use_graphrag: true
  llm:
    provider: "openai"
    model_name: "gpt-3.5-turbo"
```

## Examples

The repository includes examples:

- **The Hobbit**: Pre-configured for processing J.R.R. Tolkien's classic
- **Custom Texts**: Configure your own processing pipeline

## Visualization Types

The system generates several types of visualizations:

1. **Complete Narrative Structure**: The full temporal-spatial representation
2. **Timeline View**: Events across the temporal dimension
3. **Character Arcs**: Tracking individual characters through the narrative

## How It Works

### Without GraphRAG (Basic):

1. Text is extracted from PDFs or text files
2. Simple regex patterns identify potential entities
3. Basic relationship inference based on co-occurrence
4. Visualization in cylindrical coordinates

### With GraphRAG (Enhanced):

1. Text is extracted from PDFs or text files
2. GraphRAG processes the text with advanced NLP models
3. LLM-powered entity and relationship extraction
4. Knowledge graph construction with semantic understanding
5. Graph is mapped to cylindrical coordinates
6. Relationships preserved in spatial positioning

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
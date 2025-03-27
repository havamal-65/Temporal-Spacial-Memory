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

# GraphRAG Document Processor

This tool automates the process of ingesting documents into GraphRAG and managing the input/output files.

## Features

- **Document Processing**: Select and process documents using GraphRAG with a simple UI
- **Output Management**: Automatically creates dedicated output folders for each document
- **Duplicate Handling**: Detects when the same document is processed again and offers to overwrite or create a new version
- **File Browsing**: Browse input files and output visualizations directly from the UI
- **Visualization Viewing**: Easily open and view generated visualizations

## Getting Started

### Prerequisites

- Python 3.8 or higher
- GraphRAG installed and configured
- Required Python packages: tkinter, pyyaml

### Running the Application

1. Double-click the `process_document.bat` file (Windows) to launch the application
2. If you're on Mac or Linux, run `python document_processor.py` in your terminal

### How to Use

1. **Select a Document**: Click the "Browse" button to select a document file (PDF, TXT, etc.)
2. **Set Document Name**: Enter a name for the document (used for the output folder)
3. **Process**: Click "Process Document" to start processing
4. **View Results**: Once processing is complete, the output files will appear in the Output Files section
5. **Open Visualizations**: Select an output folder and click "Open Selected" to view the visualizations

### Output Organization

Each document is processed into its own folder in the `Output` directory:

- If processing the same document again, you'll be asked if you want to overwrite the existing output
- If you choose not to overwrite, a new folder with a timestamp will be created
- All visualizations, vector stores, and data files are saved in the document's folder

## Troubleshooting

- **Processing Errors**: Check the error message for details - most often related to API keys or file access
- **Missing Visualizations**: Make sure the document was processed successfully
- **Performance Issues**: Large documents may take a long time to process

## Advanced Configuration

The tool automatically updates the `settings.yaml` file to direct output to the document-specific folder. If you need to make additional configuration changes, edit the `settings.yaml` file directly. 
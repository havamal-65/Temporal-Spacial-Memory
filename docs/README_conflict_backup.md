# Temporal-Spatial Memory

A high-performance database system optimized for storing and querying data with both temporal and spatial dimensions, enhanced with GraphRAG for improved knowledge representation and retrieval.

- **Temporal**: When events occurred
- **Distance**: How important or relevant information is
- **Angular**: The topical or conceptual organization

- **Sprint 1**: ✅ Completed - Core Storage, Spatial Indexing, and Query Building
- **Sprint 2**: ✅ Completed - Query Engine, Combined Temporal-Spatial Indexing, and Testing
- **Sprint 3**: ✅ Completed - GraphRAG Integration and Knowledge Graph Enhancement
- **Sprint 4**: 🔄 In Progress - API Design and Delta Optimization

The system now integrates with GraphRAG for dramatically improved entity recognition and relationship extraction. Benefits include:

- **Multi-dimensional indexing**: Efficiently query data across both time and space dimensions
- **Immutable time-series storage**: Track changes to spatial data over time
- **High-performance queries**: Optimized query execution with cost-based optimization
- **Efficient storage**: In-memory and SQLite-based storage for fast, portable, and persistent data
- **Flexible query API**: Build complex temporal and spatial queries with an intuitive API
- **GraphRAG Integration**: Enhanced knowledge representation using graph-based retrieval augmented generation
- **Secure Configuration**: Environment-based configuration management for sensitive data

## Overview

Temporal-Spatial Memory offers a unique approach to organizing knowledge in a cylindrical coordinate system:

- **Storage Engine**: In-memory and SQLite backends for high-performance, durable storage
- **Spatial Indexing**: R-tree based spatial index for efficient 2D/3D queries
- **Temporal Indexing**: Specialized index structures for time-based data retrieval
- **Combined Index**: Unified temporal-spatial index for multi-dimensional queries
- **GraphRAG Engine**: Graph-based knowledge representation and retrieval system

This creates a "mesh tube" that enables:

- **Query Builder**: Expressive API for constructing complex queries
- **Query Engine**: Optimized execution with multiple strategies
- **Query Optimization**: Cost-based optimization with index selection
- **Knowledge Graph Queries**: Graph-based querying capabilities

## Features

- **Narrative Analysis**: Process literary texts and analyze their structure
- **Character Tracking**: Follow character arcs through narratives
- **Thematic Analysis**: Identify and track themes through texts
- **PDF Processing**: Directly analyze PDF documents
- **Interactive Visualizations**: Explore narratives through interactive HTML interfaces
- **In-Memory and SQLite Storage**: Fast, portable storage backends for all environments

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

## Supported Storage Backends

- **In-Memory**: Fastest, best for development, testing, and small/medium datasets.
- **SQLite**: (If enabled) Lightweight, file-based storage for persistence and portability.

> **Note:** RocksDB and other key-value store backends are no longer supported. All code, tests, and dependencies related to RocksDB have been removed for simplicity, maintainability, and cross-platform compatibility.

## Troubleshooting

- **Processing Errors**: Check the error message for details - most often related to API keys or file access
- **Missing Visualizations**: Make sure the document was processed successfully
- **Performance Issues**: Large documents may take a long time to process
- **Storage Issues**: If you need persistent storage, use the SQLite backend. For most workflows, in-memory storage is sufficient and fastest.

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

- Python 3.8+
- RocksDB
- Required Python packages (see requirements.txt)
- Environment configuration (see .env.example)

### Running the Application

```bash
# Clone the repository
git clone https://github.com/havamal-65/Temporal-Spacial-Memory.git

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

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
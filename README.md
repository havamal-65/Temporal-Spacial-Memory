# Temporal-Spatial Memory System with Polar Coordinates

A sophisticated information retrieval and memory system that maps text to 4D polar-temporal coordinates for enhanced context retrieval, narrative awareness, and multi-dimensional information organization.

## Overview

The Temporal-Spatial Memory System organizes information in a 4D coordinate space defined by:

- **Radius (r)**: Semantic importance/relevance
- **Theta (θ)**: Semantic direction/meaning
- **Temporal (t)**: Sequential/chronological position
- **Z-coordinate (z)**: Structural layer or perspective

This coordinate system enables rich information retrieval capabilities that surpass traditional vector search methods by incorporating temporal relationships, semantic directions, and structural organization.

## Key Features

- **Polar-Temporal Coordinate System**: Maps text to a 4D space that preserves both semantic relationships and narrative structure
- **Temporal-Aware Retrieval**: Find information with awareness of chronological sequence
- **Directional Bias**: Favor specific semantic directions in information retrieval
- **Multi-Layer Organization**: Filter information based on structural layers
- **Visualization Tools**: Explore information distribution across coordinate dimensions
- **Natural Language Query Processing**: Parse queries for temporal constraints and coordinate filters
- **RAG Integration**: Generate contextually rich, narrative-aware content for LLMs
- **Advanced Retrieval Methods**: Including Hypothetical Document Embeddings (HyDE) and hybrid search (semantic + keyword)
- **Coordinate Validation**: Ensures consistent coordinate mapping between storage and retrieval

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/temporal-spatial-memory.git
   cd temporal-spatial-memory
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (copy .env.example to .env and fill in your API keys)
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Quick Start

1. Process a document into the polar-temporal coordinate system:
   ```bash
   python ingest_structured_atlas.py --input-pdf input/your_document.pdf --output-atlas-path output/atlas_storage
   ```

2. Query the system:
   ```bash
   python src/query.py --storage-path output/atlas_storage --query "Find information about key events in the early chapters"
   ```
   
   Use advanced retrieval methods:
   ```bash
   # Use hybrid search for better keyword matching
   python src/query.py --storage-path output/atlas_storage --query "Hobbit" --use-hybrid-search
   
   # Use HyDE for better semantic understanding
   python src/query.py --storage-path output/atlas_storage --query "Tell me about the main character" --use-hyde
   ```

3. Visualize the coordinate space:
   ```bash
   python visualize_atlas.py --atlas-path output/atlas_storage --type dashboard
   ```

## Documentation

### Architecture and Guides

- [Coordinate System Architecture](docs/coordinate_system_architecture.md): Details of the 4D polar-temporal coordinate system
- [Temporal Aspect User Guide](docs/temporal_aspect_user_guide.md): How to leverage temporal dimensions in queries
- [Advanced Retrieval Methods](docs/Phase7_Coordinate_System_Alignment.md): Details on HyDE and hybrid search implementation
- [API Documentation](docs/api_documentation.md): Comprehensive API reference
- [Example Notebook](docs/example_notebook.md): Jupyter notebook with common use cases

### Previous Development Phases

- **Phase 1**: Coordinate Transformation Implementation ✓
- **Phase 2**: Storage Optimization ✓
- **Phase 3**: Retrieval Methods ✓
- **Phase 4**: Visualization & Analysis ✓
- **Phase 5**: Testing & Optimization ✓
- **Phase 6**: Documentation & Integration ✓
- **Phase 7**: Embedding Coordinate System Alignment ✓

## System Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  Document Input │───┬─▶│ Polar-Temporal  │──┬──▶│  NarrativeAtlas │
│                 │   │  │ Transformation  │  │   │                 │
└─────────────────┘   │  └─────────────────┘  │   └─────────────────┘
                      │                       │             │
                      │                       │             │
                      │  ┌─────────────────┐  │             ▼
                      │  │                 │  │   ┌─────────────────┐
                      └─▶│   Embedding     │──┘   │                 │
                         │    Service      │      │     Queries     │
                         │                 │      │                 │
                         └─────────────────┘      └─────────────────┘
```

## Core Components

- **NarrativeAtlas**: Main interface for the system; manages nodes and coordinates
- **CoordinateMapper**: Transforms text and embeddings into polar-temporal coordinates
- **Visualization Tools**: Dashboard, static visualizations, and network exports
- **Query Processing**: Natural language parsing and coordinate-aware retrieval

## Example Usage

```python
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service

# Initialize
embedding_service = create_embedding_service()
atlas = NarrativeAtlas(storage_path="output/atlas", embedding_service=embedding_service)

# Add content
node_id = atlas.add_node(
    node_id=None,
    content={"text": "Example content to store"},
    embedding=None,  # Will be generated
    metadata={"page_number": 1, "chunk_index_on_page": 0}
)

# Temporal-aware search
results = atlas.search_with_temporal_focus(
    query_text="Find related information",
    temporal_focus=5.0,  # Target temporal position
    decay_rate=0.1
)

# Process results
for node, score in results:
    print(f"Score: {score}, Content: {node.content['text']}")
```

## New in Phase 7: Coordinate System Alignment

Phase 7 brings major improvements to the system's coordinate handling and retrieval capabilities:

1. **Fixed Coordinate System Mismatch**: We've corrected a critical issue where the coordinate system parameters were inconsistent between ingestion and query processes. This ensures that data ingested with embedding-based coordinates can now be properly retrieved using the same coordinate system.

2. **Enhanced Retrieval Methods**:
   - **Hybrid Search**: Combines semantic embedding search with keyword matching, greatly improving results for exact-match queries like "Hobbit".
   - **HyDE (Hypothetical Document Embeddings)**: Generates a hypothetical document that would answer a query, then embeds that document instead of the original query for better semantic context.

3. **System Robustness**:
   - Added configuration validation to prevent parameter mismatches
   - Improved error handling for different coordinate types
   - Enhanced logging for easier debugging of coordinate transformations

Try these new features with:

```bash
# Use hybrid search for better keyword matching
python src/query.py --storage-path output/atlas_storage --query "Hobbit" --use-hybrid-search

# Use HyDE for better semantic understanding 
python src/query.py --storage-path output/atlas_storage --query "Tell me about the main character" --use-hyde
```

## Server API

The system includes a FastAPI server for accessing functionality via HTTP:

```bash
# Start the server
python server.py
```

Access the API at `http://localhost:8000/narrative-rag` with queries:

```json
{
  "query": "How did the main character evolve through the story?",
  "k": 3
}
```

## Visualization

The system provides multiple visualization options:

- **Interactive Dashboard**: Explore the coordinate space in real-time
- **Static Visualizations**: Generate 2D and 3D plots of coordinates
- **Network Exports**: Export to Gephi, Cytoscape, or D3.js formats
- **Heatmaps**: Visualize information density across coordinate dimensions

## License

[MIT License](LICENSE)

## Acknowledgements

This project utilizes several open-source libraries and frameworks:
- [LangChain](https://github.com/langchain-ai/langchain) for embeddings and vector stores
- [FAISS](https://github.com/facebookresearch/faiss) for vector similarity search
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) for embeddings
- [Plotly](https://github.com/plotly/plotly.py) for interactive visualizations

## Features

- **4D Polar-Temporal Coordinate Space**: Map information into a 4-dimensional space for intuitive retrieval
- **Semantic Embedding Integration**: Convert text embeddings to meaningful polar coordinates
- **Contextual Retrieval**: Search with awareness of temporal, thematic, and relevance dimensions
- **Coordinate-Based Filtering**: Filter results by time period, thematic direction, and relevance radius
- **Rich Visualization**: Visual exploration of the information space with relationship analysis
- **Advanced Retrieval Methods**: Multiple retrieval techniques for optimal information access

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables in `.env` file:
```
OPENAI_API_KEY=your_openai_key_here
COHERE_API_KEY=your_cohere_key_here (optional, for reranking)
```

## Usage

### Ingest Documents

```bash
python ingest_structured_atlas.py --input-directory ./input --output-directory ./output/atlas
```

### Query the Database

Basic query:
```bash
python run_project.py --query "What happened in Middle Earth?"
```

With advanced parameters:
```bash
python run_project.py --query "What happened in Middle Earth?" --temporal-focus 0.5 --directional-bias 1.5 --use-hybrid
```

### Advanced Retrieval Methods (Phase 8)

The system provides multiple advanced retrieval methods:

- **ColBERT Token-Level Retrieval**: Fine-grained matching between query and document tokens
  ```bash
  python run_project.py --query "Your query" --retrieval-method colbert
  ```

- **Cohere Reranking**: Reranks initial retrieval results for improved relevance
  ```bash
  python run_project.py --query "Your query" --retrieval-method rerank
  ```

- **Maximal Marginal Relevance (MMR)**: Provides diverse results while maintaining relevance
  ```bash
  python run_project.py --query "Your query" --retrieval-method mmr --diversity-lambda 0.6
  ```

- **RAG-Fusion**: Combines multiple retrieval methods with reciprocal rank fusion
  ```bash
  python run_project.py --query "Your query" --retrieval-method rag_fusion
  ```

- **Weighted Ensemble**: Uses a weighted combination of different retrieval techniques
  ```bash
  python run_project.py --query "Your query" --retrieval-method ensemble
  ```

### Visualization

```bash
python visualize_atlas.py --input-directory ./output/atlas --output-directory ./output/viz
```

## System Architecture

The system consists of several components:

1. **Embedding Service**: Converts text to vector embeddings
2. **Coordinate Mapper**: Transforms embeddings into polar-temporal coordinates
3. **Narrative Atlas**: Core database with coordinate-based storage and retrieval
4. **Query Engine**: Processes natural language queries and retrieves relevant information
5. **Advanced Retrieval System**: Provides multiple methods for improved information retrieval

## Advanced Retrieval Methods

Phase 8 introduces four key advanced retrieval enhancements:

1. **ColBERT-style Token-Level Embeddings**:
   - Creates embeddings for individual tokens rather than entire documents
   - Enables more precise matching between query and document tokens
   - Particularly effective for capturing localized semantic information

2. **Cohere Reranker**:
   - Uses Cohere's reranking API to improve retrieval relevance
   - Applies advanced LLM-based relevance scoring to initial results
   - Helps correct errors in the initial retrieval phase

3. **Maximal Marginal Relevance (MMR)**:
   - Balances relevance with information diversity
   - Reduces redundancy in search results
   - Controllable diversity-relevance trade-off via lambda parameter

4. **Hybrid Retrieval Fusion**:
   - RAG-Fusion: Combines multiple retrievers with reciprocal rank fusion
   - Weighted ensemble: Applies different weights to various retrieval methods
   - Provides more robust retrieval performance across different query types

## Development Phases

1. ✅ **Phase 1**: Coordinate Transformation Implementation
2. ✅ **Phase 2**: Storage Optimization
3. ✅ **Phase 3**: Retrieval Methods
4. ✅ **Phase 4**: Visualization & Analysis
5. ✅ **Phase 5**: Testing & Optimization
6. ✅ **Phase 6**: Documentation & Integration
7. ✅ **Phase 7**: Embedding Coordinate System Alignment
8. ✅ **Phase.8**: Advanced Retrieval Enhancement
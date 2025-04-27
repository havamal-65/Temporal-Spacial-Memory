# Temporal-Spatial Memory System

A 4D polar-temporal memory system for information retrieval, designed to map and store knowledge in a coordinate space defined by relevance (r), perspective (θ), time (t), and abstraction (z).

## Overview

This project implements a knowledge representation system using a 4D polar-temporal coordinate space. The system allows for the ingestion, storage, and retrieval of information along different dimensions of meaning.

The four dimensions are:
- **r (radius)**: Relevance/significance to the core concept
- **θ (theta)**: Perspective/approach to the topic
- **t (time)**: Temporal position
- **z (height)**: Level of abstraction/granularity

## Components

The system is organized into several key components:

1. **Core Coordinate System**: Defines the mathematical model and operations for the 4D space.
2. **Ingestion Pipeline**: Processes documents into the system.
3. **Storage Layer**: Manages the efficient storage and retrieval of information.
4. **Query Engine**: Allows for complex querying across the coordinate space.
5. **Narrative Atlas**: A high-level interface for managing and querying narrative elements (characters, events, locations) using semantic search powered by LangChain and FAISS.

## Embedding Service

The system supports multiple embedding service types for generating vector representations of text:

1. **Mock Embedding Service**: Generates deterministic pseudo-embeddings for testing and development.
2. **LangChain Embedding Service**: Uses real embedding models from the LangChain ecosystem.
3. **Cascading Embedding Service**: Provides fallback mechanisms if the primary service fails.

Supported embedding models include:
- `all-MiniLM-L6-v2` (local, 384 dimensions)
- `all-mpnet-base-v2` (local, 768 dimensions) 
- `text-embedding-3-small` (OpenAI, 1536 dimensions)
- `text-embedding-3-large` (OpenAI, 3072 dimensions)

The embedding service can be configured through environment variables or directly when initializing the ingestion pipeline.

## Narrative Atlas (Detailed)

The `NarrativeAtlas` class (`src/models/narrative_atlas.py`) provides a structured way to interact with narrative data.

Key features include:

- **Node Management**: Methods to create, retrieve, and delete specific node types (characters, events, locations).
- **LangChain FAISS Integration**: Uses `langchain_community.vectorstores.FAISS` for storing and searching text embeddings.
- **Scalable Indexing**: Initializes new vector stores using `faiss.IndexHNSWFlat` for efficient approximate similarity search, suitable for larger datasets.
- **Persistence**: Saves and loads the FAISS index and associated node ID mappings to disk (`save_local`, `load_local`).
- **Refined Embeddings**: Constructs descriptive text for embedding based on node type and content (e.g., including participant names for events) to improve search relevance.
- **Basic RAG Support**: Includes an `answer_query_with_context` method that retrieves relevant nodes based on a query, formats them as context, and constructs a prompt suitable for Retrieval-Augmented Generation with an LLM.

An integration test (`tests/integration/test_narrative_atlas_faiss.py`) verifies the core add, save, load, search, and delete functionality.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/temporal-spatial-memory.git
   cd temporal-spatial-memory
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Download the spaCy model (required for entity extraction):
   ```
   python -m spacy download en_core_web_sm
   ```

4. (Optional) Create a `.env` file based on `.env.example` to configure the embedding service and other settings.

## Usage

### Running the System

Use the `run.py` script to run the system:

```
python run.py --mode all --clear-db
```

This will:
1. Clear the existing database (if --clear-db is set)
2. Process all documents in the `input` directory
3. Store the chunks in the 4D coordinate space

### Command-line Options

- `--mode`: Operation mode (`ingest`, `query`, or `all`, default: `ingest`)
- `--input-dir`: Directory containing input documents (default: `input`)
- `--output-dir`: Directory for processing output (default: `output`)
- `--storage-path`: Path for database storage (default: `output/db`)
- `--clear-db`: Clear the database before ingestion
- `--text-query`: Query by text similarity
- `--max-results`: Maximum number of results to return (default: 10)

### Ingestion Pipeline

To just run the ingestion pipeline:

```
python src/main.py --input-dir input --output-dir output
```

### Query Engine

To query the database:

```
python src/query.py --text-query "Your query here" --min-relevance 0.1
```

## Configuration

The system can be configured through environment variables:

- `EMBEDDING_SERVICE_TYPE`: Type of embedding service to use ("mock", "langchain", or "cascading")
- `EMBEDDING_MODEL_NAME`: Name of the embedding model (default: "all-MiniLM-L6-v2")
- `EMBEDDING_CACHE_SIZE`: Size of the LRU cache for embeddings (default: 1000)
- `OPENAI_API_KEY`: API key for OpenAI embeddings (if using OpenAI models)
- `CHUNK_SIZE`: Default size of text chunks (default: 1000)
- `CHUNK_OVERLAP`: Default overlap between chunks (default: 200)

## Supported File Types

The system currently supports the following document formats:
- PDF (.pdf)
- Microsoft Word (.docx)
- Text (.txt)
- Markdown (.md)
- HTML (.html)

## Architecture

The system follows a pipeline architecture:

1. **Core Coordinate System**: Defines the fundamental 4D coordinate structure and implements custom distance metrics.
2. **Ingestion Pipeline**: Handles document loading, text chunking, entity extraction, and coordinate mapping.
3. **Storage Layer**: Manages the persistence of nodes and their relationships in the database.
4. **Query Engine**: Provides semantic search and coordinate-based querying capabilities.

## Project Structure

```
.
├── input/                 # Input documents
├── output/                # Processing output and database storage
├── src/
│   ├── models/            # Core data models
│   │   └── coordinate_system.py
│   ├── services/          # Service components
│   │   ├── ingestion_pipeline.py
│   │   └── storage_manager.py
│   ├── utils/             # Utility functions
│   │   ├── document_loader.py
│   │   ├── text_chunker.py
│   │   ├── entity_extractor.py
│   │   ├── coordinate_mapper.py
│   │   └── embedding_service.py
│   ├── main.py            # Main ingestion script
│   └── query.py           # Query script
├── run.py                 # System runner script
└── requirements.txt       # Python dependencies
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
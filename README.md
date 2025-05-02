# Temporal-Spatial Memory

## Description

This project implements a system for ingesting text documents, analyzing their content and structure chunk by chunk, and storing them in a "Narrative Atlas". The core idea is to represent each text chunk using 4D Polar-Temporal Coordinates (`r`, `theta`, `z`, `t`) within a vector database (FAISS).

-   `r` (radius) and `theta` (angle) represent semantic similarity relative to a central theme or origin.
-   `z` (depth) and `z_type` represent the hierarchical structure within the document.
-   `t` (time) represents the sequential position of the chunk in the original document.

The system uses an initial analysis pass followed by a "Steward LLM" phase, which performs a global analysis to refine the assigned coordinates (excluding `t`) for better consistency and accuracy across the entire document.

## Key Concepts

-   **Narrative Atlas:** A vector store (currently using FAISS) that stores text chunk embeddings alongside their calculated Polar-Temporal Coordinates and other metadata.
-   **Polar-Temporal Coordinates:** A 4D system (`r`, `theta`, `z`, `t`) for locating text chunks based on semantics, structure, and sequence.
-   **Chunking:** Dividing input documents into smaller, manageable text segments for analysis.
-   **Embedding:** Generating vector representations of text chunks using language models.
-   **Steward LLM:** A secondary LLM process (implemented using a Map-Reduce pattern) responsible for refining the initial coordinates based on a global view of the document's content and structure.

## Core Components

-   `src/models/narrative_atlas.py`: Manages the FAISS vector store and associated metadata.
-   `src/data_models.py`: Defines Pydantic models for coordinates, nodes, and other data structures.
-   `src/services/ingestion_pipeline.py`: Orchestrates the document ingestion process, including chunking, initial coordinate mapping, and invoking the Steward LLM.
-   `src/services/coordinate_mapper.py`: Responsible for calculating the initial coordinates for each text chunk.
-   `src/services/steward_analyzer.py`: Implements the Steward LLM logic using a Map-Reduce approach for global coordinate refinement.
-   `ingest_structured_atlas.py`: Main script for ingesting PDF documents, performing initial structural/semantic analysis, and optionally running the Steward LLM refinement.
-   `src/query.py`: Handles querying the Narrative Atlas (under development/verification).
-   `requirements.txt`: Lists project dependencies.
-   `.env`: File for storing environment variables (e.g., API keys).
-   `server.py`: (Potentially for future API access - TBD)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Temporal-Spacial\ Memory
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables:**
    Create a `.env` file in the project root and add necessary variables, such as your OpenAI API key:
    ```dotenv
    OPENAI_API_KEY='your_openai_api_key_here'
    # Add other necessary environment variables
    ```

## Usage

1.  Place the document(s) you want to ingest (currently supports PDF via `ingest_structured_atlas.py`) into a suitable directory (e.g., `input/`).
2.  Run the ingestion script (`ingest_structured_atlas.py`), specifying the input PDF and the path for the atlas data:
    ```bash
    python ingest_structured_atlas.py --input-pdf ./input/your_document.pdf --output-atlas-path ./output/my_atlas_data
    ```
    -   Use `--overwrite` to clear any existing atlas data at the output path before starting.
    -   Use `--start-page` and `--end-page` to process only a specific range of pages.
    -   Use `--llm-model` to specify a different OpenAI model (e.g., `gpt-4o-mini`).
3.  Processed outputs (the Narrative Atlas data including FAISS index and node database) will be saved in the directory specified by `--output-atlas-path`. Debug logs are printed to the console.
4.  (Future/Under Development) Query the generated atlas using `src/query.py`:
    ```bash
    # Example structure - verify arguments in src/query.py
    python src/query.py --atlas-path ./output/my_atlas_data --query "Search for specific information"
    ```

## Testing

*(Information about running tests, if available in the `tests/` directory, should be added here.)*

## Project Goal & Vision

The primary goal is to build a "Narrative Atlas" capable of reconstructing and querying narrative sequences from source documents. It aims to understand not just *what* information exists, but *where* it fits within the overall structure and flow of the narrative in a multi-dimensional context. This involves mapping text chunks (nodes) into a 4D coordinate system:

-   **t (time)**: Represents the sequential position within the document/narrative flow. Derived from structural features like page number and chunk order.
-   **r (radius)**: Represents relevance or centrality to the core narrative or a specific query context. Currently fixed in Phase 1, intended for semantic refinement in Phase 2. (Range 0.0 - 1.0, lower is more relevant).
-   **θ (theta)**: Represents thematic category or perspective. Currently derived simplistically from structure (page number) in Phase 1, intended for semantic refinement in Phase 2. (Range 0 - 2π or 0-360 degrees).
-   **z (height)**: Represents the level of abstraction or context layer (e.g., document root, section, paragraph, chunk). Derived from structural information.

## Approach: Phased Development

The system is being developed in phases:

1.  **Phase 1: Structural Backbone (Complete)**
    *   Focus on accurately mapping the *structure* of documents (pages, chunk order) to establish the temporal (`t`) and initial spatial (`theta`, `z`, fixed `r`) coordinates.
    *   Ingest documents, perform page-by-page chunking, and store nodes with structure-derived coordinates in the `NarrativeAtlas`.
    *   Utilize FAISS for efficient vector similarity search based on chunk embeddings.
2.  **Phase 2: Semantic Refinement (Planned)**
    *   Integrate a Large Language Model (LLM) to analyze node content and metadata.
    *   Use LLM insights to refine the semantic coordinates (`r` and `theta`) based on content relevance and thematic classification.
    *   Update nodes in the `NarrativeAtlas` with these refined coordinates, adding a layer of semantic understanding.

## Current Status (Post-Phase 2 Refinement Debugging)

*   **Phase 1 (Structural Backbone):** Complete and functional.
*   **Phase 2 (Semantic Refinement):**
    *   The `refine_coordinates.py` script has been developed and debugged.
    *   It successfully loads the atlas data created by the ingestion phase.
    *   It utilizes an LLM (`gpt-4o-mini` by default) via LangChain to analyze node content.
    *   It correctly assigns semantic coordinates (`r` for relevance, `theta` for topic) based on LLM output.
    *   **Batch processing** is implemented using `refinement_chain.batch()` for improved performance.
    *   **Retry logic** with exponential backoff is implemented in `refine_coordinates.py` to handle potential OpenAI API rate limits.
    *   The script now successfully processes all nodes in testing, handling potential rate limits.
    *   The updated nodes with refined coordinates are saved to `spatial_temporal_db.pkl`.
    *   A progress report is available: `docs/planning/progress_report_phase2_refinement.md`.

## Components

The system is organized into several key components:

1.  **Models (`src/models`)**:
    *   `SpatialTemporalDB`: Basic in-memory node storage.
    *   `Node`: Dataclass representing a text chunk or other entity.
    *   `CoordinateSystem`: Defines the `PolarTemporalCoordinate`.
    *   `NarrativeAtlas`: High-level interface for managing nodes, coordinates, and the FAISS vector store. Orchestrates coordinate calculation and storage.
2.  **Services (`src/services`)**:
    *   `IngestionPipeline`: Orchestrates document loading, chunking, embedding generation, and adding nodes to the `NarrativeAtlas`.
3.  **Utilities (`src/utils`)**:
    *   `DocumentLoader`: Loads various document types (PDF, DOCX, TXT, etc.).
    *   `TextChunker`: Splits text into manageable chunks.
    *   `EntityExtractor`: Extracts named entities, events, and locations using spaCy.
    *   `CoordinateMapper`: Calculates coordinates (primarily structural in Phase 1) and extracts keywords.
    *   `EmbeddingService`: Handles text embedding generation (supports mock, LangChain models).

## Installation

1.  Clone the repository:
    ```bash
    git clone <your-repo-url>
    cd Temporal-Spacial Memory
    ```
2.  Create a virtual environment (recommended) and activate it.
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Download the spaCy model (required for entity extraction):
    ```bash
    python -m spacy download en_core_web_sm
    ```
5.  (Optional) Create a `.env` file to configure `OPENAI_API_KEY` if using OpenAI embeddings, or other settings like `CHUNK_SIZE`, `CHUNK_OVERLAP`.

## Usage

Use the `run.py` script for primary operations:

**1. Ingest Documents:**

*   Place documents in the `input/` directory (or a subdirectory).
*   Run the ingestion command, specifying the storage path and input directory.

    ```bash
    # Example: Ingest documents from 'input/' into 'output/my_atlas'
    python run.py --mode ingest --storage-path output/my_atlas --input-dir input
    ```
*   Use `--clear-db` flag to remove existing data at the storage path before ingesting.

    ```bash
    # Example: Clear and ingest into 'output/test_atlas'
    python run.py --mode ingest --storage-path output/test_atlas --input-dir input --clear-db
    ```

**2. Query the Atlas:**

*   Run the query command, specifying the storage path and your text query.

    ```bash
    # Example: Query 'output/my_atlas'
    python run.py --mode query --storage-path output/my_atlas --text-query "Search for this information"
    ```
*   Adjust the number of results with `--max-results` (default: 10).

### Command-line Options (`run.py`)

*   `--mode`: Operation mode (`ingest`, `query`, default: `ingest`).
*   `--input-dir`: Directory containing input documents for ingestion (default: `input`).
*   `--storage-path`: Path for storing/loading the Narrative Atlas data (DB + FAISS index). Required for both ingest and query.
*   `--clear-db`: (Ingest mode only) Clear existing data at `--storage-path` before ingestion.
*   `--text-query`: (Query mode only) The text query for similarity search.
*   `--max-results`: (Query mode only) Maximum number of results to return (default: 10).
*   `--embedding-service`: Choose the embedding service (`mock`, `langchain`, `cascading`, default: `mock`).

## Configuration

Environment variables can be set (e.g., in a `.env` file):

*   `EMBEDDING_SERVICE_TYPE`: Default embedding service if not specified via CLI.
*   `EMBEDDING_MODEL_NAME`: Specific model name (e.g., "all-MiniLM-L6-v2", "text-embedding-3-small").
*   `OPENAI_API_KEY`: Required if using OpenAI models.
*   `CHUNK_SIZE`: Default text chunk size (default: 1000).
*   `CHUNK_OVERLAP`: Default chunk overlap (default: 200).

## Next Steps

1.  ~~**Address Rate Limiting:** Implement retry logic (e.g., with exponential backoff) in `refine_coordinates.py` to handle `RateLimitError` during batch processing.~~ (DONE)
2.  ~~**Complete Refinement:** Run the finalized `refine_coordinates.py` script to process all nodes and generate the full set of semantic coordinates.~~ (DONE - Verified)
3.  **Phase 3 (Querying Mechanisms):**
    *   Develop advanced querying mechanisms that leverage the refined `r` and `theta` coordinates.
4.  **Phase 4 (Visualization):**
    *   Implement visualization tools to explore the 4D Narrative Atlas.

## License

MIT License.
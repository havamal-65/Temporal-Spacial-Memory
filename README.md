# Temporal-Spatial Memory

## Description

This project implements a system for ingesting text documents (currently PDFs), extracting structured entities (characters, events, locations) page by page using an LLM, calculating initial 4D Polar-Temporal Coordinates (`r`, `theta`, `z`, `t`) for these entities, and storing them in a "Narrative Atlas" (FAISS vector store + metadata).

-   `r` (radius) and `theta` (angle) represent semantic position.
-   `z` (depth) and `z_type` represent structural layer/type.
-   `t` (time) represents the sequential position (page number).

The ingestion pipeline includes an optional "Steward LLM" phase, which uses a Map-Reduce approach to perform a global analysis across all extracted entities, refining the `r`, `theta`, `z`, and `z_type` coordinates for better consistency and accuracy across the entire document. The `t` coordinate remains fixed.

## Key Concepts

-   **Narrative Atlas:** A vector store (currently using FAISS) that stores text chunk embeddings alongside their calculated Polar-Temporal Coordinates and other metadata.
-   **Polar-Temporal Coordinates:** A 4D system (`r`, `theta`, `z`, `t`) for locating text chunks based on semantics, structure, and sequence.
-   **Chunking:** Dividing input documents into smaller, manageable text segments for analysis.
-   **Embedding:** Generating vector representations of text chunks using language models.
-   **Steward LLM:** A secondary LLM process (implemented using a Map-Reduce pattern) responsible for refining the initial coordinates based on a global view of the document's content and structure.

## Core Components

-   `ingest_structured_atlas.py`: Main script for ingesting PDF documents, performing entity extraction, initial coordinate mapping, and optionally running the Steward LLM refinement.
-   `src/models/narrative_atlas.py`: Manages the FAISS vector store and associated metadata, including adding/updating nodes and coordinates.
-   `src/data_models.py`: Defines Pydantic models for coordinates, nodes, entities, and other data structures.
-   `src/utils/embedding_service.py`: Handles text embedding generation (currently using SentenceTransformers via Langchain).
-   `src/services/steward_analyzer.py`: Implements the Steward LLM logic using a Map-Reduce approach for global coordinate refinement (r, theta, z, z_type).
-   `src/query.py`: Handles querying the Narrative Atlas (under development/verification).
-   `setup.py`: Cross-platform script to set up the virtual environment and install dependencies.
-   `requirements.txt`: Lists project dependencies.
-   `.env` / `.env copy.txt`: Files for storing environment variables (e.g., API keys).
-   `server.py`: (Potentially for future API access - TBD)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd Temporal-Spacial\ Memory
    ```
2.  **Run the setup script:**
    This script will create a virtual environment (if it doesn't exist), install dependencies from `requirements.txt`, and download the necessary spaCy model.
    ```bash
    python setup.py
    ```
3.  **Activate the virtual environment:**
    After the setup script finishes, activate the created environment. The script will print the correct command for your OS (Windows or Linux/macOS).
    ```bash
    # Example for Windows (Command Prompt/PowerShell)
    .\venv\Scripts\activate
    
    # Example for Linux/macOS (bash/zsh)
    source venv/bin/activate 
    ```
4.  **Configure Environment Variables:**
    The setup script will remind you, but ensure you have a `.env` file in the project root. If you don't, copy the `.env copy.txt` file to `.env` and add your OpenAI API key and any other required variables:
    ```bash
    # Example for Windows
    copy ".env copy.txt" .env 
    
    # Example for Linux/macOS
    cp ".env copy.txt" .env
    ```
    Then, edit the `.env` file to add your credentials.

## Usage

1.  **Setup the environment:** Follow the instructions in the [Setup](#setup) section.
2.  **Activate the virtual environment** (the setup script provides the command).
3.  **Run Ingestion:**
    Use the `ingest_structured_atlas.py` script to process a PDF and build/update an atlas. The Steward LLM refinement step is automatically included if the analyzer initializes correctly (requires `OPENAI_API_KEY`).

    ```bash
    python ingest_structured_atlas.py --input-pdf <path/to/your/document.pdf> --output-atlas-path <path/to/save/atlas/data>
    ```
    **Key Arguments:**
    *   `--input-pdf`: (Required) Path to the input PDF file.
    *   `--output-atlas-path`: (Required) Directory path to save/load the Narrative Atlas data (FAISS index and metadata).
    *   `--llm-model`: (Optional) OpenAI model for entity extraction and Steward refinement (default: `gpt-3.5-turbo`). Ensure your API key has access.
    *   `--start-page`: (Optional) 1-indexed page number to start processing from (default: 1).
    *   `--end-page`: (Optional) 1-indexed page number to end processing at (inclusive, default: end of document).
    *   `--overwrite`: (Optional) If set, ignores and overwrites any existing atlas data at the output path.

4.  **Querying (Development):**
    The `src/query.py` script is intended for querying the generated atlas, but its functionality is still under development/verification.
    ```bash
    # Example (details might change)
    # python src/query.py --atlas-path <path/to/your/atlas/data> --query "Search term"
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
    *   **Retry logic** with exponential backoff is implemented in `refine_coordinates.py`
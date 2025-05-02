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
    *   **Retry logic** with exponential backoff is implemented in `refine_coordinates.py`
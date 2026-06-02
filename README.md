# Temporal-Spatial Memory System with Polar Coordinates

A document-memory and retrieval system that maps text and narrative entities into a
4D **polar-temporal coordinate space**, enabling retrieval that is aware of semantic
direction, relevance, narrative sequence, and structural layer — not just vector
similarity.

## The 4D Coordinate System

Every node (text chunk, character, event, or location) is placed at coordinates
`(r, θ, t, z)`:

- **Radius (r)** — semantic centrality / relevance. Derived from how strongly the
  node's embedding matches its best semantic sector.
- **Theta (θ)** — semantic direction. The node is assigned to one of 8 compass
  sectors via the `SemanticCompass` (cosine similarity to sector reference centroids).
- **Temporal (t)** — sequential position in the source document
  (`(page - 1) + chunk_position`), preserving narrative order.
- **Z (z)** — structural layer / perspective (e.g. main text vs. metadata).

All four coordinates are now populated at ingest time. Narrative entities
(characters, events, locations) are embedded from their real text and mapped through
the same `CoordinateMapper`/`SemanticCompass` pipeline as text chunks, so they receive
meaningful `r` and `θ` values rather than placeholder zeros.

> Note: sentence-transformer embeddings are L2-normalised (constant magnitude), so when
> the semantic compass is active both `r` and `θ` are derived from sector cosine
> similarity. Configurations without the compass fall back to the legacy
> magnitude/`arctan2` behaviour.

## LLM Provider Configuration

LLM-powered steps (PDF entity extraction, natural-language query parsing, optional
Steward refinement, HyDE) run through a single provider factory
(`src/utils/llm_factory.py`). The provider is selected with the `LLM_PROVIDER`
environment variable.

- **`local` (default)** — an OpenAI-compatible local server. No API key or quota
  required. Works with [Ollama](https://ollama.com) (default
  `http://localhost:11434/v1`) or LM Studio (`http://localhost:1234/v1`).
- **`openai`** — the hosted OpenAI API. Requires `OPENAI_API_KEY`.

Relevant environment variables (see `.env.example`):

```bash
LLM_PROVIDER=local                              # "local" (default) or "openai"
LOCAL_LLM_BASE_URL=http://localhost:11434/v1    # Ollama default; LM Studio: :1234/v1
LOCAL_LLM_MODEL=llama3.2:3b
LOCAL_LLM_API_KEY=ollama                         # placeholder; local servers ignore it
# OPENAI_API_KEY=...                             # only needed when LLM_PROVIDER=openai
```

## Installation

1. Clone the repository and install dependencies:

```bash
git clone https://github.com/havamal-65/Temporal-Spatial-Memory.git
cd Temporal-Spatial-Memory
pip install -r requirements.txt
```

2. Create your local environment file:

```bash
cp .env.example .env
```

The defaults run fully locally; edit `.env` only if you want to switch providers or
endpoints.

3. (Local provider) Install Ollama and pull the default model:

```bash
ollama pull llama3.2:3b
```

Make sure the Ollama server is running before ingesting or querying.

### Windows note

On Windows, set UTF-8 output encoding so console logging and document text render
correctly:

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

## Usage

### 1. Ingest a document

Extracts entities and text into the 4D atlas:

```bash
python ingest_structured_atlas.py --input-pdf input/your_document.pdf --output-atlas-path output/atlas
```

Useful flags:

- `--overwrite` — clear any existing atlas at the output path before ingesting
  (a true overwrite, so stale nodes are not left behind).
- `--start-page` / `--end-page` — limit the page range.
- `--enable-steward` — run the optional Steward LLM coordinate-refinement pass after
  ingestion (off by default).

### 2. Run the end-to-end demo

Loads a stored atlas and runs sector-filtered search, coordinate-range filtering, and
an NL query:

```bash
python demo_atlas.py --atlas output/atlas --k 5
```

Demos 1 and 2 require no LLM. Demo 3 (NL query parsing) uses the configured LLM
provider (local by default).

### 3. Query directly

**Grounded Q&A (recommended)** — retrieve passages, generate an answer with citations:

```bash
python src/query.py \
  --storage-path output/hobbit_local_full \
  --query "What does the party meet while traveling through the mountains?" \
  --answer \
  --max-results 12 \
  --show-context
```

Requires a running LLM (Ollama by default). Answers are grounded in retrieved
paragraph text; citations use verse-style refs like `the_hobbit_tolkien:68:1`.

**Retrieval-only modes:**

```bash
# Hybrid search (semantic + keyword) — good for exact-match terms
python src/query.py --storage-path output/atlas --query "Arkenstone" --use-hybrid-search

# Temporal focus — bias results toward a point in the narrative
python src/query.py --storage-path output/atlas --query "the journey begins" --temporal-focus 5.0

# Hypothetical Document Embeddings (HyDE)
python src/query.py --storage-path output/atlas --query "Tell me about the main character" --use-hyde
```

When the FAISS index holds fewer vectors than nodes (segments in FAISS, entities in
SQLite), similarity search scores **all in-memory embeddings**, so entity nodes
remain reachable. Hybrid search combines semantic and keyword matching; the answer
path uses multi-channel retrieval (timeline, region hints, theme coverage) for
list-style and character questions.

### Addressable references

Ingest creates **segment** nodes (one per paragraph) with stable refs:

`{doc_id}:{page}:{paragraph}` — e.g. `the_hobbit_tolkien:126:1`

Entity nodes link back via `source_refs`. Retrieval can expand a hit to neighboring
paragraphs without scanning the whole book. See
[Addressable text plan](docs/addressable_text_plan.md).

## Project Structure

```
src/
├── models/      # NarrativeAtlas, spatial-temporal DB
├── utils/       # coordinate_mapper, semantic_compass, llm_factory, embedding_service
├── services/    # ingestion pipeline, storage manager
├── temporal/    # temporal reasoning extensions
└── visualization/  # dashboards, plots, exporters
docs/            # architecture and user guides
tests/           # unit and integration tests
```

## Core Components

- **NarrativeAtlas** — main interface; manages nodes, coordinates, and retrieval.
- **CoordinateMapper** — maps text/embeddings to `(r, θ, t, z)` coordinates.
- **SemanticCompass** — assigns semantic-direction sectors used for `θ` and `r`.
- **llm_factory** — single, provider-configurable entry point for all LLM access.

## Documentation

- [Usefulness roadmap](docs/usefulness_roadmap.md) — what’s done and what’s next
- [Addressable full text](docs/addressable_text_plan.md) — verse-style refs and segment ingest
- [Token efficiency](docs/token_efficiency.md) — context budgets and deduplication
- [Coordinate System Architecture](docs/coordinate_system_architecture.md)
- [Temporal Aspect User Guide](docs/temporal_aspect_user_guide.md)
- [API Documentation](docs/api_documentation.md)
- [Example Notebook](docs/example_notebook.md)

## Known Limitations

- With the local provider, the Steward refinement step is conservative and may
  recommend zero coordinate adjustments; it is disabled by default (`--enable-steward`
  to opt in).
- FAISS indexes **segment** nodes; entity nodes are searchable via in-memory
  embedding fallback and hybrid keyword matching.
- Small local models (e.g. `llama3.2:3b`) may omit retrieved details in answers even
  when citations are good; try a larger model or increase `--max-context-tokens`.
- Region routing uses keyword hints in `src/models/retrieval_merge.py` for some
  question shapes (mountains, Erebor, Beorn); not fully automatic.
- Six tests under `tests/temporal/` are known pre-existing failures.

## Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain) — embeddings and chat models
- [FAISS](https://github.com/facebookresearch/faiss) — vector similarity search
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) — embeddings
- [Ollama](https://ollama.com) — local LLM serving

## License

[MIT License](LICENSE)

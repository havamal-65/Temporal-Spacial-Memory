<!-- CURSOR_PRESERVE: true -->
# Project Roadmap — Detailed Checklist ✅

> NOTE: This file is flagged with `CURSOR_PRESERVE` so the Cursor summarizer should **not** collapse or truncate it. Keep full detail for ongoing reference.

---

## Phase 1 — Short-Term

- [x] **Deletion & Consistency**
  - [x] Wire `SpatialTemporalDB` into `NarrativeAtlas` for unified node storage.
  - [x] Extend `NarrativeAtlas.delete_node` to update DB + FAISS + typed maps.
  - [x] Expand integration test to cover deletion flow.

- [x] **Enrich SpatialTemporalDB**
  - [x] Add node `update` / patch method.
  - [x] Add query/filters by type & time.
  - [x] Unit tests for CRUD.

- [ ] **Embedding / Relevance Fine-Tuning**
  - [x] Refine character/location/event embeddings (DONE).
  - [ ] Expose HNSW params (`M`, `efSearch`) via config.

- [ ] **Basic RAG Demo**
  - [x] Implement `answer_query_with_context` (DONE).
  - [ ] Add mock LLM call + example notebook.

---

## Phase 2 — Mid-Term

- [ ] **Scalability & Persistence**
  - [ ] Disk-based `SpatialTemporalDB` (SQLite/DuckDB).
  - [ ] Atomic `save_all` / `load_all` (DB + FAISS).

- [ ] **Config & Benchmarking**
  - [ ] YAML/env config for `alpha, beta, gamma`, index params.
  - [ ] Benchmark script for N synthetic nodes.

- [ ] **API Layer & CI**
  - [ ] FastAPI endpoints (`/nodes`, `/search`, `/rag`).
  - [ ] GitHub-Actions: lint, pytest, coverage.

---

## Phase 3 — Stretch Goals

- [ ] 4-D Navigation (`t`, `z` layers).
- [ ] UMAP/TSNE visualization front-end.
- [ ] Reranking / advanced retrieval.
- [ ] Multi-modal embeddings (image/audio).
- [ ] Production hardening (pgvector/Qdrant, RBAC).

---

**Last updated:** _initial import_
**Progress updated:** _SpatialTemporalDB enriched & tested_ 
# Addressable Full Text ("verse" references)

**Status: implemented** (May 2026). Full Hobbit ingest with segments lives in
`output/hobbit_local_full`. This document remains the design reference.

## Goal
Ingest the full source text as **addressable units** (paragraph-level to start),
store them in the existing node store, give every extracted entity/event a stable
**reference** into that text, and let retrieval expand wider context on demand by
reference window — so an LLM (or a person) can look through the surrounding text
without reading the whole book. Inspired by Bible verse addressing
(`book:chapter:verse`, range-able like `John 3:16-18`).

## Decisions (locked)
- **Granularity:** paragraph-level first; revisit sentence-level after testing.
- **Storage:** unified — segments are nodes in the existing `SpatialTemporalDB`
  (distinct `type="segment"`, `z_type="LAYER_MAIN"`), reusing all coordinate and
  sequence-retrieval machinery. No separate table, no duplicated logic.

## Why this fits the current code
- `atlas.add_node(...)` already indexes FAISS when given an embedding
  (`src/models/narrative_atlas.py:478-480`), so segment nodes populate the
  currently-empty FAISS index for free.
- `t` is already an ordinal address; `SequenceRetriever.get_neighbors`
  (`src/models/sequence_retrieval.py`) already fetches a t-window in order — a
  reference window over segment nodes is the same mechanism, scoped to segments.

---

## Reference scheme
- **Human-readable id:** `{doc_id}:{page}:{para}` e.g. `hobbit:40:3`.
  - `doc_id` = sanitized PDF filename stem.
  - Ranges render as `hobbit:40:3-41:1`.
- **Ordinal backing:** the temporal coordinate `t`, used for ordering and range
  fetches (no separate index needed).
- **Single t/page convention (must standardize):** today entity nodes use
  `t = float(page_num)` (1-indexed) while the chunk formula in
  `src/utils/coordinate_mapper.py:576-578` uses `page-1 + fraction` (0-indexed),
  and `assemble_sequence_context` assumes `page = int(t)+1`. Standardize on:
  - `t = page_num + (para_idx / max(1, total_paras_on_page))` (page is 1-indexed)
  - `page = int(t)`
  Apply consistently to entities (already `float(page_num)`) and segments, and fix
  the off-by-one in `assemble_sequence_context` (`page = int(t)` not `int(t)+1`).

---

## Data model (unified node store)
Segment node:
- `id`: `segment:{doc_id}:{page}:{para}`
- `type`: `"segment"`
- `content`: `{"text": <paragraph text>, "ref": "hobbit:40:3"}`
- `coordinates`: `r/theta` from embedding (existing mapper), `t` per convention,
  `z_type="LAYER_MAIN"`
- `embedding`: paragraph embedding (→ FAISS via `add_node`)
- `metadata`: `{node_type:"segment", doc_id, page, para_idx, total_paras, ref}`

Entity/event nodes gain a back-reference:
- `content["source_refs"]`: list of refs (append on each appearance; dedup-safe)
- `metadata["source_refs"]`: same, for SQL/debug visibility

---

## Work breakdown

### Phase 1 — Segment store at ingest
1. Add a small paragraph splitter (reuse `src/utils/text_chunker.py` or split on
   blank lines with a min-length guard) — keep it a separate composable helper.
2. In `ingest_structured_atlas.py` page loop, before entity extraction: segment
   `page_text`, and for each paragraph call `atlas.add_node(...)` with a segment
   node (embedding computed → FAISS indexed). Reuse the standardized t convention.
3. Verify segments persist to SQLite and FAISS (`ntotal > 0`).

### Phase 2 — Link entities/events to references
4. After segmenting a page, attach `source_refs` to the entities/events extracted
   from that page:
   - characters/locations: substring match of name within page paragraphs.
   - events: pick the paragraph with highest embedding similarity to the event
     description.
5. Extend `_get_or_create_character` / `_get_or_create_location` / `_create_event`
   (`src/models/narrative_atlas.py`) to accept and append `source_refs`
   (append on repeat appearances; do not overwrite).

### Phase 3 — Reference + window retrieval API
6. New helpers (in `SequenceRetriever`, reusing existing t-window logic):
   - `parse_ref(ref_str) -> (doc_id, page, para)` and `resolve_ref(ref_str) -> node`.
   - `get_text_window(ref_or_node, before=1, after=1) -> List[(node, score)]`:
     fetch **segment** nodes in the surrounding t-range, sorted by t.
7. Thin wrapper `NarrativeAtlas.get_text_window(...)` for a single public interface.

### Phase 4 — Wire into answers/retrieval
8. Entity/event hits expose `source_refs`; when wider context is needed, expand via
   `get_text_window` to include surrounding paragraphs (the "look through the text"
   feature). Segment nodes are also directly retrievable (rich prose grounding).
9. Surface references in assembled context labels (e.g. `[hobbit:40:3]`) so answers
   can cite them — dovetails with roadmap item 1 (LLM answer generation).

---

## Validation
- Unit tests (no LLM, synthetic atlas):
  - segmentation yields ordered refs; segment nodes are t-monotonic.
  - `get_text_window` returns the correct before/after paragraph range in t order.
  - `parse_ref` / `resolve_ref` round-trip; entity nodes carry `source_refs`.
- Eval harness (`tests/eval/`): add cases that retrieve an entity, expand its
  reference window, and check the surrounding paragraphs are contiguous and on-topic;
  report context size (token efficiency signal).
- Small-range re-ingest (e.g. pages 1-10) into a temp atlas to confirm segments +
  links populate and FAISS is non-empty, before any full re-ingest.

## Risks / notes
- **t/page convention** must be fixed in one place and applied everywhere, or
  entities and segments will misalign on the t axis (see Reference scheme).
- Paragraph count grows the node set (Hobbit ~ a few thousand segments) — fine for
  in-memory + FAISS at this scale; sentence-level would multiply it.
- PyPDFLoader paragraph boundaries are imperfect on some PDFs; the splitter should
  fall back to page-as-one-paragraph when no blank lines are found.
- A full re-ingest (~tens of minutes on the local model) is needed to populate
  segments for the existing `output/hobbit_local_full`; prove on a small range first.

## Out of scope (later)
- Sentence-level addressing (after paragraph-level proves out).
- Cross-document global ordinals (multi-book corpora).

## Implementation status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Segment store at ingest (`paragraph_segmenter`, segment nodes in FAISS) | done |
| 2 | Entity `source_refs` linking | done |
| 3 | `parse_ref`, `resolve_ref`, `get_text_window` | done |
| 4 | Wire into `answer_query`, citations, CLI `--answer` | done |
| Validation | Unit tests, smoke ingest, eval harness extensions | done |

Remaining: full eval of **answer quality** on a fixed question set; optional
sentence-level granularity.

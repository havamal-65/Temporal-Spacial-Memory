# Roadmap: From Retrieval Engine to Useful Tool

This captures prioritized work for turning Temporal-Spatial Memory into a tool you
can point at a book, ask questions, and get **sequence-aware, grounded answers**.

Status legend: **[done]** shipped · **[partial]** partially in place · **[todo]** not started.

Last updated: May 2026.

---

## 1. Close the RAG loop — actually answer questions
**Impact: highest · Effort: low · Status: [done]**

- `NarrativeAtlas.answer_query()` retrieves passages, assembles t-ordered context,
  and calls the configured LLM via `src/models/rag_answer.py`.
- `src/query.py --answer` prints the answer and citation refs.
- `server.py` exposes a grounded answer path (verify against your deployment).

Grounded prompt rules: answer only from passages, cite refs, list multiple valid
answers when the question expects enumeration.

---

## 2. Fix the entry points so it is usable end-to-end
**Impact: high · Effort: low-medium · Status: [partial]**

**Done:**
- Primary CLI: `python src/query.py --storage-path … --query "…" --answer`
- Ingest: `python ingest_structured_atlas.py --input-pdf … --output-atlas-path …`

**Remaining:**
- Single documented “ingest then ask” script without dead paths in `run_project.py`
- Harden `server.py` defaults and document the `/ask` (or equivalent) endpoint
- Optional: thin `ask` subcommand wrapper

---

## 3. Make retrieved content rich enough to answer from
**Impact: high · Effort: medium · Status: [done]**

**Addressable full text** (see `docs/addressable_text_plan.md`):

- Paragraph-level **segment** nodes with refs `doc:page:para` (e.g.
  `the_hobbit_tolkien:68:1`)
- Entity/event nodes carry `source_refs` back to prose
- `SequenceRetriever.get_text_window()` / `expand_results_with_refs()` widen hits
- Full Hobbit atlas: `output/hobbit_local_full` (~310 segments + ~1,550 entities)

**Retrieval quality** (post-addressable):

- Hybrid semantic + keyword search over all nodes (FAISS segments + DB entities)
- Multi-channel retrieval for list-style questions (enumeration + MMR + region hints)
- Region / theme injection in `src/models/retrieval_merge.py` (journey hazards,
  Beorn, Arkenstone/Erebor, etc.)

---

## 4. Token efficiency
**Impact: medium · Effort: low-medium · Status: [done]**

**Shipped:**
- `src/utils/token_budget.py` — `tiktoken` counting (cl100k_base fallback), text + embedding dedupe, trim
- Token-budgeted `assemble_sequence_context(max_total_tokens=…)`
- `answer_query` dedupes after ref expansion; returns `context_tokens` / `context_chars`
- CLI `--max-context-tokens` (default 1500); enumeration queries use a 2000-token floor
- Embedding near-duplicate collapse (`dedupe_results_by_embedding`, threshold 0.92)
- Region-scoped hybrid keyword scan (`t_min` / `t_max` from `region_t_range` in `_retrieve_for_query`)
- Eval harness reports `context_tokens` and optional `expect_max_context_tokens` assertions
- Server API: `max_context_tokens` input, `context_tokens` output

**Future (optional at Hobbit scale):**
- FAISS/in-memory semantic prefilter for `find_similar_nodes` on multi-book corpora
- Semantic dedupe at retrieval-merge time (before ref expansion)

---

## 5. Trust and polish
**Impact: medium · Effort: medium · Status: [partial]**

**Done:**
- Sequence eval harness: `tests/eval/sequence_eval.py`
- Retrieval regression tests: `tests/test_retrieval_hybrid.py`, `tests/test_retrieval_merge.py`

**Remaining:**
- Eval cases that score **answer quality** on fixed question sets (not just ordering)
- Fix 6 pre-existing failures in `tests/temporal/`
- Fix `visualize_atlas.py` (Plotly categorical color + KMeans NaN)
- Pin runtime dependencies; remove `run_project.py` dead code
- Commit and push the addressable-text + retrieval work when ready

---

## Suggested sequence (updated)

1. ~~Answers (1)~~ → ~~Addressable text (3)~~ → ~~Token efficiency (4)~~ → **Polish (5)** → **Entry points (2)**

Item 5 adds measurable trust; item 2 is mostly packaging.

---

## Stretch goals

- Second book ingest to prove generality (no Hobbit-specific tuning)
- Reduce reliance on hand-tuned region keyword hints (automatic region detection)
- Larger local model option for synthesis when 3B skips retrieved facets

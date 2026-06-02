# Token Efficiency



How the system keeps LLM context bounded and avoids wasting tokens on duplicate or

overlapping passages.



## Goals



1. **Predictable cost** — cap context by token count, not only characters.

2. **Less redundancy** — ref expansion (`before=1, after=1`) can pull adjacent

   paragraphs that overlap; dedupe before sending to the LLM.

3. **Observability** — expose `context_tokens` and `context_chars` in answer metadata

   for eval and tuning.



## Components



### `src/utils/token_budget.py`



| Function | Purpose |

|----------|---------|

| `count_tokens(text)` | Count tokens (`tiktoken` cl100k_base; falls back to chars÷4) |

| `normalize_for_dedupe(text)` | Whitespace-normalized text for comparison |

| `dedupe_results_by_text(results, extract_text)` | Drop duplicate / subsumed passages (keep higher score) |

| `dedupe_results_by_embedding(results, extract_text, threshold=0.92)` | Drop paraphrase / near-duplicate segments via cosine similarity on stored embeddings |

| `dedupe_results_for_context(results, extract_text)` | Text dedupe then embedding dedupe (production path) |

| `trim_text_to_tokens(text, max_tokens)` | Hard trim with ellipsis |



### Context assembly



`SequenceRetriever.assemble_sequence_context()` accepts:



- `max_total_tokens` — primary budget (preferred)

- `max_tokens_per_passage` — per-block cap

- Legacy `max_total_chars` / `max_chars_per_passage` still supported



Passages are added in narrative (`t`) order until the token budget is exhausted.



### Answer path



`NarrativeAtlas.answer_query()`:



1. Retrieves with `_retrieve_for_query` (region-scoped hybrid when hints match)

2. Optionally expands via `source_refs`

3. **Dedupes** overlapping text, then near-duplicate embeddings

4. Assembles context under token budget

5. Returns `context_tokens`, `context_chars` alongside answer and citations



### Hybrid keyword prefilter



`search_with_hybrid(..., t_min=, t_max=)` limits the expensive keyword scan to nodes

within a narrative time window. `_retrieve_for_query` passes `region_t_range(query)`

when a region hint matches (mountains, Beorn, Erebor/jewel, etc.).



### CLI



```bash

python src/query.py \

  --storage-path output/hobbit_local_full \

  --query "Who is Gandalf?" \

  --answer \

  --max-context-tokens 1500

```



Default token budget: **1500** tokens (enumeration queries may use a higher floor).



### Server API



`QueryInput.max_context_tokens` (default 1500) and `RagOutput.context_tokens` mirror

the CLI answer path.



### Eval harness



`tests/eval/sequence_eval.py` reports real `context_tokens` (not chars÷4). Case fields:



| Field | Purpose |

|-------|---------|

| `max_context_tokens` | Budget passed to production context or `answer_query` |

| `use_production_context` | Run `_retrieve_for_query` + expand + dedupe + assemble (no LLM) |

| `expect_max_context_tokens` | Assert assembled/answer context stays under ceiling |



Example cases: `token_budget_mountain`, `token_budget_jewel` in `sequence_cases.json`.



## Tuning tips



- **Compound questions** (jewel + mountain + guardian): retrieval may return 10–12

  passages; 1500–2000 tokens is usually enough if dedupe is on.

- **Enumeration questions** (multiple dangers on a journey): allow 2000–2500 tokens

  or rely on automatic enumeration budget bump.

- If answers miss facets, increase `--max-context-tokens` before increasing `k`.



## Future work



- FAISS/in-memory semantic prefilter for `find_similar_nodes` on very large multi-book atlases

- Semantic dedupe at retrieval-merge time (before ref expansion)


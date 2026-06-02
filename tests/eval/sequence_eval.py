"""
Repeatable evaluation harness for sequence-aware retrieval.

Runs a fixed set of cases (tests/eval/sequence_cases.json) against a built
atlas and records metrics so improvements can be compared before/after:
  - intent classification matches the expected mode
  - returned passages are t-monotonic (story order) when expected
  - recall of expected event substrings (when a case declares them)
  - assembled context size (chars + tiktoken count) — token-efficiency signal

This is a standalone script (not part of the pytest golden suite) because it
needs a built atlas and a local embedding service. It degrades gracefully:
if the atlas is missing it prints guidance and exits without error.

Usage (from project root):
    $env:PYTHONIOENCODING='utf-8'
    python tests/eval/sequence_eval.py
    python tests/eval/sequence_eval.py --atlas output/hobbit_local_full --baseline

The first run with --baseline writes tests/eval/baseline_sequence.json. Later
runs print a metric delta against that baseline.
"""

import os
import sys
import json
import argparse
import re
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

EVAL_DIR = os.path.dirname(__file__)
CASES_PATH = os.path.join(EVAL_DIR, "sequence_cases.json")
BASELINE_PATH = os.path.join(EVAL_DIR, "baseline_sequence.json")
DEFAULT_ATLAS = os.path.join(PROJECT_ROOT, "output", "hobbit_local_full")


def _is_t_monotonic(results) -> bool:
    ts = [node.coordinates.t for node, _ in results]
    return ts == sorted(ts)


def _recall(results, substrings: List[str]) -> Optional[float]:
    if not substrings:
        return None
    from src.models.sequence_retrieval import SequenceRetriever

    blob = " ".join(SequenceRetriever._extract_text(node).lower() for node, _ in results)
    hits = sum(1 for s in substrings if s.lower() in blob)
    return hits / len(substrings)


def _production_context(atlas, sr, query: str, k: int, max_context_tokens: int) -> tuple:
    """Mirror answer_query context path without LLM generation."""
    from src.utils.token_budget import count_tokens, dedupe_results_for_context

    results = atlas._retrieve_for_query(query, k=k)
    results = sr.expand_results_with_refs(results, before=1, after=1)
    results = dedupe_results_for_context(results, sr._extract_text)
    per_passage = max(120, min(350, max_context_tokens // max(len(results), 1)))
    context = sr.assemble_sequence_context(
        results,
        max_total_tokens=max_context_tokens,
        max_tokens_per_passage=per_passage,
    )
    return results, context, count_tokens(context)


def run_case(atlas, sr, case: Dict[str, Any]) -> Dict[str, Any]:
    from src.models.sequence_retrieval import SequenceRetriever
    from src.utils.token_budget import count_tokens

    query = case["query"]
    k = case.get("k", 10)
    max_context_tokens = case.get("max_context_tokens", 1500)
    intent = SequenceRetriever.detect_sequence_intent(query)

    if case.get("use_production_context"):
        results, context, context_token_count = _production_context(
            atlas, sr, query, k, max_context_tokens
        )
        recall = _recall(results, case.get("expect_event_substrings", []))
    elif intent["mode"] == "timeline":
        results = sr.fetch_timeline(
            t_min=case.get("t_min"), t_max=case.get("t_max"), query=query, k=k
        )
        context = sr.assemble_sequence_context(results)
        recall = _recall(results, case.get("expect_event_substrings", []))
        context_token_count = count_tokens(context)
    elif intent["mode"] == "neighbors":
        results = sr.get_neighbors(intent["anchor"], direction=intent["direction"], k=k)
        context = sr.assemble_sequence_context(results)
        recall = _recall(results, case.get("expect_event_substrings", []))
        context_token_count = count_tokens(context)
    else:
        try:
            results = atlas.search_with_nl_query(query, k=k)
        except Exception:
            results = atlas.find_similar_nodes(query, k=k)
        context = sr.assemble_sequence_context(results)
        recall = _recall(results, case.get("expect_event_substrings", []))
        context_token_count = count_tokens(context)

    answer_metrics: Dict[str, Any] = {}
    if case.get("run_answer"):
        try:
            from src.utils.llm_factory import llm_is_available

            if llm_is_available():
                ans = atlas.answer_query(
                    query,
                    k=k,
                    max_context_tokens=max_context_tokens,
                )
                answer_text = (ans.get("answer") or "").lower()
                subs = case.get("expect_answer_substrings") or []
                answer_metrics["answer_ok"] = all(s.lower() in answer_text for s in subs) if subs else True
                citations = ans.get("citations") or []
                pat = case.get("expect_cited_ref_pattern")
                answer_metrics["citation_ok"] = (
                    any(re.search(pat, c) for c in citations) if pat and citations else bool(citations) or not pat
                )
                answer_metrics["answer_chars"] = len(ans.get("answer") or "")
                answer_metrics["num_citations"] = len(citations)
                answer_metrics["answer_context_tokens"] = ans.get("context_tokens")
                answer_metrics["answer_context_chars"] = ans.get("context_chars")
            else:
                answer_metrics["skipped"] = "llm_unavailable"
        except Exception as e:
            answer_metrics["error"] = str(e)

    token_budget_ok: Optional[bool] = None
    ceiling = case.get("expect_max_context_tokens")
    if ceiling is not None:
        check_tokens = answer_metrics.get("answer_context_tokens", context_token_count)
        if check_tokens is not None:
            token_budget_ok = check_tokens <= ceiling

    metrics = {
        "id": case["id"],
        "query": query,
        "detected_mode": intent["mode"],
        "expected_mode": case.get("expected_mode"),
        "mode_match": intent["mode"] == case.get("expected_mode"),
        "num_results": len(results),
        "t_values": [round(node.coordinates.t, 2) for node, _ in results],
        "t_monotonic": _is_t_monotonic(results) if results else None,
        "expect_t_monotonic": case.get("expect_t_monotonic"),
        "recall": recall,
        "context_chars": len(context),
        "context_tokens": context_token_count,
        "token_budget_ok": token_budget_ok,
        "expect_max_context_tokens": ceiling,
    }
    metrics.update(answer_metrics)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Sequence retrieval evaluation harness")
    parser.add_argument("--atlas", default=DEFAULT_ATLAS, help="Path to a built atlas storage dir")
    parser.add_argument("--baseline", action="store_true", help="Write results as the new baseline")
    args = parser.parse_args()

    if not os.path.exists(os.path.join(args.atlas, "nodes.sqlite")):
        print(f"[skip] No atlas found at {args.atlas}.")
        print("       Build one first, e.g.:")
        print('       python ingest_structured_atlas.py --input-pdf "input/your_book.pdf" '
              '--output-atlas-path output/hobbit_local_full --overwrite')
        return 0

    from src.models.narrative_atlas import NarrativeAtlas
    from src.models.sequence_retrieval import SequenceRetriever
    from src.utils.embedding_service import create_embedding_service

    embedding_service = create_embedding_service("langchain")
    atlas = NarrativeAtlas(storage_path=args.atlas, embedding_service=embedding_service)
    sr = SequenceRetriever(atlas)
    print(f"Loaded atlas '{args.atlas}' with {len(atlas.db.nodes)} nodes.\n")

    with open(CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    results: List[Dict[str, Any]] = []
    for case in cases:
        m = run_case(atlas, sr, case)
        results.append(m)
        flag = "OK " if m["mode_match"] else "!! "
        if m.get("token_budget_ok") is False:
            flag = "!! "
        mono = "" if m["expect_t_monotonic"] is None else f" monotonic={m['t_monotonic']}"
        rec = "" if m["recall"] is None else f" recall={m['recall']:.2f}"
        ans = ""
        if m.get("skipped"):
            ans = f" answer=skip({m['skipped']})"
        elif "answer_ok" in m:
            ans = f" answer_ok={m['answer_ok']} citations={m.get('num_citations', 0)}"
        tok = f" ctx={m['context_tokens']}tok"
        if m.get("answer_context_tokens") is not None:
            tok = f" answer_ctx={m['answer_context_tokens']}tok"
        budget = ""
        if m.get("expect_max_context_tokens") is not None:
            budget = f" budget_ok={m.get('token_budget_ok')}"
        print(f"[{flag}] {m['id']}: mode={m['detected_mode']} "
              f"n={m['num_results']}{mono}{rec}{ans}{tok}{budget}")
        print(f"       t-order: {m['t_values']}")

    summary = {
        "atlas": args.atlas,
        "num_cases": len(results),
        "mode_match_rate": round(sum(r["mode_match"] for r in results) / len(results), 3),
        "monotonic_ok": sum(
            1 for r in results
            if r["expect_t_monotonic"] and r["t_monotonic"]
        ),
        "avg_context_chars": round(sum(r["context_chars"] for r in results) / len(results), 1),
        "avg_context_tokens": round(sum(r["context_tokens"] for r in results) / len(results), 1),
        "cases": results,
    }

    print("\n--- summary ---")
    print(f"mode_match_rate: {summary['mode_match_rate']}  "
          f"avg_context_tokens: {summary['avg_context_tokens']}  "
          f"avg_context_chars: {summary['avg_context_chars']}")

    if args.baseline:
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nBaseline written to {BASELINE_PATH}")
    elif os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            base = json.load(f)
        print(f"\nvs baseline: mode_match_rate "
              f"{base.get('mode_match_rate')} -> {summary['mode_match_rate']}, "
              f"avg_context_tokens {base.get('avg_context_tokens', base.get('avg_context_chars', 0) // 4)} "
              f"-> {summary['avg_context_tokens']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

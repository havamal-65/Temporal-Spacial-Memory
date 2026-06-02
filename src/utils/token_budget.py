"""
Token counting and context-budget helpers for LLM retrieval.

Uses tiktoken when available; falls back to a chars/4 heuristic for local models.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger("TokenBudget")

Result = Tuple[Any, float]

_ENCODER = None
_ENCODER_TRIED = False


def _get_encoder():
    global _ENCODER, _ENCODER_TRIED
    if _ENCODER_TRIED:
        return _ENCODER
    _ENCODER_TRIED = True
    try:
        import tiktoken

        _ENCODER = tiktoken.get_encoding("cl100k_base")
    except Exception as exc:
        logger.debug("tiktoken unavailable (%s); using char heuristic", exc)
        _ENCODER = None
    return _ENCODER


def count_tokens(text: str) -> int:
    """Return approximate token count for a string."""
    if not text:
        return 0
    enc = _get_encoder()
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def normalize_for_dedupe(text: str) -> str:
    """Collapse whitespace for duplicate / overlap checks."""
    return " ".join((text or "").lower().split())


def text_fingerprint(text: str) -> str:
    """Stable hash of normalized passage text."""
    norm = normalize_for_dedupe(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def trim_text_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to at most max_tokens (word-bounded when possible)."""
    if max_tokens <= 0 or not text:
        return ""
    if count_tokens(text) <= max_tokens:
        return text
    words = text.split()
    lo, hi = 0, len(words)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        chunk = " ".join(words[:mid])
        if count_tokens(chunk) <= max_tokens:
            lo = mid
        else:
            hi = mid - 1
    if lo == 0:
        return text[: max(1, max_tokens * 4)].rstrip() + "..."
    return " ".join(words[:lo]).rstrip() + "..."


def _is_subsumed(shorter: str, longer: str, min_len: int = 80) -> bool:
    if len(shorter) < min_len or len(longer) < min_len:
        return shorter == longer and bool(shorter)
    return shorter in longer


def dedupe_results_by_text(
    results: List[Result],
    extract_text: Callable[[Any], str],
    *,
    min_subsumed_len: int = 80,
) -> List[Result]:
    """Drop duplicate or subsumed passages; keep highest-scoring survivor."""
    if not results:
        return []
    sorted_hits = sorted(results, key=lambda x: x[1], reverse=True)
    kept: List[Result] = []
    kept_norms: List[str] = []
    seen_fp: set = set()

    for node, score in sorted_hits:
        raw = extract_text(node)
        norm = normalize_for_dedupe(raw)
        if not norm:
            continue
        fp = text_fingerprint(raw)
        if fp in seen_fp:
            continue
        if any(
            _is_subsumed(norm, k, min_subsumed_len)
            or _is_subsumed(k, norm, min_subsumed_len)
            for k in kept_norms
        ):
            continue
        kept.append((node, score))
        kept_norms.append(norm)
        seen_fp.add(fp)

    kept.sort(key=lambda x: x[0].coordinates.t)
    return kept


def _embedding_similarity(a: Any, b: Any) -> Optional[float]:
    """Cosine similarity between two nodes' embeddings (dot product if normalized)."""
    emb_a = getattr(a, "embedding", None)
    emb_b = getattr(b, "embedding", None)
    if emb_a is None or emb_b is None:
        return None
    try:
        import numpy as np

        va = np.asarray(emb_a, dtype=np.float32)
        vb = np.asarray(emb_b, dtype=np.float32)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom <= 0:
            return None
        return float(np.dot(va, vb) / denom)
    except Exception:
        return None


def dedupe_results_by_embedding(
    results: List[Result],
    *,
    threshold: float = 0.92,
) -> List[Result]:
    """Drop near-duplicate passages by embedding similarity (after text dedupe)."""
    if not results:
        return []
    sorted_hits = sorted(results, key=lambda x: x[1], reverse=True)
    kept: List[Result] = []
    kept_nodes: List[Any] = []

    for node, score in sorted_hits:
        if getattr(node, "embedding", None) is None:
            kept.append((node, score))
            kept_nodes.append(node)
            continue
        is_dup = False
        for kn in kept_nodes:
            if getattr(kn, "embedding", None) is None:
                continue
            sim = _embedding_similarity(node, kn)
            if sim is not None and sim >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append((node, score))
            kept_nodes.append(node)

    kept.sort(key=lambda x: x[0].coordinates.t)
    return kept


def dedupe_results_for_context(
    results: List[Result],
    extract_text: Callable[[Any], str],
    *,
    embedding_threshold: float = 0.92,
) -> List[Result]:
    """Text dedupe then embedding near-duplicate removal."""
    text_deduped = dedupe_results_by_text(results, extract_text)
    return dedupe_results_by_embedding(text_deduped, threshold=embedding_threshold)

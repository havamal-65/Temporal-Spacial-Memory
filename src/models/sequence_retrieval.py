"""
Sequence-aware retrieval for the Narrative Atlas.

This module makes the temporal coordinate ``t`` an ORDERING axis instead of
only a filter or a soft scoring bias. It delivers the project's core promise:
using time to help an LLM understand narrative sequence.

It is intentionally composable (atomic architecture): a ``SequenceRetriever``
operates on an existing ``NarrativeAtlas`` -- reusing its ``SpatialTemporalDB``
coordinate-range queries, its embedding service, and its in-memory similarity
search -- rather than duplicating any of that logic. It deliberately avoids
importing ``NarrativeAtlas`` / ``Node`` at module load time so there is no
circular import; nodes are accessed by duck typing.

Public surface:
- ``detect_sequence_intent(query)``  -> route a query to timeline / neighbors / point
- ``fetch_timeline(...)``            -> passages in a t-range, returned in story order
- ``get_neighbors(...)``             -> what comes before/after an anchor passage
- ``assemble_sequence_context(...)`` -> t-ordered, page-labeled LLM context
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("SequenceRetriever")

# A retrieval result mirrors the rest of the atlas: (node, score).
Result = Tuple[Any, float]

# --- Intent detection patterns (deterministic, no LLM) -----------------------
# "after X" / "before X" with a captured anchor phrase route to neighbor lookup.
_AFTER_PAT = re.compile(r"\b(?:after|following|subsequent to)\b\s+(?P<anchor>.+)", re.IGNORECASE)
_BEFORE_PAT = re.compile(
    r"\b(?:before|prior to|leading up to|preceding|up until)\b\s+(?P<anchor>.+)", re.IGNORECASE
)
# Phrases that signal a request for ordered / chronological coverage.
_TIMELINE_KEYWORDS = (
    "chronological", "in order", "timeline", "sequence of", "order of events",
    "step by step", "beginning to end", "start to finish", "over the course",
    "throughout the",
)
_TIMELINE_PAT = re.compile(
    r"\b(?:summar(?:y|ize|ise)|list|trace|outline|walk me through|recap)\b.*\b(?:events?|story|plot|happenings?)\b",
    re.IGNORECASE,
)


def _clean_anchor(text: str) -> str:
    """Normalize a captured anchor phrase into a searchable noun phrase."""
    text = text.strip().strip("?.!,").strip()
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


class SequenceRetriever:
    """Time-ordered retrieval helpers layered on top of a ``NarrativeAtlas``."""

    def __init__(self, atlas: Any):
        # Duck-typed: requires atlas.db (SpatialTemporalDB), atlas.embedding_service,
        # and atlas.find_similar_nodes. No NarrativeAtlas import needed.
        self.atlas = atlas

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_sequence_intent(query: str) -> Dict[str, Optional[str]]:
        """Classify a query into a retrieval mode using keyword/regex rules.

        Returns a dict with keys:
          - mode:      'neighbors' | 'timeline' | 'point'
          - direction: 'before' | 'after' | 'both' | None
          - anchor:    cleaned anchor phrase for neighbor lookups, else None

        Keyword-based on purpose: it is deterministic and does not depend on the
        (small, sometimes-unreliable) local LLM, complementing the LLM-based
        t_min/t_max extraction already done by the NL parser.
        """
        q = (query or "").strip()
        if not q:
            return {"mode": "point", "direction": None, "anchor": None}

        match = _AFTER_PAT.search(q)
        if match:
            anchor = _clean_anchor(match.group("anchor"))
            if anchor:
                return {"mode": "neighbors", "direction": "after", "anchor": anchor}

        match = _BEFORE_PAT.search(q)
        if match:
            anchor = _clean_anchor(match.group("anchor"))
            if anchor:
                return {"mode": "neighbors", "direction": "before", "anchor": anchor}

        lowered = q.lower()
        if any(kw in lowered for kw in _TIMELINE_KEYWORDS) or _TIMELINE_PAT.search(q):
            return {"mode": "timeline", "direction": "both", "anchor": None}

        return {"mode": "point", "direction": None, "anchor": None}

    # ------------------------------------------------------------------
    # Timeline retrieval
    # ------------------------------------------------------------------

    def fetch_timeline(
        self,
        t_min: Optional[float] = None,
        t_max: Optional[float] = None,
        query: Optional[str] = None,
        k: int = 20,
        semantic_threshold: Optional[float] = None,
    ) -> List[Result]:
        """Return passages within a t-range, sorted ascending by ``t`` (story order).

        When ``query`` is given, candidates are first ranked by embedding
        similarity (optionally filtered by ``semantic_threshold``) and the top
        ``k`` are kept, then re-sorted by ``t`` so the most relevant passages are
        presented in narrative order. Without ``query`` the earliest ``k``
        passages in the range are returned in order.
        """
        ids = self.atlas.db.query_by_coordinate_range(t_min=t_min, t_max=t_max)
        nodes = [self.atlas.db.nodes[nid] for nid in ids if nid in self.atlas.db.nodes]
        if not nodes:
            return []

        if query:
            scored = self._score_nodes(nodes, query)
            if semantic_threshold is not None:
                scored = [(n, s) for n, s in scored if s >= semantic_threshold]
            scored.sort(key=lambda x: x[1], reverse=True)
            chosen = scored[:k]
        else:
            nodes.sort(key=lambda n: n.coordinates.t)
            chosen = [(n, 0.0) for n in nodes[:k]]

        chosen.sort(key=lambda x: x[0].coordinates.t)
        return chosen

    # ------------------------------------------------------------------
    # Neighbor (before / after) retrieval
    # ------------------------------------------------------------------

    def get_neighbors(
        self,
        anchor: Any,
        direction: str = "both",
        window: float = 5.0,
        k: int = 10,
    ) -> List[Result]:
        """Return passages temporally adjacent to an anchor, in story order.

        ``anchor`` may be a node id, a node, or free text (resolved to the most
        similar node). The result includes the anchor itself (score 1.0) so the
        LLM can see the reference point in sequence; neighbors carry score 0.0.
        """
        anchor_node = self.resolve_anchor(anchor)
        if anchor_node is None:
            logger.info("get_neighbors: could not resolve anchor %r", anchor)
            return []

        t0 = anchor_node.coordinates.t
        lo = t0 - window if direction in ("before", "both") else t0
        hi = t0 + window if direction in ("after", "both") else t0

        ids = self.atlas.db.query_by_coordinate_range(t_min=lo, t_max=hi)
        nodes = [self.atlas.db.nodes[nid] for nid in ids if nid in self.atlas.db.nodes]
        if not nodes:
            return []

        # Keep the k passages closest in time to the anchor, then present in t order.
        nodes.sort(key=lambda n: abs(n.coordinates.t - t0))
        nodes = nodes[:k]
        nodes.sort(key=lambda n: n.coordinates.t)
        return [(n, 1.0 if n.id == anchor_node.id else 0.0) for n in nodes]

    def resolve_anchor(self, anchor: Any) -> Optional[Any]:
        """Resolve an anchor (node, node id, or text) to a concrete node."""
        if anchor is None:
            return None
        # A node-like object already.
        if hasattr(anchor, "coordinates") and hasattr(anchor, "id"):
            return anchor
        if isinstance(anchor, str):
            if anchor in self.atlas.db.nodes:
                return self.atlas.db.nodes[anchor]
            resolved = self.resolve_ref(anchor)
            if resolved is not None:
                return resolved
        results = self.atlas.find_similar_nodes(str(anchor), k=1)
        return results[0][0] if results else None

    # ------------------------------------------------------------------
    # Addressable reference resolution and text windows
    # ------------------------------------------------------------------

    @staticmethod
    def parse_ref(ref: str) -> Optional[Tuple[str, int, int]]:
        """Parse ``doc_id:page:para`` (para is 1-based in the ref string)."""
        if not ref:
            return None
        parts = ref.strip().split(":")
        if len(parts) < 3:
            return None
        try:
            page = int(parts[-2])
            para = int(parts[-1])
            doc_id = ":".join(parts[:-2])
            return doc_id, page, para
        except ValueError:
            return None

    def resolve_ref(self, ref: str) -> Optional[Any]:
        """Look up a segment node by its human-readable reference."""
        parsed = self.parse_ref(ref)
        if not parsed:
            return None
        doc_id, page, para = parsed
        node_id = f"segment:{doc_id}:{page}:{para}"
        return self.atlas.db.nodes.get(node_id)

    def get_text_window(
        self,
        ref_or_node: Any,
        before: int = 1,
        after: int = 1,
        segment_only: bool = True,
    ) -> List[Result]:
        """Return segment nodes surrounding a reference, in t-ascending order."""
        anchor = self.resolve_ref(ref_or_node) if isinstance(ref_or_node, str) else ref_or_node
        if anchor is None and isinstance(ref_or_node, str):
            anchor = self.atlas.db.nodes.get(ref_or_node)
        if anchor is None or not hasattr(anchor, "coordinates"):
            return []

        parsed = None
        content = getattr(anchor, "content", {}) or {}
        ref_str = content.get("ref") if isinstance(content, dict) else None
        if ref_str:
            parsed = self.parse_ref(ref_str)
        if parsed is None and anchor.id.startswith("segment:"):
            parts = anchor.id.split(":")
            if len(parts) >= 4:
                try:
                    parsed = (parts[1], int(parts[2]), int(parts[3]))
                except ValueError:
                    pass

        if parsed is None:
            return [(anchor, 1.0)]

        doc_id, page, para = parsed
        candidates: List[Any] = []
        for delta in range(-before, after + 1):
            p = para + delta
            if p < 1:
                continue
            nid = f"segment:{doc_id}:{page}:{p}"
            node = self.atlas.db.nodes.get(nid)
            if node is not None:
                if segment_only and getattr(node, "type", None) != "segment":
                    continue
                candidates.append(node)

        if not candidates:
            return [(anchor, 1.0)]

        candidates.sort(key=lambda n: n.coordinates.t)
        return [(n, 1.0 if n.id == anchor.id else 0.0) for n in candidates]

    def expand_results_with_refs(
        self,
        results: List[Result],
        before: int = 1,
        after: int = 1,
    ) -> List[Result]:
        """Expand entity hits via source_refs into surrounding segment prose."""
        seen_ids: set = set()
        expanded: List[Result] = []
        for node, score in results:
            refs: List[str] = []
            content = getattr(node, "content", {}) or {}
            meta = getattr(node, "metadata", {}) or {}
            if isinstance(content, dict):
                refs.extend(content.get("source_refs") or [])
            if isinstance(meta, dict):
                refs.extend(meta.get("source_refs") or [])
            refs = list(dict.fromkeys(refs))  # dedupe, preserve order

            if refs and getattr(node, "type", None) != "segment":
                for ref in refs[:2]:
                    for seg, seg_score in self.get_text_window(ref, before=before, after=after):
                        if seg.id not in seen_ids:
                            seen_ids.add(seg.id)
                            expanded.append((seg, max(score, seg_score)))
            elif node.id not in seen_ids:
                seen_ids.add(node.id)
                expanded.append((node, score))

        expanded.sort(key=lambda x: x[0].coordinates.t)
        return expanded

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def assemble_sequence_context(
        self,
        results: List[Result],
        max_chars_per_passage: int = 400,
        max_total_chars: int = 3000,
        max_tokens_per_passage: Optional[int] = None,
        max_total_tokens: Optional[int] = None,
    ) -> str:
        """Build t-ordered, page-labeled context for an LLM.

        Sorting by ``t`` and labeling each block with its sequence position and
        page makes the narrative ordering explicit to the model. Prefer
        ``max_total_tokens`` / ``max_tokens_per_passage`` when set; otherwise
        falls back to character caps.
        """
        from src.utils.token_budget import count_tokens, trim_text_to_tokens

        ordered = sorted(results, key=lambda x: x[0].coordinates.t)
        total_passages = len(ordered)
        parts: List[str] = []
        running_chars = 0
        running_tokens = 0
        use_tokens = max_total_tokens is not None and max_total_tokens > 0

        for i, (node, _score) in enumerate(ordered):
            t = node.coordinates.t
            page = int(t)
            ref = self._node_ref(node)
            text = self._extract_text(node)

            if use_tokens and max_tokens_per_passage:
                text = trim_text_to_tokens(text, max_tokens_per_passage)
            elif len(text) > max_chars_per_passage:
                text = text[:max_chars_per_passage].rstrip() + "..."

            if ref:
                label = f"[Passage {i + 1} of {total_passages} - {ref} page {page} (t={t:.2f})]"
            else:
                label = f"[Passage {i + 1} of {total_passages} - page {page} (t={t:.2f})]"
            block = f"{label}\n{text}\n"

            if use_tokens:
                block_tokens = count_tokens(block)
                if running_tokens + block_tokens > max_total_tokens and parts:
                    break
                parts.append(block)
                running_tokens += block_tokens
            else:
                if running_chars + len(block) > max_total_chars and parts:
                    break
                parts.append(block)
                running_chars += len(block)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_nodes(self, nodes: List[Any], query: str) -> List[Result]:
        """Embed the query once and score each node by dot-product similarity."""
        query_emb = np.asarray(self.atlas.embedding_service.embed_query(query), dtype=np.float32)
        scored: List[Result] = []
        for node in nodes:
            if getattr(node, "embedding", None) is not None:
                scored.append((node, float(np.dot(query_emb, node.embedding))))
        return scored

    @staticmethod
    def _node_ref(node: Any) -> Optional[str]:
        content = getattr(node, "content", None)
        if isinstance(content, dict) and content.get("ref"):
            return str(content["ref"])
        meta = getattr(node, "metadata", None)
        if isinstance(meta, dict) and meta.get("ref"):
            return str(meta["ref"])
        return None

    @staticmethod
    def _extract_text(node: Any) -> str:
        """Best-effort human-readable text for a node's content."""
        content = getattr(node, "content", None)
        if isinstance(content, dict):
            for key in ("text", "description", "name"):
                value = content.get(key)
                if value:
                    return value if isinstance(value, str) else json.dumps(value)
            return json.dumps(content)
        return str(content)

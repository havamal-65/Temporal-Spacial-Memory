"""
Composable helpers for merging and diversifying retrieval result lists.

Used by NarrativeAtlas._retrieve_for_query to combine hybrid search, MMR,
and region-scoped timeline fetches so questions with several valid answers
(e.g. multiple perils on a journey) surface distinct passages.
"""

import re
from typing import Any, List, Optional, Tuple

Result = Tuple[Any, float]

# (keyword fragments, t_min, t_max) — narrative region hints from query text.
_REGION_HINTS: List[Tuple[Tuple[str, ...], float, float]] = [
    (("misty", "mountain"), 55.0, 110.0),
    (("mountain", "path"), 55.0, 110.0),
    (("beorn",), 118.0, 150.0),
    (("skin-changer",), 120.0, 150.0),
    (("skin", "changer"), 120.0, 150.0),
    (("mirkwood", "forest"), 140.0, 200.0),
    (("lonely mountain",), 200.0, 305.0),
    (("erebor",), 200.0, 305.0),
    (("smaug",), 200.0, 305.0),
    (("dragon",), 200.0, 305.0),
    (("arkenstone",), 220.0, 305.0),
    (("jewel",), 220.0, 305.0),
    (("dwarves", "treasure"), 200.0, 305.0),
    (("dwarves", "seeking"), 200.0, 305.0),
    # Generic journey-mountain hint last — "mountain" alone also appears in
    # treasure questions ("which mountain was it in?").
    (("mountain",), 55.0, 110.0),
]

# t-ranges for the Lonely Mountain / Erebor story arc (treasure, Smaug, Arkenstone).
_EREBOR_T_RANGES = frozenset({(200.0, 305.0), (220.0, 305.0)})

_ENUMERATION_RE = re.compile(
    r"\b(?:meet|meets|met|encounter|encounters|face|faces|avoid|avoiding|"
    r"dangers?|perils?|threats?|enemies|what.*(?:happened|happen))\b",
    re.IGNORECASE,
)


def query_suggests_enumeration(query: str) -> bool:
    """True when the user likely expects a list of distinct items/events."""
    return bool(_ENUMERATION_RE.search(query or ""))


def region_t_range(query: str) -> Optional[Tuple[float, float]]:
    """Infer a t-range window from place/journey keywords in the query."""
    lowered = (query or "").lower()
    matches: List[Tuple[int, Tuple[float, float], Tuple[str, ...]]] = []
    for fragments, t_min, t_max in _REGION_HINTS:
        if all(frag in lowered for frag in fragments):
            matches.append((len(fragments), (t_min, t_max), fragments))

    if not matches:
        return None

    best_specificity = max(m[0] for m in matches)
    tied = [m for m in matches if m[0] == best_specificity]
    if len(tied) == 1:
        return tied[0][1]

    # e.g. "jewel" + generic "mountain" both match at specificity 1 — prefer Erebor.
    for _spec, rng, _frags in tied:
        if rng in _EREBOR_T_RANGES:
            return rng
    return tied[0][1]


def expansion_queries(
    query: str,
    region: Optional[Tuple[float, float]] = None,
) -> List[str]:
    """Extra search strings to pull distinct hazard/entity mentions."""
    if not query_suggests_enumeration(query):
        return []
    if region is not None:
        # Stay on vocabulary that appears inside the inferred narrative region.
        return [
            f"{query} goblins cave tunnels",
            f"{query} stone giants thunder storm lightning",
            f"{query} narrow paths cliffs falling snow",
        ]
    return [
        f"{query} goblins orcs wargs",
        f"{query} giants thunder storm",
        f"{query} wolves eagles",
    ]


# Keyword groups — if retrieval misses one theme, scan region segments for it.
_JOURNEY_HAZARD_THEMES: List[Tuple[str, Tuple[str, ...]]] = [
    ("goblins", ("goblin", "goblin-town")),
    ("giants_storm", ("giant", "thunder", "storm", "lightning", "crash")),
]

_BEORN_THEMES: List[Tuple[str, Tuple[str, ...]]] = [
    ("skin_changer", ("skin-changer", "skin changer")),
    ("bear_form", ("bear", "skin-changer")),
]

_ARKENSTONE_THEMES: List[Tuple[str, Tuple[str, ...]]] = [
    ("arkenstone", ("arkenstone",)),
    ("smaug_treasure", ("smaug", "treasure", "hoard")),
    ("bilbo_theft", ("thief in the night", "thief")),
]


def themes_for_query(query: str) -> List[Tuple[str, Tuple[str, ...]]]:
    """Theme keyword groups to inject when retrieval misses a facet of the answer."""
    lowered = (query or "").lower()
    if "beorn" in lowered or "skin-changer" in lowered or "skin changer" in lowered:
        return _BEORN_THEMES
    if "arkenstone" in lowered or "smaug" in lowered or "jewel" in lowered:
        return _ARKENSTONE_THEMES
    if query_suggests_enumeration(query):
        return _JOURNEY_HAZARD_THEMES
    return []


def inject_theme_coverage(
    results: List[Result],
    candidates: List[Any],
    extract_text: Any,
    themes: Optional[List[Tuple[str, Tuple[str, ...]]]] = None,
) -> List[Result]:
    """Ensure at least one hit per hazard theme when passages exist in candidates."""
    theme_list = themes or _JOURNEY_HAZARD_THEMES
    seen = {n.id for n, _ in results}
    augmented = list(results)

    def _blob(nodes: List[Result]) -> str:
        return " ".join(extract_text(n).lower() for n, _ in nodes)

    blob = _blob(augmented)
    for _label, keywords in theme_list:
        if any(kw in blob for kw in keywords):
            continue
        for node in candidates:
            if node.id in seen:
                continue
            text = extract_text(node).lower()
            if any(kw in text for kw in keywords):
                augmented.append((node, 0.72))
                seen.add(node.id)
                blob = _blob(augmented)
                break
    return augmented


def filter_to_region(
    results: List[Result],
    t_min: float,
    t_max: float,
    k: int,
    *,
    strict: bool = False,
) -> List[Result]:
    """Prefer hits whose narrative time falls inside [t_min, t_max]."""
    in_region = [(n, s) for n, s in results if t_min <= n.coordinates.t <= t_max]
    ranked = sorted(in_region, key=lambda x: x[1], reverse=True)
    if strict:
        if ranked:
            return ranked[:k]
        return sorted(results, key=lambda x: x[1], reverse=True)[:k]
    if len(ranked) >= k:
        return ranked[:k]
    seen = {n.id for n, _ in ranked}
    backfill = [(n, s) for n, s in results if n.id not in seen]
    merged = ranked + sorted(backfill, key=lambda x: x[1], reverse=True)
    return merged[:k]


def merge_result_lists(*lists: List[Result], k: int) -> List[Result]:
    """Dedupe by node id, keep best score, return top k."""
    best: dict = {}
    for results in lists:
        for node, score in results:
            nid = node.id
            if nid not in best or score > best[nid][1]:
                best[nid] = (node, score)
    merged = sorted(best.values(), key=lambda x: x[1], reverse=True)
    return merged[:k]


def spread_by_time(results: List[Result], k: int, min_t_gap: float = 3.0) -> List[Result]:
    """Prefer high-scoring hits spread across narrative time (t axis)."""
    if not results:
        return []
    sorted_hits = sorted(results, key=lambda x: x[1], reverse=True)
    chosen: List[Result] = []
    chosen_ts: List[float] = []

    for node, score in sorted_hits:
        t = node.coordinates.t
        if any(abs(t - ct) < min_t_gap for ct in chosen_ts):
            continue
        chosen.append((node, score))
        chosen_ts.append(t)
        if len(chosen) >= k:
            return chosen

    # Fill remaining slots if t-spread was too strict
    seen = {n.id for n, _ in chosen}
    for node, score in sorted_hits:
        if node.id in seen:
            continue
        chosen.append((node, score))
        if len(chosen) >= k:
            break
    return chosen

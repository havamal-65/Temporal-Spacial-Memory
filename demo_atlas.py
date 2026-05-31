#!/usr/bin/env python3
"""
Temporal-Spatial Memory System - End-to-End Demo

Loads the Hobbit SQLite+FAISS atlas (399 nodes, 8 semantic sectors) and runs
three illustrative query types against the live data:

  1. Sector-filtered semantic search  (no LLM required)
  2. Coordinate range filter          (no LLM required)
  3. NL query with sector augmentation (requires an LLM provider; local by default)

Usage:
    python demo_atlas.py
    python demo_atlas.py --atlas output/db_debug_all --k 5
"""

import os
import sys
import math
import argparse
import logging
from collections import Counter
from typing import List, Tuple

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from src.models.narrative_atlas import NarrativeAtlas, Node
from src.utils.embedding_service import create_embedding_service
from src.nl_parser import CoordinateFilters
from src.utils.semantic_compass import SemanticCompassMapper
from src.utils.llm_factory import llm_is_available

logging.basicConfig(level=logging.WARNING)  # suppress library chatter during demo

SECTOR_LABELS = {
    "N":  "Action / Adventure",
    "NE": "Technical / Instructional",
    "E":  "Scientific / Analytical",
    "SE": "Educational / Reference",
    "S":  "Creative / Artistic",
    "SW": "Personal / Lifestyle",
    "W":  "Historical / Reflective",
    "NW": "Philosophical / Abstract",
}

HALF_SECTOR = math.pi / 8  # half-width of one sector slice


def _theta_to_sector(theta: float) -> str:
    angles = SemanticCompassMapper.SECTOR_ANGLES
    best, best_dist = "N", float("inf")
    for name, center in angles.items():
        dist = abs((theta - center + math.pi) % (2 * math.pi) - math.pi)
        if dist < best_dist:
            best, best_dist = name, dist
    return best


def _excerpt(node: Node, max_chars: int = 120) -> str:
    c = node.content
    text = c.get("text") or c.get("description") or c.get("name") or str(c)
    text = text.replace("\n", " ").strip()
    return text[:max_chars] + "..." if len(text) > max_chars else text


def _print_results(results: List[Tuple[Node, float]]) -> None:
    if not results:
        print("  (no results)")
        return
    for rank, (node, score) in enumerate(results, 1):
        coords = node.coordinates
        sector = _theta_to_sector(coords.theta)
        print(
            f"  {rank}. [{sector:2s}] r={coords.r:.2f} t={coords.t:.2f}"
            f"  score={score:.3f}  {node.type}"
        )
        print(f"     {_excerpt(node)}")


# ------------------------------------------------------------------------------
# 1. Atlas overview
# ------------------------------------------------------------------------------

def show_overview(atlas: NarrativeAtlas) -> None:
    nodes = list(atlas.db.nodes.values())
    t_vals = [n.coordinates.t for n in nodes]
    r_vals = [n.coordinates.r for n in nodes]
    sector_counts = Counter(_theta_to_sector(n.coordinates.theta) for n in nodes)
    type_counts = Counter(n.type for n in nodes)

    print("\n" + "=" * 60)
    print(f"  ATLAS OVERVIEW  ({len(nodes)} nodes)")
    print("=" * 60)
    print(f"  Temporal range  t in [{min(t_vals):.2f}, {max(t_vals):.2f}]")
    print(f"  Radius range    r in [{min(r_vals):.2f}, {max(r_vals):.2f}]")
    print(f"  Node types      {dict(type_counts)}")
    print()
    print("  Sector distribution:")
    for s in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        bar = "#" * (sector_counts.get(s, 0) // 5)
        print(f"    {s:2s}  {SECTOR_LABELS[s]:<30s}  {sector_counts.get(s, 0):3d}  {bar}")


# ------------------------------------------------------------------------------
# 2. Sector-filtered search
# ------------------------------------------------------------------------------

SECTOR_QUERIES = [
    ("battle between armies sword fighting",        None,       "auto-detect -> N (action)"),
    ("ancient history of the dwarven kingdoms",     ["W"],      "explicit W (historical)"),
    ("beautiful song and poetry of the elves",      ["S"],      "explicit S (creative)"),
    ("historical fiction legends and narrative",    ["W", "S"], "SQL OR: W + S sectors"),
]


def demo_sector_search(atlas: NarrativeAtlas, k: int) -> None:
    print("\n" + "=" * 60)
    print("  DEMO 1 - Sector-Filtered Semantic Search")
    print("=" * 60)

    for query, sectors, label in SECTOR_QUERIES:
        print(f"\n  Query : \"{query}\"")
        print(f"  Mode  : {label}")
        results = atlas.search_with_sector_filter(query, sectors=sectors, k=k)
        _print_results(results)


# ------------------------------------------------------------------------------
# 3. Coordinate range filter
# ------------------------------------------------------------------------------

def demo_coordinate_filter(atlas: NarrativeAtlas, k: int) -> None:
    print("\n" + "=" * 60)
    print("  DEMO 2 - Coordinate Range Filter")
    print("=" * 60)

    nodes = list(atlas.db.nodes.values())
    t_vals = [n.coordinates.t for n in nodes]
    t_min_all, t_max_all = min(t_vals), max(t_vals)
    t_span = t_max_all - t_min_all

    slices = [
        ("early chapters  (t <= 30%)",   t_min_all,              t_min_all + t_span * 0.30),
        ("middle section (30-70%)",     t_min_all + t_span * 0.30, t_min_all + t_span * 0.70),
        ("final chapters  (t >= 70%)",   t_min_all + t_span * 0.70, t_max_all),
    ]

    query = "dragon treasure mountain danger"

    for label, t_lo, t_hi in slices:
        filters = CoordinateFilters(t_min=t_lo, t_max=t_hi)
        matching_ids = atlas._get_ids_matching_filters(filters)

        print(f"\n  Query  : \"{query}\"")
        print(f"  Filter : {label}  ->  {len(matching_ids)} candidate nodes")

        if not matching_ids:
            print("  (no nodes in this range)")
            continue

        # Rank candidates by embedding similarity
        query_emb = atlas.embedding_service.embed_query(query)
        import numpy as np
        query_emb = np.array(query_emb)
        scored = []
        for nid in matching_ids:
            node = atlas.db.nodes[nid]
            if node.embedding is not None:
                sim = float(np.dot(query_emb, node.embedding))
                scored.append((node, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        _print_results(scored[:k])


# ------------------------------------------------------------------------------
# 4. NL query with sector augmentation (optional - needs OPENAI_API_KEY)
# ------------------------------------------------------------------------------

NL_QUERIES = [
    "Who are the dwarves in the quest?",
    "What happens when Bilbo finds the ring?",
    "Tell me about the battle in the final act",
]


def demo_nl_query(atlas: NarrativeAtlas, k: int) -> None:
    print("\n" + "=" * 60)
    print("  DEMO 3 - NL Query with Sector Augmentation")
    print("=" * 60)

    if not llm_is_available():
        print("\n  Skipped - no LLM provider available.")
        print("  Set LLM_PROVIDER=local with a running local server (Ollama/LM Studio),")
        print("  or LLM_PROVIDER=openai with OPENAI_API_KEY, to enable NL parsing.")
        return

    for nl_query in NL_QUERIES:
        print(f"\n  Query : \"{nl_query}\"")
        results = atlas.search_with_nl_query(nl_query, k=k)
        _print_results(results)


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Temporal-Spatial Memory Demo")
    parser.add_argument(
        "--atlas",
        default=os.path.join(os.path.dirname(__file__), "output", "db_debug_all"),
        help="Path to the atlas storage directory (default: output/db_debug_all)",
    )
    parser.add_argument("--k", type=int, default=4, help="Results per query (default: 4)")
    args = parser.parse_args()

    if not os.path.isdir(args.atlas):
        print(f"ERROR: Atlas path not found: {args.atlas}")
        print("Run the migration first:  python migrate_to_sqlite.py")
        sys.exit(1)

    print(f"Loading atlas from: {args.atlas}")
    emb_svc = create_embedding_service("langchain")
    atlas = NarrativeAtlas(storage_path=args.atlas, embedding_service=emb_svc)

    show_overview(atlas)
    demo_sector_search(atlas, k=args.k)
    demo_coordinate_filter(atlas, k=args.k)
    demo_nl_query(atlas, k=args.k)

    print("\n" + "=" * 60)
    print("  Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

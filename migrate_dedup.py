#!/usr/bin/env python3
"""One-time dedup migration: collapse duplicate nodes (same content) in the live atlas.

Run once against the Hobbit SQLite database to remove content-identical nodes that
were created when the same event description appeared on multiple PDF pages during
ingest.  The node with the lexicographically smallest id is kept for each duplicate
group; all others are deleted.

Usage:
    python migrate_dedup.py
    python migrate_dedup.py --atlas output/db_debug_all
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.WARNING)

from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Dedup migration for Narrative Atlas")
    parser.add_argument(
        "--atlas",
        default=os.path.join(os.path.dirname(__file__), "output", "db_debug_all"),
        help="Path to the atlas storage directory (default: output/db_debug_all)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.atlas):
        print(f"ERROR: Atlas path not found: {args.atlas}")
        sys.exit(1)

    print(f"Loading atlas from: {args.atlas}")
    emb_svc = create_embedding_service("langchain")
    atlas = NarrativeAtlas(storage_path=args.atlas, embedding_service=emb_svc)

    before = len(atlas.db.nodes)
    removed = atlas.dedup_nodes()
    after = len(atlas.db.nodes)
    print(f"Dedup complete: {before} -> {after} nodes ({removed} duplicates removed)")


if __name__ == "__main__":
    main()

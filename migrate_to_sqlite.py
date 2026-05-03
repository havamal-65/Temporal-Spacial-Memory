"""
Migrate existing pickle-based atlas to SQLite with semantic compass theta values.

Loads the 399 Hobbit nodes from output/db_debug_all/spatial_temporal_db.pkl,
re-assigns theta using SemanticCompassMapper (from each node's existing 384-dim
embedding), computes r from embedding norm, and writes a fresh NarrativeAtlas
to output/db_debug_all/ (SQLite + FAISS).

Run from project root:
    python migrate_to_sqlite.py
"""

import os
import sys
import pickle
import logging
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migration")

from src.utils.embedding_service import LangchainEmbeddingService
from src.utils.semantic_compass import SemanticCompassMapper
from src.models.narrative_atlas import NarrativeAtlas
from src.data_models import PolarTemporalCoordinate

PKL_PATH = (
    "output/db_debug_all/spatial_temporal_db.pkl.pre_migration_backup"
    if os.path.exists("output/db_debug_all/spatial_temporal_db.pkl.pre_migration_backup")
    else "output/db_debug_all/spatial_temporal_db.pkl"
)
OUTPUT_PATH = "output/db_debug_all"


def _get_node_text(node) -> str:
    """Extract best text representation from a node for re-embedding."""
    content = node.content or {}
    return (
        content.get("text")
        or content.get("description")
        or content.get("name")
        or node.type
        or "unknown"
    )


def _coord_from_node(node, compass: SemanticCompassMapper, emb_svc=None) -> tuple:
    """Re-derive (r, theta) from the node's embedding; preserve t from old coords.

    Returns (PolarTemporalCoordinate, embedding_array) so the caller can store
    a valid (non-zero) embedding in FAISS.
    """
    emb = node.embedding
    old_coords = node.coordinates if isinstance(node.coordinates, dict) else {}

    t = old_coords.get("t", 0.0) if isinstance(old_coords, dict) else getattr(old_coords, "t", 0.0)

    # Detect zero / missing embeddings and re-compute from text content.
    is_zero = (emb is None or emb.size == 0 or float(np.linalg.norm(emb)) < 1e-9)
    if is_zero and emb_svc is not None:
        text = _get_node_text(node)
        emb = np.array(emb_svc.embed_query(text), dtype=np.float32)

    if emb is not None and emb.size > 0:
        norm = float(np.linalg.norm(emb))
        r = max(0.05, min(norm, 5.0))
        _, theta = compass.embedding_to_sector(emb)
    else:
        r = 1.0
        theta = 0.0

    return PolarTemporalCoordinate(r=r, theta=theta, t=t, z=0.0, z_type="DEFAULT"), emb


def main():
    logger.info("Loading existing pickle: %s", PKL_PATH)
    with open(PKL_PATH, "rb") as f:
        old_nodes: dict = pickle.load(f)
    logger.info("Loaded %d nodes", len(old_nodes))

    logger.info("Initialising sentence-transformer (all-MiniLM-L6-v2)…")
    emb_svc = LangchainEmbeddingService(
        model_provider="sentence_transformer",
        model_name="all-MiniLM-L6-v2",
        cache_dir="./cache/embeddings",
    )

    logger.info("Initialising SemanticCompassMapper…")
    compass = SemanticCompassMapper(emb_svc)

    logger.info("Creating fresh NarrativeAtlas at %s", OUTPUT_PATH)
    # Remove stale pkl so NarrativeAtlas.load() doesn't try to re-migrate it
    stale_pkl = os.path.join(OUTPUT_PATH, "spatial_temporal_db.pkl")
    if os.path.exists(stale_pkl):
        os.rename(stale_pkl, stale_pkl + ".pre_migration_backup")
        logger.info("Renamed stale pkl to .pre_migration_backup")

    # Remove previous SQLite and FAISS files so we start clean (avoids duplicate
    # FAISS entries and stale zero-vector embeddings from a prior migration run).
    for stale in ["nodes.sqlite", "vector_index.faiss", "vector_index.pkl"]:
        stale_path = os.path.join(OUTPUT_PATH, stale)
        if os.path.exists(stale_path):
            os.remove(stale_path)
            logger.info("Removed stale file: %s", stale)

    atlas = NarrativeAtlas(storage_path=OUTPUT_PATH, embedding_service=emb_svc)

    sector_counts: dict = {}
    reembedded = 0
    errors = 0

    for i, (nid, node) in enumerate(old_nodes.items()):
        try:
            coords, emb = _coord_from_node(node, compass, emb_svc)

            was_zero = (node.embedding is None
                        or node.embedding.size == 0
                        or float(np.linalg.norm(node.embedding)) < 1e-9)
            if was_zero:
                reembedded += 1

            ANGLE_TO_SECTOR = {
                0.0: "N", 0.785: "NE", 1.571: "E", 2.356: "SE",
                3.142: "S", 3.927: "SW", 4.712: "W", 5.498: "NW",
            }
            sector = ANGLE_TO_SECTOR.get(round(coords.theta, 3), f"{coords.theta:.3f}")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

            content = node.content or {}
            atlas.add_node(
                node_id=node.id,
                content=content,
                embedding=emb,
                metadata=node.metadata or {"node_type": node.type},
                coordinates=coords,
            )

            if (i + 1) % 50 == 0:
                logger.info("  %d / %d nodes migrated", i + 1, len(old_nodes))

        except Exception as e:
            logger.error("Failed to migrate node %s: %s", nid, e)
            errors += 1

    atlas.save()

    logger.info("Migration complete.")
    logger.info("  Total nodes: %d  (errors: %d, re-embedded: %d)", len(atlas.db.nodes), errors, reembedded)
    logger.info("  Sector distribution:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 2)
        logger.info("    %-6s %3d  %s", sector, count, bar)


if __name__ == "__main__":
    main()

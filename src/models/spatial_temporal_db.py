import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


class SpatialTemporalDB:
    """
    SQLite-backed node store with in-memory cache.

    self.nodes mirrors the SQLite table so callers in NarrativeAtlas can
    continue using dict-style reads (self.db.nodes[id], iteration, etc.)
    without any changes.  All writes go through add_node() which updates
    both the cache and the database atomically.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.nodes: Dict[str, Any] = {}
        self._db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id              TEXT PRIMARY KEY,
                type            TEXT NOT NULL,
                content         TEXT NOT NULL,
                r               REAL NOT NULL DEFAULT 0.0,
                theta           REAL NOT NULL DEFAULT 0.0,
                t               REAL NOT NULL DEFAULT 0.0,
                z               REAL NOT NULL DEFAULT 0.0,
                z_type          TEXT NOT NULL DEFAULT 'DEFAULT',
                embedding       BLOB,
                keywords        TEXT,
                metadata        TEXT NOT NULL DEFAULT '{}',
                parent_node_id  TEXT,
                timestamp       REAL NOT NULL DEFAULT 0.0,
                mapping_details TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_theta ON nodes(theta);
            CREATE INDEX IF NOT EXISTS idx_t     ON nodes(t);
            CREATE INDEX IF NOT EXISTS idx_r     ON nodes(r);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def _extract_coords(self, node: Any):
        """Return (r, theta, t, z, z_type) from a Node's coordinates field."""
        coords = node.coordinates
        if hasattr(coords, "r"):
            return coords.r, coords.theta, coords.t, coords.z, coords.z_type
        if isinstance(coords, dict):
            return (
                coords.get("r", 0.0),
                coords.get("theta", 0.0),
                coords.get("t", 0.0),
                coords.get("z", 0.0),
                coords.get("z_type", "DEFAULT"),
            )
        return 0.0, 0.0, 0.0, 0.0, "DEFAULT"

    def add_node(self, node: Any) -> None:
        """Upsert node into SQLite and update in-memory cache."""
        r, theta, t, z, z_type = self._extract_coords(node)
        emb_bytes = node.embedding.tobytes() if node.embedding is not None else None

        self._conn.execute(
            """INSERT OR REPLACE INTO nodes
               (id, type, content, r, theta, t, z, z_type,
                embedding, keywords, metadata, parent_node_id,
                timestamp, mapping_details)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                node.id,
                node.type,
                json.dumps(node.content),
                r, theta, t, z, z_type,
                emb_bytes,
                json.dumps(node.keywords) if node.keywords is not None else None,
                json.dumps(node.metadata),
                node.parent_node_id,
                node.timestamp,
                json.dumps(node.mapping_details),
            ),
        )
        self._conn.commit()
        self.nodes[node.id] = node

    def delete_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        self._conn.commit()
        del self.nodes[node_id]
        return True

    def clear_all(self) -> None:
        """Delete all rows and clear the in-memory cache."""
        self._conn.execute("DELETE FROM nodes")
        self._conn.commit()
        self.nodes.clear()

    # ------------------------------------------------------------------
    # SQL-accelerated coordinate range query
    # ------------------------------------------------------------------

    def query_by_coordinate_range(
        self,
        theta_min: Optional[float] = None,
        theta_max: Optional[float] = None,
        theta_ranges: Optional[List[Tuple[float, float]]] = None,
        r_min: Optional[float] = None,
        r_max: Optional[float] = None,
        t_min: Optional[float] = None,
        t_max: Optional[float] = None,
        z_min: Optional[float] = None,
        z_max: Optional[float] = None,
        z_type: Optional[str] = None,
    ) -> Set[str]:
        """Return node IDs matching all supplied coordinate constraints.

        theta_ranges (list of (lo, hi) pairs) takes precedence over theta_min/theta_max
        when provided and non-empty.  Each pair follows the same wrap-around convention
        as theta_min/theta_max: lo > hi signals the N-sector 0/2π crossing.
        An empty theta_ranges list is treated as no theta filter.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if theta_ranges:
            # Multi-range OR: one clause per sector, combined with OR.
            range_parts: List[str] = []
            for lo, hi in theta_ranges:
                if lo <= hi:
                    range_parts.append("theta BETWEEN ? AND ?")
                    params.extend([lo, hi])
                else:
                    range_parts.append("(theta >= ? OR theta <= ?)")
                    params.extend([lo, hi])
            conditions.append("(" + " OR ".join(range_parts) + ")")
        elif theta_min is not None and theta_max is not None:
            if theta_min <= theta_max:
                conditions.append("theta BETWEEN ? AND ?")
                params.extend([theta_min, theta_max])
            else:
                # N-sector wrap-around: theta >= theta_min OR theta <= theta_max
                conditions.append("(theta >= ? OR theta <= ?)")
                params.extend([theta_min, theta_max])
        elif theta_min is not None:
            conditions.append("theta >= ?")
            params.append(theta_min)
        elif theta_max is not None:
            conditions.append("theta <= ?")
            params.append(theta_max)

        if r_min is not None:
            conditions.append("r >= ?")
            params.append(r_min)
        if r_max is not None:
            conditions.append("r <= ?")
            params.append(r_max)
        if t_min is not None:
            conditions.append("t >= ?")
            params.append(t_min)
        if t_max is not None:
            conditions.append("t <= ?")
            params.append(t_max)
        if z_min is not None:
            conditions.append("z >= ?")
            params.append(z_min)
        if z_max is not None:
            conditions.append("z <= ?")
            params.append(z_max)
        if z_type is not None:
            conditions.append("z_type = ?")
            params.append(z_type)

        if not conditions:
            return set(self.nodes.keys())

        sql = "SELECT id FROM nodes WHERE " + " AND ".join(conditions)
        cursor = self._conn.execute(sql, params)
        return {row[0] for row in cursor.fetchall()}

    # ------------------------------------------------------------------
    # Persistence helpers (called from NarrativeAtlas.load / save)
    # ------------------------------------------------------------------

    def load_all_to_memory(self) -> List[dict]:
        """
        Return all persisted rows as plain dicts.
        NarrativeAtlas.load() reconstructs Node objects from these dicts
        and populates self.db.nodes via add_node().
        """
        cursor = self._conn.execute(
            "SELECT id, type, content, r, theta, t, z, z_type, "
            "embedding, keywords, metadata, parent_node_id, "
            "timestamp, mapping_details FROM nodes"
        )
        rows = []
        for row in cursor.fetchall():
            emb_bytes = row["embedding"]
            rows.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "content": json.loads(row["content"]),
                    "r": row["r"],
                    "theta": row["theta"],
                    "t": row["t"],
                    "z": row["z"],
                    "z_type": row["z_type"],
                    "embedding": (
                        np.frombuffer(emb_bytes, dtype=np.float32).copy()
                        if emb_bytes
                        else None
                    ),
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else None,
                    "metadata": json.loads(row["metadata"]),
                    "parent_node_id": row["parent_node_id"],
                    "timestamp": row["timestamp"],
                    "mapping_details": json.loads(row["mapping_details"]),
                }
            )
        return rows

    def dedup_by_content(self) -> int:
        """Remove duplicate nodes that share the same content JSON.

        For each group of duplicates, the node with the lexicographically smallest
        id is kept; all others are deleted from SQLite and the in-memory cache.
        Returns the number of rows deleted.
        """
        cursor = self._conn.execute("SELECT id, content FROM nodes ORDER BY id")
        rows = cursor.fetchall()

        seen: Dict[str, str] = {}  # content_hash -> first id
        to_delete: List[str] = []
        for row in rows:
            content_hash = hashlib.md5(row[1].encode()).hexdigest()
            if content_hash in seen:
                to_delete.append(row[0])
            else:
                seen[content_hash] = row[0]

        if to_delete:
            placeholders = ",".join("?" * len(to_delete))
            self._conn.execute(
                f"DELETE FROM nodes WHERE id IN ({placeholders})", to_delete
            )
            self._conn.commit()
            for node_id in to_delete:
                self.nodes.pop(node_id, None)

        return len(to_delete)

    def close(self) -> None:
        self._conn.close()

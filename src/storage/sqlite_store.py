import sqlite3
import json
from typing import List, Dict, Optional
from uuid import UUID
from pathlib import Path
from ..core.node_v2 import Node
from .node_store import NodeStore

class SQLiteNodeStore(NodeStore):
    """
    SQLite implementation of NodeStore for persistent node storage.
    Stores all node fields, serializing complex fields as JSON.
    """
    def __init__(self, db_path: str, timeout: float = 5.0):
        self.db_path = db_path
        self.timeout = timeout
        self._persistent_conn = None
        if db_path == ':memory:':
            self._persistent_conn = sqlite3.connect(db_path, timeout=timeout)
        self._ensure_table()

    def _get_conn(self):
        if self._persistent_conn is not None:
            return self._persistent_conn
        return sqlite3.connect(self.db_path, timeout=self.timeout)

    def _ensure_table(self):
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                content TEXT,
                position_time REAL,
                position_radius REAL,
                position_theta REAL,
                connections TEXT,
                origin_reference TEXT,
                delta_information TEXT,
                metadata TEXT
            )
            """
        )
        if self._persistent_conn is None:
            conn.close()

    def put(self, node: Node) -> None:
        data = node.to_dict()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes (
                    id, content, position_time, position_radius, position_theta, connections, origin_reference, delta_information, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(data['id']),
                    json.dumps(data['content']),
                    data['position'][0],
                    data['position'][1],
                    data['position'][2],
                    json.dumps(data['connections']),
                    data['origin_reference'],
                    json.dumps(data['delta_information']),
                    json.dumps(data['metadata'])
                )
            )

    def get(self, node_id: UUID) -> Optional[Node]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM nodes WHERE id = ?", (str(node_id),))
            row = cur.fetchone()
            if not row:
                return None
            data = {
                'id': row[0],
                'content': json.loads(row[1]),
                'position': (row[2], row[3], row[4]),
                'connections': json.loads(row[5]),
                'origin_reference': row[6],
                'delta_information': json.loads(row[7]),
                'metadata': json.loads(row[8])
            }
            return Node.from_dict(data)

    def delete(self, node_id: UUID) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM nodes WHERE id = ?", (str(node_id),))
            return cur.rowcount > 0

    def exists(self, node_id: UUID) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (str(node_id),))
            return cur.fetchone() is not None

    def list_ids(self) -> List[UUID]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT id FROM nodes")
            return [UUID(row[0]) for row in cur.fetchall()]

    def count(self) -> int:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM nodes")
            return cur.fetchone()[0]

    def get_many(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        if not node_ids:
            return {}
        placeholders = ','.join(['?'] * len(node_ids))
        with self._get_conn() as conn:
            cur = conn.execute(f"SELECT * FROM nodes WHERE id IN ({placeholders})", [str(nid) for nid in node_ids])
            result = {}
            for row in cur.fetchall():
                data = {
                    'id': row[0],
                    'content': json.loads(row[1]),
                    'position': (row[2], row[3], row[4]),
                    'connections': json.loads(row[5]),
                    'origin_reference': row[6],
                    'delta_information': json.loads(row[7]),
                    'metadata': json.loads(row[8])
                }
                node = Node.from_dict(data)
                result[node.id] = node
            return result

    def put_many(self, nodes: List[Node]) -> None:
        if not nodes:
            return
        with self._get_conn() as conn:
            conn.execute('BEGIN')
            for node in nodes:
                data = node.to_dict()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nodes (
                        id, content, position_time, position_radius, position_theta, connections, origin_reference, delta_information, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data['id']),
                        json.dumps(data['content']),
                        data['position'][0],
                        data['position'][1],
                        data['position'][2],
                        json.dumps(data['connections']),
                        data['origin_reference'],
                        json.dumps(data['delta_information']),
                        json.dumps(data['metadata'])
                    )
                )
            conn.commit()

    def close(self) -> None:
        # No persistent connection to close (using context managers)
        pass 
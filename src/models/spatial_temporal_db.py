from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class Node:
    node_id: str
    data: Dict[str, Any]
    created: datetime = field(default_factory=datetime.utcnow)


class SpatialTemporalDB:
    """Simple in-memory store mapping node_id -> Node."""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    # ------------------------------------------------------------------
    # Basic CRUD helpers
    # ------------------------------------------------------------------
    def add_node(self, node_id: str, data: Dict[str, Any]):
        self.nodes[node_id] = Node(node_id=node_id, data=data)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def delete_node(self, node_id: str) -> bool:
        """Remove node from DB; return True if removed."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    # Convenience for __contains__
    def __contains__(self, node_id: str) -> bool:
        return node_id in self.nodes

    def __len__(self):
        return len(self.nodes)

    # ------------------------------------------------------------------
    # Update & Query helpers
    # ------------------------------------------------------------------
    def update_node(self, node_id: str, **fields: Any) -> bool:
        """Patch fields inside the node's `data` dict. Returns True if updated."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.data.update(fields)
        return True

    def query_nodes(
        self,
        *,
        node_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Node]:
        """Return nodes matching optional type and creation time range."""
        results: Dict[str, Node] = {}
        for nid, node in self.nodes.items():
            if node_type and node.data.get("type") != node_type:
                continue
            if start_time and node.created < start_time:
                continue
            if end_time and node.created > end_time:
                continue
            results[nid] = node
        return results 
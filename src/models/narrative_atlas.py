import os
import json
import uuid
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import faiss

# Internal DB
from src.models.spatial_temporal_db import SpatialTemporalDB

# ---------------------------------------------------------------------------
# Helper: deterministic pseudo-random embedding based on text hash (avoids
# external API calls during tests). In production you can swap this out for
# a real embedding model such as OpenAIEmbeddings.
# ---------------------------------------------------------------------------

def _hash_embedding(text: str, dim: int = 128) -> np.ndarray:
    """Return a deterministic pseudo-random vector for the given text."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand/trim to the desired dimension
    needed_bytes = dim * 4  # float32 => 4 bytes each
    repeats = (needed_bytes // len(h)) + 1
    full_bytes = (h * repeats)[:needed_bytes]
    arr = np.frombuffer(full_bytes, dtype=np.uint8).astype(np.float32)
    # Simple normalization to unit length
    vec = arr / 255.0
    vec = vec.reshape(-1)[:dim]
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

# ---------------------------------------------------------------------------
# NarrativeAtlas
# ---------------------------------------------------------------------------

class NarrativeAtlas:
    """A lightweight knowledge graph with FAISS-backed semantic search."""

    DEFAULT_EMBED_DIM = 128

    def __init__(
        self,
        storage_path: str = "./atlas_store",
        embed_dim: int = DEFAULT_EMBED_DIM,
        *,
        hnsw_m: int = 32,
        hnsw_ef_construction: int = 40,
        hnsw_ef_search: int = 64,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.embed_dim = embed_dim
        self.next_faiss_id = 0  # monotonically increasing integer ID

        # Maps
        self.faiss_id_to_node_id: Dict[int, str] = {}
        self.node_id_to_faiss_id: Dict[str, int] = {}

        # Simple typed dictionaries
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.characters: Dict[str, str] = {}  # node_id -> name
        self.events: Dict[str, str] = {}
        self.locations: Dict[str, str] = {}
        self.themes: Dict[str, str] = {}

        # Build FAISS index (use HNSW for scalability)
        base_index = faiss.IndexHNSWFlat(self.embed_dim, hnsw_m, faiss.METRIC_L2)
        base_index.hnsw.efConstruction = hnsw_ef_construction
        base_index.hnsw.efSearch = hnsw_ef_search
        self.faiss_index = faiss.IndexIDMap2(base_index)

        # Spatial-temporal DB instance
        self.db = SpatialTemporalDB()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _embed(self, text: str) -> np.ndarray:
        return _hash_embedding(text, self.embed_dim).astype(np.float32)

    def _add_or_update_embedding(self, node_id: str, text: str):
        vec = self._embed(text).reshape(1, self.embed_dim)
        if node_id in self.node_id_to_faiss_id:
            # Update: remove old then add new
            old_fid = self.node_id_to_faiss_id[node_id]
            self.faiss_index.remove_ids(np.array([old_fid], dtype="int64"))
            fid = old_fid
        else:
            fid = self.next_faiss_id
            self.next_faiss_id += 1
            self.node_id_to_faiss_id[node_id] = fid
            self.faiss_id_to_node_id[fid] = node_id
        self.faiss_index.add_with_ids(vec, np.array([fid], dtype="int64"))

        # Add to Spatial-temporal DB
        self.db.add_node(node_id, self.nodes[node_id])

    # ------------------------------------------------------------------
    # Public creation helpers (minimal for tests)
    # ------------------------------------------------------------------
    def _get_or_create_character(self, name: str, importance: float) -> str:
        for nid, nm in self.characters.items():
            if nm == name:
                return nid
        node_id = str(uuid.uuid4())
        self.characters[node_id] = name
        self.nodes[node_id] = {
            "type": "character",
            "name": name,
            "importance": importance,
            "created": datetime.utcnow().isoformat(),
        }
        self._add_or_update_embedding(node_id, f"Character: {name} Importance: {importance}")
        return node_id

    def _get_or_create_location(self, name: str, significance: float) -> str:
        for nid, nm in self.locations.items():
            if nm == name:
                return nid
        node_id = str(uuid.uuid4())
        self.locations[node_id] = name
        self.nodes[node_id] = {
            "type": "location",
            "name": name,
            "significance": significance,
            "created": datetime.utcnow().isoformat(),
        }
        self._add_or_update_embedding(node_id, f"Location: {name} Significance: {significance}")
        return node_id

    def _create_event(self, description: str, impact: float, participant_ids: List[str]) -> str:
        node_id = str(uuid.uuid4())
        self.events[node_id] = description
        self.nodes[node_id] = {
            "type": "event",
            "description": description,
            "impact": impact,
            "participants": participant_ids,
            "created": datetime.utcnow().isoformat(),
        }
        # Build an embedding string combining description and participant names
        participant_names = [self.nodes[p]["name"] for p in participant_ids if p in self.nodes]
        embed_text = f"Event: {description} Participants: {'; '.join(participant_names)} Impact: {impact}"
        self._add_or_update_embedding(node_id, embed_text)
        return node_id

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def find_similar_nodes(self, query_text: str, k: int = 3) -> List[Tuple[str, float]]:
        if self.faiss_index.ntotal == 0:
            return []
        qvec = self._embed(query_text).reshape(1, self.embed_dim)
        D, I = self.faiss_index.search(qvec, k)
        results: List[Tuple[str, float]] = []
        for dist, fid in zip(D[0], I[0]):
            if fid == -1:
                continue
            node_id = self.faiss_id_to_node_id.get(int(fid))
            if node_id:
                results.append((node_id, float(dist)))
        return results

    def answer_query_with_context(self, user_query: str, k: int = 3) -> str:
        """Return an LLM-ready prompt containing context for the user query."""
        retrieved = self.find_similar_nodes(user_query, k=k)
        if not retrieved:
            return (
                f"No relevant context found for the query: {user_query}\n"
                "(Atlas is empty or semantic search returned nothing.)"
            )
        context_lines: List[str] = []
        for node_id, dist in retrieved:
            n = self.nodes[node_id]
            ntype = n.get("type", "unknown")
            if ntype == "character":
                context_lines.append(f"Character: {n['name']} (importance {n.get('importance')})")
            elif ntype == "location":
                context_lines.append(f"Location: {n['name']} (significance {n.get('significance')})")
            elif ntype == "event":
                context_lines.append(f"Event: {n['description']} (impact {n.get('impact')})")
            else:
                context_lines.append(str(n))
        formatted_context = "\n".join(context_lines)
        prompt = (
            "Based ONLY on the following context:\n"
            "--- CONTEXT START ---\n"
            f"{formatted_context}\n"
            "--- CONTEXT END ---\n\n"
            f"Answer the question: {user_query}"
        )
        return prompt

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self):
        faiss_path = self.storage_path / "faiss.index"
        meta_path = self.storage_path / "atlas_meta.pkl"
        faiss.write_index(self.faiss_index, str(faiss_path))
        data = {
            "next_faiss_id": self.next_faiss_id,
            "faiss_id_to_node_id": self.faiss_id_to_node_id,
            "node_id_to_faiss_id": self.node_id_to_faiss_id,
            "nodes": self.nodes,
            "characters": self.characters,
            "events": self.events,
            "locations": self.locations,
            "themes": self.themes,
        }
        with open(meta_path, "wb") as f:
            pickle.dump(data, f)

    def load(self):
        faiss_path = self.storage_path / "faiss.index"
        meta_path = self.storage_path / "atlas_meta.pkl"
        if not faiss_path.exists() or not meta_path.exists():
            raise FileNotFoundError("Saved atlas data not found in storage path")
        self.faiss_index = faiss.read_index(str(faiss_path))
        with open(meta_path, "rb") as f:
            data = pickle.load(f)
        self.next_faiss_id = data["next_faiss_id"]
        self.faiss_id_to_node_id = data["faiss_id_to_node_id"]
        self.node_id_to_faiss_id = data["node_id_to_faiss_id"]
        self.nodes = data["nodes"]
        self.characters = data["characters"]
        self.events = data["events"]
        self.locations = data["locations"]
        self.themes = data["themes"]

    # ------------------------------------------------------------------
    # Deletion (for later prompts)
    # ------------------------------------------------------------------
    def delete_node(self, node_id: str) -> bool:
        # Attempt to remove from DB (may be empty if reloaded older state)
        self.db.delete_node(node_id)

        # Remove from FAISS & maps
        fid = self.node_id_to_faiss_id.get(node_id)
        if fid is not None:
            try:
                self.faiss_index.remove_ids(np.array([fid], dtype="int64"))
            except Exception:
                pass  # continue cleanup even if FAISS removal fails
            self.node_id_to_faiss_id.pop(node_id, None)
            self.faiss_id_to_node_id.pop(fid, None)

        # Typed dictionaries & master dict
        self.characters.pop(node_id, None)
        self.events.pop(node_id, None)
        self.locations.pop(node_id, None)
        self.themes.pop(node_id, None)
        self.nodes.pop(node_id, None)

        return True 
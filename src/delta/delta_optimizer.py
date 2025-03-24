"""
Delta optimization module for time-series data.

This module provides optimized storage and retrieval for temporal data changes.
"""

import os
import time
import json
import zlib
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime
from collections import defaultdict

from src.core.node import Node

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeltaCompressor:
    """
    Compresses delta objects for efficient storage.
    """
    
    @staticmethod
    def compress(data: Dict[str, Any]) -> bytes:
        """
        Compress a dictionary to a binary format.
        
        Args:
            data: Dictionary to compress
            
        Returns:
            Compressed binary data
        """
        # Convert to JSON
        json_data = json.dumps(data, sort_keys=True)
        
        # Compress with zlib
        compressed = zlib.compress(json_data.encode('utf-8'), level=9)
        
        return compressed
    
    @staticmethod
    def decompress(compressed_data: bytes) -> Dict[str, Any]:
        """
        Decompress binary data to a dictionary.
        
        Args:
            compressed_data: Compressed binary data
            
        Returns:
            Decompressed dictionary
        """
        # Decompress with zlib
        json_data = zlib.decompress(compressed_data).decode('utf-8')
        
        # Parse JSON
        return json.loads(json_data)

class DeltaEncoder:
    """
    Encodes differences between node versions.
    """
    
    @classmethod
    def compute_delta(cls, old_node: Node, new_node: Node) -> Dict[str, Any]:
        """
        Compute delta between old and new node versions.
        
        Args:
            old_node: Previous node version
            new_node: Current node version
            
        Returns:
            Delta dictionary
        """
        delta = {
            "node_id": new_node.id,
            "timestamp": time.time(),
            "version": new_node.metadata.get("version", 1),
            "prev_version": old_node.metadata.get("version", 0),
            "changes": {}
        }
        
        # Check content changes
        if old_node.content != new_node.content:
            delta["changes"]["content"] = {
                "old": old_node.content,
                "new": new_node.content
            }
        
        # Check coordinate changes
        if old_node.coordinates.spatial != new_node.coordinates.spatial:
            delta["changes"]["spatial"] = {
                "old": old_node.coordinates.spatial,
                "new": new_node.coordinates.spatial
            }
        
        if old_node.coordinates.temporal != new_node.coordinates.temporal:
            delta["changes"]["temporal"] = {
                "old": old_node.coordinates.temporal,
                "new": new_node.coordinates.temporal
            }
        
        # Check metadata changes
        old_meta = old_node.metadata.copy() if old_node.metadata else {}
        new_meta = new_node.metadata.copy() if new_node.metadata else {}
        
        # Remove standard metadata fields
        for field in ["created_at", "updated_at", "created_by", "updated_by", "version"]:
            old_meta.pop(field, None)
            new_meta.pop(field, None)
        
        # Find added/changed metadata
        delta["changes"]["metadata"] = {"added": {}, "changed": {}, "removed": []}
        
        for key, value in new_meta.items():
            if key not in old_meta:
                delta["changes"]["metadata"]["added"][key] = value
            elif old_meta[key] != value:
                delta["changes"]["metadata"]["changed"][key] = {
                    "old": old_meta[key],
                    "new": value
                }
        
        # Find removed metadata
        for key in old_meta:
            if key not in new_meta:
                delta["changes"]["metadata"]["removed"].append(key)
        
        # If there are no changes to metadata, remove the metadata section
        if (not delta["changes"]["metadata"]["added"] and
            not delta["changes"]["metadata"]["changed"] and
            not delta["changes"]["metadata"]["removed"]):
            del delta["changes"]["metadata"]
        
        return delta
    
    @classmethod
    def apply_delta(cls, node: Node, delta: Dict[str, Any]) -> Node:
        """
        Apply delta changes to a node.
        
        Args:
            node: Base node
            delta: Delta changes
            
        Returns:
            Updated node
        """
        node_id = node.id
        content = node.content
        spatial = node.coordinates.spatial
        temporal = node.coordinates.temporal
        metadata = node.metadata.copy() if node.metadata else {}
        
        # Apply changes
        changes = delta.get("changes", {})
        
        # Update content
        if "content" in changes:
            content = changes["content"]["new"]
        
        # Update coordinates
        if "spatial" in changes:
            spatial = changes["spatial"]["new"]
        
        if "temporal" in changes:
            temporal = changes["temporal"]["new"]
        
        # Update metadata
        metadata["version"] = delta.get("version", metadata.get("version", 0) + 1)
        metadata["updated_at"] = delta.get("timestamp", time.time())
        
        if "metadata" in changes:
            # Add new metadata
            for key, value in changes["metadata"].get("added", {}).items():
                metadata[key] = value
            
            # Update changed metadata
            for key, value in changes["metadata"].get("changed", {}).items():
                metadata[key] = value["new"]
            
            # Remove metadata
            for key in changes["metadata"].get("removed", []):
                if key in metadata:
                    del metadata[key]
        
        # Create updated node
        from src.core.coordinates import Coordinates
        return Node(
            id=node_id,
            content=content,
            coordinates=Coordinates(spatial=spatial, temporal=temporal),
            metadata=metadata
        )

class DeltaStore:
    """
    Manages storage and retrieval of deltas.
    """
    
    def __init__(self, db_path: str = "data/delta_store"):
        """
        Initialize the delta store.
        
        Args:
            db_path: Path to delta storage
        """
        self.db_path = db_path
        self.deltas = {}  # In-memory cache
        self.index = defaultdict(list)  # node_id -> [version timestamps]
        
        # Create directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        # Load index
        self.load_index()
    
    def store_delta(self, delta: Dict[str, Any]) -> None:
        """
        Store a delta.
        
        Args:
            delta: Delta to store
        """
        node_id = delta["node_id"]
        version = delta["version"]
        timestamp = delta["timestamp"]
        
        # Compress delta
        compressed = DeltaCompressor.compress(delta)
        
        # Generate filename
        filename = f"{node_id}_{version}_{timestamp}.delta"
        filepath = os.path.join(self.db_path, filename)
        
        # Write to file
        with open(filepath, "wb") as f:
            f.write(compressed)
        
        # Update index
        self.index[node_id].append((version, timestamp, filename))
        self.index[node_id].sort(key=lambda x: x[0])  # Sort by version
        
        # Save index
        self.save_index()
        
        # Update cache
        self.deltas[(node_id, version)] = delta
    
    def get_delta(self, node_id: str, version: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific delta.
        
        Args:
            node_id: Node ID
            version: Node version
            
        Returns:
            Delta if found, None otherwise
        """
        # Check cache
        if (node_id, version) in self.deltas:
            return self.deltas[(node_id, version)]
        
        # Find in index
        for v, _, filename in self.index[node_id]:
            if v == version:
                # Load from file
                filepath = os.path.join(self.db_path, filename)
                try:
                    with open(filepath, "rb") as f:
                        compressed = f.read()
                        delta = DeltaCompressor.decompress(compressed)
                        self.deltas[(node_id, version)] = delta
                        return delta
                except Exception as e:
                    logger.error(f"Error loading delta {filename}: {str(e)}")
                    return None
        
        return None
    
    def get_delta_chain(self, node_id: str, start_version: int = 1, 
                      end_version: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a chain of deltas for a node.
        
        Args:
            node_id: Node ID
            start_version: Start version (inclusive)
            end_version: End version (inclusive, defaults to latest)
            
        Returns:
            List of deltas
        """
        versions = [entry[0] for entry in self.index[node_id]]
        if not versions:
            return []
        
        if end_version is None:
            end_version = max(versions)
        
        deltas = []
        for version in range(start_version, end_version + 1):
            delta = self.get_delta(node_id, version)
            if delta:
                deltas.append(delta)
        
        return deltas
    
    def reconstruct_node(self, node_id: str, base_node: Node, 
                        target_version: Optional[int] = None) -> Optional[Node]:
        """
        Reconstruct a node to a specific version by applying deltas.
        
        Args:
            node_id: Node ID
            base_node: Base node
            target_version: Target version (defaults to latest)
            
        Returns:
            Reconstructed node or None if not possible
        """
        versions = [entry[0] for entry in self.index[node_id]]
        if not versions:
            return base_node
        
        if target_version is None:
            target_version = max(versions)
        
        # If base_node is newer than target, we can't reconstruct
        base_version = base_node.metadata.get("version", 1)
        if base_version > target_version:
            logger.warning(f"Base node version {base_version} is newer than target {target_version}")
            return None
        
        # If already at target version, return base
        if base_version == target_version:
            return base_node
        
        # Get required deltas
        deltas = self.get_delta_chain(node_id, base_version + 1, target_version)
        
        # Apply deltas in sequence
        node = base_node
        for delta in deltas:
            node = DeltaEncoder.apply_delta(node, delta)
        
        return node
    
    def prune_deltas(self, node_id: str, keep_versions: int = 10) -> int:
        """
        Prune old deltas for a node, keeping only the most recent ones.
        
        Args:
            node_id: Node ID
            keep_versions: Number of most recent versions to keep
            
        Returns:
            Number of pruned deltas
        """
        entries = self.index[node_id]
        if len(entries) <= keep_versions:
            return 0
        
        # Sort by version (ascending)
        entries.sort(key=lambda x: x[0])
        
        # Identify entries to prune
        to_prune = entries[:-keep_versions]
        
        # Remove files
        pruned_count = 0
        for _, _, filename in to_prune:
            filepath = os.path.join(self.db_path, filename)
            try:
                os.remove(filepath)
                pruned_count += 1
            except Exception as e:
                logger.error(f"Error removing delta file {filepath}: {str(e)}")
        
        # Update index
        self.index[node_id] = entries[-keep_versions:]
        
        # Update cache
        for version, _, _ in to_prune:
            self.deltas.pop((node_id, version), None)
        
        # Save index
        self.save_index()
        
        return pruned_count
    
    def merge_deltas(self, node_id: str, start_version: int, end_version: int) -> bool:
        """
        Merge multiple consecutive deltas into a single delta.
        
        Args:
            node_id: Node ID
            start_version: Start version (inclusive)
            end_version: End version (inclusive)
            
        Returns:
            True if successful, False otherwise
        """
        # Get base node
        base_delta = self.get_delta(node_id, start_version - 1)
        if not base_delta:
            logger.warning(f"Base delta (version {start_version - 1}) not found for node {node_id}")
            return False
        
        # Get deltas to merge
        deltas = self.get_delta_chain(node_id, start_version, end_version)
        if len(deltas) < 2:
            logger.warning(f"Not enough deltas to merge for node {node_id}")
            return False
        
        # Generate cumulative delta
        merged_delta = {
            "node_id": node_id,
            "timestamp": time.time(),
            "version": end_version,
            "prev_version": start_version - 1,
            "changes": {}
        }
        
        # Apply deltas to determine final state
        initial_state = self.reconstruct_node(node_id, base_delta["node"], start_version - 1)
        final_state = self.reconstruct_node(node_id, initial_state, end_version)
        
        if not initial_state or not final_state:
            logger.warning(f"Failed to reconstruct states for node {node_id}")
            return False
        
        # Compute direct delta between initial and final states
        merged_delta = DeltaEncoder.compute_delta(initial_state, final_state)
        
        # Store merged delta
        self.store_delta(merged_delta)
        
        # Remove old deltas
        for version in range(start_version, end_version):
            self.remove_delta(node_id, version)
        
        return True
    
    def remove_delta(self, node_id: str, version: int) -> bool:
        """
        Remove a specific delta.
        
        Args:
            node_id: Node ID
            version: Version to remove
            
        Returns:
            True if successful, False otherwise
        """
        # Find in index
        for i, (v, _, filename) in enumerate(self.index[node_id]):
            if v == version:
                # Remove file
                filepath = os.path.join(self.db_path, filename)
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.error(f"Error removing delta file {filepath}: {str(e)}")
                    return False
                
                # Update index
                self.index[node_id].pop(i)
                
                # Update cache
                self.deltas.pop((node_id, version), None)
                
                # Save index
                self.save_index()
                
                return True
        
        return False
    
    def save_index(self) -> None:
        """Save index to file."""
        index_path = os.path.join(self.db_path, "index.json")
        
        # Convert defaultdict to regular dict for JSON serialization
        serializable_index = {}
        for node_id, entries in self.index.items():
            serializable_index[node_id] = entries
        
        with open(index_path, "w") as f:
            json.dump(serializable_index, f, indent=2)
    
    def load_index(self) -> None:
        """Load index from file."""
        index_path = os.path.join(self.db_path, "index.json")
        
        if not os.path.exists(index_path):
            return
        
        try:
            with open(index_path, "r") as f:
                loaded_index = json.load(f)
                
                # Convert to defaultdict
                for node_id, entries in loaded_index.items():
                    self.index[node_id] = entries
        except Exception as e:
            logger.error(f"Error loading delta index: {str(e)}")

class DeltaOptimizer:
    """
    Manages delta optimization strategies.
    """
    
    def __init__(self, delta_store: DeltaStore):
        """
        Initialize the delta optimizer.
        
        Args:
            delta_store: Delta storage
        """
        self.delta_store = delta_store
        self.stats = {
            "total_deltas": 0,
            "pruned_deltas": 0,
            "merged_deltas": 0,
            "compression_ratio": 0.0
        }
    
    def optimize(self, node_id: str) -> Dict[str, Any]:
        """
        Optimize deltas for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Optimization statistics
        """
        stats = {
            "node_id": node_id,
            "original_delta_count": len(self.delta_store.index[node_id]),
            "pruned": 0,
            "merged": 0,
            "final_delta_count": 0
        }
        
        # Prune old deltas
        stats["pruned"] = self.delta_store.prune_deltas(node_id)
        
        # Merge consecutive deltas
        entries = self.delta_store.index[node_id]
        if len(entries) >= 5:
            # Find consecutive version groups
            versions = sorted([entry[0] for entry in entries])
            
            # Simple strategy: merge oldest 5 consecutive versions if available
            if len(versions) >= 5:
                start = versions[0]
                end = versions[4]
                if end - start == 4:  # Ensure they're consecutive
                    if self.delta_store.merge_deltas(node_id, start, end):
                        stats["merged"] = 5
        
        # Update stats
        stats["final_delta_count"] = len(self.delta_store.index[node_id])
        
        # Update global stats
        self.stats["total_deltas"] += stats["final_delta_count"]
        self.stats["pruned_deltas"] += stats["pruned"]
        self.stats["merged_deltas"] += stats["merged"]
        
        return stats
    
    def optimize_all(self) -> Dict[str, Any]:
        """
        Optimize all deltas.
        
        Returns:
            Optimization statistics
        """
        overall_stats = {
            "total_nodes": len(self.delta_store.index),
            "total_deltas_before": sum(len(entries) for entries in self.delta_store.index.values()),
            "total_pruned": 0,
            "total_merged": 0,
            "total_deltas_after": 0
        }
        
        for node_id in list(self.delta_store.index.keys()):
            node_stats = self.optimize(node_id)
            overall_stats["total_pruned"] += node_stats["pruned"]
            overall_stats["total_merged"] += node_stats["merged"]
        
        overall_stats["total_deltas_after"] = sum(len(entries) for entries in self.delta_store.index.values())
        
        return overall_stats
    
    def calculate_compression_ratio(self) -> float:
        """
        Calculate overall compression ratio.
        
        Returns:
            Compression ratio (original / compressed)
        """
        total_original = 0
        total_compressed = 0
        
        for node_id in self.delta_store.index:
            for version, _, filename in self.delta_store.index[node_id]:
                filepath = os.path.join(self.delta_store.db_path, filename)
                
                # Get compressed size
                try:
                    compressed_size = os.path.getsize(filepath)
                except:
                    continue
                
                # Load and get original size
                delta = self.delta_store.get_delta(node_id, version)
                if delta:
                    original_size = len(json.dumps(delta).encode('utf-8'))
                    
                    total_original += original_size
                    total_compressed += compressed_size
        
        if total_compressed == 0:
            return 0.0
        
        ratio = total_original / total_compressed
        self.stats["compression_ratio"] = ratio
        
        return ratio
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.
        
        Returns:
            Statistics dictionary
        """
        # Update compression ratio
        self.calculate_compression_ratio()
        
        return self.stats 
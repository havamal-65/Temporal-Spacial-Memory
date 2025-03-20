"""
Chain optimization for the delta chain system.

This module provides the ChainOptimizer class for improving
the performance and storage efficiency of delta chains.
"""

from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
import logging
import time
import copy

from .store import DeltaStore
from .records import DeltaRecord
from .reconstruction import StateReconstructor


class ChainOptimizer:
    """
    Optimizes delta chains for improved performance and storage efficiency.
    
    This class provides methods for compacting, pruning, and
    checkpointing delta chains.
    """
    
    def __init__(self, delta_store: DeltaStore):
        """
        Initialize a chain optimizer.
        
        Args:
            delta_store: Storage for delta records
        """
        self.delta_store = delta_store
        self.reconstructor = StateReconstructor(delta_store)
        self.logger = logging.getLogger(__name__)
    
    def compact_chain(self, 
                     node_id: UUID,
                     threshold: int = 10) -> bool:
        """
        Compact a delta chain by merging small deltas.
        
        Args:
            node_id: The node whose chain to compact
            threshold: Maximum number of operations to merge
            
        Returns:
            True if compaction was performed
        """
        # Get all deltas for the node
        deltas = self.delta_store.get_deltas_for_node(node_id)
        
        if len(deltas) < 2:
            return False
            
        # Sort by timestamp
        deltas.sort(key=lambda d: d.timestamp)
        
        # Track if we performed any compaction
        compacted = False
        
        # Find candidates for merging
        for i in range(len(deltas) - 1):
            # Check if this and the next delta are small enough to merge
            if len(deltas[i].operations) + len(deltas[i+1].operations) <= threshold:
                # Merge the deltas
                merged_ops = deltas[i].operations + deltas[i+1].operations
                
                # Create a new delta with the combined operations
                merged_delta = DeltaRecord(
                    node_id=node_id,
                    timestamp=deltas[i+1].timestamp,
                    operations=merged_ops,
                    previous_delta_id=deltas[i].previous_delta_id,
                    metadata={
                        "merged": True,
                        "original_ids": [str(deltas[i].delta_id), str(deltas[i+1].delta_id)],
                        "original_timestamps": [deltas[i].timestamp, deltas[i+1].timestamp]
                    }
                )
                
                # Store the merged delta
                self.delta_store.store_delta(merged_delta)
                
                # Update references in any deltas that pointed to the second delta
                for j in range(i+2, len(deltas)):
                    if deltas[j].previous_delta_id == deltas[i+1].delta_id:
                        # Create an updated delta with the new reference
                        updated_delta = DeltaRecord(
                            node_id=deltas[j].node_id,
                            timestamp=deltas[j].timestamp,
                            operations=deltas[j].operations,
                            previous_delta_id=merged_delta.delta_id,
                            delta_id=deltas[j].delta_id,
                            metadata=deltas[j].metadata
                        )
                        self.delta_store.store_delta(updated_delta)
                
                # Delete the original deltas
                self.delta_store.delete_delta(deltas[i].delta_id)
                self.delta_store.delete_delta(deltas[i+1].delta_id)
                
                compacted = True
                break
        
        return compacted
    
    def create_checkpoint(self,
                         node_id: UUID,
                         timestamp: float,
                         content: Dict[str, Any]) -> UUID:
        """
        Create a checkpoint to optimize future reconstructions.
        
        Args:
            node_id: The node to checkpoint
            timestamp: When this checkpoint represents
            content: The full content at this point
            
        Returns:
            ID of the checkpoint delta
        """
        # Get the previous delta
        deltas = self.delta_store.get_deltas_in_time_range(
            node_id=node_id,
            start_time=0,
            end_time=timestamp
        )
        
        # Sort by timestamp to find the latest delta before or at the checkpoint
        deltas.sort(key=lambda d: d.timestamp)
        previous_delta_id = None
        if deltas:
            previous_delta_id = deltas[-1].delta_id
        
        # Create a checkpoint delta with no operations
        # The content is stored in the metadata for space efficiency
        checkpoint_delta = DeltaRecord(
            node_id=node_id,
            timestamp=timestamp,
            operations=[],  # No operations needed
            previous_delta_id=previous_delta_id,
            metadata={
                "checkpoint": True,
                "content": content
            }
        )
        
        # Store the checkpoint
        self.delta_store.store_delta(checkpoint_delta)
        
        self.logger.info(f"Created checkpoint at {timestamp} for node {node_id}")
        
        return checkpoint_delta.delta_id
    
    def prune_chain(self,
                   node_id: UUID,
                   older_than: float) -> int:
        """
        Remove old deltas that are no longer needed.
        
        Args:
            node_id: The node whose chain to prune
            older_than: Remove deltas older than this timestamp
            
        Returns:
            Number of deltas removed
        """
        # Get all deltas older than the specified timestamp
        deltas = self.delta_store.get_deltas_in_time_range(
            node_id=node_id,
            start_time=0,
            end_time=older_than
        )
        
        if not deltas:
            return 0
        
        # Create a checkpoint at the cutoff point
        # First reconstruct the state at that point
        node_state = self.reconstructor.reconstruct_state(
            node_id=node_id,
            origin_content={},  # Will be populated from the earliest delta
            target_timestamp=older_than
        )
        
        # Create the checkpoint
        self.create_checkpoint(
            node_id=node_id,
            timestamp=older_than,
            content=node_state
        )
        
        # Delete all deltas older than the cutoff
        count = 0
        for delta in deltas:
            if self.delta_store.delete_delta(delta.delta_id):
                count += 1
        
        self.logger.info(f"Pruned {count} deltas older than {older_than} for node {node_id}")
        
        return count
    
    def analyze_chain(self, node_id: UUID) -> Dict[str, Any]:
        """
        Analyze a delta chain to identify optimization opportunities.
        
        Args:
            node_id: The node whose chain to analyze
            
        Returns:
            Analysis results with optimization recommendations
        """
        # Get all deltas for the node
        deltas = self.delta_store.get_deltas_for_node(node_id)
        
        if not deltas:
            return {"status": "empty", "recommendations": []}
        
        # Sort by timestamp
        deltas.sort(key=lambda d: d.timestamp)
        
        # Calculate total size
        total_size = sum(delta.get_size() for delta in deltas)
        
        # Identify small deltas that could be merged
        small_deltas = []
        for i in range(len(deltas) - 1):
            if len(deltas[i].operations) <= 5:  # Arbitrary threshold
                small_deltas.append(deltas[i].delta_id)
        
        # Identify long chains without checkpoints
        chain_length = len(deltas)
        checkpoints = [d for d in deltas if d.metadata.get('checkpoint', False)]
        checkpoint_count = len(checkpoints)
        
        # Create analysis result
        result = {
            "chain_length": chain_length,
            "total_size_bytes": total_size,
            "checkpoint_count": checkpoint_count,
            "small_deltas_count": len(small_deltas),
            "oldest_delta": deltas[0].timestamp if deltas else None,
            "newest_delta": deltas[-1].timestamp if deltas else None,
            "recommendations": []
        }
        
        # Add recommendations
        if chain_length > 50 and checkpoint_count == 0:
            result["recommendations"].append({
                "type": "add_checkpoints",
                "message": f"Add checkpoints to improve reconstruction performance for this long chain ({chain_length} deltas)"
            })
        
        if len(small_deltas) > 5:
            result["recommendations"].append({
                "type": "compact_chain",
                "message": f"Compact chain to merge {len(small_deltas)} small deltas"
            })
        
        # Check if there are very old deltas that could be pruned
        if chain_length > 10:
            oldest_quarter = deltas[:chain_length // 4]
            if oldest_quarter:
                cutoff = oldest_quarter[-1].timestamp
                result["recommendations"].append({
                    "type": "prune_chain",
                    "message": f"Prune deltas older than {cutoff} to reduce storage (approximately {len(oldest_quarter)} deltas)"
                })
        
        return result
    
    def optimize_all_chains(self, 
                           min_length: int = 10, 
                           max_operations: int = 50) -> Dict[str, int]:
        """
        Apply optimization to all chains that meet criteria.
        
        Args:
            min_length: Minimum chain length to consider for optimization
            max_operations: Maximum operations to merge when compacting
            
        Returns:
            Dictionary with counts of optimizations performed
        """
        # This would normally scan the delta store for all nodes,
        # but for simplicity we'll return a placeholder
        return {
            "chains_analyzed": 0,
            "checkpoints_created": 0,
            "chains_compacted": 0,
            "chains_pruned": 0
        } 
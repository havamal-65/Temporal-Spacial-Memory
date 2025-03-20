"""
Delta chain management for the delta chain system.

This module provides the DeltaChain class for organizing and 
manipulating sequences of deltas that track changes to node content over time.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from uuid import UUID
import copy
import bisect

from .records import DeltaRecord


class DeltaChain:
    """
    Manages a chain of delta records for a node.
    
    A delta chain represents the evolution of a node's content over time,
    allowing for efficient storage and reconstruction of the node state
    at any point in its history.
    """
    
    def __init__(self, 
                 node_id: UUID, 
                 origin_content: Dict[str, Any],
                 origin_timestamp: float):
        """
        Initialize a delta chain.
        
        Args:
            node_id: The node this chain applies to
            origin_content: The base content for the chain
            origin_timestamp: When the origin content was created
        """
        self.node_id = node_id
        self.origin_content = copy.deepcopy(origin_content)
        self.origin_timestamp = origin_timestamp
        self.deltas: Dict[UUID, DeltaRecord] = {}  # delta_id -> DeltaRecord
        self.head_delta_id: Optional[UUID] = None  # Most recent delta
        
        # Additional indices for efficient access
        self.timestamps: Dict[UUID, float] = {}  # delta_id -> timestamp
        self.delta_ids_by_time: List[UUID] = []  # Sorted by timestamp
        
        # Chain structure
        self.next_delta: Dict[UUID, UUID] = {}  # delta_id -> next_delta_id
        self.checkpoints: Dict[float, Dict[str, Any]] = {}  # timestamp -> content snapshot
    
    def append_delta(self, delta: DeltaRecord) -> None:
        """
        Add a delta to the chain.
        
        Args:
            delta: The delta record to add
            
        Raises:
            ValueError: If the delta is for a different node or doesn't link properly
        """
        if delta.node_id != self.node_id:
            raise ValueError("Delta is for a different node")
            
        if delta.is_empty():
            return  # Skip empty deltas
            
        if self.head_delta_id and delta.previous_delta_id != self.head_delta_id:
            raise ValueError("Delta does not link to head of chain")
            
        # Add to main storage
        self.deltas[delta.delta_id] = delta
        
        # Update indices
        self.timestamps[delta.delta_id] = delta.timestamp
        
        # Insert into sorted timestamp list
        index = bisect.bisect(
            [self.timestamps.get(did, 0) for did in self.delta_ids_by_time], 
            delta.timestamp
        )
        self.delta_ids_by_time.insert(index, delta.delta_id)
        
        # Update chain linkage
        if self.head_delta_id:
            self.next_delta[self.head_delta_id] = delta.delta_id
            
        # Update head pointer
        self.head_delta_id = delta.delta_id
    
    def get_content_at(self, timestamp: float) -> Dict[str, Any]:
        """
        Reconstruct content at the given timestamp.
        
        Args:
            timestamp: The target timestamp
            
        Returns:
            The reconstructed content state
        """
        # Start with origin content
        if timestamp <= self.origin_timestamp:
            return copy.deepcopy(self.origin_content)
        
        # Check if we have an exact checkpoint
        if timestamp in self.checkpoints:
            return copy.deepcopy(self.checkpoints[timestamp])
            
        # Find the closest earlier checkpoint
        checkpoint_time = self.origin_timestamp
        content = copy.deepcopy(self.origin_content)
        
        for ckpt_time in sorted(self.checkpoints.keys()):
            if ckpt_time <= timestamp and ckpt_time > checkpoint_time:
                checkpoint_time = ckpt_time
                content = copy.deepcopy(self.checkpoints[ckpt_time])
        
        # Find deltas to apply
        delta_ids = self.get_delta_ids_in_range(checkpoint_time, timestamp)
        
        # Apply deltas in chronological order
        for delta_id in delta_ids:
            delta = self.deltas[delta_id]
            content = delta.apply(content)
            
        return content
    
    def get_latest_content(self) -> Dict[str, Any]:
        """
        Get the most recent content state.
        
        Returns:
            The content after applying all deltas
        """
        return self.get_content_at(float('inf'))
    
    def get_delta_ids_in_range(self, 
                              start_timestamp: float, 
                              end_timestamp: float) -> List[UUID]:
        """
        Get IDs of deltas in the given time range.
        
        Args:
            start_timestamp: Start of time range (exclusive)
            end_timestamp: End of time range (inclusive)
            
        Returns:
            List of delta IDs in chronological order
        """
        result = []
        
        for delta_id in self.delta_ids_by_time:
            timestamp = self.timestamps[delta_id]
            if start_timestamp < timestamp <= end_timestamp:
                result.append(delta_id)
                
        return result
    
    def get_delta_by_id(self, delta_id: UUID) -> Optional[DeltaRecord]:
        """
        Get a specific delta by ID.
        
        Args:
            delta_id: The ID of the delta to retrieve
            
        Returns:
            The delta record if found, None otherwise
        """
        return self.deltas.get(delta_id)
    
    def create_checkpoint(self, timestamp: float) -> None:
        """
        Create a content checkpoint at the given timestamp.
        
        Args:
            timestamp: When to create the checkpoint
            
        Raises:
            ValueError: If the timestamp is invalid
        """
        if timestamp < self.origin_timestamp:
            raise ValueError("Cannot create checkpoint before origin")
            
        content = self.get_content_at(timestamp)
        self.checkpoints[timestamp] = content
    
    def compact(self, max_operations: int = 50) -> int:
        """
        Compact the chain by merging small deltas.
        
        Args:
            max_operations: Maximum number of operations to merge
            
        Returns:
            Number of deltas removed
        """
        if not self.delta_ids_by_time:
            return 0
            
        removed_count = 0
        current_id = None
        
        # Start from the earliest delta
        for i in range(len(self.delta_ids_by_time) - 1):
            current_id = self.delta_ids_by_time[i]
            next_id = self.delta_ids_by_time[i + 1]
            
            current_delta = self.deltas[current_id]
            next_delta = self.deltas[next_id]
            
            # If combined they're under the threshold, merge them
            if len(current_delta.operations) + len(next_delta.operations) <= max_operations:
                # Create a new merged delta
                merged_ops = current_delta.operations + next_delta.operations
                merged_delta = DeltaRecord(
                    node_id=self.node_id,
                    timestamp=next_delta.timestamp,
                    operations=merged_ops,
                    previous_delta_id=current_delta.previous_delta_id,
                    delta_id=next_delta.delta_id,
                    metadata={
                        "merged": True,
                        "merged_delta_ids": [str(current_id), str(next_id)]
                    }
                )
                
                # Update the chain
                self.deltas[next_id] = merged_delta
                
                # If current was linked to previous, update the link
                if current_delta.previous_delta_id and current_delta.previous_delta_id in self.next_delta:
                    self.next_delta[current_delta.previous_delta_id] = next_id
                
                # Remove current delta
                del self.deltas[current_id]
                del self.timestamps[current_id]
                self.delta_ids_by_time.remove(current_id)
                if current_id in self.next_delta:
                    del self.next_delta[current_id]
                
                removed_count += 1
                
                # We've modified the list, so we need to restart
                return removed_count + self.compact(max_operations)
        
        return removed_count
    
    def prune(self, older_than: float) -> int:
        """
        Remove deltas older than the specified timestamp.
        
        Args:
            older_than: Prune deltas older than this timestamp
            
        Returns:
            Number of deltas removed
        """
        if older_than <= self.origin_timestamp:
            return 0
            
        # Create a checkpoint at the pruning point
        self.create_checkpoint(older_than)
        
        # Find deltas to remove
        to_remove = self.get_delta_ids_in_range(self.origin_timestamp, older_than)
        
        # Remove the deltas
        for delta_id in to_remove:
            del self.deltas[delta_id]
            del self.timestamps[delta_id]
            if delta_id in self.next_delta:
                del self.next_delta[delta_id]
        
        # Update the delta_ids_by_time list
        self.delta_ids_by_time = [did for did in self.delta_ids_by_time if did not in to_remove]
        
        # Update the origin
        self.origin_content = self.checkpoints[older_than]
        self.origin_timestamp = older_than
        
        # Remove checkpoints that are no longer needed
        self.checkpoints = {t: c for t, c in self.checkpoints.items() if t >= older_than}
        
        return len(to_remove)
    
    def get_chain_size(self) -> int:
        """
        Get the total size of the delta chain.
        
        Returns:
            The approximate size in bytes
        """
        size = 0
        
        # Origin content
        import json
        size += len(json.dumps(self.origin_content))
        
        # Deltas
        for delta in self.deltas.values():
            size += delta.get_size()
            
        # Checkpoints
        for content in self.checkpoints.values():
            size += len(json.dumps(content))
            
        return size
    
    def get_all_delta_ids(self) -> List[UUID]:
        """
        Get all delta IDs in chronological order.
        
        Returns:
            List of all delta IDs
        """
        return self.delta_ids_by_time.copy()
    
    def __len__(self) -> int:
        """Get the number of deltas in the chain."""
        return len(self.deltas) 
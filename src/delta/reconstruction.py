"""
State reconstruction for the delta chain system.

This module provides the StateReconstructor class for efficiently
reconstructing node content at any point in time.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID
import copy
import time
import logging

from .records import DeltaRecord
from .store import DeltaStore


class StateReconstructor:
    """
    Reconstructs node state at a given point in time.
    
    This class efficiently reconstructs node content by applying
    the appropriate sequence of delta operations.
    """
    
    def __init__(self, delta_store: DeltaStore):
        """
        Initialize a state reconstructor.
        
        Args:
            delta_store: Storage for delta records
        """
        self.delta_store = delta_store
        self.logger = logging.getLogger(__name__)
        
        # Cache for reconstructed states to improve performance
        self._state_cache: Dict[Tuple[UUID, float], Dict[str, Any]] = {}
        self._cache_size = 100  # Maximum number of states to cache
    
    def reconstruct_state(self, 
                         node_id: UUID, 
                         origin_content: Dict[str, Any],
                         target_timestamp: float) -> Dict[str, Any]:
        """
        Reconstruct node state at the given timestamp.
        
        Args:
            node_id: The node to reconstruct
            origin_content: The base/origin content
            target_timestamp: Target time for reconstruction
            
        Returns:
            The reconstructed content state
        """
        # Check cache first
        cache_key = (node_id, target_timestamp)
        if cache_key in self._state_cache:
            return copy.deepcopy(self._state_cache[cache_key])
        
        # Start with a copy of the origin content
        current_state = copy.deepcopy(origin_content)
        
        # Get applicable deltas
        start_time = time.time()
        deltas = self.delta_store.get_deltas_in_time_range(
            node_id=node_id,
            start_time=0,  # From beginning
            end_time=target_timestamp
        )
        query_time = time.time() - start_time
        
        # Apply deltas in sequence
        apply_start = time.time()
        for delta in deltas:
            for operation in delta.operations:
                current_state = operation.apply(current_state)
        apply_time = time.time() - apply_start
        
        # Log performance metrics
        self.logger.debug(
            f"Reconstructed state for node {node_id} at {target_timestamp}: "
            f"retrieved {len(deltas)} deltas in {query_time:.3f}s, "
            f"applied in {apply_time:.3f}s"
        )
        
        # Cache the result if not too many entries
        if len(self._state_cache) < self._cache_size:
            self._state_cache[cache_key] = copy.deepcopy(current_state)
            
        return current_state
    
    def reconstruct_delta_chain(self,
                               node_id: UUID,
                               origin_content: Dict[str, Any],
                               delta_ids: List[UUID]) -> Dict[str, Any]:
        """
        Reconstruct state by applying specific deltas.
        
        Args:
            node_id: The node to reconstruct
            origin_content: The base/origin content
            delta_ids: List of delta IDs to apply in sequence
            
        Returns:
            The reconstructed content state
        """
        # Start with a copy of the origin content
        current_state = copy.deepcopy(origin_content)
        
        # Apply each delta in sequence
        for delta_id in delta_ids:
            delta = self.delta_store.get_delta(delta_id)
            if delta:
                for operation in delta.operations:
                    current_state = operation.apply(current_state)
            else:
                self.logger.warning(f"Delta {delta_id} not found, skipping")
                
        return current_state
    
    def clear_cache(self) -> None:
        """Clear the state cache."""
        self._state_cache.clear()
    
    def get_delta_chain(self, 
                        node_id: UUID, 
                        start_timestamp: float, 
                        end_timestamp: float) -> List[DeltaRecord]:
        """
        Get all deltas for a node in the given time range.
        
        Args:
            node_id: The ID of the node
            start_timestamp: Start of time range (inclusive)
            end_timestamp: End of time range (inclusive)
            
        Returns:
            List of delta records in chronological order
        """
        return self.delta_store.get_deltas_in_time_range(
            node_id=node_id,
            start_time=start_timestamp,
            end_time=end_timestamp
        )
    
    def get_content_at_checkpoints(self,
                                  node_id: UUID,
                                  origin_content: Dict[str, Any],
                                  checkpoints: List[float]) -> Dict[float, Dict[str, Any]]:
        """
        Reconstruct content at multiple checkpoints.
        
        This is more efficient than calling reconstruct_state multiple times
        because it applies deltas in sequence without repeating work.
        
        Args:
            node_id: The node to reconstruct
            origin_content: The base/origin content
            checkpoints: List of timestamps to reconstruct at
            
        Returns:
            Dictionary mapping timestamps to content states
        """
        # Sort checkpoints
        sorted_checkpoints = sorted(checkpoints)
        
        if not sorted_checkpoints:
            return {}
            
        # Get all deltas up to the last checkpoint
        deltas = self.delta_store.get_deltas_in_time_range(
            node_id=node_id,
            start_time=0,
            end_time=sorted_checkpoints[-1]
        )
        
        # Initialize result with origin content
        result = {}
        current_state = copy.deepcopy(origin_content)
        
        # Keep track of checkpoints we've passed
        checkpoint_index = 0
        
        # Apply deltas in sequence
        for delta in deltas:
            # Check if we've passed any checkpoints
            while (checkpoint_index < len(sorted_checkpoints) and 
                   delta.timestamp > sorted_checkpoints[checkpoint_index]):
                # Save the current state for this checkpoint
                result[sorted_checkpoints[checkpoint_index]] = copy.deepcopy(current_state)
                checkpoint_index += 1
            
            # Apply the delta
            for operation in delta.operations:
                current_state = operation.apply(current_state)
        
        # Handle any remaining checkpoints
        while checkpoint_index < len(sorted_checkpoints):
            result[sorted_checkpoints[checkpoint_index]] = copy.deepcopy(current_state)
            checkpoint_index += 1
            
        return result 
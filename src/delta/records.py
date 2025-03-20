"""
Delta records for the delta chain system.

This module defines the record structure for deltas that
track changes to node content over time.
"""

from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID, uuid4
import copy
import json

from .operations import DeltaOperation


class DeltaRecord:
    """
    Represents a record of changes (delta) to a node.
    
    A delta record contains a list of operations that transform
    a node's content from one state to another at a specific point in time.
    """
    
    def __init__(
        self,
        node_id: UUID,
        timestamp: float,
        operations: List[DeltaOperation],
        previous_delta_id: Optional[UUID] = None,
        delta_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a delta record.
        
        Args:
            node_id: ID of the node this delta applies to
            timestamp: When this delta was created (temporal coordinate)
            operations: List of operations that form this delta
            previous_delta_id: ID of the previous delta in the chain
            delta_id: Unique identifier for this delta (auto-generated if None)
            metadata: Additional metadata about this delta
        """
        self.node_id = node_id
        self.timestamp = timestamp
        self.operations = operations
        self.previous_delta_id = previous_delta_id
        self.delta_id = delta_id or uuid4()
        self.metadata = metadata or {}
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this delta's operations to the given content.
        
        Args:
            content: The content to apply the delta to
            
        Returns:
            The updated content after applying all operations
        """
        result = copy.deepcopy(content)
        for operation in self.operations:
            result = operation.apply(result)
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reverse this delta's operations on the given content.
        
        Args:
            content: The content to reverse the delta on
            
        Returns:
            The updated content after reversing all operations
        """
        result = copy.deepcopy(content)
        for operation in reversed(self.operations):
            result = operation.reverse(result)
        return result
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of this delta.
        
        Returns:
            A string describing the delta
        """
        op_summaries = [op.get_summary() for op in self.operations]
        op_count = len(op_summaries)
        
        if op_count == 0:
            return "No changes"
        elif op_count == 1:
            return op_summaries[0]
        else:
            return f"{op_count} changes: " + ", ".join(op_summaries[:3]) + (
                f" and {op_count - 3} more" if op_count > 3 else ""
            )
    
    def get_size(self) -> int:
        """
        Estimate the size of this delta record.
        
        Returns:
            An approximate size in bytes
        """
        # This is a very rough estimation
        size = 0
        
        # Fixed fields
        size += 16  # node_id UUID
        size += 8   # timestamp float
        size += 16  # delta_id UUID
        size += 16 if self.previous_delta_id else 0
        
        # Metadata
        size += len(json.dumps(self.metadata))
        
        # Operations - rough estimate
        size += sum(len(json.dumps(op.__dict__)) for op in self.operations)
        
        return size
    
    def is_empty(self) -> bool:
        """
        Check if this delta contains any operations.
        
        Returns:
            True if the delta has no operations, False otherwise
        """
        return len(self.operations) == 0
    
    def __repr__(self) -> str:
        """String representation of the delta record."""
        return (f"DeltaRecord(node_id={self.node_id}, "
                f"timestamp={self.timestamp}, "
                f"delta_id={self.delta_id}, "
                f"operations={len(self.operations)})") 
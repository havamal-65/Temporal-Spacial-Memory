"""
Change detection for the delta chain system.

This module provides the ChangeDetector class for automatically
generating delta records by comparing content versions.
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Union
from uuid import UUID
import copy
import difflib

from .records import DeltaRecord
from .operations import (
    DeltaOperation, 
    SetValueOperation, 
    DeleteValueOperation, 
    ArrayInsertOperation, 
    ArrayDeleteOperation,
    TextDiffOperation
)


class ChangeDetector:
    """
    Detects changes between content versions and creates delta records.
    
    This class implements algorithms for determining the operations
    needed to transform one content state into another.
    """
    
    def create_delta(self,
                    node_id: UUID,
                    previous_content: Dict[str, Any],
                    new_content: Dict[str, Any],
                    timestamp: float,
                    previous_delta_id: Optional[UUID] = None) -> DeltaRecord:
        """
        Create a delta between content versions.
        
        Args:
            node_id: The node this delta applies to
            previous_content: Original content state
            new_content: New content state
            timestamp: When this change occurred
            previous_delta_id: ID of previous delta in chain
            
        Returns:
            A new delta record with detected changes
        """
        # Detect operations between the content versions
        operations = self._detect_changes(previous_content, new_content)
        
        # Create a delta record
        return DeltaRecord(
            node_id=node_id,
            timestamp=timestamp,
            operations=operations,
            previous_delta_id=previous_delta_id
        )
    
    def _detect_changes(self, 
                       previous: Dict[str, Any], 
                       new: Dict[str, Any],
                       path: List[str] = None) -> List[DeltaOperation]:
        """
        Detect all changes between two content states.
        
        Args:
            previous: Original content state
            new: New content state
            path: Current JSON path (for nested structures)
            
        Returns:
            List of operations that transform previous to new
        """
        if path is None:
            path = []
            
        operations = []
        
        # Get all keys from both dictionaries
        all_keys = set(previous.keys()) | set(new.keys())
        
        for key in all_keys:
            key_path = path + [key]
            
            # Handle key present in both dictionaries
            if key in previous and key in new:
                # Check if the values are different
                if previous[key] != new[key]:
                    # Handle dictionaries recursively
                    if isinstance(previous[key], dict) and isinstance(new[key], dict):
                        nested_ops = self._detect_changes(previous[key], new[key], key_path)
                        operations.extend(nested_ops)
                    # Handle lists with smart diffing
                    elif isinstance(previous[key], list) and isinstance(new[key], list):
                        list_ops = self._detect_array_operations(previous[key], new[key], key_path)
                        operations.extend(list_ops)
                    # Handle strings with text diffing
                    elif isinstance(previous[key], str) and isinstance(new[key], str) and len(previous[key]) > 100:
                        # Only use text diffing for longer strings
                        text_ops = self._detect_text_operations(previous[key], new[key], key_path)
                        operations.extend(text_ops)
                    # Handle simple value changes
                    else:
                        operations.append(SetValueOperation(
                            path=key_path,
                            value=new[key],
                            old_value=previous[key]
                        ))
            # Handle key only in previous (deleted)
            elif key in previous:
                operations.append(DeleteValueOperation(
                    path=key_path,
                    old_value=previous[key]
                ))
            # Handle key only in new (added)
            else:  # key in new
                operations.append(SetValueOperation(
                    path=key_path,
                    value=new[key],
                    old_value=None
                ))
                
        return operations
    
    def _detect_array_operations(self,
                               previous_array: List[Any],
                               new_array: List[Any],
                               path: List[str]) -> List[DeltaOperation]:
        """
        Detect array changes and generate operations.
        
        Uses diff algorithm to identify changes with minimal operations.
        
        Args:
            previous_array: Original array
            new_array: New array
            path: JSON path to the array
            
        Returns:
            List of operations to transform previous_array to new_array
        """
        operations = []
        
        # Handle simple cases efficiently
        if not previous_array:
            # Only additions to an empty array
            for i, item in enumerate(new_array):
                operations.append(ArrayInsertOperation(
                    path=path,
                    index=i,
                    value=item
                ))
            return operations
            
        if not new_array:
            # Deletion of all items
            for i, item in enumerate(reversed(previous_array)):
                operations.append(ArrayDeleteOperation(
                    path=path,
                    index=len(previous_array) - i - 1,
                    old_value=item
                ))
            return operations
            
        # For more complex cases, use difflib to find sequence of operations
        matcher = difflib.SequenceMatcher(None, previous_array, new_array)
        
        # Process the differences
        offset = 0  # Keep track of index shifts
        
        for op, prev_start, prev_end, new_start, new_end in matcher.get_opcodes():
            if op == 'equal':
                # No change, skip
                continue
                
            elif op == 'replace':
                # Replace section - handle as delete and insert
                # First delete the old items
                for i in range(prev_end - 1, prev_start - 1, -1):
                    operations.append(ArrayDeleteOperation(
                        path=path,
                        index=i + offset,
                        old_value=previous_array[i]
                    ))
                offset -= (prev_end - prev_start)
                
                # Then insert the new items
                for i in range(new_start, new_end):
                    operations.append(ArrayInsertOperation(
                        path=path,
                        index=i + offset,
                        value=new_array[i]
                    ))
                offset += (new_end - new_start)
                    
            elif op == 'delete':
                # Delete items
                for i in range(prev_end - 1, prev_start - 1, -1):
                    operations.append(ArrayDeleteOperation(
                        path=path,
                        index=i + offset,
                        old_value=previous_array[i]
                    ))
                offset -= (prev_end - prev_start)
                    
            elif op == 'insert':
                # Insert items
                for i in range(new_start, new_end):
                    operations.append(ArrayInsertOperation(
                        path=path,
                        index=i + offset,
                        value=new_array[i]
                    ))
                offset += (new_end - new_start)
                
        return operations
    
    def _detect_text_operations(self,
                              previous_text: str,
                              new_text: str,
                              path: List[str]) -> List[DeltaOperation]:
        """
        Detect text changes and generate operations.
        
        Uses difflib to identify text changes efficiently.
        
        Args:
            previous_text: Original text
            new_text: New text
            path: JSON path to the text field
            
        Returns:
            List of operations to transform previous_text to new_text
        """
        # If the texts are very different, just use a set operation
        if len(previous_text) == 0 or len(new_text) == 0 or len(previous_text) * 3 < len(new_text) or len(new_text) * 3 < len(previous_text):
            return [SetValueOperation(
                path=path,
                value=new_text,
                old_value=previous_text
            )]
            
        # For smaller diffs, use a text diff approach
        matcher = difflib.SequenceMatcher(None, previous_text, new_text)
        edits = []
        
        for op, prev_start, prev_end, new_start, new_end in matcher.get_opcodes():
            if op == 'equal':
                # No change, skip
                continue
                
            elif op == 'replace':
                edits.append(('replace', prev_start, new_text[new_start:new_end]))
                    
            elif op == 'delete':
                edits.append(('delete', prev_start, previous_text[prev_start:prev_end]))
                    
            elif op == 'insert':
                edits.append(('insert', prev_start, new_text[new_start:new_end]))
        
        # Simplify by using a single text diff operation if there are edits
        if edits:
            return [TextDiffOperation(path=path, edits=edits)]
        
        # No changes
        return []
    
    def optimize_operations(self, operations: List[DeltaOperation]) -> List[DeltaOperation]:
        """
        Optimize a list of operations to minimize redundancy.
        
        Args:
            operations: List of operations to optimize
            
        Returns:
            Optimized list of operations
        """
        if not operations:
            return []
            
        # Group operations by path
        path_ops: Dict[Tuple[str, ...], List[DeltaOperation]] = {}
        for op in operations:
            path_tuple = tuple(op.path)
            if path_tuple not in path_ops:
                path_ops[path_tuple] = []
            path_ops[path_tuple].append(op)
            
        # Optimize each path's operations
        result = []
        for path, ops in path_ops.items():
            # Skip paths with only one operation
            if len(ops) == 1:
                result.append(ops[0])
                continue
                
            # For multiple operations on the same path, only keep the last SetValueOperation
            # or the appropriate sequence of array operations
            if any(isinstance(op, SetValueOperation) for op in ops):
                # Find the last SetValueOperation
                last_set_op = None
                for op in reversed(ops):
                    if isinstance(op, SetValueOperation):
                        last_set_op = op
                        break
                        
                if last_set_op:
                    result.append(last_set_op)
            else:
                # Keep array operations in the correct order
                array_ops = [op for op in ops if isinstance(op, (ArrayInsertOperation, ArrayDeleteOperation))]
                text_ops = [op for op in ops if isinstance(op, TextDiffOperation)]
                
                if text_ops:
                    # Combine text operations
                    all_edits = []
                    for op in text_ops:
                        all_edits.extend(op.edits)
                    result.append(TextDiffOperation(path=list(path), edits=all_edits))
                
                # Add array operations in original order
                for op in ops:
                    if isinstance(op, (ArrayInsertOperation, ArrayDeleteOperation)):
                        result.append(op)
                        
        return result 
"""
Delta operations for the delta chain system.

This module defines the operations that can be applied in deltas,
which track changes to node content over time.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
import copy


class DeltaOperation(ABC):
    """
    Abstract base class for delta operations.
    
    Delta operations represent atomic changes to node content
    that can be applied and reversed.
    """
    
    @abstractmethod
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this operation to the given content.
        
        Args:
            content: The content to apply the operation to
            
        Returns:
            The updated content after applying the operation
        """
        pass
        
    @abstractmethod
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reverse this operation on the given content.
        
        Args:
            content: The content to reverse the operation on
            
        Returns:
            The updated content after reversing the operation
        """
        pass
        
    @abstractmethod
    def get_summary(self) -> str:
        """
        Get a human-readable summary of this operation.
        
        Returns:
            A string describing the operation
        """
        pass


class SetValueOperation(DeltaOperation):
    """
    Operation to set a value at a specified path in the content.
    """
    
    def __init__(self, path: List[str], value: Any, old_value: Optional[Any] = None):
        """
        Initialize a set value operation.
        
        Args:
            path: JSON path to the property
            value: New value to set
            old_value: Previous value (for reverse operations)
        """
        self.path = path
        self.value = copy.deepcopy(value)
        self.old_value = copy.deepcopy(old_value) if old_value is not None else None
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Set a value at the specified path."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the parent of the target path
        for key in self.path[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the value
        if self.path:
            target[self.path[-1]] = copy.deepcopy(self.value)
        
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Restore the previous value."""
        if self.old_value is None:
            raise ValueError("Cannot reverse operation without old_value")
        
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the parent of the target path
        for key in self.path[:-1]:
            if key not in target:
                return result  # Path doesn't exist, can't reverse
            target = target[key]
        
        # Restore the old value
        if self.path:
            target[self.path[-1]] = copy.deepcopy(self.old_value)
        
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        path_str = ".".join(self.path) if self.path else "root"
        return f"Set {path_str} to {type(self.value).__name__}"


class DeleteValueOperation(DeltaOperation):
    """
    Operation to delete a value at a specified path in the content.
    """
    
    def __init__(self, path: List[str], old_value: Any):
        """
        Initialize a delete value operation.
        
        Args:
            path: JSON path to the property
            old_value: Value to be deleted (for reverse operations)
        """
        self.path = path
        self.old_value = copy.deepcopy(old_value)
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a value at the specified path."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the parent of the target path
        for key in self.path[:-1]:
            if key not in target:
                return result  # Path doesn't exist, nothing to delete
            target = target[key]
        
        # Delete the value
        if self.path and self.path[-1] in target:
            del target[self.path[-1]]
        
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Restore the deleted value."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the parent of the target path
        for key in self.path[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Restore the deleted value
        if self.path:
            target[self.path[-1]] = copy.deepcopy(self.old_value)
        
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        path_str = ".".join(self.path) if self.path else "root"
        return f"Delete {path_str}"


class ArrayInsertOperation(DeltaOperation):
    """
    Operation to insert a value into an array at a specified index.
    """
    
    def __init__(self, path: List[str], index: int, value: Any):
        """
        Initialize an array insert operation.
        
        Args:
            path: JSON path to the array
            index: Index at which to insert the value
            value: Value to insert
        """
        self.path = path
        self.index = index
        self.value = copy.deepcopy(value)
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a value at the specified array index."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the array
        for key in self.path:
            if key not in target:
                target[key] = []
            target = target[key]
        
        # Ensure the target is a list
        if not isinstance(target, list):
            target = []
        
        # Insert the value
        index = min(self.index, len(target))
        target.insert(index, copy.deepcopy(self.value))
        
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Remove the inserted value."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the array
        for key in self.path:
            if key not in target:
                return result  # Path doesn't exist, can't reverse
            target = target[key]
        
        # Ensure the target is a list
        if not isinstance(target, list):
            return result
        
        # Remove the value if the index is valid
        if 0 <= self.index < len(target):
            del target[self.index]
        
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        path_str = ".".join(self.path) if self.path else "root"
        return f"Insert value at {path_str}[{self.index}]"


class ArrayDeleteOperation(DeltaOperation):
    """
    Operation to delete a value from an array at a specified index.
    """
    
    def __init__(self, path: List[str], index: int, old_value: Any):
        """
        Initialize an array delete operation.
        
        Args:
            path: JSON path to the array
            index: Index from which to delete the value
            old_value: Value to be deleted (for reverse operations)
        """
        self.path = path
        self.index = index
        self.old_value = copy.deepcopy(old_value)
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a value at the specified array index."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the array
        for key in self.path:
            if key not in target:
                return result  # Path doesn't exist, nothing to delete
            target = target[key]
        
        # Ensure the target is a list
        if not isinstance(target, list):
            return result
        
        # Remove the value if the index is valid
        if 0 <= self.index < len(target):
            del target[self.index]
        
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Restore the deleted array element."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the array
        for key in self.path:
            if key not in target:
                target[key] = []
            target = target[key]
        
        # Ensure the target is a list
        if not isinstance(target, list):
            target = []
        
        # Insert the value
        index = min(self.index, len(target))
        target.insert(index, copy.deepcopy(self.old_value))
        
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        path_str = ".".join(self.path) if self.path else "root"
        return f"Delete value at {path_str}[{self.index}]"


class TextDiffOperation(DeltaOperation):
    """
    Operation to modify text content using edit operations.
    This is more efficient than storing the full text for each change.
    """
    
    def __init__(self, path: List[str], edits: List[Tuple[str, int, str]]):
        """
        Initialize a text diff operation.
        
        Args:
            path: JSON path to the text field
            edits: List of (operation, position, text) tuples
                  operation can be 'insert', 'delete', or 'replace'
                  position is the character index in the text
                  text is the text to insert, delete, or use in replacement
        """
        self.path = path
        self.edits = edits
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Apply text edits."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the text field
        for key in self.path[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Get current text
        if self.path and self.path[-1] in target:
            text = target[self.path[-1]]
            if not isinstance(text, str):
                text = str(text)
        else:
            text = ""
        
        # Apply edits in reverse order to avoid position shifts
        sorted_edits = sorted(self.edits, key=lambda e: e[1], reverse=True)
        for op, pos, txt in sorted_edits:
            if op == 'insert':
                text = text[:pos] + txt + text[pos:]
            elif op == 'delete':
                text = text[:pos] + text[pos + len(txt):]
            elif op == 'replace':
                text = text[:pos] + txt + text[pos + len(txt):]
        
        # Set the updated text
        if self.path:
            target[self.path[-1]] = text
        
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse text edits."""
        result = copy.deepcopy(content)
        target = result
        
        # Navigate to the text field
        for key in self.path[:-1]:
            if key not in target:
                return result
            target = target[key]
        
        # Get current text
        if self.path and self.path[-1] in target:
            text = target[self.path[-1]]
            if not isinstance(text, str):
                text = str(text)
        else:
            return result
        
        # Apply inverse edits in forward order
        sorted_edits = sorted(self.edits, key=lambda e: e[1])
        for op, pos, txt in sorted_edits:
            if op == 'insert':
                # Reverse of insert is delete
                text = text[:pos] + text[pos + len(txt):]
            elif op == 'delete':
                # Reverse of delete is insert
                text = text[:pos] + txt + text[pos:]
            elif op == 'replace':
                # Need the original text for proper replacement
                # This is a simplification that might not work perfectly
                text = text[:pos] + txt + text[pos + len(txt):]
        
        # Set the updated text
        if self.path:
            target[self.path[-1]] = text
        
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        path_str = ".".join(self.path) if self.path else "root"
        edit_count = len(self.edits)
        return f"Text edits ({edit_count}) at {path_str}"


class CompositeOperation(DeltaOperation):
    """
    A composite operation that combines multiple operations.
    """
    
    def __init__(self, operations: List[DeltaOperation]):
        """
        Initialize a composite operation.
        
        Args:
            operations: List of operations to combine
        """
        self.operations = operations
    
    def apply(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all contained operations in sequence."""
        result = copy.deepcopy(content)
        for op in self.operations:
            result = op.apply(result)
        return result
    
    def reverse(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse all contained operations in reverse sequence."""
        result = copy.deepcopy(content)
        for op in reversed(self.operations):
            result = op.reverse(result)
        return result
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        op_count = len(self.operations)
        return f"Composite operation with {op_count} operations" 
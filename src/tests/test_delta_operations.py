"""
Unit tests for delta operations.

This module contains tests for the delta operations that track
changes to node content.
"""

import unittest
from uuid import uuid4
import copy

from ..delta.operations import (
    SetValueOperation,
    DeleteValueOperation,
    ArrayInsertOperation,
    ArrayDeleteOperation,
    TextDiffOperation,
    CompositeOperation
)


class TestSetValueOperation(unittest.TestCase):
    """Test cases for SetValueOperation."""
    
    def test_set_simple_value(self):
        """Test setting a simple value."""
        content = {"name": "Original"}
        op = SetValueOperation(path=["name"], value="Updated", old_value="Original")
        
        result = op.apply(content)
        self.assertEqual(result["name"], "Updated")
        self.assertEqual(content["name"], "Original")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["name"], "Original")
    
    def test_set_nested_value(self):
        """Test setting a nested value."""
        content = {"user": {"name": "Original", "age": 30}}
        op = SetValueOperation(path=["user", "name"], value="Updated", old_value="Original")
        
        result = op.apply(content)
        self.assertEqual(result["user"]["name"], "Updated")
        self.assertEqual(content["user"]["name"], "Original")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["user"]["name"], "Original")
    
    def test_set_missing_path(self):
        """Test setting a value at a missing path."""
        content = {}
        op = SetValueOperation(path=["user", "name"], value="New", old_value=None)
        
        result = op.apply(content)
        self.assertEqual(result["user"]["name"], "New")
        self.assertEqual(content, {})  # Original unchanged
    
    def test_reverse_missing_old_value(self):
        """Test reverse operation with missing old_value."""
        content = {"name": "Updated"}
        op = SetValueOperation(path=["name"], value="Updated", old_value=None)
        
        with self.assertRaises(ValueError):
            op.reverse(content)


class TestDeleteValueOperation(unittest.TestCase):
    """Test cases for DeleteValueOperation."""
    
    def test_delete_simple_value(self):
        """Test deleting a simple value."""
        content = {"name": "Test", "age": 30}
        op = DeleteValueOperation(path=["name"], old_value="Test")
        
        result = op.apply(content)
        self.assertNotIn("name", result)
        self.assertEqual(content["name"], "Test")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["name"], "Test")
    
    def test_delete_nested_value(self):
        """Test deleting a nested value."""
        content = {"user": {"name": "Test", "age": 30}}
        op = DeleteValueOperation(path=["user", "name"], old_value="Test")
        
        result = op.apply(content)
        self.assertNotIn("name", result["user"])
        self.assertEqual(content["user"]["name"], "Test")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["user"]["name"], "Test")
    
    def test_delete_missing_path(self):
        """Test deleting a value at a missing path."""
        content = {}
        op = DeleteValueOperation(path=["user", "name"], old_value="Test")
        
        result = op.apply(content)
        self.assertEqual(result, {})  # No change
        
        # Test reverse (should create the path)
        restored = op.reverse(result)
        self.assertEqual(restored["user"]["name"], "Test")


class TestArrayOperations(unittest.TestCase):
    """Test cases for array operations."""
    
    def test_array_insert(self):
        """Test inserting an array element."""
        content = {"items": ["a", "c"]}
        op = ArrayInsertOperation(path=["items"], index=1, value="b")
        
        result = op.apply(content)
        self.assertEqual(result["items"], ["a", "b", "c"])
        self.assertEqual(content["items"], ["a", "c"])  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["items"], ["a", "c"])
    
    def test_array_insert_empty(self):
        """Test inserting into an empty array."""
        content = {}
        op = ArrayInsertOperation(path=["items"], index=0, value="a")
        
        result = op.apply(content)
        self.assertEqual(result["items"], ["a"])
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["items"], [])
    
    def test_array_delete(self):
        """Test deleting an array element."""
        content = {"items": ["a", "b", "c"]}
        op = ArrayDeleteOperation(path=["items"], index=1, old_value="b")
        
        result = op.apply(content)
        self.assertEqual(result["items"], ["a", "c"])
        self.assertEqual(content["items"], ["a", "b", "c"])  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["items"], ["a", "b", "c"])
    
    def test_array_delete_invalid_index(self):
        """Test deleting an array element with invalid index."""
        content = {"items": ["a"]}
        op = ArrayDeleteOperation(path=["items"], index=5, old_value="x")
        
        result = op.apply(content)
        self.assertEqual(result["items"], ["a"])  # No change
        
        # Test reverse (should add at the end)
        restored = op.reverse(result)
        self.assertEqual(restored["items"], ["a", "x"])


class TestTextDiffOperation(unittest.TestCase):
    """Test cases for TextDiffOperation."""
    
    def test_text_insert(self):
        """Test inserting text."""
        content = {"text": "Hello world"}
        op = TextDiffOperation(path=["text"], edits=[
            ('insert', 5, " beautiful")
        ])
        
        result = op.apply(content)
        self.assertEqual(result["text"], "Hello beautiful world")
        self.assertEqual(content["text"], "Hello world")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["text"], "Hello world")
    
    def test_text_delete(self):
        """Test deleting text."""
        content = {"text": "Hello beautiful world"}
        op = TextDiffOperation(path=["text"], edits=[
            ('delete', 5, " beautiful")
        ])
        
        result = op.apply(content)
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(content["text"], "Hello beautiful world")  # Original unchanged
        
        # Test reverse
        restored = op.reverse(result)
        self.assertEqual(restored["text"], "Hello beautiful world")
    
    def test_text_replace(self):
        """Test replacing text."""
        content = {"text": "Hello world"}
        op = TextDiffOperation(path=["text"], edits=[
            ('replace', 0, "Hi")
        ])
        
        result = op.apply(content)
        self.assertEqual(result["text"], "Hi world")
        self.assertEqual(content["text"], "Hello world")  # Original unchanged
    
    def test_multiple_edits(self):
        """Test multiple text edits."""
        content = {"text": "Hello world"}
        op = TextDiffOperation(path=["text"], edits=[
            ('replace', 0, "Hi"),
            ('insert', 3, " beautiful")
        ])
        
        result = op.apply(content)
        self.assertEqual(result["text"], "Hi beautiful world")
        self.assertEqual(content["text"], "Hello world")  # Original unchanged


class TestCompositeOperation(unittest.TestCase):
    """Test cases for CompositeOperation."""
    
    def test_composite_operation(self):
        """Test composite operation with multiple operations."""
        content = {"name": "Original", "items": ["a", "c"]}
        
        ops = [
            SetValueOperation(path=["name"], value="Updated", old_value="Original"),
            ArrayInsertOperation(path=["items"], index=1, value="b")
        ]
        
        composite = CompositeOperation(operations=ops)
        result = composite.apply(content)
        
        self.assertEqual(result["name"], "Updated")
        self.assertEqual(result["items"], ["a", "b", "c"])
        self.assertEqual(content["name"], "Original")  # Original unchanged
        self.assertEqual(content["items"], ["a", "c"])  # Original unchanged
        
        # Test reverse (should apply in reverse order)
        restored = composite.reverse(result)
        self.assertEqual(restored["name"], "Original")
        self.assertEqual(restored["items"], ["a", "c"])


if __name__ == '__main__':
    unittest.main() 
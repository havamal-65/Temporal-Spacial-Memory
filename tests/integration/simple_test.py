"""
Simple test to debug import issues.
"""

import unittest
from src.core.node_v2 import Node


class SimpleTest(unittest.TestCase):
    def test_node_creation(self):
        """Test that we can create a Node from node_v2"""
        node = Node(
            content={"test": "value"},
            position=(1.0, 2.0, 3.0),
            connections=[]
        )
        self.assertEqual(node.content, {"test": "value"})
        self.assertEqual(node.position, (1.0, 2.0, 3.0))


if __name__ == '__main__':
    unittest.main() 
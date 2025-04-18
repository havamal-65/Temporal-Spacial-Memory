import unittest
import tempfile
import os
import time
from uuid import uuid4, UUID
from src.core.node_v2 import Node, NodeConnection
from src.storage.sqlite_store import SQLiteNodeStore

class TestSQLiteNodeStore(unittest.TestCase):
    def setUp(self):
        # Use in-memory DB for all tests except persistence
        test_name = self._testMethodName
        if test_name == "test_persistence":
            self.db_path = f"C:/Users/evbon/AppData/Local/Temp/sqlite_test_{uuid4()}.db"
        else:
            self.db_path = ":memory:"
        self.store = SQLiteNodeStore(self.db_path, timeout=10.0)

    def tearDown(self):
        # Explicitly close and delete the store before removing the file
        if hasattr(self, 'store'):
            self.store.close()
            del self.store
        if self.db_path != ":memory:" and os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass  # If still locked, skip deletion for now

    def make_node(self, **kwargs):
        return Node(
            content=kwargs.get('content', {'text': 'test'}),
            position=kwargs.get('position', (1.0, 2.0, 3.0)),
            connections=kwargs.get('connections', []),
            origin_reference=kwargs.get('origin_reference'),
            delta_information=kwargs.get('delta_information', {}),
            metadata=kwargs.get('metadata', {})
        )

    def test_put_and_get(self):
        node = self.make_node()
        self.store.put(node)
        fetched = self.store.get(node.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, node.id)
        self.assertEqual(fetched.content, node.content)
        self.assertEqual(fetched.position, node.position)

    def test_overwrite_node(self):
        node = self.make_node()
        self.store.put(node)
        node.content['text'] = 'updated'
        self.store.put(node)
        fetched = self.store.get(node.id)
        self.assertEqual(fetched.content['text'], 'updated')

    def test_delete_and_exists(self):
        node = self.make_node()
        self.store.put(node)
        self.assertTrue(self.store.exists(node.id))
        deleted = self.store.delete(node.id)
        self.assertTrue(deleted)
        self.assertFalse(self.store.exists(node.id))
        self.assertIsNone(self.store.get(node.id))
        self.assertFalse(self.store.delete(node.id))  # Deleting again returns False

    def test_list_ids_and_count(self):
        nodes = [self.make_node() for _ in range(5)]
        for node in nodes:
            self.store.put(node)
        ids = self.store.list_ids()
        self.assertEqual(set(ids), set(n.id for n in nodes))
        self.assertEqual(self.store.count(), 5)

    def test_get_many_and_put_many(self):
        nodes = [self.make_node() for _ in range(3)]
        self.store.put_many(nodes)
        ids = [n.id for n in nodes]
        result = self.store.get_many(ids)
        self.assertEqual(set(result.keys()), set(ids))
        # Test with some missing IDs
        missing_id = uuid4()
        result = self.store.get_many(ids + [missing_id])
        self.assertEqual(set(result.keys()), set(ids))

    def test_serialization_complex_fields(self):
        conn = NodeConnection(
            target_id=uuid4(),
            connection_type='ref',
            strength=0.5,
            metadata={'foo': 'bar'}
        )
        node = self.make_node(
            content={'nested': {'a': 1, 'b': [2, 3]}},
            connections=[conn],
            delta_information={'change': 'added'},
            metadata={'tags': ['a', 'b']}
        )
        self.store.put(node)
        fetched = self.store.get(node.id)
        self.assertEqual(fetched.content, node.content)
        self.assertEqual(len(fetched.connections), 1)
        self.assertEqual(fetched.delta_information, node.delta_information)
        self.assertEqual(fetched.metadata, node.metadata)
        self.assertEqual(fetched.connections[0].connection_type, 'ref')
        self.assertEqual(fetched.connections[0].metadata['foo'], 'bar')

    def test_empty_database(self):
        self.assertEqual(self.store.count(), 0)
        self.assertEqual(self.store.list_ids(), [])
        self.assertIsNone(self.store.get(uuid4()))
        self.assertEqual(self.store.get_many([]), {})

    def test_persistence(self):
        node = self.make_node()
        self.store.put(node)
        self.store.close()
        del self.store
        reopened = SQLiteNodeStore(self.db_path, timeout=10.0)
        fetched = reopened.get(node.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, node.id)
        reopened.close()
        del reopened
        time.sleep(0.1)

    def test_invalid_db_path(self):
        # Should raise an error if path is invalid
        with self.assertRaises(Exception):
            SQLiteNodeStore('/invalid/path/to/db.sqlite')

if __name__ == '__main__':
    unittest.main() 
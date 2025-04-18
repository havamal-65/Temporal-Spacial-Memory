import time
import sqlite3
from uuid import uuid4

# Import your NodeStore (update the import as needed)
try:
    from src.storage.sqlite_store import SQLiteNodeStore
    from src.core.node_v2 import Node
except ImportError:
    SQLiteNodeStore = None
    Node = None

INCREMENTS = [10000 * i for i in range(1, 11)]  # 10k to 100k


def benchmark_your_system(num_nodes):
    if SQLiteNodeStore is None or Node is None:
        print("Your system's NodeStore or Node class could not be imported.")
        return None
    store = SQLiteNodeStore(":memory:")
    start = time.time()
    for i in range(num_nodes):
        node = Node(
            id=uuid4(),
            content={"text": f"Node {i}"},
            position=(float(i), 1.0, 0.0),
            connections=[],
            origin_reference=None,
            delta_information={},
            metadata={}
        )
        store.put(node)
    end = time.time()
    return end - start

def benchmark_sqlite(num_nodes):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, data TEXT)")
    start = time.time()
    for i in range(num_nodes):
        conn.execute("INSERT INTO nodes (data) VALUES (?)", (f"Node {i}",))
    conn.commit()
    end = time.time()
    return end - start

if __name__ == "__main__":
    print("Benchmarking node creation speed for increments of 10k up to 100k nodes...")
    print(f"{'Nodes':>8} | {'Your System (s)':>16} | {'SQLite (s)':>10}")
    print("-" * 40)
    for num_nodes in INCREMENTS:
        sys_time = benchmark_your_system(num_nodes)
        sqlite_time = benchmark_sqlite(num_nodes)
        print(f"{num_nodes:8} | {sys_time:16.4f} | {sqlite_time:10.4f}") 
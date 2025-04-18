"""
Basic usage example for the Temporal-Spatial Knowledge Database.

This example demonstrates how to create, store, and query nodes with 
spatial and temporal coordinates.
"""

# Removed RocksDB and related imports
# import os
# import shutil
# from datetime import datetime, timedelta
# import random

# from src.core.node import Node
# from src.core.coordinates import Coordinates, SpatialCoordinate, TemporalCoordinate
# from src.storage.rocksdb_store import RocksDBNodeStore
# from src.indexing.combined_index import CombinedIndex
from src.utils.graphrag_adapter import GraphRAGAdapter
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def minimal_narrative_ingest_and_summary():
    # Minimal sample text (replace with larger text for scaling)
    sample_text = """
    Bilbo Baggins is visited by Gandalf and a group of dwarves. They set out on an adventure to reclaim the Lonely Mountain from the dragon Smaug. Along the way, they encounter trolls, goblins, elves, and giant spiders. Bilbo finds a magic ring and becomes a hero.
    """
    print("Extracting knowledge graph from sample narrative...")
    adapter = GraphRAGAdapter(project_name="mvp_test")
    kg = adapter.extract_knowledge_graph(sample_text)
    print(f"Extracted {len(kg.get('nodes', []))} nodes and {len(kg.get('edges', []))} edges.")

    print("Converting to mesh nodes and applying branching logic...")
    mesh_nodes = adapter.convert_to_mesh_nodes(kg)
    print(f"Total mesh nodes: {len(mesh_nodes)}")

    # Print summary of central topics and branches
    central_nodes = [n for n in mesh_nodes if not n.metadata.get('branch')]
    branch_nodes = [n for n in mesh_nodes if n.metadata.get('branch')]
    print(f"Central topics (not branched): {len(central_nodes)}")
    for node in central_nodes:
        print(f"  - {getattr(node, 'name', node.content.get('name', ''))} (type: {getattr(node, 'type', node.content.get('type', ''))})")
    print(f"Branches: {len(branch_nodes)}")
    for node in branch_nodes:
        print(f"  - {getattr(node, 'name', node.content.get('name', ''))} (type: {getattr(node, 'type', node.content.get('type', ''))})")

    # Simple summary: print a sentence for each branch
    print("\nSummary by branch:")
    for node in branch_nodes:
        summary = node.content.get('name', str(node))
        print(f"Branch: {summary}")


if __name__ == "__main__":
    minimal_narrative_ingest_and_summary() 
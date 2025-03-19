#!/usr/bin/env python3
"""
Benchmark script to compare the Mesh Tube Knowledge Database
with a traditional document-based database approach.
"""

import os
import sys
import time
import random
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.mesh_tube import MeshTube
from src.utils.position_calculator import PositionCalculator


class DocumentDatabase:
    """
    A simplified document database implementation for comparison.
    This simulates a MongoDB-like approach with collections and documents.
    """
    
    def __init__(self, name: str, storage_path: str = None):
        """Initialize a new document database"""
        self.name = name
        self.storage_path = storage_path
        self.docs = {}  # id -> document mapping
        self.created_at = datetime.now()
        self.last_modified = self.created_at
        
        # Create indexes
        self.time_index = {}      # time -> [doc_ids]
        self.topic_index = {}     # topic -> [doc_ids]
        self.connection_index = {}  # doc_id -> [connected_doc_ids]
    
    def add_document(self, content: Dict[str, Any], 
                    time: float, 
                    distance: float, 
                    angle: float,
                    parent_id: str = None) -> Dict[str, Any]:
        """Add a new document to the database"""
        doc_id = f"doc_{len(self.docs) + 1}"
        
        doc = {
            "doc_id": doc_id,
            "content": content,
            "time": time,
            "distance": distance,
            "angle": angle,
            "parent_id": parent_id,
            "created_at": datetime.now().isoformat(),
            "connections": [],
            "delta_references": [parent_id] if parent_id else []
        }
        
        self.docs[doc_id] = doc
        self.last_modified = datetime.now()
        
        # Update indexes
        time_key = round(time, 2)  # Round to handle floating point comparison
        if time_key not in self.time_index:
            self.time_index[time_key] = []
        self.time_index[time_key].append(doc_id)
        
        # Topic index
        if "topic" in content:
            topic = content["topic"]
            if topic not in self.topic_index:
                self.topic_index[topic] = []
            self.topic_index[topic].append(doc_id)
        
        return doc
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve a document by ID"""
        return self.docs.get(doc_id)
    
    def connect_documents(self, doc_id1: str, doc_id2: str) -> bool:
        """Create bidirectional connection between documents"""
        if doc_id1 not in self.docs or doc_id2 not in self.docs:
            return False
        
        # Add connections
        if doc_id2 not in self.docs[doc_id1]["connections"]:
            self.docs[doc_id1]["connections"].append(doc_id2)
            
        if doc_id1 not in self.docs[doc_id2]["connections"]:
            self.docs[doc_id2]["connections"].append(doc_id1)
        
        # Update connection index
        if doc_id1 not in self.connection_index:
            self.connection_index[doc_id1] = []
        if doc_id2 not in self.connection_index:
            self.connection_index[doc_id2] = []
            
        self.connection_index[doc_id1].append(doc_id2)
        self.connection_index[doc_id2].append(doc_id1)
        
        self.last_modified = datetime.now()
        return True
    
    def get_documents_by_time(self, time: float, tolerance: float = 0.1) -> List[Dict[str, Any]]:
        """Get documents within a specific time range"""
        results = []
        for t in self.time_index:
            if abs(t - time) <= tolerance:
                for doc_id in self.time_index[t]:
                    results.append(self.docs[doc_id])
        return results
    
    def apply_delta(self, 
                   original_doc_id: str, 
                   delta_content: Dict[str, Any],
                   time: float,
                   distance: float = None,
                   angle: float = None) -> Dict[str, Any]:
        """Create a new document that represents a delta from original"""
        original_doc = self.get_document(original_doc_id)
        if not original_doc:
            return None
            
        # Use original values if not provided
        if distance is None:
            distance = original_doc["distance"]
            
        if angle is None:
            angle = original_doc["angle"]
            
        # Create delta document
        delta_doc = self.add_document(
            content=delta_content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=original_doc_id
        )
        
        return delta_doc
    
    def compute_document_state(self, doc_id: str) -> Dict[str, Any]:
        """Compute full state by applying all deltas in the chain"""
        doc = self.get_document(doc_id)
        if not doc:
            return {}
            
        if not doc["delta_references"]:
            return doc["content"]
            
        # Get the delta chain
        chain = [doc]
        processed_ids = {doc_id}
        queue = [ref for ref in doc["delta_references"] if ref]
        
        while queue:
            ref_id = queue.pop(0)
            if ref_id in processed_ids:
                continue
                
            ref_doc = self.get_document(ref_id)
            if ref_doc:
                chain.append(ref_doc)
                processed_ids.add(ref_id)
                
                for new_ref in ref_doc["delta_references"]:
                    if new_ref and new_ref not in processed_ids:
                        queue.append(new_ref)
        
        # Apply deltas in chronological order
        computed_state = {}
        for delta_doc in sorted(chain, key=lambda d: d["time"]):
            computed_state.update(delta_doc["content"])
            
        return computed_state
    
    def save(self, filepath: str = None) -> None:
        """Save database to JSON file"""
        if not filepath and not self.storage_path:
            raise ValueError("No storage path provided")
            
        save_path = filepath or os.path.join(self.storage_path, f"{self.name}.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        data = {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "documents": self.docs
        }
        
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'DocumentDatabase':
        """Load database from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        storage_path = os.path.dirname(filepath)
        db = cls(name=data["name"], storage_path=storage_path)
        
        db.created_at = datetime.fromisoformat(data["created_at"])
        db.last_modified = datetime.fromisoformat(data["last_modified"])
        db.docs = data["documents"]
        
        # Rebuild indexes
        for doc_id, doc in db.docs.items():
            # Time index
            time_key = round(doc["time"], 2)
            if time_key not in db.time_index:
                db.time_index[time_key] = []
            db.time_index[time_key].append(doc_id)
            
            # Topic index
            if "content" in doc and "topic" in doc["content"]:
                topic = doc["content"]["topic"]
                if topic not in db.topic_index:
                    db.topic_index[topic] = []
                db.topic_index[topic].append(doc_id)
                
            # Connection index
            if "connections" in doc:
                db.connection_index[doc_id] = doc["connections"]
        
        return db


def calculate_distance(doc1: Dict[str, Any], doc2: Dict[str, Any]) -> float:
    """Calculate spatial distance between two documents"""
    r1, theta1, z1 = doc1["distance"], doc1["angle"], doc1["time"]
    r2, theta2, z2 = doc2["distance"], doc2["angle"], doc2["time"]
    
    theta1_rad = (theta1 * 3.14159) / 180
    theta2_rad = (theta2 * 3.14159) / 180
    
    distance = (r1**2 + r2**2 - 
                2 * r1 * r2 * math.cos(theta1_rad - theta2_rad) + 
                (z1 - z2)**2) ** 0.5
    
    return distance


def benchmark_db_operation(func, iterations=10):
    """Run a benchmark function and report the average time"""
    times = []
    results = None
    
    for i in range(iterations):
        start_time = time.time()
        results = func()
        end_time = time.time()
        times.append(end_time - start_time)
    
    return {
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
        "results": results
    }


def create_test_data(num_nodes=100, num_connections=200, num_deltas=50):
    """Create test data for both database types"""
    print(f"Creating test data with {num_nodes} nodes, {num_connections} connections, {num_deltas} deltas...")
    
    # Generate topics
    topics = [
        "Artificial Intelligence", "Machine Learning", "Deep Learning", 
        "Natural Language Processing", "Computer Vision", "Reinforcement Learning",
        "Neural Networks", "Data Science", "Robotics", "Quantum Computing",
        "Blockchain", "Cybersecurity", "Internet of Things", "Augmented Reality",
        "Virtual Reality", "Cloud Computing", "Edge Computing", "Big Data",
        "Bioinformatics", "Autonomous Vehicles"
    ]
    
    # Create test data
    mesh_tube = MeshTube(name="Benchmark Mesh", storage_path="benchmark_data")
    doc_db = DocumentDatabase(name="Benchmark Doc DB", storage_path="benchmark_data")
    
    # Track node/document mappings for later use
    mesh_nodes = []
    doc_ids = []
    
    # Create nodes/documents
    for i in range(num_nodes):
        # Generate random position
        time = random.uniform(0, 10)
        distance = random.uniform(0.1, 5.0)
        angle = random.uniform(0, 360)
        
        # Select random topic
        topic = random.choice(topics)
        content = {
            "topic": topic,
            "description": f"Description for {topic}",
            "metadata": {
                "created_by": f"user_{random.randint(1, 10)}",
                "priority": random.randint(1, 5)
            }
        }
        
        # Add to mesh tube
        node = mesh_tube.add_node(
            content=content,
            time=time,
            distance=distance,
            angle=angle
        )
        mesh_nodes.append(node)
        
        # Add to document db
        doc = doc_db.add_document(
            content=content,
            time=time,
            distance=distance,
            angle=angle
        )
        doc_ids.append(doc["doc_id"])
    
    # Create connections
    for _ in range(num_connections):
        # Select random nodes/docs to connect
        idx1 = random.randint(0, len(mesh_nodes) - 1)
        idx2 = random.randint(0, len(mesh_nodes) - 1)
        
        if idx1 != idx2:
            # Connect in mesh tube
            mesh_tube.connect_nodes(
                mesh_nodes[idx1].node_id, 
                mesh_nodes[idx2].node_id
            )
            
            # Connect in doc db
            doc_db.connect_documents(
                doc_ids[idx1],
                doc_ids[idx2]
            )
    
    # Create deltas (updates)
    for _ in range(num_deltas):
        # Select random node/doc to update
        idx = random.randint(0, len(mesh_nodes) - 1)
        
        # Create delta content
        delta_content = {
            "update_version": random.randint(1, 5),
            "updated_info": f"Update {random.randint(1000, 9999)}",
            "tags": [f"tag_{random.randint(1, 10)}" for _ in range(3)]
        }
        
        # Get time for update (always after the original)
        original_time = mesh_nodes[idx].time
        update_time = original_time + random.uniform(0.5, 3.0)
        
        # Apply delta in mesh tube
        mesh_update = mesh_tube.apply_delta(
            original_node=mesh_nodes[idx],
            delta_content=delta_content,
            time=update_time
        )
        
        # Apply delta in doc db
        doc_update = doc_db.apply_delta(
            original_doc_id=doc_ids[idx],
            delta_content=delta_content,
            time=update_time
        )
    
    # Save databases for testing
    os.makedirs("benchmark_data", exist_ok=True)
    mesh_tube.save("benchmark_data/mesh_benchmark.json")
    doc_db.save("benchmark_data/doc_benchmark.json")
    
    return mesh_tube, doc_db


def run_benchmarks(mesh_tube, doc_db):
    """Run various benchmarks on both database types"""
    print("\nRunning benchmarks...\n")
    benchmark_results = {}
    
    # 1. Query by time slice
    print("Benchmark: Query by time slice")
    
    # Mesh Tube time slice query
    def mesh_time_query():
        return mesh_tube.get_temporal_slice(time=5.0, tolerance=0.5)
    
    mesh_time_result = benchmark_db_operation(mesh_time_query)
    print(f"  Mesh Tube: {mesh_time_result['avg_time']:.6f}s (found {len(mesh_time_result['results'])} nodes)")
    
    # Document DB time slice query
    def doc_time_query():
        return doc_db.get_documents_by_time(time=5.0, tolerance=0.5)
    
    doc_time_result = benchmark_db_operation(doc_time_query)
    print(f"  Document DB: {doc_time_result['avg_time']:.6f}s (found {len(doc_time_result['results'])} documents)")
    
    benchmark_results["time_slice_query"] = {
        "mesh_tube": mesh_time_result,
        "doc_db": doc_time_result
    }
    
    # 2. Compute delta state
    print("\nBenchmark: Compute node state with delta encoding")
    
    # Find nodes with deltas
    mesh_delta_nodes = [node for node in mesh_tube.nodes.values() 
                      if node.delta_references]
    doc_delta_docs = [doc_id for doc_id, doc in doc_db.docs.items() 
                    if doc["delta_references"]]
    
    if mesh_delta_nodes and doc_delta_docs:
        # Select a random node with deltas
        mesh_delta_node = random.choice(mesh_delta_nodes)
        doc_delta_id = random.choice(doc_delta_docs)
        
        # Mesh Tube compute state
        def mesh_compute_state():
            return mesh_tube.compute_node_state(mesh_delta_node.node_id)
        
        mesh_state_result = benchmark_db_operation(mesh_compute_state)
        print(f"  Mesh Tube: {mesh_state_result['avg_time']:.6f}s")
        
        # Document DB compute state
        def doc_compute_state():
            return doc_db.compute_document_state(doc_delta_id)
        
        doc_state_result = benchmark_db_operation(doc_compute_state)
        print(f"  Document DB: {doc_state_result['avg_time']:.6f}s")
        
        benchmark_results["compute_state"] = {
            "mesh_tube": mesh_state_result,
            "doc_db": doc_state_result
        }
    
    # 3. Find nearest nodes
    print("\nBenchmark: Find nearest nodes (spatial query)")
    
    # Select a random reference node
    mesh_ref_node = random.choice(list(mesh_tube.nodes.values()))
    doc_ref_id = random.choice(list(doc_db.docs.keys()))
    doc_ref = doc_db.get_document(doc_ref_id)
    
    # Mesh Tube nearest nodes
    def mesh_nearest_nodes():
        return mesh_tube.get_nearest_nodes(mesh_ref_node, limit=10)
    
    mesh_nearest_result = benchmark_db_operation(mesh_nearest_nodes)
    print(f"  Mesh Tube: {mesh_nearest_result['avg_time']:.6f}s")
    
    # Document DB nearest docs (manual implementation for comparison)
    def doc_nearest_docs():
        distances = []
        for doc_id, doc in doc_db.docs.items():
            if doc_id == doc_ref_id:
                continue
            dist = calculate_distance(doc_ref, doc)
            distances.append((doc, dist))
        distances.sort(key=lambda x: x[1])
        return distances[:10]
    
    doc_nearest_result = benchmark_db_operation(doc_nearest_docs)
    print(f"  Document DB: {doc_nearest_result['avg_time']:.6f}s")
    
    benchmark_results["nearest_nodes"] = {
        "mesh_tube": mesh_nearest_result,
        "doc_db": doc_nearest_result
    }
    
    # 4. Basic retrieval
    print("\nBenchmark: Basic node/document retrieval")
    
    # Select a random node/doc ID
    mesh_node_id = random.choice(list(mesh_tube.nodes.keys()))
    doc_id = random.choice(list(doc_db.docs.keys()))
    
    # Mesh Tube get node
    def mesh_get_node():
        return mesh_tube.get_node(mesh_node_id)
    
    mesh_get_result = benchmark_db_operation(mesh_get_node)
    print(f"  Mesh Tube: {mesh_get_result['avg_time']:.6f}s")
    
    # Document DB get document
    def doc_get_doc():
        return doc_db.get_document(doc_id)
    
    doc_get_result = benchmark_db_operation(doc_get_doc)
    print(f"  Document DB: {doc_get_result['avg_time']:.6f}s")
    
    benchmark_results["basic_retrieval"] = {
        "mesh_tube": mesh_get_result,
        "doc_db": doc_get_result
    }
    
    # 5. Save to disk
    print("\nBenchmark: Save database to disk")
    
    # Mesh Tube save
    def mesh_save():
        mesh_tube.save("benchmark_data/mesh_benchmark_test.json")
        return True
    
    mesh_save_result = benchmark_db_operation(mesh_save)
    mesh_file_size = os.path.getsize("benchmark_data/mesh_benchmark_test.json")
    print(f"  Mesh Tube: {mesh_save_result['avg_time']:.6f}s (file size: {mesh_file_size/1024:.2f} KB)")
    
    # Document DB save
    def doc_save():
        doc_db.save("benchmark_data/doc_benchmark_test.json")
        return True
    
    doc_save_result = benchmark_db_operation(doc_save)
    doc_file_size = os.path.getsize("benchmark_data/doc_benchmark_test.json")
    print(f"  Document DB: {doc_save_result['avg_time']:.6f}s (file size: {doc_file_size/1024:.2f} KB)")
    
    benchmark_results["save_to_disk"] = {
        "mesh_tube": {**mesh_save_result, "file_size": mesh_file_size},
        "doc_db": {**doc_save_result, "file_size": doc_file_size}
    }
    
    # 6. Load from disk
    print("\nBenchmark: Load database from disk")
    
    # Mesh Tube load
    def mesh_load():
        return MeshTube.load("benchmark_data/mesh_benchmark.json")
    
    mesh_load_result = benchmark_db_operation(mesh_load)
    print(f"  Mesh Tube: {mesh_load_result['avg_time']:.6f}s")
    
    # Document DB load
    def doc_load():
        return DocumentDatabase.load("benchmark_data/doc_benchmark.json")
    
    doc_load_result = benchmark_db_operation(doc_load)
    print(f"  Document DB: {doc_load_result['avg_time']:.6f}s")
    
    benchmark_results["load_from_disk"] = {
        "mesh_tube": mesh_load_result,
        "doc_db": doc_load_result
    }
    
    # 7. Knowledge Traversal (Complex Query)
    print("\nBenchmark: Knowledge Traversal (Complex Query)")
    print("  This test simulates how an AI might traverse knowledge to maintain context")
    
    # For Mesh Tube
    def mesh_knowledge_traversal():
        # 1. Start with a random node
        start_node = random.choice(list(mesh_tube.nodes.values()))
        
        # 2. Find its nearest conceptual neighbors (spatial proximity)
        neighbors = mesh_tube.get_nearest_nodes(start_node, limit=5)
        neighbor_nodes = [node for node, _ in neighbors]
        
        # 3. Follow connections to related topics
        connected_nodes = []
        for node in neighbor_nodes:
            for conn_id in node.connections:
                conn_node = mesh_tube.get_node(conn_id)
                if conn_node:
                    connected_nodes.append(conn_node)
        
        # 4. For each connected node, get its temporal evolution (deltas)
        results = []
        for node in connected_nodes[:5]:  # Limit to 5 to keep test manageable
            # Find all nodes that reference this one
            delta_nodes = [n for n in mesh_tube.nodes.values() 
                          if node.node_id in n.delta_references]
            
            # Compute full state at latest point
            if delta_nodes:
                latest_node = max(delta_nodes, key=lambda n: n.time)
                computed_state = mesh_tube.compute_node_state(latest_node.node_id)
                results.append(computed_state)
            else:
                results.append(node.content)
        
        return results
    
    mesh_traversal_result = benchmark_db_operation(mesh_knowledge_traversal)
    print(f"  Mesh Tube: {mesh_traversal_result['avg_time']:.6f}s")
    
    # For Document DB
    def doc_knowledge_traversal():
        # 1. Start with a random document
        start_doc_id = random.choice(list(doc_db.docs.keys()))
        start_doc = doc_db.get_document(start_doc_id)
        
        # 2. Find nearest conceptual neighbors (spatial proximity)
        distances = []
        for doc_id, doc in doc_db.docs.items():
            if doc_id == start_doc_id:
                continue
            dist = calculate_distance(start_doc, doc)
            distances.append((doc, dist))
        
        distances.sort(key=lambda x: x[1])
        neighbor_docs = [doc for doc, _ in distances[:5]]
        
        # 3. Follow connections to related topics
        connected_docs = []
        for doc in neighbor_docs:
            for conn_id in doc["connections"]:
                conn_doc = doc_db.get_document(conn_id)
                if conn_doc:
                    connected_docs.append(conn_doc)
        
        # 4. For each connected doc, get its temporal evolution (deltas)
        results = []
        for doc in connected_docs[:5]:  # Limit to 5 to keep test manageable
            # Find all docs that reference this one
            delta_docs = []
            for d_id, d in doc_db.docs.items():
                if "delta_references" in d and doc["doc_id"] in d["delta_references"]:
                    delta_docs.append(d)
            
            # Compute full state at latest point
            if delta_docs:
                latest_doc = max(delta_docs, key=lambda d: d["time"])
                computed_state = doc_db.compute_document_state(latest_doc["doc_id"])
                results.append(computed_state)
            else:
                results.append(doc["content"])
        
        return results
    
    doc_traversal_result = benchmark_db_operation(doc_knowledge_traversal)
    print(f"  Document DB: {doc_traversal_result['avg_time']:.6f}s")
    
    benchmark_results["knowledge_traversal"] = {
        "mesh_tube": mesh_traversal_result,
        "doc_db": doc_traversal_result
    }
    
    return benchmark_results


def print_summary(benchmark_results):
    """Print a summary of benchmark results"""
    print("\n" + "=" * 50)
    print("BENCHMARK SUMMARY")
    print("=" * 50)
    
    # Format data for the table
    rows = []
    for test_name, results in benchmark_results.items():
        mesh_time = results["mesh_tube"]["avg_time"]
        doc_time = results["doc_db"]["avg_time"]
        
        # Calculate performance ratio
        if mesh_time > 0 and doc_time > 0:
            if mesh_time < doc_time:
                ratio = f"{doc_time/mesh_time:.2f}x faster"
            else:
                ratio = f"{mesh_time/doc_time:.2f}x slower"
        else:
            ratio = "N/A"
            
        # Format test name
        display_name = test_name.replace("_", " ").title()
        
        rows.append([
            display_name,
            f"{mesh_time:.6f}s",
            f"{doc_time:.6f}s",
            ratio
        ])
    
    # Add file size comparison if available
    if "save_to_disk" in benchmark_results:
        mesh_size = benchmark_results["save_to_disk"]["mesh_tube"]["file_size"] / 1024
        doc_size = benchmark_results["save_to_disk"]["doc_db"]["file_size"] / 1024
        
        if mesh_size < doc_size:
            size_ratio = f"{doc_size/mesh_size:.2f}x smaller"
        else:
            size_ratio = f"{mesh_size/doc_size:.2f}x larger"
            
        rows.append([
            "File Size",
            f"{mesh_size:.2f} KB",
            f"{doc_size:.2f} KB",
            size_ratio
        ])
    
    # Print the table
    col_widths = [
        max(len(row[0]) for row in rows) + 2,
        max(len(row[1]) for row in rows) + 2,
        max(len(row[2]) for row in rows) + 2,
        max(len(row[3]) for row in rows) + 2
    ]
    
    # Print header
    header = [
        "Test".ljust(col_widths[0]),
        "Mesh Tube".ljust(col_widths[1]),
        "Document DB".ljust(col_widths[2]),
        "Comparison".ljust(col_widths[3])
    ]
    print("".join(header))
    print("-" * sum(col_widths))
    
    # Print rows
    for row in rows:
        formatted_row = [
            row[0].ljust(col_widths[0]),
            row[1].ljust(col_widths[1]),
            row[2].ljust(col_widths[2]),
            row[3].ljust(col_widths[3])
        ]
        print("".join(formatted_row))
    
    print("\nAnalysis:")
    print("- The Mesh Tube database is specially designed for temporal-spatial queries")
    print("- The Document database represents a more traditional approach")
    print("- Performance differences highlight the strengths of each approach")
    print("- Real-world applications would depend on specific use cases and query patterns")


def main():
    """Run the benchmark suite"""
    print("Mesh Tube vs Document Database Benchmark")
    print("========================================\n")
    
    # Check if benchmark data already exists
    if (os.path.exists("benchmark_data/mesh_benchmark.json") and 
        os.path.exists("benchmark_data/doc_benchmark.json")):
        print("Loading existing benchmark data...")
        mesh_tube = MeshTube.load("benchmark_data/mesh_benchmark.json")
        doc_db = DocumentDatabase.load("benchmark_data/doc_benchmark.json")
    else:
        # Create test data if it doesn't exist
        mesh_tube, doc_db = create_test_data(
            num_nodes=1000,
            num_connections=2500,
            num_deltas=500
        )
    
    # Run benchmarks
    benchmark_results = run_benchmarks(mesh_tube, doc_db)
    
    # Print summary
    print_summary(benchmark_results)


if __name__ == "__main__":
    import math  # Needed for distance calculations
    main() 
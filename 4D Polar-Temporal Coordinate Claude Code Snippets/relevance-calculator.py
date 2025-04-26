"""
Relevance Calculator for 4D Polar-Temporal Database

This module calculates the relevance score (r dimension) using a hybrid approach:
r(c,q,t) = α·r_semantic(c,q) + β·r_graph(c,q) + γ·r_temporal(c,t)

It integrates with FAISS for semantic similarity calculations.
"""

import numpy as np
import faiss
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
import networkx as nx


class RelevanceCalculator:
    """
    Calculates hybrid relevance scores for the radial dimension of the 4D space.
    """
    
    def __init__(self, 
                 embedding_dim: int = 1536,
                 use_gpu: bool = True,
                 alpha: float = 0.4,  # Semantic relevance weight
                 beta: float = 0.4,   # Graph relevance weight
                 gamma: float = 0.2): # Temporal relevance weight
        """
        Initialize the relevance calculator.
        
        Args:
            embedding_dim: Dimension of embeddings
            use_gpu: Whether to use GPU acceleration for FAISS
            alpha: Weight for semantic relevance
            beta: Weight for graph relevance
            gamma: Weight for temporal relevance
        """
        self.embedding_dim = embedding_dim
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        
        # Verify weights sum to 1
        assert abs(alpha + beta + gamma - 1.0) < 1e-6, "Weights must sum to 1"
        
        # Initialize FAISS index for semantic similarity
        self.index = faiss.IndexFlatL2(embedding_dim)
        
        # Use GPU if available and requested
        if use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_gpu(
                faiss.StandardGpuResources(), 0, self.index
            )
            self.using_gpu = True
        else:
            self.using_gpu = False
            
        # Initialize knowledge graph for structural relevance
        self.graph = nx.DiGraph()
        
        # Mapping of IDs to FAISS indices
        self.id_to_index = {}
        self.index_to_id = {}
        
        # Temporal information storage
        self.creation_times = {}
        self.last_access_times = {}
        self.reference_count = {}
        
    def add_item(self, 
                 item_id: str, 
                 embedding: np.ndarray, 
                 creation_time: datetime,
                 related_ids: Optional[List[str]] = None) -> None:
        """
        Add an item to the relevance system.
        
        Args:
            item_id: Unique identifier for the item
            embedding: Vector embedding of the item
            creation_time: When the item was created
            related_ids: IDs of related items for graph relevance
        """
        # Normalize embedding
        embedding = embedding.astype(np.float32).reshape(1, self.embedding_dim)
        norm_embedding = embedding / np.linalg.norm(embedding)
        
        # Add to FAISS index
        index = self.index.ntotal
        self.index.add(norm_embedding)
        
        # Update mappings
        self.id_to_index[item_id] = index
        self.index_to_id[index] = item_id
        
        # Store temporal information
        self.creation_times[item_id] = creation_time
        self.last_access_times[item_id] = creation_time
        self.reference_count[item_id] = 0
        
        # Add to knowledge graph
        self.graph.add_node(item_id)
        
        # Add relationships if provided
        if related_ids:
            for related_id in related_ids:
                if related_id in self.id_to_index:
                    self.graph.add_edge(item_id, related_id)
                    self.graph.add_edge(related_id, item_id)
    
    def calculate_semantic_relevance(self, 
                                    query_embedding: np.ndarray, 
                                    item_id: str) -> float:
        """
        Calculate semantic relevance using FAISS.
        
        Args:
            query_embedding: Embedding of the query
            item_id: ID of the item to calculate relevance for
            
        Returns:
            Semantic relevance score [0,1] where 0 is most relevant
        """
        # Normalize query embedding
        query_embedding = query_embedding.astype(np.float32).reshape(1, self.embedding_dim)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Get item index
        item_index = self.id_to_index.get(item_id)
        if item_index is None:
            return 1.0  # Least relevant if item doesn't exist
            
        # Get item embedding from index
        item_vector = np.zeros((1, self.embedding_dim), dtype=np.float32)
        faiss.reconstruct(self.index, item_index, item_vector.reshape(-1))
        
        # Calculate distance
        distances, _ = self.index.search(query_embedding, 1)
        
        # Convert to relevance score [0,1]
        # Use sigmoid-like function to map distance to relevance
        relevance = 1 / (1 + np.exp(-0.5 * distances[0][0]))
        
        return relevance
    
    def calculate_graph_relevance(self, 
                                 central_id: str, 
                                 item_id: str,
                                 max_distance: int = 5) -> float:
        """
        Calculate graph relevance based on network distance.
        
        Args:
            central_id: ID of the central/query node
            item_id: ID of the item to calculate relevance for
            max_distance: Maximum graph distance to consider
            
        Returns:
            Graph relevance score [0,1] where 0 is most relevant
        """
        # Check if both nodes exist
        if central_id not in self.graph or item_id not in self.graph:
            return 1.0  # Least relevant if either node doesn't exist
            
        # Check if they're the same node
        if central_id == item_id:
            return 0.0  # Most relevant to itself
            
        # Calculate shortest path length
        try:
            path_length = nx.shortest_path_length(
                self.graph, source=central_id, target=item_id
            )
            # Normalize to [0,1]
            relevance = min(path_length / max_distance, 1.0)
            return relevance
        except nx.NetworkXNoPath:
            return 1.0  # No path means least relevant
    
    def calculate_temporal_relevance(self, 
                                    query_time: datetime, 
                                    item_id: str,
                                    recency_weight: float = 0.7,
                                    access_weight: float = 0.3,
                                    time_decay_factor: float = 0.1) -> float:
        """
        Calculate temporal relevance based on creation time and access patterns.
        
        Args:
            query_time: Current time for the query
            item_id: ID of the item
            recency_weight: Weight for recency factor
            access_weight: Weight for access frequency
            time_decay_factor: Controls the decay rate over time
            
        Returns:
            Temporal relevance score [0,1] where 0 is most relevant
        """
        if item_id not in self.creation_times:
            return 1.0  # Least relevant if item doesn't exist
            
        # Calculate time difference in hours
        creation_time = self.creation_times[item_id]
        time_diff = (query_time - creation_time).total_seconds() / 3600
        
        # Recency factor (newer items are more relevant)
        recency_factor = 1 - np.exp(-time_decay_factor * time_diff)
        
        # Access frequency factor
        access_count = self.reference_count[item_id]
        access_factor = 1 / (1 + np.log1p(access_count))
        
        # Combined temporal relevance
        relevance = recency_weight * recency_factor + access_weight * access_factor
        
        # Update access information
        self.last_access_times[item_id] = query_time
        self.reference_count[item_id] += 1
        
        return relevance
    
    def calculate_hybrid_relevance(self,
                                  query_embedding: np.ndarray,
                                  central_id: str,
                                  item_id: str,
                                  query_time: datetime) -> float:
        """
        Calculate the combined hybrid relevance score.
        
        r(c,q,t) = α·r_semantic(c,q) + β·r_graph(c,q) + γ·r_temporal(c,t)
        
        Args:
            query_embedding: Embedding of the query
            central_id: ID of the central/query node
            item_id: ID of the item to calculate relevance for
            query_time: Current time for the query
            
        Returns:
            Combined relevance score [0,1] where 0 is most relevant
        """
        semantic_relevance = self.calculate_semantic_relevance(
            query_embedding, item_id
        )
        
        graph_relevance = self.calculate_graph_relevance(
            central_id, item_id
        )
        
        temporal_relevance = self.calculate_temporal_relevance(
            query_time, item_id
        )
        
        # Combined weighted relevance
        relevance = (
            self.alpha * semantic_relevance + 
            self.beta * graph_relevance + 
            self.gamma * temporal_relevance
        )
        
        return relevance

    def get_most_relevant_items(self,
                               query_embedding: np.ndarray,
                               central_id: str,
                               query_time: datetime,
                               k: int = 10) -> List[Tuple[str, float]]:
        """
        Get the k most relevant items for a query.
        
        Args:
            query_embedding: Embedding of the query
            central_id: ID of the central/query node
            query_time: Current time for the query
            k: Number of items to return
            
        Returns:
            List of (item_id, relevance) tuples sorted by relevance
        """
        results = []
        
        for item_id in self.id_to_index.keys():
            relevance = self.calculate_hybrid_relevance(
                query_embedding, central_id, item_id, query_time
            )
            results.append((item_id, relevance))
        
        # Sort by relevance (lower is better)
        results.sort(key=lambda x: x[1])
        
        return results[:k]


# Example usage
if __name__ == "__main__":
    # Create relevance calculator
    calculator = RelevanceCalculator(embedding_dim=256, use_gpu=False)
    
    # Create some test items
    import random
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # Create 5 random items with relationships
    for i in range(5):
        item_id = f"item_{i}"
        embedding = np.random.random(256).astype(np.float32)
        creation_time = now - timedelta(hours=random.randint(1, 100))
        
        # Create some relationships
        related_ids = [f"item_{j}" for j in range(i) if random.random() > 0.5]
        
        calculator.add_item(item_id, embedding, creation_time, related_ids)
    
    # Create a query
    query_embedding = np.random.random(256).astype(np.float32)
    
    # Get most relevant items
    results = calculator.get_most_relevant_items(
        query_embedding, "item_0", now, k=3
    )
    
    print("Most relevant items:")
    for item_id, relevance in results:
        print(f"  {item_id}: {relevance:.4f}")
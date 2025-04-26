"""
FAISS Integration Layer for 4D Polar-Temporal Database

This module integrates FAISS for efficient vector search while adapting 
it to work within our 4D polar-temporal coordinate system.
It implements the hybrid architecture that uses FAISS for the semantic
similarity component (30-40%) while adding custom components for the
polar-temporal dimensions.
"""

import numpy as np
import faiss
import time
from typing import Dict, List, Tuple, Optional, Union, Any
import pickle
import os


class FaissIntegration:
    """
    Integrates FAISS into the 4D polar-temporal database architecture.
    """
    
    def __init__(self,
                 embedding_dim: int = 1536,
                 use_gpu: bool = True,
                 index_type: str = 'IVF',
                 n_centroids: int = 256,
                 n_probes: int = 20,
                 metric: str = 'cosine'):
        """
        Initialize the FAISS integration layer.
        
        Args:
            embedding_dim: Dimension of embeddings
            use_gpu: Whether to use GPU acceleration
            index_type: Type of FAISS index ('flat', 'IVF', 'HNSW')
            n_centroids: Number of centroids for IVF index
            n_probes: Number of probes for IVF search
            metric: Distance metric ('l2', 'cosine', 'ip')
        """
        self.embedding_dim = embedding_dim
        self.use_gpu = use_gpu
        self.index_type = index_type
        self.n_centroids = n_centroids
        self.n_probes = n_probes
        self.metric = metric
        
        # Mapping between internal IDs and application IDs
        self.faiss_to_id = {}
        self.id_to_faiss = {}
        
        # Create FAISS index
        self.index = self._create_index()
        
        # Storage for metadata
        self.metadata = {}
        
        # Flag to track if index needs training
        self.needs_training = index_type != 'flat'
        self.is_trained = False
        
    def _create_index(self) -> faiss.Index:
        """
        Create a FAISS index based on configuration.
        
        Returns:
            Configured FAISS index
        """
        # Configure metric
        if self.metric == 'cosine':
            metric_param = faiss.METRIC_INNER_PRODUCT
            normalize = True
        elif self.metric == 'ip':
            metric_param = faiss.METRIC_INNER_PRODUCT
            normalize = False
        else:  # l2 by default
            metric_param = faiss.METRIC_L2
            normalize = False
            
        # Create index based on type
        if self.index_type == 'flat':
            if normalize:
                index = faiss.IndexFlatIP(self.embedding_dim)
            else:
                index = faiss.IndexFlat(self.embedding_dim, metric_param)
                
        elif self.index_type == 'IVF':
            # IVF requires a quantizer
            quantizer = faiss.IndexFlat(self.embedding_dim, metric_param)
            index = faiss.IndexIVFFlat(
                quantizer,
                self.embedding_dim, 
                self.n_centroids,
                metric_param
            )
            index.nprobe = self.n_probes
            
        elif self.index_type == 'HNSW':
            index = faiss.IndexHNSWFlat(self.embedding_dim, 32, metric_param)
            
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")
            
        # Move to GPU if requested and available
        if self.use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)
            
        return index
        
    def train(self, embeddings: np.ndarray) -> None:
        """
        Train the FAISS index if required.
        
        Args:
            embeddings: Training embeddings (n_samples, embedding_dim)
        """
        if not self.needs_training or self.is_trained:
            return
            
        if self.metric == 'cosine':
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            
        print(f"Training FAISS index with {len(embeddings)} samples...")
        self.index.train(embeddings)
        self.is_trained = True
        print("FAISS index trained successfully")
        
    def add_items(self, 
                 ids: List[str],
                 embeddings: np.ndarray,
                 metadata: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Add items to the FAISS index.
        
        Args:
            ids: List of item IDs
            embeddings: Embeddings of items (n_samples, embedding_dim)
            metadata: Optional metadata for each item
        """
        if len(ids) != embeddings.shape[0]:
            raise ValueError("Number of IDs must match number of embeddings")
            
        if self.needs_training and not self.is_trained:
            print("Warning: Adding items to untrained index")
            
        # Normalize if using cosine similarity
        if self.metric == 'cosine':
            faiss.normalize_L2(embeddings)
            
        # Get current count for ID mapping
        start_idx = len(self.faiss_to_id)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Update ID mappings
        for i, item_id in enumerate(ids):
            faiss_idx = start_idx + i
            self.faiss_to_id[faiss_idx] = item_id
            self.id_to_faiss[item_id] = faiss_idx
            
            # Store metadata if provided
            if metadata is not None:
                self.metadata[item_id] = metadata[i]
                
        print(f"Added {len(ids)} items to FAISS index")
        
    def search(self,
              query_embedding: np.ndarray,
              k: int = 10) -> Tuple[List[str], List[float]]:
        """
        Search the FAISS index for similar items.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            Tuple of (item_ids, distances)
        """
        # Ensure query is properly shaped
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        # Normalize if using cosine similarity
        if self.metric == 'cosine':
            faiss.normalize_L2(query_embedding)
            
        # Perform search
        distances, indices = self.index.search(query_embedding, k)
        
        # Map FAISS indices back to item IDs
        item_ids = [self.faiss_to_id.get(int(idx)) for idx in indices[0]]
        
        # Filter out None values (if any indices weren't found)
        results = [(item_id, dist) for item_id, dist in zip(item_ids, distances[0]) 
                  if item_id is not None]
        
        # Unpack results
        result_ids, result_distances = zip(*results) if results else ([], [])
        
        return list(result_ids), list(result_distances)
        
    def get_item_embedding(self, item_id: str) -> Optional[np.ndarray]:
        """
        Get the embedding for a specific item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Item embedding or None if not found
        """
        if item_id not in self.id_to_faiss:
            return None
            
        faiss_idx = self.id_to_faiss[item_id]
        
        # Reconstruct vector from index
        embedding = np.zeros((1, self.embedding_dim), dtype=np.float32)
        
        try:
            self.index.reconstruct(faiss_idx, embedding.reshape(-1))
            return embedding
        except RuntimeError:
            print(f"Error reconstructing vector for {item_id}")
            return None
            
    def get_nearest_by_id(self, 
                         item_id: str, 
                         k: int = 10) -> List[Tuple[str, float]]:
        """
        Get items most similar to a given item.
        
        Args:
            item_id: ID of the reference item
            k: Number of results to return
            
        Returns:
            List of (item_id, distance) tuples
        """
        # Get item embedding
        embedding = self.get_item_embedding(item_id)
        
        if embedding is None:
            return []
            
        # Search using the embedding
        item_ids, distances = self.search(embedding, k + 1)  # +1 because the item itself will be included
        
        # Remove the query item from results
        results = [(id_, dist) for id_, dist in zip(item_ids, distances) if id_ != item_id]
        
        return results[:k]
        
    def save(self, path: str) -> None:
        """
        Save the FAISS index and metadata to disk.
        
        Args:
            path: Directory path to save data
        """
        os.makedirs(path, exist_ok=True)
        
        # Save the FAISS index
        if hasattr(self.index, 'cpu'):
            index_cpu = self.index.cpu()
        else:
            index_cpu = self.index
            
        faiss.write_index(index_cpu, os.path.join(path, "faiss_index.bin"))
        
        # Save mappings and metadata
        with open(os.path.join(path, "faiss_mappings.pkl"), 'wb') as f:
            pickle.dump({
                'faiss_to_id': self.faiss_to_id,
                'id_to_faiss': self.id_to_faiss,
                'metadata': self.metadata,
                'config': {
                    'embedding_dim': self.embedding_dim,
                    'index_type': self.index_type,
                    'n_centroids': self.n_centroids,
                    'n_probes': self.n_probes,
                    'metric': self.metric,
                    'is_trained': self.is_trained
                }
            }, f)
            
        print(f"FAISS index and metadata saved to {path}")
        
    @classmethod
    def load(cls, path: str, use_gpu: bool = True) -> 'FaissIntegration':
        """
        Load a saved FAISS index and metadata.
        
        Args:
            path: Directory path to load data from
            use_gpu: Whether to move index to GPU after loading
            
        Returns:
            Initialized FaissIntegration instance
        """
        # Load mappings and metadata
        with open(os.path.join(path, "faiss_mappings.pkl"), 'rb') as f:
            data = pickle.load(f)
            
        # Create instance with saved config
        config = data['config']
        instance = cls(
            embedding_dim=config['embedding_dim'],
            use_gpu=use_gpu,
            index_type=config['index_type'],
            n_centroids=config['n_centroids'],
            n_probes=config['n_probes'],
            metric=config['metric']
        )
        
        # Load the index
        index = faiss.read_index(os.path.join(path, "faiss_index.bin"))
        
        # Move to GPU if requested
        if use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)
            
        instance.index = index
        instance.faiss_to_id = data['faiss_to_id']
        instance.id_to_faiss = data['id_to_faiss']
        instance.metadata = data['metadata']
        instance.is_trained = config['is_trained']
        
        print(f"Loaded FAISS index with {len(instance.id_to_faiss)} items")
        return instance


# FAISS adapter for 4D polar-temporal space integration
class FaissPolarTemporalAdapter:
    """
    Adapts FAISS for use within the 4D polar-temporal database architecture.
    Translates between 4D coordinates and FAISS operations.
    """
    
    def __init__(self, faiss_engine: FaissIntegration):
        """
        Initialize the adapter.
        
        Args:
            faiss_engine: FaissIntegration instance
        """
        self.faiss_engine = faiss_engine
        
        # Storage for 4D coordinates
        self.id_to_coordinates = {}
        
        # Cache for faster lookups
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def add_item_with_coordinates(self,
                                 item_id: str,
                                 embedding: np.ndarray,
                                 r: float,
                                 theta: float,
                                 t: float,
                                 z: int,
                                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an item with its 4D coordinates.
        
        Args:
            item_id: Unique item ID
            embedding: Vector embedding
            r: Radial distance (relevance)
            theta: Angular position (category)
            t: Temporal position
            z: Context layer
            metadata: Optional metadata
        """
        # Add to FAISS for semantic similarity
        self.faiss_engine.add_items(
            ids=[item_id], 
            embeddings=embedding.reshape(1, -1),
            metadata=[metadata] if metadata else None
        )
        
        # Store coordinates
        self.id_to_coordinates[item_id] = {
            'r': r,
            'theta': theta,
            't': t,
            'z': z
        }
        
        # Clear relevant cache entries
        self.clear_cache_for_coordinates(r, theta, t, z)
        
    def clear_cache_for_coordinates(self, r: float, theta: float, t: float, z: int) -> None:
        """
        Clear cache entries that might be affected by a new item.
        
        Args:
            r, theta, t, z: 4D coordinates
        """
        # Identify and remove affected cache entries
        keys_to_remove = []
        
        for key in self.cache:
            if key.startswith('r_range') or key.startswith('theta_range') or \
               key.startswith('t_range') or key.startswith('z_equals'):
                # Parse the cache key to check if it's affected
                parts = key.split('_')
                if key.startswith('r_range') and float(parts[2]) <= r <= float(parts[3]):
                    keys_to_remove.append(key)
                elif key.startswith('theta_range'):
                    # Angular ranges need special handling for wraparound
                    theta_min, theta_max = float(parts[2]), float(parts[3])
                    if theta_min <= theta_max:
                        if theta_min <= theta <= theta_max:
                            keys_to_remove.append(key)
                    else:  # Wraparound case
                        if theta >= theta_min or theta <= theta_max:
                            keys_to_remove.append(key)
                elif key.startswith('t_range') and float(parts[2]) <= t <= float(parts[3]):
                    keys_to_remove.append(key)
                elif key.startswith('z_equals') and int(parts[2]) == z:
                    keys_to_remove.append(key)
        
        # Remove affected cache entries
        for key in keys_to_remove:
            del self.cache[key]
            
    def get_items_in_radius_range(self, 
                                 r_min: float, 
                                 r_max: float) -> List[str]:
        """
        Get items within a radial distance range.
        
        Args:
            r_min: Minimum radius
            r_max: Maximum radius
            
        Returns:
            List of item IDs within the range
        """
        # Check cache first
        cache_key = f"r_range_{r_min}_{r_max}"
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
            
        self.cache_misses += 1
        
        # Find all items in the range
        results = []
        for item_id, coords in self.id_to_coordinates.items():
            if r_min <= coords['r'] <= r_max:
                results.append(item_id)
                
        # Cache the results
        self.cache[cache_key] = results
        return results
        
    def get_items_in_angular_range(self, 
                                  theta_min: float, 
                                  theta_max: float) -> List[str]:
        """
        Get items within an angular range.
        
        Args:
            theta_min: Minimum angle in radians
            theta_max: Maximum angle in radians
            
        Returns:
            List of item IDs within the range
        """
        # Normalize angles to [0, 2π)
        theta_min = theta_min % (2 * np.pi)
        theta_max = theta_max % (2 * np.pi)
        
        # Check cache first
        cache_key = f"theta_range_{theta_min}_{theta_max}"
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
            
        self.cache_misses += 1
        
        # Find all items in the angular range
        results = []
        for item_id, coords in self.id_to_coordinates.items():
            theta = coords['theta']
            
            # Handle regular case and wraparound
            if theta_min <= theta_max:
                if theta_min <= theta <= theta_max:
                    results.append(item_id)
            else:  # Wraparound case (e.g., 350° to 10°)
                if theta >= theta_min or theta <= theta_max:
                    results.append(item_id)
                    
        # Cache the results
        self.cache[cache_key] = results
        return results
        
    def get_items_in_time_range(self, 
                               t_min: float, 
                               t_max: float) -> List[str]:
        """
        Get items within a temporal range.
        
        Args:
            t_min: Minimum time
            t_max: Maximum time
            
        Returns:
            List of item IDs within the range
        """
        # Check cache first
        cache_key = f"t_range_{t_min}_{t_max}"
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
            
        self.cache_misses += 1
        
        # Find all items in the time range
        results = []
        for item_id, coords in self.id_to_coordinates.items():
            if t_min <= coords['t'] <= t_max:
                results.append(item_id)
                
        # Cache the results
        self.cache[cache_key] = results
        return results
        
    def get_items_in_context_layer(self, z: int) -> List[str]:
        """
        Get items in a specific context layer.
        
        Args:
            z: Context layer
            
        Returns:
            List of item IDs in the layer
        """
        # Check cache first
        cache_key = f"z_equals_{z}"
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
            
        self.cache_misses += 1
        
        # Find all items in the context layer
        results = []
        for item_id, coords in self.id_to_coordinates.items():
            if coords['z'] == z:
                results.append(item_id)
                
        # Cache the results
        self.cache[cache_key] = results
        return results
        
    def get_similar_items(self, 
                         query_embedding: np.ndarray, 
                         k: int = 10) -> List[Tuple[str, float]]:
        """
        Get most semantically similar items using FAISS.
        
        Args:
            query_embedding: Query vector
            k: Number of results
            
        Returns:
            List of (item_id, distance) tuples
        """
        item_ids, distances = self.faiss_engine.search(query_embedding, k)
        return list(zip(item_ids, distances))
        
    def combined_query(self,
                      query_embedding: np.ndarray,
                      r_min: float = 0,
                      r_max: float = float('inf'),
                      theta_min: float = 0,
                      theta_max: float = 2 * np.pi,
                      t_min: float = float('-inf'),
                      t_max: float = float('inf'),
                      z: Optional[int] = None,
                      k: int = 10) -> List[Tuple[str, float]]:
        """
        Perform a combined query across all dimensions.
        
        Args:
            query_embedding: Query vector for semantic similarity
            r_min, r_max: Radial range
            theta_min, theta_max: Angular range
            t_min, t_max: Temporal range
            z: Specific context layer (if None, all layers)
            k: Number of results
            
        Returns:
            List of (item_id, distance) tuples
        """
        start_time = time.time()
        
        # Get items matching the coordinate constraints
        r_matches = set(self.get_items_in_radius_range(r_min, r_max))
        theta_matches = set(self.get_items_in_angular_range(theta_min, theta_max))
        t_matches = set(self.get_items_in_time_range(t_min, t_max))
        
        # Combine the coordinate constraints
        coordinate_matches = r_matches.intersection(theta_matches).intersection(t_matches)
        
        # Apply context layer filter if specified
        if z is not None:
            z_matches = set(self.get_items_in_context_layer(z))
            coordinate_matches = coordinate_matches.intersection(z_matches)
            
        # If no matches, return empty list
        if not coordinate_matches:
            return []
            
        # Get all items matching the coordinate constraints
        coordinate_match_list = list(coordinate_matches)
        
        # If we have embeddings, rank by semantic similarity
        if query_embedding is not None:
            # Get embeddings for all matching items
            embeddings = []
            valid_ids = []
            
            for item_id in coordinate_match_list:
                embedding = self.faiss_engine.get_item_embedding(item_id)
                if embedding is not None:
                    embeddings.append(embedding.reshape(1, -1))
                    valid_ids.append(item_id)
                    
            if not embeddings:
                return []
                
            # Concatenate embeddings
            all_embeddings = np.vstack(embeddings)
            
            # Calculate similarity scores
            if self.faiss_engine.metric == 'cosine':
                faiss.normalize_L2(all_embeddings)
                faiss.normalize_L2(query_embedding.reshape(1, -1))
                scores, _ = self.faiss_engine.index.search(query_embedding.reshape(1, -1), len(valid_ids))
                results = [(id_, score) for id_, score in zip(valid_ids, scores[0])]
                # Sort by decreasing similarity (higher is better for inner product)
                results.sort(key=lambda x: x[1], reverse=True)
            else:
                distances, _ = self.faiss_engine.index.search(query_embedding.reshape(1, -1), len(valid_ids))
                results = [(id_, dist) for id_, dist in zip(valid_ids, distances[0])]
                # Sort by increasing distance (lower is better for L2)
                results.sort(key=lambda x: x[1])
                
            end_time = time.time()
            print(f"Combined query took {end_time - start_time:.4f} seconds")
            print(f"Cache stats: {self.cache_hits} hits, {self.cache_misses} misses")
            
            return results[:k]
        else:
            # No embedding, just return the coordinate matches
            return [(id_, 0.0) for id_ in coordinate_match_list[:k]]


# Example usage
if __name__ == "__main__":
    # Create FAISS engine
    faiss_engine = FaissIntegration(
        embedding_dim=256,
        use_gpu=False,
        index_type='flat'
    )
    
    # Create adapter
    adapter = FaissPolarTemporalAdapter(faiss_engine)
    
    # Add some test items
    for i in range(100):
        item_id = f"item_{i}"
        embedding = np.random.random(256).astype(np.float32)
        r = np.random.uniform(0, 3)
        theta = np.random.uniform(0, 2 * np.pi)
        t = np.random.uniform(0, 100)
        z = np.random.randint(1, 4)
        
        adapter.add_item_with_coordinates(
            item_id=item_id,
            embedding=embedding,
            r=r,
            theta=theta,
            t=t,
            z=z
        )
    
    # Test combined query
    query_embedding = np.random.random(256).astype(np.float32)
    results = adapter.combined_query(
        query_embedding=query_embedding,
        r_min=0, r_max=2,
        theta_min=0, theta_max=np.pi,
        t_min=0, t_max=50,
        z=2,
        k=5
    )
    
    print("Combined query results:")
    for item_id, score in results:
        coords = adapter.id_to_coordinates[item_id]
        print(f"  {item_id}: score={score:.4f}, r={coords['r']:.2f}, "
              f"θ={coords['theta']:.2f}, t={coords['t']:.2f}, z={coords['z']}")
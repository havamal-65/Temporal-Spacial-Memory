from typing import Dict, List, Any, Optional, Tuple, Set
import math
import json
import os
import time as time_module
from datetime import datetime
from rtree import index
from collections import OrderedDict, defaultdict

from .node import Node

class TemporalCache:
    """
    Temporal-aware cache that prioritizes recently accessed items
    while preserving temporal locality of reference.
    """
    
    def __init__(self, capacity: int = 100):
        """
        Initialize a new temporal cache.
        
        Args:
            capacity: Maximum number of items to store in the cache
        """
        self.capacity = capacity
        self.cache = OrderedDict()  # For LRU functionality
        self.time_regions = defaultdict(set)  # Time region -> set of node_ids
        self.access_counts = defaultdict(int)  # node_id -> access count
        
        # Each time region covers this time span
        self.time_region_span = 10.0
        
    def get(self, key: str, time_value: float) -> Any:
        """Get a value from the cache"""
        if key not in self.cache:
            return None
            
        # Update access counts
        self.access_counts[key] += 1
        
        # Move to the end (most recently used)
        value = self.cache.pop(key)
        self.cache[key] = value
        
        return value
        
    def put(self, key: str, value: Any, time_value: float) -> None:
        """Add a value to the cache with its temporal position"""
        # If at capacity, evict items
        if len(self.cache) >= self.capacity:
            self._evict()
            
        # Add to cache
        self.cache[key] = value
        
        # Add to the appropriate time region
        time_region = int(time_value / self.time_region_span)
        self.time_regions[time_region].add(key)
        
    def _evict(self) -> None:
        """Evict items when cache is full using temporal-aware strategy"""
        # If any items have never been accessed, remove the oldest one first
        zero_access_keys = [k for k, count in self.access_counts.items() if count == 0]
        if zero_access_keys and zero_access_keys[0] in self.cache:
            lru_key = zero_access_keys[0]
            self._remove_item(lru_key)
            return
            
        # Otherwise use standard LRU (the oldest item in the OrderedDict)
        if self.cache:
            lru_key, _ = next(iter(self.cache.items()))
            self._remove_item(lru_key)
            
    def _remove_item(self, key: str) -> None:
        """Remove an item from all cache data structures"""
        if key in self.cache:
            # Remove from main cache
            value = self.cache.pop(key)
            
            # Remove from time regions
            for region, keys in self.time_regions.items():
                if key in keys:
                    keys.remove(key)
                    
            # Remove from access counts
            if key in self.access_counts:
                del self.access_counts[key]
                
    def clear_region(self, time_value: float) -> None:
        """Clear all items in a specific time region"""
        time_region = int(time_value / self.time_region_span)
        if time_region in self.time_regions:
            # Get all keys in this region
            keys_to_remove = list(self.time_regions[time_region])
            
            # Remove each key
            for key in keys_to_remove:
                self._remove_item(key)
                
            # Clear the region itself
            del self.time_regions[time_region]

class MeshTube:
    """
    The main Mesh Tube Knowledge Database class.
    
    This class manages a collection of nodes in a 3D cylindrical mesh structure,
    providing methods to add, retrieve, and connect nodes, as well as
    functionality for delta encoding and temporal-spatial navigation.
    """
    
    def __init__(self, name: str, storage_path: Optional[str] = None):
        """
        Initialize a new Mesh Tube Knowledge Database.
        
        Args:
            name: Name of this knowledge database
            storage_path: Path to store the database files (optional)
        """
        self.name = name
        self.nodes: Dict[str, Node] = {}  # node_id -> Node mapping
        self.storage_path = storage_path
        self.created_at = datetime.now()
        self.last_modified = self.created_at
        
        # Predictive model weights
        self.alpha = 0.5  # semantic importance weight
        self.beta = 0.3   # relational relevance weight
        self.gamma = 0.2  # velocity (momentum) weight
        
        # Initialize spatial index (R-tree)
        self._init_spatial_index()
        
        # Initialize caches
        self._init_caches()
    
    def _init_caches(self):
        """Initialize caching layers for performance optimization"""
        # Cache for computed node states (from delta chains)
        self.state_cache = TemporalCache(capacity=200)
        
        # Cache for nearest neighbor results
        self.nearest_cache = TemporalCache(capacity=50)
        
        # Cache for temporal slices
        self.slice_cache = TemporalCache(capacity=20)
        
        # Cache for paths (node sequences)
        self.path_cache = TemporalCache(capacity=30)
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _init_spatial_index(self):
        """Initialize the R-tree spatial index for efficient spatial queries"""
        # Create an in-memory R-tree index with custom properties
        p = index.Property()
        p.dimension = 3  # 3D space: time, distance, angle
        p.buffering_capacity = 10
        self.spatial_index = index.Index(properties=p)
    
    def _update_spatial_index(self):
        """
        Rebuild the spatial index based on current nodes.
        Called when multiple nodes are modified or after bulk operations.
        """
        self._init_spatial_index()
        
        # Add all nodes to the spatial index
        for node_id, node in self.nodes.items():
            # Convert cylindrical coordinates to Cartesian for better indexing
            x = node.distance * math.cos(math.radians(node.angle))
            y = node.distance * math.sin(math.radians(node.angle))
            z = node.time
            
            # Store as bounding box with small extent (practically a point)
            self.spatial_index.insert(
                int(hash(node_id) % (2**31)), 
                (x, y, z, x, y, z),
                obj=node_id
            )
    
    def add_node(self, 
                content: Dict[str, Any],
                time: float,
                distance: float,
                angle: float,
                parent_id: Optional[str] = None) -> Node:
        """
        Add a new node to the mesh tube database.
        
        Args:
            content: The data content of the node
            time: Temporal coordinate
            distance: Radial distance from center
            angle: Angular position
            parent_id: Optional parent node for delta encoding
            
        Returns:
            The newly created node
        """
        node = Node(
            content=content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=parent_id
        )
        
        self.nodes[node.node_id] = node
        self.last_modified = datetime.now()
        
        # Add to spatial index
        x = distance * math.cos(math.radians(angle))
        y = distance * math.sin(math.radians(angle))
        z = time
        
        self.spatial_index.insert(
            int(hash(node.node_id) % (2**31)),
            (x, y, z, x, y, z),
            obj=node.node_id
        )
        
        return node
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve a node by its ID"""
        return self.nodes.get(node_id)
    
    def connect_nodes(self, node_id1: str, node_id2: str) -> bool:
        """
        Create a bidirectional connection between two nodes
        
        Returns:
            True if connection was successful, False otherwise
        """
        node1 = self.get_node(node_id1)
        node2 = self.get_node(node_id2)
        
        if not node1 or not node2:
            return False
        
        node1.add_connection(node2.node_id)
        node2.add_connection(node1.node_id)
        self.last_modified = datetime.now()
        
        return True
    
    def get_temporal_slice(self, time: float, tolerance: float = 0.01) -> List[Node]:
        """
        Get all nodes at a specific time point (with tolerance)
        
        Args:
            time: The time coordinate to retrieve
            tolerance: How close a node must be to the time point to be included
            
        Returns:
            List of nodes at the specified time slice
        """
        # Check cache first
        cache_key = f"slice_{time}_{tolerance}"
        cached_slice = self.slice_cache.get(cache_key, time)
        if cached_slice is not None:
            self.cache_hits += 1
            return cached_slice
            
        self.cache_misses += 1
        
        # Compute the slice
        result = [
            node for node in self.nodes.values()
            if abs(node.time - time) <= tolerance
        ]
        
        # Cache the result
        self.slice_cache.put(cache_key, result, time)
        
        return result
    
    def get_nodes_by_distance(self, 
                             min_distance: float, 
                             max_distance: float) -> List[Node]:
        """Get all nodes within a specific distance range from center"""
        return [
            node for node in self.nodes.values()
            if min_distance <= node.distance <= max_distance
        ]
    
    def get_nodes_by_angular_slice(self, 
                                  min_angle: float, 
                                  max_angle: float) -> List[Node]:
        """Get all nodes within a specific angular section"""
        return [
            node for node in self.nodes.values()
            if min_angle <= node.angle <= max_angle
        ]
    
    def get_nearest_nodes(self, 
                         reference_node: Node, 
                         limit: int = 10) -> List[Tuple[Node, float]]:
        """
        Find nodes nearest to a reference node in the mesh using R-tree spatial indexing
        
        Args:
            reference_node: The node to measure distance from
            limit: Maximum number of nodes to return
            
        Returns:
            List of (node, distance) tuples, ordered by proximity
        """
        # Check cache first
        cache_key = f"nearest_{reference_node.node_id}_{limit}"
        cached_nearest = self.nearest_cache.get(cache_key, reference_node.time)
        if cached_nearest is not None:
            self.cache_hits += 1
            return cached_nearest
            
        self.cache_misses += 1
        
        # Convert reference node to Cartesian coordinates for R-tree query
        ref_x = reference_node.distance * math.cos(math.radians(reference_node.angle))
        ref_y = reference_node.distance * math.sin(math.radians(reference_node.angle))
        ref_z = reference_node.time
        
        # Query point (same as bounding box in this case)
        query_point = (ref_x, ref_y, ref_z, ref_x, ref_y, ref_z)
        
        # Get more candidates than we need (some might be filtered)
        search_limit = limit * 2
        
        # Find nearest candidates using R-tree
        nearest_candidates = []
        
        # Instead of using get_object, we'll get the node IDs from our hash mapping
        found_items = list(self.spatial_index.nearest(coordinates=query_point, num_results=search_limit))
        
        for item in found_items:
            # Find the node ID that corresponds to this hash
            node_id = None
            for nid in self.nodes.keys():
                if int(hash(nid) % (2**31)) == item:
                    node_id = nid
                    break
            
            if not node_id or node_id == reference_node.node_id:
                continue
                
            node = self.nodes.get(node_id)
            if node:
                # Calculate actual cylindrical distance for accurate sorting
                distance = reference_node.spatial_distance(node)
                nearest_candidates.append((node, distance))
        
        # Sort by distance and return limited results
        nearest_candidates.sort(key=lambda x: x[1])
        result = nearest_candidates[:limit]
        
        # Cache the result
        self.nearest_cache.put(cache_key, result, reference_node.time)
        
        return result
    
    def apply_delta(self, 
                   original_node: Node, 
                   delta_content: Dict[str, Any],
                   time: float,
                   distance: Optional[float] = None,
                   angle: Optional[float] = None) -> Node:
        """
        Create a new node that represents a delta (change) from an original node
        
        Args:
            original_node: The node to derive from
            delta_content: New or changed content
            time: New temporal position
            distance: New radial distance (optional, uses original if not provided)
            angle: New angular position (optional, uses original if not provided)
            
        Returns:
            A new node that references the original node
        """
        # Use original values for spatial coordinates if not provided
        if distance is None:
            distance = original_node.distance
            
        if angle is None:
            angle = original_node.angle
            
        # Create a new node with the delta content
        delta_node = self.add_node(
            content=delta_content,
            time=time,
            distance=distance,
            angle=angle,
            parent_id=original_node.node_id
        )
        
        # Make sure we have the reference
        delta_node.add_delta_reference(original_node.node_id)
        
        return delta_node
    
    def compute_node_state(self, node_id: str) -> Dict[str, Any]:
        """
        Compute the full state of a node by applying all delta references
        
        Args:
            node_id: ID of the node to compute
            
        Returns:
            The computed full content state of the node
        """
        node = self.get_node(node_id)
        if not node:
            return {}
            
        # Check if in cache first
        cache_key = f"state_{node_id}"
        cached_state = self.state_cache.get(cache_key, node.time)
        if cached_state is not None:
            self.cache_hits += 1
            return cached_state
            
        self.cache_misses += 1
            
        # If no delta references, return the node's content directly
        if not node.delta_references:
            # Cache the result
            self.state_cache.put(cache_key, node.content, node.time)
            return node.content
            
        # Start with an empty state
        computed_state = {}
        
        # Find all nodes in the reference chain
        chain = self._get_delta_chain(node)
        
        # Apply deltas in chronological order (oldest first)
        for delta_node in sorted(chain, key=lambda n: n.time):
            # Update the state with this node's content
            computed_state.update(delta_node.content)
            
        # Cache the result
        self.state_cache.put(cache_key, computed_state, node.time)
            
        return computed_state
    
    def _get_delta_chain(self, node: Node) -> List[Node]:
        """Get all nodes in a delta reference chain, including the node itself"""
        chain = [node]
        processed_ids = {node.node_id}
        
        # Process queue of nodes to check for references
        queue = list(node.delta_references)
        
        while queue:
            ref_id = queue.pop(0)
            if ref_id in processed_ids:
                continue
                
            ref_node = self.get_node(ref_id)
            if ref_node:
                chain.append(ref_node)
                processed_ids.add(ref_id)
                
                # Add any new references to the queue
                for new_ref in ref_node.delta_references:
                    if new_ref not in processed_ids:
                        queue.append(new_ref)
        
        return chain
    
    def compress_deltas(self, max_chain_length: int = 10) -> None:
        """
        Compress delta chains to reduce storage overhead.
        
        This implementation identifies long delta chains and merges older nodes
        to reduce the total storage requirements while maintaining data integrity.
        
        Args:
            max_chain_length: Maximum length of delta chains before compression
        """
        # Group nodes by delta chains
        node_chains = {}
        
        # Find the root node of each chain
        for node_id, node in self.nodes.items():
            chain = self._get_delta_chain(node)
            if len(chain) > 1:  # Only process actual chains
                # Use the oldest node as the chain identifier
                oldest_node = min(chain, key=lambda n: n.time)
                if oldest_node.node_id not in node_chains:
                    node_chains[oldest_node.node_id] = []
                
                if node not in node_chains[oldest_node.node_id]:
                    node_chains[oldest_node.node_id].append(node)
        
        # Process each chain that exceeds the maximum length
        for chain_id, chain in node_chains.items():
            if len(chain) <= max_chain_length:
                continue
            
            # Sort by time (oldest first)
            sorted_chain = sorted(chain, key=lambda n: n.time)
            
            # Keep the most recent nodes and merge the older ones
            nodes_to_keep = sorted_chain[-max_chain_length:]
            nodes_to_merge = sorted_chain[:-max_chain_length]
            
            if not nodes_to_merge:
                continue
                
            # Create a merged node with the combined state
            merged_content = {}
            for node in nodes_to_merge:
                merged_content.update(node.content)
            
            # Create a new merged node at the position of the most recent merged node
            last_merged = nodes_to_merge[-1]
            merged_node = self.add_node(
                content=merged_content,
                time=last_merged.time,
                distance=last_merged.distance,
                angle=last_merged.angle
            )
            
            # Update references in the kept nodes
            for node in nodes_to_keep:
                # Replace any references to merged nodes with the new merged node
                new_references = []
                for ref_id in node.delta_references:
                    if any(n.node_id == ref_id for n in nodes_to_merge):
                        new_references.append(merged_node.node_id)
                    else:
                        new_references.append(ref_id)
                
                # Remove duplicates
                node.delta_references = list(set(new_references))
            
            # Remove the merged nodes
            for node in nodes_to_merge:
                if node.node_id in self.nodes:
                    del self.nodes[node.node_id]
    
    def load_temporal_window(self, start_time: float, end_time: float) -> 'MeshTube':
        """
        Load only nodes within a specific time window.
        
        Args:
            start_time: Beginning of the time window
            end_time: End of the time window
            
        Returns:
            A new MeshTube containing only the requested nodes
        """
        # Create a new MeshTube instance
        window_tube = MeshTube(f"{self.name}_window", self.storage_path)
        
        # Copy relevant settings
        window_tube.alpha = self.alpha
        window_tube.beta = self.beta
        window_tube.gamma = self.gamma
        
        # Find nodes within the time window
        window_nodes = [
            node for node in self.nodes.values()
            if start_time <= node.time <= end_time
        ]
        
        # Copy nodes to the new tube
        for node in window_nodes:
            # Deep copy the node
            window_tube.nodes[node.node_id] = Node.from_dict(node.to_dict())
        
        # Only keep connections between nodes in the window
        node_ids_in_window = set(window_tube.nodes.keys())
        for node in window_tube.nodes.values():
            # Filter connections to only those in the window
            node.connections = {
                conn_id for conn_id in node.connections
                if conn_id in node_ids_in_window
            }
            
            # Filter delta references to only those in the window
            node.delta_references = [
                ref_id for ref_id in node.delta_references
                if ref_id in node_ids_in_window
            ]
        
        return window_tube
    
    def predict_topic_probability(self, topic_id: str, future_time: float) -> float:
        """
        Predict the probability of a topic appearing at a future time
        
        This implements the core predictive equation:
        P(T_{i,t+1} | M_t) = α·S(T_i) + β·R(T_i, M_t) + γ·V(T_i, t)
        
        Args:
            topic_id: ID of the topic/node to predict
            future_time: Time point to predict for
            
        Returns:
            Probability value between 0 and 1
        """
        topic_node = self.get_node(topic_id)
        if not topic_node:
            return 0.0
            
        # Calculate semantic importance (inversely related to distance from center)
        semantic_importance = 1.0 / (1.0 + topic_node.distance)
        
        # Calculate relational relevance (number of connections relative to max)
        max_connections = max(
            len(node.connections) for node in self.nodes.values()
        ) if self.nodes else 1
        
        relational_relevance = len(topic_node.connections) / max_connections
        
        # Calculate velocity (momentum of recent changes)
        # This is a simplified version - real implementation would analyze
        # historical time series data
        delta_chain = self._get_delta_chain(topic_node)
        if len(delta_chain) <= 1:
            velocity = 0.0
        else:
            # Calculate rate of change over time
            time_diffs = [
                abs(delta_chain[i+1].time - delta_chain[i].time)
                for i in range(len(delta_chain)-1)
            ]
            avg_time_diff = sum(time_diffs) / len(time_diffs) if time_diffs else 1.0
            velocity = 1.0 / (1.0 + avg_time_diff)  # Higher velocity if changes are frequent
        
        # Apply the predictive equation
        probability = (
            self.alpha * semantic_importance +
            self.beta * relational_relevance +
            self.gamma * velocity
        )
        
        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, probability))
    
    def save(self, filepath: Optional[str] = None) -> None:
        """
        Save the database to a JSON file
        
        Args:
            filepath: Path to save to (uses storage_path/name.json if not provided)
        """
        if not filepath and not self.storage_path:
            raise ValueError("No storage path provided")
            
        # Determine the save path
        save_path = filepath
        if not save_path:
            save_path = os.path.join(self.storage_path, f"{self.name}.json")
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Serialize the database
        data = {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "nodes": {
                node_id: node.to_dict() 
                for node_id, node in self.nodes.items()
            },
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma
        }
        
        # Write to file
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'MeshTube':
        """
        Load a database from a JSON file
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            A new MeshTube instance with the loaded data
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        storage_path = os.path.dirname(filepath)
        mesh_tube = cls(name=data["name"], storage_path=storage_path)
        
        mesh_tube.created_at = datetime.fromisoformat(data["created_at"])
        mesh_tube.last_modified = datetime.fromisoformat(data["last_modified"])
        mesh_tube.alpha = data.get("alpha", 0.5)
        mesh_tube.beta = data.get("beta", 0.3)
        mesh_tube.gamma = data.get("gamma", 0.2)
        
        # Load nodes
        for node_data in data["nodes"].values():
            node = Node.from_dict(node_data)
            mesh_tube.nodes[node.node_id] = node
            
        return mesh_tube
    
    def clear_caches(self) -> None:
        """Clear all caches"""
        self._init_caches()
        
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get statistics about cache performance"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = 0
        if total_requests > 0:
            hit_rate = self.cache_hits / total_requests
            
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "state_cache_size": len(self.state_cache.cache),
            "nearest_cache_size": len(self.nearest_cache.cache),
            "slice_cache_size": len(self.slice_cache.cache),
            "path_cache_size": len(self.path_cache.cache)
        } 
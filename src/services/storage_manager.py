"""
Storage Manager Service

This module provides a simple storage manager for the 4D polar-temporal database.
It implements basic storage operations with JSON files.
"""

import os
import json
import time
import pickle
import logging
import shutil
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('StorageManager')


class SimpleStorageManager:
    """
    Simple file-based storage manager for the 4D polar-temporal database.
    """
    
    def __init__(self, storage_path: str = 'output/db'):
        """
        Initialize the storage manager.
        
        Args:
            storage_path: Path to the storage directory
        """
        self.storage_path = storage_path
        self.items_dir = os.path.join(storage_path, 'items')
        self.index_path = os.path.join(storage_path, 'index.json')
        
        # Create directories if they don't exist
        os.makedirs(self.items_dir, exist_ok=True)
        
        # In-memory index of items
        self.index = {}
        
        # Load existing index if it exists
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    self.index = json.load(f)
                logger.info(f"Loaded index with {len(self.index)} items")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                # Start with an empty index
                self.index = {}
        
        # Statistics
        self.stats = {
            'items_stored': len(self.index),
            'items_retrieved': 0,
            'storage_operations': 0,
            'errors': 0
        }
    
    def store_item(self,
                 item_id: str,
                 content: str,
                 coordinates: Dict[str, float],
                 metadata: Dict[str, Any] = None,
                 embedding: Optional[np.ndarray] = None) -> bool:
        """
        Store an item in the database.
        
        Args:
            item_id: Unique identifier for the item
            content: Text content of the item
            coordinates: 4D coordinates (r, theta, t, z)
            metadata: Optional metadata
            embedding: Optional vector embedding
            
        Returns:
            True if storage succeeded, False otherwise
        """
        try:
            # Create item data structure
            item_data = {
                'id': item_id,
                'content': content,
                'coordinates': coordinates,
                'metadata': metadata or {},
                'timestamp': time.time()
            }
            
            # Serialize embedding separately if present
            if embedding is not None:
                embedding_path = os.path.join(self.items_dir, f"{item_id}.embedding")
                with open(embedding_path, 'wb') as f:
                    pickle.dump(embedding, f)
                item_data['has_embedding'] = True
            else:
                item_data['has_embedding'] = False
            
            # Store item data as JSON
            item_path = os.path.join(self.items_dir, f"{item_id}.json")
            with open(item_path, 'w') as f:
                json.dump(item_data, f, indent=2)
            
            # Update index
            self.index[item_id] = {
                'coordinates': coordinates,
                'path': item_path,
                'timestamp': item_data['timestamp']
            }
            
            # Save index periodically (could be optimized to save less frequently)
            with open(self.index_path, 'w') as f:
                json.dump(self.index, f, indent=2)
            
            # Update statistics
            self.stats['items_stored'] += 1
            self.stats['storage_operations'] += 1
            
            logger.debug(f"Stored item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing item {item_id}: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_item(self, item_id: str, include_embedding: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the database.
        
        Args:
            item_id: Item ID to retrieve
            include_embedding: Whether to include the embedding in the result
            
        Returns:
            Item data or None if not found
        """
        if item_id not in self.index:
            return None
        
        try:
            # Get item path from index
            item_path = self.index[item_id]['path']
            
            # Load item data
            with open(item_path, 'r') as f:
                item_data = json.load(f)
            
            # Load embedding if requested and available
            if include_embedding and item_data.get('has_embedding', False):
                embedding_path = os.path.join(self.items_dir, f"{item_id}.embedding")
                if os.path.exists(embedding_path):
                    with open(embedding_path, 'rb') as f:
                        item_data['embedding'] = pickle.load(f)
            
            # Update statistics
            self.stats['items_retrieved'] += 1
            
            return item_data
            
        except Exception as e:
            logger.error(f"Error retrieving item {item_id}: {e}")
            self.stats['errors'] += 1
            return None
    
    def query_items(self,
                  r_min: float = 0,
                  r_max: float = float('inf'),
                  theta_min: float = 0,
                  theta_max: float = 2 * np.pi,
                  t_min: Optional[float] = None,
                  t_max: Optional[float] = None,
                  z: Optional[int] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query items based on 4D coordinate constraints.
        
        Args:
            r_min: Minimum radial distance
            r_max: Maximum radial distance
            theta_min: Minimum angular position
            theta_max: Maximum angular position
            t_min: Minimum temporal position
            t_max: Maximum temporal position
            z: Specific context layer
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        results = []
        
        # Set default time bounds if not provided
        if t_min is None:
            t_min = float('-inf')
        if t_max is None:
            t_max = float('inf')
        
        # Check each item in the index
        for item_id, item_info in self.index.items():
            coords = item_info['coordinates']
            
            # Check if item matches all constraints
            if (
                r_min <= coords['r'] <= r_max and
                theta_min <= coords['theta'] <= theta_max and
                t_min <= coords['t'] <= t_max and
                (z is None or coords['z'] == z)
            ):
                # Get the full item
                item = self.get_item(item_id)
                if item:
                    results.append(item)
                
                # Check limit
                if len(results) >= limit:
                    break
        
        return results
    
    def delete_item(self, item_id: str) -> bool:
        """
        Delete an item from the database.
        
        Args:
            item_id: Item ID to delete
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        if item_id not in self.index:
            return False
        
        try:
            # Get item info from index
            item_info = self.index[item_id]
            
            # Delete item file
            item_path = item_info['path']
            if os.path.exists(item_path):
                os.remove(item_path)
            
            # Delete embedding file if it exists
            embedding_path = os.path.join(self.items_dir, f"{item_id}.embedding")
            if os.path.exists(embedding_path):
                os.remove(embedding_path)
            
            # Remove from index
            del self.index[item_id]
            
            # Save updated index
            with open(self.index_path, 'w') as f:
                json.dump(self.index, f, indent=2)
            
            # Update statistics
            self.stats['storage_operations'] += 1
            
            logger.debug(f"Deleted item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting item {item_id}: {e}")
            self.stats['errors'] += 1
            return False
    
    def clear_all(self) -> bool:
        """
        Clear all data from the database.
        
        Returns:
            True if clearing succeeded, False otherwise
        """
        try:
            # Delete all files in items directory
            for file_path in Path(self.items_dir).glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            
            # Reset index
            self.index = {}
            
            # Save empty index
            with open(self.index_path, 'w') as f:
                json.dump(self.index, f, indent=2)
            
            # Reset statistics
            self.stats = {
                'items_stored': 0,
                'items_retrieved': 0,
                'storage_operations': 1,
                'errors': 0
            }
            
            logger.info("Cleared all data from database")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current storage statistics.
        
        Returns:
            Statistics dictionary
        """
        # Add current item count
        self.stats['current_items'] = len(self.index)
        
        return self.stats 
"""
Temporal-Spatial Memory Database

This module provides access to the core functionality of the Temporal-Spatial
Memory database, with configurable implementations.
"""

import os
import sys
from typing import Type, Any, Dict

# Get environment variables or use defaults
__version__ = '0.1.0'

# Configuration for which implementation to use
# Set to True to use simplified implementation without external dependencies
# False to use the full implementation with rtree
__use_simplified_impl = False  # Always use the full implementation

def get_mesh_tube_class():
    """
    Get the full MeshTube class.
    
    Returns:
        The full MeshTube class
    """
    try:
        from src.models.mesh_tube import MeshTube
        return MeshTube
    except ImportError as e:
        raise ImportError(f"Unable to import full MeshTube implementation: {e}. Please check installation.")

def set_storage_path(path: str) -> None:
    """
    Set the default storage path for saving databases.
    
    Args:
        path: Directory to store databases
    """
    os.makedirs(path, exist_ok=True)
    os.environ['MESHTUBE_STORAGE_PATH'] = path
    
def get_storage_path() -> str:
    """Get the default storage path."""
    return os.environ.get('MESHTUBE_STORAGE_PATH', 'data') 
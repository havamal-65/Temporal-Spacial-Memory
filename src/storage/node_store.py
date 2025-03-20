"""
Storage interface for the Temporal-Spatial Knowledge Database.

This module defines the abstract NodeStore class and its implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple
from uuid import UUID
import os
from pathlib import Path

# Import from node_v2 instead of node
from ..core.node_v2 import Node
from ..core.exceptions import NodeError


class NodeStore(ABC):
    """
    Abstract base class for node storage.
    
    This defines the interface that all node storage implementations must follow.
    """
    
    @abstractmethod
    def put(self, node: Node) -> None:
        """
        Store a node.
        
        Args:
            node: The node to store
        """
        pass
    
    @abstractmethod
    def get(self, node_id: UUID) -> Optional[Node]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            The node if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, node_id: UUID) -> bool:
        """
        Delete a node by its ID.
        
        Args:
            node_id: The ID of the node to delete
            
        Returns:
            True if the node was deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, node_id: UUID) -> bool:
        """
        Check if a node exists.
        
        Args:
            node_id: The ID of the node to check
            
        Returns:
            True if the node exists, False otherwise
        """
        pass
    
    @abstractmethod
    def list_ids(self) -> List[UUID]:
        """
        List all node IDs.
        
        Returns:
            A list of all node IDs
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count the number of nodes.
        
        Returns:
            The number of nodes
        """
        pass
    
    def save(self, node: Node) -> None:
        """
        Alias for put to match RocksDB convention.
        
        Args:
            node: The node to store
        """
        self.put(node)
    
    def get_many(self, node_ids: List[UUID]) -> Dict[UUID, Node]:
        """
        Retrieve multiple nodes by their IDs.
        
        Default implementation calls get for each ID, but implementations
        can override this for batch efficiency.
        
        Args:
            node_ids: The IDs of the nodes to retrieve
            
        Returns:
            A dictionary mapping IDs to nodes
        """
        return {node_id: node for node_id in node_ids 
                if (node := self.get(node_id)) is not None}
    
    def put_many(self, nodes: List[Node]) -> None:
        """
        Store multiple nodes.
        
        Default implementation calls put for each node, but implementations
        can override this for batch efficiency.
        
        Args:
            nodes: The nodes to store
        """
        for node in nodes:
            self.put(node)
    
    def close(self) -> None:
        """
        Close the store and release resources.
        
        The default implementation does nothing, but implementations that use external
        resources should override this to properly release them.
        """
        pass


class InMemoryNodeStore(NodeStore):
    """In-memory implementation of NodeStore using a dictionary."""
    
    def __init__(self):
        """Initialize an empty store."""
        self.nodes: Dict[UUID, Node] = {}
    
    def put(self, node: Node) -> None:
        """Store a node in memory."""
        self.nodes[node.id] = node
    
    def get(self, node_id: UUID) -> Optional[Node]:
        """Retrieve a node from memory."""
        return self.nodes.get(node_id)
    
    def delete(self, node_id: UUID) -> bool:
        """Delete a node from memory."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False
    
    def exists(self, node_id: UUID) -> bool:
        """Check if a node exists in memory."""
        return node_id in self.nodes
    
    def list_ids(self) -> List[UUID]:
        """List all node IDs in memory."""
        return list(self.nodes.keys())
    
    def count(self) -> int:
        """Count the number of nodes in memory."""
        return len(self.nodes)
    
    def clear(self) -> None:
        """Clear all nodes from memory."""
        self.nodes.clear() 
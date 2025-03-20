"""
R-tree node structure implementation for the Temporal-Spatial Knowledge Database.

This module provides the core R-tree node classes used for spatial indexing.
"""

from __future__ import annotations
from typing import List, Optional, Union, Set, Dict, Tuple
from uuid import UUID
from weakref import ref, ReferenceType

from ..core.coordinates import SpatioTemporalCoordinate
from .rectangle import Rectangle


class RTreeEntry:
    """
    An entry in a leaf node of the R-tree.
    
    This class represents a single entry in a leaf node of the R-tree,
    pointing to a node in the database.
    """
    
    def __init__(self, mbr: Rectangle, node_id: UUID):
        """
        Initialize a new R-tree entry.
        
        Args:
            mbr: The minimum bounding rectangle for this entry
            node_id: The ID of the node in the database
        """
        self.mbr = mbr
        self.node_id = node_id
    
    def __repr__(self) -> str:
        """String representation of the entry."""
        return f"RTreeEntry(node_id={self.node_id}, mbr={self.mbr})"


class RTreeNode:
    """
    A node in the R-tree structure.
    
    This class represents a node in the R-tree structure, which can be
    either a leaf node containing entries pointing to database nodes,
    or a non-leaf node containing references to child R-tree nodes.
    """
    
    def __init__(self, level: int, is_leaf: bool, parent: Optional[ReferenceType] = None):
        """
        Initialize a new R-tree node.
        
        Args:
            level: The level in the tree (0 for leaf nodes)
            is_leaf: Whether this is a leaf node
            parent: Weak reference to the parent node (to avoid circular references)
        """
        self.level = level
        self.is_leaf = is_leaf
        self.parent = parent
        self.entries: List[Union[RTreeEntry, RTreeNodeRef]] = []
    
    def mbr(self) -> Rectangle:
        """
        Calculate the minimum bounding rectangle for this node.
        
        Returns:
            The minimum bounding rectangle containing all entries
            
        Raises:
            ValueError: If the node has no entries
        """
        if not self.entries:
            raise ValueError("Cannot calculate MBR for empty node")
        
        # Start with the MBR of the first entry
        result = self.entries[0].mbr
        
        # Merge with the MBRs of the remaining entries
        for entry in self.entries[1:]:
            result = result.merge(entry.mbr)
        
        return result
    
    def add_entry(self, entry: Union[RTreeEntry, RTreeNodeRef]) -> None:
        """
        Add an entry to this node.
        
        Args:
            entry: The entry to add
        """
        self.entries.append(entry)
        
        # If this is a node reference, update its parent pointer
        if isinstance(entry, RTreeNodeRef):
            entry.child_node.parent = ref(self)
    
    def remove_entry(self, entry: Union[RTreeEntry, RTreeNodeRef]) -> bool:
        """
        Remove an entry from this node.
        
        Args:
            entry: The entry to remove
            
        Returns:
            True if the entry was found and removed, False otherwise
        """
        try:
            self.entries.remove(entry)
            return True
        except ValueError:
            return False
    
    def find_entry(self, node_id: UUID) -> Optional[RTreeEntry]:
        """
        Find an entry by node ID.
        
        This only works for leaf nodes.
        
        Args:
            node_id: The node ID to find
            
        Returns:
            The entry if found, None otherwise
        """
        if not self.is_leaf:
            return None
        
        for entry in self.entries:
            if isinstance(entry, RTreeEntry) and entry.node_id == node_id:
                return entry
        
        return None
    
    def find_entries_intersecting(self, rect: Rectangle) -> List[Union[RTreeEntry, RTreeNodeRef]]:
        """
        Find all entries whose MBRs intersect with the given rectangle.
        
        Args:
            rect: The rectangle to intersect with
            
        Returns:
            List of intersecting entries
        """
        return [entry for entry in self.entries if entry.mbr.intersects(rect)]
    
    def find_entries_containing(self, coord: SpatioTemporalCoordinate) -> List[Union[RTreeEntry, RTreeNodeRef]]:
        """
        Find all entries whose MBRs contain the given coordinate.
        
        Args:
            coord: The coordinate to check
            
        Returns:
            List of entries containing the coordinate
        """
        return [entry for entry in self.entries if entry.mbr.contains(coord)]
    
    def is_full(self, max_entries: int) -> bool:
        """
        Check if this node is full.
        
        Args:
            max_entries: Maximum number of entries allowed
            
        Returns:
            True if the node is full, False otherwise
        """
        return len(self.entries) >= max_entries
    
    def is_underfull(self, min_entries: int) -> bool:
        """
        Check if this node is underfull.
        
        Args:
            min_entries: Minimum number of entries required
            
        Returns:
            True if the node is underfull, False otherwise
        """
        return len(self.entries) < min_entries
    
    def __repr__(self) -> str:
        """String representation of the node."""
        node_type = "Leaf" if self.is_leaf else "Internal"
        return f"{node_type}Node(level={self.level}, entries={len(self.entries)})"


class RTreeNodeRef:
    """
    A reference to a child node in the R-tree.
    
    This class represents a reference to a child node in a non-leaf
    node of the R-tree.
    """
    
    def __init__(self, mbr: Rectangle, child_node: RTreeNode):
        """
        Initialize a new R-tree node reference.
        
        Args:
            mbr: The minimum bounding rectangle for this child node
            child_node: The child node being referenced
        """
        self.mbr = mbr
        self.child_node = child_node
    
    def update_mbr(self) -> None:
        """
        Update the MBR to match the child node's current MBR.
        
        This is used when the child node's entries change.
        """
        try:
            self.mbr = self.child_node.mbr()
        except ValueError:
            # Child node is empty, so keep the existing MBR
            pass
    
    def __repr__(self) -> str:
        """String representation of the node reference."""
        return f"RTreeNodeRef(mbr={self.mbr}, child={self.child_node})" 
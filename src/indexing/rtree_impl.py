"""
R-tree implementation for the Temporal-Spatial Knowledge Database.

This module provides an implementation of the R-tree index structure
for efficient spatial queries in the three-dimensional space of the
Temporal-Spatial Knowledge Database.
"""

from __future__ import annotations
from typing import List, Set, Dict, Tuple, Optional, Any, Iterator, Union
from uuid import UUID
import heapq
import math

from ..core.coordinates import SpatioTemporalCoordinate
from ..core.exceptions import SpatialIndexError
from .rectangle import Rectangle
from .rtree_node import RTreeNode, RTreeEntry, RTreeNodeRef


class RTree:
    """
    R-tree implementation for spatial indexing.
    
    This class provides an implementation of the R-tree index structure,
    which efficiently supports spatial queries like range queries and
    nearest neighbor searches.
    """
    
    def __init__(self, 
                 max_entries: int = 50, 
                 min_entries: int = 20,
                 dimension_weights: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        """
        Initialize a new R-tree.
        
        Args:
            max_entries: Maximum number of entries in a node
            min_entries: Minimum number of entries in a node (except root)
            dimension_weights: Weights for each dimension (t, r, theta)
        """
        if min_entries < 1 or min_entries > max_entries // 2:
            raise ValueError(f"min_entries must be between 1 and {max_entries // 2}")
        
        self.root = RTreeNode(level=0, is_leaf=True)
        self.max_entries = max_entries
        self.min_entries = min_entries
        self.dimension_weights = dimension_weights
        self.size = 0
        
        # Keep track of coordinates for nodes
        self._node_coords: Dict[UUID, SpatioTemporalCoordinate] = {}
    
    def insert(self, coord: SpatioTemporalCoordinate, node_id: UUID) -> None:
        """
        Insert a node at the given coordinate.
        
        Args:
            coord: The coordinate to insert at
            node_id: The ID of the node to insert
            
        Raises:
            SpatialIndexError: If there's an error during insertion
        """
        try:
            # Create a small rectangle around the coordinate
            entry_rect = Rectangle.from_coordinate(coord)
            entry = RTreeEntry(entry_rect, node_id)
            
            # Choose leaf node to insert into
            leaf = self._choose_leaf(coord)
            
            # Add the entry to the leaf
            leaf.add_entry(entry)
            
            # Store the coordinate for later use
            self._node_coords[node_id] = coord
            
            # Split if necessary and adjust the tree
            self._adjust_tree(leaf)
            
            # Increment size
            self.size += 1
        except Exception as e:
            raise SpatialIndexError(f"Error inserting node {node_id}: {e}") from e
    
    def delete(self, coord: SpatioTemporalCoordinate, node_id: UUID) -> bool:
        """
        Delete a node at the given coordinate.
        
        Args:
            coord: The coordinate of the node
            node_id: The ID of the node to delete
            
        Returns:
            True if the node was found and deleted, False otherwise
            
        Raises:
            SpatialIndexError: If there's an error during deletion
        """
        try:
            # Find the leaf node containing the entry
            leaf = self._find_leaf(node_id)
            if not leaf:
                return False
            
            # Find the entry in the leaf
            entry = leaf.find_entry(node_id)
            if not entry:
                return False
            
            # Remove the entry from the leaf
            leaf.remove_entry(entry)
            
            # Remove the coordinate from our mapping
            if node_id in self._node_coords:
                del self._node_coords[node_id]
            
            # Condense the tree if necessary
            self._condense_tree(leaf)
            
            # Decrement size
            self.size -= 1
            
            # If the root has only one child and is not a leaf, make the child the new root
            if not self.root.is_leaf and len(self.root.entries) == 1:
                old_root = self.root
                self.root = old_root.entries[0].child_node
                self.root.parent = None
            
            return True
        except Exception as e:
            raise SpatialIndexError(f"Error deleting node {node_id}: {e}") from e
    
    def update(self, old_coord: SpatioTemporalCoordinate, 
               new_coord: SpatioTemporalCoordinate, 
               node_id: UUID) -> None:
        """
        Update the position of a node.
        
        Args:
            old_coord: The old coordinate of the node
            new_coord: The new coordinate to move the node to
            node_id: The ID of the node to update
            
        Raises:
            SpatialIndexError: If there's an error during update
        """
        try:
            # Delete the old entry and insert a new one
            if self.delete(old_coord, node_id):
                self.insert(new_coord, node_id)
            else:
                # Node wasn't found at old_coord, just insert at new_coord
                self.insert(new_coord, node_id)
        except Exception as e:
            raise SpatialIndexError(f"Error updating node {node_id}: {e}") from e
    
    def find_exact(self, coord: SpatioTemporalCoordinate) -> List[UUID]:
        """
        Find nodes at the exact coordinate.
        
        Args:
            coord: The coordinate to search for
            
        Returns:
            List of node IDs at the coordinate
            
        Raises:
            SpatialIndexError: If there's an error during the search
        """
        try:
            # Create a small rectangle around the coordinate for the search
            search_rect = Rectangle.from_coordinate(coord)
            
            # Perform a range query with this small rectangle
            return self.range_query(search_rect)
        except Exception as e:
            raise SpatialIndexError(f"Error finding nodes at {coord}: {e}") from e
    
    def range_query(self, query_rect: Rectangle) -> List[UUID]:
        """
        Find all nodes within the given rectangle.
        
        Args:
            query_rect: The rectangle to search within
            
        Returns:
            List of node IDs within the rectangle
            
        Raises:
            SpatialIndexError: If there's an error during the query
        """
        try:
            result: Set[UUID] = set()
            self._range_query_recursive(self.root, query_rect, result)
            return list(result)
        except Exception as e:
            raise SpatialIndexError(f"Error performing range query: {e}") from e
    
    def nearest_neighbors(self, 
                          coord: SpatioTemporalCoordinate, 
                          k: int = 10) -> List[Tuple[UUID, float]]:
        """
        Find k nearest neighbors to the given coordinate.
        
        Args:
            coord: The coordinate to search near
            k: Maximum number of neighbors to return
            
        Returns:
            List of (node_id, distance) tuples sorted by distance
            
        Raises:
            SpatialIndexError: If there's an error during the search
        """
        try:
            # Priority queue for nearest neighbor search
            # We use a max heap to efficiently maintain the k nearest neighbors
            candidates: List[Tuple[float, UUID]] = []
            
            # Maximum distance found so far (initialize to infinity)
            max_dist = float('inf')
            
            # Recursively search for nearest neighbors
            self._nearest_neighbors_recursive(self.root, coord, k, candidates, max_dist)
            
            # Convert to list of (node_id, distance) tuples sorted by distance
            result = []
            for dist, node_id in sorted(candidates):
                result.append((node_id, dist))
            
            return result
        except Exception as e:
            raise SpatialIndexError(f"Error finding nearest neighbors to {coord}: {e}") from e
    
    def _choose_leaf(self, coord: SpatioTemporalCoordinate) -> RTreeNode:
        """
        Choose appropriate leaf node for insertion.
        
        This method traverses the tree from the root to a leaf, choosing
        the best path based on the least enlargement criterion.
        
        Args:
            coord: The coordinate to insert
            
        Returns:
            The chosen leaf node
        """
        node = self.root
        
        # Create a small rectangle around the coordinate
        entry_rect = Rectangle.from_coordinate(coord)
        
        while not node.is_leaf:
            best_entry = None
            best_enlargement = float('inf')
            
            for entry in node.entries:
                # Calculate how much the entry's MBR would need to be enlarged
                enlarged = entry.mbr.enlarge(coord)
                enlargement = enlarged.area() - entry.mbr.area()
                
                # Choose the entry that requires the least enlargement
                if best_entry is None or enlargement < best_enlargement:
                    best_entry = entry
                    best_enlargement = enlargement
                elif enlargement == best_enlargement:
                    # Break ties by choosing the entry with the smallest area
                    if entry.mbr.area() < best_entry.mbr.area():
                        best_entry = entry
                        best_enlargement = enlargement
            
            # Move to the next level
            node = best_entry.child_node
        
        return node
    
    def _split_node(self, node: RTreeNode) -> Tuple[RTreeNode, RTreeNode]:
        """
        Split a node when it exceeds capacity.
        
        This method implements the quadratic split algorithm, which is a
        good compromise between split quality and computational cost.
        
        Args:
            node: The node to split
            
        Returns:
            Tuple of (original_node, new_node)
        """
        # Create a new node at the same level
        new_node = RTreeNode(level=node.level, is_leaf=node.is_leaf)
        
        # Collect all entries from the node
        all_entries = node.entries.copy()
        
        # Clear the original node
        node.entries = []
        
        # Step 1: Pick two seeds for the two groups
        seed1, seed2 = self._pick_seeds(all_entries)
        
        # Step 2: Add seeds to their respective nodes
        node.add_entry(seed1)
        new_node.add_entry(seed2)
        
        # Remove seeds from all_entries
        all_entries.remove(seed1)
        all_entries.remove(seed2)
        
        # Step 3: Assign remaining entries
        while all_entries:
            # If one group is getting too small, assign all remaining entries to it
            if len(node.entries) + len(all_entries) <= self.min_entries:
                # Assign all remaining entries to original node
                for entry in all_entries:
                    node.add_entry(entry)
                all_entries = []
                break
            
            if len(new_node.entries) + len(all_entries) <= self.min_entries:
                # Assign all remaining entries to new node
                for entry in all_entries:
                    new_node.add_entry(entry)
                all_entries = []
                break
            
            # Find the entry with the maximum difference in enlargement
            best_entry, preference = self._pick_next(all_entries, node, new_node)
            
            # Add to the preferred node
            if preference == 1:
                node.add_entry(best_entry)
            else:
                new_node.add_entry(best_entry)
            
            # Remove from all_entries
            all_entries.remove(best_entry)
        
        return node, new_node
    
    def _pick_seeds(self, entries: List[Union[RTreeEntry, RTreeNodeRef]]) -> Tuple[Union[RTreeEntry, RTreeNodeRef], Union[RTreeEntry, RTreeNodeRef]]:
        """
        Pick two seed entries for the quadratic split algorithm.
        
        This method finds the pair of entries that would waste the most
        area if put in the same node.
        
        Args:
            entries: List of entries to choose from
            
        Returns:
            Tuple of (seed1, seed2)
        """
        max_waste = float('-inf')
        seeds = None
        
        for i, entry1 in enumerate(entries):
            for j, entry2 in enumerate(entries[i+1:], i+1):
                # Calculate the waste (dead space) if these entries were paired
                merged = entry1.mbr.merge(entry2.mbr)
                waste = merged.area() - entry1.mbr.area() - entry2.mbr.area()
                
                if waste > max_waste:
                    max_waste = waste
                    seeds = (entry1, entry2)
        
        return seeds
    
    def _pick_next(self, entries: List[Union[RTreeEntry, RTreeNodeRef]], 
                  node1: RTreeNode, node2: RTreeNode) -> Tuple[Union[RTreeEntry, RTreeNodeRef], int]:
        """
        Pick the next entry to assign during node splitting.
        
        This method finds the entry with the maximum difference in
        enlargement when assigned to each of the two nodes.
        
        Args:
            entries: List of entries to choose from
            node1: The first node
            node2: The second node
            
        Returns:
            Tuple of (chosen_entry, preference)
            where preference is 1 for node1, 2 for node2
        """
        max_diff = float('-inf')
        best_entry = None
        preference = 0
        
        # Calculate MBRs for both nodes
        mbr1 = node1.mbr()
        mbr2 = node2.mbr()
        
        for entry in entries:
            # Calculate enlargement for each node
            enlarged1 = mbr1.merge(entry.mbr)
            enlarged2 = mbr2.merge(entry.mbr)
            
            enlargement1 = enlarged1.area() - mbr1.area()
            enlargement2 = enlarged2.area() - mbr2.area()
            
            # Calculate the difference in enlargement
            diff = abs(enlargement1 - enlargement2)
            
            if diff > max_diff:
                max_diff = diff
                best_entry = entry
                preference = 1 if enlargement1 < enlargement2 else 2
        
        return best_entry, preference
    
    def _adjust_tree(self, node: RTreeNode, new_node: Optional[RTreeNode] = None) -> None:
        """
        Adjust the tree after insertion or deletion.
        
        This method propagates changes up the tree, splitting nodes as
        necessary and updating MBRs.
        
        Args:
            node: The node that was modified
            new_node: Optional new node created from a split
        """
        # If this is the root, handle specially
        if node == self.root:
            if new_node:
                # Create a new root
                new_root = RTreeNode(level=node.level + 1, is_leaf=False)
                
                # Add the old root and the new node as children
                new_root.add_entry(RTreeNodeRef(node.mbr(), node))
                new_root.add_entry(RTreeNodeRef(new_node.mbr(), new_node))
                
                # Update the root
                self.root = new_root
            return
        
        # Update the MBR in the parent
        parent = node.parent()
        
        # Find the entry in the parent that points to this node
        for entry in parent.entries:
            if isinstance(entry, RTreeNodeRef) and entry.child_node == node:
                # Update the MBR
                entry.update_mbr()
                break
        
        # If we have a new node, add it to the parent
        if new_node:
            # Create a new entry for the new node
            new_entry = RTreeNodeRef(new_node.mbr(), new_node)
            
            # Add to the parent
            parent.add_entry(new_entry)
            
            # Check if the parent needs to be split
            if parent.is_full(self.max_entries):
                # Split the parent
                parent, parent_new = self._split_node(parent)
                
                # Propagate the split up the tree
                self._adjust_tree(parent, parent_new)
            else:
                # Just propagate the MBR update
                self._adjust_tree(parent)
        else:
            # Just propagate the MBR update
            self._adjust_tree(parent)
    
    def _find_leaf(self, node_id: UUID) -> Optional[RTreeNode]:
        """
        Find the leaf node containing the entry for the given node ID.
        
        Args:
            node_id: The node ID to find
            
        Returns:
            The leaf node containing the entry, or None if not found
        """
        return self._find_leaf_recursive(self.root, node_id)
    
    def _find_leaf_recursive(self, node: RTreeNode, node_id: UUID) -> Optional[RTreeNode]:
        """
        Recursive helper for _find_leaf.
        
        Args:
            node: The current node to search
            node_id: The node ID to find
            
        Returns:
            The leaf node containing the entry, or None if not found
        """
        if node.is_leaf:
            # Check if this leaf contains the entry
            for entry in node.entries:
                if isinstance(entry, RTreeEntry) and entry.node_id == node_id:
                    return node
            return None
        
        # Check each child
        for entry in node.entries:
            if isinstance(entry, RTreeNodeRef):
                result = self._find_leaf_recursive(entry.child_node, node_id)
                if result:
                    return result
        
        return None
    
    def _condense_tree(self, leaf: RTreeNode) -> None:
        """
        Condense the tree after deletion.
        
        This method removes underfull nodes and reinserts their entries.
        
        Args:
            leaf: The leaf node where deletion occurred
        """
        # Collect nodes to be reinserted
        reinsert_nodes = []
        
        current = leaf
        
        # Traverse up the tree
        while current != self.root:
            parent = current.parent()
            
            # Find the entry in the parent that points to this node
            parent_entry = None
            for entry in parent.entries:
                if isinstance(entry, RTreeNodeRef) and entry.child_node == current:
                    parent_entry = entry
                    break
            
            # Check if this node is underfull
            if current.is_underfull(self.min_entries):
                # Remove this node from its parent
                parent.remove_entry(parent_entry)
                
                # Collect entries for reinsertion
                reinsert_nodes.extend(current.entries)
            else:
                # Update the MBR in the parent
                parent_entry.update_mbr()
            
            # Move up to the parent
            current = parent
        
        # Reinsert all entries from eliminated nodes
        for entry in reinsert_nodes:
            if isinstance(entry, RTreeEntry):
                # Get the coordinate for this node
                if entry.node_id in self._node_coords:
                    coord = self._node_coords[entry.node_id]
                    # Reinsert the entry
                    self.delete(coord, entry.node_id)
                    self.insert(coord, entry.node_id)
            elif isinstance(entry, RTreeNodeRef):
                # Reinsert all entries from this subtree
                self._reinsert_subtree(entry.child_node)
    
    def _reinsert_subtree(self, node: RTreeNode) -> None:
        """
        Reinsert all entries from a subtree.
        
        Args:
            node: The root of the subtree to reinsert
        """
        if node.is_leaf:
            # Reinsert each entry
            for entry in node.entries:
                if isinstance(entry, RTreeEntry) and entry.node_id in self._node_coords:
                    coord = self._node_coords[entry.node_id]
                    self.insert(coord, entry.node_id)
        else:
            # Reinsert each subtree
            for entry in node.entries:
                if isinstance(entry, RTreeNodeRef):
                    self._reinsert_subtree(entry.child_node)
    
    def _range_query_recursive(self, node: RTreeNode, query_rect: Rectangle, result: Set[UUID]) -> None:
        """
        Recursive helper for range_query.
        
        Args:
            node: The current node to search
            query_rect: The rectangle to search within
            result: Set to collect the results
        """
        # Check each entry in this node
        for entry in node.entries:
            # Check if this entry's MBR intersects with the query rectangle
            if entry.mbr.intersects(query_rect):
                if node.is_leaf:
                    # Add the node ID to the result
                    if isinstance(entry, RTreeEntry):
                        result.add(entry.node_id)
                else:
                    # Recursively search the child node
                    if isinstance(entry, RTreeNodeRef):
                        self._range_query_recursive(entry.child_node, query_rect, result)
    
    def _nearest_neighbors_recursive(self, node: RTreeNode, 
                                    coord: SpatioTemporalCoordinate,
                                    k: int,
                                    candidates: List[Tuple[float, UUID]],
                                    max_dist: float) -> float:
        """
        Recursive helper for nearest_neighbors.
        
        Args:
            node: The current node to search
            coord: The coordinate to search near
            k: Maximum number of neighbors to find
            candidates: Priority queue to collect results
            max_dist: Maximum distance found so far
            
        Returns:
            Updated maximum distance
        """
        if node.is_leaf:
            # Check each entry in this leaf
            for entry in node.entries:
                if isinstance(entry, RTreeEntry):
                    # Calculate the distance to this entry
                    if entry.node_id in self._node_coords:
                        entry_coord = self._node_coords[entry.node_id]
                        dist = coord.distance_to(entry_coord)
                        
                        # If we haven't found k neighbors yet, or this entry is closer than the furthest one
                        if len(candidates) < k:
                            # Add to the candidates
                            heapq.heappush(candidates, (-dist, entry.node_id))
                            
                            # Update max_dist if we now have k candidates
                            if len(candidates) == k:
                                max_dist = -candidates[0][0]
                        elif dist < max_dist:
                            # Replace the furthest candidate
                            heapq.heappushpop(candidates, (-dist, entry.node_id))
                            
                            # Update max_dist
                            max_dist = -candidates[0][0]
        else:
            # Sort entries by distance to the coordinate
            entries_with_dist = []
            for entry in node.entries:
                # Calculate minimum distance to the entry's MBR
                min_dist = self._min_dist_to_rect(coord, entry.mbr)
                entries_with_dist.append((min_dist, entry))
            
            # Sort by distance
            entries_with_dist.sort()
            
            # Visit entries in order of distance
            for min_dist, entry in entries_with_dist:
                # Prune branches that cannot contain closer neighbors
                if min_dist > max_dist and len(candidates) == k:
                    break
                
                # Recursively search the child node
                if isinstance(entry, RTreeNodeRef):
                    max_dist = self._nearest_neighbors_recursive(
                        entry.child_node, coord, k, candidates, max_dist
                    )
        
        return max_dist
    
    def _min_dist_to_rect(self, coord: SpatioTemporalCoordinate, rect: Rectangle) -> float:
        """
        Calculate the minimum distance from a coordinate to a rectangle.
        
        Args:
            coord: The coordinate
            rect: The rectangle
            
        Returns:
            The minimum distance
        """
        # Check if the coordinate is inside the rectangle
        if rect.contains(coord):
            return 0.0
        
        # Calculate the distance to the nearest point on the rectangle
        # This is a simplified approximation that doesn't fully account for
        # the cylindrical nature of the space, but is sufficient for most cases
        
        # Calculate distance in each dimension
        t_dist = 0.0
        if coord.t < rect.min_t:
            t_dist = rect.min_t - coord.t
        elif coord.t > rect.max_t:
            t_dist = coord.t - rect.max_t
        
        r_dist = 0.0
        if coord.r < rect.min_r:
            r_dist = rect.min_r - coord.r
        elif coord.r > rect.max_r:
            r_dist = coord.r - rect.max_r
        
        theta_dist = 0.0
        if rect.min_theta <= rect.max_theta:
            # Normal case (no wrap-around)
            if coord.theta < rect.min_theta:
                theta_dist = min(
                    rect.min_theta - coord.theta,
                    coord.theta + 2 * math.pi - rect.max_theta
                )
            elif coord.theta > rect.max_theta:
                theta_dist = min(
                    coord.theta - rect.max_theta,
                    rect.min_theta + 2 * math.pi - coord.theta
                )
        else:
            # Wrap-around case
            if coord.theta > rect.max_theta and coord.theta < rect.min_theta:
                theta_dist = min(
                    coord.theta - rect.max_theta,
                    rect.min_theta - coord.theta
                )
        
        # Apply dimension weights
        t_dist *= self.dimension_weights[0]
        r_dist *= self.dimension_weights[1]
        theta_dist *= self.dimension_weights[2]
        
        # Calculate Euclidean distance
        return math.sqrt(t_dist**2 + r_dist**2 + theta_dist**2)
    
    def __len__(self) -> int:
        """Get the number of entries in the tree."""
        return self.size 
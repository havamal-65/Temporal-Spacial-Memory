"""
Time navigation for the delta chain system.

This module provides the TimeNavigator class for navigating
node content through time, enabling time-travel capabilities.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from uuid import UUID
import copy
import difflib
import json

from .store import DeltaStore
from .reconstruction import StateReconstructor
from ..storage.node_store import NodeStore


class TimeNavigator:
    """
    Enables temporal navigation through node content history.
    
    This class provides interfaces for exploring the evolution of
    node content over time, including history visualization and
    state comparison.
    """
    
    def __init__(self, delta_store: DeltaStore, node_store: NodeStore):
        """
        Initialize a time navigator.
        
        Args:
            delta_store: Storage for delta records
            node_store: Storage for nodes
        """
        self.delta_store = delta_store
        self.node_store = node_store
        self.reconstructor = StateReconstructor(delta_store)
    
    def get_node_at_time(self, 
                        node_id: UUID, 
                        timestamp: float) -> Optional[Dict[str, Any]]:
        """
        Get a node as it existed at a specific time.
        
        Args:
            node_id: The ID of the node
            timestamp: The target timestamp
            
        Returns:
            The node content at the given time, or None if not found
        """
        # Get the node's origin content
        node = self.node_store.get(str(node_id))
        if not node:
            return None
            
        # Get the origin content and timestamp
        origin_content = node.content
        origin_timestamp = 0.0  # Default to 0 for nodes without a timestamp
        if node.coordinates and node.coordinates.temporal:
            origin_timestamp = node.coordinates.temporal.timestamp.timestamp()
            
        # If requested time is before the node existed, return None
        if timestamp < origin_timestamp:
            return None
            
        # Reconstruct the state at the target time
        return self.reconstructor.reconstruct_state(
            node_id=node_id,
            origin_content=origin_content,
            target_timestamp=timestamp
        )
    
    def get_delta_history(self, 
                         node_id: UUID) -> List[Tuple[float, str]]:
        """
        Get a timeline of changes for a node.
        
        Args:
            node_id: The ID of the node
            
        Returns:
            List of (timestamp, summary) tuples in chronological order
        """
        # Get all deltas for the node
        deltas = self.delta_store.get_deltas_for_node(node_id)
        
        # Extract timestamps and summaries
        history = [(delta.timestamp, delta.get_summary()) for delta in deltas]
        
        # Sort by timestamp
        history.sort(key=lambda x: x[0])
        
        return history
    
    def compare_states(self,
                      node_id: UUID,
                      timestamp1: float,
                      timestamp2: float) -> Dict[str, Any]:
        """
        Compare node state between two points in time.
        
        Args:
            node_id: The ID of the node
            timestamp1: First timestamp
            timestamp2: Second timestamp
            
        Returns:
            Comparison result with added, removed, and changed fields
        """
        # Get the states at both timestamps
        state1 = self.get_node_at_time(node_id, timestamp1)
        state2 = self.get_node_at_time(node_id, timestamp2)
        
        if not state1 or not state2:
            return {"error": "Unable to retrieve one or both states"}
            
        # Initialize result
        result = {
            "added": {},
            "removed": {},
            "changed": {},
            "timestamp1": timestamp1,
            "timestamp2": timestamp2
        }
        
        # Find all keys
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            # Key only in state2 (added)
            if key not in state1:
                result["added"][key] = state2[key]
            # Key only in state1 (removed)
            elif key not in state2:
                result["removed"][key] = state1[key]
            # Key in both states
            elif state1[key] != state2[key]:
                # Handle nested dictionaries recursively
                if isinstance(state1[key], dict) and isinstance(state2[key], dict):
                    nested_diff = self._compare_dict(state1[key], state2[key])
                    if any(nested_diff.values()):
                        result["changed"][key] = nested_diff
                # Handle lists
                elif isinstance(state1[key], list) and isinstance(state2[key], list):
                    # Simple list comparison for now
                    result["changed"][key] = {
                        "before": state1[key],
                        "after": state2[key]
                    }
                # Handle strings with diff
                elif isinstance(state1[key], str) and isinstance(state2[key], str):
                    # For long strings, show a diff
                    if len(state1[key]) > 100 or len(state2[key]) > 100:
                        result["changed"][key] = {
                            "type": "text_diff",
                            "diff": self._text_diff(state1[key], state2[key])
                        }
                    else:
                        result["changed"][key] = {
                            "before": state1[key],
                            "after": state2[key]
                        }
                # Simple value change
                else:
                    result["changed"][key] = {
                        "before": state1[key],
                        "after": state2[key]
                    }
        
        return result
    
    def _compare_dict(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two dictionaries recursively.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary
            
        Returns:
            Comparison result with added, removed, and changed fields
        """
        result = {
            "added": {},
            "removed": {},
            "changed": {}
        }
        
        # Find all keys
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            # Key only in dict2 (added)
            if key not in dict1:
                result["added"][key] = dict2[key]
            # Key only in dict1 (removed)
            elif key not in dict2:
                result["removed"][key] = dict1[key]
            # Key in both dictionaries
            elif dict1[key] != dict2[key]:
                # Handle nested dictionaries recursively
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    nested_diff = self._compare_dict(dict1[key], dict2[key])
                    if any(nested_diff.values()):
                        result["changed"][key] = nested_diff
                # Simple value change
                else:
                    result["changed"][key] = {
                        "before": dict1[key],
                        "after": dict2[key]
                    }
        
        return result
    
    def _text_diff(self, text1: str, text2: str) -> List[Dict[str, Any]]:
        """
        Generate a human-readable diff between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            List of diff operations
        """
        result = []
        matcher = difflib.SequenceMatcher(None, text1, text2)
        
        for op, text1_start, text1_end, text2_start, text2_end in matcher.get_opcodes():
            if op == 'equal':
                # Show some context around changes
                if len(result) > 0 and result[-1]['op'] != 'equal':
                    result.append({
                        'op': 'equal',
                        'text': text1[text1_start:text1_end]
                    })
            elif op == 'replace':
                result.append({
                    'op': 'replace',
                    'removed': text1[text1_start:text1_end],
                    'added': text2[text2_start:text2_end]
                })
            elif op == 'delete':
                result.append({
                    'op': 'remove',
                    'text': text1[text1_start:text1_end]
                })
            elif op == 'insert':
                result.append({
                    'op': 'add',
                    'text': text2[text2_start:text2_end]
                })
        
        return result
    
    def get_significant_timestamps(self, node_id: UUID, max_points: int = 10) -> List[float]:
        """
        Get significant timestamps in a node's history.
        
        This is useful for creating waypoints for navigation or visualization.
        
        Args:
            node_id: The ID of the node
            max_points: Maximum number of timestamps to return
            
        Returns:
            List of significant timestamps
        """
        # Get all deltas for the node
        deltas = self.delta_store.get_deltas_for_node(node_id)
        
        if not deltas:
            return []
            
        # Sort by timestamp
        deltas.sort(key=lambda d: d.timestamp)
        
        # If we have fewer deltas than max_points, return all timestamps
        if len(deltas) <= max_points:
            return [delta.timestamp for delta in deltas]
            
        # Otherwise, select evenly spaced timestamps
        step = len(deltas) / (max_points - 1)
        indices = [int(i * step) for i in range(max_points - 1)] + [len(deltas) - 1]
        
        return [deltas[i].timestamp for i in indices]
    
    def get_change_frequency(self, node_id: UUID, time_window: float = 86400.0) -> List[Tuple[float, int]]:
        """
        Calculate the frequency of changes over time.
        
        Args:
            node_id: The ID of the node
            time_window: Size of time window in seconds (default: 1 day)
            
        Returns:
            List of (timestamp, change_count) tuples
        """
        # Get all deltas for the node
        deltas = self.delta_store.get_deltas_for_node(node_id)
        
        if not deltas:
            return []
            
        # Sort by timestamp
        deltas.sort(key=lambda d: d.timestamp)
        
        # Group by time windows
        result = []
        current_window = deltas[0].timestamp
        count = 0
        
        for delta in deltas:
            if delta.timestamp <= current_window + time_window:
                count += 1
            else:
                # Start a new window
                result.append((current_window, count))
                # Skip empty windows
                windows_to_skip = int((delta.timestamp - current_window) / time_window)
                current_window += windows_to_skip * time_window
                count = 1
        
        # Add the last window
        if count > 0:
            result.append((current_window, count))
            
        return result 
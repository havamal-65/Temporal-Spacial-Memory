import math
import random
from typing import List, Dict, Any, Optional, Tuple

from ..models.node import Node
from ..models.mesh_tube import MeshTube

class PositionCalculator:
    """
    Utility class for calculating optimal positions for new nodes in the mesh tube.
    
    This class helps determine the best placement for new information based on:
    - Relationship to existing nodes
    - Temporal position
    - Topic relevance
    """
    
    @staticmethod
    def suggest_position_for_new_topic(
            mesh_tube: MeshTube,
            content: Dict[str, Any],
            related_node_ids: List[str] = None,
            current_time: float = None
        ) -> Tuple[float, float, float]:
        """
        Suggest coordinates for a new topic node
        
        Args:
            mesh_tube: The mesh tube instance
            content: The content of the new node
            related_node_ids: IDs of nodes that are related to this one
            current_time: The current time value (defaults to max time + 1)
            
        Returns:
            A tuple of (time, distance, angle) coordinates
        """
        # Determine time coordinate
        if current_time is None:
            # Default to a time step after the latest node
            if mesh_tube.nodes:
                current_time = max(node.time for node in mesh_tube.nodes.values()) + 1.0
            else:
                current_time = 0.0
                
        # If no related nodes, place near center with random angle
        if not related_node_ids or not mesh_tube.nodes:
            distance = random.uniform(0.1, 0.5)  # Close to center
            angle = random.uniform(0, 360)  # Random angle
            return (current_time, distance, angle)
            
        # Calculate average position of related nodes
        related_nodes = [
            mesh_tube.get_node(node_id) 
            for node_id in related_node_ids
            if mesh_tube.get_node(node_id) is not None
        ]
        
        if not related_nodes:
            distance = random.uniform(0.1, 0.5)
            angle = random.uniform(0, 360)
            return (current_time, distance, angle)
            
        # Calculate average distance and angle
        avg_distance = sum(node.distance for node in related_nodes) / len(related_nodes)
        
        # For angle, we need to handle circularity
        # Convert to cartesian, average, then convert back
        x_sum = sum(node.distance * math.cos(math.radians(node.angle)) for node in related_nodes)
        y_sum = sum(node.distance * math.sin(math.radians(node.angle)) for node in related_nodes)
        
        # Calculate average position in cartesian
        avg_x = x_sum / len(related_nodes)
        avg_y = y_sum / len(related_nodes)
        
        # Convert back to polar coordinates
        distance = math.sqrt(avg_x**2 + avg_y**2)
        angle = math.degrees(math.atan2(avg_y, avg_x))
        if angle < 0:
            angle += 360  # Convert to 0-360 range
            
        # Add small random variations to prevent exact overlaps
        distance += random.uniform(-0.1, 0.1)
        angle += random.uniform(-10, 10)
        
        # Ensure distance is positive and angle is in range
        distance = max(0.1, distance)
        angle = angle % 360
        
        return (current_time, distance, angle)
    
    @staticmethod
    def suggest_position_for_delta(
            mesh_tube: MeshTube,
            original_node: Node,
            delta_content: Dict[str, Any],
            current_time: float = None,
            significance: float = 0.5  # 0 to 1, how significant is this change
        ) -> Tuple[float, float, float]:
        """
        Suggest coordinates for a delta (change) node
        
        Args:
            mesh_tube: The mesh tube instance
            original_node: The original node this is a delta of
            delta_content: The new/changed content
            current_time: Current time value (defaults to max time + 1)
            significance: How significant the change is (affects distance change)
            
        Returns:
            A tuple of (time, distance, angle) coordinates
        """
        # Determine time coordinate
        if current_time is None:
            # Default to a time step after the latest node
            if mesh_tube.nodes:
                current_time = max(node.time for node in mesh_tube.nodes.values()) + 1.0
            else:
                current_time = original_node.time + 1.0
        
        # For deltas, we generally keep a similar position as the original
        # But may adjust based on significance of change
        
        # Minor distance adjustment based on significance
        distance_adjustment = (random.uniform(-0.2, 0.2) * significance)
        new_distance = max(0.1, original_node.distance + distance_adjustment)
        
        # Small angle adjustment
        angle_adjustment = random.uniform(-5, 5) * significance
        new_angle = (original_node.angle + angle_adjustment) % 360
        
        return (current_time, new_distance, new_angle)
    
    @staticmethod
    def calculate_angular_distribution(
            mesh_tube: MeshTube,
            time_slice: float,
            num_segments: int = 12,
            tolerance: float = 0.1
        ) -> List[int]:
        """
        Calculate how nodes are distributed angularly in a time slice
        
        Args:
            mesh_tube: The mesh tube instance
            time_slice: The time value to analyze
            num_segments: Number of angular segments to divide the circle into
            tolerance: Time tolerance for including nodes
            
        Returns:
            List of counts per angular segment
        """
        # Get nodes in the time slice
        nodes = mesh_tube.get_temporal_slice(time_slice, tolerance)
        
        # Initialize segment counts
        segments = [0] * num_segments
        segment_size = 360 / num_segments
        
        # Count nodes in each segment
        for node in nodes:
            segment_idx = int(node.angle / segment_size) % num_segments
            segments[segment_idx] += 1
            
        return segments
    
    @staticmethod
    def find_balanced_angle(
            mesh_tube: MeshTube,
            time_slice: float,
            distance: float,
            tolerance: float = 0.1
        ) -> float:
        """
        Find an angle with the least nodes (to balance distribution)
        
        Args:
            mesh_tube: The mesh tube instance
            time_slice: The time value to analyze
            distance: The approximate distance from center
            tolerance: Time tolerance for including nodes
            
        Returns:
            An angle (in degrees) with balanced node distribution
        """
        # Get angular distribution
        num_segments = 36  # 10-degree segments
        distribution = PositionCalculator.calculate_angular_distribution(
            mesh_tube, time_slice, num_segments, tolerance
        )
        
        # Find segment with minimum count
        min_count = min(distribution)
        min_segments = [i for i, count in enumerate(distribution) if count == min_count]
        
        # Choose a random segment among the minimums
        chosen_segment = random.choice(min_segments)
        
        # Convert segment to angle (middle of segment)
        segment_size = 360 / num_segments
        angle = chosen_segment * segment_size + segment_size / 2
        
        # Add small random variation
        angle += random.uniform(-segment_size/4, segment_size/4)
        angle = angle % 360
        
        return angle 
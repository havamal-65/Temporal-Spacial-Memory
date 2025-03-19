from typing import List, Dict, Any, Optional
import math
import os

from ..models.mesh_tube import MeshTube
from ..models.node import Node

class MeshVisualizer:
    """
    A simple text-based visualizer for the Mesh Tube Knowledge Database.
    
    This class provides methods to visualize the structure in various ways:
    - Temporal slices (2D cross-sections)
    - Node connections
    - Distribution of nodes
    """
    
    @staticmethod
    def visualize_temporal_slice(
            mesh_tube: MeshTube,
            time: float,
            tolerance: float = 0.1,
            width: int = 60,
            height: int = 20,
            show_ids: bool = False
        ) -> str:
        """
        Generate an ASCII visualization of a temporal slice of the mesh tube.
        
        Args:
            mesh_tube: The mesh tube instance
            time: The time coordinate to visualize
            tolerance: Time tolerance for including nodes
            width: Width of the visualization
            height: Height of the visualization
            show_ids: Whether to show node IDs
            
        Returns:
            ASCII string visualization
        """
        # Get nodes in the time slice
        nodes = mesh_tube.get_temporal_slice(time, tolerance)
        
        # Determine max distance for normalization
        max_distance = 1.0
        if nodes:
            max_distance = max(node.distance for node in nodes) + 0.1
            
        # Create a blank canvas
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Draw a circular border
        center_x, center_y = width // 2, height // 2
        radius = min(center_x, center_y) - 1
        
        # Draw border
        for y in range(height):
            for x in range(width):
                dx, dy = x - center_x, y - center_y
                distance = math.sqrt(dx*dx + dy*dy)
                if abs(distance - radius) < 0.5:
                    grid[y][x] = '·'
        
        # Place nodes on the grid
        for node in nodes:
            # Normalize distance to radius
            norm_distance = (node.distance / max_distance) * radius
            
            # Convert angle (degrees) to radians
            angle_rad = math.radians(node.angle)
            
            # Calculate position
            x = center_x + int(norm_distance * math.cos(angle_rad))
            y = center_y + int(norm_distance * math.sin(angle_rad))
            
            # Ensure within bounds
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = 'O'  # Node marker
                
        # Draw center marker
        grid[center_y][center_x] = '+'
        
        # Convert grid to string
        visualization = f"Temporal Slice at t={time} (±{tolerance})\n"
        visualization += f"Nodes: {len(nodes)}\n"
        visualization += '\n'
        
        for row in grid:
            visualization += ''.join(row) + '\n'
            
        # Add node details if requested
        if show_ids and nodes:
            visualization += '\nNodes:\n'
            for i, node in enumerate(nodes):
                visualization += f"{i+1}. ID: {node.node_id[:8]}... "
                visualization += f"Pos: ({node.distance:.2f}, {node.angle:.1f}°)\n"
                
        return visualization
    
    @staticmethod
    def visualize_connections(mesh_tube: MeshTube, node_id: str) -> str:
        """
        Visualize the connections of a specific node
        
        Args:
            mesh_tube: The mesh tube instance
            node_id: The ID of the node to visualize
            
        Returns:
            ASCII string visualization
        """
        node = mesh_tube.get_node(node_id)
        if not node:
            return f"Node {node_id} not found."
            
        visualization = f"Connections for Node {node_id[:8]}...\n"
        visualization += f"Time: {node.time}, Pos: ({node.distance:.2f}, {node.angle:.1f}°)\n"
        visualization += f"Content: {str(node.content)[:50]}...\n\n"
        
        if not node.connections:
            visualization += "No connections.\n"
            return visualization
            
        visualization += f"Connected to {len(node.connections)} nodes:\n"
        
        for i, conn_id in enumerate(sorted(node.connections)):
            conn_node = mesh_tube.get_node(conn_id)
            if conn_node:
                # Calculate temporal and spatial distance
                temporal_dist = abs(conn_node.time - node.time)
                spatial_dist = node.spatial_distance(conn_node)
                
                visualization += f"{i+1}. ID: {conn_id[:8]}... "
                visualization += f"Time: {conn_node.time} (Δt={temporal_dist:.2f}), "
                visualization += f"Dist: {spatial_dist:.2f}\n"
                
        if node.delta_references:
            visualization += "\nDelta References:\n"
            for i, ref_id in enumerate(node.delta_references):
                ref_node = mesh_tube.get_node(ref_id)
                if ref_node:
                    visualization += f"{i+1}. ID: {ref_id[:8]}... Time: {ref_node.time}\n"
                    
        return visualization
    
    @staticmethod
    def visualize_timeline(
            mesh_tube: MeshTube,
            start_time: Optional[float] = None,
            end_time: Optional[float] = None,
            width: int = 80
        ) -> str:
        """
        Visualize node distribution over a timeline
        
        Args:
            mesh_tube: The mesh tube instance
            start_time: Start of timeline (defaults to min time)
            end_time: End of timeline (defaults to max time)
            width: Width of the visualization
            
        Returns:
            ASCII string visualization
        """
        if not mesh_tube.nodes:
            return "No nodes in database."
            
        # Determine time range
        times = [node.time for node in mesh_tube.nodes.values()]
        min_time = start_time if start_time is not None else min(times)
        max_time = end_time if end_time is not None else max(times)
        
        if min_time == max_time:
            min_time -= 0.5
            max_time += 0.5
            
        # Create timeline bins
        num_bins = width - 10
        bins = [0] * num_bins
        
        # Distribute nodes into bins
        for node in mesh_tube.nodes.values():
            if min_time <= node.time <= max_time:
                bin_idx = int((node.time - min_time) / (max_time - min_time) * (num_bins - 1))
                bin_idx = max(0, min(bin_idx, num_bins - 1))  # Ensure in bounds
                bins[bin_idx] += 1
                
        # Find max bin height for normalization
        max_height = max(bins) if bins else 1
        
        # Create the visualization
        visualization = f"Timeline: {min_time:.1f} to {max_time:.1f}\n"
        visualization += f"Total Nodes: {sum(bins)}\n\n"
        
        # Draw histogram
        for i in range(10, 0, -1):  # 10 rows of height
            threshold = i * max_height / 10
            line = "     "
            for count in bins:
                line += "█" if count >= threshold else " "
            visualization += line + "\n"
            
        # Draw timeline
        visualization += "     " + "▔" * num_bins + "\n"
        
        # Draw time markers
        markers = [min_time + (max_time - min_time) * i / 4 for i in range(5)]
        marker_line = "     "
        marker_positions = [int(num_bins * i / 4) for i in range(5)]
        
        for i, pos in enumerate(marker_positions):
            while len(marker_line) < pos + 5:
                marker_line += " "
            marker_line += "┬"
            
        visualization += marker_line + "\n"
        
        # Draw time labels
        label_line = "     "
        for i, pos in enumerate(marker_positions):
            time_label = f"{markers[i]:.1f}"
            label_pos = pos - len(time_label) // 2 + 5
            while len(label_line) < label_pos:
                label_line += " "
            label_line += time_label
            
        visualization += label_line + "\n"
        
        return visualization
    
    @staticmethod
    def print_mesh_stats(mesh_tube: MeshTube) -> str:
        """
        Generate statistics about the mesh tube
        
        Args:
            mesh_tube: The mesh tube instance
            
        Returns:
            ASCII string with statistics
        """
        if not mesh_tube.nodes:
            return "Empty database. No statistics available."
            
        node_count = len(mesh_tube.nodes)
        
        # Calculate connection stats
        connection_counts = [len(node.connections) for node in mesh_tube.nodes.values()]
        avg_connections = sum(connection_counts) / node_count if node_count else 0
        max_connections = max(connection_counts) if connection_counts else 0
        
        # Calculate time range
        times = [node.time for node in mesh_tube.nodes.values()]
        min_time, max_time = min(times), max(times)
        time_span = max_time - min_time
        
        # Calculate distance stats
        distances = [node.distance for node in mesh_tube.nodes.values()]
        avg_distance = sum(distances) / node_count
        max_distance = max(distances)
        
        # Calculate delta reference stats
        delta_counts = [len(node.delta_references) for node in mesh_tube.nodes.values()]
        nodes_with_deltas = sum(1 for c in delta_counts if c > 0)
        
        # Generate statistics string
        stats = f"Mesh Tube Statistics: {mesh_tube.name}\n"
        stats += f"{'=' * 40}\n"
        stats += f"Total Nodes: {node_count}\n"
        stats += f"Time Range: {min_time:.2f} to {max_time:.2f} (span: {time_span:.2f})\n"
        stats += f"Average Distance from Center: {avg_distance:.2f}\n"
        stats += f"Maximum Distance from Center: {max_distance:.2f}\n"
        stats += f"Average Connections per Node: {avg_connections:.2f}\n"
        stats += f"Most Connected Node: {max_connections} connections\n"
        stats += f"Nodes with Delta References: {nodes_with_deltas} ({nodes_with_deltas/node_count*100:.1f}%)\n"
        stats += f"Created: {mesh_tube.created_at}\n"
        stats += f"Last Modified: {mesh_tube.last_modified}\n"
        
        return stats 
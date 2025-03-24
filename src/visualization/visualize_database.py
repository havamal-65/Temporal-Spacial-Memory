#!/usr/bin/env python3
"""
Visualization script for the Temporal-Spatial Memory Database
"""

import os
import sys
import traceback
import time
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    from mpl_toolkits.mplot3d import Axes3D
except ImportError as e:
    print(f"Error importing visualization libraries: {e}")
    print("Please install required packages: pip install matplotlib numpy")
    sys.exit(1)

from src.models.mesh_tube import MeshTube
from src.visualization.interactive_visualizer import InteractiveVisualizer

def visualize_2d_slice(mesh, time, tolerance=0.1, save_path=None):
    """
    Create a 2D visualization of nodes at a specific time slice
    
    Args:
        mesh: MeshTube instance
        time: Time point to visualize
        tolerance: Time tolerance for selecting nodes
        save_path: Optional path to save the visualization
    """
    try:
        # Get nodes at this time slice
        nodes = mesh.get_temporal_slice(time, tolerance)
        
        if not nodes:
            print(f"No nodes found at time {time} (±{tolerance})")
            return
        
        # Create a plot
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Draw the nodes
        for node in nodes:
            # Convert polar coordinates to cartesian
            r = node.distance
            theta = np.radians(node.angle)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            
            # Draw the node
            circle = patches.Circle((x, y), radius=0.05, 
                                alpha=0.7, 
                                color='blue')
            ax.add_patch(circle)
            
            # Add node label
            topic = node.content.get('topic', f"Node {node.node_id}")
            ax.text(x, y + 0.07, topic, ha='center', va='center', fontsize=9)
        
        # Draw connections between nodes
        for node in nodes:
            # Convert polar coordinates to cartesian
            r1 = node.distance
            theta1 = np.radians(node.angle)
            x1 = r1 * np.cos(theta1)
            y1 = r1 * np.sin(theta1)
            
            # Get connected nodes from the node's connections attribute
            try:
                for connected_id in node.connections:
                    connected_node = mesh.get_node(connected_id)
                    if connected_node and abs(connected_node.time - time) <= tolerance:
                        r2 = connected_node.distance
                        theta2 = np.radians(connected_node.angle)
                        x2 = r2 * np.cos(theta2)
                        y2 = r2 * np.sin(theta2)
                        
                        # Draw connection line
                        ax.plot([x1, x2], [y1, y2], 'k-', alpha=0.3, linewidth=1)
            except Exception as e:
                print(f"Error drawing connections for node {node.node_id}: {e}")
                continue
        
        # Set plot properties
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add concentric circles to represent distance
        for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
            circle = patches.Circle((0, 0), radius=r, 
                                fill=False, 
                                edgecolor='gray', 
                                linestyle='--', 
                                alpha=0.5)
            ax.add_patch(circle)
        
        # Set title and labels
        ax.set_title(f'2D Slice at Time {time} (±{tolerance})')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to {save_path}")
        else:
            plt.show()
    except Exception as e:
        print(f"Error in 2D visualization at time {time}: {e}")
        traceback.print_exc()

def visualize_3d(mesh, start_time=None, end_time=None, save_path=None):
    """
    Create a 3D visualization of the entire mesh tube
    
    Args:
        mesh: MeshTube instance
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering
        save_path: Optional path to save the visualization
    """
    try:
        # Get all nodes
        nodes = list(mesh.nodes.values())
        print(f"Total nodes for 3D visualization: {len(nodes)}")
        
        # Filter by time if needed
        if start_time is not None:
            nodes = [n for n in nodes if n.time >= start_time]
        if end_time is not None:
            nodes = [n for n in nodes if n.time <= end_time]
        
        if not nodes:
            print("No nodes found in the specified time range")
            return
        
        # Create 3D plot
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot nodes
        for node in nodes:
            # Convert polar coordinates to cartesian
            r = node.distance
            theta = np.radians(node.angle)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = node.time
            
            # Plot the node
            ax.scatter(x, y, z, color='blue', alpha=0.7, s=30)
            
            # Add node label
            topic = node.content.get('topic', f"Node {node.node_id}")
            ax.text(x, y, z + 0.1, topic, fontsize=8)
        
        # Plot connections
        for node in nodes:
            try:
                # Convert polar coordinates to cartesian
                r1 = node.distance
                theta1 = np.radians(node.angle)
                x1 = r1 * np.cos(theta1)
                y1 = r1 * np.sin(theta1)
                z1 = node.time
                
                # Get connected nodes directly from the node's connections attribute
                for connected_id in node.connections:
                    connected_node = mesh.get_node(connected_id)
                    if connected_node and connected_node in nodes:
                        r2 = connected_node.distance
                        theta2 = np.radians(connected_node.angle)
                        x2 = r2 * np.cos(theta2)
                        y2 = r2 * np.sin(theta2)
                        z2 = connected_node.time
                        
                        # Draw connection line
                        ax.plot([x1, x2], [y1, y2], [z1, z2], 'k-', alpha=0.3, linewidth=1)
            except Exception as e:
                print(f"Error drawing 3D connections for node {node.node_id}: {e}")
                continue
        
        # Set labels and title
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Time')
        title = 'Temporal-Spatial Knowledge Database 3D Visualization'
        if start_time is not None and end_time is not None:
            title += f" (Time: {start_time} to {end_time})"
        ax.set_title(title)
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"3D visualization saved to {save_path}")
        else:
            plt.show()
    except Exception as e:
        print(f"Error in 3D visualization: {e}")
        traceback.print_exc()

def main():
    # Initialize database
    db_path = os.path.join('data', 'literature_memory.db')
    mesh_tube = MeshTube(name='literature_memory', storage_path=db_path)
    
    # Create visualizer
    visualizer = InteractiveVisualizer(mesh_tube)
    
    # Create output directory
    output_dir = 'visualizations'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate initial visualization
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'mesh_visualization_{timestamp}.html')
    visualizer.save_to_html(output_file)
    
    print(f"Visualization saved to: {output_file}")
    print("Open this file in a web browser to view the interactive visualization.")
    print("The visualization will update automatically when the database changes.")
    
    # Monitor database for changes
    last_modified = os.path.getmtime(db_path)
    
    try:
        while True:
            # Check if database has been modified
            current_modified = os.path.getmtime(db_path)
            if current_modified > last_modified:
                print("\nDatabase updated, regenerating visualization...")
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = os.path.join(output_dir, f'mesh_visualization_{timestamp}.html')
                visualizer.save_to_html(output_file)
                print(f"Updated visualization saved to: {output_file}")
                last_modified = current_modified
            
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        print("\nStopping visualization monitor...")

if __name__ == '__main__':
    main() 
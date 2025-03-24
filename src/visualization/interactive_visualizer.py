import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime

from ..models.mesh_tube import MeshTube
from ..models.node import Node

class InteractiveVisualizer:
    """
    Interactive 3D visualization of the Mesh Tube Knowledge Database using Plotly.
    Provides real-time updates and interactive exploration capabilities.
    """
    
    def __init__(self, mesh_tube: MeshTube):
        self.mesh_tube = mesh_tube
        self.fig = None
        self.last_update = None
        
    def create_visualization(self) -> go.Figure:
        """
        Create the initial 3D visualization of the mesh tube.
        
        Returns:
            Plotly figure object
        """
        # Create subplots: 3D view and timeline
        self.fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('3D Mesh Tube View', 'Timeline Distribution'),
            specs=[[{"type": "scatter3d"}], [{"type": "scatter"}]],
            row_heights=[0.7, 0.3]
        )
        
        # Get all nodes
        nodes = list(self.mesh_tube.nodes.values())
        if not nodes:
            return self.fig
            
        # Extract coordinates and properties
        times = [node.time for node in nodes]
        distances = [node.distance for node in nodes]
        angles = [node.angle for node in nodes]
        
        # Convert angles to radians for 3D plotting
        angles_rad = np.radians(angles)
        
        # Calculate 3D coordinates
        x = [d * np.cos(a) for d, a in zip(distances, angles_rad)]
        y = [d * np.sin(a) for d, a in zip(distances, angles_rad)]
        z = times
        
        # Create node traces
        self.fig.add_trace(
            go.Scatter3d(
                x=x, y=y, z=z,
                mode='markers',
                marker=dict(
                    size=8,
                    color=times,
                    colorscale='Viridis',
                    colorbar=dict(title='Time'),
                    opacity=0.8
                ),
                text=[f"Node: {node.node_id[:8]}...<br>Content: {str(node.content)[:50]}..." 
                      for node in nodes],
                hoverinfo='text',
                name='Nodes'
            ),
            row=1, col=1
        )
        
        # Add connections
        for node in nodes:
            for conn_id in node.connections:
                conn_node = self.mesh_tube.get_node(conn_id)
                if conn_node:
                    # Calculate connection coordinates
                    conn_angle_rad = np.radians(conn_node.angle)
                    conn_x = conn_node.distance * np.cos(conn_angle_rad)
                    conn_y = conn_node.distance * np.sin(conn_angle_rad)
                    conn_z = conn_node.time
                    
                    # Add connection line
                    self.fig.add_trace(
                        go.Scatter3d(
                            x=[node.distance * np.cos(angles_rad[nodes.index(node)]), conn_x],
                            y=[node.distance * np.sin(angles_rad[nodes.index(node)]), conn_y],
                            z=[node.time, conn_z],
                            mode='lines',
                            line=dict(color='gray', width=1),
                            opacity=0.3,
                            showlegend=False
                        ),
                        row=1, col=1
                    )
        
        # Add timeline distribution
        self.fig.add_trace(
            go.Scatter(
                x=times,
                y=[1] * len(times),
                mode='markers',
                marker=dict(size=8, color=times, colorscale='Viridis'),
                name='Timeline'
            ),
            row=2, col=1
        )
        
        # Update layout
        self.fig.update_layout(
            title='Mesh Tube Knowledge Database Visualization',
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Time',
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            showlegend=True,
            height=800
        )
        
        # Update timeline subplot
        self.fig.update_xaxes(title_text='Time', row=2, col=1)
        self.fig.update_yaxes(showticklabels=False, row=2, col=1)
        
        self.last_update = datetime.now()
        return self.fig
    
    def update_visualization(self) -> go.Figure:
        """
        Update the visualization with current database state.
        
        Returns:
            Updated Plotly figure object
        """
        if self.fig is None:
            return self.create_visualization()
            
        # Check if database has changed
        current_time = datetime.now()
        if self.last_update and (current_time - self.last_update).total_seconds() < 1:
            return self.fig
            
        # Recreate visualization with current state
        return self.create_visualization()
    
    def save_to_html(self, filepath: str) -> None:
        """
        Save the visualization to an HTML file.
        
        Args:
            filepath: Path to save the HTML file
        """
        if self.fig is None:
            self.create_visualization()
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the figure
        self.fig.write_html(filepath)
        
    def add_query_node(self, query_text: str, node_id: str) -> None:
        """
        Add a query node to the visualization.
        
        Args:
            query_text: The query text
            node_id: The ID of the query node
        """
        if self.fig is None:
            self.create_visualization()
            
        # Get query node
        query_node = self.mesh_tube.get_node(node_id)
        if not query_node:
            return
            
        # Add query node with special styling
        angle_rad = np.radians(query_node.angle)
        x = query_node.distance * np.cos(angle_rad)
        y = query_node.distance * np.sin(angle_rad)
        z = query_node.time
        
        self.fig.add_trace(
            go.Scatter3d(
                x=[x],
                y=[y],
                z=[z],
                mode='markers',
                marker=dict(
                    size=12,
                    color='red',
                    symbol='diamond'
                ),
                text=f"Query: {query_text}<br>Node: {node_id[:8]}...",
                hoverinfo='text',
                name='Query'
            ),
            row=1, col=1
        )
        
        # Update layout to show query
        self.fig.update_layout(
            title=f'Mesh Tube Knowledge Database Visualization - Query: {query_text[:30]}...'
        ) 
"""
Coordinate Visualizer for the Temporal-Spatial Memory System.

This module provides visualization tools for rendering nodes in the 4D 
polar-temporal coordinate space (r, theta, t, z) with various projection options.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import matplotlib.cm as cm
from typing import List, Dict, Any, Optional, Tuple, Union
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import logging

from src.data_models import PolarTemporalCoordinate
from src.models.narrative_atlas import Node, NarrativeAtlas

# Configure logging
logger = logging.getLogger("CoordinateVisualizer")


class CoordinateVisualizer:
    """
    Visualizes nodes in the 4D polar-temporal coordinate space.
    
    Provides multiple visualization options including:
    - 2D polar projection (r-theta view)
    - Temporal sequence view (t dimension)
    - 3D projections (r-theta-t or r-theta-z)
    - Interactive dashboards with filtering
    """
    
    def __init__(self, 
                 output_dir: str = "output/visualizations",
                 colormap: str = "viridis",
                 interactive: bool = True):
        """
        Initialize the coordinate visualizer.
        
        Args:
            output_dir: Directory to save visualization outputs
            colormap: Matplotlib/Plotly colormap to use
            interactive: Whether to use interactive (Plotly) or static (Matplotlib) visualizations
        """
        self.output_dir = output_dir
        self.colormap = colormap
        self.interactive = interactive
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Logging
        logger.info(f"Initialized CoordinateVisualizer with output_dir={output_dir}")
    
    def visualize_polar_projection(self, 
                                  nodes: List[Node],
                                  color_by: str = "t",
                                  size_by: Optional[str] = None,
                                  filter_func: Optional[callable] = None,
                                  title: str = "Polar Projection (r-θ)",
                                  show_labels: bool = False,
                                  filename: Optional[str] = None) -> Union[plt.Figure, go.Figure]:
        """
        Create a 2D polar projection (r-theta) visualization of nodes.
        
        Args:
            nodes: List of nodes to visualize
            color_by: Node attribute to use for coloring ('t', 'z', 'type', etc.)
            size_by: Node attribute to use for marker size (optional)
            filter_func: Function to filter nodes (takes a Node, returns bool)
            title: Plot title
            show_labels: Whether to show node labels
            filename: If provided, save visualization to this filename
            
        Returns:
            Matplotlib or Plotly figure object
        """
        # Filter nodes if a filter function is provided
        if filter_func:
            nodes = [node for node in nodes if filter_func(node)]
        
        if not nodes:
            logger.warning("No nodes to visualize after filtering.")
            return None
        
        # Extract coordinates and prepare data
        r_values = []
        theta_values = []
        t_values = []
        z_values = []
        labels = []
        types = []
        
        for node in nodes:
            if node.coordinates:
                r_values.append(node.coordinates.r)
                theta_values.append(node.coordinates.theta)
                t_values.append(node.coordinates.t)
                z_values.append(node.coordinates.z)
                labels.append(node.id)
                types.append(node.type)
        
        # Prepare data for visualization
        data = {
            'r': r_values,
            'theta': theta_values,
            't': t_values,
            'z': z_values,
            'type': types,
            'label': labels
        }
        
        # Create a DataFrame for easier handling
        df = pd.DataFrame(data)
        
        if self.interactive:
            # Interactive Plotly polar plot
            fig = go.Figure()
            
            # Determine color values
            color_values = df[color_by] if color_by in df.columns else df['t']
            
            # Determine size values (default to a constant)
            size_values = df[size_by] if size_by and size_by in df.columns else [10] * len(df)
            
            # Add scatter plot in polar coordinates
            fig.add_trace(go.Scatterpolar(
                r=df['r'],
                theta=df['theta'] * 180 / np.pi,  # Convert radians to degrees for Plotly
                mode='markers',
                marker=dict(
                    size=size_values,
                    color=color_values,
                    colorscale=self.colormap,
                    showscale=True,
                    colorbar=dict(title=color_by)
                ),
                text=df['label'],
                hoverinfo='text+r+theta',
                name='Nodes'
            ))
            
            # Update layout
            fig.update_layout(
                title=title,
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(df['r']) * 1.1]
                    ),
                    angularaxis=dict(
                        visible=True,
                        direction='clockwise'
                    )
                ),
                showlegend=True
            )
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                fig.write_html(output_path)
                logger.info(f"Saved interactive polar projection to {output_path}")
            
            return fig
            
        else:
            # Static Matplotlib polar plot
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': 'polar'})
            
            # Get values for coloring
            if color_by == 't':
                colors = df['t']
                cmap_label = 'Temporal Position (t)'
            elif color_by == 'z':
                colors = df['z']
                cmap_label = 'Z Coordinate'
            elif color_by == 'type':
                # For categorical coloring, use a categorical colormap
                type_categories = df['type'].unique()
                type_map = {t: i for i, t in enumerate(type_categories)}
                colors = [type_map[t] for t in df['type']]
                cmap_label = 'Node Type'
            else:
                colors = df['t']  # Default to temporal position
                cmap_label = 'Temporal Position (t)'
            
            # Create color normalization
            norm = Normalize(vmin=min(colors), vmax=max(colors))
            
            # Determine marker size
            if size_by:
                if size_by in df.columns:
                    sizes = df[size_by]
                    # Normalize sizes between 20 and 100
                    size_norm = Normalize(vmin=min(sizes), vmax=max(sizes))
                    sizes = [20 + 80 * size_norm(s) for s in sizes]
                else:
                    sizes = [30] * len(df)
            else:
                sizes = [30] * len(df)
            
            # Create scatter plot
            scatter = ax.scatter(df['theta'], df['r'], c=colors, s=sizes, 
                               cmap=self.colormap, alpha=0.7)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
            cbar.set_label(cmap_label)
            
            # Set plot properties
            ax.set_title(title)
            ax.set_theta_zero_location('N')  # 0 angle at the top
            ax.set_theta_direction(-1)  # Clockwise
            ax.set_rlabel_position(0)  # Move radial labels away from plot
            
            # Add node labels if requested
            if show_labels:
                for i, label in enumerate(df['label']):
                    ax.annotate(label, 
                               (df['theta'].iloc[i], df['r'].iloc[i]),
                               xytext=(5, 5), 
                               textcoords='offset points')
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved static polar projection to {output_path}")
            
            return fig
    
    def visualize_temporal_sequence(self,
                                   nodes: List[Node],
                                   color_by: str = "r",
                                   group_by: Optional[str] = "type",
                                   window_size: Optional[int] = None,
                                   title: str = "Temporal Sequence View",
                                   filename: Optional[str] = None) -> Union[plt.Figure, go.Figure]:
        """
        Create a temporal sequence visualization showing nodes along the t dimension.
        
        Args:
            nodes: List of nodes to visualize
            color_by: Node attribute to use for coloring
            group_by: Node attribute to use for grouping
            window_size: Size of the moving average window (for trend lines)
            title: Plot title
            filename: If provided, save visualization to this filename
            
        Returns:
            Matplotlib or Plotly figure object
        """
        # Prepare data
        t_values = []
        r_values = []
        theta_values = []
        z_values = []
        types = []
        labels = []
        
        for node in nodes:
            if node.coordinates:
                t_values.append(node.coordinates.t)
                r_values.append(node.coordinates.r)
                theta_values.append(node.coordinates.theta)
                z_values.append(node.coordinates.z)
                types.append(node.type)
                labels.append(node.id)
        
        # Create DataFrame
        df = pd.DataFrame({
            't': t_values,
            'r': r_values,
            'theta': theta_values,
            'z': z_values,
            'type': types,
            'label': labels
        })
        
        # Sort by temporal position
        df = df.sort_values('t')
        
        if self.interactive:
            # Interactive Plotly visualization
            
            # Determine color values
            color_values = df[color_by] if color_by in df.columns else df['r']
            
            if group_by and group_by in df.columns:
                # Create a grouped visualization
                fig = px.scatter(df, x='t', y='r', color=group_by, 
                               hover_data=['label', 'theta', 'z'],
                               title=title,
                               labels={
                                   't': 'Temporal Position (t)',
                                   'r': 'Radial Distance (r)',
                                   'theta': 'Angular Position (θ)',
                                   'z': 'Z Coordinate'
                               })
                
                # Add trend lines if window_size is specified
                if window_size and window_size > 0:
                    for group in df[group_by].unique():
                        group_df = df[df[group_by] == group]
                        if len(group_df) >= window_size:
                            # Calculate moving average
                            group_df = group_df.sort_values('t')
                            r_moving_avg = group_df['r'].rolling(window=window_size, center=True).mean()
                            
                            # Add trend line
                            fig.add_trace(go.Scatter(
                                x=group_df['t'],
                                y=r_moving_avg,
                                mode='lines',
                                line=dict(width=2, dash='dash'),
                                name=f'{group} Trend'
                            ))
            else:
                # Create a simple scatter plot
                fig = px.scatter(df, x='t', y='r', color=color_values,
                               hover_data=['label', 'type', 'theta', 'z'],
                               color_continuous_scale=self.colormap,
                               title=title,
                               labels={
                                   't': 'Temporal Position (t)',
                                   'r': 'Radial Distance (r)'
                               })
            
            # Update layout
            fig.update_layout(
                xaxis_title='Temporal Position (t)',
                yaxis_title='Radial Distance (r)',
                coloraxis_colorbar=dict(title=color_by)
            )
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                fig.write_html(output_path)
                logger.info(f"Saved interactive temporal sequence to {output_path}")
            
            return fig
            
        else:
            # Static Matplotlib visualization
            fig, ax = plt.subplots(figsize=(12, 6))
            
            if group_by and group_by in df.columns:
                # Group by the specified attribute
                groups = df[group_by].unique()
                cmap = plt.cm.get_cmap(self.colormap, len(groups))
                
                for i, group in enumerate(groups):
                    group_df = df[df[group_by] == group]
                    ax.scatter(group_df['t'], group_df['r'], 
                             color=cmap(i), alpha=0.7, label=group)
                    
                    # Add trend line if window_size is specified
                    if window_size and window_size > 0 and len(group_df) >= window_size:
                        group_df = group_df.sort_values('t')
                        r_moving_avg = group_df['r'].rolling(window=window_size, center=True).mean()
                        ax.plot(group_df['t'], r_moving_avg, '--', color=cmap(i), linewidth=2)
                
                ax.legend(title=group_by)
                
            else:
                # Color by the specified attribute
                if color_by in df.columns:
                    scatter = ax.scatter(df['t'], df['r'], c=df[color_by], 
                                      cmap=self.colormap, alpha=0.7)
                    cbar = plt.colorbar(scatter, ax=ax)
                    cbar.set_label(color_by)
                else:
                    ax.scatter(df['t'], df['r'], alpha=0.7)
            
            # Set plot properties
            ax.set_title(title)
            ax.set_xlabel('Temporal Position (t)')
            ax.set_ylabel('Radial Distance (r)')
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved static temporal sequence to {output_path}")
            
            return fig
    
    def visualize_3d_projection(self,
                              nodes: List[Node],
                              dimensions: str = "r-theta-t",
                              color_by: str = "type",
                              filter_func: Optional[callable] = None,
                              title: str = "3D Coordinate Projection",
                              filename: Optional[str] = None) -> go.Figure:
        """
        Create a 3D visualization of nodes with selected dimensions.
        
        Args:
            nodes: List of nodes to visualize
            dimensions: Which dimensions to visualize ('r-theta-t', 'r-theta-z', etc.)
            color_by: Node attribute to use for coloring
            filter_func: Function to filter nodes (takes a Node, returns bool)
            title: Plot title
            filename: If provided, save visualization to this filename
            
        Returns:
            Plotly figure object
        """
        # This visualization is only available in interactive mode
        if not self.interactive:
            logger.warning("3D projection is only available in interactive mode. Switching to interactive.")
        
        # Filter nodes if a filter function is provided
        if filter_func:
            nodes = [node for node in nodes if filter_func(node)]
        
        if not nodes:
            logger.warning("No nodes to visualize after filtering.")
            return None
        
        # Prepare data
        data = []
        for node in nodes:
            if node.coordinates:
                # For polar coordinates, convert to cartesian for 3D view
                x = node.coordinates.r * np.cos(node.coordinates.theta)
                y = node.coordinates.r * np.sin(node.coordinates.theta)
                
                entry = {
                    'id': node.id,
                    'type': node.type,
                    'r': node.coordinates.r,
                    'theta': node.coordinates.theta,
                    't': node.coordinates.t,
                    'z': node.coordinates.z,
                    'x': x,
                    'y': y
                }
                data.append(entry)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create 3D figure
        fig = go.Figure()
        
        # Parse dimensions to visualize
        dim_parts = dimensions.lower().split('-')
        
        # Map dimension names to actual column names
        dim_map = {
            'r': 'r',
            'theta': 'theta',
            't': 't',
            'z': 'z',
            'x': 'x',
            'y': 'y'
        }
        
        # Get the actual column names to use
        x_dim = dim_map.get(dim_parts[0], 'x')
        y_dim = dim_map.get(dim_parts[1], 'y')
        z_dim = dim_map.get(dim_parts[2], 't')
        
        # Prepare color values
        if color_by in df.columns:
            color_values = df[color_by]
            
            # If color_by is categorical (like 'type'), create discrete colors
            if df[color_by].dtype == 'object':
                categories = df[color_by].unique()
                color_discrete_map = {cat: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                                     for i, cat in enumerate(categories)}
                
                # Create a separate trace for each category for better legend
                for category in categories:
                    category_df = df[df[color_by] == category]
                    fig.add_trace(go.Scatter3d(
                        x=category_df[x_dim],
                        y=category_df[y_dim],
                        z=category_df[z_dim],
                        mode='markers',
                        marker=dict(
                            size=5,
                            color=color_discrete_map[category],
                            opacity=0.8
                        ),
                        text=category_df['id'],
                        hoverinfo='text',
                        name=category
                    ))
            else:
                # For continuous values, use a colorscale
                fig.add_trace(go.Scatter3d(
                    x=df[x_dim],
                    y=df[y_dim],
                    z=df[z_dim],
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=color_values,
                        colorscale=self.colormap,
                        opacity=0.8,
                        colorbar=dict(title=color_by)
                    ),
                    text=df['id'],
                    hoverinfo='text'
                ))
        else:
            # Default coloring
            fig.add_trace(go.Scatter3d(
                x=df[x_dim],
                y=df[y_dim],
                z=df[z_dim],
                mode='markers',
                marker=dict(
                    size=5,
                    color=df['t'],
                    colorscale=self.colormap,
                    opacity=0.8,
                    colorbar=dict(title='t')
                ),
                text=df['id'],
                hoverinfo='text'
            ))
        
        # Create axis labels based on the dimensions
        x_label = f"{dim_parts[0]} Coordinate"
        y_label = f"{dim_parts[1]} Coordinate"
        z_label = f"{dim_parts[2]} Coordinate"
        
        # Update layout
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title=x_label,
                yaxis_title=y_label,
                zaxis_title=z_label
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            legend=dict(
                x=0.01,
                y=0.99,
                traceorder="normal",
                bgcolor="rgba(255, 255, 255, 0.5)",
                bordercolor="rgba(0, 0, 0, 0.5)",
                borderwidth=1
            )
        )
        
        # Save if filename provided
        if filename:
            output_path = os.path.join(self.output_dir, filename)
            fig.write_html(output_path)
            logger.info(f"Saved 3D projection to {output_path}")
        
        return fig
    
    def create_relevance_heatmap(self,
                               nodes: List[Node],
                               dimensions: str = "theta-t",
                               z_value: str = "r",
                               bins: Tuple[int, int] = (20, 20),
                               title: str = "Relevance Heatmap",
                               filename: Optional[str] = None) -> Union[plt.Figure, go.Figure]:
        """
        Create a heatmap showing data density or relevance across dimensions.
        
        Args:
            nodes: List of nodes to visualize
            dimensions: Which dimensions to use for x and y ('theta-t', 'r-t', etc.)
            z_value: Which value to use for coloring the heatmap
            bins: Number of bins for each dimension
            title: Plot title
            filename: If provided, save visualization to this filename
            
        Returns:
            Matplotlib or Plotly figure object
        """
        # Prepare data
        data = []
        for node in nodes:
            if node.coordinates:
                entry = {
                    'id': node.id,
                    'type': node.type,
                    'r': node.coordinates.r,
                    'theta': node.coordinates.theta,
                    't': node.coordinates.t,
                    'z': node.coordinates.z
                }
                data.append(entry)
        
        df = pd.DataFrame(data)
        
        # Parse dimensions to visualize
        dim_parts = dimensions.lower().split('-')
        x_dim = dim_parts[0]
        y_dim = dim_parts[1]
        
        # Handle theta conversion if needed
        if x_dim == 'theta' or y_dim == 'theta':
            df['theta_degrees'] = df['theta'] * 180 / np.pi
        
        # Use degrees for theta if it's one of the dimensions
        x_values = df['theta_degrees'] if x_dim == 'theta' else df[x_dim]
        y_values = df['theta_degrees'] if y_dim == 'theta' else df[y_dim]
        z_values = df[z_value] if z_value in df.columns else df['r']
        
        if self.interactive:
            # Create interactive Plotly heatmap
            
            # Create 2D histogram
            fig = go.Figure()
            
            # Add heatmap
            heatmap = go.Histogram2d(
                x=x_values,
                y=y_values,
                z=z_values,
                colorscale=self.colormap,
                nbinsx=bins[0],
                nbinsy=bins[1],
                histfunc='avg',  # Use average of z values in each bin
                colorbar=dict(title=z_value)
            )
            
            fig.add_trace(heatmap)
            
            # Set x and y axis labels
            x_label = 'θ (degrees)' if x_dim == 'theta' else f'{x_dim} Coordinate'
            y_label = 'θ (degrees)' if y_dim == 'theta' else f'{y_dim} Coordinate'
            
            # Update layout
            fig.update_layout(
                title=title,
                xaxis_title=x_label,
                yaxis_title=y_label
            )
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                fig.write_html(output_path)
                logger.info(f"Saved interactive heatmap to {output_path}")
            
            return fig
            
        else:
            # Create static Matplotlib heatmap
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Create heatmap
            h = ax.hist2d(x_values, y_values, bins=bins, 
                        weights=z_values, 
                        cmap=self.colormap,
                        average='count')  # Average the z values in each bin
            
            # Add colorbar
            cbar = plt.colorbar(h[3], ax=ax)
            cbar.set_label(z_value)
            
            # Set x and y axis labels
            x_label = 'θ (degrees)' if x_dim == 'theta' else f'{x_dim} Coordinate'
            y_label = 'θ (degrees)' if y_dim == 'theta' else f'{y_dim} Coordinate'
            
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(title)
            
            # Save if filename provided
            if filename:
                output_path = os.path.join(self.output_dir, filename)
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved static heatmap to {output_path}")
            
            return fig
            
    def visualize_atlas(self, 
                       atlas: NarrativeAtlas,
                       view_type: str = "polar",
                       color_by: str = "type",
                       filter_func: Optional[callable] = None,
                       output_prefix: str = "atlas_viz") -> Dict[str, Any]:
        """
        Create a comprehensive visualization of a NarrativeAtlas.
        
        Args:
            atlas: NarrativeAtlas instance to visualize
            view_type: Type of visualization ('polar', 'temporal', '3d', 'heatmap', 'all')
            color_by: Node attribute to use for coloring
            filter_func: Function to filter nodes
            output_prefix: Prefix for output filenames
            
        Returns:
            Dictionary of generated visualizations
        """
        # Extract nodes from atlas
        nodes = list(atlas.db.nodes.values())
        
        if not nodes:
            logger.warning("No nodes found in the atlas.")
            return {}
        
        logger.info(f"Visualizing atlas with {len(nodes)} nodes, view_type={view_type}")
        
        # Create output dict
        visualizations = {}
        
        if view_type in ["polar", "all"]:
            # Create polar projection
            polar_fig = self.visualize_polar_projection(
                nodes=nodes,
                color_by=color_by,
                filter_func=filter_func,
                title="Polar Projection of Atlas Nodes",
                filename=f"{output_prefix}_polar.html" if self.interactive else f"{output_prefix}_polar.png"
            )
            visualizations["polar"] = polar_fig
        
        if view_type in ["temporal", "all"]:
            # Create temporal sequence visualization
            temporal_fig = self.visualize_temporal_sequence(
                nodes=nodes,
                color_by="r" if color_by == "type" else color_by,
                group_by="type" if color_by != "type" else None,
                window_size=5,
                title="Temporal Sequence of Atlas Nodes",
                filename=f"{output_prefix}_temporal.html" if self.interactive else f"{output_prefix}_temporal.png"
            )
            visualizations["temporal"] = temporal_fig
        
        if (view_type in ["3d", "all"]) and self.interactive:
            # Create 3D projection
            projection_3d = self.visualize_3d_projection(
                nodes=nodes,
                dimensions="r-theta-t",
                color_by=color_by,
                filter_func=filter_func,
                title="3D Projection of Atlas Nodes",
                filename=f"{output_prefix}_3d.html"
            )
            visualizations["3d"] = projection_3d
        
        if view_type in ["heatmap", "all"]:
            # Create relevance heatmap
            heatmap_fig = self.create_relevance_heatmap(
                nodes=nodes,
                dimensions="theta-t",
                z_value="r",
                title="Relevance Heatmap by Angular Position and Time",
                filename=f"{output_prefix}_heatmap.html" if self.interactive else f"{output_prefix}_heatmap.png"
            )
            visualizations["heatmap"] = heatmap_fig
        
        return visualizations 
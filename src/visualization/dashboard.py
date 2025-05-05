"""
Interactive Dashboard for Temporal-Spatial Memory System.

This module provides a web-based dashboard for visualizing and exploring
the 4D polar-temporal coordinate space interactively.
"""

import os
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import threading
import webbrowser
from urllib.parse import quote

from src.data_models import PolarTemporalCoordinate
from src.models.narrative_atlas import Node, NarrativeAtlas
from src.visualization.coordinate_visualizer import CoordinateVisualizer

# Configure logging
logger = logging.getLogger("Dashboard")


class Dashboard:
    """
    Interactive web dashboard for exploring the 4D polar-temporal coordinate space.
    
    Features:
    - Multiple coordinated views (polar, temporal sequence, 3D, heatmap)
    - Interactive filtering and querying
    - Entity relationship visualization
    - Data exploration tools
    """
    
    def __init__(self, 
                 narrative_atlas: NarrativeAtlas,
                 port: int = 8050,
                 debug: bool = False,
                 theme: str = "bootstrap"):
        """
        Initialize the dashboard.
        
        Args:
            narrative_atlas: The NarrativeAtlas instance to visualize
            port: Port to run the Dash server on
            debug: Whether to run Dash in debug mode
            theme: Dashboard theme (bootstrap, plotly, etc.)
        """
        self.narrative_atlas = narrative_atlas
        self.port = port
        self.debug = debug
        self.theme = theme
        
        # Create coordinate visualizer for generating plots
        self.visualizer = CoordinateVisualizer(interactive=True)
        
        # Extract nodes from atlas for visualization
        self.nodes = list(narrative_atlas.db.nodes.values())
        if not self.nodes:
            logger.warning("No nodes found in the atlas for visualization.")
        else:
            logger.info(f"Dashboard initialized with {len(self.nodes)} nodes.")
        
        # Prepare node data for dashboard
        self.prepare_data()
        
        # Create Dash app
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title="Temporal-Spatial Memory Dashboard"
        )
        
        # Set up the layout
        self.setup_layout()
        
        # Set up callbacks
        self.setup_callbacks()
    
    def prepare_data(self):
        """Prepare node data for dashboard visualization."""
        # Extract data from nodes
        data = []
        for node in self.nodes:
            if node.coordinates:
                # For polar coordinates, convert to cartesian for some visualizations
                x = node.coordinates.r * np.cos(node.coordinates.theta)
                y = node.coordinates.r * np.sin(node.coordinates.theta)
                
                # Extract text for display
                if isinstance(node.content, dict):
                    if 'text' in node.content:
                        text = node.content['text']
                    else:
                        # Fallback to string representation
                        text = str(node.content)
                else:
                    text = str(node.content)
                
                # Truncate text for display
                text_preview = text[:100] + "..." if len(text) > 100 else text
                
                entry = {
                    'id': node.id,
                    'type': node.type,
                    'r': node.coordinates.r,
                    'theta': node.coordinates.theta,
                    'theta_degrees': node.coordinates.theta * 180 / np.pi,
                    't': node.coordinates.t,
                    'z': node.coordinates.z,
                    'z_type': node.coordinates.z_type if hasattr(node.coordinates, 'z_type') else "",
                    'x': x,
                    'y': y,
                    'text_preview': text_preview,
                    'full_text': text
                }
                data.append(entry)
        
        # Create DataFrame
        self.df = pd.DataFrame(data)
        
        # Get unique values for filters
        self.node_types = self.df['type'].unique() if 'type' in self.df.columns else []
        self.z_types = self.df['z_type'].unique() if 'z_type' in self.df.columns else []
        
        # Calculate ranges for sliders
        self.r_range = [self.df['r'].min(), self.df['r'].max()] if not self.df.empty else [0, 1]
        self.theta_range = [0, 360]  # Use degrees for the UI
        self.t_range = [self.df['t'].min(), self.df['t'].max()] if not self.df.empty else [0, 10]
        self.z_range = [self.df['z'].min(), self.df['z'].max()] if not self.df.empty else [0, 1]
    
    def setup_layout(self):
        """Set up the Dash app layout."""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("Temporal-Spatial Memory Dashboard", className="display-4 text-center my-4"),
                    html.Hr()
                ], width=12)
            ]),
            
            # Controls and filters
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Filters & Controls"),
                        dbc.CardBody([
                            # Node Type Filter
                            html.Label("Node Types:"),
                            dcc.Dropdown(
                                id='node-type-filter',
                                options=[{'label': t, 'value': t} for t in self.node_types],
                                value=list(self.node_types),
                                multi=True
                            ),
                            html.Br(),
                            
                            # Z Type Filter
                            html.Label("Z Types:"),
                            dcc.Dropdown(
                                id='z-type-filter',
                                options=[{'label': t, 'value': t} for t in self.z_types],
                                value=list(self.z_types),
                                multi=True
                            ),
                            html.Br(),
                            
                            # Radius Range
                            html.Label("Radius (r) Range:"),
                            dcc.RangeSlider(
                                id='r-range-slider',
                                min=self.r_range[0],
                                max=self.r_range[1],
                                step=(self.r_range[1] - self.r_range[0]) / 100,
                                value=self.r_range,
                                marks={
                                    self.r_range[0]: {'label': f'{self.r_range[0]:.2f}'},
                                    self.r_range[1]: {'label': f'{self.r_range[1]:.2f}'}
                                }
                            ),
                            html.Br(),
                            
                            # Theta Range
                            html.Label("Angular (θ) Range (degrees):"),
                            dcc.RangeSlider(
                                id='theta-range-slider',
                                min=0,
                                max=360,
                                step=5,
                                value=[0, 360],
                                marks={
                                    0: {'label': '0°'},
                                    90: {'label': '90°'},
                                    180: {'label': '180°'},
                                    270: {'label': '270°'},
                                    360: {'label': '360°'}
                                }
                            ),
                            html.Br(),
                            
                            # Temporal Range
                            html.Label("Temporal (t) Range:"),
                            dcc.RangeSlider(
                                id='t-range-slider',
                                min=self.t_range[0],
                                max=self.t_range[1],
                                step=(self.t_range[1] - self.t_range[0]) / 100,
                                value=self.t_range,
                                marks={
                                    self.t_range[0]: {'label': f'{self.t_range[0]:.2f}'},
                                    self.t_range[1]: {'label': f'{self.t_range[1]:.2f}'}
                                }
                            ),
                            html.Br(),
                            
                            # Color By Selector
                            html.Label("Color By:"),
                            dcc.RadioItems(
                                id='color-by-selector',
                                options=[
                                    {'label': 'Node Type', 'value': 'type'},
                                    {'label': 'Temporal (t)', 'value': 't'},
                                    {'label': 'Radius (r)', 'value': 'r'},
                                    {'label': 'Angular (θ)', 'value': 'theta_degrees'},
                                    {'label': 'Z-coordinate (z)', 'value': 'z'}
                                ],
                                value='type',
                                labelStyle={'display': 'block'}
                            ),
                            html.Br(),
                            
                            # Query Input
                            html.Label("Search Query:"),
                            dbc.InputGroup([
                                dbc.Input(id='query-input', type='text', placeholder='Enter search query...'),
                                dbc.Button('Search', id='search-button', color='primary', className='ms-2')
                            ]),
                            html.Br(),
                            
                            # Visualization Options
                            html.Label("Display Options:"),
                            dbc.Checklist(
                                id='display-options',
                                options=[
                                    {'label': 'Show Labels', 'value': 'show_labels'},
                                    {'label': 'Show Grid', 'value': 'show_grid'},
                                    {'label': 'Show Trend Lines', 'value': 'show_trends'}
                                ],
                                value=['show_grid']
                            )
                        ])
                    ]),
                    html.Br(),
                    # Legend and Info Card
                    dbc.Card([
                        dbc.CardHeader("Information"),
                        dbc.CardBody([
                            html.Div(id='selection-info', children="Click on a node to see details.")
                        ])
                    ])
                ], width=3),
                
                # Visualization panes
                dbc.Col([
                    # Tabs for different visualizations
                    dbc.Tabs([
                        # Polar View
                        dbc.Tab([
                            dcc.Graph(
                                id='polar-view',
                                figure=go.Figure(),
                                style={'height': '70vh'}
                            )
                        ], label="Polar View"),
                        
                        # Temporal View
                        dbc.Tab([
                            dcc.Graph(
                                id='temporal-view',
                                figure=go.Figure(),
                                style={'height': '70vh'}
                            )
                        ], label="Temporal View"),
                        
                        # 3D View
                        dbc.Tab([
                            dcc.Graph(
                                id='3d-view',
                                figure=go.Figure(),
                                style={'height': '70vh'}
                            )
                        ], label="3D View"),
                        
                        # Heatmap View
                        dbc.Tab([
                            dcc.Graph(
                                id='heatmap-view',
                                figure=go.Figure(),
                                style={'height': '70vh'}
                            )
                        ], label="Heatmap"),
                        
                        # Entity Relationships
                        dbc.Tab([
                            dcc.Graph(
                                id='relationship-view',
                                figure=go.Figure(),
                                style={'height': '70vh'}
                            )
                        ], label="Entity Relationships")
                    ]),
                    
                    # Selected Node Details
                    dbc.Card([
                        dbc.CardHeader("Selected Node Details"),
                        dbc.CardBody([
                            html.Div(id='node-details', children="Click on a node to view details.")
                        ])
                    ])
                ], width=9)
            ]),
            
            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    html.P("Temporal-Spatial Memory System Dashboard", className="text-center text-muted")
                ], width=12)
            ])
        ], fluid=True)
    
    def setup_callbacks(self):
        """Set up Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output('polar-view', 'figure'),
             Output('temporal-view', 'figure'),
             Output('3d-view', 'figure'),
             Output('heatmap-view', 'figure'),
             Output('relationship-view', 'figure')],
            [Input('node-type-filter', 'value'),
             Input('z-type-filter', 'value'),
             Input('r-range-slider', 'value'),
             Input('theta-range-slider', 'value'),
             Input('t-range-slider', 'value'),
             Input('color-by-selector', 'value'),
             Input('display-options', 'value'),
             Input('search-button', 'n_clicks')],
            [State('query-input', 'value')]
        )
        def update_visualizations(node_types, z_types, r_range, theta_range, t_range, 
                                 color_by, display_options, search_clicks, query):
            """Update all visualizations based on filter settings."""
            # Start with all data
            filtered_df = self.df.copy()
            
            # Apply filters
            if node_types:
                filtered_df = filtered_df[filtered_df['type'].isin(node_types)]
            
            if z_types:
                filtered_df = filtered_df[filtered_df['z_type'].isin(z_types)]
            
            # Apply range filters
            filtered_df = filtered_df[
                (filtered_df['r'] >= r_range[0]) & 
                (filtered_df['r'] <= r_range[1]) &
                (filtered_df['t'] >= t_range[0]) & 
                (filtered_df['t'] <= t_range[1])
            ]
            
            # Apply theta filter (in degrees, handling wrap-around)
            if theta_range[0] < theta_range[1]:
                # Normal range
                filtered_df = filtered_df[
                    (filtered_df['theta_degrees'] >= theta_range[0]) & 
                    (filtered_df['theta_degrees'] <= theta_range[1])
                ]
            else:
                # Wrapping around 360
                filtered_df = filtered_df[
                    (filtered_df['theta_degrees'] >= theta_range[0]) | 
                    (filtered_df['theta_degrees'] <= theta_range[1])
                ]
            
            # Apply search query if provided and button is clicked
            ctx = callback_context
            if ctx.triggered and 'search-button' in ctx.triggered[0]['prop_id'] and query:
                # In a real implementation, this would integrate with the narrative atlas query
                # For now, we'll just do a simple text search on the previews
                filtered_df = filtered_df[filtered_df['text_preview'].str.contains(query, case=False, na=False)]
            
            # Check if we have any data left after filtering
            if filtered_df.empty:
                empty_fig = go.Figure().update_layout(
                    title="No data matches the current filters",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                )
                return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
            
            # Display options
            show_labels = 'show_labels' in display_options
            show_grid = 'show_grid' in display_options
            show_trends = 'show_trends' in display_options
            
            # Create polar view
            polar_fig = go.Figure()
            
            # Add scatter polar plot
            polar_fig.add_trace(go.Scatterpolar(
                r=filtered_df['r'],
                theta=filtered_df['theta_degrees'],  # Use degrees for polar plot
                mode='markers+text' if show_labels else 'markers',
                text=filtered_df['id'] if show_labels else None,
                textposition="top center" if show_labels else None,
                marker=dict(
                    size=10,
                    color=filtered_df[color_by],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title=color_by)
                ),
                hoverinfo='text',
                hovertext=filtered_df['text_preview'],
                name='Nodes'
            ))
            
            # Update polar layout
            polar_fig.update_layout(
                title="Polar Projection (r-θ)",
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, filtered_df['r'].max() * 1.1]
                    ),
                    angularaxis=dict(
                        visible=True,
                        direction='clockwise'
                    )
                ),
                showlegend=False
            )
            
            # Create temporal view
            temporal_fig = px.scatter(
                filtered_df,
                x='t',
                y='r',
                color=color_by,
                hover_data=['id', 'type', 'theta_degrees', 'z', 'text_preview'],
                title="Temporal Sequence View"
            )
            
            # Add trend lines if enabled
            if show_trends and len(filtered_df) > 5:
                # Group by type for trend lines
                for node_type in filtered_df['type'].unique():
                    type_df = filtered_df[filtered_df['type'] == node_type]
                    if len(type_df) >= 5:  # Need at least a few points for meaningful trend
                        type_df = type_df.sort_values('t')
                        # Calculate moving average
                        window_size = min(5, len(type_df))
                        r_moving_avg = type_df['r'].rolling(window=window_size, center=True).mean()
                        
                        # Add trend line
                        temporal_fig.add_trace(go.Scatter(
                            x=type_df['t'],
                            y=r_moving_avg,
                            mode='lines',
                            line=dict(width=2, dash='dash'),
                            name=f'{node_type} Trend'
                        ))
            
            # Update temporal layout
            temporal_fig.update_layout(
                xaxis_title="Temporal Position (t)",
                yaxis_title="Radius (r)",
                xaxis=dict(showgrid=show_grid),
                yaxis=dict(showgrid=show_grid)
            )
            
            # Create 3D view
            # Convert polar to cartesian for 3D visualization
            filtered_df['x_cart'] = filtered_df['r'] * np.cos(filtered_df['theta'])
            filtered_df['y_cart'] = filtered_df['r'] * np.sin(filtered_df['theta'])
            
            # Create 3D scatter plot
            threed_fig = go.Figure()
            
            # If color_by is categorical, create separate traces for better legend
            if color_by == 'type' or color_by == 'z_type':
                for category in filtered_df[color_by].unique():
                    cat_df = filtered_df[filtered_df[color_by] == category]
                    threed_fig.add_trace(go.Scatter3d(
                        x=cat_df['x_cart'],
                        y=cat_df['y_cart'],
                        z=cat_df['t'],
                        mode='markers+text' if show_labels else 'markers',
                        text=cat_df['id'] if show_labels else None,
                        marker=dict(
                            size=5,
                            opacity=0.8
                        ),
                        hovertext=cat_df['text_preview'],
                        name=category
                    ))
            else:
                # Continuous color scale
                threed_fig.add_trace(go.Scatter3d(
                    x=filtered_df['x_cart'],
                    y=filtered_df['y_cart'],
                    z=filtered_df['t'],
                    mode='markers+text' if show_labels else 'markers',
                    text=filtered_df['id'] if show_labels else None,
                    marker=dict(
                        size=5,
                        color=filtered_df[color_by],
                        colorscale='Viridis',
                        opacity=0.8,
                        colorbar=dict(title=color_by)
                    ),
                    hovertext=filtered_df['text_preview']
                ))
            
            # Update 3D layout
            threed_fig.update_layout(
                title="3D View (x-y-t)",
                scene=dict(
                    xaxis_title="X (r·cos(θ))",
                    yaxis_title="Y (r·sin(θ))",
                    zaxis_title="Temporal Position (t)",
                    xaxis=dict(showgrid=show_grid),
                    yaxis=dict(showgrid=show_grid),
                    zaxis=dict(showgrid=show_grid)
                )
            )
            
            # Create heatmap view
            heatmap_fig = go.Figure()
            
            # Create 2D histogram
            heatmap = go.Histogram2d(
                x=filtered_df['theta_degrees'],
                y=filtered_df['t'],
                z=filtered_df['r'],
                colorscale='Viridis',
                nbinsx=20,
                nbinsy=20,
                histfunc='avg',  # Use average of r values in each bin
                colorbar=dict(title='Average r')
            )
            
            heatmap_fig.add_trace(heatmap)
            
            # Update heatmap layout
            heatmap_fig.update_layout(
                title="Relevance Heatmap (θ-t)",
                xaxis_title="Angular Position (θ) in degrees",
                yaxis_title="Temporal Position (t)"
            )
            
            # Create entity relationship view
            # For demonstration, we'll create a network graph based on temporal proximity
            relationship_fig = go.Figure()
            
            # Sort by temporal position for edge creation
            filtered_df = filtered_df.sort_values('t')
            
            # Create network nodes
            relationship_fig.add_trace(go.Scatter(
                x=filtered_df['x_cart'],
                y=filtered_df['y_cart'],
                mode='markers+text' if show_labels else 'markers',
                text=filtered_df['id'] if show_labels else None,
                marker=dict(
                    size=10,
                    color=filtered_df[color_by],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title=color_by)
                ),
                hovertext=filtered_df['text_preview'],
                name='Nodes'
            ))
            
            # Create edges between temporally adjacent nodes
            # (would be more sophisticated in a real implementation)
            for i in range(len(filtered_df) - 1):
                # Only connect nodes that are temporally close
                if abs(filtered_df.iloc[i+1]['t'] - filtered_df.iloc[i]['t']) < (t_range[1] - t_range[0]) / 10:
                    relationship_fig.add_trace(go.Scatter(
                        x=[filtered_df.iloc[i]['x_cart'], filtered_df.iloc[i+1]['x_cart']],
                        y=[filtered_df.iloc[i]['y_cart'], filtered_df.iloc[i+1]['y_cart']],
                        mode='lines',
                        line=dict(width=1, color='rgba(150,150,150,0.5)'),
                        showlegend=False
                    ))
            
            # Update relationship layout
            relationship_fig.update_layout(
                title="Entity Relationships",
                xaxis_title="X Position",
                yaxis_title="Y Position",
                xaxis=dict(showgrid=show_grid),
                yaxis=dict(showgrid=show_grid)
            )
            
            return polar_fig, temporal_fig, threed_fig, heatmap_fig, relationship_fig
        
        # Callback for node selection
        @self.app.callback(
            [Output('node-details', 'children'),
             Output('selection-info', 'children')],
            [Input('polar-view', 'clickData'),
             Input('temporal-view', 'clickData'),
             Input('3d-view', 'clickData'),
             Input('relationship-view', 'clickData')]
        )
        def display_node_details(polar_click, temporal_click, threed_click, relationship_click):
            """Display detailed information about the selected node."""
            ctx = callback_context
            if not ctx.triggered:
                return "Click on a node to view details.", "No node selected."
            
            # Determine which graph was clicked
            click_source = ctx.triggered[0]['prop_id'].split('.')[0]
            click_data = None
            
            if click_source == 'polar-view' and polar_click:
                click_data = polar_click
            elif click_source == 'temporal-view' and temporal_click:
                click_data = temporal_click
            elif click_source == '3d-view' and threed_click:
                click_data = threed_click
            elif click_source == 'relationship-view' and relationship_click:
                click_data = relationship_click
            
            if not click_data:
                return "Click on a node to view details.", "No node selected."
            
            # Extract the clicked point information
            point_index = click_data['points'][0]['pointIndex']
            
            # Access the corresponding row in the filtered dataframe
            # This is a simplification - in a real implementation, we would need to
            # track the filtered data more carefully
            try:
                if click_source == 'polar-view':
                    # For polar view, we need to match r and theta
                    r = click_data['points'][0]['r']
                    theta = click_data['points'][0]['theta']
                    selected_node = self.df[(self.df['r'].round(3) == round(r, 3)) & 
                                          (self.df['theta_degrees'].round(1) == round(theta, 1))].iloc[0]
                elif click_source == 'temporal-view':
                    # For temporal view, match t and r
                    t = click_data['points'][0]['x']
                    r = click_data['points'][0]['y']
                    selected_node = self.df[(self.df['t'].round(3) == round(t, 3)) & 
                                          (self.df['r'].round(3) == round(r, 3))].iloc[0]
                elif click_source == '3d-view':
                    # For 3D view, this gets more complex - we'll use the point index as an approximation
                    # In a real implementation, we would need better tracking of the filtered data
                    selected_node = self.df.iloc[point_index]
                else:
                    # For relationship view (network graph)
                    x = click_data['points'][0]['x']
                    y = click_data['points'][0]['y']
                    selected_node = self.df[(self.df['x'].round(3) == round(x, 3)) & 
                                          (self.df['y'].round(3) == round(y, 3))].iloc[0]
            except (IndexError, KeyError):
                return "Unable to identify the selected node.", "Selection error."
            
            # Format node details
            node_id = selected_node['id']
            node_type = selected_node['type']
            coordinates = f"r: {selected_node['r']:.3f}, θ: {selected_node['theta_degrees']:.1f}°, t: {selected_node['t']:.3f}, z: {selected_node['z']:.3f}"
            
            detail_components = [
                html.H5(f"Node ID: {node_id}"),
                html.P(f"Type: {node_type}"),
                html.P(f"Coordinates: {coordinates}"),
                html.P(f"Z-Type: {selected_node['z_type']}"),
                html.Hr(),
                html.H6("Content:"),
                html.Div(selected_node['full_text'], style={'max-height': '200px', 'overflow-y': 'auto'})
            ]
            
            # Create summary for info panel
            info_components = [
                html.H5(f"Selected: {node_id}"),
                html.P(f"Type: {node_type}"),
                html.P(f"Coordinates: {coordinates}")
            ]
            
            return html.Div(detail_components), html.Div(info_components)
    
    def run(self, open_browser: bool = True):
        """Run the dashboard server."""
        if not self.nodes:
            logger.warning("Running dashboard with no data.")
        
        if open_browser:
            # Open browser in a separate thread
            port = self.port
            def open_browser_tab():
                webbrowser.open_new(f"http://localhost:{port}")
            
            threading.Timer(1.0, open_browser_tab).start()
        
        # Run the server
        self.app.run_server(debug=self.debug, port=self.port)
        
    def generate_static_report(self, output_path: str = "output/dashboard_report.html"):
        """Generate a static HTML report with all visualizations."""
        # Create visualizations
        visualization_results = self.visualizer.visualize_atlas(
            atlas=self.narrative_atlas,
            view_type="all",
            color_by="type"
        )
        
        # Combine into a report
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<title>Temporal-Spatial Memory Visualization Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1, h2 { color: #2c3e50; }",
            ".viz-container { margin: 20px 0; padding: 10px; border: 1px solid #eee; }",
            "</style>",
            "</head><body>",
            "<h1>Temporal-Spatial Memory Visualization Report</h1>",
            f"<p>Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p>Nodes in atlas: {len(self.nodes)}</p>"
        ]
        
        # Add each visualization as an iframe
        for viz_name, fig in visualization_results.items():
            # Save each figure to a temporary HTML file
            if viz_name != "3d" or fig is not None:
                temp_file = f"output/temp_{viz_name}.html"
                os.makedirs(os.path.dirname(temp_file), exist_ok=True)
                
                if isinstance(fig, go.Figure):
                    fig.write_html(temp_file)
                    html_parts.append(f"<div class='viz-container'>")
                    html_parts.append(f"<h2>{viz_name.title()} Visualization</h2>")
                    html_parts.append(f"<iframe src='{quote(os.path.basename(temp_file))}' width='100%' height='600px' frameborder='0'></iframe>")
                    html_parts.append("</div>")
        
        # Close the HTML
        html_parts.append("</body></html>")
        
        # Write the complete report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write("\n".join(html_parts))
        
        logger.info(f"Static report generated at {output_path}")
        return output_path 
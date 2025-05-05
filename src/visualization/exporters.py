"""
Exporters for the Temporal-Spatial Memory System.

This module provides exporters to convert the coordinate data into formats
compatible with external visualization tools and network analysis software.
"""

import os
import json
import pandas as pd
import numpy as np
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from datetime import datetime
import csv
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from src.data_models import PolarTemporalCoordinate
from src.models.narrative_atlas import Node, NarrativeAtlas

# Configure logging
logger = logging.getLogger("Exporters")


class NetworkExporter:
    """
    Exports node and relationship data for network visualization tools.
    
    Supported formats:
    - NetworkX for Python analysis
    - Gephi (GEXF/GraphML)
    - Cytoscape (JSON)
    - D3.js (JSON)
    """
    
    def __init__(self, 
                 output_dir: str = "output/network_exports",
                 similarity_threshold: float = 0.5,
                 temporal_link_threshold: float = 0.2):
        """
        Initialize the network exporter.
        
        Args:
            output_dir: Directory to save exports
            similarity_threshold: Minimum similarity to create an edge (0-1)
            temporal_link_threshold: Maximum temporal distance to create a link (as fraction of total time span)
        """
        self.output_dir = output_dir
        self.similarity_threshold = similarity_threshold
        self.temporal_link_threshold = temporal_link_threshold
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def prepare_network(self, 
                       nodes: List[Node], 
                       link_type: str = "similarity",
                       include_attributes: bool = True,
                       weighted_edges: bool = True) -> nx.Graph:
        """
        Prepare a NetworkX graph from node data.
        
        Args:
            nodes: List of nodes
            link_type: Type of links to create ('similarity', 'temporal', 'combined')
            include_attributes: Whether to include node attributes in the graph
            weighted_edges: Whether to include edge weights
            
        Returns:
            NetworkX graph
        """
        if not nodes:
            logger.warning("No nodes provided for network export.")
            return nx.Graph()
        
        # Create a new graph
        G = nx.Graph()
        
        # Add nodes with coordinates and attributes
        for node in nodes:
            if node.coordinates:
                # Create attributes dict
                attrs = {
                    'id': node.id,
                    'type': node.type,
                    'r': float(node.coordinates.r),
                    'theta': float(node.coordinates.theta),
                    'theta_degrees': float(node.coordinates.theta * 180 / np.pi),
                    't': float(node.coordinates.t),
                    'z': float(node.coordinates.z),
                    'x': float(node.coordinates.r * np.cos(node.coordinates.theta)),
                    'y': float(node.coordinates.r * np.sin(node.coordinates.theta))
                }
                
                # Add z_type if available
                if hasattr(node.coordinates, 'z_type'):
                    attrs['z_type'] = node.coordinates.z_type
                
                # Include additional attributes if requested
                if include_attributes and node.metadata:
                    for key, value in node.metadata.items():
                        # Ensure attribute names don't conflict with existing ones
                        attr_key = f"meta_{key}" if key in attrs else key
                        # Only include serializable attributes
                        if isinstance(value, (str, int, float, bool, type(None))):
                            attrs[attr_key] = value
                
                # Add node to graph
                G.add_node(node.id, **attrs)
        
        # Skip edge creation if there's only one node
        if len(G.nodes) <= 1:
            return G
        
        # Create edges based on the specified link type
        if link_type == "similarity" or link_type == "combined":
            # Create edges based on coordinate similarity
            for i, node1 in enumerate(nodes):
                for node2 in nodes[i+1:]:
                    if node1.coordinates and node2.coordinates:
                        # Calculate similarity score (Euclidean distance in 4D space)
                        v1 = np.array([
                            node1.coordinates.r * np.cos(node1.coordinates.theta),
                            node1.coordinates.r * np.sin(node1.coordinates.theta),
                            node1.coordinates.t,
                            node1.coordinates.z
                        ])
                        
                        v2 = np.array([
                            node2.coordinates.r * np.cos(node2.coordinates.theta),
                            node2.coordinates.r * np.sin(node2.coordinates.theta),
                            node2.coordinates.t,
                            node2.coordinates.z
                        ])
                        
                        # Calculate Euclidean distance
                        distance = np.linalg.norm(v1 - v2)
                        
                        # Convert distance to similarity (0-1 scale)
                        similarity = 1 / (1 + distance)
                        
                        # Add edge if similarity is above threshold
                        if similarity >= self.similarity_threshold:
                            if weighted_edges:
                                G.add_edge(node1.id, node2.id, weight=similarity, type="similarity")
                            else:
                                G.add_edge(node1.id, node2.id, type="similarity")
        
        if link_type == "temporal" or link_type == "combined":
            # Get temporal range
            temporal_coords = [n.coordinates.t for n in nodes if n.coordinates]
            t_min, t_max = min(temporal_coords), max(temporal_coords)
            t_range = t_max - t_min
            
            # Create edges based on temporal proximity
            nodes_by_t = sorted([(n.id, n.coordinates.t) for n in nodes if n.coordinates], key=lambda x: x[1])
            
            for i in range(len(nodes_by_t) - 1):
                id1, t1 = nodes_by_t[i]
                id2, t2 = nodes_by_t[i+1]
                
                # Calculate temporal distance as a fraction of the total range
                t_distance = (t2 - t1) / t_range if t_range > 0 else 0
                
                # Add edge if temporal distance is below threshold
                if t_distance <= self.temporal_link_threshold:
                    if weighted_edges:
                        # Higher weight for closer temporal connection
                        weight = 1 - (t_distance / self.temporal_link_threshold)
                        G.add_edge(id1, id2, weight=weight, type="temporal")
                    else:
                        G.add_edge(id1, id2, type="temporal")
        
        logger.info(f"Created network with {len(G.nodes)} nodes and {len(G.edges)} edges.")
        return G
    
    def export_to_gephi(self, 
                       G: nx.Graph, 
                       filename: str = "network_export.gexf",
                       include_viz: bool = True) -> str:
        """
        Export network to Gephi GEXF format.
        
        Args:
            G: NetworkX graph
            filename: Output filename
            include_viz: Whether to include visualization attributes
            
        Returns:
            Path to the exported file
        """
        if len(G.nodes) == 0:
            logger.warning("Empty graph, not exporting to Gephi.")
            return ""
        
        # Add visualization attributes if requested
        if include_viz:
            for node_id, attrs in G.nodes(data=True):
                # Set position based on x, y coordinates
                if 'x' in attrs and 'y' in attrs:
                    G.nodes[node_id]['viz'] = {
                        'position': {
                            'x': float(attrs['x']) * 100,
                            'y': float(attrs['y']) * 100,
                            'z': 0.0
                        }
                    }
                
                # Set color based on node type
                if 'type' in attrs:
                    # Simple hash function to get consistent colors for types
                    type_hash = hash(attrs['type']) % 360
                    rgb = tuple(int(x*255) for x in plt.cm.hsv(type_hash/360))
                    
                    G.nodes[node_id]['viz']['color'] = {
                        'r': rgb[0],
                        'g': rgb[1],
                        'b': rgb[2],
                        'a': 1.0
                    }
                
                # Set size based on radial position (more central = larger)
                if 'r' in attrs:
                    # Invert r since smaller r is more central
                    size = 5 + 20 * (1 - attrs['r'])
                    G.nodes[node_id]['viz']['size'] = size
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save to GEXF
        output_path = os.path.join(self.output_dir, filename)
        nx.write_gexf(G, output_path)
        
        logger.info(f"Exported network to Gephi format: {output_path}")
        return output_path
    
    def export_to_cytoscape(self, 
                          G: nx.Graph, 
                          filename: str = "network_export.json") -> str:
        """
        Export network to Cytoscape JSON format.
        
        Args:
            G: NetworkX graph
            filename: Output filename
            
        Returns:
            Path to the exported file
        """
        if len(G.nodes) == 0:
            logger.warning("Empty graph, not exporting to Cytoscape.")
            return ""
        
        # Convert NetworkX graph to Cytoscape JSON format
        cy_data = {
            'data': {'name': 'Temporal-Spatial Memory Network'},
            'elements': {
                'nodes': [],
                'edges': []
            }
        }
        
        # Add nodes
        for node_id, attrs in G.nodes(data=True):
            cy_node = {
                'data': {
                    'id': str(node_id),
                    'label': str(node_id)
                }
            }
            
            # Add node attributes
            for key, value in attrs.items():
                cy_node['data'][key] = value
            
            # Add position
            if 'x' in attrs and 'y' in attrs:
                cy_node['position'] = {
                    'x': float(attrs['x']) * 100,
                    'y': float(attrs['y']) * 100
                }
            
            cy_data['elements']['nodes'].append(cy_node)
        
        # Add edges
        for i, (source, target, attrs) in enumerate(G.edges(data=True)):
            edge_id = f"e{i}"
            cy_edge = {
                'data': {
                    'id': edge_id,
                    'source': str(source),
                    'target': str(target)
                }
            }
            
            # Add edge attributes
            for key, value in attrs.items():
                cy_edge['data'][key] = value
            
            cy_data['elements']['edges'].append(cy_edge)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save to JSON
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            json.dump(cy_data, f, indent=2)
        
        logger.info(f"Exported network to Cytoscape format: {output_path}")
        return output_path
    
    def export_to_d3(self,
                   G: nx.Graph,
                   filename: str = "network_export_d3.json") -> str:
        """
        Export network to D3.js JSON format.
        
        Args:
            G: NetworkX graph
            filename: Output filename
            
        Returns:
            Path to the exported file
        """
        if len(G.nodes) == 0:
            logger.warning("Empty graph, not exporting to D3.js.")
            return ""
        
        # Convert NetworkX graph to D3.js compatible format
        d3_data = {
            'nodes': [],
            'links': []
        }
        
        # Create a node mapping for link references
        node_map = {}
        
        # Add nodes
        for i, (node_id, attrs) in enumerate(G.nodes(data=True)):
            # Store index for creating links
            node_map[node_id] = i
            
            # Create node object
            node_obj = {
                'id': str(node_id),
                'group': attrs.get('type', 'default')
            }
            
            # Add coordinates if available
            if 'x' in attrs and 'y' in attrs:
                node_obj['x'] = float(attrs['x'])
                node_obj['y'] = float(attrs['y'])
            
            # Add temporal position if available
            if 't' in attrs:
                node_obj['t'] = float(attrs['t'])
            
            # Add radius position (for forcing layout)
            if 'r' in attrs:
                node_obj['r'] = float(attrs['r'])
            
            d3_data['nodes'].append(node_obj)
        
        # Add links
        for source, target, attrs in G.edges(data=True):
            link_obj = {
                'source': node_map[source],
                'target': node_map[target],
                'type': attrs.get('type', 'default')
            }
            
            # Add weight if available
            if 'weight' in attrs:
                link_obj['value'] = float(attrs['weight'])
            
            d3_data['links'].append(link_obj)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save to JSON
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            json.dump(d3_data, f, indent=2)
        
        logger.info(f"Exported network to D3.js format: {output_path}")
        return output_path
    
    def export_atlas_network(self,
                           atlas: NarrativeAtlas,
                           formats: List[str] = ["gephi", "cytoscape", "d3"],
                           link_type: str = "combined") -> Dict[str, str]:
        """
        Export a NarrativeAtlas to network formats.
        
        Args:
            atlas: NarrativeAtlas instance
            formats: List of export formats
            link_type: Type of links to create
            
        Returns:
            Dictionary of format -> file path
        """
        # Extract nodes from atlas
        nodes = list(atlas.db.nodes.values())
        
        if not nodes:
            logger.warning("No nodes found in atlas for network export.")
            return {}
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare network
        G = self.prepare_network(nodes, link_type=link_type)
        
        # Export in each requested format
        exports = {}
        
        if "gephi" in formats:
            gephi_path = self.export_to_gephi(
                G, 
                filename=f"atlas_network_{timestamp}.gexf"
            )
            exports["gephi"] = gephi_path
        
        if "cytoscape" in formats:
            cytoscape_path = self.export_to_cytoscape(
                G, 
                filename=f"atlas_network_{timestamp}.json"
            )
            exports["cytoscape"] = cytoscape_path
        
        if "d3" in formats:
            d3_path = self.export_to_d3(
                G, 
                filename=f"atlas_network_{timestamp}_d3.json"
            )
            exports["d3"] = d3_path
        
        logger.info(f"Exported atlas network in {len(exports)} formats.")
        return exports


class HeatmapExporter:
    """
    Exports heatmap data for external visualization tools.
    
    Features:
    - 2D heatmaps of data density across different dimensions
    - Relevance heatmaps (r value distribution)
    - Temporal pattern visualization
    """
    
    def __init__(self, output_dir: str = "output/heatmap_exports"):
        """
        Initialize the heatmap exporter.
        
        Args:
            output_dir: Directory to save exports
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def prepare_heatmap_data(self, 
                          nodes: List[Node],
                          dimensions: Tuple[str, str] = ("theta", "t"),
                          value_field: str = "r",
                          bins: Tuple[int, int] = (36, 20)) -> Dict[str, Any]:
        """
        Prepare heatmap data from node coordinates.
        
        Args:
            nodes: List of nodes
            dimensions: Tuple of dimensions to use for x and y axis
            value_field: Field to use for cell values
            bins: Number of bins for each dimension
            
        Returns:
            Dictionary with heatmap data
        """
        if not nodes:
            logger.warning("No nodes provided for heatmap export.")
            return {}
        
        # Extract coordinate data
        dim1_values = []
        dim2_values = []
        val_values = []
        
        for node in nodes:
            if node.coordinates:
                # Get first dimension value
                if dimensions[0] == "theta":
                    # Convert to degrees for easier visualization
                    dim1_values.append(node.coordinates.theta * 180 / np.pi)
                elif dimensions[0] == "r":
                    dim1_values.append(node.coordinates.r)
                elif dimensions[0] == "t":
                    dim1_values.append(node.coordinates.t)
                elif dimensions[0] == "z":
                    dim1_values.append(node.coordinates.z)
                else:
                    # Skip this node if dimension not found
                    continue
                
                # Get second dimension value
                if dimensions[1] == "theta":
                    # Convert to degrees for easier visualization
                    dim2_values.append(node.coordinates.theta * 180 / np.pi)
                elif dimensions[1] == "r":
                    dim2_values.append(node.coordinates.r)
                elif dimensions[1] == "t":
                    dim2_values.append(node.coordinates.t)
                elif dimensions[1] == "z":
                    dim2_values.append(node.coordinates.z)
                else:
                    # Skip this node if dimension not found
                    continue
                
                # Get value field
                if value_field == "r":
                    val_values.append(node.coordinates.r)
                elif value_field == "theta":
                    val_values.append(node.coordinates.theta * 180 / np.pi)
                elif value_field == "t":
                    val_values.append(node.coordinates.t)
                elif value_field == "z":
                    val_values.append(node.coordinates.z)
                else:
                    # Default to 1 for count-based heatmap
                    val_values.append(1)
        
        # Create 2D histogram (heatmap data)
        dim1_range = [min(dim1_values), max(dim1_values)]
        dim2_range = [min(dim2_values), max(dim2_values)]
        
        # Handle special case for theta (0-360 degrees)
        if dimensions[0] == "theta":
            dim1_range = [0, 360]
        if dimensions[1] == "theta":
            dim2_range = [0, 360]
        
        # Create bins
        dim1_bins = np.linspace(dim1_range[0], dim1_range[1], bins[0] + 1)
        dim2_bins = np.linspace(dim2_range[0], dim2_range[1], bins[1] + 1)
        
        # Calculate bin midpoints for axis labels
        dim1_centers = (dim1_bins[:-1] + dim1_bins[1:]) / 2
        dim2_centers = (dim2_bins[:-1] + dim2_bins[1:]) / 2
        
        # Create histogram
        hist_data, x_edges, y_edges = np.histogram2d(
            dim1_values, dim2_values, bins=[dim1_bins, dim2_bins], weights=val_values
        )
        
        # For count-based heatmap, we're done
        if value_field in ["count", "density"]:
            heatmap_data = hist_data.T  # Transpose for correct orientation
        else:
            # For value-based heatmap, normalize by count
            # First, calculate count histogram
            count_hist, _, _ = np.histogram2d(
                dim1_values, dim2_values, bins=[dim1_bins, dim2_bins]
            )
            
            # Avoid division by zero
            count_hist = np.where(count_hist > 0, count_hist, 1)
            
            # Calculate average value per bin
            heatmap_data = (hist_data / count_hist).T
        
        # Prepare result
        result = {
            "data": heatmap_data.tolist(),
            "x_labels": dim1_centers.tolist(),
            "y_labels": dim2_centers.tolist(),
            "x_dimension": dimensions[0],
            "y_dimension": dimensions[1],
            "value_field": value_field,
            "x_range": dim1_range,
            "y_range": dim2_range,
            "count": len(dim1_values)
        }
        
        logger.info(f"Prepared heatmap data for {result['count']} nodes.")
        return result
    
    def export_heatmap_json(self,
                          heatmap_data: Dict[str, Any],
                          filename: str = "heatmap_export.json") -> str:
        """
        Export heatmap data to JSON format.
        
        Args:
            heatmap_data: Heatmap data dictionary
            filename: Output filename
            
        Returns:
            Path to the exported file
        """
        if not heatmap_data:
            logger.warning("No heatmap data to export.")
            return ""
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save to JSON
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            json.dump(heatmap_data, f, indent=2)
        
        logger.info(f"Exported heatmap data to JSON: {output_path}")
        return output_path
    
    def export_heatmap_csv(self,
                         heatmap_data: Dict[str, Any],
                         filename: str = "heatmap_export.csv") -> str:
        """
        Export heatmap data to CSV format.
        
        Args:
            heatmap_data: Heatmap data dictionary
            filename: Output filename
            
        Returns:
            Path to the exported file
        """
        if not heatmap_data:
            logger.warning("No heatmap data to export.")
            return ""
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get data matrix and labels
        data_matrix = heatmap_data["data"]
        x_labels = heatmap_data["x_labels"]
        y_labels = heatmap_data["y_labels"]
        
        # Save to CSV
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header row with x labels
            header = ["y / x"] + [f"{x:.2f}" for x in x_labels]
            writer.writerow(header)
            
            # Write data rows
            for i, y_label in enumerate(y_labels):
                row_data = [f"{y_label:.2f}"] + [f"{cell:.4f}" for cell in data_matrix[i]]
                writer.writerow(row_data)
        
        logger.info(f"Exported heatmap data to CSV: {output_path}")
        return output_path
    
    def export_atlas_heatmaps(self,
                            atlas: NarrativeAtlas,
                            dimensions_list: List[Tuple[str, str]] = None,
                            formats: List[str] = ["json", "csv"]) -> Dict[str, str]:
        """
        Export multiple heatmap visualizations from a NarrativeAtlas.
        
        Args:
            atlas: NarrativeAtlas instance
            dimensions_list: List of dimension pairs to create heatmaps for
            formats: List of export formats
            
        Returns:
            Dictionary of export IDs -> file paths
        """
        # Extract nodes from atlas
        nodes = list(atlas.db.nodes.values())
        
        if not nodes:
            logger.warning("No nodes found in atlas for heatmap export.")
            return {}
        
        # Default dimensions if not specified
        if dimensions_list is None:
            dimensions_list = [
                ("theta", "t"),  # Angular position vs. temporal position
                ("r", "t"),      # Radial position vs. temporal position
                ("theta", "r")   # Angular position vs. radial position
            ]
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create exports for each dimension pair
        exports = {}
        
        for dims in dimensions_list:
            # Create heatmap data
            heatmap_data = self.prepare_heatmap_data(
                nodes, 
                dimensions=dims,
                value_field="count"  # Use count for density heatmap
            )
            
            if not heatmap_data:
                continue
            
            # Export in each requested format
            for fmt in formats:
                if fmt == "json":
                    json_path = self.export_heatmap_json(
                        heatmap_data,
                        filename=f"heatmap_{dims[0]}_{dims[1]}_{timestamp}.json"
                    )
                    exports[f"{dims[0]}_{dims[1]}_json"] = json_path
                
                elif fmt == "csv":
                    csv_path = self.export_heatmap_csv(
                        heatmap_data,
                        filename=f"heatmap_{dims[0]}_{dims[1]}_{timestamp}.csv"
                    )
                    exports[f"{dims[0]}_{dims[1]}_csv"] = csv_path
        
        logger.info(f"Exported {len(exports)} heatmap files from atlas.")
        return exports 
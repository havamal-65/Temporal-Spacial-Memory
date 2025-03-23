"""
Visualization Tool for Knowledge Tracker

This module provides tools to visualize the knowledge stored in the 
Temporal-Spatial Knowledge Database, including knowledge domains,
topics, and facts.
"""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from datetime import datetime, timedelta
import logging
from uuid import UUID
import math
import json
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from .tracker import KnowledgeTracker, KnowledgeDomain, KnowledgeTopic, KnowledgeFact

logger = logging.getLogger(__name__)


class VisualizationTool:
    """
    Visualization tool for the Knowledge Tracker.
    
    This class provides methods to visualize the knowledge stored in
    the Temporal-Spatial Knowledge Database.
    """
    
    def __init__(self, tracker: KnowledgeTracker):
        """
        Initialize the visualization tool.
        
        Args:
            tracker: Knowledge tracker to visualize
        """
        self.tracker = tracker
        
        # Set up default styles
        self.domain_color = "#4287f5"
        self.topic_color = "#42c2f5"
        self.fact_color = "#42f5b3"
        self.connection_color = "#cccccc"
        self.confidence_cmap = LinearSegmentedColormap.from_list(
            "confidence", ["#f54242", "#f5f542", "#42f54e"]
        )
        
        # Set up custom node styles
        self.node_sizes = {
            "domain": 500,
            "topic": 300,
            "fact": 100
        }
    
    def visualize_domain(self, 
                        domain_id: UUID, 
                        include_facts: bool = True,
                        max_facts_per_topic: int = 10) -> Figure:
        """
        Visualize a knowledge domain and its topics.
        
        Args:
            domain_id: ID of the domain to visualize
            include_facts: Whether to include facts in the visualization
            max_facts_per_topic: Maximum number of facts to show per topic
            
        Returns:
            Matplotlib figure
        """
        # Get domain
        domain = self.tracker.get_domain(domain_id)
        if not domain:
            raise ValueError(f"Domain with ID {domain_id} not found")
        
        # Get topics for this domain
        topics = self.tracker.get_topics_by_domain(domain_id)
        
        # Create graph
        G = nx.DiGraph()
        
        # Add domain node
        G.add_node(str(domain.id), 
                label=domain.name, 
                type="domain",
                description=domain.description)
        
        # Add topic nodes and connections to domain
        for topic in topics:
            G.add_node(str(topic.id), 
                    label=topic.name, 
                    type="topic",
                    description=topic.description)
            G.add_edge(str(topic.id), str(domain.id), type="belongs_to")
            
            # Add facts if requested
            if include_facts:
                facts = self.tracker.get_facts_by_topic(topic.id)
                
                # Limit the number of facts if needed
                if len(facts) > max_facts_per_topic:
                    facts = facts[:max_facts_per_topic]
                
                # Add fact nodes and connections to topic
                for fact in facts:
                    G.add_node(str(fact.id), 
                            label=self._truncate_text(fact.content, 30), 
                            type="fact",
                            confidence=fact.confidence,
                            verification_count=fact.verification_count)
                    G.add_edge(str(fact.id), str(topic.id), type="belongs_to")
                    
                    # Add connections between related facts
                    for related_id in fact.related_facts:
                        if str(related_id) in G:
                            G.add_edge(str(fact.id), str(related_id), type="related_to")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Set positions
        pos = nx.spring_layout(G, k=0.15, iterations=50, seed=42)
        
        # Draw different node types with different styles
        self._draw_nodes_by_type(G, pos, "domain", ax)
        self._draw_nodes_by_type(G, pos, "topic", ax)
        if include_facts:
            self._draw_nodes_by_type(G, pos, "fact", ax)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.5, width=1.0, 
                           edge_color=self.connection_color, ax=ax)
        
        # Add labels
        nx.draw_networkx_labels(G, pos, 
                             font_size=8, 
                             labels={n: G.nodes[n]["label"] for n in G.nodes})
        
        # Set title
        ax.set_title(f"Knowledge Domain: {domain.name}")
        
        # Hide axis
        ax.set_axis_off()
        
        return fig
    
    def visualize_topics_over_time(self,
                                 domain_id: UUID,
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> Figure:
        """
        Visualize the growth of topics over time.
        
        Args:
            domain_id: ID of the domain to visualize
            start_time: Optional start time (defaults to earliest topic)
            end_time: Optional end time (defaults to now)
            
        Returns:
            Matplotlib figure
        """
        # Get domain
        domain = self.tracker.get_domain(domain_id)
        if not domain:
            raise ValueError(f"Domain with ID {domain_id} not found")
        
        # Get topics for this domain
        topics = self.tracker.get_topics_by_domain(domain_id)
        
        # Sort topics by creation time
        topics.sort(key=lambda t: t.created_at)
        
        # Set time range
        if not start_time:
            start_time = topics[0].created_at if topics else datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Track topic counts over time
        topic_times = [t.created_at for t in topics]
        topic_counts = list(range(1, len(topics) + 1))
        
        # Plot topics over time
        ax.plot(topic_times, topic_counts, marker='o', linestyle='-', color=self.topic_color)
        
        # Annotate some key topics
        for i, topic in enumerate(topics):
            if i % max(1, len(topics) // 5) == 0:  # Annotate ~5 topics
                ax.annotate(topic.name, (topic.created_at, i + 1),
                         textcoords="offset points", xytext=(0, 10),
                         ha='center', fontsize=8)
        
        # Set labels and title
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Topics')
        ax.set_title(f'Topic Growth Over Time for Domain: {domain.name}')
        
        # Format x-axis as dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        return fig
    
    def visualize_confidence_distribution(self, topic_id: UUID) -> Figure:
        """
        Visualize the confidence distribution of facts in a topic.
        
        Args:
            topic_id: ID of the topic to visualize
            
        Returns:
            Matplotlib figure
        """
        # Get topic
        topic = self.tracker.get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic with ID {topic_id} not found")
        
        # Get facts for this topic
        facts = self.tracker.get_facts_by_topic(topic_id)
        
        # Extract confidence values
        confidence_values = [fact.confidence for fact in facts]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create histogram
        bins = 10
        n, bins, patches = ax.hist(confidence_values, bins=bins, alpha=0.7)
        
        # Color the bars according to confidence
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        for count, x, patch in zip(n, bin_centers, patches):
            color = self.confidence_cmap(x)
            patch.set_facecolor(color)
        
        # Set labels and title
        ax.set_xlabel('Confidence')
        ax.set_ylabel('Number of Facts')
        ax.set_title(f'Confidence Distribution for Topic: {topic.name}')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.5)
        
        return fig
    
    def visualize_fact_verification_history(self, 
                                          topic_id: UUID,
                                          top_n: int = 10) -> Figure:
        """
        Visualize the verification history of facts in a topic.
        
        Args:
            topic_id: ID of the topic to visualize
            top_n: Number of most verified facts to show
            
        Returns:
            Matplotlib figure
        """
        # Get topic
        topic = self.tracker.get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic with ID {topic_id} not found")
        
        # Get facts for this topic
        facts = self.tracker.get_facts_by_topic(topic_id)
        
        # Sort facts by verification count and take top N
        facts.sort(key=lambda f: f.verification_count, reverse=True)
        top_facts = facts[:min(top_n, len(facts))]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Bar plot of verification counts
        y_pos = range(len(top_facts))
        verification_counts = [fact.verification_count for fact in top_facts]
        bars = ax.barh(y_pos, verification_counts, align='center', alpha=0.7)
        
        # Color bars by confidence
        for i, fact in enumerate(top_facts):
            bars[i].set_color(self.confidence_cmap(fact.confidence))
        
        # Set labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels([self._truncate_text(fact.content, 40) for fact in top_facts])
        ax.invert_yaxis()  # labels read top-to-bottom
        ax.set_xlabel('Verification Count')
        ax.set_title(f'Most Verified Facts for Topic: {topic.name}')
        
        # Add counts as text
        for i, count in enumerate(verification_counts):
            ax.text(count + 0.1, i, str(count), va='center')
        
        return fig
    
    def visualize_temporal_spatial_distribution(self, 
                                              domain_id: UUID,
                                              time_as_color: bool = True) -> Figure:
        """
        Visualize the temporal-spatial distribution of facts in a domain.
        
        Args:
            domain_id: ID of the domain to visualize
            time_as_color: Whether to represent time as color (True) or as Z-axis (False)
            
        Returns:
            Matplotlib figure
        """
        # Get domain
        domain = self.tracker.get_domain(domain_id)
        if not domain:
            raise ValueError(f"Domain with ID {domain_id} not found")
        
        # Get topics for this domain
        topics = self.tracker.get_topics_by_domain(domain_id)
        
        # Collect facts from all topics
        all_facts = []
        for topic in topics:
            facts = self.tracker.get_facts_by_topic(topic.id)
            all_facts.extend((fact, topic.name) for fact in facts)
        
        # If no facts, return empty figure
        if not all_facts:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(0.5, 0.5, "No facts available for visualization", 
                  ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return fig
        
        # Create figure
        if time_as_color:
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Extract spatial coordinates and timestamps
            x_coords = []
            y_coords = []
            timestamps = []
            topic_names = []
            
            for fact, topic_name in all_facts:
                # Get node for this fact
                node = self.tracker._get_node_by_id(fact.id)
                if node and node.position:
                    # Position[0] is the timestamp, position[1:3] are spatial coordinates
                    timestamps.append(fact.created_at.timestamp())
                    x_coords.append(node.position[1])
                    y_coords.append(node.position[2])
                    topic_names.append(topic_name)
            
            # Convert timestamps to colors
            min_time = min(timestamps)
            max_time = max(timestamps)
            time_range = max_time - min_time
            colors = [(t - min_time) / time_range for t in timestamps]
            
            # Create scatter plot
            scatter = ax.scatter(x_coords, y_coords, c=colors, s=100, alpha=0.7, 
                              cmap='viridis', edgecolors='white', linewidths=0.5)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Time (newer →)')
            
            # Add tooltips for a few points
            for i in range(min(10, len(x_coords))):
                idx = int(i * len(x_coords) / 10)
                ax.annotate(topic_names[idx], (x_coords[idx], y_coords[idx]),
                         textcoords="offset points", xytext=(0, 10),
                         ha='center', fontsize=8)
        else:
            # 3D visualization with time as Z-axis
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            # Extract spatial coordinates and timestamps
            x_coords = []
            y_coords = []
            z_coords = []  # Time as z-axis
            topic_names = []
            
            for fact, topic_name in all_facts:
                # Get node for this fact
                node = self.tracker._get_node_by_id(fact.id)
                if node and node.position:
                    # Position[0] is the timestamp, position[1:3] are spatial coordinates
                    z_coords.append(fact.created_at.timestamp())
                    x_coords.append(node.position[1])
                    y_coords.append(node.position[2])
                    topic_names.append(topic_name)
            
            # Normalize Z-coordinates for better visualization
            min_z = min(z_coords)
            max_z = max(z_coords)
            z_range = max_z - min_z
            z_coords_norm = [(z - min_z) / z_range for z in z_coords]
            
            # Create scatter plot
            scatter = ax.scatter(x_coords, y_coords, z_coords_norm, c=z_coords_norm, 
                              s=100, alpha=0.7, cmap='viridis', 
                              edgecolors='white', linewidths=0.5)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Time (newer →)')
            
            # Set labels
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.set_zlabel('Time')
        
        # Set title
        plt.title(f'Temporal-Spatial Distribution of Facts in Domain: {domain.name}')
        
        return fig
    
    def _draw_nodes_by_type(self, G: nx.DiGraph, pos: Dict, node_type: str, ax: Axes) -> None:
        """
        Draw nodes of a specific type.
        
        Args:
            G: NetworkX graph
            pos: Node positions
            node_type: Type of nodes to draw
            ax: Matplotlib axes
        """
        # Get nodes of this type
        nodes = [n for n, attr in G.nodes(data=True) if attr.get("type") == node_type]
        
        if not nodes:
            return
        
        # Set node color
        if node_type == "domain":
            color = self.domain_color
        elif node_type == "topic":
            color = self.topic_color
        elif node_type == "fact":
            # Color facts by confidence if available
            colors = [self.confidence_cmap(G.nodes[n].get("confidence", 0.5)) for n in nodes]
            nx.draw_networkx_nodes(G, pos, nodelist=nodes, 
                                node_size=self.node_sizes.get(node_type, 300),
                                node_color=colors, alpha=0.8, ax=ax)
            return
        else:
            color = "#cccccc"  # Default color
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, nodelist=nodes, 
                            node_size=self.node_sizes.get(node_type, 300),
                            node_color=color, alpha=0.8, ax=ax)
    
    def _truncate_text(self, text: str, max_length: int = 20) -> str:
        """
        Truncate text to a maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..." 
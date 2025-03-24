"""
Knowledge Visualizer

This module provides visualization tools for the Knowledge Tracker,
allowing users to generate visual representations of knowledge domains,
topics, and facts.
"""

import logging
import os
from datetime import datetime
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

class KnowledgeVisualizer:
    """
    A class to visualize knowledge from the Knowledge Tracker.
    
    This class provides methods to generate visual representations
    of knowledge domains, topics, and facts, including domain overviews,
    topic networks, and fact timelines.
    """
    
    def __init__(self, tracker):
        """
        Initialize the KnowledgeVisualizer.
        
        Args:
            tracker: An instance of KnowledgeTracker
        """
        self.tracker = tracker
        self.output_dir = "visualizations"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def create_domain_overview(self, domain_id, filename=None):
        """
        Create a visual overview of a knowledge domain and its topics.
        
        Args:
            domain_id: ID of the domain to visualize
            filename: Output filename (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a directed graph
            G = nx.DiGraph()
            
            # Get domain details
            domain = self.tracker.get_domain(domain_id)
            if not domain:
                logger.error(f"Domain {domain_id} not found")
                return False
            
            # Add domain node
            G.add_node(str(domain.id), type="domain", name=domain.name)
            
            # Get topics for this domain
            topics = self.tracker.get_topics_by_domain(domain_id)
            
            # Add topic nodes and edges
            for topic in topics:
                G.add_node(str(topic.id), type="topic", name=topic.name)
                G.add_edge(str(domain.id), str(topic.id))
            
            # Create the plot
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, seed=42)
            
            # Draw domain nodes
            domain_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "domain"]
            nx.draw_networkx_nodes(G, pos, nodelist=domain_nodes, node_size=1200, 
                                  node_color="lightblue", alpha=0.8)
            
            # Draw topic nodes
            topic_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "topic"]
            nx.draw_networkx_nodes(G, pos, nodelist=topic_nodes, node_size=800, 
                                  node_color="lightgreen", alpha=0.8)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.7, arrows=True)
            
            # Draw labels
            labels = {n: d.get("name", n) for n, d in G.nodes(data=True)}
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
            
            # Set title and adjust layout
            plt.title(f"Domain Overview: {domain.name}")
            plt.axis("off")
            plt.tight_layout()
            
            # Save or show the figure
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, dpi=300, bbox_inches="tight")
                logger.info(f"Domain overview saved to {full_path}")
                plt.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating domain overview: {str(e)}")
            return False
    
    def create_topic_network(self, topic_id, filename=None):
        """
        Create a network visualization of a topic and its facts.
        
        Args:
            topic_id: ID of the topic to visualize
            filename: Output filename (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a directed graph
            G = nx.DiGraph()
            
            # Get topic details
            topic = self.tracker.get_topic(topic_id)
            if not topic:
                logger.error(f"Topic {topic_id} not found")
                return False
            
            # Add topic node
            G.add_node(str(topic.id), type="topic", name=topic.name)
            
            # Get facts for this topic
            facts = self.tracker.get_facts_by_topic(topic_id)
            
            # Add fact nodes and edges
            for fact in facts:
                G.add_node(str(fact.id), type="fact", content=fact.content, 
                           confidence=fact.confidence)
                G.add_edge(str(topic.id), str(fact.id))
                
                # Add edges for related facts
                for related_id in fact.related_facts:
                    if str(related_id) in G:
                        G.add_edge(str(fact.id), str(related_id), style="dashed")
            
            # Create the plot
            plt.figure(figsize=(14, 10))
            pos = nx.spring_layout(G, seed=42)
            
            # Draw topic node
            topic_nodes = [str(topic.id)]
            nx.draw_networkx_nodes(G, pos, nodelist=topic_nodes, node_size=1200, 
                                  node_color="lightgreen", alpha=0.8)
            
            # Draw fact nodes with color based on confidence
            fact_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "fact"]
            
            # Only draw fact nodes if there are any
            if fact_nodes:
                confidences = [G.nodes[n].get("confidence", 0.5) for n in fact_nodes]
                cmap = plt.cm.get_cmap("YlOrRd")
                nx.draw_networkx_nodes(G, pos, nodelist=fact_nodes, node_size=800, 
                                      node_color=confidences, cmap=cmap, alpha=0.8)
                
                # Draw edges
                solid_edges = [(u, v) for u, v, d in G.edges(data=True) 
                              if d.get("style") != "dashed"]
                dashed_edges = [(u, v) for u, v, d in G.edges(data=True) 
                               if d.get("style") == "dashed"]
                
                nx.draw_networkx_edges(G, pos, edgelist=solid_edges, 
                                      width=1.5, alpha=0.7, arrows=True)
                
                if dashed_edges:
                    nx.draw_networkx_edges(G, pos, edgelist=dashed_edges, 
                                          width=1.0, alpha=0.5, style="dashed", arrows=False)
                
                # Add a colorbar for confidence
                sm = plt.cm.ScalarMappable(cmap=cmap)
                sm.set_array(confidences)
                
                # Only add colorbar if we have facts
                if fact_nodes:
                    plt.colorbar(sm, label="Confidence", ax=plt.gca())
            else:
                # If no facts, just draw the topic node with a label
                nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.7, arrows=True)
            
            # Draw labels
            topic_labels = {n: G.nodes[n].get("name", n) for n in topic_nodes}
            fact_labels = {n: G.nodes[n].get("content", "")[:20] + "..." 
                          for n in fact_nodes}
            labels = {**topic_labels, **fact_labels}
            
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=9)
            
            # Set title and adjust layout
            plt.title(f"Topic Network: {topic.name}")
            plt.axis("off")
            plt.tight_layout()
            
            # Save or show the figure
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, dpi=300, bbox_inches="tight")
                logger.info(f"Topic network saved to {full_path}")
                plt.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating topic network: {str(e)}")
            return False
    
    def create_fact_timeline(self, domain_id, filename=None):
        """
        Create a timeline visualization of facts for a domain.
        
        Args:
            domain_id: ID of the domain
            filename: Output filename (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get domain details
            domain = self.tracker.get_domain(domain_id)
            if not domain:
                logger.error(f"Domain {domain_id} not found")
                return False
            
            # Get topics for this domain
            topics = self.tracker.get_topics_by_domain(domain_id)
            
            # Collect all facts with their creation dates
            facts_data = []
            for topic in topics:
                facts = self.tracker.get_facts_by_topic(topic.id)
                for fact in facts:
                    facts_data.append({
                        "topic": topic.name,
                        "content": fact.content[:30] + "...",
                        "created_at": datetime.fromisoformat(fact.created_at),
                        "confidence": fact.confidence
                    })
            
            if not facts_data:
                logger.warning(f"No facts found for domain {domain_id}")
                return False
            
            # Sort facts by creation date
            facts_data.sort(key=lambda x: x["created_at"])
            
            # Create the plot
            plt.figure(figsize=(14, 8))
            
            # Extract data for plotting
            topics = list(set(fact["topic"] for fact in facts_data))
            topic_indices = {topic: i for i, topic in enumerate(topics)}
            
            x_dates = [fact["created_at"] for fact in facts_data]
            y_positions = [topic_indices[fact["topic"]] for fact in facts_data]
            confidences = [fact["confidence"] for fact in facts_data]
            
            # Create scatter plot
            scatter = plt.scatter(x_dates, y_positions, c=confidences, cmap="YlOrRd", 
                                 s=100, alpha=0.8)
            
            # Add text labels
            for i, fact in enumerate(facts_data):
                plt.text(fact["created_at"], y_positions[i], fact["content"], 
                        fontsize=8, ha="right", va="center")
            
            # Set axis labels and title
            plt.yticks(range(len(topics)), topics)
            plt.xlabel("Time")
            plt.ylabel("Topic")
            plt.title(f"Fact Timeline: {domain.name}")
            
            # Add a colorbar for confidence
            plt.colorbar(scatter, label="Confidence")
            
            # Format the time axis
            plt.gcf().autofmt_xdate()
            plt.tight_layout()
            
            # Save or show the figure
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, dpi=300, bbox_inches="tight")
                logger.info(f"Fact timeline saved to {full_path}")
                plt.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating fact timeline: {str(e)}")
            return False 
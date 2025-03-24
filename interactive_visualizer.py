#!/usr/bin/env python3
"""
Interactive 3D Visualization for the Conversation Memory Database.
This creates a web-based 3D visualization where conversations are represented
as spheres in 3D space, with connections shown as lines.
"""

import os
import sys
import json
import math
import random
import plotly.graph_objects as go
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from src.models.mesh_tube import MeshTube
from src.models.node import Node
from conversation_memory import ConversationMemory

# Node type to color mapping
NODE_COLORS = {
    "conversation": "#1f77b4",  # Blue
    "message": "#ff7f0e",       # Orange
    "keyword": "#2ca02c",       # Green
    "query": "#d62728",         # Red
    "default": "#7f7f7f"        # Gray
}

def create_3d_visualization(memory_db: MeshTube, output_file: str = "memory_visualization.html"):
    """
    Create an interactive 3D visualization of the memory database.
    
    Args:
        memory_db: MeshTube database to visualize
        output_file: HTML file to save the visualization
    """
    # Extract all nodes
    nodes = list(memory_db.nodes.values())
    
    if not nodes:
        print("No data to visualize.")
        return
    
    # Create node and connection data
    node_x, node_y, node_z = [], [], []  # Node positions
    node_colors, node_sizes = [], []     # Node visual properties
    node_texts = []                      # Node hover info
    
    # Edge data (lines)
    edge_x, edge_y, edge_z = [], [], []
    
    # Process all nodes
    node_map = {}  # Map node_id to index in the lists
    
    for i, node in enumerate(nodes):
        # Convert cylindrical coordinates to cartesian
        r = node.distance
        theta = math.radians(node.angle)
        
        # For query nodes, use a specific distance and arrange them along the time axis
        if node.content.get("type") == "query":
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = node.time
        else:
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = node.time
        
        # Store node position
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        
        # Store node index for edge creation
        node_map[node.node_id] = i
        
        # Determine node color based on type
        node_type = node.content.get("type", "default")
        node_colors.append(NODE_COLORS.get(node_type, NODE_COLORS["default"]))
        
        # Determine node size
        if node_type == "conversation":
            node_sizes.append(15)  # Larger for conversations
        elif node_type == "keyword":
            node_sizes.append(12)  # Medium for keywords
        else:
            node_sizes.append(10)  # Slightly larger sizes for all other nodes for better visibility
        
        # Create hover text
        text = f"Type: {node_type}<br>"
        text += f"Coordinates: (Time: {node.time}, Distance: {node.distance}, Angle: {node.angle})<br>"
        
        if node_type == "conversation":
            text += f"Title: {node.content.get('title', 'Untitled')}<br>"
            text += f"Summary: {node.content.get('summary', 'No summary')[:50]}...<br>"
            text += f"Messages: {node.content.get('message_count', 0)}"
        elif node_type == "message":
            text += f"Role: {node.content.get('role', 'unknown')}<br>"
            content = node.content.get('content', '')
            text += f"Content: {content[:50]}..." if len(content) > 50 else f"Content: {content}"
        elif node_type == "keyword":
            text += f"Keyword: {node.content.get('keyword', '')}"
        elif node_type == "query":
            text += f"Query: {node.content.get('query', '')[:50]}...<br>"
            result = node.content.get('result', '')
            text += f"Result: {result[:50]}..." if len(result) > 50 else f"Result: {result}"
        
        node_texts.append(text)
    
    # Process connections (edges)
    processed_edges = set()  # To avoid duplicates
    
    for node in nodes:
        for connected_id in node.connections:
            # Create a unique edge identifier
            edge_key = tuple(sorted([node.node_id, connected_id]))
            
            if edge_key in processed_edges:
                continue  # Skip if already processed
                
            processed_edges.add(edge_key)
            
            # Get indices for both nodes
            if connected_id not in node_map:
                continue  # Skip if connected node not found
                
            i1 = node_map[node.node_id]
            i2 = node_map[connected_id]
            
            # Add line segments
            edge_x.extend([node_x[i1], node_x[i2], None])
            edge_y.extend([node_y[i1], node_y[i2], None])
            edge_z.extend([node_z[i1], node_z[i2], None])
    
    # Create 3D scatter plot for nodes
    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            opacity=0.8,
            line=dict(width=0.5, color='rgb(50,50,50)')
        ),
        text=node_texts,
        hoverinfo='text'
    )
    
    # Create lines for connections
    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(
            color='rgba(50,50,50,0.8)',  # Charcoal grey with higher opacity
            width=2  # Slightly thicker lines
        ),
        hoverinfo='none'
    )
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace])
    
    # Add legend
    legend_traces = []
    for node_type, color in NODE_COLORS.items():
        legend_trace = go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            name=node_type.capitalize()
        )
        legend_traces.append(legend_trace)
    
    fig.add_traces(legend_traces)
    
    # Update layout
    fig.update_layout(
        title=f"3D Memory Visualization - {memory_db.name}",
        scene=dict(
            xaxis=dict(title="Distance (Radial)"),
            yaxis=dict(title="Angle (Angular)"),
            zaxis=dict(title="Time"),
            aspectmode='auto'
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.7)"
        )
    )
    
    # Save as HTML file
    fig.write_html(output_file)
    print(f"Visualization saved to {output_file}")
    
    # Return the figure for inline display
    return fig


def create_conversation_visualization(memory: ConversationMemory, 
                                     conversation_id: str,
                                     output_file: Optional[str] = None):
    """
    Create a focused 3D visualization for a specific conversation.
    
    Args:
        memory: ConversationMemory instance
        conversation_id: ID of the conversation to visualize
        output_file: Optional HTML file to save the visualization
        
    Returns:
        Plotly figure
    """
    # Get conversation data
    conversation = memory.get_conversation(conversation_id)
    
    if "error" in conversation:
        print(f"Error: {conversation['error']}")
        return None
    
    # Get related conversations
    related = memory.get_related_conversations(conversation_id)
    
    # Extract nodes related to this conversation
    nodes = list(memory.db.nodes.values())
    relevant_nodes = []
    
    # Find conversation node and its direct connections
    conv_node = None
    
    for node in nodes:
        if (node.content.get("type") == "conversation" and 
            node.content.get("id") == conversation_id):
            conv_node = node
            relevant_nodes.append(node)
            break
    
    if not conv_node:
        print(f"Conversation node {conversation_id} not found")
        return None
    
    # Add directly connected nodes
    for node in nodes:
        # Include all messages from this conversation
        if (node.content.get("type") == "message" and 
            node.content.get("conversation_id") == conversation_id):
            relevant_nodes.append(node)
        
        # Include connected keywords
        elif node.content.get("type") == "keyword" and conv_node.node_id in node.connections:
            relevant_nodes.append(node)
        
        # Include queries related to this conversation
        elif (node.content.get("type") == "query" and 
              node.content.get("conversation_id") == conversation_id):
            relevant_nodes.append(node)
    
    # Add related conversation nodes
    related_ids = [r.get("id") for r in related if "id" in r]
    for node in nodes:
        if (node.content.get("type") == "conversation" and 
            node.content.get("id") in related_ids):
            relevant_nodes.append(node)
    
    # Create a temporary MeshTube with just the relevant nodes
    temp_db = MeshTube(name=f"Conversation: {conversation.get('title', 'Untitled')}")
    
    # Add nodes to temp database
    node_map = {}  # Original ID to new node mapping
    for node in relevant_nodes:
        new_node = temp_db.add_node(
            content=node.content,
            time=node.time,
            distance=node.distance,
            angle=node.angle,
            parent_id=node.parent_id
        )
        node_map[node.node_id] = new_node
    
    # Add connections
    for node in relevant_nodes:
        for conn_id in node.connections:
            if conn_id in node_map:
                temp_db.connect_nodes(
                    node_map[node.node_id].node_id, 
                    node_map[conn_id].node_id
                )
    
    # Create visualization
    title = f"Conversation: {conversation.get('title', 'Untitled')}"
    if output_file:
        output_path = output_file
    else:
        conv_title = conversation.get('title', 'conversation').replace(' ', '_').lower()
        output_path = f"conversation_{conv_title}_{conversation_id[:8]}.html"
    
    fig = create_3d_visualization(temp_db, output_path)
    fig.update_layout(title=title)
    
    return fig


def create_combined_time_visualization(memory: ConversationMemory, output_file: str = "conversation_timeline.html"):
    """
    Create a visualization showing conversations arranged by time.
    
    Args:
        memory: ConversationMemory instance
        output_file: HTML file to save the visualization
    """
    # Get all conversations
    all_conversations = memory.get_all_conversations()
    
    if not all_conversations:
        print("No conversations to visualize.")
        return None
    
    # Extract time data from created_at timestamps
    # This is simplified - in a real system, parse the timestamps correctly
    # For now, just use the order of conversations
    for i, conv in enumerate(all_conversations):
        conv["time_position"] = i
    
    # Create a visualization with conversations on a timeline
    fig = go.Figure()
    
    # X will be time, Y will be randomly distributed for visibility
    conv_x, conv_y, conv_z = [], [], []
    conv_colors, conv_sizes = [], []
    conv_texts = []
    
    # Create a point for each conversation
    for conv in all_conversations:
        conv_x.append(conv["time_position"])
        # Random Y position for spacing (can be more sophisticated)
        conv_y.append(random.uniform(-1, 1))
        # Use number of messages for Z height
        conv_z.append(conv.get("message_count", 1))
        
        # Color and size
        conv_colors.append(NODE_COLORS["conversation"])
        conv_sizes.append(15)
        
        # Hover text
        text = f"Title: {conv.get('title', 'Untitled')}<br>"
        text += f"Messages: {conv.get('message_count', 0)}<br>"
        text += f"Keywords: {', '.join(conv.get('keywords', []))}<br>"
        text += f"Summary: {conv.get('summary', 'No summary')[:100]}..."
        
        conv_texts.append(text)
    
    # Create scatter plot
    conv_trace = go.Scatter3d(
        x=conv_x, y=conv_y, z=conv_z,
        mode='markers',
        marker=dict(
            size=conv_sizes,
            color=conv_colors,
            opacity=0.8,
        ),
        text=conv_texts,
        hoverinfo='text'
    )
    
    fig.add_trace(conv_trace)
    
    # Update layout
    fig.update_layout(
        title="Conversation Timeline Visualization",
        scene=dict(
            xaxis=dict(title="Time (Chronological)"),
            yaxis=dict(title="Topic Distribution"),
            zaxis=dict(title="Message Count"),
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    # Save to file
    fig.write_html(output_file)
    print(f"Timeline visualization saved to {output_file}")
    
    return fig


def main():
    """Main function to demonstrate the visualizer."""
    # Check if plotly is available
    try:
        import plotly
    except ImportError:
        print("Plotly is required for visualization.")
        print("Please install it with: pip install plotly")
        return
    
    # Check for existing memory database
    memory = ConversationMemory()
    
    # Get memory data file path
    memory_file = os.path.join("data", "conversation_memory.json")
    
    # If memory database exists, load it
    if os.path.exists(memory_file):
        print("Loading existing memory database...")
        memory.load()
        
        # Fix query node positioning if needed
        for node in memory.db.nodes.values():
            if node.content.get("type") == "query":
                # Adjust query node positions to be consistently along the time axis
                # This ensures they appear properly in the visualization
                conversation_id = node.content.get("conversation_id")
                if conversation_id:
                    # Find the related conversation node
                    for conv_node in memory.db.nodes.values():
                        if (conv_node.content.get("type") == "conversation" and 
                            conv_node.content.get("id") == conversation_id):
                            # Position query at same angle as conversation but at a fixed distance
                            node.angle = conv_node.angle
                            node.distance = 0.4  # Fixed distance for query nodes
                            # Position slightly higher in time than the conversation
                            node.time = conv_node.time + 0.2
                            break
        
        # Create visualization of all memory
        create_3d_visualization(memory.db, "memory_visualization.html")
        
        # Create timeline visualization
        create_combined_time_visualization(memory, "conversation_timeline.html")
        
        # Get all conversations
        conversations = memory.get_all_conversations()
        
        # Create focused visualizations for each conversation
        for i, conv in enumerate(conversations[:3]):  # Limit to first 3 for demo
            print(f"Creating visualization for conversation: {conv.get('title')}")
            create_conversation_visualization(
                memory, 
                conv.get("id"), 
                f"conversation_{i+1}_visualization.html"
            )
        
        print("Visualizations complete!")
        
    else:
        print("No existing memory database found. Creating sample data...")
        
        # Create sample conversation
        messages = [
            {"role": "user", "content": "How do I use the Temporal-Spatial Memory Database?"},
            {"role": "assistant", "content": "The Temporal-Spatial Memory Database organizes information in a cylindrical structure with time, distance, and angle dimensions. You can store and connect nodes representing different concepts and track changes over time."},
            {"role": "user", "content": "Can you show me an example?"},
            {"role": "assistant", "content": "Sure! Here's an example: Create a database with db = MeshTube(name='My DB'), add nodes with db.add_node(), connect them with db.connect_nodes(), and query with methods like get_temporal_slice() and get_nearest_nodes()."}
        ]
        
        summary = "A conversation about using the Temporal-Spatial Memory Database with a brief example."
        keywords = ["database", "temporal", "spatial", "example", "query"]
        
        # Add conversation to memory
        conv_id = memory.add_conversation(
            title="Using the Memory Database",
            messages=messages,
            summary=summary,
            keywords=keywords
        )
        
        # Create a second conversation
        messages2 = [
            {"role": "user", "content": "What is the difference between spatial and temporal dimensions?"},
            {"role": "assistant", "content": "Spatial dimensions refer to physical space (like x, y, z coordinates) while temporal dimensions relate to time. In our database, spatial dimensions include distance from center and angle, while time is the temporal dimension."},
            {"role": "user", "content": "How does this help with organizing information?"},
            {"role": "assistant", "content": "This structure allows you to organize information both by conceptual relationships (using spatial positioning) and by when information was added or relevant (using the time dimension). It's useful for tracking how concepts evolve and relate to each other."}
        ]
        
        summary2 = "Discussion about spatial vs temporal dimensions and how they help organize information."
        keywords2 = ["spatial", "temporal", "dimensions", "organization", "conceptual"]
        
        # Add second conversation to memory
        conv_id2 = memory.add_conversation(
            title="Spatial vs Temporal Dimensions",
            messages=messages2,
            summary=summary2,
            keywords=keywords2
        )
        
        # Add a query
        memory.add_query_result(
            query="How do I visualize the database?",
            result="You can visualize the database using the interactive_visualizer.py script, which creates 3D visualizations where nodes are represented as spheres and connections as lines.",
            conversation_id=conv_id
        )
        
        # Create visualizations
        create_3d_visualization(memory.db, "memory_visualization.html")
        create_combined_time_visualization(memory, "conversation_timeline.html")
        
        # Create focused visualization for first conversation
        create_conversation_visualization(memory, conv_id, "conversation_1_visualization.html")
        
        # Create focused visualization for second conversation
        create_conversation_visualization(memory, conv_id2, "conversation_2_visualization.html")
        
        print("Sample visualizations created!")


if __name__ == "__main__":
    main() 
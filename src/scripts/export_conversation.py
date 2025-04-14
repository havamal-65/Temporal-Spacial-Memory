#!/usr/bin/env python3
"""
Script to export conversation to a text file.
"""

import os
import sys
import json
import textwrap
from datetime import datetime
from typing import Dict, List

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.node import Node
from models.mesh_tube import MeshTube

def wrap_text(text, width=80):
    """Wrap text to the specified width."""
    if not text:
        return ""
    return '\n'.join(textwrap.wrap(text, width=width))

def format_keywords(keywords, width=80):
    """Format keywords list to fit within width."""
    if not keywords:
        return "None"
    
    # Join keywords with commas
    text = ", ".join(keywords)
    
    # Wrap the text
    return wrap_text(text, width=width)

def main():
    """Main function to export conversation to a text file."""
    try:
        # Initialize memory system
        memory = MeshTube("conversation_memory", "data")
        memory.load()
        
        # Find conversation node
        conversation_node = None
        for node_id, node in memory.nodes.items():
            if isinstance(node, Node) and isinstance(node.content, dict) and node.content.get("type") == "conversation":
                conversation_node = node
                break
        
        if not conversation_node:
            print("No conversation found in database.")
            return
        
        # Prepare output file
        output_dir = "exports"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"conversation_{timestamp}.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write conversation details
            content = conversation_node.content
            f.write("="*80 + "\n")
            f.write(f"CONVERSATION: {content.get('title', 'Untitled')}\n")
            f.write("="*80 + "\n\n")
            
            summary = content.get('summary', 'No summary available')
            f.write(f"Summary:\n{wrap_text(summary)}\n\n")
            
            keywords = content.get('keywords', [])
            f.write(f"Keywords: {format_keywords(keywords)}\n\n")
            
            f.write(f"Message count: {content.get('message_count', 0)}\n")
            f.write("-"*80 + "\n\n")
            
            # Collect and sort messages
            messages = []
            for node_id, node in memory.nodes.items():
                if isinstance(node, Node) and isinstance(node.content, dict) and node.content.get("type") == "message":
                    messages.append((node.content.get("index", 0), node))
            
            # Sort messages by index
            messages.sort(key=lambda x: x[0])
            
            # Write messages
            f.write("MESSAGES:\n")
            for idx, (_, message_node) in enumerate(messages, 1):
                role = message_node.content.get('role', 'unknown')
                content = message_node.content.get('content', 'No content')
                f.write(f"\n{idx}. [{role}]\n")
                f.write(wrap_text(content) + "\n")
                f.write("-"*40 + "\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"Conversation exported to: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
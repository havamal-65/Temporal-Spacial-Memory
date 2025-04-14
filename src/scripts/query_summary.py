#!/usr/bin/env python3
"""
Query script to get conversation summaries from the memory database.
"""

import os
import sys
import json
import textwrap
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
    """Main function to query conversation summaries."""
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
        
        # Print conversation details
        content = conversation_node.content
        print("\n" + "="*80)
        print(f"CONVERSATION: {content.get('title', 'Untitled')}")
        print("="*80)
        
        summary = content.get('summary', 'No summary available')
        print(f"Summary:\n{wrap_text(summary)}\n")
        
        keywords = content.get('keywords', [])
        print(f"Keywords: {format_keywords(keywords)}")
        
        print(f"Message count: {content.get('message_count', 0)}")
        print("-"*80)
        
        # Collect and sort messages
        messages = []
        for node_id, node in memory.nodes.items():
            if isinstance(node, Node) and isinstance(node.content, dict) and node.content.get("type") == "message":
                messages.append((node.content.get("index", 0), node))
        
        # Sort messages by index
        messages.sort(key=lambda x: x[0])
        
        # Print messages
        print("\nMESSAGES:")
        for idx, (_, message_node) in enumerate(messages, 1):
            role = message_node.content.get('role', 'unknown')
            content = message_node.content.get('content', 'No content')
            print(f"\n{idx}. [{role}]")
            print(wrap_text(content))
            print("-"*40)
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
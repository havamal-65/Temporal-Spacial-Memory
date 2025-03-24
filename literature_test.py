#!/usr/bin/env python3
"""
Test script for processing literature paragraphs with the Temporal-Spatial Memory system.
Allows inputting paragraphs from literature and visualizing their structure in the memory database.
"""

import os
import sys
import argparse
import textwrap
import re
from typing import List, Dict, Any, Optional

from conversation_memory import ConversationMemory, extract_keywords, generate_summary
import interactive_visualizer

def process_literature_paragraph(text: str, title: str) -> str:
    """
    Process a literature paragraph and store it in the memory database.
    
    Args:
        text: The literature paragraph text
        title: Title for this literature entry
        
    Returns:
        The ID of the created entry in the database
    """
    # Create or load the memory database
    memory = ConversationMemory(db_name="literature_memory")
    memory.load()
    
    # Split the paragraph into sentences to simulate messages
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Format as messages alternating between "narrator" and "character"
    messages = []
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        # Determine a role based on sentence characteristics
        # This is just for demonstration - in reality you'd use more sophisticated NLP
        if '"' in sentence or "'" in sentence:
            role = "character"
        else:
            role = "narrator"
            
        messages.append({
            "role": role,
            "content": sentence.strip()
        })
    
    # Extract keywords from the full text
    keywords = extract_keywords(text, max_keywords=8)
    
    # Generate a simple summary
    summary = generate_summary(messages, max_length=150)
    
    # Add to memory
    entry_id = memory.add_conversation(
        title=title,
        messages=messages,
        summary=summary,
        keywords=keywords
    )
    
    # Save the memory database
    memory.save()
    
    # Create a visualization for this literature entry
    interactive_visualizer.create_conversation_visualization(
        memory,
        entry_id,
        f"literature_{entry_id[:8]}.html"
    )
    
    # Update the main visualization
    interactive_visualizer.create_3d_visualization(
        memory.db,
        "literature_visualization.html"
    )
    
    return entry_id

def add_query_about_literature(text: str, entry_id: str) -> None:
    """
    Add a query about the literature paragraph.
    
    Args:
        text: The query text
        entry_id: ID of the literature entry
    """
    memory = ConversationMemory(db_name="literature_memory")
    memory.load()
    
    # Add the query
    memory.add_query_result(
        query=text,
        result="This is a query about the literature paragraph.",
        conversation_id=entry_id
    )
    
    # Regenerate visualizations
    interactive_visualizer.create_3d_visualization(
        memory.db,
        "literature_visualization.html"
    )
    
    interactive_visualizer.create_conversation_visualization(
        memory,
        entry_id,
        f"literature_{entry_id[:8]}.html"
    )

def create_literature_launcher() -> None:
    """Create a launcher HTML file for the literature visualizations."""
    memory = ConversationMemory(db_name="literature_memory")
    memory.load()
    
    # Get all literature entries
    entries = memory.get_all_conversations()
    
    # Create HTML content
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Literature Memory Visualizations</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f9fc;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        }
        .card h2 {
            color: #3498db;
            margin-top: 0;
        }
        .card p {
            color: #666;
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        footer {
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <h1>Literature Memory Visualizations</h1>
    
    <div class="container">
        <div class="card">
            <h2>Complete Literature Memory</h2>
            <p>View the entire memory database with all literature entries and their relationships.</p>
            <a href="literature_visualization.html" class="btn">Open Visualization</a>
        </div>
"""
    
    # Add card for each literature entry
    for i, entry in enumerate(entries):
        entry_id = entry.get("id", "")
        html += f"""
        <div class="card">
            <h2>{entry.get("title", "Untitled")}</h2>
            <p>{entry.get("summary", "No summary")[:100]}...</p>
            <p>Keywords: {", ".join(entry.get("keywords", []))}</p>
            <a href="literature_{entry_id[:8]}.html" class="btn">Open Visualization</a>
        </div>
"""
    
    # Close HTML
    html += """
    </div>
    
    <footer>
        <p>Literature Analysis with Temporal-Spatial Memory Database</p>
        <p>Instructions: Click on a visualization to open it. In each visualization, you can:
        <br>• Rotate the view by clicking and dragging
        <br>• Zoom with the scroll wheel
        <br>• Hover over nodes to see details
        <br>• Click on legend items to show/hide specific node types</p>
    </footer>
</body>
</html>
"""
    
    # Write the launcher file
    with open("literature_launcher.html", "w") as f:
        f.write(html)

def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description='Process a literature paragraph into the memory database.')
    parser.add_argument('--text', '-t', type=str, help='Literature paragraph text')
    parser.add_argument('--title', type=str, default="Literature Excerpt", help='Title for this literature entry')
    parser.add_argument('--query', '-q', type=str, help='Add a query about the literature')
    parser.add_argument('--entry-id', type=str, help='Entry ID for adding a query')
    
    args = parser.parse_args()
    
    # Handle different operations
    if args.text:
        # Process the literature paragraph
        entry_id = process_literature_paragraph(args.text, args.title)
        print(f"Created literature entry with ID: {entry_id}")
        print(f"Visualization saved to literature_{entry_id[:8]}.html")
        
        # Create the launcher
        create_literature_launcher()
        print("Launcher created at literature_launcher.html")
        
        # Open the launcher
        os.system("start literature_launcher.html")
        
    elif args.query and args.entry_id:
        # Add a query about existing literature
        add_query_about_literature(args.query, args.entry_id)
        print(f"Added query: {args.query}")
        print("Visualizations updated")
        
        # Open the launcher
        os.system("start literature_launcher.html")
        
    else:
        # Interactive mode for testing
        print("=== Literature Memory Test ===")
        print("Enter a paragraph from literature to analyze:")
        
        text = input("> ")
        if not text:
            print("No text entered. Exiting.")
            return
            
        title = input("Enter a title: ")
        if not title:
            title = "Literature Excerpt"
            
        entry_id = process_literature_paragraph(text, title)
        print(f"Created literature entry with ID: {entry_id}")
        
        # Create the launcher
        create_literature_launcher()
        print("Launcher created at literature_launcher.html")
        
        # Open the launcher
        os.system("start literature_launcher.html")

if __name__ == "__main__":
    main() 
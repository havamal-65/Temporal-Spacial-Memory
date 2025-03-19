#!/usr/bin/env python3
"""
Comparison visualization between Mesh Tube Knowledge Database
and traditional document database approaches.
"""

import os
import sys
import random
from datetime import datetime

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def draw_box(text, width=30, height=3, border='│'):
    """Draw a box around text"""
    result = ['┌' + '─' * width + '┐']
    
    # Add padding lines above
    padding_above = (height - 1) // 2 - 1  # -1 for the text line
    for _ in range(padding_above):
        result.append(f'{border}' + ' ' * width + f'{border}')
    
    # Add centered text
    if len(text) > width:
        text = text[:width-3] + '...'
    text_line = f'{border}' + text.center(width) + f'{border}'
    result.append(text_line)
    
    # Add padding lines below
    padding_below = height - padding_above - 2  # -2 for text and top border
    for _ in range(padding_below):
        result.append(f'{border}' + ' ' * width + f'{border}')
    
    result.append('└' + '─' * width + '┘')
    return result

def draw_line(start_x, start_y, end_x, end_y, canvas, char=None):
    """Draw a line on the canvas using simple characters"""
    # Determine line character based on direction
    if char is None:
        if start_x == end_x:  # Vertical line
            char = '│'
        elif start_y == end_y:  # Horizontal line
            char = '─'
        else:  # Diagonal line
            char = '╱' if (end_x > start_x and end_y < start_y) or (end_x < start_x and end_y > start_y) else '╲'
    
    # Draw line
    if start_x == end_x:  # Vertical line
        for y in range(min(start_y, end_y), max(start_y, end_y) + 1):
            if 0 <= y < len(canvas) and 0 <= start_x < len(canvas[y]):
                canvas[y][start_x] = char
    elif start_y == end_y:  # Horizontal line
        for x in range(min(start_x, end_x), max(start_x, end_x) + 1):
            if 0 <= start_y < len(canvas) and 0 <= x < len(canvas[start_y]):
                canvas[start_y][x] = char
    else:  # Diagonal line (simplified)
        # Using Bresenham's line algorithm
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        sx = 1 if start_x < end_x else -1
        sy = 1 if start_y < end_y else -1
        err = dx - dy
        
        x, y = start_x, start_y
        while True:
            if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
                canvas[y][x] = char
            
            if x == end_x and y == end_y:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

def visualize_document_db():
    """Generate ASCII visualization of a document database structure"""
    # Create a blank canvas
    width, height = 80, 30
    canvas = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Draw document collections as boxes
    collection1_box = draw_box("Documents Collection", 25, 4)
    collection2_box = draw_box("Topics Collection", 25, 4)
    collection3_box = draw_box("Connections Collection", 25, 4)
    
    # Position boxes on canvas
    for i, line in enumerate(collection1_box):
        for j, char in enumerate(line):
            canvas[5 + i][10 + j] = char
    
    for i, line in enumerate(collection2_box):
        for j, char in enumerate(line):
            canvas[5 + i][45 + j] = char
            
    for i, line in enumerate(collection3_box):
        for j, char in enumerate(line):
            canvas[15 + i][27 + j] = char
    
    # Add lines for relationships
    draw_line(20, 9, 20, 15, canvas)
    draw_line(55, 9, 55, 15, canvas)
    draw_line(20, 15, 27, 15, canvas)
    draw_line(55, 15, 52, 15, canvas)
    
    # Add individual documents
    doc1_box = draw_box("Doc 1: {topic: 'AI'}", 20, 3)
    doc2_box = draw_box("Doc 2: {topic: 'ML'}", 20, 3)
    doc3_box = draw_box("Doc 3: {topic: 'NLP'}", 20, 3)
    
    # Position document boxes
    for i, line in enumerate(doc1_box):
        for j, char in enumerate(line):
            canvas[20 + i][10 + j] = char
    
    for i, line in enumerate(doc2_box):
        for j, char in enumerate(line):
            canvas[20 + i][40 + j] = char
            
    for i, line in enumerate(doc3_box):
        for j, char in enumerate(line):
            canvas[25 + i][25 + j] = char
    
    # Add connections
    draw_line(20, 23, 30, 25, canvas)
    draw_line(50, 23, 40, 25, canvas)
    
    # Convert canvas to string
    title = "Traditional Document Database Structure"
    header = f"{title}\n{'=' * len(title)}\n"
    footer = "\nDocument DBs store information in collections with explicit references."
    
    visualization = header
    for row in canvas:
        visualization += ''.join(row) + '\n'
    visualization += footer
    
    return visualization

def visualize_mesh_tube():
    """Generate ASCII visualization of the Mesh Tube database structure"""
    # Create a blank canvas
    width, height = 80, 30
    canvas = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Draw the tube outline
    center_x, center_y = width // 2, height // 2
    radius = 12
    
    # Draw time axis
    for y in range(5, 25):
        canvas[y][center_x] = '│'
    canvas[4][center_x] = '▲'
    canvas[25][center_x] = '▼'
    canvas[3][center_x-3:center_x+4] = 'Time t=0'
    canvas[26][center_x-3:center_x+4] = 'Time t=n'
    
    # Draw circular outlines at different time points
    for t in range(3):
        y_pos = 8 + t * 7
        
        # Draw circle
        for x in range(center_x - radius, center_x + radius + 1):
            for y in range(y_pos - radius//2, y_pos + radius//2 + 1):
                dx = x - center_x
                dy = (y - y_pos) * 2  # Adjust for aspect ratio
                distance = (dx*dx + dy*dy) ** 0.5
                
                if abs(distance - radius) < 0.5:
                    canvas[y][x] = '·'
    
    # Add nodes at different positions
    nodes = [
        # (Time slice, angle, distance, label)
        (0, 0, 0.5, "AI"),
        (0, 45, 0.7, "ML"),
        (0, 90, 0.6, "DL"),
        (1, 15, 0.8, "NLP"),
        (1, 60, 0.7, "GPT"),
        (2, 30, 0.9, "Ethics"),
        (2, 75, 0.5, "RAG")
    ]
    
    # Calculate positions and add nodes
    time_slices = [8, 15, 22]  # Y-positions for the 3 time slices
    
    for t, angle, distance, label in nodes:
        # Calculate position on canvas
        y = time_slices[t]
        angle_rad = angle * 3.14159 / 180
        x_offset = int(distance * radius * 0.9 * -1 * (angle / 180 - 1))
        x = center_x + x_offset
        
        # Draw node
        canvas[y][x] = 'O'
        
        # Add label
        if x < center_x:
            for i, char in enumerate(label):
                canvas[y][x - len(label) + i] = char
        else:
            for i, char in enumerate(label):
                canvas[y][x + 1 + i] = char
    
    # Add connections between nodes
    connections = [
        (0, 0, 0, 1),  # AI -> ML
        (0, 1, 0, 2),  # ML -> DL
        (0, 0, 1, 0),  # AI -> NLP (t=0 to t=1)
        (1, 0, 1, 1),  # NLP -> GPT (same time)
        (1, 1, 2, 1),  # GPT -> RAG (t=1 to t=2)
    ]
    
    for t1, n1, t2, n2 in connections:
        # Find coordinates for both nodes
        node1 = nodes[t1 * 3 + n1]
        node2 = nodes[t2 * 3 + n2]
        
        y1 = time_slices[node1[0]]
        x1 = center_x + int(node1[2] * radius * 0.9 * -1 * (node1[1] / 180 - 1))
        
        y2 = time_slices[node2[0]]
        x2 = center_x + int(node2[2] * radius * 0.9 * -1 * (node2[1] / 180 - 1))
        
        # Draw line
        draw_line(x1, y1, x2, y2, canvas, '•')
    
    # Convert canvas to string
    title = "Mesh Tube Knowledge Database Structure"
    header = f"{title}\n{'=' * len(title)}\n"
    footer = "\nMesh Tube integrates temporal (vertical) and conceptual (radial) dimensions."
    
    visualization = header
    for row in canvas:
        visualization += ''.join(row) + '\n'
    visualization += footer
    
    return visualization

def visualize_delta_encoding():
    """Generate ASCII visualization showing delta encoding advantage"""
    # Create a blank canvas
    width, height = 80, 20
    canvas = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Draw document approach (full copies)
    doc_title = "Document DB: Full Document Copies"
    for i, char in enumerate(doc_title):
        canvas[1][5 + i] = char
    
    doc1 = draw_box("Topic: AI, Desc: 'Artificial Intelligence'", 40, 3)
    doc2 = draw_box("Topic: AI, Desc: 'AI', Methods: ['ML', 'DL']", 40, 3)
    doc3 = draw_box("Topic: AI, Desc: 'AI', Methods: ['ML', 'DL', 'NLP']", 40, 3)
    
    # Position document boxes
    for i, line in enumerate(doc1):
        for j, char in enumerate(line):
            canvas[3 + i][5 + j] = char
    
    for i, line in enumerate(doc2):
        for j, char in enumerate(line):
            canvas[7 + i][5 + j] = char
            
    for i, line in enumerate(doc3):
        for j, char in enumerate(line):
            canvas[11 + i][5 + j] = char
    
    # Add time indicators
    canvas[4][47] = 't'
    canvas[4][48] = '='
    canvas[4][49] = '0'
    
    canvas[8][47] = 't'
    canvas[8][48] = '='
    canvas[8][49] = '1'
    
    canvas[12][47] = 't'
    canvas[12][48] = '='
    canvas[12][49] = '2'
    
    # Add storage indicator
    storage_text = "Storage: 3 full documents"
    for i, char in enumerate(storage_text):
        canvas[15][20 + i] = char
    
    # Draw mesh tube approach (delta encoding)
    mesh_title = "Mesh Tube: Delta Encoding"
    for i, char in enumerate(mesh_title):
        canvas[1][55 + i] = char
    
    node1 = draw_box("Topic: AI, Desc: 'Artificial Intelligence'", 40, 3)
    node2 = draw_box("Methods: ['ML', 'DL']", 25, 3)
    node3 = draw_box("Methods: ['ML', 'DL', 'NLP']", 25, 3)
    
    # Position node boxes
    for i, line in enumerate(node1):
        for j, char in enumerate(line):
            canvas[3 + i][55 + j] = char
    
    for i, line in enumerate(node2):
        for j, char in enumerate(line):
            canvas[7 + i][62 + j] = char
            
    for i, line in enumerate(node3):
        for j, char in enumerate(line):
            canvas[11 + i][62 + j] = char
    
    # Add delta references
    for i in range(6, 7):
        canvas[i][70] = '│'
    canvas[7][70] = '▲'
    
    for i in range(10, 11):
        canvas[i][70] = '│'
    canvas[11][70] = '▲'
    
    # Add time indicators
    canvas[4][97] = 't'
    canvas[4][98] = '='
    canvas[4][99] = '0'
    
    canvas[8][97] = 't'
    canvas[8][98] = '='
    canvas[8][99] = '1'
    
    canvas[12][97] = 't'
    canvas[12][98] = '='
    canvas[12][99] = '2'
    
    # Add delta references
    delta_ref1 = "Delta Ref: Origin"
    for i, char in enumerate(delta_ref1):
        canvas[7][40 + i] = char
    
    delta_ref2 = "Delta Ref: t=1"
    for i, char in enumerate(delta_ref2):
        canvas[11][40 + i] = char
    
    # Add storage indicator
    storage_text = "Storage: 1 full document + 2 deltas"
    for i, char in enumerate(storage_text):
        canvas[15][65 + i] = char
    
    # Convert canvas to string
    title = "Delta Encoding: Document DB vs. Mesh Tube"
    header = f"{title}\n{'=' * len(title)}\n"
    footer = "\nMesh Tube's delta encoding stores only changes, reducing redundancy."
    
    visualization = header
    for row in canvas:
        visualization += ''.join(row) + '\n'
    visualization += footer
    
    return visualization

def main():
    """Generate and display the visualizations"""
    print("\nGenerating visualizations to compare database approaches...\n")
    
    # Generate visualizations
    doc_db_viz = visualize_document_db()
    mesh_tube_viz = visualize_mesh_tube()
    delta_encoding_viz = visualize_delta_encoding()
    
    # Display visualizations
    print("\n" + "=" * 80)
    print(doc_db_viz)
    
    print("\n" + "=" * 80)
    print(mesh_tube_viz)
    
    print("\n" + "=" * 80)
    print(delta_encoding_viz)
    
    print("\n" + "=" * 80)
    print("Key Differences:\n")
    print("1. Temporal-Spatial Integration:")
    print("   - Document DB: Time is just another field with no inherent structure")
    print("   - Mesh Tube: Time is a fundamental dimension with built-in traversal")
    
    print("\n2. Conceptual Proximity:")
    print("   - Document DB: Relations through explicit references only")
    print("   - Mesh Tube: Spatial positioning encodes semantic relationships")
    
    print("\n3. Context Preservation:")
    print("   - Document DB: Requires complex joins/lookups to trace context")
    print("   - Mesh Tube: Natural traversal of related topics through time")
    
    print("\n4. Storage Efficiency:")
    print("   - Document DB: More compact but less structured")
    print("   - Mesh Tube: Larger but with delta encoding for evolving content")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
3D visualization for narrative structures using the Temporal-Spatial Memory framework.
"""

import os
import json
import math
from typing import Dict, List, Any, Optional

# Import visualization utilities as needed
# This implementation assumes you have HTML/JS visualization utilities

def create_narrative_visualization(atlas, output_path: str) -> None:
    """
    Create an interactive 3D visualization of the narrative structure.
    
    Args:
        atlas: The NarrativeAtlas instance
        output_path: Path to save the visualization HTML file
    """
    # Create data structure for visualization
    nodes_data = []
    links_data = []
    
    # Process characters
    for char_id, character in atlas.characters.items():
        # Map character attributes for visualization
        node = {
            "id": char_id,
            "type": "character",
            "name": character.content.get("name", "Unnamed"),
            "time": character.time,
            "distance": character.distance,
            "angle": character.angle,
            "size": math.log(character.content.get("mentions", 1) + 1) * 3,
            "color": "#3498db"  # Blue for characters
        }
        nodes_data.append(node)
        
        # Add connections
        for conn_id in character.connections:
            links_data.append({
                "source": char_id,
                "target": conn_id,
                "value": 1
            })
    
    # Process events
    for event_id, event in atlas.events.items():
        # Map event attributes for visualization
        node = {
            "id": event_id,
            "type": "event",
            "name": event.content.get("description", "Unnamed")[:30] + "...",
            "time": event.time,
            "distance": event.distance,
            "angle": event.angle,
            "size": event.content.get("importance", 0.5) * 5,
            "color": "#e74c3c"  # Red for events
        }
        nodes_data.append(node)
    
    # Process locations
    for loc_id, location in atlas.locations.items():
        # Map location attributes for visualization
        node = {
            "id": loc_id,
            "type": "location",
            "name": location.content.get("name", "Unnamed"),
            "time": location.time,
            "distance": location.distance,
            "angle": location.angle,
            "size": location.content.get("scene_count", 1) * 2,
            "color": "#2ecc71"  # Green for locations
        }
        nodes_data.append(node)
    
    # Process themes
    for theme_id, theme in atlas.themes.items():
        # Map theme attributes for visualization
        node = {
            "id": theme_id,
            "type": "theme",
            "name": theme.content.get("name", "Unnamed"),
            "time": theme.time,
            "distance": theme.distance,
            "angle": theme.angle,
            "size": theme.content.get("instances", 1) * 2,
            "color": "#9b59b6"  # Purple for themes
        }
        nodes_data.append(node)
    
    # Prepare data for visualization
    vis_data = {
        "nodes": nodes_data,
        "links": links_data,
        "metadata": {
            "title": atlas.name,
            "segments": len(atlas.segments),
            "timeline_start": atlas.metrics.get("timeline_start", 0.0),
            "timeline_end": atlas.metrics.get("timeline_end", 0.0),
            "character_count": len(atlas.characters),
            "event_count": len(atlas.events),
            "location_count": len(atlas.locations),
            "theme_count": len(atlas.themes)
        }
    }
    
    # Create HTML visualization
    html = _generate_visualization_html(vis_data)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)

def create_character_arc_visualization(atlas, character_id: str, output_path: str) -> None:
    """
    Create a visualization focused on a single character's arc.
    
    Args:
        atlas: The NarrativeAtlas instance
        character_id: ID of character to focus on
        output_path: Path to save the visualization HTML file
    """
    character = atlas.characters.get(character_id)
    if not character:
        print(f"Character not found: {character_id}")
        return
    
    # Get character arc data
    arc_data = atlas.analyze_character_arc(character_id)
    
    # Prepare visualization data
    events_data = []
    for event in arc_data.get("events", []):
        segment = atlas.get_segment_at_position(event.get("time", 0))
        events_data.append({
            "id": event.get("event_id", ""),
            "description": event.get("description", ""),
            "time": event.get("time", 0),
            "segment_text": segment.get("text", "") if segment else ""
        })
    
    # Create HTML visualization
    html = _generate_character_arc_html(character, events_data, arc_data)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)

def create_narrative_timeline(atlas, output_path: str) -> None:
    """
    Create a timeline visualization of the narrative.
    
    Args:
        atlas: The NarrativeAtlas instance
        output_path: Path to save the visualization HTML file
    """
    # Prepare timeline data
    timeline_data = []
    
    # Add narrative phases
    structure_data = atlas.analyze_narrative_structure()
    phases = structure_data.get("narrative_phases", [])
    
    # Add events to timeline
    for event_id, event in atlas.events.items():
        segment = atlas.get_segment_at_position(event.time)
        timeline_data.append({
            "id": event_id,
            "type": "event",
            "title": event.content.get("description", "")[:50],
            "time": event.time,
            "importance": event.content.get("importance", 0.5),
            "participants": event.content.get("participants", []),
            "segment_text": segment.get("text", "") if segment else ""
        })
    
    # Add character first appearances
    for char_id, character in atlas.characters.items():
        # Find first event with this character
        first_event = None
        first_time = float('inf')
        
        for event_id, event in atlas.events.items():
            if (char_id in event.content.get("participants", []) and 
                event.time < first_time):
                first_time = event.time
                first_event = event_id
        
        if first_event:
            timeline_data.append({
                "id": char_id,
                "type": "character_intro",
                "title": f"Introduction of {character.content.get('name', 'Character')}",
                "time": first_time,
                "character_id": char_id
            })
    
    # Create HTML visualization
    html = _generate_timeline_html(timeline_data, phases, atlas.name)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)

def _generate_visualization_html(vis_data: Dict[str, Any]) -> str:
    """Generate HTML for 3D visualization."""
    # Convert Python data to JSON for JavaScript
    vis_data_json = json.dumps(vis_data)
    
    # Basic HTML template with placeholder for visualization data
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Narrative Atlas: {vis_data['metadata']['title']}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/three@0.132.2/build/three.min.js"></script>
    <script src="https://unpkg.com/three-spritetext@1.6.5/dist/three-spritetext.min.js"></script>
    <script src="https://unpkg.com/three-forcegraph"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #container {{ width: 100%; height: 100vh; }}
        #info-panel {{ 
            position: absolute; 
            top: 10px; 
            left: 10px; 
            background: rgba(255,255,255,0.8); 
            padding: 15px; 
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            max-width: 300px;
        }}
        h1, h2 {{ margin-top: 0; color: #333; }}
        .stat {{ margin: 5px 0; }}
        .legend {{ display: flex; flex-wrap: wrap; margin-top: 10px; }}
        .legend-item {{ 
            display: flex; 
            align-items: center; 
            margin-right: 15px;
            margin-bottom: 5px;
            cursor: pointer;
        }}
        .legend-color {{ 
            width: 15px; 
            height: 15px; 
            margin-right: 5px; 
            border-radius: 50%; 
        }}
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="info-panel">
        <h1>Narrative Atlas</h1>
        <h2>{vis_data['metadata']['title']}</h2>
        <div class="stats">
            <div class="stat">Characters: {vis_data['metadata']['character_count']}</div>
            <div class="stat">Events: {vis_data['metadata']['event_count']}</div>
            <div class="stat">Locations: {vis_data['metadata']['location_count']}</div>
            <div class="stat">Themes: {vis_data['metadata']['theme_count']}</div>
        </div>
        <div class="legend">
            <div class="legend-item" data-type="character">
                <div class="legend-color" style="background-color: #3498db;"></div>
                <div>Characters</div>
            </div>
            <div class="legend-item" data-type="event">
                <div class="legend-color" style="background-color: #e74c3c;"></div>
                <div>Events</div>
            </div>
            <div class="legend-item" data-type="location">
                <div class="legend-color" style="background-color: #2ecc71;"></div>
                <div>Locations</div>
            </div>
            <div class="legend-item" data-type="theme">
                <div class="legend-color" style="background-color: #9b59b6;"></div>
                <div>Themes</div>
            </div>
        </div>
    </div>

    <script>
        // Visualization data
        const data = {vis_data_json};
        
        // Initialize 3D Graph
        const Graph = ForceGraph3D()
            (document.getElementById('container'))
            .graphData(data)
            .nodeId('id')
            .nodeLabel('name')
            .nodeColor('color')
            .nodeVal('size')
            .linkWidth(1)
            .linkOpacity(0.5)
            .backgroundColor('#f7f7f7')
            .showNavInfo(true);
            
        // Add text labels to nodes
        Graph.nodeThreeObject(node => {{
            const sprite = new SpriteText(node.name);
            sprite.color = node.color;
            sprite.textHeight = 4;
            sprite.position.y = node.size + 4;
            return sprite;
        }});
        
        // Position nodes based on cylindrical coordinates
        Graph.nodePositionUpdate((node, pos) => {{
            // Convert cylindrical coordinates to Cartesian
            const radius = node.distance * 100;
            const angle = node.angle * (Math.PI / 180);
            const height = node.time * 20;
            
            return {{
                x: radius * Math.cos(angle),
                y: height,
                z: radius * Math.sin(angle)
            }};
        }});
        
        // Legend toggle functionality
        document.querySelectorAll('.legend-item').forEach(item => {{
            item.addEventListener('click', () => {{
                const type = item.getAttribute('data-type');
                const graphData = Graph.graphData();
                
                // Toggle visibility
                const newNodes = graphData.nodes.map(node => {{
                    if (node.type === type) {{
                        return {{
                            ...node,
                            hidden: !node.hidden
                        }};
                    }}
                    return node;
                }});
                
                Graph.graphData({{
                    nodes: newNodes,
                    links: graphData.links
                }});
                
                // Toggle legend item style
                item.style.opacity = item.style.opacity === '0.5' ? '1' : '0.5';
            }});
        }});
    </script>
</body>
</html>
    """

def _generate_character_arc_html(character, events_data, arc_data):
    """Generate HTML for character arc visualization."""
    # Convert Python data to JSON for JavaScript
    character_data = {
        "name": character.content.get('name', 'Character'),
        "attributes": character.content.get('attributes', [])
    }
    character_json = json.dumps(character_data)
    events_json = json.dumps(events_data)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Character Arc: {character.content.get('name', 'Character')}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; background: #f9f9f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        h2 {{ color: #7f8c8d; font-weight: normal; margin-top: 0; }}
        .arc-viz {{ width: 100%; height: 300px; margin: 30px 0; }}
        .events-container {{ margin-top: 40px; }}
        .event-card {{ 
            background: white; 
            border-radius: 4px; 
            padding: 15px; 
            margin: 15px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .event-title {{ color: #e74c3c; margin-top: 0; }}
        .event-text {{ color: #333; line-height: 1.5; }}
        .timeline {{ 
            position: relative; 
            height: 4px; 
            background: #ddd; 
            margin: 40px 0;
        }}
        .timeline-marker {{ 
            position: absolute; 
            width: 12px; 
            height: 12px; 
            background: #e74c3c; 
            border-radius: 50%; 
            top: -4px; 
            transform: translateX(-50%);
            cursor: pointer;
        }}
        .stats {{ 
            display: flex; 
            flex-wrap: wrap; 
            gap: 20px; 
            margin: 30px 0;
            background: white;
            padding: 15px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stat {{ 
            flex: 1; 
            min-width: 150px;
            padding: 10px; 
            background: #f7f7f7;
            border-radius: 4px;
        }}
        .stat-title {{ color: #7f8c8d; margin: 0; font-size: 14px; }}
        .stat-value {{ color: #2c3e50; margin: 5px 0 0; font-size: 20px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{character.content.get('name', 'Character')}</h1>
        <h2>Character Arc Analysis</h2>
        
        <div class="stats">
            <div class="stat">
                <h3 class="stat-title">Mentions</h3>
                <p class="stat-value">{arc_data.get('mentions', 0)}</p>
            </div>
            <div class="stat">
                <h3 class="stat-title">First Appearance</h3>
                <p class="stat-value">Segment {int(arc_data.get('first_appearance', 0))}</p>
            </div>
            <div class="stat">
                <h3 class="stat-title">Last Appearance</h3>
                <p class="stat-value">Segment {int(arc_data.get('last_appearance', 0))}</p>
            </div>
            <div class="stat">
                <h3 class="stat-title">Location Count</h3>
                <p class="stat-value">{len(arc_data.get('locations', []))}</p>
            </div>
        </div>
        
        <div class="arc-viz" id="arc-viz"></div>
        
        <div class="timeline" id="timeline">
            <!-- Timeline markers will be added dynamically -->
        </div>
        
        <div class="events-container" id="events-container">
            <h2>Character Events</h2>
            <!-- Event cards will be added dynamically -->
        </div>
    </div>

    <script>
        // Character arc data
        const character = {character_json};
        const events = {events_json};
        
        // Create timeline markers
        const timeline = document.getElementById('timeline');
        const timelineWidth = timeline.offsetWidth;
        const maxTime = events.length > 0 ? Math.max(...events.map(e => e.time)) : 0;
        
        events.forEach((event, i) => {{
            const marker = document.createElement('div');
            marker.className = 'timeline-marker';
            marker.setAttribute('data-index', i);
            marker.style.left = `${{(event.time / maxTime) * 100}}%`;
            marker.title = event.description;
            
            marker.addEventListener('click', () => {{
                document.getElementById(`event-${{i}}`).scrollIntoView({{ behavior: 'smooth' }});
            }});
            
            timeline.appendChild(marker);
        }});
        
        // Create event cards
        const eventsContainer = document.getElementById('events-container');
        
        events.forEach((event, i) => {{
            const card = document.createElement('div');
            card.className = 'event-card';
            card.id = `event-${{i}}`;
            
            card.innerHTML = `
                <h3 class="event-title">${{event.description}}</h3>
                <p class="event-text">${{event.segment_text}}</p>
            `;
            
            eventsContainer.appendChild(card);
        }});
        
        // Create arc visualization with D3
        const arcViz = d3.select('#arc-viz');
        const width = arcViz.node().offsetWidth;
        const height = 300;
        
        const svg = arcViz.append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(0, ${{height/2}})`);
            
        // X scale for time
        const x = d3.scaleLinear()
            .domain([0, maxTime])
            .range([0, width]);
            
        // Y scale for importance
        const y = d3.scaleLinear()
            .domain([0, 1])
            .range([50, -50]);
            
        // Create line for character arc
        const line = d3.line()
            .x(d => x(d.time))
            .y(d => y(d.importance || 0.5))
            .curve(d3.curveCatmullRom);
            
        // Add axis
        svg.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', 0)
            .attr('y2', 0)
            .attr('stroke', '#ddd')
            .attr('stroke-width', 1);
            
        // Prepare data points with interpolation
        const points = events.map(event => ({{
            time: event.time,
            importance: 0.5
        }}));
        
        // Draw line
        svg.append('path')
            .datum(points)
            .attr('fill', 'none')
            .attr('stroke', '#3498db')
            .attr('stroke-width', 3)
            .attr('d', line);
            
        // Add points
        svg.selectAll('circle')
            .data(points)
            .enter()
            .append('circle')
            .attr('cx', d => x(d.time))
            .attr('cy', d => y(d.importance))
            .attr('r', 5)
            .attr('fill', '#3498db');
    </script>
</body>
</html>
    """

def _generate_timeline_html(timeline_data, phases, title):
    """Generate HTML for narrative timeline visualization."""
    # Convert Python data to JSON for JavaScript
    timeline_json = json.dumps(timeline_data)
    phases_json = json.dumps(phases)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Narrative Timeline: {title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; background: #f9f9f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        .timeline {{ 
            width: 100%; 
            height: 500px; 
            margin: 30px 0; 
            position: relative;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .phase {{ 
            position: absolute; 
            height: 100%; 
            top: 0; 
            opacity: 0.2; 
        }}
        .phase-label {{ 
            position: absolute; 
            top: 5px; 
            text-align: center; 
            font-weight: bold; 
            color: #333; 
        }}
        .event-point {{ 
            position: absolute; 
            width: 12px; 
            height: 12px; 
            border-radius: 50%; 
            cursor: pointer;
            transform: translate(-50%, -50%);
        }}
        .event-point[data-type="event"] {{ background: #e74c3c; }}
        .event-point[data-type="character_intro"] {{ background: #3498db; }}
        .event-tooltip {{ 
            position: absolute; 
            background: rgba(0,0,0,0.8); 
            color: white; 
            padding: 10px; 
            border-radius: 4px; 
            font-size: 14px; 
            pointer-events: none; 
            opacity: 0; 
            transition: opacity 0.2s; 
            max-width: 250px;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Narrative Timeline: {title}</h1>
        
        <div class="timeline" id="timeline">
            <!-- Will be populated by script -->
        </div>
    </div>

    <script>
        // Timeline data
        const events = {timeline_json};
        const phases = {phases_json};
        
        // Get max time value for scaling
        const maxTime = events.length > 0 ? Math.max(...events.map(e => e.time)) : 0;
        
        // Setup container dimensions
        const timeline = document.getElementById('timeline');
        const width = timeline.offsetWidth - 40; // Account for padding
        const height = timeline.offsetHeight - 40;
        
        // Add narrative phases as background
        phases.forEach(phase => {{
            const phaseEl = document.createElement('div');
            phaseEl.className = 'phase';
            
            // Calculate position based on segments
            const startPercent = (phase.start / maxTime) * 100;
            const endPercent = (phase.end / maxTime) * 100;
            const phaseWidth = endPercent - startPercent;
            
            phaseEl.style.left = `${{startPercent}}%`;
            phaseEl.style.width = `${{phaseWidth}}%`;
            phaseEl.style.backgroundColor = getPhaseColor(phase.name);
            
            // Add label
            const labelEl = document.createElement('div');
            labelEl.className = 'phase-label';
            labelEl.style.left = `${{(startPercent + phaseWidth/2)}}%`;
            labelEl.style.width = `${{phaseWidth}}%`;
            labelEl.textContent = phase.name;
            
            timeline.appendChild(phaseEl);
            timeline.appendChild(labelEl);
        }});
        
        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'event-tooltip';
        document.body.appendChild(tooltip);
        
        // Add event points
        events.forEach(event => {{
            const point = document.createElement('div');
            point.className = 'event-point';
            point.setAttribute('data-type', event.type);
            
            // Position horizontally based on time, vertically based on importance
            const xPos = (event.time / maxTime) * width + 20; // +20 for padding
            
            // For events, use importance; for character intros, use fixed position
            let yPos;
            if (event.type === 'event') {{
                yPos = height - (event.importance * height * 0.6) - 100;
            }} else {{
                yPos = 100; // Position character intros at the top
            }}
            
            point.style.left = `${{xPos}}px`;
            point.style.top = `${{yPos}}px`;
            
            // Add tooltip behavior
            point.addEventListener('mouseover', (e) => {{
                tooltip.textContent = event.title;
                tooltip.style.left = `${{e.pageX + 10}}px`;
                tooltip.style.top = `${{e.pageY + 10}}px`;
                tooltip.style.opacity = '1';
            }});
            
            point.addEventListener('mouseout', () => {{
                tooltip.style.opacity = '0';
            }});
            
            timeline.appendChild(point);
        }});
        
        // Helper function for phase colors
        function getPhaseColor(phaseName) {{
            const colors = {{
                'Exposition': '#3498db',
                'Rising Action': '#2ecc71', 
                'Climax': '#e74c3c',
                'Falling Action': '#f39c12',
                'Resolution': '#9b59b6'
            }};
            return colors[phaseName] || '#ddd';
        }}
    </script>
</body>
</html>
    """

# Add additional visualization functions as needed 
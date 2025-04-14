#!/usr/bin/env python3
"""
Enhanced 3D visualization for narrative structures using Three.js and ForceGraph3D.
"""

import os
import json
import math
from typing import Dict, List, Any, Optional

def create_enhanced_hobbit_visualization(atlas, output_path: str) -> None:
    """
    Create an enhanced interactive 3D visualization of the hobbit narrative structure.
    
    Args:
        atlas: The NarrativeAtlas instance
        output_path: Path to save the visualization HTML file
    """
    # Create data structure for visualization
    nodes_data = []
    links_data = []
    
    # Process characters
    for char_id, character in atlas.characters.items():
        # Filter out common words mistakenly identified as characters
        name = character.content.get("name", "Unnamed")
        common_words = ["the", "and", "but", "he", "it", "they", "there", "in", "of", "to", "a", "was", "had", "you", "that", "this", "not", "for", "his"]
        
        if name.lower() in common_words or len(name) <= 1:
            continue
        
        # Map character attributes for visualization
        node = {
            "id": char_id,
            "type": "character",
            "name": name,
            "time": character.time,
            "distance": character.distance,
            "angle": character.angle,
            "size": math.log(character.content.get("mentions", 1) + 1) * 3,
            "color": "#3498db",  # Blue for characters
            "mentions": character.content.get("mentions", 1),
            "description": character.content.get("description", "")
        }
        nodes_data.append(node)
        
        # Add connections
        for conn_id in character.connections:
            if conn_id in atlas.characters:
                links_data.append({
                    "source": char_id,
                    "target": conn_id,
                    "value": 1
                })
    
    # Process events
    for event_id, event in atlas.events.items():
        # Map event attributes for visualization
        description = event.content.get("description", "Unnamed event")
        node = {
            "id": event_id,
            "type": "event",
            "name": description[:30] + ("..." if len(description) > 30 else ""),
            "time": event.time,
            "distance": event.distance,
            "angle": event.angle,
            "size": event.content.get("importance", 0.5) * 5,
            "color": "#e74c3c",  # Red for events
            "description": description,
            "participants": event.content.get("participants", [])
        }
        nodes_data.append(node)
        
        # Connect events to participating characters
        for participant_id in event.content.get("participants", []):
            if participant_id in atlas.characters:
                links_data.append({
                    "source": event_id,
                    "target": participant_id,
                    "value": 0.5,
                    "type": "participation"
                })
    
    # Process locations
    for loc_id, location in atlas.locations.items():
        # Map location attributes for visualization
        node = {
            "id": loc_id,
            "type": "location",
            "name": location.content.get("name", "Unnamed location"),
            "time": location.time,
            "distance": location.distance,
            "angle": location.angle,
            "size": location.content.get("scene_count", 1) * 2,
            "color": "#2ecc71",  # Green for locations
            "description": location.content.get("description", "")
        }
        nodes_data.append(node)
        
        # Connect locations to events that occurred there
        for event_id, event in atlas.events.items():
            if loc_id in event.content.get("locations", []):
                links_data.append({
                    "source": loc_id,
                    "target": event_id,
                    "value": 0.5,
                    "type": "location"
                })
    
    # Process themes
    for theme_id, theme in atlas.themes.items():
        # Map theme attributes for visualization
        node = {
            "id": theme_id,
            "type": "theme",
            "name": theme.content.get("name", "Unnamed theme"),
            "time": theme.time,
            "distance": theme.distance,
            "angle": theme.angle,
            "size": theme.content.get("instances", 1) * 2,
            "color": "#9b59b6",  # Purple for themes
            "description": theme.content.get("description", "")
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
    html = _generate_enhanced_visualization_html(vis_data)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"Enhanced 3D visualization created: {output_path}")

def _generate_enhanced_visualization_html(vis_data: Dict[str, Any]) -> str:
    """Generate enhanced HTML for 3D visualization."""
    # Convert Python data to JSON for JavaScript
    vis_data_json = json.dumps(vis_data)
    
    # Basic HTML template with placeholder for visualization data
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Narrative Atlas: {vis_data['metadata']['title']}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/three@0.152.2/build/three.min.js"></script>
    <script src="https://unpkg.com/three-spritetext@1.8.0/dist/three-spritetext.min.js"></script>
    <script src="https://unpkg.com/three-forcegraph@1.44.1/dist/three-forcegraph.min.js"></script>
    <script src="https://unpkg.com/three/examples/js/controls/OrbitControls.js"></script>
    <style>
        body {{ 
            margin: 0; 
            padding: 0; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: #f7f9fc;
            color: #333;
            overflow: hidden;
        }}
        #container {{ 
            width: 100%; 
            height: 100vh; 
            position: relative;
        }}
        #info-panel {{ 
            position: absolute; 
            top: 10px; 
            left: 10px; 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            max-width: 350px;
            z-index: 1000;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        #detail-panel {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255,255,255,0.9);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            max-width: 350px;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        #controls-panel {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255,255,255,0.9);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        h1, h2 {{ margin-top: 0; color: #2c3e50; }}
        h3 {{ color: #3498db; margin-bottom: 10px; }}
        .stat {{ margin: 8px 0; font-size: 14px; }}
        .legend {{ display: flex; flex-wrap: wrap; margin-top: 15px; }}
        .legend-item {{ 
            display: flex; 
            align-items: center; 
            margin-right: 15px;
            margin-bottom: 8px;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 20px;
            transition: background-color 0.2s ease;
        }}
        .legend-item:hover {{ 
            background-color: rgba(0,0,0,0.05);
        }}
        .legend-item.disabled {{
            opacity: 0.5;
        }}
        .legend-color {{ 
            width: 15px; 
            height: 15px; 
            margin-right: 8px; 
            border-radius: 50%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .panel-toggle {{
            cursor: pointer;
            position: absolute;
            bottom: 10px;
            right: 10px;
            padding: 5px 10px;
            background: rgba(255,255,255,0.8);
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }}
        .control-group {{
            margin-bottom: 12px;
        }}
        .control-label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        .slider {{
            width: 100%;
            margin: 5px 0;
        }}
        button {{
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
            transition: background-color 0.2s ease;
        }}
        button:hover {{
            background-color: #2980b9;
        }}
        .detail-label {{
            font-weight: bold;
            margin-right: 5px;
            color: #555;
        }}
        .detail-value {{
            color: #333;
        }}
        .detail-item {{
            margin-bottom: 10px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-right: 5px;
            margin-bottom: 5px;
            color: white;
        }}
        .badge.character {{
            background-color: #3498db;
        }}
        .badge.event {{
            background-color: #e74c3c;
        }}
        .badge.location {{
            background-color: #2ecc71;
        }}
        .badge.theme {{
            background-color: #9b59b6;
        }}
        .timeline {{
            position: absolute;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            height: 30px;
            background: rgba(255,255,255,0.9);
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
            display: flex;
            align-items: center;
            padding: 0 15px;
            z-index: 900;
        }}
        .timeline-slider {{
            width: 100%;
        }}
        .chapter-marker {{
            position: absolute;
            width: 2px;
            background-color: rgba(0,0,0,0.3);
            height: 10px;
            bottom: 0;
            cursor: pointer;
        }}
        #loader {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255,255,255,0.9);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 1100;
            transition: opacity 0.5s ease;
        }}
        .spinner {{
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div id="loader">
        <div class="spinner"></div>
        <h2>Loading The Hobbit visualization...</h2>
        <p>Preparing narrative structure elements</p>
    </div>

    <div id="container"></div>
    
    <div id="info-panel">
        <h1>Narrative Atlas</h1>
        <h2>{vis_data['metadata']['title'].replace("_", " ").title()}</h2>
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
        <div class="panel-toggle">Hide Panel</div>
    </div>
    
    <div id="detail-panel">
        <h2>Node Details</h2>
        <div id="detail-content"></div>
    </div>
    
    <div id="controls-panel">
        <div class="control-group">
            <span class="control-label">Node Size:</span>
            <input type="range" min="0.5" max="2" step="0.1" value="1" class="slider" id="size-slider">
        </div>
        <div class="control-group">
            <span class="control-label">Link Opacity:</span>
            <input type="range" min="0.1" max="1" step="0.1" value="0.5" class="slider" id="link-opacity-slider">
        </div>
        <div class="control-group">
            <button id="reset-view">Reset View</button>
            <button id="focus-main">Focus Main Characters</button>
        </div>
    </div>
    
    <div class="timeline">
        <input type="range" min="0" max="100" value="0" class="timeline-slider" id="time-slider">
    </div>

    <script>
        // Visualization data
        const data = {vis_data_json};
        
        // Wait for all resources to load
        window.addEventListener('load', () => {{
            setTimeout(() => {{
                document.getElementById('loader').style.opacity = '0';
                setTimeout(() => {{
                    document.getElementById('loader').style.display = 'none';
                }}, 500);
            }}, 1000);
        }});
        
        // Initial setup
        let nodeScale = 1;
        let selectedNodeId = null;
        let timelineValue = 0;
        let filteredNodes = [];
        
        // Initialize 3D Graph
        const Graph = ForceGraph3D()
            (document.getElementById('container'))
            .graphData(data)
            .nodeId('id')
            .nodeLabel('name')
            .nodeColor(node => node.color)
            .nodeVal(node => node.size * nodeScale)
            .linkWidth(1)
            .linkOpacity(0.5)
            .backgroundColor('#f7f9fc')
            .showNavInfo(true);
            
        // Add text labels to nodes
        Graph.nodeThreeObject(node => {{
            const group = new THREE.Group();
            
            // Add sprite for text label
            const sprite = new SpriteText(node.name);
            sprite.color = node.color;
            sprite.textHeight = 4;
            sprite.position.y = (node.size * nodeScale) + 4;
            
            // Create custom material for glow effect
            const geometry = new THREE.SphereGeometry(node.size * nodeScale, 32, 32);
            const material = new THREE.MeshLambertMaterial({{ 
                color: node.color,
                transparent: true,
                opacity: 0.7
            }});
            
            const mesh = new THREE.Mesh(geometry, material);
            
            group.add(mesh);
            group.add(sprite);
            
            return group;
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
        
        // Handle node click event
        Graph.onNodeClick(node => {{
            if (selectedNodeId === node.id) {{
                // Deselect if clicking the same node
                selectedNodeId = null;
                document.getElementById('detail-panel').style.display = 'none';
            }} else {{
                // Select new node
                selectedNodeId = node.id;
                updateDetailPanel(node);
                document.getElementById('detail-panel').style.display = 'block';
            }}
        }});
        
        // Update detail panel with node information
        function updateDetailPanel(node) {{
            const detailContent = document.getElementById('detail-content');
            let html = '';
            
            html += `<div class="detail-item"><span class="badge ${{node.type}}">${{node.type.toUpperCase()}}</span></div>`;
            html += `<div class="detail-item"><h3>${{node.name}}</h3></div>`;
            
            if (node.description) {{
                html += `<div class="detail-item">
                    <span class="detail-label">Description:</span>
                    <div class="detail-value">${{node.description}}</div>
                </div>`;
            }}
            
            html += `<div class="detail-item">
                <span class="detail-label">Time:</span>
                <span class="detail-value">${{node.time.toFixed(2)}}</span>
            </div>`;
            
            html += `<div class="detail-item">
                <span class="detail-label">Distance:</span>
                <span class="detail-value">${{node.distance.toFixed(2)}}</span>
            </div>`;
            
            html += `<div class="detail-item">
                <span class="detail-label">Angle:</span>
                <span class="detail-value">${{node.angle.toFixed(2)}}°</span>
            </div>`;
            
            if (node.type === 'character' && node.mentions) {{
                html += `<div class="detail-item">
                    <span class="detail-label">Mentions:</span>
                    <span class="detail-value">${{node.mentions}}</span>
                </div>`;
            }}
            
            if (node.type === 'event' && node.participants && node.participants.length > 0) {{
                html += `<div class="detail-item">
                    <span class="detail-label">Participants:</span>
                    <div class="detail-value">`;
                
                // Find character names for participant IDs
                node.participants.forEach(participantId => {{
                    const character = data.nodes.find(n => n.id === participantId);
                    if (character) {{
                        html += `<span class="badge character">${{character.name}}</span>`;
                    }}
                }});
                
                html += `</div></div>`;
            }}
            
            html += `<div class="detail-item">
                <button id="focus-node">Focus on this node</button>
            </div>`;
            
            detailContent.innerHTML = html;
            
            // Add event listener for focus button
            document.getElementById('focus-node').addEventListener('click', () => {{
                // Calculate position based on node's coordinates
                const radius = node.distance * 100;
                const angle = node.angle * (Math.PI / 180);
                const height = node.time * 20;
                
                const x = radius * Math.cos(angle);
                const y = height;
                const z = radius * Math.sin(angle);
                
                // Set camera position to focus on this node
                Graph.cameraPosition(
                    {{ x: x + 200, y: y, z: z + 200 }}, // new position
                    {{ x, y, z }}, // lookAt position
                    2000 // transition duration
                );
            }});
        }}
        
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
                item.classList.toggle('disabled');
            }});
        }});
        
        // Timeline slider functionality
        document.getElementById('time-slider').addEventListener('input', (e) => {{
            const timeValue = parseFloat(e.target.value) / 100;
            timelineValue = timeValue;
            
            const maxTime = Math.max(...data.nodes.map(node => node.time));
            const currentTime = maxTime * timeValue;
            
            // Filter nodes by time
            const graphData = Graph.graphData();
            const visibleNodes = data.nodes.filter(node => node.time <= currentTime);
            const visibleNodeIds = new Set(visibleNodes.map(node => node.id));
            
            // Filter links - only include links where both source and target are visible
            const visibleLinks = data.links.filter(link => 
                visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target)
            );
            
            // Update the graph with filtered data
            Graph.graphData({{
                nodes: visibleNodes,
                links: visibleLinks
            }});
        }});
        
        // Control panel sliders
        document.getElementById('size-slider').addEventListener('input', (e) => {{
            nodeScale = parseFloat(e.target.value);
            Graph.nodeVal(node => node.size * nodeScale);
            Graph.nodeThreeObject(null).nodeThreeObject(node => {{
                const group = new THREE.Group();
                
                const sprite = new SpriteText(node.name);
                sprite.color = node.color;
                sprite.textHeight = 4;
                sprite.position.y = (node.size * nodeScale) + 4;
                
                const geometry = new THREE.SphereGeometry(node.size * nodeScale, 32, 32);
                const material = new THREE.MeshLambertMaterial({{ 
                    color: node.color,
                    transparent: true,
                    opacity: 0.7
                }});
                
                const mesh = new THREE.Mesh(geometry, material);
                
                group.add(mesh);
                group.add(sprite);
                
                return group;
            }});
        }});
        
        document.getElementById('link-opacity-slider').addEventListener('input', (e) => {{
            const opacity = parseFloat(e.target.value);
            Graph.linkOpacity(opacity);
        }});
        
        // Reset view button
        document.getElementById('reset-view').addEventListener('click', () => {{
            Graph.cameraPosition(
                {{ x: 0, y: 0, z: 400 }}, // default position
                {{ x: 0, y: 0, z: 0 }}, // lookAt
                1000 // transition duration
            );
        }});
        
        // Focus main characters button
        document.getElementById('focus-main').addEventListener('click', () => {{
            // Find top 5 characters by mentions
            const mainCharacters = data.nodes
                .filter(node => node.type === 'character')
                .sort((a, b) => (b.mentions || 0) - (a.mentions || 0))
                .slice(0, 5);
            
            if (mainCharacters.length > 0) {{
                // Calculate average position
                let avgX = 0, avgY = 0, avgZ = 0;
                
                mainCharacters.forEach(char => {{
                    const radius = char.distance * 100;
                    const angle = char.angle * (Math.PI / 180);
                    const height = char.time * 20;
                    
                    avgX += radius * Math.cos(angle);
                    avgY += height;
                    avgZ += radius * Math.sin(angle);
                }});
                
                avgX /= mainCharacters.length;
                avgY /= mainCharacters.length;
                avgZ /= mainCharacters.length;
                
                // Set camera to focus on main characters
                Graph.cameraPosition(
                    {{ x: avgX, y: avgY, z: avgZ + 300 }},
                    {{ x: avgX, y: avgY, z: avgZ }},
                    1500
                );
            }}
        }});
        
        // Panel toggle functionality
        document.querySelector('#info-panel .panel-toggle').addEventListener('click', function() {{
            const panel = document.getElementById('info-panel');
            const statsSection = panel.querySelector('.stats');
            const legendSection = panel.querySelector('.legend');
            
            if (this.textContent === 'Hide Panel') {{
                statsSection.style.display = 'none';
                legendSection.style.display = 'none';
                this.textContent = 'Show Panel';
            }} else {{
                statsSection.style.display = 'block';
                legendSection.style.display = 'flex';
                this.textContent = 'Hide Panel';
            }}
        }});
        
        // Initialize with a reasonably positioned camera
        setTimeout(() => {{
            Graph.cameraPosition(
                {{ x: 0, y: 0, z: 400 }},
                {{ x: 0, y: 0, z: 0 }},
                0
            );
        }}, 1000);
    </script>
</body>
</html>""" 
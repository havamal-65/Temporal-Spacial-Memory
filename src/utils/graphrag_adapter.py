#!/usr/bin/env python3
"""
GraphRAG Adapter - Integrates GraphRAG with Temporal-Spatial Memory

This module provides adapters to convert between GraphRAG's knowledge graph
representation and the cylindrical coordinate system used by Temporal-Spatial Memory.
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from pathlib import Path

# GraphRAG imports
import graphrag.api as graphrag_api
from graphrag.config.load_config import load_config
from graphrag.config.models.graph_rag_config import GraphRagConfig

# Temporal-Spatial Memory imports
from ..models.mesh_node import MeshNode
from ..models.narrative_nodes import CharacterNode, LocationNode, EventNode, ThemeNode

class GraphRAGAdapter:
    """
    Adapter class that bridges GraphRAG with Temporal-Spatial Memory system.
    """
    
    def __init__(self, project_name: str = "narrative_project"):
        """
        Initialize the GraphRAG adapter.
        
        Args:
            project_name: Name to use for the GraphRAG project
        """
        self.project_name = project_name
        self.project_dir = Path(f"data/{project_name}")
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize config
        self.config = self._initialize_config()
        
    def _initialize_config(self) -> GraphRagConfig:
        """Initialize GraphRAG configuration."""
        # Check if the project already has a config
        config_path = self.project_dir / "settings.yaml"
        
        if config_path.exists():
            return load_config(self.project_dir)
        
        # Create a new configuration using CLI
        from subprocess import run
        result = run(
            ["graphrag", "init", str(self.project_dir.absolute())],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error initializing GraphRAG: {result.stderr}")
            raise RuntimeError("Failed to initialize GraphRAG")
            
        # Load the newly created config
        return load_config(self.project_dir)
        
    def extract_knowledge_graph(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process text with GraphRAG to extract a knowledge graph.
        
        Args:
            text: The narrative text to process
            metadata: Additional metadata about the narrative
            
        Returns:
            GraphRAG knowledge graph
        """
        if metadata is None:
            metadata = {"type": "narrative", "temporal_structure": "linear"}
        
        # Write text to file for GraphRAG to process
        text_path = self.project_dir / "input.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Process text with GraphRAG API
        print("Extracting knowledge graph with GraphRAG...")
        result = graphrag_api.build_index(
            str(self.project_dir),
            verbose=True,
            cache=True
        )
        
        # Extract the knowledge graph from the result
        knowledge_graph = {
            "nodes": result.get("entities", []),
            "edges": result.get("relationships", [])
        }
        
        return knowledge_graph
    
    def convert_to_mesh_nodes(self, knowledge_graph: Dict[str, Any]) -> List[MeshNode]:
        """
        Convert GraphRAG knowledge graph to temporal-spatial mesh nodes.
        
        Args:
            knowledge_graph: GraphRAG knowledge graph
            
        Returns:
            List of MeshNode objects
        """
        mesh_nodes = []
        
        # Track entities by type for building relationships
        entity_nodes = {
            "character": {},
            "location": {},
            "event": {},
            "theme": {}
        }
        
        # First pass: Create mesh nodes for all entities
        for node in knowledge_graph.get("nodes", []):
            node_type = self._determine_node_type(node)
            node_id = node.get("id", "")
            name = node.get("label", "")
            
            # Calculate cylindrical coordinates
            time = node.get("metadata", {}).get("position_in_narrative", 0.0)
            
            # Map centrality to distance (more central = closer to core axis)
            centrality = node.get("metadata", {}).get("centrality", 0.5)
            distance = 1.0 - centrality  # Invert so important entities are closer to center
            
            # Calculate angular position based on entity type and other properties
            angle = self._calculate_thematic_angle(node)
            
            # Create the appropriate node type
            if node_type == "character":
                mesh_node = CharacterNode(
                    node_id=node_id,
                    name=name,
                    time=time,
                    distance=distance,
                    angle=angle
                )
                entity_nodes["character"][node_id] = mesh_node
                
            elif node_type == "location":
                mesh_node = LocationNode(
                    node_id=node_id,
                    name=name,
                    time=time,
                    distance=distance,
                    angle=angle
                )
                entity_nodes["location"][node_id] = mesh_node
                
            elif node_type == "event":
                mesh_node = EventNode(
                    node_id=node_id,
                    name=name,
                    time=time,
                    distance=distance,
                    angle=angle
                )
                entity_nodes["event"][node_id] = mesh_node
                
            elif node_type == "theme":
                mesh_node = ThemeNode(
                    node_id=node_id,
                    name=name,
                    time=time,
                    distance=distance,
                    angle=angle
                )
                entity_nodes["theme"][node_id] = mesh_node
            
            else:
                # Generic mesh node for other types
                mesh_node = MeshNode(
                    time=time,
                    distance=distance,
                    angle=angle,
                    content={
                        "name": name,
                        "type": node_type,
                        "properties": node.get("properties", {})
                    }
                )
            
            mesh_nodes.append(mesh_node)
        
        # Second pass: Process relationships from edges
        for edge in knowledge_graph.get("edges", []):
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")
            relation_type = edge.get("label", "")
            
            # Find the source and target nodes
            source_node = None
            target_node = None
            
            # Look for source and target in all entity types
            for entity_type in entity_nodes:
                if source_id in entity_nodes[entity_type]:
                    source_node = entity_nodes[entity_type][source_id]
                if target_id in entity_nodes[entity_type]:
                    target_node = entity_nodes[entity_type][target_id]
            
            # Add relationship if both nodes were found
            if source_node and target_node:
                # Get the temporal properties of the relationship
                time_start = edge.get("metadata", {}).get("time_start", source_node.time)
                time_end = edge.get("metadata", {}).get("time_end", target_node.time)
                
                # Add relationship to source node
                source_node.add_relationship(
                    target_id=target_node.node_id,
                    relationship_type=relation_type,
                    properties={
                        "time_start": time_start,
                        "time_end": time_end,
                        "weight": edge.get("weight", 1.0)
                    }
                )
        
        return mesh_nodes
    
    def _determine_node_type(self, node: Dict[str, Any]) -> str:
        """
        Determine the node type from GraphRAG node properties.
        
        Args:
            node: GraphRAG node
            
        Returns:
            Node type (character, location, event, theme, or other)
        """
        # Check if node has an explicit type property
        if "type" in node:
            node_type = node["type"].lower()
            if node_type in ["character", "person", "protagonist", "antagonist"]:
                return "character"
            elif node_type in ["location", "place", "setting"]:
                return "location"
            elif node_type in ["event", "action", "happening"]:
                return "event"
            elif node_type in ["theme", "concept", "idea"]:
                return "theme"
        
        # Infer from properties or labels
        label = node.get("label", "").lower()
        properties = node.get("properties", {})
        
        # Common patterns for character names (proper names, titles)
        if re.match(r'^[A-Z][a-z]+( [A-Z][a-z]+)*$', node.get("label", "")):
            return "character"
        
        # Location often has geographic properties
        if "coordinates" in properties or "region" in properties:
            return "location"
        
        # Events often have temporal properties
        if "date" in properties or "duration" in properties:
            return "event"
        
        # Default to generic type
        return "entity"
    
    def _calculate_thematic_angle(self, node: Dict[str, Any]) -> float:
        """
        Calculate the angular position based on thematic clustering.
        
        Args:
            node: GraphRAG node
            
        Returns:
            Angular position in radians (0 to 2π)
        """
        # This is a simplified approach - in a real implementation, 
        # we would use thematic clustering or embeddings to position
        # related entities at similar angular positions
        
        # Use node properties to calculate a hash-based angle
        name = node.get("label", "")
        node_type = self._determine_node_type(node)
        
        # Different types get different base angles
        type_offsets = {
            "character": 0.0,
            "location": np.pi/2,  # 90 degrees
            "event": np.pi,       # 180 degrees
            "theme": 3*np.pi/2    # 270 degrees
        }
        
        # Get base angle for type
        base_angle = type_offsets.get(node_type, 0.0)
        
        # Calculate a consistent hash-based offset (0-0.5)
        name_hash = hash(name) % 1000 / 1000.0 * 0.5
        
        # Combine base angle with hash offset
        angle = base_angle + name_hash
        
        # Ensure angle is in [0, 2π)
        return angle % (2 * np.pi) 
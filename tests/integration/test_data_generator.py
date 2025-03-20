"""
Test data generator for integration tests.

This module provides utilities for generating realistic test data
for the Temporal-Spatial Knowledge Database.
"""

import math
import time
import copy
import uuid
import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from src.core.node_v2 import Node


class TestDataGenerator:
    def __init__(self, seed: int = 42):
        """
        Initialize test data generator
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        self.categories = [
            "science", "art", "history", "technology", 
            "philosophy", "mathematics", "literature"
        ]
        self.tags = [
            "important", "reviewed", "verified", "draft", 
            "hypothesis", "theory", "observation", "experiment",
            "reference", "primary", "secondary", "tertiary"
        ]
        
    def generate_node(self, 
                     position: Optional[Tuple[float, float, float]] = None,
                     content_complexity: str = "medium") -> Node:
        """
        Generate a test node
        
        Args:
            position: Optional (t, r, θ) position, random if None
            content_complexity: 'simple', 'medium', or 'complex'
            
        Returns:
            A randomly generated node
        """
        # Generate position if not provided
        if position is None:
            t = self.random.uniform(0, 100)
            r = self.random.uniform(0, 10)
            theta = self.random.uniform(0, 2 * math.pi)
            position = (t, r, theta)
            
        # Generate content based on complexity
        content = self._generate_content(content_complexity)
        
        # Create node
        return Node(
            id=uuid4(),
            content=content,
            position=position,
            connections=[]
        )
        
    def generate_node_cluster(self,
                             center: Tuple[float, float, float],
                             radius: float,
                             count: int,
                             time_variance: float = 1.0) -> List[Node]:
        """
        Generate a cluster of related nodes
        
        Args:
            center: Central position (t, r, θ)
            radius: Maximum distance from center
            count: Number of nodes to generate
            time_variance: Variation in time dimension
            
        Returns:
            List of generated nodes
        """
        nodes = []
        base_t, base_r, base_theta = center
        
        for _ in range(count):
            # Generate position with gaussian distribution around center
            t_offset = self.random.gauss(0, time_variance)
            r_offset = self.random.gauss(0, radius/3)  # 3-sigma within radius
            theta_offset = self.random.gauss(0, radius/(3 * base_r)) if base_r > 0 else self.random.uniform(0, 2 * math.pi)
            
            # Calculate new position
            t = base_t + t_offset
            r = max(0, base_r + r_offset)  # Ensure r is non-negative
            theta = (base_theta + theta_offset) % (2 * math.pi)  # Wrap to [0, 2π)
            
            # Create node
            node = self.generate_node(position=(t, r, theta))
            nodes.append(node)
            
        return nodes
        
    def generate_evolving_node_sequence(self,
                                       base_position: Tuple[float, float, float],
                                       num_evolution_steps: int,
                                       time_step: float = 1.0,
                                       change_magnitude: float = 0.2) -> List[Node]:
        """
        Generate a sequence of nodes that represent evolution of a concept
        
        Args:
            base_position: Starting position (t, r, θ)
            num_evolution_steps: Number of evolution steps
            time_step: Time increment between steps
            change_magnitude: How much the content changes per step
        
        Returns:
            List of nodes in temporal sequence
        """
        nodes = []
        base_t, base_r, base_theta = base_position
        
        # Generate base node
        base_node = self.generate_node(position=base_position)
        nodes.append(base_node)
        
        # Track content for incremental changes
        current_content = copy.deepcopy(base_node.content)
        
        # Generate evolution
        for i in range(1, num_evolution_steps):
            # Update position
            t = base_t + i * time_step
            r = base_r + self.random.uniform(-0.1, 0.1) * i  # Slight variation in relevance
            theta = base_theta + self.random.uniform(-0.05, 0.05) * i  # Slight conceptual drift
            
            # Update content
            current_content = self._evolve_content(current_content, change_magnitude)
            
            # Create node
            node = Node(
                id=uuid4(),
                content=current_content,
                position=(t, r, theta),
                connections=[],
                origin_reference=base_node.id
            )
            nodes.append(node)
            
        return nodes
        
    def _generate_content(self, complexity: str) -> Dict[str, Any]:
        """Generate content with specified complexity"""
        if complexity == "simple":
            return {
                "title": self._random_title(),
                "description": self._random_paragraph()
            }
        elif complexity == "medium":
            return {
                "title": self._random_title(),
                "description": self._random_paragraph(),
                "attributes": {
                    "category": self._random_category(),
                    "tags": self._random_tags(3),
                    "importance": self.random.uniform(0, 1)
                },
                "related_info": self._random_paragraph()
            }
        else:  # complex
            return {
                "title": self._random_title(),
                "description": self._random_paragraph(),
                "attributes": {
                    "category": self._random_category(),
                    "tags": self._random_tags(5),
                    "importance": self.random.uniform(0, 1),
                    "metadata": {
                        "created_at": time.time(),
                        "version": f"1.{self.random.randint(0, 10)}",
                        "status": self._random_choice(["draft", "review", "approved", "published"])
                    }
                },
                "sections": [
                    {
                        "heading": self._random_title(),
                        "content": self._random_paragraph(),
                        "subsections": [
                            {
                                "heading": self._random_title(),
                                "content": self._random_paragraph()
                            } for _ in range(self.random.randint(1, 3))
                        ]
                    } for _ in range(self.random.randint(2, 4))
                ],
                "related_info": self._random_paragraph()
            }
            
    def _evolve_content(self, content: Dict[str, Any], magnitude: float) -> Dict[str, Any]:
        """Create an evolved version of the content"""
        # Make a deep copy of the content
        evolved = copy.deepcopy(content)
        
        # Evolve title with probability based on magnitude
        if self.random.random() < magnitude:
            evolved["title"] = self._modify_text(evolved["title"])
            
        # Evolve description with higher probability
        if self.random.random() < magnitude * 1.5:
            evolved["description"] = self._modify_text(evolved["description"])
            
        # Evolve attributes if they exist
        if "attributes" in evolved:
            # Maybe change category
            if self.random.random() < magnitude / 2:
                evolved["attributes"]["category"] = self._random_category()
                
            # Maybe update tags
            if self.random.random() < magnitude:
                current_tags = evolved["attributes"]["tags"]
                if self.random.random() < 0.5:
                    # Add a tag
                    new_tag = self._random_choice(self.tags)
                    if new_tag not in current_tags:
                        current_tags.append(new_tag)
                else:
                    # Remove a tag if there are any
                    if current_tags:
                        current_tags.remove(self.random.choice(current_tags))
                        
            # Update importance
            evolved["attributes"]["importance"] = min(1.0, max(0.0, 
                evolved["attributes"]["importance"] + self.random.uniform(-0.1, 0.1) * magnitude))
                
            # Update metadata if it exists
            if "metadata" in evolved["attributes"]:
                # Update timestamp
                evolved["attributes"]["metadata"]["created_at"] = time.time()
                
                # Maybe update version
                if self.random.random() < magnitude:
                    version_parts = evolved["attributes"]["metadata"]["version"].split(".")
                    minor_version = int(version_parts[1]) + 1
                    evolved["attributes"]["metadata"]["version"] = f"{version_parts[0]}.{minor_version}"
                    
                # Maybe update status
                if self.random.random() < magnitude / 2:
                    statuses = ["draft", "review", "approved", "published"]
                    current_idx = statuses.index(evolved["attributes"]["metadata"]["status"])
                    new_idx = min(len(statuses) - 1, current_idx + 1)  # Progress status forward
                    evolved["attributes"]["metadata"]["status"] = statuses[new_idx]
                    
        # Evolve sections if they exist
        if "sections" in evolved:
            for section in evolved["sections"]:
                # Maybe update heading
                if self.random.random() < magnitude:
                    section["heading"] = self._modify_text(section["heading"])
                    
                # Maybe update content
                if self.random.random() < magnitude * 1.2:
                    section["content"] = self._modify_text(section["content"])
                    
                # Maybe update subsections
                if "subsections" in section:
                    for subsection in section["subsections"]:
                        if self.random.random() < magnitude:
                            subsection["heading"] = self._modify_text(subsection["heading"])
                        if self.random.random() < magnitude * 1.2:
                            subsection["content"] = self._modify_text(subsection["content"])
        
        # Evolve related info if it exists
        if "related_info" in evolved and self.random.random() < magnitude:
            evolved["related_info"] = self._modify_text(evolved["related_info"])
            
        return evolved
        
    def _modify_text(self, text: str) -> str:
        """Make small modifications to text"""
        words = text.split()
        
        # Choose a modification type
        mod_type = self.random.random()
        
        if mod_type < 0.3 and len(words) > 3:
            # Remove a random word
            del words[self.random.randint(0, len(words) - 1)]
        elif mod_type < 0.6:
            # Add a random word
            words.insert(
                self.random.randint(0, len(words)),
                self.random.choice([
                    "important", "significant", "notable", "key", "critical",
                    "minor", "subtle", "nuanced", "complex", "simple", 
                    "interesting", "remarkable", "curious", "unusual", "common"
                ])
            )
        else:
            # Replace a random word
            if words:
                words[self.random.randint(0, len(words) - 1)] = self.random.choice([
                    "concept", "idea", "theory", "hypothesis", "observation",
                    "experiment", "result", "conclusion", "analysis", "interpretation",
                    "framework", "model", "approach", "technique", "method"
                ])
                
        return " ".join(words)
        
    def _random_title(self) -> str:
        """Generate a random title"""
        prefixes = [
            "Analysis of", "Introduction to", "Theory of", "Reflections on", 
            "Investigation of", "Principles of", "Foundations of", "Explorations in",
            "Developments in", "Advances in", "Perspectives on", "Insights into"
        ]
        
        subjects = [
            "Temporal Knowledge", "Spatial Reasoning", "Information Systems",
            "Knowledge Representation", "Conceptual Frameworks", "Data Structures",
            "Learning Models", "Cognitive Processes", "Analytical Methods",
            "Historical Patterns", "Theoretical Constructs", "Complex Systems"
        ]
        
        return f"{self.random.choice(prefixes)} {self.random.choice(subjects)}"
        
    def _random_paragraph(self) -> str:
        """Generate a random paragraph"""
        num_sentences = self.random.randint(3, 8)
        sentences = []
        
        sentence_starters = [
            "This concept involves", "The theory suggests", "Research indicates",
            "Evidence demonstrates", "Experts believe", "Studies show",
            "The framework proposes", "Analysis reveals", "The model predicts",
            "Observations confirm", "The hypothesis states", "Recent findings suggest"
        ]
        
        sentence_middles = [
            "the relationship between", "the interaction of", "the importance of",
            "significant developments in", "a novel approach to", "fundamental principles of",
            "key characteristics of", "essential elements in", "critical factors affecting",
            "underlying mechanisms of", "practical applications of", "theoretical foundations of"
        ]
        
        sentence_objects = [
            "temporal knowledge structures", "spatial relationships", "information systems",
            "conceptual frameworks", "data representations", "learning algorithms",
            "cognitive processes", "analytical methods", "historical patterns",
            "theoretical constructs", "complex systems", "knowledge domains"
        ]
        
        sentence_endings = [
            "across different domains.", "in various contexts.", "under specific conditions.",
            "with important implications.", "leading to new insights.", "challenging existing paradigms.",
            "supporting the main hypothesis.", "extending previous findings.", "inspiring future research.",
            "with practical applications.", "in theoretical frameworks.", "within larger systems."
        ]
        
        for _ in range(num_sentences):
            sentence = (
                f"{self.random.choice(sentence_starters)} "
                f"{self.random.choice(sentence_middles)} "
                f"{self.random.choice(sentence_objects)} "
                f"{self.random.choice(sentence_endings)}"
            )
            sentences.append(sentence)
            
        return " ".join(sentences)
        
    def _random_tags(self, count: int) -> List[str]:
        """Generate random tags"""
        return self.random.sample(self.tags, min(count, len(self.tags)))
        
    def _random_category(self) -> str:
        """Generate random category"""
        return self.random.choice(self.categories)
        
    def _random_choice(self, options: List[Any]) -> Any:
        """Choose random element"""
        return self.random.choice(options) 
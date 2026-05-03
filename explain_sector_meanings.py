#!/usr/bin/env python3
"""
Explain Sector Meanings and Usage

Demonstrates what each compass direction means in the context of 
semantic content organization and how different types of content
naturally cluster in different sectors.
"""

import sys
import os
import numpy as np
import math

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.angular_sector_system import create_compass_32_system

def explain_compass_directions():
    """Explain what each compass direction represents."""
    
    print("🧭 COMPASS DIRECTION MEANINGS")
    print("=" * 60)
    
    # Create compass system
    compass = create_compass_32_system()
    
    # Semantic interpretations for each major direction
    direction_meanings = {
        "N": {
            "semantic": "Action, Adventure, Movement",
            "content_types": ["Adventure stories", "Action narratives", "Journey descriptions", "Quest content"],
            "angle_range": "337.5° - 22.5°",
            "characteristics": "Dynamic, forward-moving, goal-oriented content"
        },
        "NE": {
            "semantic": "Technical, Instructional, How-to",
            "content_types": ["Technical manuals", "Tutorials", "Instructions", "Engineering content"],
            "angle_range": "22.5° - 67.5°", 
            "characteristics": "Practical, solution-oriented, step-by-step content"
        },
        "E": {
            "semantic": "Scientific, Analytical, Data",
            "content_types": ["Scientific papers", "Research", "Data analysis", "Factual content"],
            "angle_range": "67.5° - 112.5°",
            "characteristics": "Objective, evidence-based, analytical content"
        },
        "SE": {
            "semantic": "Educational, Reference, Information",
            "content_types": ["Encyclopedias", "Reference materials", "Educational content", "Definitions"],
            "angle_range": "112.5° - 157.5°",
            "characteristics": "Informative, educational, knowledge-building content"
        },
        "S": {
            "semantic": "Creative, Artistic, Expressive",
            "content_types": ["Poetry", "Creative writing", "Art descriptions", "Musical content"],
            "angle_range": "157.5° - 202.5°",
            "characteristics": "Emotional, creative, subjective, artistic content"
        },
        "SW": {
            "semantic": "Personal, Lifestyle, Practical Living",
            "content_types": ["Recipes", "Life advice", "Personal stories", "Lifestyle content"],
            "angle_range": "202.5° - 247.5°",
            "characteristics": "Personal, relatable, everyday life content"
        },
        "W": {
            "semantic": "Historical, Past-focused, Reflective",
            "content_types": ["Historical accounts", "Memoirs", "Past events", "Legacy content"],
            "angle_range": "247.5° - 292.5°",
            "characteristics": "Retrospective, time-oriented, contextual content"
        },
        "NW": {
            "semantic": "Philosophical, Theoretical, Abstract",
            "content_types": ["Philosophy", "Theory", "Abstract concepts", "Contemplative content"],
            "angle_range": "292.5° - 337.5°",
            "characteristics": "Conceptual, theoretical, thought-provoking content"
        }
    }
    
    for direction, info in direction_meanings.items():
        print(f"\n📍 {direction} - {info['semantic']}")
        print(f"   Angle Range: {info['angle_range']}")
        print(f"   Content Types: {', '.join(info['content_types'])}")
        print(f"   Character: {info['characteristics']}")


def demonstrate_content_clustering():
    """Show how different content types cluster in sectors."""
    
    print("\n\n🎯 CONTENT CLUSTERING BY SECTOR")
    print("=" * 60)
    
    # Simulate how different content might be distributed
    content_examples = [
        # Adventure/Action content (North)
        ("The hero embarked on a dangerous quest", "N", "Adventure narrative"),
        ("Step-by-step guide to assembling the device", "NE", "Technical instruction"),
        ("Statistical analysis reveals significant correlation", "E", "Scientific analysis"),
        
        # Educational content (Southeast)  
        ("Photosynthesis is the process by which plants", "SE", "Educational explanation"),
        ("In moonlit gardens, shadows dance with grace", "S", "Poetic expression"),
        ("Heat oven to 350°F and mix dry ingredients", "SW", "Recipe instruction"),
        
        # Historical content (West)
        ("During the Renaissance period, art flourished", "W", "Historical account"),
        ("The nature of consciousness remains a mystery", "NW", "Philosophical inquiry")
    ]
    
    print("Content Examples and Their Natural Sectors:")
    print("-" * 60)
    
    for content, expected_sector, category in content_examples:
        print(f"\n{category}:")
        print(f"  Content: \"{content[:50]}...\"")
        print(f"  Sector: {expected_sector} ({get_sector_description(expected_sector)})")


def get_sector_description(sector):
    """Get description for a sector."""
    descriptions = {
        "N": "Action/Adventure",
        "NE": "Technical/Instructional", 
        "E": "Scientific/Analytical",
        "SE": "Educational/Reference",
        "S": "Creative/Artistic",
        "SW": "Personal/Lifestyle",
        "W": "Historical/Reflective",
        "NW": "Philosophical/Abstract"
    }
    return descriptions.get(sector, "Unknown")


def explain_practical_usage():
    """Explain how sectors are used practically."""
    
    print("\n\n⚡ PRACTICAL USAGE EXAMPLES")
    print("=" * 60)
    
    usage_examples = [
        {
            "query": "Find technical documentation",
            "sector_search": "NE + adjacent (ENE, N)",
            "reasoning": "Technical content clusters in Northeast direction",
            "example_command": "search_in_sectors(['NE', 'ENE', 'N'])"
        },
        {
            "query": "Find creative or artistic content", 
            "sector_search": "S + adjacent (SSE, SSW)",
            "reasoning": "Creative content clusters in South direction",
            "example_command": "search_in_sectors(['S', 'SSE', 'SSW'])"
        },
        {
            "query": "Find historical information",
            "sector_search": "W + adjacent (WSW, WNW)",
            "reasoning": "Historical content clusters in West direction", 
            "example_command": "search_in_sectors(['W', 'WSW', 'WNW'])"
        },
        {
            "query": "Find scientific research",
            "sector_search": "E + adjacent (ENE, ESE)",
            "reasoning": "Scientific content clusters in East direction",
            "example_command": "search_in_sectors(['E', 'ENE', 'ESE'])"
        }
    ]
    
    for example in usage_examples:
        print(f"\n🔍 Query: \"{example['query']}\"")
        print(f"   Search Strategy: {example['sector_search']}")
        print(f"   Reasoning: {example['reasoning']}")
        print(f"   Code: {example['example_command']}")


def explain_embedding_to_angle_mapping():
    """Explain how embedding vectors become angles."""
    
    print("\n\n🔧 HOW EMBEDDINGS BECOME COMPASS DIRECTIONS")
    print("=" * 60)
    
    print("The process of mapping content to compass directions:")
    print()
    print("1. 📝 Text Content → 🔢 High-dimensional Embedding Vector")
    print("   Example: 'Adventure story' → [0.1, 0.8, -0.2, 0.4, ...]")
    print()
    print("2. 🔢 High-dimensional Vector → 📐 2D Projection")
    print("   Take first two components: [0.1, 0.8] → (x=0.1, y=0.8)")
    print()
    print("3. 📐 2D Coordinates → 🧭 Angle Calculation") 
    print("   angle = arctan2(y, x) = arctan2(0.8, 0.1) = 82.9°")
    print()
    print("4. 🧭 Angle → 📍 Compass Sector")
    print("   82.9° falls in East sector (67.5° - 112.5°)")
    print()
    print("5. 📍 Result: Content mapped to 'E' (Scientific/Analytical)")
    
    # Demonstrate with actual calculation
    print("\n🧮 EXAMPLE CALCULATION:")
    print("-" * 30)
    
    # Simulate some embeddings
    sample_embeddings = [
        ([0.1, 0.8], "Technical/Scientific content"),
        ([0.7, 0.7], "Instructional content"), 
        ([-0.5, 0.8], "Creative content"),
        ([-0.8, -0.2], "Historical content")
    ]
    
    compass = create_compass_32_system()
    
    for (x, y), content_type in sample_embeddings:
        angle_rad = math.atan2(y, x)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360
            
        # Normalize to [0, 2π) for sector lookup
        normalized_angle = angle_rad % (2 * math.pi)
        if normalized_angle < 0:
            normalized_angle += 2 * math.pi
            
        sector = compass.angle_to_sector(normalized_angle)
        
        print(f"{content_type}:")
        print(f"  Embedding: ({x:+.1f}, {y:+.1f})")
        print(f"  Angle: {angle_deg:6.1f}° → Sector {sector.name}")
        print()


def explain_advantages():
    """Explain the advantages of this system."""
    
    print("\n\n✨ ADVANTAGES OF DIRECTIONAL ORGANIZATION")
    print("=" * 60)
    
    advantages = [
        {
            "benefit": "🎯 Semantic Clustering",
            "description": "Similar content naturally groups together",
            "example": "All technical docs in NE, all creative writing in S"
        },
        {
            "benefit": "🔍 Intuitive Search",
            "description": "Query by content type using familiar directions",
            "example": "\"Find something scientific\" → search East sectors"
        },
        {
            "benefit": "📊 Content Analytics", 
            "description": "Track distribution of content types",
            "example": "\"70% of our content is technical (NE sector)\""
        },
        {
            "benefit": "🗺️ Spatial Metaphors",
            "description": "Use navigation concepts for information space",
            "example": "\"Adventure content to the North, history to the West\""
        },
        {
            "benefit": "⚡ Efficient Indexing",
            "description": "Pre-organize content by sector for fast retrieval",
            "example": "Index NE sector for technical documentation searches"
        }
    ]
    
    for advantage in advantages:
        print(f"\n{advantage['benefit']}: {advantage['description']}")
        print(f"   Example: {advantage['example']}")


if __name__ == "__main__":
    print("🌐 UNDERSTANDING COMPASS DIRECTIONS IN YOUR MEMORY SYSTEM")
    print("How content semantically maps to different directions")
    print("=" * 80)
    
    explain_compass_directions()
    demonstrate_content_clustering()
    explain_practical_usage()
    explain_embedding_to_angle_mapping()
    explain_advantages()
    
    print("\n" + "=" * 80)
    print("💡 Key Insight: Compass directions provide semantic organization")
    print("   based on the natural clustering of content in embedding space!") 
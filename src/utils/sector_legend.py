"""
Sector Legend and Semantic Mapping

This module provides a comprehensive legend/key for mapping natural language
queries and content types to compass sectors. Used by AI systems to translate
user queries into appropriate sector searches.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from .angular_sector_system import SectorSystem, create_compass_32_system
except ImportError:
    from angular_sector_system import SectorSystem, create_compass_32_system


@dataclass
class SectorMapping:
    """Represents a mapping between content types and sectors."""
    primary_sectors: List[str]      # Main sectors for this content type
    secondary_sectors: List[str]    # Adjacent/related sectors
    keywords: List[str]             # Keywords that indicate this content type
    phrases: List[str]              # Common phrases that indicate this content type
    confidence: float               # Confidence score (0.0-1.0)


class ContentCategory(Enum):
    """Main content categories mapped to compass directions."""
    ACTION_ADVENTURE = "action_adventure"
    TECHNICAL_INSTRUCTIONAL = "technical_instructional"
    SCIENTIFIC_ANALYTICAL = "scientific_analytical"
    EDUCATIONAL_REFERENCE = "educational_reference"
    CREATIVE_ARTISTIC = "creative_artistic"
    PERSONAL_LIFESTYLE = "personal_lifestyle"
    HISTORICAL_REFLECTIVE = "historical_reflective"
    PHILOSOPHICAL_ABSTRACT = "philosophical_abstract"


class SectorLegend:
    """
    Comprehensive legend for mapping content to compass sectors.
    Used by AI systems to translate natural language queries.
    """
    
    def __init__(self):
        """Initialize the sector legend with comprehensive mappings."""
        self.compass_system = create_compass_32_system()
        self.category_mappings = self._create_category_mappings()
        self.query_patterns = self._create_query_patterns()
        
    def _create_category_mappings(self) -> Dict[ContentCategory, SectorMapping]:
        """Create detailed mappings for each content category."""
        
        mappings = {
            ContentCategory.ACTION_ADVENTURE: SectorMapping(
                primary_sectors=["N", "NbE", "NbW"],
                secondary_sectors=["NNE", "NNW"],
                keywords=[
                    "adventure", "quest", "journey", "exploration", "expedition",
                    "action", "battle", "fight", "conflict", "challenge",
                    "hero", "heroic", "brave", "courage", "mission",
                    "travel", "voyage", "trek", "discovery", "rescue"
                ],
                phrases=[
                    "adventure story", "action sequence", "heroic journey",
                    "quest for", "epic adventure", "dangerous mission",
                    "exploration of", "battle against", "journey to"
                ],
                confidence=0.9
            ),
            
            ContentCategory.TECHNICAL_INSTRUCTIONAL: SectorMapping(
                primary_sectors=["NE", "NEbN", "NEbE"],
                secondary_sectors=["ENE", "NNE"],
                keywords=[
                    "technical", "manual", "guide", "tutorial", "instructions",
                    "how-to", "step-by-step", "procedure", "process", "method",
                    "installation", "setup", "configuration", "troubleshooting",
                    "assembly", "repair", "maintenance", "operation"
                ],
                phrases=[
                    "how to", "step by step", "technical manual", "user guide",
                    "installation guide", "setup instructions", "repair manual",
                    "operating procedures", "maintenance guide", "troubleshooting"
                ],
                confidence=0.95
            ),
            
            ContentCategory.SCIENTIFIC_ANALYTICAL: SectorMapping(
                primary_sectors=["E", "EbN", "EbS"],
                secondary_sectors=["ENE", "ESE"],
                keywords=[
                    "scientific", "research", "study", "analysis", "data",
                    "experiment", "hypothesis", "theory", "evidence", "findings",
                    "statistics", "correlation", "methodology", "results",
                    "peer-reviewed", "empirical", "quantitative", "qualitative"
                ],
                phrases=[
                    "research shows", "scientific study", "data analysis",
                    "experimental results", "statistical analysis", "research findings",
                    "empirical evidence", "peer reviewed", "methodology section"
                ],
                confidence=0.9
            ),
            
            ContentCategory.EDUCATIONAL_REFERENCE: SectorMapping(
                primary_sectors=["SE", "SEbE", "SEbS"],
                secondary_sectors=["ESE", "SSE"],
                keywords=[
                    "educational", "reference", "encyclopedia", "definition",
                    "explanation", "overview", "introduction", "basics",
                    "fundamentals", "concepts", "principles", "learn",
                    "understand", "knowledge", "information", "facts"
                ],
                phrases=[
                    "what is", "definition of", "introduction to", "overview of",
                    "basic concepts", "fundamental principles", "educational material",
                    "reference guide", "learning resource", "knowledge base"
                ],
                confidence=0.85
            ),
            
            ContentCategory.CREATIVE_ARTISTIC: SectorMapping(
                primary_sectors=["S", "SbE", "SbW"],
                secondary_sectors=["SSE", "SSW"],
                keywords=[
                    "creative", "artistic", "poetry", "poem", "art", "music",
                    "painting", "sculpture", "creative writing", "fiction",
                    "story", "novel", "imagination", "inspiration", "beautiful",
                    "aesthetic", "emotional", "expressive", "artistic"
                ],
                phrases=[
                    "creative writing", "artistic expression", "poetry collection",
                    "works of art", "creative work", "artistic piece",
                    "musical composition", "fictional story", "creative process"
                ],
                confidence=0.9
            ),
            
            ContentCategory.PERSONAL_LIFESTYLE: SectorMapping(
                primary_sectors=["SW", "SWbS", "SWbW"],
                secondary_sectors=["WSW", "SSW"],
                keywords=[
                    "personal", "lifestyle", "recipe", "cooking", "food",
                    "health", "fitness", "wellness", "advice", "tips",
                    "family", "relationships", "home", "daily", "routine",
                    "self-help", "improvement", "habits", "life"
                ],
                phrases=[
                    "personal story", "life advice", "cooking recipe",
                    "health tips", "lifestyle guide", "daily routine",
                    "personal experience", "family life", "home improvement"
                ],
                confidence=0.85
            ),
            
            ContentCategory.HISTORICAL_REFLECTIVE: SectorMapping(
                primary_sectors=["W", "WbS", "WbN"],
                secondary_sectors=["WSW", "WNW"],
                keywords=[
                    "historical", "history", "past", "ancient", "medieval",
                    "century", "era", "period", "timeline", "events",
                    "documentary", "memoir", "biography", "legacy",
                    "tradition", "heritage", "archive", "record"
                ],
                phrases=[
                    "in the past", "historical account", "during the", "era of",
                    "historical perspective", "past events", "memory of",
                    "historical context", "legacy of", "traditional"
                ],
                confidence=0.9
            ),
            
            ContentCategory.PHILOSOPHICAL_ABSTRACT: SectorMapping(
                primary_sectors=["NW", "NWbN", "NWbW"],
                secondary_sectors=["WNW", "NNW"],
                keywords=[
                    "philosophical", "philosophy", "abstract", "theoretical",
                    "concept", "idea", "thought", "thinking", "consciousness",
                    "existence", "reality", "truth", "meaning", "purpose",
                    "ethics", "morality", "metaphysics", "epistemology"
                ],
                phrases=[
                    "philosophical question", "abstract concept", "theoretical framework",
                    "nature of", "meaning of", "question of", "philosophy of",
                    "theoretical approach", "conceptual analysis", "abstract thinking"
                ],
                confidence=0.85
            )
        }
        
        return mappings
    
    def _create_query_patterns(self) -> List[Dict[str, any]]:
        """Create patterns for common query types."""
        
        patterns = [
            # Direct content type queries
            {
                "pattern": r"(?:find|show|get|search for|look for)\s+(?:me\s+)?(?:some\s+)?(?:technical|tech)\s+(?:documentation|docs|manuals|guides)",
                "category": ContentCategory.TECHNICAL_INSTRUCTIONAL,
                "confidence": 0.95
            },
            {
                "pattern": r"(?:find|show|get|search for|look for)\s+(?:me\s+)?(?:some\s+)?(?:scientific|research)\s+(?:papers|studies|research|data)",
                "category": ContentCategory.SCIENTIFIC_ANALYTICAL,
                "confidence": 0.9
            },
            {
                "pattern": r"(?:find|show|get|search for|look for)\s+(?:me\s+)?(?:some\s+)?(?:creative|artistic)\s+(?:writing|content|work|pieces)",
                "category": ContentCategory.CREATIVE_ARTISTIC,
                "confidence": 0.9
            },
            {
                "pattern": r"(?:find|show|get|search for|look for)\s+(?:me\s+)?(?:some\s+)?(?:historical|history)\s+(?:information|content|accounts|records)",
                "category": ContentCategory.HISTORICAL_REFLECTIVE,
                "confidence": 0.9
            },
            
            # How-to queries
            {
                "pattern": r"how\s+(?:do\s+i|to|can\s+i)\s+.+",
                "category": ContentCategory.TECHNICAL_INSTRUCTIONAL,
                "confidence": 0.8
            },
            
            # What-is queries
            {
                "pattern": r"what\s+is\s+.+",
                "category": ContentCategory.EDUCATIONAL_REFERENCE,
                "confidence": 0.7
            },
            
            # Recipe/cooking queries
            {
                "pattern": r"(?:recipe|cooking|how to cook|how to make)\s+.+",
                "category": ContentCategory.PERSONAL_LIFESTYLE,
                "confidence": 0.85
            },
            
            # Adventure/story queries
            {
                "pattern": r"(?:adventure|story|tale|journey)\s+(?:about|of|involving)\s+.+",
                "category": ContentCategory.ACTION_ADVENTURE,
                "confidence": 0.8
            }
        ]
        
        return patterns
    
    def translate_query(self, query: str) -> Dict[str, any]:
        """
        Translate a natural language query into sector recommendations.
        
        Args:
            query: Natural language query from user
            
        Returns:
            Dictionary with sector recommendations and confidence
        """
        query_lower = query.lower()
        results = {
            "query": query,
            "recommendations": [],
            "confidence": 0.0,
            "reasoning": []
        }
        
        # Check for direct pattern matches
        for pattern_info in self.query_patterns:
            if re.search(pattern_info["pattern"], query_lower):
                category = pattern_info["category"]
                mapping = self.category_mappings[category]
                
                results["recommendations"].append({
                    "sectors": mapping.primary_sectors + mapping.secondary_sectors,
                    "primary_sectors": mapping.primary_sectors,
                    "secondary_sectors": mapping.secondary_sectors,
                    "category": category.value,
                    "confidence": pattern_info["confidence"],
                    "match_type": "pattern"
                })
                results["reasoning"].append(f"Matched pattern: {pattern_info['pattern']}")
        
        # Check for keyword matches
        keyword_scores = {}
        for category, mapping in self.category_mappings.items():
            score = 0
            matched_keywords = []
            
            # Check keywords
            for keyword in mapping.keywords:
                if keyword in query_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Check phrases
            for phrase in mapping.phrases:
                if phrase in query_lower:
                    score += 2  # Phrases get higher weight
                    matched_keywords.append(phrase)
            
            if score > 0:
                confidence = min(score * 0.1, 1.0)  # Scale to 0-1
                keyword_scores[category] = {
                    "score": score,
                    "confidence": confidence,
                    "matched_keywords": matched_keywords
                }
        
        # Add keyword-based recommendations
        for category, score_info in keyword_scores.items():
            mapping = self.category_mappings[category]
            
            results["recommendations"].append({
                "sectors": mapping.primary_sectors + mapping.secondary_sectors,
                "primary_sectors": mapping.primary_sectors,
                "secondary_sectors": mapping.secondary_sectors,
                "category": category.value,
                "confidence": score_info["confidence"],
                "match_type": "keywords",
                "matched_keywords": score_info["matched_keywords"]
            })
            results["reasoning"].append(f"Keywords matched for {category.value}: {score_info['matched_keywords']}")
        
        # Sort recommendations by confidence
        results["recommendations"].sort(key=lambda x: x["confidence"], reverse=True)
        
        # Set overall confidence to highest recommendation
        if results["recommendations"]:
            results["confidence"] = results["recommendations"][0]["confidence"]
        
        return results
    
    def get_sectors_for_content_type(self, content_type: str) -> List[str]:
        """
        Get sectors for a specific content type.
        
        Args:
            content_type: Type of content to find sectors for
            
        Returns:
            List of recommended sectors
        """
        content_type_lower = content_type.lower()
        
        for category, mapping in self.category_mappings.items():
            if any(keyword in content_type_lower for keyword in mapping.keywords):
                return mapping.primary_sectors + mapping.secondary_sectors
        
        return []
    
    def get_legend(self) -> Dict[str, any]:
        """
        Get the complete legend/key for reference.
        
        Returns:
            Dictionary containing the complete legend
        """
        legend = {
            "description": "Semantic legend for compass sector content mapping",
            "categories": {}
        }
        
        for category, mapping in self.category_mappings.items():
            legend["categories"][category.value] = {
                "primary_sectors": mapping.primary_sectors,
                "secondary_sectors": mapping.secondary_sectors,
                "keywords": mapping.keywords,
                "phrases": mapping.phrases,
                "confidence": mapping.confidence,
                "description": self._get_category_description(category)
            }
        
        return legend
    
    def _get_category_description(self, category: ContentCategory) -> str:
        """Get human-readable description for a category."""
        descriptions = {
            ContentCategory.ACTION_ADVENTURE: "Action, adventure, journeys, quests, heroic content",
            ContentCategory.TECHNICAL_INSTRUCTIONAL: "Technical manuals, how-to guides, instructions, tutorials",
            ContentCategory.SCIENTIFIC_ANALYTICAL: "Scientific research, data analysis, empirical studies",
            ContentCategory.EDUCATIONAL_REFERENCE: "Educational material, reference content, definitions, overviews",
            ContentCategory.CREATIVE_ARTISTIC: "Creative writing, poetry, art, music, fiction",
            ContentCategory.PERSONAL_LIFESTYLE: "Personal stories, recipes, lifestyle advice, daily life",
            ContentCategory.HISTORICAL_REFLECTIVE: "Historical accounts, past events, memoirs, traditions",
            ContentCategory.PHILOSOPHICAL_ABSTRACT: "Philosophy, abstract concepts, theoretical frameworks"
        }
        return descriptions.get(category, "Unknown category")


# Global legend instance
_sector_legend = None

def get_sector_legend() -> SectorLegend:
    """Get the global sector legend instance."""
    global _sector_legend
    if _sector_legend is None:
        _sector_legend = SectorLegend()
    return _sector_legend


# Convenience functions for AI integration
def translate_natural_query(query: str) -> Dict[str, any]:
    """
    Translate a natural language query to sector recommendations.
    Main function for AI systems to use.
    """
    legend = get_sector_legend()
    return legend.translate_query(query)


def get_sectors_for_query(query: str) -> List[str]:
    """
    Get just the recommended sectors for a query.
    Simplified function returning only sector names.
    """
    result = translate_natural_query(query)
    if result["recommendations"]:
        return result["recommendations"][0]["primary_sectors"]
    return []


def get_legend_reference() -> Dict[str, any]:
    """
    Get the complete legend for reference.
    Useful for AI systems to understand available categories.
    """
    legend = get_sector_legend()
    return legend.get_legend()


if __name__ == "__main__":
    # Test the legend system
    legend = SectorLegend()
    
    test_queries = [
        "Find me some technical documentation",
        "Show me creative writing",
        "I need scientific research about climate",
        "How to cook pasta",
        "What is photosynthesis?",
        "Historical accounts of World War II",
        "Adventure stories about space exploration",
        "Philosophical questions about consciousness"
    ]
    
    print("🗺️ SECTOR LEGEND QUERY TRANSLATION TEST")
    print("=" * 60)
    
    for query in test_queries:
        result = legend.translate_query(query)
        print(f"\n🔍 Query: \"{query}\"")
        if result["recommendations"]:
            best = result["recommendations"][0]
            print(f"   Primary Sectors: {', '.join(best['primary_sectors'])}")
            print(f"   Category: {best['category']}")
            print(f"   Confidence: {best['confidence']:.2f}")
        else:
            print("   No recommendations found") 
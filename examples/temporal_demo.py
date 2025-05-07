#!/usr/bin/env python
"""
Temporal Reasoning Demonstration Script

This script demonstrates how to use the temporal reasoning capabilities
of the Temporal-Spatial Memory System through various examples.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.temporal import TemporalExpression, TemporalGranularity
from src.temporal.feature_extractor import TemporalFeatureExtractor
from src.temporal.coordinate_extension import TemporalCoordinateExtension

def demonstrate_basic_extraction():
    """Demonstrate basic temporal expression extraction"""
    print("\n=== Basic Temporal Expression Extraction ===")
    
    extractor = TemporalFeatureExtractor()
    
    samples = [
        "The meeting is scheduled for January 15, 2023 at 3:00 PM.",
        "We need to complete this project by next Friday.",
        "The event happened three days ago and lasted for about two hours.",
        "During the summer of 2022, we conducted extensive research.",
        "I'll see you tomorrow morning around 9 AM."
    ]
    
    for sample in samples:
        print(f"\nText: {sample}")
        expressions = extractor.extract_expressions(sample)
        
        if not expressions:
            print("  No temporal expressions detected")
        
        for expr in expressions:
            print(f"  Found: '{expr.text}'")
            print(f"    Type: {expr.expression_type}")
            print(f"    Normalized: {expr.normalized_value}")
            print(f"    Confidence: {expr.confidence:.2f}")

def demonstrate_coordinate_extension():
    """Demonstrate how temporal expressions extend the coordinate system"""
    print("\n=== Temporal Coordinate Extension ===")
    
    coordinator = TemporalCoordinateExtension()
    
    # Create some sample base coordinates
    base_coordinate = {"r": 0.85, "theta": 0.42, "z": 1.0}
    
    # Create some sample temporal expressions
    expressions = [
        TemporalExpression(
            text="January 15, 2023",
            normalized_value="2023-01-15",
            expression_type="absolute_date",
            confidence=0.95,
            granularity=TemporalGranularity.DAY
        ),
        TemporalExpression(
            text="next week",
            normalized_value="relative:+7d",
            expression_type="relative_date",
            confidence=0.85,
            granularity=TemporalGranularity.WEEK
        ),
        TemporalExpression(
            text="two hours",
            normalized_value="duration:2h",
            expression_type="duration",
            confidence=0.9,
            granularity=TemporalGranularity.HOUR
        )
    ]
    
    # Extend coordinates with each expression
    for expr in expressions:
        print(f"\nBase coordinate: {base_coordinate}")
        print(f"Extending with: '{expr.text}' ({expr.expression_type})")
        
        extended = coordinator.extend_coordinate(base_coordinate, expr)
        print(f"Extended coordinate: {extended}")
        
        # Demonstrate temporal distance calculation
        reference_time = datetime.now().timestamp()
        distance = coordinator.calculate_temporal_distance(extended, {"t": reference_time})
        print(f"Temporal distance from now: {distance:.2f}")

def demonstrate_literary_patterns():
    """Demonstrate recognition of literary temporal patterns"""
    print("\n=== Literary Temporal Pattern Recognition ===")
    
    # Define literary time patterns similar to what we used in hobbit_analysis.py
    LITERARY_TIME_PATTERNS = {
        "literary_duration": re.compile(
            r"\b((?:a |one |two |three |four |five |six |seven |eight |nine |ten |eleven |twelve |fourteen |fifteen |twenty |thirty |forty |fifty |hundred |thousands? of |many |several |few |couple of )?"
            r"(?:minute|hour|day|night|week|month|year|decade|century|age)s?(?:(?: and | or )(?:a |one |two |three |four |five |six |seven |eight |nine |ten |eleven |twelve |fourteen |fifteen |twenty |thirty |forty |fifty |hundred |many |several |few |couple of )?(?:minute|hour|day|night|week|month|year|decade|century|age)s?)?)\b",
            re.IGNORECASE
        ),
        "literary_relative": re.compile(
            r"\b((?:long |right |just |soon |much |very )?"
            r"(?:ago|before|after|later|now|then|early|immediately|instantly|eventually|subsequently|previously|formerly|recently|lately|nowadays))\b",
            re.IGNORECASE
        ),
        "literary_time_of_day": re.compile(
            r"\b((?:early |late |before |after |in the |during the |at )?"
            r"(?:morning|dawn|daybreak|sunrise|noon|afternoon|evening|dusk|sunset|twilight|night|midnight))\b",
            re.IGNORECASE
        ),
        "literary_seasons": re.compile(
            r"\b((?:in |during |throughout |early |late |mid-?)?"
            r"(?:spring|summer|autumn|fall|winter)(?:time)?)\b",
            re.IGNORECASE
        )
    }
    
    # Sample literary excerpts
    literary_samples = [
        "Long ago in a distant land, Aku, the shapeshifting master of darkness, unleashed an unspeakable evil.",
        "It was during the late summer that the rumors began to spread throughout the village.",
        "They traveled for many days and nights before reaching the ancient temple.",
        "The battle lasted ages and ages, wearing down even the mightiest warriors.",
        "At dawn they set forth, hoping to reach the mountains before nightfall."
    ]
    
    for sample in literary_samples:
        print(f"\nText: {sample}")
        
        # Find matches for each pattern type
        all_matches = []
        for pattern_type, pattern in LITERARY_TIME_PATTERNS.items():
            matches = pattern.finditer(sample)
            for match in matches:
                match_text = match.group(0)
                position = f"{match.start()}-{match.end()}"
                
                all_matches.append({
                    "text": match_text,
                    "pattern_type": pattern_type,
                    "position": position
                })
                
                print(f"  Found: '{match_text}'")
                print(f"    Type: {pattern_type}")
                print(f"    Position: {position}")

def demonstrate_temporal_filtering():
    """Demonstrate filtering results based on temporal criteria"""
    print("\n=== Temporal Filtering ===")
    
    coordinator = TemporalCoordinateExtension()
    
    # Create sample coordinates with temporal components
    coordinates = [
        {"r": 0.85, "theta": 0.42, "z": 1.0, "t": datetime(2023, 1, 1).timestamp()},
        {"r": 0.78, "theta": 0.36, "z": 1.0, "t": datetime(2023, 5, 15).timestamp()},
        {"r": 0.92, "theta": 0.51, "z": 1.0, "t": datetime(2023, 8, 30).timestamp()},
        {"r": 0.65, "theta": 0.29, "z": 1.0, "t": datetime(2023, 12, 31).timestamp()}
    ]
    
    # Create temporal filters for different time periods
    q1_filter = coordinator.create_temporal_filter(
        start_time=datetime(2023, 1, 1).timestamp(),
        end_time=datetime(2023, 3, 31).timestamp()
    )
    
    middle_year_filter = coordinator.create_temporal_filter(
        start_time=datetime(2023, 4, 1).timestamp(),
        end_time=datetime(2023, 9, 30).timestamp()
    )
    
    # Apply filters
    print("\nAll coordinates:")
    for i, coord in enumerate(coordinates):
        date = datetime.fromtimestamp(coord["t"]).strftime("%Y-%m-%d")
        print(f"  [{i}] r={coord['r']:.2f}, theta={coord['theta']:.2f}, t={date}")
    
    print("\nQ1 2023 filter results:")
    q1_results = [i for i, coord in enumerate(coordinates) if q1_filter(coord)]
    for i in q1_results:
        date = datetime.fromtimestamp(coordinates[i]["t"]).strftime("%Y-%m-%d")
        print(f"  [{i}] r={coordinates[i]['r']:.2f}, theta={coordinates[i]['theta']:.2f}, t={date}")
    
    print("\nMid-year (Apr-Sep) 2023 filter results:")
    mid_results = [i for i, coord in enumerate(coordinates) if middle_year_filter(coord)]
    for i in mid_results:
        date = datetime.fromtimestamp(coordinates[i]["t"]).strftime("%Y-%m-%d")
        print(f"  [{i}] r={coordinates[i]['r']:.2f}, theta={coordinates[i]['theta']:.2f}, t={date}")

def main():
    """Main function demonstrating temporal reasoning capabilities"""
    print("=== Temporal Reasoning Demonstration ===")
    print("This script demonstrates the temporal reasoning capabilities")
    print("of the Temporal-Spatial Memory System.")
    
    # Run demonstrations
    demonstrate_basic_extraction()
    demonstrate_coordinate_extension()
    demonstrate_literary_patterns()
    demonstrate_temporal_filtering()
    
    print("\n=== Demonstration Complete ===")
    print("For more detailed usage examples, see docs/temporal_reasoning_guide.md")

if __name__ == "__main__":
    main() 
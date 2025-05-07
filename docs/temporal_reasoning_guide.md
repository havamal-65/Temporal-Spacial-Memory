# Temporal Reasoning Guide

This guide explains how to use the Temporal-Spatial Memory System's temporal reasoning capabilities, which enable advanced temporal expression extraction, analysis, and coordinate mapping.

## Overview

The temporal reasoning module enhances the system's ability to understand and process time-related information in text. This is particularly valuable for:

- Literary analysis (identifying when events occur in narratives)
- Historical document processing (tracking chronological sequences)
- Temporal question answering (e.g., "What happened last Tuesday?")
- Causal relationship identification (inferring possible cause-effect relationships based on temporal ordering)

## Core Components

### 1. Temporal Feature Extractor

The `TemporalFeatureExtractor` identifies and extracts temporal expressions from text:

```python
from src.temporal.feature_extractor import TemporalFeatureExtractor

extractor = TemporalFeatureExtractor()
text = "The meeting is scheduled for next Tuesday at 3 PM."
expressions = extractor.extract_expressions(text)

for expr in expressions:
    print(f"Expression: {expr.text}")
    print(f"Normalized: {expr.normalized_value}")
    print(f"Confidence: {expr.confidence}")
    print(f"Granularity: {expr.granularity}")
```

#### Supported Expression Types

- **Absolute Dates**: "January 1, 2023", "2023-01-01", "01/01/2023"
- **Relative Dates**: "yesterday", "next week", "two days ago"
- **Time Expressions**: "3:00 PM", "noon", "midnight"
- **Durations**: "for three hours", "over the span of two weeks"
- **Literary Temporal Expressions**: "long ago", "at that moment", "in ancient times"

### 2. Temporal Coordinate Extension

The `TemporalCoordinateExtension` maps temporal expressions to coordinates in the system:

```python
from src.temporal.coordinate_extension import TemporalCoordinateExtension

coordinator = TemporalCoordinateExtension()
base_coordinate = {"r": 1.0, "theta": 0.5}
extended = coordinator.extend_coordinate(base_coordinate, temporal_expression)
```

This extension:
- Adds a temporal dimension (`t`) to the coordinates
- Calculates temporal distance between coordinates
- Applies decay functions for time-sensitive relevance scoring
- Enables filtering by time period or temporal proximity

### 3. Literary Temporal Pattern Recognition

For literary text, specialized pattern recognition enables identification of more nuanced temporal expressions:

```python
from src.temporal.literary_patterns import extract_literary_temporal_expressions

text = "Long ago in a distant land..."
expressions = extract_literary_temporal_expressions(text)
```

This feature recognizes patterns like:
- "ages and ages" (literary_duration)
- "long ago" (literary_relative)
- "morning", "noon", "nightfall" (literary_time_of_day)
- "spring", "autumn", "winter" (literary_seasons)

## The Hobbit Analysis Example

Our system includes a demonstration of temporal expression extraction and analysis from J.R.R. Tolkien's "The Hobbit". This example showcases the system's ability to identify various types of temporal expressions in literary text.

### Running the Analysis

```bash
python hobbit_analysis.py
```

This script:
1. Analyzes excerpts from The Hobbit
2. Identifies various temporal expressions
3. Categorizes them by type
4. Saves the results to a JSON file (`hobbit_temporal_analysis_results.json`)

### Sample Results

Here's an excerpt of the analysis results:

```json
{
  "chapter": "Chapter 1: An Unexpected Party",
  "paragraph_id": "01.005",
  "text": "Long ago in my grandfather Took's time, Old Took was still the head of the family.",
  "matches": [
    {
      "text": "Long ago",
      "pattern_type": "literary_relative",
      "position": "0-8"
    }
  ]
}
```

### Understanding the Results

The analysis identifies several types of temporal expressions:

1. **Relative Temporal References**:
   - "Long ago" (Chapter 1)
   - "later" (Chapter 5)

2. **Time of Day References**:
   - "morning" and "noon" (Chapter 2)

3. **Duration References**:
   - "fourteen days" (Chapter 3)
   - "few hours" (Chapter 5)
   - "two days and two nights" (Chapter 9)
   - "ages and ages" (Chapter 5)

4. **Calendar References**:
   - "May", "Thursday", "Friday" (Chapter 19)

## Integrating with the Narrative Atlas

You can integrate temporal reasoning with the Narrative Atlas for enhanced retrieval:

```python
from src.models.narrative_atlas import NarrativeAtlas
from src.temporal.feature_extractor import TemporalFeatureExtractor

# Initialize components
atlas = NarrativeAtlas(storage_path="output/atlas")
extractor = TemporalFeatureExtractor()

# Process text with temporal awareness
text = "The meeting occurred yesterday at the headquarters."
expressions = extractor.extract_expressions(text)

# Add temporal metadata to the node
node_id = atlas.add_node(
    content={"text": text},
    metadata={"temporal_expressions": [expr.__dict__ for expr in expressions]}
)

# Query with temporal constraints
results = atlas.search(
    query="What happened yesterday?",
    use_temporal_reasoning=True
)
```

## Advanced Features

### Temporal Distance Calculation

Calculate distance between temporal expressions:

```python
from src.temporal.coordinate_extension import TemporalCoordinateExtension

coordinator = TemporalCoordinateExtension()
distance = coordinator.calculate_temporal_distance(coord1, coord2)
```

### Temporal Filtering

Filter results based on time periods:

```python
from datetime import datetime
from src.temporal.coordinate_extension import TemporalCoordinateExtension

coordinator = TemporalCoordinateExtension()
filter_func = coordinator.create_temporal_filter(
    start_time=datetime(2023, 1, 1).timestamp(),
    end_time=datetime(2023, 12, 31).timestamp()
)

# Apply filter to coordinates
filtered_results = [coord for coord in results if filter_func(coord)]
```

### Temporal Relevance Weighting

Adjust relevance scores based on temporal proximity:

```python
from src.temporal.coordinate_extension import TemporalCoordinateExtension

coordinator = TemporalCoordinateExtension()
weighted_score = coordinator.apply_temporal_weighting(
    base_score=0.85,
    coord={'t': 1672531200.0},  # Jan 1, 2023
    query_time=1672704000.0,    # Jan 3, 2023
    temporal_weight=0.3
)
```

## Command Line Usage

Analyze a document with temporal reasoning:

```bash
python run_project.py --query "What happened last week?" --use-temporal-reasoning
```

Extract temporal expressions from a file:

```bash
python run_project.py --extract-temporal --input-file input/document.txt --output-file output/temporal_analysis.json
```

## Best Practices

1. **Normalize Reference Points**: For relative times, establish clear reference points
2. **Handle Ambiguity**: Be aware that some expressions may have multiple interpretations
3. **Consider Context**: Temporal expressions often require context for proper interpretation
4. **Combine with Semantic Search**: Use temporal reasoning alongside semantic search for best results
5. **Validate Results**: For critical applications, validate temporal extractions against ground truth 
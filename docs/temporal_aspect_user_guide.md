# User Guide: Leveraging Temporal Aspects

## Introduction

The Temporal-Spatial Memory System provides powerful capabilities for time-aware information retrieval and analysis. This guide explains how to effectively leverage the temporal dimension (`t` coordinate) in your queries and analyses.

## Understanding Temporal Coordinates

In our system, temporal coordinates represent sequential/chronological positioning of information. They are derived from:

- Document structure (page numbers)
- Position within pages (chunk sequence)
- Explicit temporal metadata (when available)

This allows for retrieval that respects the natural flow of information as it was originally presented.

## Basic Temporal Queries

### Time-Focused Retrieval

To retrieve information from a specific time point:

```python
# Retrieve information focused around temporal coordinate 5.0
results = atlas.search_with_temporal_focus(
    query_text="What happened with Bilbo?", 
    temporal_focus=5.0,  # Target temporal position
    decay_rate=0.1       # How quickly relevance decays with temporal distance
)
```

### Temporal Range Filtering

To limit results to a specific temporal range:

```python
from src.nl_parser import CoordinateFilters

# Create filters for a temporal range
filters = CoordinateFilters(
    t_min=2.5,  # Start of temporal range
    t_max=7.8   # End of temporal range
)

# Get matching node IDs
matching_ids = atlas._get_ids_matching_filters(filters)

# Use in search
results = atlas.search_with_nl_query(
    "What events occurred with the dragon?",
    filters=filters
)
```

## Advanced Temporal Features

### Temporal Decay

Control how relevance diminishes with temporal distance:

```python
# Strong temporal decay (quickly diminishes with distance)
results_strong = atlas.search_with_retrieval_params(
    query_text="What happened in the mountain?",
    retrieval_params={
        "temporal_focus": 10.5,
        "temporal_decay_rate": 0.3  # Strong decay
    }
)

# Weak temporal decay (slowly diminishes with distance)
results_weak = atlas.search_with_retrieval_params(
    query_text="What happened in the mountain?",
    retrieval_params={
        "temporal_focus": 10.5,
        "temporal_decay_rate": 0.05  # Weak decay
    }
)
```

### Temporal Sequences

To analyze sequences of events or information:

```python
# Get nodes in temporal order
nodes = atlas.get_nodes_by_temporal_order(
    start_t=0.0,
    end_t=20.0,
    node_types=["event", "character_appearance"]
)

# Process nodes in sequence
for node in nodes:
    print(f"At t={node.coordinates.t}: {node.content.get('description', '')}")
```

### Temporal Clustering

Identify clusters of information across time:

```python
from src.visualization.analytics import ClusterAnalyzer

analyzer = ClusterAnalyzer()
results = analyzer.analyze_atlas(atlas)

# Get temporal clusters
temporal_clusters = results['temporal']['temporal_clusters']

for i, cluster in enumerate(temporal_clusters):
    print(f"Temporal Cluster {i}: t_min={cluster['t_min']}, t_max={cluster['t_max']}")
    print(f"Contains {len(cluster['node_ids'])} nodes")
```

## Natural Language Temporal Queries

The system supports natural language specifications of temporal aspects:

```python
# These queries will be parsed to extract temporal constraints
results1 = atlas.search_with_nl_query("What happened in the early chapters?")
results2 = atlas.search_with_nl_query("Show me events from the middle of the story")
results3 = atlas.search_with_nl_query("Find information near the end of the book")
```

## Visualization of Temporal Information

### Temporal Heatmaps

Generate heatmaps to visualize information density across time:

```python
from src.visualization.exporters import HeatmapExporter

exporter = HeatmapExporter(output_dir="output/heatmaps")
heatmaps = exporter.export_atlas_heatmaps(
    atlas=atlas,
    dimensions_list=[("t", "r")], # Temporal vs. Radius
    bin_sizes={"t": 1.0, "r": 0.2}
)
```

### Temporal Evolution Visualization

Visualize how information or themes evolve over time:

```python
from src.visualization.coordinate_visualizer import CoordinateVisualizer

visualizer = CoordinateVisualizer()
timeline = visualizer.visualize_temporal_evolution(
    atlas=atlas,
    query="dragon",  # Track this concept through time
    window_size=2.0  # Size of sliding window
)
```

## Practical Examples

### Tracking Character Development

```python
# How a character develops through the narrative
character_timeline = atlas.search_with_retrieval_params(
    query_text="Thorin character development",
    retrieval_params={
        "sort_by": "temporal",
        "directional_bias": None,  # No directional bias
        "include_metadata": ["temporal_position", "chapter"]
    }
)

# Process results in temporal order
for node, score in character_timeline:
    print(f"t={node.coordinates.t} | {node.content.get('text', '')[:100]}...")
```

### Finding Key Plot Points

```python
# Identify significant events across the narrative
plot_points = atlas.search_with_retrieval_params(
    query_text="major events dragon treasure battle",
    retrieval_params={
        "radial_preference": 0.8,  # Prefer higher radius (more important)
        "min_temporal_distance": 3.0,  # Ensure events are separated in time
        "k": 5  # Get top 5 results
    }
)
```

### Comparative Analysis Across Time Periods

```python
# Compare early vs late descriptions
early_mentions = atlas.search_with_temporal_focus(
    query_text="Bilbo's ring",
    temporal_focus=3.0
)

late_mentions = atlas.search_with_temporal_focus(
    query_text="Bilbo's ring",
    temporal_focus=15.0
)

# Compare the descriptions
for node, score in early_mentions:
    print(f"EARLY (t={node.coordinates.t}): {node.content.get('text', '')[:100]}")
    
for node, score in late_mentions:
    print(f"LATE (t={node.coordinates.t}): {node.content.get('text', '')[:100]}")
```

## Tips for Effective Temporal Retrieval

1. **Use appropriate decay rates** - Higher decay rates (0.2-0.3) for very time-sensitive queries, lower rates (0.05-0.1) for broader context
2. **Combine temporal focus with semantic search** - Get relevance and temporal proximity together
3. **Consider z-coordinate filtering** - Combine temporal filtering with structural layer filtering
4. **Use temporal clustering** for narrative structure analysis
5. **Visualize before querying** to understand the temporal distribution of your information

## Troubleshooting

- **Too few results?** Try decreasing the temporal decay rate
- **Irrelevant results despite temporal focus?** Try increasing the decay rate
- **Missing expected results?** Check if temporal coordinates are assigned correctly in the atlas
- **Inconsistent temporal positioning?** Review how the document was ingested and chunked 
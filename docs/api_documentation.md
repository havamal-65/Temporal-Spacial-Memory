# API Documentation: Temporal-Spatial Memory System

This document provides comprehensive API documentation for the key classes and methods in the Temporal-Spatial Memory System.

## Table of Contents

1. [NarrativeAtlas](#narrativeatlas)
2. [CoordinateMapper](#coordinatemapper)
3. [Visualization Tools](#visualization-tools)
4. [Query Processing](#query-processing)
5. [Data Models](#data-models)
6. [Server API](#server-api)

## NarrativeAtlas

The `NarrativeAtlas` class is the primary interface for working with the temporal-spatial memory system.

### Initialization

```python
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service

# Create an embedding service
embedding_service = create_embedding_service(service_type="langchain")

# Initialize the NarrativeAtlas
atlas = NarrativeAtlas(
    storage_path="output/atlas_storage",
    embedding_service=embedding_service
)
```

### Core Methods

#### Adding Content

```python
# Add a node with content
node_id = atlas.add_node(
    node_id=None,                # Auto-generated if None
    content={"text": "Content text here"},
    embedding=None,              # Will be generated if None
    metadata={"node_type": "content", "source": "document_name"},
    coordinates=None,            # Will be generated if None
    keywords=None,               # Will be extracted if None
    parent_node_id=None          # Optional parent reference
)
```

#### Basic Search

```python
# Find similar nodes using semantic search
results = atlas.find_similar_nodes(
    query_text="What is a hobbit?",
    k=5                          # Number of results to return
)

# Each result is a tuple of (Node, score)
for node, score in results:
    print(f"Score: {score}, Content: {node.content.get('text', '')[:100]}...")
```

#### Advanced Search Methods

```python
# Search with natural language query (supports temporal and coordinate filters)
results = atlas.search_with_nl_query(
    nl_query="Find information about dragons in the middle chapters",
    k=10
)

# Search with temporal focus
results = atlas.search_with_temporal_focus(
    query_text="What happened with Bilbo?",
    temporal_focus=5.0,          # Target temporal position
    decay_rate=0.1,              # Temporal decay rate
    k=5
)

# Search with directional bias (semantic direction)
results = atlas.search_with_directional_bias(
    query_text="Tell me about the treasure",
    direction=1.5,               # Angular direction in radians
    strength=0.3,                # Bias strength
    k=5
)

# Search with custom retrieval parameters
results = atlas.search_with_retrieval_params(
    query_text="What happened in the mountain?",
    retrieval_params={
        "temporal_focus": 10.5,
        "temporal_decay_rate": 0.2,
        "radial_preference": 0.7,
        "directional_bias": 2.1,
        "directional_strength": 0.4,
        "z_filters": {"z_type": "LAYER", "z_min": 0, "z_max": 2}
    },
    k=10
)
```

#### RAG Integration

```python
# Generate context-enhanced prompt for LLM
context_prompt = atlas.answer_query_with_context(
    user_query="Explain the relationship between Bilbo and Gollum",
    k=3                          # Number of context nodes to include
)
```

#### Persistence

```python
# Save atlas state to disk
atlas.save()

# Load atlas state from disk
success = atlas.load()

# Clear all data
atlas.clear()
```

#### Node Management

```python
# Delete a node
success = atlas.delete_node(node_id="node_12345")

# Update node coordinates
success = atlas.update_node_coordinates(
    node_id="node_12345",
    new_coordinates=PolarTemporalCoordinate(r=0.8, theta=1.2, t=5.6, z=0.0, z_type="LAYER")
)
```

## CoordinateMapper

The `CoordinateMapper` class handles transformation of text and embeddings into polar-temporal coordinates.

### Initialization

```python
from src.utils.coordinate_mapper import CoordinateMapper
from src.utils.embedding_service import create_embedding_service

embedding_service = create_embedding_service()

coordinate_mapper = CoordinateMapper(
    embedding_service=embedding_service,
    # Coordinate calculation parameters
    base_radius=0.9,
    use_embedding_for_coords=True,
    embedding_r_scale=1.0,
    embedding_theta_scale=3.14159,
    # Normalization parameters
    normalize_embeddings=True,
    max_radius=100.0,
    min_radius=0.1,
    # Z-mapping parameters
    layer_z_map={'MAIN': 0.0, 'FOOTNOTE': 1.0, 'COMMENTARY': 2.0},
    # Logging parameters
    log_coordinates=True
)
```

### Methods

```python
# Map content to coordinates
mapping_result = coordinate_mapper.map_to_coordinates(
    content="Text content to map",
    metadata={
        "page_number": 5,
        "chunk_index_on_page": 2,
        "total_chunks_on_page": 8,
        "structural_layer_type": "MAIN"
    },
    embedding=None  # Optional pre-computed embedding
)

# The result contains:
coordinates = mapping_result['coordinate']   # PolarTemporalCoordinate object
keywords = mapping_result['keywords']        # Extracted keywords
embedding = mapping_result['embedding']      # Embedding used (or generated)
details = mapping_result['mapping_details']  # Details about the mapping process
```

## Visualization Tools

### CoordinateVisualizer

```python
from src.visualization.coordinate_visualizer import CoordinateVisualizer

visualizer = CoordinateVisualizer(
    output_dir="output/visualizations",
    interactive=True
)

# Generate visualizations
visualizations = visualizer.visualize_atlas(
    atlas=atlas,
    view_type="all",        # "polar", "temporal", "3d", "heatmap", or "all"
    color_by="type"         # Node attribute for coloring
)

# Visualize temporal evolution
timeline = visualizer.visualize_temporal_evolution(
    atlas=atlas,
    query="dragon",         # Concept to track
    window_size=2.0         # Sliding window size
)
```

### Dashboard

```python
from src.visualization.dashboard import Dashboard

# Create interactive dashboard
dashboard = Dashboard(
    narrative_atlas=atlas,
    port=8050,
    debug=False
)

# Run the dashboard
dashboard.run(open_browser=True)

# Generate static report
report_path = dashboard.generate_static_report("output/atlas_report.html")
```

### Exporters

```python
from src.visualization.exporters import NetworkExporter, HeatmapExporter

# Export network for external tools
network_exporter = NetworkExporter(output_dir="output/networks")
exports = network_exporter.export_atlas_network(
    atlas=atlas,
    formats=["gephi", "cytoscape", "d3"],
    link_type="combined"
)

# Export heatmaps
heatmap_exporter = HeatmapExporter(output_dir="output/heatmaps")
heatmaps = heatmap_exporter.export_atlas_heatmaps(
    atlas=atlas,
    dimensions_list=[("theta", "t"), ("r", "t"), ("theta", "r")],
    bin_sizes={"theta": 0.2, "t": 1.0, "r": 0.1}
)
```

### Analytics

```python
from src.visualization.analytics import ClusterAnalyzer

analyzer = ClusterAnalyzer(output_dir="output/analytics")
results = analyzer.analyze_atlas(atlas)

# Access analysis results
clusters = results['clustering']['clusters']
temporal_patterns = results['temporal']['temporal_clusters']
information_entropy = results['distribution']['overall_entropy']
```

## Query Processing

### NlQueryParser

```python
from src.nl_parser import NlQueryParser, CoordinateFilters

parser = NlQueryParser()

# Parse natural language query
parsed_query = parser.parse_query(
    "Find information about the ring in the early chapters"
)

# Access parsed components
semantic_query = parsed_query.semantic_query
temporal_filters = parsed_query.temporal_filters
coordinate_filters = parsed_query.coordinate_filters
directives = parsed_query.directives

# Create custom filters
custom_filters = CoordinateFilters(
    r_min=0.5,
    r_max=None,
    theta_min=0.0,
    theta_max=3.14,
    t_min=1.0,
    t_max=5.0,
    z_min=None,
    z_max=None,
    z_type=None
)
```

## Data Models

### PolarTemporalCoordinate

```python
from src.data_models import PolarTemporalCoordinate, Z_TYPES

# Create coordinate object
coordinates = PolarTemporalCoordinate(
    r=0.75,
    theta=2.14,
    t=3.5,
    z=1.0,
    z_type="LAYER"  # One of Z_TYPES: "DEFAULT", "LAYER", "PERSPECTIVE", "VERSION", "ABSTRACTION"
)
```

### Node

```python
from src.models.narrative_atlas import Node

# Node structure (for reference)
node = Node(
    id="node_12345",
    type="content",
    content={"text": "Content text", "additional_info": "Extra data"},
    coordinates=PolarTemporalCoordinate(...),
    embedding=np.array(...),
    keywords=["keyword1", "keyword2"],
    metadata={"source": "document_name", "page": 5},
    parent_node_id=None,
    timestamp=1623451789.0,
    mapping_details={"calculation_method": "embedding-based"}
)
```

## Server API

The system provides a FastAPI server for accessing the NarrativeAtlas functionality via HTTP.

### Starting the Server

```bash
# Start the server
python server.py
```

### API Endpoints

#### `/narrative-rag`

Retrieve context and generate a prompt/response for a query:

```
POST /narrative-rag

{
  "query": "What happened when Bilbo met Gollum?",
  "k": 3
}
```

Response:

```json
{
  "result": "Context-enhanced response or prompt..."
}
```

#### `/health`

Check the status of the server:

```
GET /health
```

Response:

```json
{
  "status": "ok",
  "atlas_status": "loaded",
  "index_size": 1250
}
```

### Client Usage

```python
import requests

# Make a query request
response = requests.post(
    "http://localhost:8000/narrative-rag",
    json={
        "query": "Explain how Bilbo escaped from the goblins",
        "k": 5
    }
)

# Access the response
result = response.json()["result"]
print(result)
``` 
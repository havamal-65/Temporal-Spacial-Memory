# Example Notebook: Temporal-Spatial Memory System

This notebook demonstrates common use cases for the Temporal-Spatial Memory System with Polar Coordinates.

## 1. Setup and Initialization

First, we'll import the necessary modules and initialize our system.

```python
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path if needed
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.getcwd())))

# Import system components
from src.models.narrative_atlas import NarrativeAtlas
from src.utils.embedding_service import create_embedding_service
from src.data_models import PolarTemporalCoordinate
from src.visualization.coordinate_visualizer import CoordinateVisualizer
```

Let's initialize our embedding service and NarrativeAtlas:

```python
# Initialize the embedding service (using sentence-transformers)
embedding_service = create_embedding_service(service_type="langchain")

# Path to store our data
atlas_path = "output/example_atlas"
os.makedirs(atlas_path, exist_ok=True)

# Initialize the NarrativeAtlas
atlas = NarrativeAtlas(
    storage_path=atlas_path,
    embedding_service=embedding_service
)
```

## 2. Ingesting Content with Polar-Temporal Coordinates

Now let's add some content to our atlas. We'll create documents with natural temporal sequence.

```python
# Example story content with temporal progression
content_blocks = [
    "Once upon a time, in a small village, there lived a curious young explorer named Elara.",
    "Elara spent her days dreaming of adventures beyond the distant mountains.",
    "One morning, Elara discovered an ancient map hidden in her grandmother's attic.",
    "The map showed a path to a legendary crystal cave said to hold powerful secrets.",
    "Determined to find the cave, Elara prepared for her journey with supplies and courage.",
    "As dawn broke, Elara set out toward the mountains, following the map's instructions.",
    "The path was difficult, winding through dense forests and across rapid streams.",
    "After three days of travel, Elara finally reached the entrance to the crystal cave.",
    "Inside, the cave glittered with thousands of crystals that reflected colorful light.",
    "At the center of the cave, Elara found a mysterious crystal pedestal.",
    "When she touched the pedestal, the crystals began to glow with an ethereal blue light.",
    "Suddenly, the cave transformed into a vast repository of ancient knowledge.",
    "Elara learned that the cave was created by an advanced civilization long ago.",
    "They had preserved their wisdom in the crystals for future generations to discover.",
    "Elara spent days studying the knowledge, learning about science, art, and philosophy.",
    "When she finally returned to her village, she brought back incredible insights.",
    "Elara shared the ancient knowledge with her community, transforming their understanding.",
    "The village flourished with new technologies and ideas from the crystal cave.",
    "Elara became renowned as a wise teacher and continued to explore for more knowledge.",
    "And so, the legacy of the crystal cave lived on through Elara and her village."
]

# Add content to the atlas with automatically generated coordinates
node_ids = []
for i, content in enumerate(content_blocks):
    # Create metadata with page and position information
    metadata = {
        "page_number": (i // 5) + 1,  # 5 blocks per page
        "chunk_index_on_page": i % 5,
        "total_chunks_on_page": 5,
        "doc_id": "elara_story",
        "node_type": "content",
        "structural_layer_type": "MAIN"
    }
    
    # Add the node to our atlas
    node_id = atlas.add_node(
        node_id=None,
        content={"text": content},
        embedding=None,  # Will be generated automatically
        metadata=metadata,
        coordinates=None  # Will be calculated from embedding and metadata
    )
    
    node_ids.append(node_id)
    print(f"Added node {node_id} with temporal position t={atlas.db.nodes[node_id].coordinates.t:.2f}")

# Save our atlas
atlas.save()
```

## 3. Basic Retrieval

Let's start with some basic retrieval operations to demonstrate the system:

```python
# Simple semantic search
query = "crystal cave"
results = atlas.find_similar_nodes(query, k=3)

print(f"\nResults for query: '{query}'")
for node, score in results:
    print(f"Score: {score:.4f} | t={node.coordinates.t:.2f} | {node.content['text'][:100]}...")
```

Now let's examine how the temporal aspect affects our results:

```python
# Search with temporal focus on early part of the story
early_results = atlas.search_with_temporal_focus(
    query_text="Elara discoveries",
    temporal_focus=2.0,  # Focus on early content
    decay_rate=0.2,
    k=3
)

print(f"\nResults focused on early story (t=2.0):")
for node, score in early_results:
    print(f"Score: {score:.4f} | t={node.coordinates.t:.2f} | {node.content['text'][:100]}...")

# Search with temporal focus on later part of the story
late_results = atlas.search_with_temporal_focus(
    query_text="Elara discoveries",
    temporal_focus=15.0,  # Focus on later content
    decay_rate=0.2,
    k=3
)

print(f"\nResults focused on later story (t=15.0):")
for node, score in late_results:
    print(f"Score: {score:.4f} | t={node.coordinates.t:.2f} | {node.content['text'][:100]}...")
```

## 4. Advanced Coordinate-Based Queries

Now let's explore more sophisticated coordinate-based queries:

```python
# Create a query with coordinate filters using natural language
nl_query = "What did Elara find in the middle of the story?"
filtered_results = atlas.search_with_nl_query(nl_query, k=5)

print(f"\nResults for query with implied temporal filter: '{nl_query}'")
for node, score in filtered_results:
    print(f"Score: {score:.4f} | t={node.coordinates.t:.2f} | {node.content['text'][:100]}...")

# Custom retrieval parameters with directional bias and temporal focus
custom_results = atlas.search_with_retrieval_params(
    query_text="Elara's impact on the village",
    retrieval_params={
        "temporal_focus": 16.0,  # Late in the story
        "temporal_decay_rate": 0.15,
        "directional_bias": atlas.db.nodes[node_ids[-1]].coordinates.theta,  # Direction of the last node
        "directional_strength": 0.3
    },
    k=3
)

print(f"\nResults with custom retrieval parameters:")
for node, score in custom_results:
    print(f"Score: {score:.4f} | t={node.coordinates.t:.2f} | θ={node.coordinates.theta:.2f} | {node.content['text'][:100]}...")
```

## 5. Visualizing the Coordinate Space

Let's visualize our nodes in the polar-temporal coordinate space:

```python
# Initialize visualizer
visualizer = CoordinateVisualizer(output_dir="output/visualizations")

# Visualize nodes in various projections
vis_paths = visualizer.visualize_atlas(
    atlas=atlas,
    view_type="all",  # Generate all types of visualizations
    color_by="t"      # Color by temporal coordinate
)

# Display a temporal heat map (if in Jupyter, it would show the image)
# Here we just print the path
print(f"\nVisualization files generated at:")
for view_type, path in vis_paths.items():
    print(f"- {view_type}: {path}")
```

## 6. Finding Narratively Connected Content

Let's build a narrative chain through our content:

```python
# Function to find the next node in narrative sequence
def find_next_in_narrative(current_node_id, query_text, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []
    
    # Get current node's temporal position
    current_t = atlas.db.nodes[current_node_id].coordinates.t
    
    # Search for nodes that come after current node
    results = atlas.search_with_retrieval_params(
        query_text=query_text,
        retrieval_params={
            "temporal_focus": current_t + 2.0,  # Look ahead temporally
            "temporal_decay_rate": 0.15,
            "min_t": current_t + 0.5  # Only consider nodes after current
        },
        k=10
    )
    
    # Filter out nodes we've already used
    filtered_results = [(node, score) for node, score in results 
                        if node.id not in exclude_ids]
    
    if filtered_results:
        return filtered_results[0][0].id  # Return first matching node
    return None

# Build a narrative chain starting from the first node
narrative_chain = [node_ids[0]]  # Start with first node
current_node_id = node_ids[0]

# Build chain of 5 connected elements
for _ in range(4):
    next_node_id = find_next_in_narrative(
        current_node_id=current_node_id,
        query_text="Elara journey",
        exclude_ids=narrative_chain
    )
    
    if next_node_id:
        narrative_chain.append(next_node_id)
        current_node_id = next_node_id
    else:
        break

# Print the narrative chain
print("\nNarrative Chain:")
for i, node_id in enumerate(narrative_chain):
    node = atlas.db.nodes[node_id]
    print(f"{i+1}. [t={node.coordinates.t:.2f}] {node.content['text']}")
```

## 7. Generating RAG Context with Polar-Temporal Awareness

Finally, let's see how our system can be integrated with RAG for rich context generation:

```python
# Generate context and query using our temporal-spatial approach
context_prompt = atlas.answer_query_with_context(
    user_query="How did Elara's discovery change her village?",
    k=3  # Include 3 context elements
)

print("\nGenerated RAG Context with Polar-Temporal Awareness:")
print(context_prompt)
```

## 8. Conclusion

This notebook has demonstrated the core capabilities of the Temporal-Spatial Memory System with Polar Coordinates. We've seen how:

1. Content can be mapped to 4D polar-temporal coordinates
2. Temporal focus enables narrative-aware retrieval
3. Coordinate-based filtering enhances precision
4. Directional bias allows semantic direction preferences
5. The system can trace narrative sequences
6. RAG contexts can be temporally and spatially aware

These capabilities provide a richer and more nuanced approach to information retrieval, particularly for narrative content where temporal sequence and semantic relationships are crucial.

To continue exploring, you might try:

- Adding different types of content with varied semantic directions
- Experimenting with different z-coordinate layers for multi-perspective analysis
- Creating custom visualization for specific coordinate planes
- Integrating with LLM systems for contextually aware response generation 
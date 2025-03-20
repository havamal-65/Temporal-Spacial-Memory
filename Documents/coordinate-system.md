# Coordinate System for Temporal-Spatial Knowledge Representation

The coordinate system is the fundamental innovation in our knowledge database approach. It provides a mathematical foundation for organizing and retrieving information based on time, relevance, and conceptual relationships.

## Core Coordinate Structure

We use a three-dimensional cylindrical coordinate system:

```
Position(node) = (t, r, θ)
```

Where:
- **t (temporal)**: Position along the time axis
- **r (relevance)**: Radial distance from the central axis
- **θ (conceptual)**: Angular position representing semantic relationships

## Temporal Coordinate (t)

The temporal dimension has several unique properties:

1. **Continuous Progression**: Unlike discrete timestamps, our system treats time as a continuous axis
2. **Delta References**: Nodes at different temporal positions can reference earlier versions
3. **Temporal Density**: Important time periods may have higher node density
4. **Time Windows**: Operations typically focus on specific time ranges

Example implementation:
```python
class TemporalCoordinate:
    def __init__(self, absolute_time, reference_time=None):
        self.absolute_time = absolute_time
        self.reference_time = reference_time  # For delta references
```

## Relevance Coordinate (r)

The radial coordinate represents conceptual centrality:

1. **Core Concepts**: Lower r values (closer to center) for fundamental topics
2. **Peripheral Details**: Higher r values for specialized information
3. **Relevance Decay**: r may increase over time as topics become less central
4. **Bounded Range**: Typically normalized within a fixed range (e.g., 0-10)

This dimension effectively creates concentric "shells" of information based on importance.

## Conceptual Coordinate (θ)

The angular coordinate represents semantic relationships:

1. **Semantic Proximity**: Related concepts have similar θ values
2. **Topic Clusters**: Similar topics form clusters in angular regions
3. **Wrapping**: The angular nature (0-360°) creates a continuous space
4. **Multi-Revolution**: Complex knowledge spaces may use multiple revolutions

This is perhaps the most innovative aspect - using angular position to represent conceptual similarity.

## Coordinate Assignment Algorithms

Determining optimal coordinates is a critical challenge:

### Vector Embedding Projection

Converting high-dimensional embeddings to our coordinate system:

```python
def calculate_coordinates(topic, related_topics, current_time):
    # Get embedding for this topic
    embedding = embedding_model.encode(topic)
    
    # Calculate temporal coordinate
    t = current_time
    
    # Calculate relevance from centrality metrics
    centrality = calculate_centrality(topic, related_topics)
    r = map_to_radius(centrality)  # Lower centrality = higher radius
    
    # Calculate conceptual coordinate from embedding
    θ = project_to_angle(embedding, existing_topic_embeddings)
    
    return (t, r, θ)
```

### Adaptive Position Refinement

Coordinates evolve based on ongoing system learning:

```python
def refine_position(node, new_relationships):
    # Start with current position
    current_t, current_r, current_θ = node.position
    
    # Update relevance based on new centrality
    updated_r = adjust_radius(current_r, calculate_centrality(node, new_relationships))
    
    # Update angular position based on new relationships
    conceptual_forces = calculate_conceptual_forces(node, new_relationships)
    updated_θ = adjust_angle(current_θ, conceptual_forces)
    
    return (current_t, updated_r, updated_θ)
```

## Coordinate-Based Operations

The coordinate system enables efficient operations:

### Range Queries

Finding knowledge within specific time and conceptual ranges:

```python
def find_in_range(t_range, r_range, θ_range):
    # Use spatial indexing to efficiently find nodes in the specified ranges
    return spatial_index.query_range(
        min_t=t_range[0], max_t=t_range[1],
        min_r=r_range[0], max_r=r_range[1],
        min_θ=θ_range[0], max_θ=θ_range[1]
    )
```

### Nearest-Neighbor Searches

Finding related knowledge across conceptual space:

```python
def find_related(node, max_distance):
    t, r, θ = node.position
    
    # Calculate distance in cylindrical coordinates
    def distance(node1, node2):
        t1, r1, θ1 = node1.position
        t2, r2, θ2 = node2.position
        
        # Angular distance needs special handling for wrapping
        δθ = min(abs(θ1 - θ2), 360 - abs(θ1 - θ2))
        
        # Weighted distance formula
        return sqrt(w_t*(t1-t2)² + w_r*(r1-r2)² + w_θ*(δθ)²)
    
    return spatial_index.nearest_neighbors(node, distance_func=distance, k=10)
```

### Trajectory Analysis

Tracking concept evolution over time:

```python
def trace_concept_evolution(concept, start_time, end_time):
    # Find initial position of concept
    initial_node = find_by_content(concept, time=start_time)
    if not initial_node:
        return []
    
    trajectory = [initial_node]
    current = initial_node
    
    # Trace through time following position and delta references
    while current.position[0] < end_time:
        next_nodes = find_in_range(
            t_range=(current.position[0], current.position[0] + time_step),
            r_range=(0, max_radius),
            θ_range=(current.position[2] - angle_margin, current.position[2] + angle_margin)
        )
        
        # Find most likely continuation
        next_node = find_most_related(current, next_nodes)
        if not next_node:
            break
            
        trajectory.append(next_node)
        current = next_node
    
    return trajectory
```

## Advantages of Coordinate-Based Addressing

1. **Implicit Relationships**: Position itself encodes semantic meaning
2. **Efficient Traversal**: Related concepts are naturally close in coordinate space
3. **Temporal Continuity**: Topics maintain position coherence through time
4. **Intuitive Navigation**: The spatial metaphor maps well to human understanding
5. **Scalable Indexing**: Enables efficient spatial data structures for large knowledge bases

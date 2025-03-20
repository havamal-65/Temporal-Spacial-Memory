# Query Interface and API Design

This document outlines the query interface and API design for the temporal-spatial knowledge database, detailing how users would interact with the system to retrieve and manipulate information.

## Core Query Concepts

The temporal-spatial database requires specialized query capabilities that leverage its unique coordinate-based structure:

### 1. Coordinate-Based Queries

Queries can target specific regions in the coordinate space:

```python
# Find nodes within a specific coordinate range
def query_coordinate_range(
    time_range=(t_min, t_max),
    relevance_range=(r_min, r_max),
    angle_range=(θ_min, θ_max),
    branch_id=None  # Optional branch context
):
    """Retrieve nodes within the specified coordinate ranges"""
```

### 2. Spatial Proximity Queries

Find nodes that are "near" a reference node in conceptual space:

```python
# Find nodes related to a specific node
def query_related_nodes(
    node_id,
    max_distance=2.0,
    time_direction="any",  # "past", "future", "any"
    limit=20,
    traversal_strategy="direct"  # "direct", "transitive", "weighted"
):
    """Retrieve nodes that are conceptually related to the specified node"""
```

### 3. Temporal Evolution Queries

Track how concepts evolve over time:

```python
# Trace a concept through time
def query_concept_evolution(
    concept_name,
    start_time=None,
    end_time=None,
    include_branches=True,
    include_details=False  # Whether to include peripheral nodes
):
    """Trace how a concept evolves through time"""
```

### 4. Branch-Aware Queries

Handle queries that span multiple branches:

```python
# Find information across branches
def query_across_branches(
    query_terms,
    include_branches="all",  # "all", list of branch IDs, or "main"
    branch_depth=1,  # How many levels of child branches to include
    consolidate_results=True  # Whether to combine results from different branches
):
    """Search for information across multiple branches"""
```

## Query Language Design

The system would offer multiple query interfaces to accommodate different needs:

### 1. Structured API Calls

```python
# Example API usage
results = knowledge_base.query_related_nodes(
    node_id="concept:machine_learning",
    max_distance=1.5,
    time_direction="future",
    limit=10
)
```

### 2. Declarative Query Language

A specialized query language for more complex operations:

```
FIND NODES
WHERE CONCEPT CONTAINS "neural networks"
AND TIME BETWEEN 2020-01 AND 2023-05
AND RELEVANCE < 3.0
TRACE EVOLUTION
LIMIT 10
```

### 3. Natural Language Interface

For less technical users:

```
"Show me how the concept of transformers evolved from 2018 to present"
```

## Core API Methods

### Knowledge Retrieval

```python
class TemporalSpatialKnowledgeBase:
    def get_node(self, node_id):
        """Retrieve a specific node by ID"""
        
    def find_nodes(self, query_filters, sort_by=None, limit=None):
        """Find nodes matching specified filters"""
        
    def get_node_state(self, node_id, at_time=None):
        """Get the complete state of a node at a specific time"""
        
    def traverse_connections(self, start_node_id, max_depth=2, filters=None):
        """Traverse the connection graph from a starting node"""
```

### Knowledge Navigation

```python
class TemporalSpatialKnowledgeBase:
    def get_time_slice(self, time_point, branch_id=None, filters=None):
        """Get a slice of the knowledge structure at a specific time"""
        
    def get_branch(self, branch_id):
        """Get information about a specific branch"""
        
    def list_branches(self, filters=None, sort_by=None):
        """List available branches matching filters"""
        
    def find_branch_point(self, branch_id):
        """Find where a branch diverged from its parent"""
```

### Knowledge Modification

```python
class TemporalSpatialKnowledgeBase:
    def add_node(self, content, position=None, connections=None):
        """Add a new node to the knowledge base"""
        
    def update_node(self, node_id, content_updates, create_delta=True):
        """Update an existing node, optionally creating a delta node"""
        
    def connect_nodes(self, source_id, target_id, relationship_type=None, strength=1.0):
        """Create a connection between two nodes"""
        
    def create_branch(self, center_node_id, name=None, satellites=None):
        """Explicitly create a new branch with the specified center"""
```

### Analysis and Insights

```python
class TemporalSpatialKnowledgeBase:
    def detect_branch_candidates(self, threshold=0.8):
        """Find nodes that are candidates for becoming new branches"""
        
    def analyze_concept_importance(self, concept_name, time_range=None):
        """Analyze how important a concept is over time"""
        
    def find_emerging_concepts(self, time_range, min_growth=0.5):
        """Identify concepts that are rapidly growing in importance"""
        
    def analyze_knowledge_gaps(self, context=None):
        """Identify areas where knowledge is sparse or missing"""
```

## Query Examples for Different Domains

### Conversational AI Use Case

```python
# Find relevant context for a conversation
context_nodes = knowledge_base.query_related_nodes(
    node_id="conversation:current_topic",
    max_distance=2.0,
    time_direction="past",
    limit=10,
    traversal_strategy="weighted"
)

# Track how the conversation has evolved
conversation_evolution = knowledge_base.query_concept_evolution(
    concept_name="user_interest:machine_learning",
    start_time=conversation_start_time,
    end_time=current_time
)
```

### Research Knowledge Management Use Case

```python
# Find papers related to a concept across disciplines
related_papers = knowledge_base.find_nodes(
    query_filters={
        "type": "research_paper",
        "concept_distance": {
            "from": "concept:graph_neural_networks",
            "max_distance": 1.5
        },
        "time": {
            "from": "2020-01-01",
            "to": "2023-12-31"
        }
    },
    sort_by="relevance",
    limit=20
)

# Trace how a research area evolved
concept_trajectory = knowledge_base.query_concept_evolution(
    concept_name="research_area:transformer_models",
    start_time="2017-01-01",
    include_branches=True
)
```

### Software Development Use Case

```python
# Find all code affected by a change
affected_components = knowledge_base.traverse_connections(
    start_node_id="component:authentication_service",
    max_depth=3,
    filters={
        "relationship_type": "depends_on",
        "direction": "incoming"
    }
)

# Analyze architectural drift
architectural_analysis = knowledge_base.analyze_concept_importance(
    concept_name="architecture:microservices",
    time_range=("2020-01-01", "2023-12-31")
)
```

## API Response Structure

Responses would follow a consistent structure:

```json
{
  "status": "success",
  "query_info": {
    "type": "related_nodes",
    "parameters": { ... },
    "execution_time": 0.0123
  },
  "result": {
    "items": [
      {
        "id": "node:1234",
        "content": { ... },
        "position": {
          "time": 1672531200,
          "relevance": 1.2,
          "angle": 2.35,
          "branch_id": "branch:main"
        },
        "connections": [ ... ],
        "metadata": { ... }
      },
      ...
    ],
    "count": 5,
    "total_available": 42
  },
  "continuation_token": "eyJwYWdlIjogMiwgInNpemUiOiAyMH0="
}
```

## Advanced Query Features

### 1. Aggregation Queries

Analyze patterns across the knowledge structure:

```python
# Count nodes by concept category over time
knowledge_base.aggregate(
    group_by=["concept_category", "time_bucket(1 month)"],
    aggregates=[
        {"function": "count", "field": "id"},
        {"function": "avg", "field": "relevance"}
    ],
    filters={ ... }
)
```

### 2. Comparative Queries

Compare different time periods or branches:

```python
# Compare concept importance between two time periods
knowledge_base.compare(
    entity="concept:machine_learning",
    contexts=[
        {"time_range": ("2020-01-01", "2020-12-31")},
        {"time_range": ("2022-01-01", "2022-12-31")}
    ],
    metrics=["connection_count", "relevance", "mention_frequency"]
)
```

### 3. Predictive Queries

Use the mathematical prediction model to forecast knowledge evolution:

```python
# Predict emerging topics
predicted_topics = knowledge_base.predict_emerging_concepts(
    from_time=current_time,
    forecast_period="6 months",
    confidence_threshold=0.7
)
```

## Client Libraries and Interfaces

The system would provide multiple ways to interact with the API:

1. **Python Client Library**: For programmatic access and integration
2. **REST API**: For web and service integration
3. **GraphQL Endpoint**: For flexible, client-defined queries
4. **Web Interface**: Interactive visualization and exploration
5. **Command-Line Tools**: For scripting and automation

## Conclusion

The query interface and API design for the temporal-spatial knowledge database leverage its unique coordinate-based structure to enable powerful knowledge retrieval, navigation, and analysis. By supporting multiple query interfaces and providing domain-specific capabilities, the system can address diverse use cases while maintaining a consistent underlying data model.

The combination of coordinate-based queries, branch awareness, and temporal evolution tracking enables users to interact with knowledge in ways that aren't possible with traditional database systems, making it especially valuable for applications where understanding relationships and context over time is critical.

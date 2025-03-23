# Knowledge Tracker Example

This example demonstrates how to use the Temporal-Spatial Knowledge Database to track AI knowledge over time and space.

## Overview

The Knowledge Tracker is a specialized tool built on top of the Temporal-Spatial Knowledge Database that allows you to:

- Create and manage knowledge domains, topics, and facts
- Track changes in knowledge over time
- Visualize the relationships between different knowledge entities
- Monitor confidence levels and verification status of facts
- Analyze the spatial and temporal distribution of knowledge

## Components

- **KnowledgeTracker**: The main class that interfaces with the database and provides methods for managing knowledge entities.
- **VisualizationTool**: Provides various visualization methods to explore and analyze the knowledge stored in the database.
- **Example Application**: Demonstrates how to use the Knowledge Tracker and VisualizationTool to build a complete knowledge management system.

## Requirements

- Python 3.8+
- Matplotlib
- NetworkX
- NumPy
- Access to a running instance of the Temporal-Spatial Knowledge Database

## Usage

Run the example with:

```
python examples/knowledge_tracker/main.py
```

The example will:

1. Create a sample knowledge base with AI-related domains, topics, and facts
2. Simulate knowledge verification and updates over time
3. Generate various visualizations of the knowledge
4. Save the visualizations as PNG files

## Visualization Types

The example generates several types of visualizations:

- **Domain Visualization**: Shows the structure of a knowledge domain with its topics and facts as a network graph.
- **Topics Over Time**: Shows how topics have been added to a domain over time.
- **Confidence Distribution**: Displays the distribution of confidence values for facts in a topic.
- **Fact Verification History**: Shows the most verified facts in a topic.
- **Temporal-Spatial Distribution**: Visualizes how facts are distributed in temporal and spatial dimensions.

## API Reference

### KnowledgeTracker

```python
# Create a new knowledge domain
domain_id = tracker.add_domain(name="Domain Name", description="Domain Description")

# Add a topic to a domain
topic_id = tracker.add_topic(domain_id=domain_id, name="Topic Name", description="Topic Description")

# Add a fact to a topic
fact_id = tracker.add_fact(topic_id=topic_id, content="Fact content", source="Source", confidence=0.9)

# Connect related facts
tracker.add_related_fact(fact_id1, fact_id2)

# Get entities
domain = tracker.get_domain(domain_id)
topic = tracker.get_topic(topic_id)
facts = tracker.get_facts_by_topic(topic_id)

# Verify a fact
tracker.verify_fact(fact_id, new_confidence=0.95)
```

### VisualizationTool

```python
# Create a visualization tool
vis_tool = VisualizationTool(tracker)

# Visualize a domain
fig = vis_tool.visualize_domain(domain_id)

# Visualize topics over time
fig = vis_tool.visualize_topics_over_time(domain_id)

# Visualize confidence distribution
fig = vis_tool.visualize_confidence_distribution(topic_id)

# Visualize fact verification history
fig = vis_tool.visualize_fact_verification_history(topic_id)

# Visualize temporal-spatial distribution
fig = vis_tool.visualize_temporal_spatial_distribution(domain_id)
```

## Extending the Example

You can extend this example by:

1. Adding more visualization types
2. Implementing more sophisticated knowledge verification algorithms
3. Adding a web interface to interact with the knowledge base
4. Implementing automatic knowledge extraction from external sources
5. Creating specialized views for different types of knowledge domains

## License

This example is part of the Temporal-Spatial Knowledge Database project and is subject to its licensing terms. 
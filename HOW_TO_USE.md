# How to Use the Temporal-Spatial Memory Database

This guide explains how to use the Temporal-Spatial Memory Database in your projects.

## Getting Started

The Temporal-Spatial Memory Database is a specialized knowledge database that organizes information in a cylindrical mesh structure, with three primary dimensions:

1. **Time (longitudinal axis)** - When information was added or when it was relevant
2. **Distance (radial axis)** - How central or important the information is (smaller = more important)
3. **Angle (angular position)** - How concepts relate to each other conceptually

## Basic Usage

### Step 1: Create a Database Instance

```python
from src.models.mesh_tube import MeshTube

# Create a new database
db = MeshTube(name="My Knowledge Database", storage_path="data")
```

The `storage_path` parameter defines where database files will be stored.

### Step 2: Add Nodes (Knowledge Items)

Each piece of information is stored as a node with specific coordinates:

```python
# Add a core concept (close to center)
core_node = db.add_node(
    content={"topic": "Machine Learning", "description": "Core concept"},
    time=0,             # Time coordinate (0 = now, or base reference point)
    distance=0.1,       # Close to center (core topic)
    angle=0             # Angular position in the tube
)

# Add a related concept
related_node = db.add_node(
    content={"topic": "Neural Networks", "description": "A machine learning technique"},
    time=0,             # Same time point
    distance=0.3,       # Slightly less central
    angle=45            # 45 degrees from the first topic
)
```

### Step 3: Connect Related Nodes

Connect nodes that are conceptually related:

```python
# Create a bidirectional connection between nodes
db.connect_nodes(core_node.node_id, related_node.node_id)
```

### Step 4: Update Information Over Time (Delta Updates)

Add changes to existing information:

```python
# Update information about Neural Networks at a later time
updated_node = db.apply_delta(
    original_node=related_node,
    delta_content={"new_subtopic": "Deep Learning", "added_info": "New techniques"},
    time=1.0  # A later point in time
)
```

The database maintains the full history of changes.

### Step 5: Query the Database

#### Get a Single Node

```python
node = db.get_node(node_id)
```

#### Find Nodes at a Specific Time

```python
# Get all nodes at time=0 (with a tolerance of ±0.1)
nodes_at_time_0 = db.get_temporal_slice(time=0, tolerance=0.1)
```

#### Find Nearest Nodes

```python
# Find the 5 closest nodes to a reference node
nearest_nodes = db.get_nearest_nodes(reference_node, limit=5)
for node, distance in nearest_nodes:
    print(f"Node: {node.content.get('topic')}, Distance: {distance}")
```

#### Compute Full State After Updates

```python
# Get the complete state of a node after all delta updates
full_state = db.compute_node_state(node_id)
```

### Step 6: Save and Load the Database

```python
# Save the database
db.save("data/my_knowledge_db.json")

# Load a saved database
loaded_db = MeshTube.load("data/my_knowledge_db.json")
```

## Visualizing the Database

You can visualize the database using the provided visualization tools:

```python
# Visualize a 2D time slice
from visualize_database import visualize_2d_slice

visualize_2d_slice(
    mesh=db, 
    time=0,                # Time point to visualize 
    tolerance=0.1,         # Time range tolerance
    save_path='time_slice_0.png'  # Optional file path to save
)

# Visualize the 3D structure
from visualize_database import visualize_3d

visualize_3d(
    mesh=db,
    save_path='3d_visualization.png'  # Optional file path to save
)
```

## Example Code

For a complete example, see `example_usage.py`:

```python
python example_usage.py
```

This will create a sample database and demonstrate basic functionality.

To visualize the database:

```python
python visualize_database.py
```

This will generate visualizations in the `visualizations` directory.

## Advanced Usage

### Working with Node Properties

Each node has the following key properties:
- `node_id`: Unique identifier (UUID)
- `content`: Dictionary containing the actual data
- `time`: Longitudinal position
- `distance`: Radial distance from center
- `angle`: Angular position (0-360 degrees)
- `connections`: Set of connected node IDs
- `delta_references`: List of temporal predecessor references

### Understanding Delta Updates

Delta updates allow the database to maintain a history of changes while preserving the original information:

1. Original content is maintained
2. Delta changes are stored as separate nodes
3. Temporal relationships between versions are maintained
4. The full state can be computed by combining original content with all deltas

## Technical Details

The database uses:
- JSON for storage
- In-memory indices for efficient querying
- R-tree for spatial queries (when available)
- Cylindrical coordinate system for node positioning 
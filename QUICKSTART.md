# Mesh Tube Knowledge Database - Quick Start Guide

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Basic Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/mesh-tube-knowledge-db.git
   cd mesh-tube-knowledge-db
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Installation with R-tree Support (Optional)

For optimal spatial query performance, install with R-tree support:

1. Install required system dependencies:

   **On Ubuntu/Debian:**
   ```bash
   sudo apt-get install libspatialindex-dev
   ```

   **On macOS:**
   ```bash
   brew install spatialindex
   ```

   **On Windows:**
   The rtree package will attempt to download precompiled binaries when installing with pip.
   If this fails, you may need to download and install spatialindex separately.

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Usage Example

### Creating a Simple Knowledge Database

```python
from src.models.mesh_tube import MeshTube

# Create a new database
db = MeshTube("example_db", storage_path="./data")

# Add some nodes with content
node1 = db.add_node(
    content={"topic": "Artificial Intelligence", "description": "The field of AI research"},
    time=1.0,    # Time coordinate
    distance=0.0, # At the center (core topic)
    angle=0.0     # Angular position
)

node2 = db.add_node(
    content={"topic": "Machine Learning", "description": "A subset of AI focusing on learning from data"},
    time=1.5,
    distance=1.0, # Slightly away from center
    angle=45.0    # 45 degrees from the first topic
)

# Connect the nodes
db.connect_nodes(node1.node_id, node2.node_id)

# Add a change to the Machine Learning topic
ml_update = db.apply_delta(
    original_node=node2,
    delta_content={"subtopic": "Deep Learning", "added_on": "2023-06-01"},
    time=2.0  # Later point in time
)

# Find nodes near the AI topic
nearest_nodes = db.get_nearest_nodes(node1, limit=5)
for node, distance in nearest_nodes:
    print(f"Topic: {node.content.get('topic')}, Distance: {distance}")

# Get a time slice of the database
time_slice = db.get_temporal_slice(time=1.5, tolerance=0.5)
print(f"Found {len(time_slice)} nodes at time 1.5 (±0.5)")
```

### Running the Demo

The repository comes with built-in examples and visualizations:

```bash
# Run the main example
python src/example.py

# Run optimization benchmarks
python optimization_benchmark.py

# Display sample test data
python simple_display_test_data.py
```

## Using Optimizations

### Delta Compression

```python
# Compress delta chains to reduce storage
db.compress_deltas(max_chain_length=5)
```

### Loading Temporal Windows

```python
# Load only a specific time window
recent_data = db.load_temporal_window(start_time=10.0, end_time=20.0)
```

### Viewing Cache Statistics

```python
# Check cache performance
stats = db.get_cache_statistics()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
```

## Common Issues and Solutions

### RTree Import Error

If you encounter `ModuleNotFoundError: No module named 'rtree'` or `OSError: could not find or load spatialindex_c-64.dll`:

1. Ensure you've installed the system dependencies for spatialindex
2. Try reinstalling the rtree package:
   ```bash
   pip uninstall rtree
   pip install rtree
   ```

3. If problems persist, use the simplified implementation without R-tree:
   ```python
   # Use the simplified implementation (see simple_display_test_data.py)
   ```

### Memory Usage Concerns

If dealing with very large datasets:

1. Use the partial loading feature:
   ```python
   # Load only what you need
   window = db.load_temporal_window(start_time, end_time)
   ```

2. Adjust cache sizes:
   ```python
   # Reduce cache sizes
   db.state_cache.capacity = 50
   db.nearest_cache.capacity = 20
   ```

## Next Steps

1. Check the full [Documentation](DOCUMENTATION.md) for detailed API references
2. Review the [benchmark results](optimization_benchmark_results.png)
3. Explore the example code in the `src/` directory 
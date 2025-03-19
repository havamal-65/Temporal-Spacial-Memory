# Mesh Tube Knowledge Database

A novel temporal-spatial knowledge representation system designed specifically for tracking topics and conversations over time. The system represents information in a three-dimensional cylindrical "mesh tube" where:

- The longitudinal axis represents time progression
- The radial distance from center represents relevance to core topics
- The angular position represents conceptual relationships between topics

## Key Features

- **3D Knowledge Representation**: Spatial organization of knowledge with meaningful coordinates
- **Delta Encoding**: Efficient storage of evolving information through change-based references
- **Temporal-Spatial Navigation**: Navigate knowledge both by time and by conceptual proximity
- **Mathematical Prediction Model**: Forecasting which topics are likely to appear in future discussions
- **Flexible Connections**: Any node can connect to any other node to represent relationships

## Performance Optimizations

The system includes several advanced optimizations for production-ready performance:

- **Delta Compression**: Reduces storage overhead by up to 30% by intelligently merging older nodes in delta chains
- **R-tree Spatial Indexing**: Accelerates nearest-neighbor queries by using a specialized spatial index
- **Temporal-Aware Caching**: Improves performance for frequently accessed paths with time-based locality awareness
- **Partial Loading**: Supports loading only specific time windows to reduce memory usage for large datasets

In benchmark tests, these optimizations delivered:
- 37% faster knowledge traversal operations
- Reduced storage requirements for temporal data
- Significantly improved query response times for spatial proximity searches

## Why Mesh Tube?

Traditional database approaches struggle with representing evolving conversations and topic relationships over time. The Mesh Tube Knowledge Database solves this by:

- Integrating temporal and conceptual dimensions in a unified representation
- Providing natural navigation between related topics regardless of when they were discussed
- Enabling efficient storage through delta-encoding
- Supporting spatial indexing and retrieval methods

This makes it particularly well-suited for AI systems that need to maintain context through complex, evolving discussions.

## Real-World Applications

The Mesh Tube Knowledge Database is particularly valuable for:

1. **AI Assistants**: Maintaining conversational context across complex discussions
2. **Research Knowledge Graphs**: Tracking how scientific concepts evolve and relate over time
3. **Educational Systems**: Mapping conceptual hierarchies with temporal progression

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/mesh-tube-db.git
   cd mesh-tube-db
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the example script to see the Mesh Tube Knowledge Database in action:

```
python src/example.py
```

This will:
1. Create a sample knowledge database about AI topics
2. Add nodes and connections between them
3. Apply delta updates to show how topics evolve
4. Visualize the database in various ways
5. Demonstrate the prediction model

To benchmark the performance optimizations:

```
python optimization_benchmark.py
```

This will generate test data and measure the performance improvements from:
- Spatial indexing with R-tree
- Delta compression
- Temporal-aware caching
- Partial data loading

## Project Structure

```
mesh-tube-db/
├── data/                 # Storage directory for saved databases
├── src/                  # Source code
│   ├── models/           # Core data models
│   │   ├── node.py       # Node representation
│   │   └── mesh_tube.py  # Main database class
│   ├── utils/            # Utility functions
│   │   └── position_calculator.py  # Spatial positioning utilities
│   ├── visualization/    # Visualization tools
│   │   └── mesh_visualizer.py      # Visualization tools
│   └── example.py        # Example usage script
├── tests/                # Test directory
├── benchmark_data/       # Benchmark test data
└── optimization_benchmark.py  # Performance optimization benchmark
```

## Future Improvements

- 3D visualization using WebGL or similar technology
- Advanced prediction models using machine learning
- Distributed storage for large-scale applications
- Query language for complex temporal-spatial searches
- GPU acceleration for large-scale spatial computations

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
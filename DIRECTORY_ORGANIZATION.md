# Directory Organization

This document outlines the organization of the Temporal-Spatial Memory project directories.

## Root Directory

- `README.md`: Main project documentation
- `requirements.txt`: Python package dependencies
- `LICENSE`: Project license information
- `setup.py`, `setup.cfg`, `pyproject.toml`: Python package configuration files
- `.gitignore`: Git ignore configuration

## Code Directories

- `src/`: Main source code for the project
  - `src/core/`: Core functionality
  - `src/models/`: Data models and schemas
  - `src/utils/`: Utility functions
  - `src/visualization/`: Visualization components

- `tests/`: Test modules and test data
  - `tests/unit/`: Unit tests
  - `tests/integration/`: Integration tests
  - `tests/performance/`: Performance tests

- `benchmarks/`: Performance benchmarking code
  - `benchmarks/data_generators/`: Test data generators
  - `benchmarks/scenarios/`: Benchmark scenarios

## Documentation and Examples

- `docs/`: Detailed documentation
  - `docs/api/`: API documentation
  - `docs/examples/`: Documentation examples
  - `docs/benchmarks/`: Benchmark documentation

- `examples/`: Example code for using the library
  - `examples/basic_usage.py`: Simple example showing basic usage
  - `examples/process_hobbit.py`: Example for processing The Hobbit
  - `examples/process_hobbit_with_graphrag.py`: Example using GraphRAG for processing
  - `examples/v2_usage.py`: Example using v2 API

## Data Directories

- `data/`: Data files for the project
- `Input/`: Input files for examples and tests
- `Output/`: Generated output files

## GraphRAG Integration

- `graphrag/`: GraphRAG library integration

## Other Directories

- `to_delete/`: Files and directories that are planned for removal
  - Includes unused or deprecated files

## Best Practices

1. **Keep Code Organized**: Place new code in the appropriate directories based on functionality
2. **Use Examples**: Add new examples in the examples directory
3. **Document New Features**: Update documentation in the docs directory
4. **Test Coverage**: Add tests for new functionality in the tests directory
5. **Cleanup Strategy**: Place files for deletion in to_delete for review before removing 
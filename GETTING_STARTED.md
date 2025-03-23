# Getting Started with Temporal-Spatial Memory Database

This guide will help you get the database running on your system, with solutions for common issues.

## Installation

### Step 1: Clone and Install Dependencies

```bash
# Clone the repository (if you haven't already)
git clone <repository-url>
cd temporal-spatial-memory

# Run the installation script
python install_dev.py
```

The installation script will:
1. Install the package in development mode
2. Install all required dependencies
3. Handle special cases like RTree on Windows

### Step 2: Run the Database

The database uses RTree for spatial indexing, providing excellent performance for spatial queries.

## Running Tests

### Test the Database

```bash
# Run the database test
python test_simple_db.py
```

If all tests pass, the database is working correctly.

## Running Benchmarks

```bash
# Run benchmarks
python run_simplified_benchmark.py
```

This will create a test database, measure performance of different operations, and generate a performance graph in the `benchmark_results` directory.

## Common Issues and Solutions

### RTree Import Error on Windows

If you see this error:
```
OSError: could not find or load spatialindex_c-64.dll
```

Solutions:
1. Try reinstalling RTree with the Windows wheel: 
   ```
   pip uninstall rtree
   pip install wheel
   pip install rtree
   ```
2. If that doesn't work, check that you have the Microsoft Visual C++ Redistributable installed on your system.
3. Ensure your PATH environment variable includes the location of the DLL.

### Missing Dependency Errors

If you see import errors, make sure you've run the installation script:
```
python install_dev.py
```

## Getting Help

If you encounter issues not covered here, please check the full documentation or open an issue on the repository. 
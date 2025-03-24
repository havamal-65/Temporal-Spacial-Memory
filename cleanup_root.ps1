# Create additional directories
mkdir -Force src\scripts
mkdir -Force src\visualization
mkdir -Force src\benchmarks
mkdir -Force docs\api
mkdir -Force docs\examples
mkdir -Force docs\benchmarks

# Move Python scripts to src/scripts
Move-Item -Force process_*.py src\scripts\
Move-Item -Force run_*.py src\scripts\
Move-Item -Force test_*.py src\scripts\
Move-Item -Force example_usage.py src\scripts\
Move-Item -Force simple_test.py src\scripts\
Move-Item -Force display_test_data.py src\scripts\
Move-Item -Force simple_display_test_data.py src\scripts\

# Move visualization files
Move-Item -Force interactive_visualizer.py src\visualization\
Move-Item -Force visualization_launcher.html src\visualization\
Move-Item -Force visualize_database.py src\visualization\

# Move benchmark files
Move-Item -Force benchmark.py src\benchmarks\
Move-Item -Force benchmark_runner.py src\benchmarks\
Move-Item -Force optimization_benchmark.py src\benchmarks\
Move-Item -Force comparison_visualization.py src\benchmarks\
Move-Item -Force simple_benchmark.py src\benchmarks\

# Move documentation
Move-Item -Force HOW_TO_USE.md docs\
Move-Item -Force GETTING_STARTED.md docs\
Move-Item -Force QUICKSTART.md docs\
Move-Item -Force DOCUMENTATION.md docs\
Move-Item -Force PERFORMANCE.md docs\
Move-Item -Force mesh_tube_knowledge_database.md docs\

# Move test and integration files
Move-Item -Force integration_test_runner.py src\scripts\
Move-Item -Force run_integration_tests.py src\scripts\
Move-Item -Force run_integration_tests.bat src\scripts\
Move-Item -Force fix_runner.py src\scripts\

# Move conversation files
Move-Item -Force conversation_*.py src\scripts\
Move-Item -Force conversations\* Input\Conversations\

# Clean up empty directories
Remove-Item -Force benchmark_data -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force benchmark_results -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force data -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force visualizations -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force conversations -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force __pycache__ -Recurse -ErrorAction SilentlyContinue
Remove-Item -Force temporal_spatial_db.egg-info -Recurse -ErrorAction SilentlyContinue

# Remove unnecessary files
Remove-Item -Force "h origin master" -ErrorAction SilentlyContinue
Remove-Item -Force repomix-output.xml -ErrorAction SilentlyContinue
Remove-Item -Force organize_files.ps1 -ErrorAction SilentlyContinue

Write-Host "Project root directory has been cleaned up and organized." 
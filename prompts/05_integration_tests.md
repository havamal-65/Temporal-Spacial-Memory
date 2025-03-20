# Integration Tests and Performance Benchmarking for Temporal-Spatial Database

## Objective
Develop comprehensive integration tests and performance benchmarks to validate the complete Temporal-Spatial Knowledge Database system, ensuring all components work together correctly and meet performance targets.

## Core Integration Test Framework

1. **Test Environment Setup**
   Implement a reusable test environment:

```python
class TestEnvironment:
    def __init__(self, test_data_path: str = "test_data", use_in_memory: bool = True):
        """
        Initialize test environment
        
        Args:
            test_data_path: Directory for test data
            use_in_memory: Whether to use in-memory storage (vs. on-disk)
        """
        self.test_data_path = test_data_path
        self.use_in_memory = use_in_memory
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.query_engine = None
        
    def setup(self) -> None:
        """Set up a fresh environment with all components"""
        # Clean up previous test data
        if os.path.exists(self.test_data_path) and not self.use_in_memory:
            shutil.rmtree(self.test_data_path)
            os.makedirs(self.test_data_path)
            
        # Create storage components
        if self.use_in_memory:
            self.node_store = InMemoryNodeStore()
            self.delta_store = InMemoryDeltaStore()
        else:
            self.node_store = RocksDBNodeStore(os.path.join(self.test_data_path, "nodes"))
            self.delta_store = RocksDBDeltaStore(os.path.join(self.test_data_path, "deltas"))
            
        # Create index components
        self.spatial_index = RTree(max_entries=50, min_entries=20)
        self.temporal_index = TemporalIndex(resolution=0.1)
        
        # Create combined index
        self.combined_index = SpatioTemporalIndex(
            spatial_index=self.spatial_index,
            temporal_index=self.temporal_index
        )
        
        # Create query engine
        self.query_engine = QueryEngine(
            node_store=self.node_store,
            delta_store=self.delta_store,
            index=self.combined_index
        )
        
    def teardown(self) -> None:
        """Clean up test environment"""
        # Close connections
        if not self.use_in_memory:
            self.node_store.close()
            self.delta_store.close()
            
        # Clean up resources
        self.node_store = None
        self.delta_store = None
        self.spatial_index = None
        self.temporal_index = None
        self.combined_index = None
        self.query_engine = None
```

2. **Test Data Generation**
   Create data generators for realistic test scenarios:

```python
class TestDataGenerator:
    def __init__(self, seed: int = 42):
        """
        Initialize test data generator
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        
    def generate_node(self, 
                     position: Optional[Tuple[float, float, float]] = None,
                     content_complexity: str = "medium") -> Node:
        """
        Generate a test node
        
        Args:
            position: Optional (t, r, θ) position, random if None
            content_complexity: 'simple', 'medium', or 'complex'
            
        Returns:
            A randomly generated node
        """
        # Generate position if not provided
        if position is None:
            t = self.random.uniform(0, 100)
            r = self.random.uniform(0, 10)
            theta = self.random.uniform(0, 2 * math.pi)
            position = (t, r, theta)
            
        # Generate content based on complexity
        content = self._generate_content(content_complexity)
        
        # Create node
        return Node(
            id=uuid4(),
            content=content,
            position=position,
            connections=[]
        )
        
    def generate_node_cluster(self,
                             center: Tuple[float, float, float],
                             radius: float,
                             count: int,
                             time_variance: float = 1.0) -> List[Node]:
        """
        Generate a cluster of related nodes
        
        Args:
            center: Central position (t, r, θ)
            radius: Maximum distance from center
            count: Number of nodes to generate
            time_variance: Variation in time dimension
            
        Returns:
            List of generated nodes
        """
        nodes = []
        base_t, base_r, base_theta = center
        
        for _ in range(count):
            # Generate position with gaussian distribution around center
            t_offset = self.random.gauss(0, time_variance)
            r_offset = self.random.gauss(0, radius/3)  # 3-sigma within radius
            theta_offset = self.random.gauss(0, radius/(3 * base_r)) if base_r > 0 else self.random.uniform(0, 2 * math.pi)
            
            # Calculate new position
            t = base_t + t_offset
            r = max(0, base_r + r_offset)  # Ensure r is non-negative
            theta = (base_theta + theta_offset) % (2 * math.pi)  # Wrap to [0, 2π)
            
            # Create node
            node = self.generate_node(position=(t, r, theta))
            nodes.append(node)
            
        return nodes
        
    def generate_evolving_node_sequence(self,
                                       base_position: Tuple[float, float, float],
                                       num_evolution_steps: int,
                                       time_step: float = 1.0,
                                       change_magnitude: float = 0.2) -> List[Node]:
        """
        Generate a sequence of nodes that represent evolution of a concept
        
        Args:
            base_position: Starting position (t, r, θ)
            num_evolution_steps: Number of evolution steps
            time_step: Time increment between steps
            change_magnitude: How much the content changes per step
        
        Returns:
            List of nodes in temporal sequence
        """
        nodes = []
        base_t, base_r, base_theta = base_position
        
        # Generate base node
        base_node = self.generate_node(position=base_position)
        nodes.append(base_node)
        
        # Track content for incremental changes
        current_content = copy.deepcopy(base_node.content)
        
        # Generate evolution
        for i in range(1, num_evolution_steps):
            # Update position
            t = base_t + i * time_step
            r = base_r + self.random.uniform(-0.1, 0.1) * i  # Slight variation in relevance
            theta = base_theta + self.random.uniform(-0.05, 0.05) * i  # Slight conceptual drift
            
            # Update content
            current_content = self._evolve_content(current_content, change_magnitude)
            
            # Create node
            node = Node(
                id=uuid4(),
                content=current_content,
                position=(t, r, theta),
                connections=[],
                origin_reference=base_node.id
            )
            nodes.append(node)
            
        return nodes
        
    def _generate_content(self, complexity: str) -> Dict[str, Any]:
        """Generate content with specified complexity"""
        if complexity == "simple":
            return {
                "title": self._random_title(),
                "description": self._random_paragraph()
            }
        elif complexity == "medium":
            return {
                "title": self._random_title(),
                "description": self._random_paragraph(),
                "attributes": {
                    "category": self._random_category(),
                    "tags": self._random_tags(3),
                    "importance": self.random.uniform(0, 1)
                },
                "related_info": self._random_paragraph()
            }
        else:  # complex
            return {
                "title": self._random_title(),
                "description": self._random_paragraph(),
                "attributes": {
                    "category": self._random_category(),
                    "tags": self._random_tags(5),
                    "importance": self.random.uniform(0, 1),
                    "metadata": {
                        "created_at": time.time(),
                        "version": f"1.{self.random.randint(0, 10)}",
                        "status": self._random_choice(["draft", "review", "approved", "published"])
                    }
                },
                "sections": [
                    {
                        "heading": self._random_title(),
                        "content": self._random_paragraph(),
                        "subsections": [
                            {
                                "heading": self._random_title(),
                                "content": self._random_paragraph()
                            } for _ in range(self.random.randint(1, 3))
                        ]
                    } for _ in range(self.random.randint(2, 4))
                ],
                "related_info": self._random_paragraph()
            }
            
    def _evolve_content(self, content: Dict[str, Any], magnitude: float) -> Dict[str, Any]:
        """Create an evolved version of the content"""
        # Implementation of content evolution
        # Deep copy then modify with probability based on magnitude
        pass
        
    # Various helper methods for generating random test data
    def _random_title(self) -> str:
        # Generate a random title
        pass
        
    def _random_paragraph(self) -> str:
        # Generate a random paragraph
        pass
        
    def _random_tags(self, count: int) -> List[str]:
        # Generate random tags
        pass
        
    def _random_category(self) -> str:
        # Generate random category
        pass
        
    def _random_choice(self, options: List[Any]) -> Any:
        # Choose random element
        return self.random.choice(options)
```

## Integration Test Scenarios

1. **End-to-End System Test**
   Implement tests that exercise the full system:

```python
class EndToEndTest:
    def __init__(self, 
                 env: TestEnvironment, 
                 generator: TestDataGenerator):
        self.env = env
        self.generator = generator
        
    def setup(self):
        """Set up the test environment"""
        self.env.setup()
        
    def teardown(self):
        """Clean up after tests"""
        self.env.teardown()
        
    def test_node_storage_and_retrieval(self):
        """Test basic node storage and retrieval"""
        # Generate test node
        node = self.generator.generate_node()
        
        # Store node
        self.env.node_store.put(node)
        
        # Retrieve node
        retrieved_node = self.env.node_store.get(node.id)
        
        # Verify node was retrieved correctly
        assert retrieved_node is not None
        assert retrieved_node.id == node.id
        assert retrieved_node.content == node.content
        assert retrieved_node.position == node.position
        
    def test_spatial_index_queries(self):
        """Test spatial index queries"""
        # Generate cluster of nodes
        center = (50.0, 5.0, math.pi)
        nodes = self.generator.generate_node_cluster(
            center=center,
            radius=2.0,
            count=20
        )
        
        # Store nodes and build index
        for node in nodes:
            self.env.node_store.put(node)
            coord = SpatioTemporalCoordinate(*node.position)
            self.env.spatial_index.insert(coord, node.id)
            
        # Test nearest neighbor query
        test_coord = SpatioTemporalCoordinate(
            center[0], center[1], center[2])
        nearest = self.env.spatial_index.nearest_neighbors(
            test_coord, k=5)
        
        # Verify results
        assert len(nearest) == 5
        
        # Test range query
        query_rect = Rectangle(
            min_t=center[0] - 5, max_t=center[0] + 5,
            min_r=center[1] - 2, max_r=center[1] + 2,
            min_theta=center[2] - 0.5, max_theta=center[2] + 0.5
        )
        range_results = self.env.spatial_index.range_query(query_rect)
        
        # Verify range results
        assert len(range_results) > 0
        
    def test_delta_chain_evolution(self):
        """Test delta chain evolution and reconstruction"""
        # Generate evolving node sequence
        base_position = (10.0, 1.0, 0.5 * math.pi)
        nodes = self.generator.generate_evolving_node_sequence(
            base_position=base_position,
            num_evolution_steps=10,
            time_step=1.0
        )
        
        # Store base node
        base_node = nodes[0]
        self.env.node_store.put(base_node)
        
        # Create detector and store
        detector = ChangeDetector()
        
        # Process evolution
        previous_content = base_node.content
        previous_delta_id = None
        
        for i in range(1, len(nodes)):
            node = nodes[i]
            # Detect changes
            delta = detector.create_delta(
                node_id=base_node.id,
                previous_content=previous_content,
                new_content=node.content,
                timestamp=node.position[0],
                previous_delta_id=previous_delta_id
            )
            
            # Store delta
            self.env.delta_store.store_delta(delta)
            
            # Update for next iteration
            previous_content = node.content
            previous_delta_id = delta.delta_id
            
        # Test state reconstruction
        reconstructor = StateReconstructor(self.env.delta_store)
        
        # Reconstruct at each time point
        for i in range(1, len(nodes)):
            node = nodes[i]
            reconstructed = reconstructor.reconstruct_state(
                node_id=base_node.id,
                origin_content=base_node.content,
                target_timestamp=node.position[0]
            )
            
            # Verify reconstruction
            assert reconstructed == node.content
            
    def test_combined_query_functionality(self):
        """Test combined spatiotemporal queries"""
        # Generate data with temporal and spatial patterns
        # Implementation
        pass
```

2. **Workflow-Based Tests**
   Implement tests that simulate realistic usage patterns:

```python
class WorkflowTest:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        self.env = env
        self.generator = generator
        
    def test_knowledge_growth_workflow(self):
        """Test a workflow simulating knowledge growth over time"""
        # Simulate the growth of a knowledge graph
        # Implementation
        pass
        
    def test_knowledge_evolution_workflow(self):
        """Test a workflow simulating concept evolution"""
        # Simulate the evolution of concepts over time
        # Implementation
        pass
        
    def test_branching_workflow(self):
        """Test the branching mechanism"""
        # Simulate the creation and management of branches
        # Implementation
        pass
```

## Performance Benchmarks

1. **Basic Operation Benchmarks**
   Implement benchmarks for fundamental operations:

```python
class BasicOperationBenchmark:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        self.env = env
        self.generator = generator
        
    def benchmark_node_insertion(self, node_count: int = 10000):
        """Benchmark node insertion performance"""
        # Generate nodes
        nodes = [self.generator.generate_node() for _ in range(node_count)]
        
        # Measure insertion time
        start_time = time.time()
        for node in nodes:
            self.env.node_store.put(node)
        end_time = time.time()
        
        insertion_time = end_time - start_time
        ops_per_second = node_count / insertion_time
        
        return {
            "operation": "node_insertion",
            "count": node_count,
            "total_time": insertion_time,
            "ops_per_second": ops_per_second
        }
        
    def benchmark_node_retrieval(self, node_count: int = 10000):
        """Benchmark node retrieval performance"""
        # Generate and store nodes
        node_ids = []
        for _ in range(node_count):
            node = self.generator.generate_node()
            self.env.node_store.put(node)
            node_ids.append(node.id)
            
        # Measure retrieval time
        start_time = time.time()
        for node_id in node_ids:
            self.env.node_store.get(node_id)
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        ops_per_second = node_count / retrieval_time
        
        return {
            "operation": "node_retrieval",
            "count": node_count,
            "total_time": retrieval_time,
            "ops_per_second": ops_per_second
        }
        
    def benchmark_spatial_indexing(self, node_count: int = 10000):
        """Benchmark spatial indexing performance"""
        # Implementation
        pass
        
    def benchmark_delta_reconstruction(self, chain_length: int = 100):
        """Benchmark delta chain reconstruction performance"""
        # Implementation
        pass
```

2. **Scalability Benchmarks**
   Implement benchmarks to test scaling behavior:

```python
class ScalabilityBenchmark:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        self.env = env
        self.generator = generator
        
    def benchmark_increasing_node_count(self, 
                                      max_nodes: int = 1000000, 
                                      step: int = 100000):
        """Benchmark performance with increasing node count"""
        results = []
        
        for node_count in range(step, max_nodes + step, step):
            # Generate nodes
            nodes = [self.generator.generate_node() for _ in range(step)]
            
            # Measure insertion time
            start_time = time.time()
            for node in nodes:
                self.env.node_store.put(node)
                coord = SpatioTemporalCoordinate(*node.position)
                self.env.spatial_index.insert(coord, node.id)
            end_time = time.time()
            
            # Measure query time
            query_times = []
            for _ in range(100):  # 100 random queries
                t = self.generator.random.uniform(0, 100)
                r = self.generator.random.uniform(0, 10)
                theta = self.generator.random.uniform(0, 2 * math.pi)
                coord = SpatioTemporalCoordinate(t, r, theta)
                
                query_start = time.time()
                self.env.spatial_index.nearest_neighbors(coord, k=10)
                query_end = time.time()
                
                query_times.append(query_end - query_start)
            
            # Record results
            results.append({
                "node_count": node_count,
                "insertion_time": end_time - start_time,
                "avg_query_time": sum(query_times) / len(query_times),
                "min_query_time": min(query_times),
                "max_query_time": max(query_times)
            })
            
        return results
        
    def benchmark_increasing_delta_chain_length(self,
                                              max_length: int = 1000,
                                              step: int = 100):
        """Benchmark performance with increasing delta chain length"""
        # Implementation
        pass
        
    def benchmark_memory_usage(self, max_nodes: int = 1000000, step: int = 100000):
        """Benchmark memory usage with increasing data size"""
        # Implementation using memory_profiler
        pass
```

3. **Comparative Benchmarks**
   Implement benchmarks comparing different configurations:

```python
class ComparativeBenchmark:
    def __init__(self):
        self.results = {}
        
    def compare_storage_implementations(self, 
                                      node_count: int = 10000,
                                      implementations: List[str] = ["memory", "rocksdb"]):
        """Compare different storage implementations"""
        for impl in implementations:
            # Create appropriate environment
            if impl == "memory":
                env = TestEnvironment(use_in_memory=True)
            else:
                env = TestEnvironment(use_in_memory=False, 
                                       test_data_path=f"test_data_{impl}")
            
            generator = TestDataGenerator()
            benchmark = BasicOperationBenchmark(env, generator)
            
            # Run benchmarks
            env.setup()
            insertion_results = benchmark.benchmark_node_insertion(node_count)
            retrieval_results = benchmark.benchmark_node_retrieval(node_count)
            env.teardown()
            
            # Store results
            self.results[f"{impl}_insertion"] = insertion_results
            self.results[f"{impl}_retrieval"] = retrieval_results
            
        return self.results
        
    def compare_indexing_strategies(self,
                                  node_count: int = 10000,
                                  strategies: List[Dict] = [
                                      {"name": "default", "max_entries": 50, "min_entries": 20},
                                      {"name": "small_nodes", "max_entries": 20, "min_entries": 8},
                                      {"name": "large_nodes", "max_entries": 100, "min_entries": 40}
                                  ]):
        """Compare different indexing strategies"""
        # Implementation
        pass
        
    def compare_optimization_strategies(self,
                                      chain_length: int = 1000,
                                      strategies: List[str] = ["none", "checkpoints", "compaction"]):
        """Compare different chain optimization strategies"""
        # Implementation
        pass
```

## Benchmark Visualization

1. **Results Formatting**
   Implement functions to format benchmark results:

```python
def format_benchmark_results(results: Dict) -> pd.DataFrame:
    """Convert benchmark results to a pandas DataFrame"""
    # Implementation
    pass

def save_results_to_file(results: Dict, filename: str):
    """Save benchmark results to file (JSON and CSV)"""
    # Implementation
    pass
```

2. **Visualization Functions**
   Implement visualization of benchmark results:

```python
def plot_operation_performance(results: pd.DataFrame, operation: str):
    """Plot performance of a specific operation"""
    # Implementation using matplotlib or similar
    pass
    
def plot_scalability_results(results: pd.DataFrame):
    """Plot scalability test results"""
    # Implementation
    pass
    
def plot_comparison_results(results: pd.DataFrame, metric: str):
    """Plot comparison of different implementations/strategies"""
    # Implementation
    pass
```

## System Load Testing

1. **Concurrent Access Testing**
   Implement tests for concurrent access:

```python
class ConcurrentAccessTest:
    def __init__(self, env: TestEnvironment, generator: TestDataGenerator):
        self.env = env
        self.generator = generator
        
    def test_concurrent_reads(self, num_threads: int = 10, operations_per_thread: int = 1000):
        """Test concurrent read operations"""
        # Implementation using threading
        pass
        
    def test_concurrent_writes(self, num_threads: int = 10, operations_per_thread: int = 100):
        """Test concurrent write operations"""
        # Implementation
        pass
        
    def test_mixed_workload(self, num_threads: int = 20, read_ratio: float = 0.8):
        """Test mixed read/write workload"""
        # Implementation
        pass
```

2. **Resource Utilization Monitoring**
   Implement resource monitoring:

```python
class ResourceMonitor:
    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.cpu_usage = []
        self.memory_usage = []
        self.disk_io = []
        self.stop_event = threading.Event()
        
    def start_monitoring(self):
        """Start monitoring resources"""
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring resources"""
        self.stop_event.set()
        self.monitor_thread.join()
        
    def _monitor_resources(self):
        """Resource monitoring loop"""
        # Implementation using psutil or similar
        pass
        
    def get_results(self):
        """Get monitoring results"""
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_io": self.disk_io
        }
        
    def plot_results(self):
        """Plot resource utilization"""
        # Implementation
        pass
```

## Real-World Dataset Testing

1. **Dataset Import**
   Implement functions to import real-world datasets:

```python
def import_dataset(dataset_path: str, dataset_type: str) -> List[Node]:
    """Import dataset and convert to nodes"""
    # Implementation for different dataset types
    pass
```

2. **Real-World Query Simulation**
   Implement tests using real-world query patterns:

```python
class RealWorldQueryTest:
    def __init__(self, env: TestEnvironment):
        self.env = env
        
    def load_dataset(self, dataset_path: str, dataset_type: str):
        """Load dataset into test environment"""
        # Implementation
        pass
        
    def run_realistic_query_workload(self, query_file: str):
        """Run a set of realistic queries"""
        # Implementation
        pass
```

## Success Criteria

1. All integration tests pass, demonstrating correctness of the complete system
2. Performance benchmarks show acceptable throughput for core operations:
   - Node insertion: >= 10,000 nodes/second
   - Node retrieval: >= 50,000 nodes/second
   - Spatial queries: <= 10ms for nearest neighbor queries
   - Delta chain reconstruction: <= 100ms for chains of 100 deltas
3. Scalability tests demonstrate sub-linear growth in query time with increasing data size
4. Resource utilization remains within acceptable bounds:
   - Memory usage grows linearly with data size
   - CPU utilization stays below 80% under load
5. System handles concurrent access without errors or deadlocks
6. Performance comparing favorably to baseline systems on equivalent workloads 
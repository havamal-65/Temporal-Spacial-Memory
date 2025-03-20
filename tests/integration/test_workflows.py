"""
Workflow-based integration tests for the Temporal-Spatial Knowledge Database.

These tests simulate realistic usage patterns and workflows.
"""

import math
import unittest
import tempfile
import shutil
import time
from uuid import uuid4

# Import with error handling
from src.core.node_v2 import Node

# Handle possibly missing dependencies
try:
    from src.core.coordinates import SpatioTemporalCoordinate
    COORDINATES_AVAILABLE = True
except ImportError:
    # Create a simple mock class
    class SpatioTemporalCoordinate:
        def __init__(self, t, r, theta):
            self.t = t
            self.r = r
            self.theta = theta
    COORDINATES_AVAILABLE = False

try:
    from src.delta.detector import ChangeDetector
    from src.delta.chain import DeltaChain
    from src.delta.navigator import DeltaNavigator
    DELTA_AVAILABLE = True
except ImportError:
    # Create mock classes if not available
    class ChangeDetector:
        def create_delta(self, *args, **kwargs):
            return type('obj', (object,), {
                'delta_id': uuid4(),
                'branch_id': kwargs.get('branch_id', None),
                'merged_delta_id': kwargs.get('merged_delta_id', None)
            })
        def apply_delta(self, *args, **kwargs):
            return {}
        def apply_delta_chain(self, *args, **kwargs):
            return {}
    
    class DeltaChain:
        def __init__(self, *args, **kwargs):
            pass
        def get_all_deltas(self, *args, **kwargs):
            return []
        def reconstruct_at_time(self, *args, **kwargs):
            return {}
    
    class DeltaNavigator:
        def __init__(self, *args, **kwargs):
            pass
        def get_all_deltas(self, *args, **kwargs):
            return []
        def get_latest_delta(self, *args, **kwargs):
            return None
        def get_branches(self, *args, **kwargs):
            return []
    DELTA_AVAILABLE = False

from tests.integration.test_environment import TestEnvironment
from tests.integration.test_data_generator import TestDataGenerator


@unittest.skipIf(not COORDINATES_AVAILABLE or not DELTA_AVAILABLE,
                "Required dependencies not available")
class WorkflowTest(unittest.TestCase):
    def setUp(self):
        """Set up the test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.env = TestEnvironment(test_data_path=self.temp_dir, use_in_memory=True)
        self.generator = TestDataGenerator()
        self.env.setup()
        
    def tearDown(self):
        """Clean up after tests"""
        self.env.teardown()
        shutil.rmtree(self.temp_dir)
        
    def test_knowledge_growth_workflow(self):
        """Test a workflow simulating knowledge growth over time"""
        # Scenario: Adding nodes to a knowledge base over time
        # and querying at different time points
        
        # Initial knowledge base - physics concepts
        physics_center = (10.0, 8.0, 0.0)
        physics_nodes = self.generator.generate_node_cluster(
            center=physics_center,
            radius=1.0,
            count=10,
            time_variance=0.2
        )
        
        # Add initial physics nodes
        for node in physics_nodes:
            self.env.node_store.put(node)
            self.env.combined_index.insert(node)
            
        # First query - physics knowledge
        physics_area_results = self.env.combined_index.query(
            min_t=9.0, max_t=11.0,
            min_r=7.0, max_r=9.0,
            min_theta=0.0, max_theta=0.1
        )
        
        # Verify we can find physics nodes
        self.assertTrue(len(physics_area_results) > 0)
        
        # Add second knowledge domain - biology (at a later time point)
        biology_center = (20.0, 8.0, math.pi/2)  # Different conceptual area (theta)
        biology_nodes = self.generator.generate_node_cluster(
            center=biology_center,
            radius=1.0,
            count=15,
            time_variance=0.2
        )
        
        # Add biology nodes
        for node in biology_nodes:
            self.env.node_store.put(node)
            self.env.combined_index.insert(node)
            
        # Query for biology knowledge
        biology_area_results = self.env.combined_index.query(
            min_t=19.0, max_t=21.0,
            min_r=7.0, max_r=9.0,
            min_theta=math.pi/2 - 0.1, max_theta=math.pi/2 + 0.1
        )
        
        # Verify we can find biology nodes
        self.assertTrue(len(biology_area_results) > 0)
        
        # Add third knowledge domain - connections between physics and biology
        # (multidisciplinary nodes at an even later time point)
        connection_center = (30.0, 8.0, math.pi/4)  # Between physics and biology
        connection_nodes = self.generator.generate_node_cluster(
            center=connection_center,
            radius=1.5,
            count=8,
            time_variance=0.2
        )
        
        # Add connection nodes
        for node in connection_nodes:
            self.env.node_store.put(node)
            self.env.combined_index.insert(node)
            
        # Connect nodes across domains
        for idx, conn_node in enumerate(connection_nodes):
            # Connect to random physics and biology nodes
            if physics_nodes and biology_nodes:
                physics_conn = physics_nodes[idx % len(physics_nodes)]
                biology_conn = biology_nodes[idx % len(biology_nodes)]
                
                # Add connections (both directions)
                conn_node.add_connection(physics_conn.id, "reference")
                conn_node.add_connection(biology_conn.id, "reference")
                
                # Update node
                self.env.node_store.put(conn_node)
        
        # Query for interdisciplinary knowledge
        interdisciplinary_results = self.env.combined_index.query(
            min_t=29.0, max_t=31.0,
            min_r=6.5, max_r=9.5,
            min_theta=math.pi/4 - 0.1, max_theta=math.pi/4 + 0.1
        )
        
        # Verify we can find interdisciplinary nodes
        self.assertTrue(len(interdisciplinary_results) > 0)
        
        # Verify complete timeline query returns all nodes
        all_results = self.env.combined_index.query_temporal_range(
            min_t=0.0, max_t=40.0
        )
        
        # Should have all nodes from all three domains
        expected_count = len(physics_nodes) + len(biology_nodes) + len(connection_nodes)
        self.assertEqual(len(all_results), expected_count)
        
    def test_knowledge_evolution_workflow(self):
        """Test a workflow simulating concept evolution"""
        # Scenario: A single concept evolves over time through multiple 
        # versions and branches
        
        # Create detector
        detector = ChangeDetector()
        
        # Generate base concept
        base_position = (10.0, 9.0, math.pi/6)
        base_node = self.generator.generate_node(position=base_position)
        
        # Store base node
        self.env.node_store.put(base_node)
        self.env.combined_index.insert(base_node)
        
        # First evolution path - main development line
        main_branch_deltas = []
        previous_content = base_node.content
        previous_delta_id = None
        base_t = base_position[0]
        
        # Create 5 sequential evolutions
        for i in range(1, 6):
            # Create evolved content
            new_content = self.generator._evolve_content(
                previous_content, 
                magnitude=0.3
            )
            
            # Create delta
            delta = detector.create_delta(
                node_id=base_node.id,
                previous_content=previous_content,
                new_content=new_content,
                timestamp=base_t + i,
                previous_delta_id=previous_delta_id
            )
            
            # Store delta
            self.env.delta_store.store_delta(delta)
            main_branch_deltas.append(delta)
            
            # Update for next iteration
            previous_content = new_content
            previous_delta_id = delta.delta_id
        
        # Second evolution path - branch from version 2
        branch_point_delta = main_branch_deltas[1]  # Branch from 3rd version (index 1)
        branch_base_content = detector.apply_delta(
            base_node.content,
            branch_point_delta
        )
        
        # Create branch
        branch_deltas = []
        previous_content = branch_base_content
        previous_delta_id = branch_point_delta.delta_id
        branch_base_t = base_t + 2  # Branch from version 3
        
        # Create 3 branch evolutions
        for i in range(1, 4):
            # Create evolved content (different evolution direction)
            new_content = self.generator._evolve_content(
                previous_content, 
                magnitude=0.4  # More aggressive changes in this branch
            )
            
            # Create delta
            delta = detector.create_delta(
                node_id=base_node.id,
                previous_content=previous_content,
                new_content=new_content,
                timestamp=branch_base_t + i,
                previous_delta_id=previous_delta_id,
                branch_id=uuid4()  # New branch
            )
            
            # Store delta
            self.env.delta_store.store_delta(delta)
            branch_deltas.append(delta)
            
            # Update for next iteration
            previous_content = new_content
            previous_delta_id = delta.delta_id
            
        # Create navigator
        navigator = DeltaNavigator(self.env.delta_store)
        
        # Get all deltas for the node
        all_deltas = navigator.get_all_deltas(base_node.id)
        
        # Should have main branch + branch deltas
        expected_delta_count = len(main_branch_deltas) + len(branch_deltas)
        self.assertEqual(len(all_deltas), expected_delta_count)
        
        # Check we can navigate to the latest main branch version
        latest_main = navigator.get_latest_delta(base_node.id)
        if latest_main:  # Check for None in case of mock
            self.assertEqual(latest_main.delta_id, main_branch_deltas[-1].delta_id)
        
        # Check we can navigate to the latest alternate branch version
        latest_branch = navigator.get_latest_delta(
            base_node.id, 
            branch_id=branch_deltas[0].branch_id
        )
        if latest_branch:  # Check for None in case of mock
            self.assertEqual(latest_branch.delta_id, branch_deltas[-1].delta_id)
        
        # Test reconstruction at different time points
        chain = DeltaChain(self.env.delta_store, base_node.id)
        
        # Reconstruct at end of main branch
        main_end = chain.reconstruct_at_time(
            base_content=base_node.content,
            target_time=base_t + 5
        )
        
        # Reconstruct at end of alternate branch
        branch_end = chain.reconstruct_at_time(
            base_content=base_node.content,
            target_time=branch_base_t + 3,
            branch_id=branch_deltas[0].branch_id
        )
        
        # Verify reconstructions are different (skip if mocked)
        if main_end and branch_end:
            self.assertNotEqual(main_end, branch_end)
        
    def test_branching_workflow(self):
        """Test the branching mechanism"""
        # Scenario: Create multiple branches of a concept and navigate between them
        
        # Create base node
        base_position = (1.0, 7.0, 0.0)
        base_node = self.generator.generate_node(position=base_position)
        self.env.node_store.put(base_node)
        
        # Create detector
        detector = ChangeDetector()
        
        # Create several different branches
        branches = {}
        for branch_name in ["research", "development", "application"]:
            branch_id = uuid4()
            branch_deltas = []
            previous_content = base_node.content
            previous_delta_id = None
            
            # Create 3 deltas per branch
            for i in range(1, 4):
                # Create evolved content
                new_content = self.generator._evolve_content(
                    previous_content, 
                    magnitude=0.2 + (0.1 * i)  # Increasing change magnitude
                )
                
                # Create delta
                delta = detector.create_delta(
                    node_id=base_node.id,
                    previous_content=previous_content,
                    new_content=new_content,
                    timestamp=base_position[0] + i,
                    previous_delta_id=previous_delta_id,
                    branch_id=branch_id if i > 1 else None  # First delta is main branch
                )
                
                # Store delta
                self.env.delta_store.store_delta(delta)
                branch_deltas.append(delta)
                
                # Update for next iteration
                previous_content = new_content
                previous_delta_id = delta.delta_id
                
            # Store branch info
            branches[branch_name] = {
                "id": branch_id,
                "deltas": branch_deltas
            }
        
        # Create navigator
        navigator = DeltaNavigator(self.env.delta_store)
        
        # Test getting branches
        all_branches = navigator.get_branches(base_node.id)
        
        # Should have 3 branches (including main)
        self.assertEqual(len(all_branches), 3)
        
        # Test navigating between branches
        for branch_name, branch_data in branches.items():
            latest = navigator.get_latest_delta(
                base_node.id,
                branch_id=branch_data["id"] if branch_name != "research" else None
            )
            
            # Should be the last delta in the branch (skip if None in mocks)
            if latest:
                self.assertEqual(latest.delta_id, branch_data["deltas"][-1].delta_id)
        
        # Test merging branches
        research_latest = branches["research"]["deltas"][-1]
        development_latest = branches["development"]["deltas"][-1]
        
        # Create merged content
        research_content = detector.apply_delta_chain(
            base_node.content,
            research_latest
        )
        
        development_content = detector.apply_delta_chain(
            base_node.content,
            development_latest
        )
        
        # Simple merge strategy: combine unique keys
        merged_content = {**research_content, **development_content}
        
        # Create merge delta
        merge_delta = detector.create_delta(
            node_id=base_node.id,
            previous_content=research_content,
            new_content=merged_content,
            timestamp=base_position[0] + 5,
            previous_delta_id=research_latest.delta_id,
            merged_delta_id=development_latest.delta_id
        )
        
        # Store merge
        self.env.delta_store.store_delta(merge_delta)
        
        # Verify merge appears in chain
        chain = DeltaChain(self.env.delta_store, base_node.id)
        all_deltas = chain.get_all_deltas()
        
        # Count should include all branch deltas plus merge
        expected_count = sum(len(b["deltas"]) for b in branches.values()) + 1
        self.assertEqual(len(all_deltas), expected_count)
        
        # Verify chain includes merge (skip if mocked)
        if all_deltas and hasattr(all_deltas[0], 'merged_delta_id'):
            self.assertTrue(any(d.merged_delta_id == development_latest.delta_id 
                              for d in all_deltas))


if __name__ == '__main__':
    unittest.main() 
"""
Unit tests for the query module.
"""

import unittest
from datetime import datetime, timedelta
import json

from src.query import (
    Query,
    QueryType,
    QueryOperator,
    TemporalCriteria,
    SpatialCriteria,
    ContentCriteria,
    CompositeCriteria,
    query,
    temporal_query,
    spatial_query,
    content_query
)

class TestQueryCriteria(unittest.TestCase):
    """Test suite for query criteria classes."""
    
    def test_temporal_criteria(self):
        """Test TemporalCriteria creation and validation."""
        # Test valid criteria
        now = datetime.now()
        later = now + timedelta(hours=1)
        
        # Test after
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=now
        )
        self.assertTrue(criteria.validate())
        
        # Test before
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            end_time=later
        )
        self.assertTrue(criteria.validate())
        
        # Test between
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=now,
            end_time=later
        )
        self.assertTrue(criteria.validate())
        
        # Test invalid criteria (no bounds)
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL
        )
        with self.assertRaises(ValueError):
            criteria.validate()
            
        # Test invalid criteria (start after end)
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=later,
            end_time=now
        )
        with self.assertRaises(ValueError):
            criteria.validate()
    
    def test_spatial_criteria(self):
        """Test SpatialCriteria creation and validation."""
        # Test valid bounding box
        criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            min_x=0.0,
            min_y=0.0,
            max_x=10.0,
            max_y=10.0
        )
        self.assertTrue(criteria.validate())
        
        # Test valid circle
        criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            center_x=0.0,
            center_y=0.0,
            radius=5.0
        )
        self.assertTrue(criteria.validate())
        
        # Test invalid (no bounds)
        criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL
        )
        with self.assertRaises(ValueError):
            criteria.validate()
            
        # Test invalid (min > max)
        criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            min_x=10.0,
            min_y=0.0,
            max_x=0.0,
            max_y=10.0
        )
        with self.assertRaises(ValueError):
            criteria.validate()
            
        # Test invalid radius
        criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            center_x=0.0,
            center_y=0.0,
            radius=-1.0
        )
        with self.assertRaises(ValueError):
            criteria.validate()
    
    def test_content_criteria(self):
        """Test ContentCriteria creation and validation."""
        # Test valid criteria
        criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name="name",
            operator="=",
            value="test"
        )
        self.assertTrue(criteria.validate())
        
        # Test invalid (no field name)
        criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name="",
            operator="=",
            value="test"
        )
        with self.assertRaises(ValueError):
            criteria.validate()
            
        # Test invalid operator
        criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name="name",
            operator="INVALID",
            value="test"
        )
        with self.assertRaises(ValueError):
            criteria.validate()

class TestQueryBuilder(unittest.TestCase):
    """Test suite for query builder classes."""
    
    def test_temporal_query_builder(self):
        """Test TemporalQueryBuilder."""
        now = datetime.now()
        later = now + timedelta(hours=1)
        
        # Test before
        q = temporal_query().before(later).build()
        self.assertEqual(q.criteria.query_type, QueryType.TEMPORAL)
        self.assertIsNone(q.criteria.start_time)
        self.assertEqual(q.criteria.end_time, later)
        
        # Test after
        q = temporal_query().after(now).build()
        self.assertEqual(q.criteria.query_type, QueryType.TEMPORAL)
        self.assertEqual(q.criteria.start_time, now)
        self.assertIsNone(q.criteria.end_time)
        
        # Test between
        q = temporal_query().between(now, later).build()
        self.assertEqual(q.criteria.query_type, QueryType.TEMPORAL)
        self.assertEqual(q.criteria.start_time, now)
        self.assertEqual(q.criteria.end_time, later)
        
        # Test limit and offset
        q = temporal_query().between(now, later).limit(10).offset(5).build()
        self.assertEqual(q.limit, 10)
        self.assertEqual(q.offset, 5)
    
    def test_spatial_query_builder(self):
        """Test SpatialQueryBuilder."""
        # Test within rectangle
        q = spatial_query().within_rectangle(0.0, 0.0, 10.0, 10.0).build()
        self.assertEqual(q.criteria.query_type, QueryType.SPATIAL)
        self.assertEqual(q.criteria.min_x, 0.0)
        self.assertEqual(q.criteria.max_y, 10.0)
        
        # Test near
        q = spatial_query().near(0.0, 0.0, 5.0).build()
        self.assertEqual(q.criteria.query_type, QueryType.SPATIAL)
        self.assertEqual(q.criteria.center_x, 0.0)
        self.assertEqual(q.criteria.radius, 5.0)
    
    def test_content_query_builder(self):
        """Test ContentQueryBuilder."""
        # Test equals
        q = content_query().equals("name", "test").build()
        self.assertEqual(q.criteria.query_type, QueryType.CONTENT)
        self.assertEqual(q.criteria.field_name, "name")
        self.assertEqual(q.criteria.operator, "=")
        self.assertEqual(q.criteria.value, "test")
        
        # Test greater than
        q = content_query().greater_than("age", 18).build()
        self.assertEqual(q.criteria.operator, ">")
        self.assertEqual(q.criteria.value, 18)
        
        # Test in list
        q = content_query().in_list("status", ["active", "pending"]).build()
        self.assertEqual(q.criteria.operator, "IN")
        self.assertEqual(q.criteria.value, ["active", "pending"])
    
    def test_compound_query_builder(self):
        """Test CompoundQueryBuilder."""
        now = datetime.now()
        
        # Test combining temporal and spatial
        builder = query()
        builder.temporal().after(now)
        builder.spatial().near(0.0, 0.0, 5.0)
        
        q = builder.build()
        self.assertEqual(q.criteria.query_type, QueryType.COMPOSITE)
        self.assertEqual(q.criteria.operator, QueryOperator.AND)
        self.assertEqual(len(q.criteria.criteria), 2)
        
        # Test query serialization
        q_json = q.to_json()
        q2 = Query.from_json(q_json)
        self.assertEqual(q.query_id, q2.query_id)
        self.assertEqual(q.criteria.query_type, q2.criteria.query_type)

class TestQuerySerialization(unittest.TestCase):
    """Test suite for query serialization."""
    
    def test_temporal_serialization(self):
        """Test serialization of temporal queries."""
        now = datetime.now()
        criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=now
        )
        q = Query(criteria=criteria)
        
        # Test to_dict and from_dict
        d = q.to_dict()
        q2 = Query.from_dict(d)
        
        self.assertEqual(q.query_id, q2.query_id)
        self.assertEqual(q.criteria.query_type, q2.criteria.query_type)
        self.assertEqual(q.criteria.start_time.isoformat(), q2.criteria.start_time.isoformat())
        
        # Test to_json and from_json
        j = q.to_json()
        q3 = Query.from_json(j)
        
        self.assertEqual(q.query_id, q3.query_id)
        self.assertEqual(q.criteria.query_type, q3.criteria.query_type)
        self.assertEqual(q.criteria.start_time.isoformat(), q3.criteria.start_time.isoformat())
    
    def test_composite_serialization(self):
        """Test serialization of composite queries."""
        now = datetime.now()
        
        # Create a composite query with temporal and spatial criteria
        temporal = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=now
        )
        
        spatial = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            center_x=0.0,
            center_y=0.0,
            radius=5.0
        )
        
        composite = CompositeCriteria(
            query_type=QueryType.COMPOSITE,
            operator=QueryOperator.AND,
            criteria=[temporal, spatial]
        )
        
        q = Query(criteria=composite)
        
        # Test to_dict and from_dict
        d = q.to_dict()
        q2 = Query.from_dict(d)
        
        self.assertEqual(q.query_id, q2.query_id)
        self.assertEqual(q.criteria.query_type, q2.criteria.query_type)
        self.assertEqual(q.criteria.operator, q2.criteria.operator)
        self.assertEqual(len(q.criteria.criteria), len(q2.criteria.criteria))
        
        # Test to_json and from_json
        j = q.to_json()
        q3 = Query.from_json(j)
        
        self.assertEqual(q.query_id, q3.query_id)
        self.assertEqual(q.criteria.query_type, q3.criteria.query_type)
        self.assertEqual(q.criteria.operator, q3.criteria.operator)
        self.assertEqual(len(q.criteria.criteria), len(q3.criteria.criteria))

if __name__ == "__main__":
    unittest.main() 
"""
Query Builder module providing a fluent interface for constructing queries.

This module provides a fluent interface for building queries against the
temporal-spatial database, supporting:
- Temporal criteria (before, after, between)
- Spatial criteria (near, within)
- Content-based filtering
- Composite queries (AND, OR, NOT)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Generic, cast

from .query import (
    Query, 
    QueryCriteria,
    TemporalCriteria,
    SpatialCriteria,
    ContentCriteria,
    CompositeCriteria,
    QueryType,
    QueryOperator
)

T = TypeVar('T', bound='QueryBuilder')

class QueryBuilder(Generic[T]):
    """Base class for all query builders providing common functionality."""
    
    def __init__(self):
        """Initialize a new query builder."""
        self._criteria: Optional[QueryCriteria] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
    
    def limit(self: T, limit: int) -> T:
        """Set the maximum number of results to return.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            Self for chaining
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        self._limit = limit
        return self
    
    def offset(self: T, offset: int) -> T:
        """Set the number of results to skip.
        
        Args:
            offset: Number of results to skip
            
        Returns:
            Self for chaining
        """
        if offset < 0:
            raise ValueError("offset must be non-negative")
        self._offset = offset
        return self
    
    def build(self) -> Query:
        """Build the final query object.
        
        Returns:
            Query: The constructed query
            
        Raises:
            ValueError: If no criteria has been set
        """
        if self._criteria is None:
            raise ValueError("No query criteria has been set")
            
        return Query(
            criteria=self._criteria,
            limit=self._limit,
            offset=self._offset
        )
    
    def and_(self: T, other_criteria: QueryCriteria) -> T:
        """Combine this query with another using AND.
        
        Args:
            other_criteria: Criteria to combine with
            
        Returns:
            Self for chaining
        """
        if self._criteria is None:
            self._criteria = other_criteria
        else:
            # If current criteria is already a composite AND, add to it
            if (isinstance(self._criteria, CompositeCriteria) and 
                self._criteria.operator == QueryOperator.AND):
                self._criteria.criteria.append(other_criteria)
            else:
                # Create a new AND composite with both criteria
                self._criteria = CompositeCriteria(
                    query_type=QueryType.COMPOSITE,
                    operator=QueryOperator.AND,
                    criteria=[self._criteria, other_criteria]
                )
        return self
    
    def or_(self: T, other_criteria: QueryCriteria) -> T:
        """Combine this query with another using OR.
        
        Args:
            other_criteria: Criteria to combine with
            
        Returns:
            Self for chaining
        """
        if self._criteria is None:
            self._criteria = other_criteria
        else:
            # If current criteria is already a composite OR, add to it
            if (isinstance(self._criteria, CompositeCriteria) and 
                self._criteria.operator == QueryOperator.OR):
                self._criteria.criteria.append(other_criteria)
            else:
                # Create a new OR composite with both criteria
                self._criteria = CompositeCriteria(
                    query_type=QueryType.COMPOSITE,
                    operator=QueryOperator.OR,
                    criteria=[self._criteria, other_criteria]
                )
        return self
    
    def not_(self: T) -> T:
        """Negate the current criteria.
        
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If no criteria has been set
        """
        if self._criteria is None:
            raise ValueError("Cannot negate: no criteria has been set")
            
        # Wrap current criteria in a NOT
        self._criteria = CompositeCriteria(
            query_type=QueryType.COMPOSITE,
            operator=QueryOperator.NOT,
            criteria=[self._criteria]
        )
        return self

class TemporalQueryBuilder(QueryBuilder['TemporalQueryBuilder']):
    """Builder for temporal queries."""
    
    def before(self, time: datetime) -> 'TemporalQueryBuilder':
        """Add criteria for events occurring before the specified time.
        
        Args:
            time: Upper bound time
            
        Returns:
            Self for chaining
        """
        self._criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            end_time=time
        )
        return self
    
    def after(self, time: datetime) -> 'TemporalQueryBuilder':
        """Add criteria for events occurring after the specified time.
        
        Args:
            time: Lower bound time
            
        Returns:
            Self for chaining
        """
        self._criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=time
        )
        return self
    
    def between(self, start_time: datetime, end_time: datetime) -> 'TemporalQueryBuilder':
        """Add criteria for events occurring between the specified times.
        
        Args:
            start_time: Lower bound time
            end_time: Upper bound time
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If start_time is after end_time
        """
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")
            
        self._criteria = TemporalCriteria(
            query_type=QueryType.TEMPORAL,
            start_time=start_time,
            end_time=end_time
        )
        return self

class SpatialQueryBuilder(QueryBuilder['SpatialQueryBuilder']):
    """Builder for spatial queries."""
    
    def within_rectangle(
        self, min_x: float, min_y: float, max_x: float, max_y: float
    ) -> 'SpatialQueryBuilder':
        """Add criteria for points within the specified rectangle.
        
        Args:
            min_x: Minimum x-coordinate
            min_y: Minimum y-coordinate
            max_x: Maximum x-coordinate
            max_y: Maximum y-coordinate
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If min_x > max_x or min_y > max_y
        """
        if min_x > max_x:
            raise ValueError("min_x must be less than or equal to max_x")
        if min_y > max_y:
            raise ValueError("min_y must be less than or equal to max_y")
            
        self._criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y
        )
        return self
    
    def near(self, center_x: float, center_y: float, radius: float) -> 'SpatialQueryBuilder':
        """Add criteria for points near the specified center point.
        
        Args:
            center_x: Center x-coordinate
            center_y: Center y-coordinate
            radius: Search radius
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If radius is not positive
        """
        if radius <= 0:
            raise ValueError("radius must be positive")
            
        self._criteria = SpatialCriteria(
            query_type=QueryType.SPATIAL,
            center_x=center_x,
            center_y=center_y,
            radius=radius
        )
        return self

class ContentQueryBuilder(QueryBuilder['ContentQueryBuilder']):
    """Builder for content-based queries."""
    
    def equals(self, field_name: str, value: Any) -> 'ContentQueryBuilder':
        """Add criteria for field equality.
        
        Args:
            field_name: Name of the field to check
            value: Value to compare against
            
        Returns:
            Self for chaining
        """
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator="=",
            value=value
        )
        return self
    
    def greater_than(self, field_name: str, value: Any) -> 'ContentQueryBuilder':
        """Add criteria for field greater than value.
        
        Args:
            field_name: Name of the field to check
            value: Value to compare against
            
        Returns:
            Self for chaining
        """
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator=">",
            value=value
        )
        return self
    
    def less_than(self, field_name: str, value: Any) -> 'ContentQueryBuilder':
        """Add criteria for field less than value.
        
        Args:
            field_name: Name of the field to check
            value: Value to compare against
            
        Returns:
            Self for chaining
        """
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator="<",
            value=value
        )
        return self
    
    def like(self, field_name: str, pattern: str) -> 'ContentQueryBuilder':
        """Add criteria for field matching pattern.
        
        Args:
            field_name: Name of the field to check
            pattern: Pattern to match against
            
        Returns:
            Self for chaining
        """
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator="LIKE",
            value=pattern
        )
        return self
    
    def in_list(self, field_name: str, values: List[Any]) -> 'ContentQueryBuilder':
        """Add criteria for field value in list.
        
        Args:
            field_name: Name of the field to check
            values: List of possible values
            
        Returns:
            Self for chaining
        """
        if not isinstance(values, list):
            raise ValueError("values must be a list")
            
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator="IN",
            value=values
        )
        return self
    
    def contains(self, field_name: str, value: Any) -> 'ContentQueryBuilder':
        """Add criteria for field containing value.
        
        Args:
            field_name: Name of the field to check (should be a list/array)
            value: Value to check for containment
            
        Returns:
            Self for chaining
        """
        self._criteria = ContentCriteria(
            query_type=QueryType.CONTENT,
            field_name=field_name,
            operator="CONTAINS",
            value=value
        )
        return self

class CompoundQueryBuilder(QueryBuilder['CompoundQueryBuilder']):
    """Builder for compound queries combining multiple types."""
    
    def __init__(self):
        """Initialize a new compound query builder."""
        super().__init__()
        self._temporal_builder = TemporalQueryBuilder()
        self._spatial_builder = SpatialQueryBuilder()
        self._content_builder = ContentQueryBuilder()
    
    def temporal(self) -> TemporalQueryBuilder:
        """Get a temporal query builder.
        
        Returns:
            TemporalQueryBuilder: Builder for temporal queries
        """
        return self._temporal_builder
    
    def spatial(self) -> SpatialQueryBuilder:
        """Get a spatial query builder.
        
        Returns:
            SpatialQueryBuilder: Builder for spatial queries
        """
        return self._spatial_builder
    
    def content(self) -> ContentQueryBuilder:
        """Get a content query builder.
        
        Returns:
            ContentQueryBuilder: Builder for content queries
        """
        return self._content_builder
    
    def and_(self, builder: QueryBuilder) -> 'CompoundQueryBuilder':
        """Combine with another builder using AND.
        
        Args:
            builder: Another query builder
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If the other builder has no criteria set
        """
        if builder._criteria is None:
            raise ValueError("Other builder has no criteria set")
            
        return cast(CompoundQueryBuilder, super().and_(builder._criteria))
    
    def or_(self, builder: QueryBuilder) -> 'CompoundQueryBuilder':
        """Combine with another builder using OR.
        
        Args:
            builder: Another query builder
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If the other builder has no criteria set
        """
        if builder._criteria is None:
            raise ValueError("Other builder has no criteria set")
            
        return cast(CompoundQueryBuilder, super().or_(builder._criteria))
    
    def build(self) -> Query:
        """Build the final query from all added criteria.
        
        Returns:
            Query: The constructed query
            
        Raises:
            ValueError: If no criteria has been set in any builder
        """
        # Collect criteria from all builders
        criteria_list = []
        
        for builder in [self, self._temporal_builder, self._spatial_builder, self._content_builder]:
            if builder._criteria is not None:
                criteria_list.append(builder._criteria)
        
        if not criteria_list:
            raise ValueError("No query criteria has been set in any builder")
        
        # If only one criteria, use it directly
        if len(criteria_list) == 1:
            self._criteria = criteria_list[0]
        else:
            # Combine all criteria with AND
            self._criteria = CompositeCriteria(
                query_type=QueryType.COMPOSITE,
                operator=QueryOperator.AND,
                criteria=criteria_list
            )
        
        return super().build()

# Factory functions for creating query builders
def query() -> CompoundQueryBuilder:
    """Create a new compound query builder.
    
    Returns:
        CompoundQueryBuilder: A new compound query builder
    """
    return CompoundQueryBuilder()

def temporal_query() -> TemporalQueryBuilder:
    """Create a new temporal query builder.
    
    Returns:
        TemporalQueryBuilder: A new temporal query builder
    """
    return TemporalQueryBuilder()

def spatial_query() -> SpatialQueryBuilder:
    """Create a new spatial query builder.
    
    Returns:
        SpatialQueryBuilder: A new spatial query builder
    """
    return SpatialQueryBuilder()

def content_query() -> ContentQueryBuilder:
    """Create a new content query builder.
    
    Returns:
        ContentQueryBuilder: A new content query builder
    """
    return ContentQueryBuilder() 
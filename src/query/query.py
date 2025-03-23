"""
Query representation and manipulation classes.

This module defines the core Query class and related structures used to represent
queries against the temporal-spatial database.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import uuid

class QueryType(Enum):
    """Enumeration of supported query types."""
    TEMPORAL = auto()
    SPATIAL = auto()
    CONTENT = auto()
    COMPOSITE = auto()
    FULL_TEXT = auto()

class QueryOperator(Enum):
    """Enumeration of query operators for composite queries."""
    AND = auto()
    OR = auto()
    NOT = auto()

@dataclass
class QueryCriteria:
    """Base class for all query criteria."""
    query_type: QueryType
    
    def validate(self) -> bool:
        """Validate that the criteria is well-formed.
        
        Returns:
            bool: True if criteria is valid, raises ValueError otherwise
        """
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert criteria to a dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "query_type": self.query_type.name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryCriteria':
        """Create criteria from dictionary representation.
        
        Args:
            data: Dictionary representation of criteria
            
        Returns:
            QueryCriteria: New criteria instance
        """
        query_type = QueryType[data["query_type"]]
        return cls(query_type=query_type)

@dataclass
class TemporalCriteria(QueryCriteria):
    """Criteria for temporal queries."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        self.query_type = QueryType.TEMPORAL
    
    def validate(self) -> bool:
        """Validate temporal criteria.
        
        Ensures that at least one time bound is set and that start_time <= end_time
        if both are specified.
        
        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        if self.start_time is None and self.end_time is None:
            raise ValueError("At least one of start_time or end_time must be specified")
        
        if (self.start_time is not None and 
            self.end_time is not None and 
            self.start_time > self.end_time):
            raise ValueError("start_time must be less than or equal to end_time")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = super().to_dict()
        if self.start_time:
            result["start_time"] = self.start_time.isoformat()
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemporalCriteria':
        """Create from dictionary representation."""
        start_time = None
        end_time = None
        
        if "start_time" in data:
            start_time = datetime.fromisoformat(data["start_time"])
        if "end_time" in data:
            end_time = datetime.fromisoformat(data["end_time"])
            
        return cls(
            query_type=QueryType.TEMPORAL,
            start_time=start_time,
            end_time=end_time
        )

@dataclass
class SpatialCriteria(QueryCriteria):
    """Criteria for spatial queries."""
    # Using simple bounding box representation for now
    # This will be enhanced when we implement full spatial functionality
    min_x: Optional[float] = None
    min_y: Optional[float] = None
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    radius: Optional[float] = None
    
    def __post_init__(self):
        self.query_type = QueryType.SPATIAL
    
    def validate(self) -> bool:
        """Validate spatial criteria.
        
        Ensures that either:
        1. All bounding box coordinates are set (min_x, min_y, max_x, max_y), or
        2. Center point and radius are set for circular queries
        
        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        # Check for bounding box query
        bbox_coords = [self.min_x, self.min_y, self.max_x, self.max_y]
        has_bbox = all(coord is not None for coord in bbox_coords)
        
        # Check for radius query
        circle_params = [self.center_x, self.center_y, self.radius]
        has_circle = all(param is not None for param in circle_params)
        
        if not (has_bbox or has_circle):
            raise ValueError(
                "Either all bounding box coordinates or center point and radius must be specified"
            )
            
        # Additional validation for bounding box
        if has_bbox and (self.min_x > self.max_x or self.min_y > self.max_y):
            raise ValueError("min_x must be <= max_x and min_y must be <= max_y")
            
        # Additional validation for radius
        if has_circle and self.radius <= 0:
            raise ValueError("radius must be positive")
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = super().to_dict()
        
        # Add bounding box coordinates if present
        for field_name in ["min_x", "min_y", "max_x", "max_y"]:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
                
        # Add circle parameters if present
        for field_name in ["center_x", "center_y", "radius"]:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
                
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpatialCriteria':
        """Create from dictionary representation."""
        return cls(
            query_type=QueryType.SPATIAL,
            min_x=data.get("min_x"),
            min_y=data.get("min_y"),
            max_x=data.get("max_x"),
            max_y=data.get("max_y"),
            center_x=data.get("center_x"),
            center_y=data.get("center_y"),
            radius=data.get("radius")
        )

@dataclass
class ContentCriteria(QueryCriteria):
    """Criteria for content-based queries."""
    field_name: str
    operator: str  # e.g., "=", ">", "<", "LIKE", "IN"
    value: Any
    
    def __post_init__(self):
        self.query_type = QueryType.CONTENT
    
    def validate(self) -> bool:
        """Validate content criteria.
        
        Ensures that field_name is not empty and operator is valid.
        
        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        if not self.field_name:
            raise ValueError("field_name must be specified")
            
        valid_operators = ["=", ">", "<", ">=", "<=", "!=", "LIKE", "IN", "CONTAINS"]
        if self.operator not in valid_operators:
            raise ValueError(f"operator must be one of {valid_operators}")
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = super().to_dict()
        result.update({
            "field_name": self.field_name,
            "operator": self.operator,
            "value": self.value
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentCriteria':
        """Create from dictionary representation."""
        return cls(
            query_type=QueryType.CONTENT,
            field_name=data["field_name"],
            operator=data["operator"],
            value=data["value"]
        )

@dataclass
class CompositeCriteria(QueryCriteria):
    """Criteria for composite queries using logical operators."""
    operator: QueryOperator
    criteria: List[QueryCriteria] = field(default_factory=list)
    
    def __post_init__(self):
        self.query_type = QueryType.COMPOSITE
    
    def validate(self) -> bool:
        """Validate composite criteria.
        
        Ensures that at least one criteria is present for AND/OR,
        and exactly one for NOT.
        
        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        if not self.criteria:
            raise ValueError("At least one criteria must be specified")
            
        if self.operator == QueryOperator.NOT and len(self.criteria) != 1:
            raise ValueError("NOT operator requires exactly one criteria")
            
        # Recursively validate each criteria
        for criterion in self.criteria:
            criterion.validate()
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = super().to_dict()
        result.update({
            "operator": self.operator.name,
            "criteria": [criterion.to_dict() for criterion in self.criteria]
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompositeCriteria':
        """Create from dictionary representation."""
        # First create the composite without criteria
        composite = cls(
            query_type=QueryType.COMPOSITE,
            operator=QueryOperator[data["operator"]],
            criteria=[]
        )
        
        # Parse and add each criteria
        for criterion_data in data["criteria"]:
            query_type = QueryType[criterion_data["query_type"]]
            
            # Create appropriate criteria based on query_type
            if query_type == QueryType.TEMPORAL:
                criterion = TemporalCriteria.from_dict(criterion_data)
            elif query_type == QueryType.SPATIAL:
                criterion = SpatialCriteria.from_dict(criterion_data)
            elif query_type == QueryType.CONTENT:
                criterion = ContentCriteria.from_dict(criterion_data)
            elif query_type == QueryType.COMPOSITE:
                criterion = CompositeCriteria.from_dict(criterion_data)
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
                
            composite.criteria.append(criterion)
            
        return composite

@dataclass
class Query:
    """Represents a complete query to the database."""
    criteria: QueryCriteria
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    limit: Optional[int] = None
    offset: Optional[int] = None
    
    def validate(self) -> bool:
        """Validate the entire query.
        
        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        # Validate limit and offset
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive")
            
        if self.offset is not None and self.offset < 0:
            raise ValueError("offset must be non-negative")
            
        # Validate criteria
        self.criteria.validate()
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary for serialization."""
        result = {
            "query_id": self.query_id,
            "criteria": self.criteria.to_dict()
        }
        
        if self.limit is not None:
            result["limit"] = self.limit
            
        if self.offset is not None:
            result["offset"] = self.offset
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Query':
        """Create query from dictionary representation."""
        # Parse criteria based on query type
        criteria_data = data["criteria"]
        query_type = QueryType[criteria_data["query_type"]]
        
        if query_type == QueryType.TEMPORAL:
            criteria = TemporalCriteria.from_dict(criteria_data)
        elif query_type == QueryType.SPATIAL:
            criteria = SpatialCriteria.from_dict(criteria_data)
        elif query_type == QueryType.CONTENT:
            criteria = ContentCriteria.from_dict(criteria_data)
        elif query_type == QueryType.COMPOSITE:
            criteria = CompositeCriteria.from_dict(criteria_data)
        else:
            raise ValueError(f"Unsupported query type: {query_type}")
            
        return cls(
            query_id=data.get("query_id", str(uuid.uuid4())),
            criteria=criteria,
            limit=data.get("limit"),
            offset=data.get("offset")
        )
    
    def to_json(self) -> str:
        """Serialize query to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Query':
        """Create query from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """Return string representation of query."""
        return f"Query(id={self.query_id}, type={self.criteria.query_type.name})" 
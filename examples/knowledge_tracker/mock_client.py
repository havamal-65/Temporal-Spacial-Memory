"""
Mock Database Client

This module provides a mock implementation of the DatabaseClient for testing purposes.
It simulates the behavior of the actual Temporal-Spatial Knowledge Database without
requiring a real database connection.
"""

import uuid
from uuid import UUID
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

logger = logging.getLogger(__name__)

class MockNode:
    """Mock implementation of a database node."""
    
    def __init__(self, id=None, properties=None, position=None):
        """
        Initialize a mock node.
        
        Args:
            id: The ID for the node (default: generated UUID)
            properties: Dictionary of node properties (default: empty dict)
            position: Spatial-temporal coordinates [t, x, y] (default: [0,0,0])
        """
        self.id = id if id is not None else uuid.uuid4()
        self.properties = properties if properties is not None else {}
        self.position = position if position is not None else [0, 0, 0]
        
    def to_dict(self):
        """Convert the node to a dictionary representation."""
        return {
            "id": str(self.id),
            "properties": self.properties,
            "position": self.position
        }

class MockEdge:
    """Mock implementation of a database edge."""
    
    def __init__(self, id=None, from_node=None, to_node=None, edge_type=None):
        """
        Initialize a mock edge.
        
        Args:
            id: The ID for the edge (default: generated UUID)
            from_node: Source node ID
            to_node: Target node ID
            edge_type: Type of the edge
        """
        self.id = id if id is not None else uuid.uuid4()
        self.from_node = from_node
        self.to_node = to_node
        self.edge_type = edge_type or "RELATED_TO"
        
    def to_dict(self):
        """Convert the edge to a dictionary representation."""
        return {
            "id": str(self.id),
            "from_node": str(self.from_node),
            "to_node": str(self.to_node),
            "edge_type": self.edge_type
        }

class MockDatabaseClient:
    """Mock implementation of the DatabaseClient interface."""
    
    def __init__(self, connection_url=None):
        """
        Initialize a mock database client.
        
        Args:
            connection_url: Ignored for mock client
        """
        self.connection_url = connection_url or "mock://localhost:8000"
        self._connected = False
        self._nodes = {}  # id -> MockNode
        self._edges = {}  # id -> MockEdge
        self._node_index = {}  # property_value -> [node_ids]
        self._relationships = []
        
    def connect(self):
        """Connect to the mock database."""
        logger.info(f"Connecting to mock database at {self.connection_url}")
        time.sleep(0.1)  # Simulate connection delay
        self._connected = True
        logger.info("Connected to mock database")
        return True
        
    def disconnect(self):
        """Disconnect from the mock database."""
        if self._connected:
            logger.info("Disconnecting from mock database")
            time.sleep(0.1)  # Simulate disconnection delay
            self._connected = False
            logger.info("Disconnected from mock database")
            return True
        return False
        
    def is_connected(self):
        """Check if connected to the mock database."""
        return self._connected
        
    def create_node(self, properties, position=None):
        """
        Create a node in the mock database.
        
        Args:
            properties: Dictionary of node properties
            position: Spatial-temporal coordinates [t, x, y]
            
        Returns:
            MockNode: The created node
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        # Create node
        node = MockNode(properties=properties, position=position)
        self._nodes[node.id] = node
        
        # Update index
        for key, value in properties.items():
            if isinstance(value, (str, int, float, bool)):
                index_key = f"{key}:{value}"
                if index_key not in self._node_index:
                    self._node_index[index_key] = []
                self._node_index[index_key].append(node.id)
                
        logger.debug(f"Created node: {node.id}")
        return node
        
    def update_node(self, node_id, properties):
        """
        Update a node in the mock database.
        
        Args:
            node_id: ID of the node to update
            properties: New properties to set
            
        Returns:
            MockNode: The updated node
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        node_id = UUID(node_id) if isinstance(node_id, str) else node_id
        
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")
            
        node = self._nodes[node_id]
        
        # Update index for removed properties
        for key, value in node.properties.items():
            if key not in properties:
                index_key = f"{key}:{value}"
                if index_key in self._node_index and node_id in self._node_index[index_key]:
                    self._node_index[index_key].remove(node_id)
        
        # Update node properties
        node.properties.update(properties)
        
        # Update index for new properties
        for key, value in properties.items():
            if isinstance(value, (str, int, float, bool)):
                index_key = f"{key}:{value}"
                if index_key not in self._node_index:
                    self._node_index[index_key] = []
                if node_id not in self._node_index[index_key]:
                    self._node_index[index_key].append(node_id)
                    
        logger.debug(f"Updated node: {node_id}")
        return node
        
    def delete_node(self, node_id):
        """
        Delete a node from the mock database.
        
        Args:
            node_id: ID of the node to delete
            
        Returns:
            bool: True if successful
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        node_id = UUID(node_id) if isinstance(node_id, str) else node_id
        
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")
            
        node = self._nodes[node_id]
        
        # Remove from index
        for key, value in node.properties.items():
            index_key = f"{key}:{value}"
            if index_key in self._node_index and node_id in self._node_index[index_key]:
                self._node_index[index_key].remove(node_id)
                
        # Remove edges
        edges_to_remove = []
        for edge_id, edge in self._edges.items():
            if edge.from_node == node_id or edge.to_node == node_id:
                edges_to_remove.append(edge_id)
                
        for edge_id in edges_to_remove:
            del self._edges[edge_id]
            
        # Remove node
        del self._nodes[node_id]
        logger.debug(f"Deleted node: {node_id}")
        return True
        
    def create_edge(self, from_id, to_id, edge_type=None):
        """
        Create an edge between nodes in the mock database.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            edge_type: Type of the edge
            
        Returns:
            MockEdge: The created edge
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        from_id = UUID(from_id) if isinstance(from_id, str) else from_id
        to_id = UUID(to_id) if isinstance(to_id, str) else to_id
        
        if from_id not in self._nodes:
            raise ValueError(f"Source node {from_id} not found")
            
        if to_id not in self._nodes:
            raise ValueError(f"Target node {to_id} not found")
            
        edge = MockEdge(from_node=from_id, to_node=to_id, edge_type=edge_type)
        self._edges[edge.id] = edge
        
        logger.debug(f"Created edge: {edge.id} ({from_id} -> {to_id})")
        return edge
        
    def delete_edge(self, edge_id):
        """
        Delete an edge from the mock database.
        
        Args:
            edge_id: ID of the edge to delete
            
        Returns:
            bool: True if successful
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        edge_id = UUID(edge_id) if isinstance(edge_id, str) else edge_id
        
        if edge_id not in self._edges:
            raise ValueError(f"Edge {edge_id} not found")
            
        del self._edges[edge_id]
        logger.debug(f"Deleted edge: {edge_id}")
        return True
        
    def query(self, query_spec):
        """
        Execute a query against the mock database.
        
        Args:
            query_spec: Dictionary containing the query specification
            
        Returns:
            list: List of matching nodes
        """
        if not self._connected:
            logger.warning("Cannot execute query: not connected to database")
            return []
            
        try:
            results = []
            
            # Extract query filters
            filters = query_spec.get("filters", {})
            
            # Apply filters to nodes
            for node in self._nodes.values():
                include = True
                
                # Check property filters
                for prop_name, prop_value in filters.get("properties", {}).items():
                    if not hasattr(node, 'properties') or node.properties is None:
                        include = False
                        break
                        
                    if prop_name not in node.properties or node.properties[prop_name] != prop_value:
                        include = False
                        break
                
                # Add to results if passes all filters
                if include:
                    results.append(node)
            
            logger.info(f"Query executed, returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
        
    def get_connected_nodes(self, node_id, edge_type=None, direction=None):
        """
        Get nodes connected to a specific node.
        
        Args:
            node_id: ID of the node
            edge_type: Filter by edge type
            direction: "outgoing" or "incoming" or None for both
            
        Returns:
            list: Connected nodes
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        node_id = UUID(node_id) if isinstance(node_id, str) else node_id
        
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")
            
        connected_ids = set()
        
        for edge in self._edges.values():
            if edge_type and edge.edge_type != edge_type:
                continue
                
            if edge.from_node == node_id and (direction is None or direction == "outgoing"):
                connected_ids.add(edge.to_node)
                
            if edge.to_node == node_id and (direction is None or direction == "incoming"):
                connected_ids.add(edge.from_node)
                
        return [self._nodes[id].to_dict() for id in connected_ids]

    def get_node(self, node_id):
        """
        Get a node by ID.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            The node if found, None otherwise
        """
        if not self._connected:
            raise ConnectionError("Not connected to the database")
            
        node_id = UUID(node_id) if isinstance(node_id, str) else node_id
        
        if node_id not in self._nodes:
            return None
            
        return self._nodes[node_id]
    
    def create_query_builder(self):
        """
        Create a query builder for constructing queries.
        
        Returns:
            A mock query builder object
        """
        return MockQueryBuilder()

    def create_relationship(self, source_node, target_node, relationship_type):
        """
        Create a relationship between two nodes.
        
        Args:
            source_node: The source node
            target_node: The target node
            relationship_type: Type of relationship to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._connected:
            logger.warning("Cannot create relationship: not connected to database")
            return False
            
        try:
            # Get node IDs
            source_id = str(source_node.id) if hasattr(source_node, 'id') else None
            target_id = str(target_node.id) if hasattr(target_node, 'id') else None
            
            if not source_id or not target_id:
                logger.warning("Cannot create relationship: invalid node IDs")
                return False
                
            # Create relationship record
            relationship = {
                "source_id": source_id,
                "target_id": target_id,
                "type": relationship_type
            }
            
            # Store the relationship
            self._relationships.append(relationship)
            
            logger.info(f"Created mock relationship: {source_id} --[{relationship_type}]--> {target_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

class MockQueryBuilder:
    """Mock implementation of a query builder."""
    
    def __init__(self):
        """Initialize the query builder."""
        self._property_filters = {}
        self._time_range = None
    
    def filter_by_property(self, property_name, property_value):
        """
        Add a property filter to the query.
        
        Args:
            property_name: Name of the property to filter by
            property_value: Value to filter for
            
        Returns:
            self: For method chaining
        """
        self._property_filters[property_name] = property_value
        return self
    
    def filter_by_time_range(self, start_time=None, end_time=None):
        """
        Add a time range filter to the query.
        
        Args:
            start_time: Start time for the range (optional)
            end_time: End time for the range (optional)
            
        Returns:
            self: For method chaining
        """
        self._time_range = {"start": start_time, "end": end_time}
        return self
    
    def build(self):
        """
        Build the query.
        
        Returns:
            dict: A dictionary representing the query
        """
        query = {
            "filters": {
                "properties": self._property_filters
            }
        }
        
        if self._time_range:
            query["filters"]["time_range"] = self._time_range
            
        return query

# Create aliases for compatibility
DatabaseClient = MockDatabaseClient
Node = MockNode
Edge = MockEdge 
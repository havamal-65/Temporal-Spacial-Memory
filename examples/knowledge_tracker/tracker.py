"""
Knowledge Tracker Module

This module provides functionality for tracking and managing AI knowledge
in a temporal-spatial database.
"""

import uuid
from uuid import UUID
import logging
import random
import math
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instead of importing from src.client, we'll define a simple interface here
class DatabaseClient:
    """Simple interface definition for the DatabaseClient."""
    
    def connect(self):
        """Connect to the database."""
        pass
    
    def disconnect(self):
        """Disconnect from the database."""
        pass
    
    def is_connected(self):
        """Check if connected to the database."""
        return False
    
    def create_node(self, properties, position):
        """Create a node in the database."""
        pass
    
    def update_node(self, node_id, properties):
        """Update a node in the database."""
        pass
    
    def delete_node(self, node_id):
        """Delete a node from the database."""
        pass
    
    def create_edge(self, from_id, to_id, edge_type):
        """Create an edge between nodes."""
        pass
    
    def delete_edge(self, edge_id):
        """Delete an edge from the database."""
        pass
    
    def query(self, query_params):
        """Query the database."""
        return []

class Node:
    """Simple interface definition for the Node class."""
    
    def __init__(self, id=None, properties=None, position=None):
        """Initialize a node with properties and position."""
        self.id = id or uuid.uuid4()
        self.properties = properties or {}
        self.position = position or [0, 0, 0]


class KnowledgeDomain:
    """Represents a domain of knowledge in the Knowledge Tracker."""
    
    def __init__(self, name, description=None):
        """
        Initialize a knowledge domain.
        
        Args:
            name (str): The name of the domain.
            description (str, optional): A description of the domain.
        """
        self.id = uuid.uuid4()
        self.name = name
        self.description = description or ""
        self.created_at = datetime.now().isoformat()
        self.topics = {}  # Dictionary of topic_id -> topic
        
    def add_topic(self, topic):
        """
        Add a topic to this domain.
        
        Args:
            topic (KnowledgeTopic): The topic to add.
        """
        topic.domain_id = self.id
        self.topics[topic.id] = topic
        
    def to_dict(self):
        """
        Convert the domain to a dictionary representation.
        
        Returns:
            dict: Dictionary containing domain information.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "topics": [topic.to_dict() for topic in self.topics.values()]
        }


class KnowledgeTopic:
    """Represents a topic within a knowledge domain."""
    
    def __init__(self, name, description=None):
        """
        Initialize a knowledge topic.
        
        Args:
            name (str): The name of the topic.
            description (str, optional): A description of the topic.
        """
        self.id = uuid.uuid4()
        self.domain_id = None  # Will be set when added to domain
        self.name = name
        self.description = description or ""
        self.created_at = datetime.now().isoformat()
        self.facts = {}  # Dictionary of fact_id -> fact
        
    def add_fact(self, fact):
        """
        Add a fact to this topic.
        
        Args:
            fact (KnowledgeFact): The fact to add.
        """
        fact.topic_id = self.id
        self.facts[fact.id] = fact
        
    def to_dict(self):
        """
        Convert the topic to a dictionary representation.
        
        Returns:
            dict: Dictionary containing topic information.
        """
        return {
            "id": str(self.id),
            "domain_id": str(self.domain_id) if self.domain_id else None,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "facts": [fact.to_dict() for fact in self.facts.values()]
        }


class KnowledgeFact:
    """Represents a fact within a knowledge topic."""
    
    def __init__(self, content, source=None, confidence=0.5):
        """
        Initialize a knowledge fact.
        
        Args:
            content (str): The content/statement of the fact.
            source (str, optional): The source of the fact.
            confidence (float, optional): Confidence level (0.0 to 1.0).
        """
        self.id = uuid.uuid4()
        self.topic_id = None  # Will be set when added to topic
        self.content = content
        self.source = source or ""
        self.confidence = min(max(confidence, 0.0), 1.0)  # Ensure between 0 and 1
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.related_facts = set()  # Set of related fact IDs
        
    def add_related_fact(self, fact_id):
        """
        Add a related fact to this fact.
        
        Args:
            fact_id (UUID): The ID of the related fact.
        """
        self.related_facts.add(fact_id)
        
    def update_confidence(self, new_confidence):
        """
        Update the confidence level of this fact.
        
        Args:
            new_confidence (float): New confidence level (0.0 to 1.0).
        """
        self.confidence = min(max(new_confidence, 0.0), 1.0)
        self.updated_at = datetime.now().isoformat()
        
    def to_dict(self):
        """
        Convert the fact to a dictionary representation.
        
        Returns:
            dict: Dictionary containing fact information.
        """
        return {
            "id": str(self.id),
            "topic_id": str(self.topic_id) if self.topic_id else None,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "related_facts": [str(fact_id) for fact_id in self.related_facts]
        }


class KnowledgeTracker:
    """
    Main knowledge tracking system.
    
    This class integrates with the Temporal-Spatial Knowledge Database to
    store and retrieve knowledge information.
    """
    
    def __init__(self, connection_url_or_client=None, api_key: Optional[str] = None):
        """
        Initialize a knowledge tracker.
        
        Args:
            connection_url_or_client: Connection URL or database client instance
            api_key: API key for authentication
        """
        # Set up client
        if connection_url_or_client is None:
            connection_url_or_client = "localhost:8000"
            
        if isinstance(connection_url_or_client, str):
            self._client = DatabaseClient(connection_url_or_client, api_key)
            self._client.connect()
        else:
            self._client = connection_url_or_client
            if not self._client.is_connected():
                self._client.connect()
        
        # Local caches
        self._domain_cache = {}
        self._topic_cache = {}
        self._fact_cache = {}
        
        # Node caches (for direct node objects)
        self._domain_nodes = {}
        self._topic_nodes = {}
        self._fact_nodes = {}
    
    def add_domain(self, domain: KnowledgeDomain) -> Node:
        """
        Add a knowledge domain to the database.
        
        Args:
            domain: Domain to add
            
        Returns:
            The created node
        """
        # Create a node for the domain
        properties = {
            "name": domain.name,
            "description": domain.description,
            "type": "domain",
            "created_at": domain.created_at
        }
        
        # Calculate spatial coordinates (2D example)
        # In a real implementation, these would be meaningful coordinates
        # Here we're just generating random ones for demonstration
        x_coord = random.uniform(0, 100)
        y_coord = random.uniform(0, 100)
        
        # Create node with temporal-spatial position
        # The first coordinate is time (in timestamp format)
        position = [datetime.now().timestamp(), x_coord, y_coord]
        
        # For testing compatibility, create the node differently depending on mock or real client
        if hasattr(Node, '__module__') and Node.__module__ == 'examples.knowledge_tracker.mock_client':
            # Using mock client
            node = Node(
                id=domain.id,
                content=json.dumps(domain.to_dict()),
                properties=properties,
                position=position
            )
        else:
            # Using real client
            node = Node(
                id=domain.id,
                content=json.dumps(domain.to_dict()),
                properties=properties,
                position=position
            )
        
        # Add to database
        self._client.add_node(node)
        
        # Cache locally
        self._domain_nodes[domain.id] = node
        self._domain_cache[domain.id] = domain
        
        return node
    
    def add_topic(self, domain_id: UUID, name: str, description: str = "") -> UUID:
        """
        Add a knowledge topic.
        
        Args:
            domain_id: ID of the domain to add the topic to
            name: Name of the topic
            description: Description of the topic
            
        Returns:
            ID of the created topic
        """
        # Convert string to UUID if needed
        if isinstance(domain_id, str):
            domain_id = UUID(domain_id)
            
        # Create topic with domain ID
        topic = KnowledgeTopic(name=name, description=description)
        topic.domain_id = domain_id
        
        # Add to database
        self._add_topic_node(topic)
        
        return topic.id
    
    def add_fact(self, topic_id: UUID, content: str, source: Optional[str] = None, confidence: float = 1.0) -> UUID:
        """
        Add a knowledge fact.
        
        Args:
            topic_id: ID of the topic to add the fact to
            content: Content of the fact
            source: Source of the fact
            confidence: Confidence level (0.0 to 1.0)
            
        Returns:
            ID of the created fact
        """
        # Convert string to UUID if needed
        if isinstance(topic_id, str):
            topic_id = UUID(topic_id)
            
        # Create fact with topic ID
        fact = KnowledgeFact(content=content, source=source, confidence=confidence)
        fact.topic_id = topic_id
        
        # Add to database
        self._add_fact_node(fact)
        
        return fact.id
    
    def update_fact(self, fact: KnowledgeFact) -> Node:
        """
        Update a knowledge fact in the database.
        
        Args:
            fact: Fact to update
            
        Returns:
            The updated node
        """
        # Get existing node
        node = self._get_node_by_id(fact.id)
        if not node:
            raise ValueError(f"Fact with ID {fact.id} not found")
        
        # Update properties
        properties = {
            "content": fact.content,
            "source": fact.source,
            "confidence": fact.confidence,
            "type": "fact",
            "topic_id": str(fact.topic_id) if fact.topic_id else None,
            "created_at": fact.created_at,
            "updated_at": fact.updated_at,
            "related_facts": [str(fact_id) for fact_id in fact.related_facts]
        }
        
        # Keep the same position
        position = node.position
        
        # For testing compatibility, create the node differently depending on mock or real client
        if hasattr(Node, '__module__') and Node.__module__ == 'examples.knowledge_tracker.mock_client':
            # Using mock client
            updated_node = Node(
                id=fact.id,
                content=json.dumps(fact.to_dict()),
                properties=properties,
                position=position
            )
        else:
            # Using real client
            updated_node = Node(
                id=fact.id,
                content=json.dumps(fact.to_dict()),
                properties=properties,
                position=position
            )
        
        # Update in database
        self._client.update_node(updated_node)
        
        # Update cache
        self._fact_nodes[fact.id] = updated_node
        self._fact_cache[fact.id] = fact
        
        return updated_node
    
    def get_domain(self, domain_id: UUID) -> Optional[KnowledgeDomain]:
        """
        Get a knowledge domain by ID.
        
        Args:
            domain_id: ID of the domain to retrieve
            
        Returns:
            KnowledgeDomain: The domain object if found, None otherwise
        """
        # Convert string to UUID if needed
        if isinstance(domain_id, str):
            domain_id = UUID(domain_id)
        
        # Check local cache first
        if domain_id in self._domain_cache:
            return self._domain_cache[domain_id]
        
        # Try to get the domain node
        node = self._get_node_by_id(domain_id)
        if not node:
            logger.warning(f"Domain {domain_id} not found")
            return None
            
        try:
            # Parse domain from node properties
            props = node.properties if hasattr(node, 'properties') else {}
            
            # Create domain object
            domain = KnowledgeDomain(
                name=props.get("name", "Unknown"),
                description=props.get("description", "")
            )
            domain.id = domain_id
            domain.created_at = props.get("created_at", datetime.now().isoformat())
            
            # Cache the domain
            self._domain_cache[domain.id] = domain
            self._domain_nodes[domain.id] = node
            
            return domain
        except Exception as e:
            logger.error(f"Failed to parse domain: {e}")
            return None
    
    def get_topic(self, topic_id: UUID) -> Optional[KnowledgeTopic]:
        """
        Get a knowledge topic by ID.
        
        Args:
            topic_id: ID of the topic to retrieve
            
        Returns:
            KnowledgeTopic: The topic object if found, None otherwise
        """
        # Convert string to UUID if needed
        if isinstance(topic_id, str):
            topic_id = UUID(topic_id)
            
        # Check local cache first
        if topic_id in self._topic_cache:
            return self._topic_cache[topic_id]
        
        # Try to get the topic node
        node = self._get_node_by_id(topic_id)
        if not node:
            logger.warning(f"Topic {topic_id} not found")
            return None
            
        try:
            # Parse topic from node properties
            props = node.properties if hasattr(node, 'properties') else {}
            
            # Create topic object
            topic = KnowledgeTopic(
                name=props.get("name", "Unknown"),
                description=props.get("description", "")
            )
            topic.id = topic_id
            topic.domain_id = UUID(props["domain_id"]) if props.get("domain_id") else None
            topic.created_at = props.get("created_at", datetime.now().isoformat())
            
            # Cache the topic
            self._topic_cache[topic.id] = topic
            self._topic_nodes[topic.id] = node
            
            return topic
        except Exception as e:
            logger.error(f"Failed to parse topic: {e}")
            return None
    
    def get_fact(self, fact_id: UUID) -> Optional[KnowledgeFact]:
        """
        Get a knowledge fact by ID.
        
        Args:
            fact_id: ID of the fact to retrieve
            
        Returns:
            KnowledgeFact: The fact object if found, None otherwise
        """
        # Convert string to UUID if needed
        if isinstance(fact_id, str):
            fact_id = UUID(fact_id)
            
        # Check local cache first
        if fact_id in self._fact_cache:
            return self._fact_cache[fact_id]
        
        # Try to get the fact node
        node = self._get_node_by_id(fact_id)
        if not node:
            logger.warning(f"Fact {fact_id} not found")
            return None
            
        try:
            # Parse fact from node properties
            props = node.properties if hasattr(node, 'properties') else {}
            
            # Create fact object
            fact = KnowledgeFact(
                content=props.get("content", ""),
                source=props.get("source", ""),
                confidence=props.get("confidence", 0.5)
            )
            fact.id = fact_id
            fact.topic_id = UUID(props["topic_id"]) if props.get("topic_id") else None
            fact.created_at = props.get("created_at", datetime.now().isoformat())
            fact.updated_at = props.get("updated_at", fact.created_at)
            
            # Add related facts
            if "related_facts" in props and isinstance(props["related_facts"], list):
                for related_id_str in props["related_facts"]:
                    try:
                        fact.related_facts.add(UUID(related_id_str))
                    except Exception:
                        pass
            
            # Cache the fact
            self._fact_cache[fact.id] = fact
            self._fact_nodes[fact.id] = node
            
            return fact
        except Exception as e:
            logger.error(f"Failed to parse fact: {e}")
            return None
    
    def get_topics_by_domain(self, domain_id: UUID) -> List[KnowledgeTopic]:
        """
        Get all topics for a domain.
        
        Args:
            domain_id: ID of the domain
            
        Returns:
            List of topics
        """
        # Convert string to UUID if needed
        if isinstance(domain_id, str):
            domain_id = UUID(domain_id)
            
        # Create query
        query_builder = self._client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "topic")
                .filter_by_property("domain_id", str(domain_id))
                .build())
        
        # Execute query
        nodes = self._client.query(query)
        
        # Parse topics from nodes
        topics = []
        for node in nodes:
            try:
                # Get topic properties
                props = node.properties if hasattr(node, 'properties') else {}
                
                # Create topic object
                topic = KnowledgeTopic(
                    name=props.get("name", "Unknown"),
                    description=props.get("description", "")
                )
                topic.id = UUID(props.get("id", str(node.id)))
                topic.domain_id = domain_id
                topic.created_at = props.get("created_at", datetime.now().isoformat())
                
                # Cache the topic
                self._topic_cache[topic.id] = topic
                self._topic_nodes[topic.id] = node
                
                topics.append(topic)
            except Exception as e:
                logger.error(f"Failed to parse topic: {e}")
        
        return topics
        
    def get_facts_by_topic(self, topic_id: UUID) -> List[KnowledgeFact]:
        """
        Get all facts for a topic.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            List of facts
        """
        # Convert string to UUID if needed
        if isinstance(topic_id, str):
            topic_id = UUID(topic_id)
            
        # Create query
        query_builder = self._client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "fact")
                .filter_by_property("topic_id", str(topic_id))
                .build())
        
        # Execute query
        nodes = self._client.query(query)
        
        # Parse facts from nodes
        facts = []
        for node in nodes:
            try:
                # Get fact properties
                props = node.properties if hasattr(node, 'properties') else {}
                
                # Create fact object
                fact = KnowledgeFact(
                    content=props.get("content", ""),
                    source=props.get("source", ""),
                    confidence=props.get("confidence", 0.5)
                )
                fact.id = UUID(props.get("id", str(node.id)))
                fact.topic_id = topic_id
                fact.created_at = props.get("created_at", datetime.now().isoformat())
                fact.updated_at = props.get("updated_at", fact.created_at)
                
                # Add related facts
                if "related_facts" in props and isinstance(props["related_facts"], list):
                    for related_id_str in props["related_facts"]:
                        try:
                            fact.related_facts.add(UUID(related_id_str))
                        except Exception:
                            pass
                
                # Cache the fact
                self._fact_cache[fact.id] = fact
                self._fact_nodes[fact.id] = node
                
                facts.append(fact)
            except Exception as e:
                logger.error(f"Failed to parse fact: {e}")
        
        return facts
    
    def get_facts_in_time_range(self, 
                              start_time: datetime, 
                              end_time: datetime) -> List[KnowledgeFact]:
        """
        Get facts created within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of facts
        """
        query_builder = self._client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "fact")
                .filter_by_time_range(start_time, end_time)
                .build())
        
        # Execute query
        nodes = self._client.query(query)
        
        # Parse facts from nodes
        facts = []
        for node in nodes:
            try:
                fact_dict = json.loads(node.content)
                fact = KnowledgeFact(
                    content=fact_dict["content"],
                    source=fact_dict["source"],
                    confidence=fact_dict["confidence"],
                    topic_id=UUID(fact_dict["topic_id"]) if fact_dict["topic_id"] else None
                )
                fact.id = UUID(fact_dict["id"])
                fact.created_at = fact_dict["created_at"]
                fact.updated_at = fact_dict["updated_at"]
                
                # Add related facts
                for related_id_str in fact_dict["related_facts"]:
                    fact.related_facts.add(UUID(related_id_str))
                
                # Cache the fact
                self._fact_cache[fact.id] = fact
                
                facts.append(fact)
            except Exception as e:
                logger.error(f"Failed to parse fact: {e}")
        
        return facts
    
    def _get_node_by_id(self, node_id: UUID) -> Optional[Node]:
        """
        Get a node from the database by ID.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            The node if found, None otherwise
        """
        try:
            # Convert to string if it's a UUID
            if isinstance(node_id, UUID):
                node_id = str(node_id)
                
            # Try to get from domain nodes cache
            for domain_id, node in self._domain_nodes.items():
                if str(domain_id) == node_id:
                    return node
                    
            # Try to get from topic nodes cache
            for topic_id, node in self._topic_nodes.items():
                if str(topic_id) == node_id:
                    return node
                    
            # Try to get from fact nodes cache
            for fact_id, node in self._fact_nodes.items():
                if str(fact_id) == node_id:
                    return node
                
            # If not in cache, try to get from database
            return self._client.get_node(node_id)
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def _connect_nodes(self, from_id, to_id, edge_type):
        """
        Create a connection between two nodes.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            edge_type: Type of the connection
        """
        return self._client.create_edge(from_id, to_id, edge_type)
    
    def close(self) -> None:
        """Close the connection to the database."""
        self._client.disconnect()

    # Helper methods for simpler API usage
    def add_domain(self, name: str, description: str = "") -> UUID:
        """
        Add a knowledge domain.
        
        Args:
            name: Name of the domain
            description: Description of the domain
            
        Returns:
            ID of the created domain
        """
        domain = KnowledgeDomain(name=name, description=description)
        self._add_domain_node(domain)
        return domain.id
        
    def add_topic(self, domain_id: UUID, name: str, description: str = "") -> UUID:
        """
        Add a knowledge topic.
        
        Args:
            domain_id: ID of the domain to add the topic to
            name: Name of the topic
            description: Description of the topic
            
        Returns:
            ID of the created topic
        """
        # Convert string to UUID if needed
        if isinstance(domain_id, str):
            domain_id = UUID(domain_id)
            
        # Create topic with domain ID
        topic = KnowledgeTopic(name=name, description=description)
        topic.domain_id = domain_id
        
        # Add to database
        self._add_topic_node(topic)
        
        return topic.id
        
    def add_fact(self, topic_id: UUID, content: str, source: Optional[str] = None, confidence: float = 1.0) -> UUID:
        """
        Add a knowledge fact.
        
        Args:
            topic_id: ID of the topic to add the fact to
            content: Content of the fact
            source: Source of the fact
            confidence: Confidence level (0.0 to 1.0)
            
        Returns:
            ID of the created fact
        """
        # Convert string to UUID if needed
        if isinstance(topic_id, str):
            topic_id = UUID(topic_id)
            
        # Create fact with topic ID
        fact = KnowledgeFact(content=content, source=source, confidence=confidence)
        fact.topic_id = topic_id
        
        # Add to database
        self._add_fact_node(fact)
        
        return fact.id
        
    def add_related_fact(self, fact_id1: UUID, fact_id2: UUID) -> bool:
        """
        Add a relationship between two facts.
        
        Args:
            fact_id1: ID of the first fact
            fact_id2: ID of the second fact
            
        Returns:
            True if successful
        """
        # Convert strings to UUIDs if needed
        if isinstance(fact_id1, str):
            fact_id1 = UUID(fact_id1)
        if isinstance(fact_id2, str):
            fact_id2 = UUID(fact_id2)
            
        # Get facts from cache or database
        fact1 = self.get_fact(fact_id1)
        fact2 = self.get_fact(fact_id2)
        
        if not fact1 or not fact2:
            return False
            
        # Add bidirectional relationship
        fact1.add_related_fact(fact_id2)
        fact2.add_related_fact(fact_id1)
        
        # Update facts in database
        self._fact_nodes[fact_id1] = self._client.update_node(
            str(fact_id1), 
            {"related_facts": [str(f) for f in fact1.related_facts]}
        )
        
        self._fact_nodes[fact_id2] = self._client.update_node(
            str(fact_id2), 
            {"related_facts": [str(f) for f in fact2.related_facts]}
        )
        
        # Update connection between nodes
        self._connect_nodes(fact_id1, fact_id2, "RELATED_TO")
        
        return True
        
    def verify_fact(self, fact_id: UUID, new_confidence: float = None, increment: float = 0.1) -> bool:
        """
        Verify a fact by increasing its confidence level.
        
        Args:
            fact_id: ID of the fact to verify
            new_confidence: Set a specific confidence value (0.0-1.0)
            increment: Amount to increase confidence by (default 0.1)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert UUID to string if needed
            if isinstance(fact_id, str):
                fact_id = UUID(fact_id)
            
            # Get the fact
            fact = self.get_fact(fact_id)
            if not fact:
                logger.warning(f"Cannot verify fact: fact {fact_id} not found")
                return False
            
            # Update confidence
            if new_confidence is not None:
                fact.confidence = max(0.0, min(1.0, new_confidence))  # Ensure in range 0-1
            else:
                fact.confidence = max(0.0, min(1.0, fact.confidence + increment))
            
            # Update timestamp
            fact.updated_at = datetime.now().isoformat()
            
            # Update in database
            node = self._fact_nodes.get(fact_id)
            if node and hasattr(node, 'properties'):
                node.properties["confidence"] = fact.confidence
                node.properties["updated_at"] = fact.updated_at
                logger.info(f"Verified fact {fact_id}, new confidence: {fact.confidence}")
            else:
                logger.warning(f"Node for fact {fact_id} not found in cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify fact: {e}")
            return False
    
    # Renamed original methods to use internally
    
    def _add_domain_node(self, domain: KnowledgeDomain) -> Node:
        """
        Add a knowledge domain to the database.
        
        Args:
            domain: The domain to add
            
        Returns:
            The created node
        """
        # Create node properties
        properties = {
            "id": str(domain.id),
            "name": domain.name,
            "description": domain.description,
            "type": "domain",
            "created_at": domain.created_at
        }
        
        # Create node with temporal-spatial position
        # The first coordinate is time (in timestamp format)
        position = [datetime.now().timestamp(), random.uniform(0, 100), random.uniform(0, 100)]
        
        # Create node with the mock client
        node = self._client.create_node(properties=properties, position=position)
            
        # Cache the node
        self._domain_nodes[domain.id] = node
        self._domain_cache[domain.id] = domain
        
        return node
        
    def _add_topic_node(self, topic: KnowledgeTopic) -> Node:
        """
        Add a knowledge topic to the database.
        
        Args:
            topic: The topic to add
            
        Returns:
            The created node
        """
        # Calculate position relative to domain
        if topic.domain_id in self._domain_nodes:
            # Position near domain node
            domain_node = self._domain_nodes[topic.domain_id]
            base_x = domain_node.position[1]
            base_y = domain_node.position[2]
            # Add some random offset (still within domain "area")
            x_coord = base_x + random.uniform(-10, 10)
            y_coord = base_y + random.uniform(-10, 10)
        else:
            # No domain node, use random position
            x_coord = random.uniform(0, 100)
            y_coord = random.uniform(0, 100)
        
        # Create node properties
        properties = {
            "id": str(topic.id),
            "name": topic.name,
            "description": topic.description,
            "type": "topic",
            "domain_id": str(topic.domain_id) if topic.domain_id else None,
            "created_at": topic.created_at
        }
        
        # Create node with temporal-spatial position
        position = [datetime.now().timestamp(), x_coord, y_coord]
        
        # Create node with the mock client
        node = self._client.create_node(properties=properties, position=position)
        
        # Cache the node
        self._topic_nodes[topic.id] = node
        self._topic_cache[topic.id] = topic
        
        # Connect to domain node if available
        if topic.domain_id and topic.domain_id in self._domain_nodes:
            domain_node = self._domain_nodes[topic.domain_id]
            self._connect_nodes(domain_node.id, node.id, "CONTAINS")
        
        return node
        
    def _add_fact_node(self, fact: KnowledgeFact) -> Node:
        """
        Add a knowledge fact to the database.
        
        Args:
            fact: The fact to add
            
        Returns:
            The created node
        """
        # Calculate position relative to topic
        if fact.topic_id in self._topic_nodes:
            # Position near topic node
            topic_node = self._topic_nodes[fact.topic_id]
            base_x = topic_node.position[1]
            base_y = topic_node.position[2]
            # Add some random offset (still within topic "area")
            x_coord = base_x + random.uniform(-5, 5)
            y_coord = base_y + random.uniform(-5, 5)
        else:
            # No topic node, use random position
            x_coord = random.uniform(0, 100)
            y_coord = random.uniform(0, 100)
        
        # Create node properties
        properties = {
            "id": str(fact.id),
            "content": fact.content,
            "source": fact.source,
            "confidence": fact.confidence,
            "type": "fact",
            "topic_id": str(fact.topic_id) if fact.topic_id else None,
            "created_at": fact.created_at,
            "updated_at": fact.updated_at,
            "related_facts": [str(fact_id) for fact_id in fact.related_facts]
        }
        
        # Create node with temporal-spatial position
        position = [datetime.now().timestamp(), x_coord, y_coord]
        
        # Create node with the mock client
        node = self._client.create_node(properties=properties, position=position)
        
        # Cache the node
        self._fact_nodes[fact.id] = node
        self._fact_cache[fact.id] = fact
        
        # Connect to topic node if available
        if fact.topic_id and fact.topic_id in self._topic_nodes:
            topic_node = self._topic_nodes[fact.topic_id]
            self._connect_nodes(topic_node.id, node.id, "CONTAINS")
        
        # Connect to related facts
        for related_id in fact.related_facts:
            if related_id in self._fact_nodes:
                related_node = self._fact_nodes[related_id]
                self._connect_nodes(node.id, related_node.id, "RELATED_TO")
        
        return node

    def create_relationship(self, source_id: UUID, target_id: UUID, relationship_type: str) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            relationship_type: Type of relationship to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert UUIDs to string if needed
            source_id_str = str(source_id) if isinstance(source_id, UUID) else source_id
            target_id_str = str(target_id) if isinstance(target_id, UUID) else target_id
            
            # Get the nodes
            source_node = self._get_node_by_id(source_id)
            target_node = self._get_node_by_id(target_id)
            
            if not source_node or not target_node:
                logger.error(f"Failed to create relationship: one or both nodes not found")
                return False
                
            # Create the relationship in the database
            success = self._client.create_relationship(
                source_node, 
                target_node, 
                relationship_type
            )
            
            if success:
                logger.info(f"Created relationship {relationship_type} from {source_id} to {target_id}")
                
                # If this is between facts, update the related_facts list
                if relationship_type == "RELATED_TO":
                    if source_id in self._fact_cache and target_id in self._fact_cache:
                        self._fact_cache[source_id].related_facts.add(target_id)
                        self._fact_cache[target_id].related_facts.add(source_id)
                        
                        # Update properties in nodes
                        if hasattr(source_node, 'properties') and source_node.properties is not None:
                            if 'related_facts' not in source_node.properties:
                                source_node.properties['related_facts'] = []
                            if target_id_str not in source_node.properties['related_facts']:
                                source_node.properties['related_facts'].append(target_id_str)
                                
                        if hasattr(target_node, 'properties') and target_node.properties is not None:
                            if 'related_facts' not in target_node.properties:
                                target_node.properties['related_facts'] = []
                            if source_id_str not in target_node.properties['related_facts']:
                                target_node.properties['related_facts'].append(source_id_str)
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False 
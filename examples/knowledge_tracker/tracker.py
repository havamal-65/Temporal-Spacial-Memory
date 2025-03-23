"""
Knowledge Tracker Implementation

This module implements a knowledge tracking system that uses the 
Temporal-Spatial Knowledge Database to store and retrieve information 
about AI knowledge growth and development over time.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
import uuid
from uuid import UUID
import logging
import json
import numpy as np

from src.client import DatabaseClient
from src.core.node_v2 import Node
from src.query.query_builder import QueryBuilder

logger = logging.getLogger(__name__)


class KnowledgeDomain:
    """Represents a domain of knowledge (e.g., 'Machine Learning', 'Physics')."""
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize a knowledge domain.
        
        Args:
            name: Name of the domain
            description: Description of the domain
        """
        self.name = name
        self.description = description
        self.id = uuid.uuid4()
        self.created_at = datetime.now()
        self.topics: Dict[UUID, KnowledgeTopic] = {}
    
    def add_topic(self, topic: 'KnowledgeTopic') -> None:
        """
        Add a topic to this domain.
        
        Args:
            topic: Topic to add
        """
        self.topics[topic.id] = topic
        topic.domain_id = self.id
    
    def remove_topic(self, topic_id: UUID) -> None:
        """
        Remove a topic from this domain.
        
        Args:
            topic_id: ID of the topic to remove
        """
        if topic_id in self.topics:
            del self.topics[topic_id]
    
    def get_topic(self, topic_id: UUID) -> Optional['KnowledgeTopic']:
        """
        Get a topic by ID.
        
        Args:
            topic_id: ID of the topic to get
            
        Returns:
            The topic if found, None otherwise
        """
        return self.topics.get(topic_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the domain to a dictionary.
        
        Returns:
            Dictionary representation of the domain
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "topics": [topic.to_dict() for topic in self.topics.values()]
        }


class KnowledgeTopic:
    """Represents a specific topic within a domain."""
    
    def __init__(self, name: str, description: str = "", domain_id: Optional[UUID] = None):
        """
        Initialize a knowledge topic.
        
        Args:
            name: Name of the topic
            description: Description of the topic
            domain_id: ID of the parent domain (optional)
        """
        self.name = name
        self.description = description
        self.id = uuid.uuid4()
        self.domain_id = domain_id
        self.created_at = datetime.now()
        self.facts: Dict[UUID, KnowledgeFact] = {}
        self.subtopics: Dict[UUID, 'KnowledgeTopic'] = {}
    
    def add_fact(self, fact: 'KnowledgeFact') -> None:
        """
        Add a fact to this topic.
        
        Args:
            fact: Fact to add
        """
        self.facts[fact.id] = fact
        fact.topic_id = self.id
    
    def remove_fact(self, fact_id: UUID) -> None:
        """
        Remove a fact from this topic.
        
        Args:
            fact_id: ID of the fact to remove
        """
        if fact_id in self.facts:
            del self.facts[fact_id]
    
    def add_subtopic(self, subtopic: 'KnowledgeTopic') -> None:
        """
        Add a subtopic to this topic.
        
        Args:
            subtopic: Subtopic to add
        """
        self.subtopics[subtopic.id] = subtopic
    
    def remove_subtopic(self, subtopic_id: UUID) -> None:
        """
        Remove a subtopic from this topic.
        
        Args:
            subtopic_id: ID of the subtopic to remove
        """
        if subtopic_id in self.subtopics:
            del self.subtopics[subtopic_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the topic to a dictionary.
        
        Returns:
            Dictionary representation of the topic
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "domain_id": str(self.domain_id) if self.domain_id else None,
            "created_at": self.created_at.isoformat(),
            "facts": [fact.to_dict() for fact in self.facts.values()],
            "subtopics": [subtopic.to_dict() for subtopic in self.subtopics.values()]
        }


class KnowledgeFact:
    """Represents a piece of knowledge related to a topic."""
    
    def __init__(self, 
                content: str, 
                source: Optional[str] = None,
                confidence: float = 1.0,
                topic_id: Optional[UUID] = None):
        """
        Initialize a knowledge fact.
        
        Args:
            content: Textual content of the fact
            source: Source of the fact (optional)
            confidence: Confidence level (0.0-1.0)
            topic_id: ID of the parent topic (optional)
        """
        self.content = content
        self.source = source
        self.confidence = confidence
        self.id = uuid.uuid4()
        self.topic_id = topic_id
        self.created_at = datetime.now()
        self.last_verified = self.created_at
        self.verification_count = 1
        self.related_facts: Set[UUID] = set()
    
    def add_related_fact(self, fact_id: UUID) -> None:
        """
        Add a related fact.
        
        Args:
            fact_id: ID of the related fact
        """
        self.related_facts.add(fact_id)
    
    def remove_related_fact(self, fact_id: UUID) -> None:
        """
        Remove a related fact.
        
        Args:
            fact_id: ID of the related fact to remove
        """
        if fact_id in self.related_facts:
            self.related_facts.remove(fact_id)
    
    def verify(self, confidence: Optional[float] = None) -> None:
        """
        Verify this fact.
        
        Args:
            confidence: New confidence level (optional)
        """
        self.last_verified = datetime.now()
        self.verification_count += 1
        
        if confidence is not None:
            # Update confidence with running average
            self.confidence = ((self.confidence * (self.verification_count - 1)) + confidence) / self.verification_count
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the fact to a dictionary.
        
        Returns:
            Dictionary representation of the fact
        """
        return {
            "id": str(self.id),
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "topic_id": str(self.topic_id) if self.topic_id else None,
            "created_at": self.created_at.isoformat(),
            "last_verified": self.last_verified.isoformat(),
            "verification_count": self.verification_count,
            "related_facts": [str(fact_id) for fact_id in self.related_facts]
        }


class KnowledgeTracker:
    """
    Main knowledge tracking system.
    
    This class integrates with the Temporal-Spatial Knowledge Database to
    store and retrieve knowledge information.
    """
    
    def __init__(self, connection_url: str = "localhost:8000", api_key: Optional[str] = None):
        """
        Initialize the knowledge tracker.
        
        Args:
            connection_url: URL of the database
            api_key: Optional API key for authentication
        """
        self.client = DatabaseClient(connection_url=connection_url, api_key=api_key)
        
        # Cache for faster access
        self.domains: Dict[UUID, KnowledgeDomain] = {}
        self.topics: Dict[UUID, KnowledgeTopic] = {}
        self.facts: Dict[UUID, KnowledgeFact] = {}
        
        # Connect to database
        self.client.connect()
    
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
            "created_at": domain.created_at.timestamp()
        }
        
        # Calculate spatial coordinates (2D example)
        # In a real implementation, these would be meaningful coordinates
        # Here we're just generating random ones for demonstration
        x_coord = np.random.uniform(0, 100)
        y_coord = np.random.uniform(0, 100)
        
        # Create node with temporal-spatial position
        # The first coordinate is time (in timestamp format)
        position = [domain.created_at.timestamp(), x_coord, y_coord]
        
        node = Node(
            id=domain.id,
            content=json.dumps(domain.to_dict()),
            properties=properties,
            position=position
        )
        
        # Add to database
        self.client.add_node(node)
        
        # Cache locally
        self.domains[domain.id] = domain
        
        return node
    
    def add_topic(self, topic: KnowledgeTopic) -> Node:
        """
        Add a knowledge topic to the database.
        
        Args:
            topic: Topic to add
            
        Returns:
            The created node
        """
        # Get domain coordinates if available for relative positioning
        domain_coords = None
        if topic.domain_id and topic.domain_id in self.domains:
            domain = self.domains[topic.domain_id]
            domain_node = self._get_node_by_id(domain.id)
            if domain_node and domain_node.position:
                domain_coords = domain_node.position[1:3]  # Skip time coordinate
        
        # Create a node for the topic
        properties = {
            "name": topic.name,
            "description": topic.description,
            "type": "topic",
            "domain_id": str(topic.domain_id) if topic.domain_id else None,
            "created_at": topic.created_at.timestamp()
        }
        
        # Calculate spatial coordinates (2D example)
        if domain_coords:
            # Position near the domain
            x_coord = domain_coords[0] + np.random.uniform(-10, 10)
            y_coord = domain_coords[1] + np.random.uniform(-10, 10)
        else:
            # Random position
            x_coord = np.random.uniform(0, 100)
            y_coord = np.random.uniform(0, 100)
        
        # Create node with temporal-spatial position
        position = [topic.created_at.timestamp(), x_coord, y_coord]
        
        node = Node(
            id=topic.id,
            content=json.dumps(topic.to_dict()),
            properties=properties,
            position=position
        )
        
        # Add to database
        self.client.add_node(node)
        
        # Cache locally
        self.topics[topic.id] = topic
        
        # Create connection to domain if available
        if topic.domain_id:
            self._connect_nodes(topic.id, topic.domain_id, "belongs_to")
        
        return node
    
    def add_fact(self, fact: KnowledgeFact) -> Node:
        """
        Add a knowledge fact to the database.
        
        Args:
            fact: Fact to add
            
        Returns:
            The created node
        """
        # Get topic coordinates if available for relative positioning
        topic_coords = None
        if fact.topic_id and fact.topic_id in self.topics:
            topic = self.topics[fact.topic_id]
            topic_node = self._get_node_by_id(topic.id)
            if topic_node and topic_node.position:
                topic_coords = topic_node.position[1:3]  # Skip time coordinate
        
        # Create a node for the fact
        properties = {
            "content": fact.content,
            "source": fact.source,
            "confidence": fact.confidence,
            "type": "fact",
            "topic_id": str(fact.topic_id) if fact.topic_id else None,
            "created_at": fact.created_at.timestamp(),
            "last_verified": fact.last_verified.timestamp(),
            "verification_count": fact.verification_count
        }
        
        # Calculate spatial coordinates (2D example)
        if topic_coords:
            # Position near the topic
            x_coord = topic_coords[0] + np.random.uniform(-5, 5)
            y_coord = topic_coords[1] + np.random.uniform(-5, 5)
        else:
            # Random position
            x_coord = np.random.uniform(0, 100)
            y_coord = np.random.uniform(0, 100)
        
        # Create node with temporal-spatial position
        position = [fact.created_at.timestamp(), x_coord, y_coord]
        
        node = Node(
            id=fact.id,
            content=json.dumps(fact.to_dict()),
            properties=properties,
            position=position
        )
        
        # Add to database
        self.client.add_node(node)
        
        # Cache locally
        self.facts[fact.id] = fact
        
        # Create connection to topic if available
        if fact.topic_id:
            self._connect_nodes(fact.id, fact.topic_id, "belongs_to")
        
        # Create connections to related facts
        for related_id in fact.related_facts:
            self._connect_nodes(fact.id, related_id, "related_to")
        
        return node
    
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
            "created_at": fact.created_at.timestamp(),
            "last_verified": fact.last_verified.timestamp(),
            "verification_count": fact.verification_count
        }
        
        # Keep the same position
        position = node.position
        
        # Create updated node
        updated_node = Node(
            id=fact.id,
            content=json.dumps(fact.to_dict()),
            properties=properties,
            position=position
        )
        
        # Update in database
        self.client.update_node(updated_node)
        
        # Update cache
        self.facts[fact.id] = fact
        
        return updated_node
    
    def get_domain(self, domain_id: UUID) -> Optional[KnowledgeDomain]:
        """
        Get a domain by ID.
        
        Args:
            domain_id: ID of the domain to get
            
        Returns:
            The domain if found, None otherwise
        """
        # Check cache first
        if domain_id in self.domains:
            return self.domains[domain_id]
        
        # Get from database
        node = self._get_node_by_id(domain_id)
        if not node:
            return None
        
        # Parse domain from node
        try:
            domain_dict = json.loads(node.content)
            domain = KnowledgeDomain(
                name=domain_dict["name"],
                description=domain_dict["description"]
            )
            domain.id = UUID(domain_dict["id"])
            domain.created_at = datetime.fromisoformat(domain_dict["created_at"])
            
            # Cache the domain
            self.domains[domain.id] = domain
            
            return domain
        except Exception as e:
            logger.error(f"Failed to parse domain: {e}")
            return None
    
    def get_topic(self, topic_id: UUID) -> Optional[KnowledgeTopic]:
        """
        Get a topic by ID.
        
        Args:
            topic_id: ID of the topic to get
            
        Returns:
            The topic if found, None otherwise
        """
        # Check cache first
        if topic_id in self.topics:
            return self.topics[topic_id]
        
        # Get from database
        node = self._get_node_by_id(topic_id)
        if not node:
            return None
        
        # Parse topic from node
        try:
            topic_dict = json.loads(node.content)
            topic = KnowledgeTopic(
                name=topic_dict["name"],
                description=topic_dict["description"],
                domain_id=UUID(topic_dict["domain_id"]) if topic_dict["domain_id"] else None
            )
            topic.id = UUID(topic_dict["id"])
            topic.created_at = datetime.fromisoformat(topic_dict["created_at"])
            
            # Cache the topic
            self.topics[topic.id] = topic
            
            return topic
        except Exception as e:
            logger.error(f"Failed to parse topic: {e}")
            return None
    
    def get_fact(self, fact_id: UUID) -> Optional[KnowledgeFact]:
        """
        Get a fact by ID.
        
        Args:
            fact_id: ID of the fact to get
            
        Returns:
            The fact if found, None otherwise
        """
        # Check cache first
        if fact_id in self.facts:
            return self.facts[fact_id]
        
        # Get from database
        node = self._get_node_by_id(fact_id)
        if not node:
            return None
        
        # Parse fact from node
        try:
            fact_dict = json.loads(node.content)
            fact = KnowledgeFact(
                content=fact_dict["content"],
                source=fact_dict["source"],
                confidence=fact_dict["confidence"],
                topic_id=UUID(fact_dict["topic_id"]) if fact_dict["topic_id"] else None
            )
            fact.id = UUID(fact_dict["id"])
            fact.created_at = datetime.fromisoformat(fact_dict["created_at"])
            fact.last_verified = datetime.fromisoformat(fact_dict["last_verified"])
            fact.verification_count = fact_dict["verification_count"]
            
            # Add related facts
            for related_id_str in fact_dict["related_facts"]:
                fact.related_facts.add(UUID(related_id_str))
            
            # Cache the fact
            self.facts[fact.id] = fact
            
            return fact
        except Exception as e:
            logger.error(f"Failed to parse fact: {e}")
            return None
    
    def get_facts_by_topic(self, topic_id: UUID) -> List[KnowledgeFact]:
        """
        Get all facts for a topic.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            List of facts
        """
        query_builder = self.client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "fact")
                .filter_by_property("topic_id", str(topic_id))
                .build())
        
        # Execute query
        nodes = self.client.query(query)
        
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
                fact.created_at = datetime.fromisoformat(fact_dict["created_at"])
                fact.last_verified = datetime.fromisoformat(fact_dict["last_verified"])
                fact.verification_count = fact_dict["verification_count"]
                
                # Add related facts
                for related_id_str in fact_dict["related_facts"]:
                    fact.related_facts.add(UUID(related_id_str))
                
                # Cache the fact
                self.facts[fact.id] = fact
                
                facts.append(fact)
            except Exception as e:
                logger.error(f"Failed to parse fact: {e}")
        
        return facts
    
    def get_topics_by_domain(self, domain_id: UUID) -> List[KnowledgeTopic]:
        """
        Get all topics for a domain.
        
        Args:
            domain_id: ID of the domain
            
        Returns:
            List of topics
        """
        query_builder = self.client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "topic")
                .filter_by_property("domain_id", str(domain_id))
                .build())
        
        # Execute query
        nodes = self.client.query(query)
        
        # Parse topics from nodes
        topics = []
        for node in nodes:
            try:
                topic_dict = json.loads(node.content)
                topic = KnowledgeTopic(
                    name=topic_dict["name"],
                    description=topic_dict["description"],
                    domain_id=UUID(topic_dict["domain_id"]) if topic_dict["domain_id"] else None
                )
                topic.id = UUID(topic_dict["id"])
                topic.created_at = datetime.fromisoformat(topic_dict["created_at"])
                
                # Cache the topic
                self.topics[topic.id] = topic
                
                topics.append(topic)
            except Exception as e:
                logger.error(f"Failed to parse topic: {e}")
        
        return topics
    
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
        query_builder = self.client.create_query_builder()
        query = (query_builder
                .filter_by_property("type", "fact")
                .filter_by_time_range(start_time, end_time)
                .build())
        
        # Execute query
        nodes = self.client.query(query)
        
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
                fact.created_at = datetime.fromisoformat(fact_dict["created_at"])
                fact.last_verified = datetime.fromisoformat(fact_dict["last_verified"])
                fact.verification_count = fact_dict["verification_count"]
                
                # Add related facts
                for related_id_str in fact_dict["related_facts"]:
                    fact.related_facts.add(UUID(related_id_str))
                
                # Cache the fact
                self.facts[fact.id] = fact
                
                facts.append(fact)
            except Exception as e:
                logger.error(f"Failed to parse fact: {e}")
        
        return facts
    
    def _get_node_by_id(self, node_id: UUID) -> Optional[Node]:
        """
        Get a node by ID from the database.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            The node if found, None otherwise
        """
        try:
            return self.client.get_node(node_id)
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def _connect_nodes(self, 
                      source_id: UUID, 
                      target_id: UUID, 
                      relationship_type: str) -> bool:
        """
        Create a connection between two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            relationship_type: Type of relationship
            
        Returns:
            True if successful, False otherwise
        """
        # This is a placeholder - actual implementation would use the database client
        # to create a connection between nodes
        logger.info(f"Creating connection {source_id} --[{relationship_type}]--> {target_id}")
        return True
    
    def close(self) -> None:
        """Close the connection to the database."""
        self.client.disconnect() 
"""
Simple Test for Knowledge Tracker

This script demonstrates the basic functionality of the Knowledge Tracker classes
without requiring the database or visualization components.
"""

import uuid
import logging
import traceback
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_knowledge_domain():
    """Test the KnowledgeDomain class functionality."""
    try:
        # Import from local directory instead of using examples path
        from tracker import KnowledgeDomain, KnowledgeTopic, KnowledgeFact
        
        # Create a domain
        domain = KnowledgeDomain(
            name="Artificial Intelligence",
            description="Knowledge about AI and machine learning"
        )
        
        # Check domain properties
        logger.info(f"Created domain: {domain.name} ({domain.id})")
        logger.info(f"Domain description: {domain.description}")
        logger.info(f"Domain created at: {domain.created_at}")
        
        # Create a topic
        topic = KnowledgeTopic(
            name="Machine Learning",
            description="Statistical techniques for learning from data"
        )
        
        # Add topic to domain
        domain.add_topic(topic)
        logger.info(f"Added topic {topic.name} to domain {domain.name}")
        
        # Check that topic was added correctly
        assert topic.id in domain.topics
        assert topic.domain_id == domain.id
        
        # Create a fact
        fact = KnowledgeFact(
            content="Random forests combine multiple decision trees",
            source="Research paper",
            confidence=0.9
        )
        
        # Add fact to topic
        topic.add_fact(fact)
        logger.info(f"Added fact to topic {topic.name}")
        
        # Check that fact was added correctly
        assert fact.id in topic.facts
        assert fact.topic_id == topic.id
        
        # Test serialization
        domain_dict = domain.to_dict()
        logger.info(f"Serialized domain to dictionary with {len(domain_dict)} entries")
        
        # Verify topics are included in serialization
        assert "topics" in domain_dict
        assert len(domain_dict["topics"]) == 1
        
        return True
    except Exception as e:
        logger.error(f"Error in test_knowledge_domain: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all tests."""
    try:
        logger.info("Starting simple tests")
        
        # Test the knowledge domain functionality
        success = test_knowledge_domain()
        
        if success:
            logger.info("All tests passed successfully!")
            print("\nAll tests passed successfully!")
            print("The basic classes for the Knowledge Tracker are usable.")
        else:
            logger.error("Tests failed!")
            print("\nTests failed!")
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"\nUnexpected error: {str(e)}")
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    main() 
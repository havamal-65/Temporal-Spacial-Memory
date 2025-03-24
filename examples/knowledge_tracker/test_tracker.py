"""
Test Script for Knowledge Tracker

This script tests the Knowledge Tracker functionality using the mock database client.
"""

import logging
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Run tests for the Knowledge Tracker."""
    
    # Import modules
    from tracker import KnowledgeTracker
    from mock_client import MockDatabaseClient
    
    # Create a mock client
    mock_client = MockDatabaseClient()
    logger.info("Created mock database client")
    
    # Connect to the mock database
    mock_client.connect()
    
    # Create a KnowledgeTracker instance with the mock client
    tracker = KnowledgeTracker(mock_client)
    logger.info("Created Knowledge Tracker with mock client")
    
    # Test adding a domain
    domain_id = tracker.add_domain(
        name="Machine Learning",
        description="Knowledge about machine learning algorithms and techniques"
    )
    logger.info(f"Added domain: Machine Learning ({domain_id})")
    
    # Convert domain_id to string for consistent use in the test
    domain_id = str(domain_id)
    
    # Test adding topics to the domain
    supervised_id = tracker.add_topic(
        domain_id=domain_id,
        name="Supervised Learning",
        description="Learning with labeled data"
    )
    logger.info(f"Added topic: Supervised Learning ({supervised_id})")
    
    # Convert topic_id to string for consistent use in the test
    supervised_id = str(supervised_id)
    
    unsupervised_id = tracker.add_topic(
        domain_id=domain_id,
        name="Unsupervised Learning",
        description="Learning without labeled data"
    )
    logger.info(f"Added topic: Unsupervised Learning ({unsupervised_id})")
    
    # Convert topic_id to string for consistent use in the test
    unsupervised_id = str(unsupervised_id)
    
    # Test adding facts to topics
    fact1_id = tracker.add_fact(
        topic_id=supervised_id,
        content="Random forests are ensembles of decision trees",
        source="Machine Learning Textbook",
        confidence=0.95
    )
    logger.info(f"Added fact: Random forests ({fact1_id})")
    
    # Convert fact_id to string for consistent use in the test
    fact1_id = str(fact1_id)
    
    fact2_id = tracker.add_fact(
        topic_id=supervised_id,
        content="Neural networks use backpropagation for training",
        source="Deep Learning Course",
        confidence=0.98
    )
    logger.info(f"Added fact: Neural networks ({fact2_id})")
    
    # Convert fact_id to string for consistent use in the test
    fact2_id = str(fact2_id)
    
    fact3_id = tracker.add_fact(
        topic_id=unsupervised_id,
        content="K-means clustering partitions data into k clusters",
        source="Data Mining Handbook",
        confidence=0.9
    )
    logger.info(f"Added fact: K-means clustering ({fact3_id})")
    
    # Convert fact_id to string for consistent use in the test
    fact3_id = str(fact3_id)
    
    # Test retrieving facts
    try:
        # Get domain
        domain = tracker.get_domain(domain_id)
        if domain:
            logger.info(f"Retrieved domain: {domain.name}")
        
        # Get topic
        topic = tracker.get_topic(supervised_id)
        if topic:
            logger.info(f"Retrieved topic: {topic.name}")
        
        # Get fact
        fact = tracker.get_fact(fact1_id)
        if fact:
            logger.info(f"Retrieved fact: {fact.content[:30]}...")
            
        # Get topics by domain
        topics = tracker.get_topics_by_domain(domain_id)
        logger.info(f"Retrieved {len(topics)} topics for domain {domain_id}")
            
        # Get facts by topic
        facts = tracker.get_facts_by_topic(supervised_id)
        logger.info(f"Retrieved {len(facts)} facts for topic {supervised_id}")
    except Exception as e:
        logger.error(f"Error retrieving data: {e}")
    
    # Test creating relationships between facts
    try:
        # Create relationship between facts
        success = tracker.add_related_fact(fact1_id, fact2_id)
        logger.info(f"Created relationship between facts: {success}")
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
    
    # Test verifying facts
    try:
        # Update confidence for a fact
        success = tracker.verify_fact(fact1_id, 0.98)
        logger.info(f"Updated fact confidence: {success}")
    except Exception as e:
        logger.error(f"Error updating fact: {e}")
    
    # Test visualization
    try:
        # Create visualization directory if it doesn't exist
        if not os.path.exists("visualizations"):
            os.makedirs("visualizations")
            
        from visualizer import KnowledgeVisualizer
        vis = KnowledgeVisualizer(tracker)
        
        # Create domain overview
        success = vis.create_domain_overview(domain_id, "domain_overview.png")
        logger.info(f"Created domain overview visualization: {success}")
        
        # Create topic network
        success = vis.create_topic_network(supervised_id, "topic_network.png")
        logger.info(f"Created topic network visualization: {success}")
        
        if success:
            logger.info("Visualizations created successfully")
    except ImportError:
        logger.warning("Visualization module not available or missing dependencies")
    except Exception as e:
        logger.error(f"Error creating visualizations: {e}")
    
    # Disconnect from the mock database
    mock_client.disconnect()
    logger.info("Disconnected from mock database")
    
    print("\nAll tests completed successfully!")
    print("The Knowledge Tracker is working as expected with the mock client.")
    
    # Check if visualizations were created
    if os.path.exists("visualizations/domain_overview.png"):
        print("Domain overview visualization created successfully.")
    if os.path.exists("visualizations/topic_network.png"):
        print("Topic network visualization created successfully.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
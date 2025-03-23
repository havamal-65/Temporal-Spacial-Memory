"""
Knowledge Tracker Example Application

This example demonstrates how to use the Temporal-Spatial Knowledge Database
to track and visualize AI knowledge across domains, topics, and facts.
"""

import os
import sys
import logging
from uuid import uuid4
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import random

# Add project root to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.client import Client
from src.database import DatabaseConfig
from examples.knowledge_tracker import KnowledgeTracker, VisualizationTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_knowledge_base():
    """
    Create a sample knowledge base with AI domains, topics, and facts.
    
    Returns:
        tuple: (tracker, ai_domain_id)
    """
    # Set up database connection
    config = DatabaseConfig(
        host="localhost",
        port=7687,
        username="neo4j",
        password="password",
        database="temporal-spatial"
    )
    
    # Initialize client and knowledge tracker
    client = Client(config)
    tracker = KnowledgeTracker(client)
    
    # Create AI domain
    ai_domain_id = tracker.add_domain(
        name="Artificial Intelligence",
        description="Knowledge about AI, machine learning, and related technologies"
    )
    
    # Create Machine Learning topic
    ml_topic_id = tracker.add_topic(
        domain_id=ai_domain_id,
        name="Machine Learning",
        description="Statistical techniques that enable computers to learn from data"
    )
    
    # Create Neural Networks topic
    nn_topic_id = tracker.add_topic(
        domain_id=ai_domain_id,
        name="Neural Networks",
        description="Computing systems inspired by biological neural networks"
    )
    
    # Create Reinforcement Learning topic
    rl_topic_id = tracker.add_topic(
        domain_id=ai_domain_id,
        name="Reinforcement Learning",
        description="Training agents to make sequences of decisions"
    )
    
    # Create NLP topic
    nlp_topic_id = tracker.add_topic(
        domain_id=ai_domain_id,
        name="Natural Language Processing",
        description="Processing and analyzing human language"
    )
    
    # Create Computer Vision topic
    cv_topic_id = tracker.add_topic(
        domain_id=ai_domain_id,
        name="Computer Vision",
        description="Enabling computers to interpret visual information"
    )
    
    # Add facts to Machine Learning topic
    ml_facts = [
        ("Supervised learning requires labeled training data", 0.95, "textbook"),
        ("Unsupervised learning works with unlabeled data", 0.92, "textbook"),
        ("Decision trees split data based on feature values", 0.88, "research paper"),
        ("Random Forests combine multiple decision trees", 0.85, "lecture notes"),
        ("Support Vector Machines find optimal hyperplanes", 0.80, "research paper"),
        ("Feature engineering is critical for traditional ML", 0.75, "blog post"),
        ("Cross-validation helps prevent overfitting", 0.90, "textbook"),
    ]
    
    ml_fact_ids = []
    for content, confidence, source in ml_facts:
        fact_id = tracker.add_fact(
            topic_id=ml_topic_id,
            content=content,
            source=source,
            confidence=confidence
        )
        ml_fact_ids.append(fact_id)
    
    # Add facts to Neural Networks topic
    nn_facts = [
        ("Deep learning uses multiple layers of neural networks", 0.95, "textbook"),
        ("Convolutional Neural Networks are specialized for image data", 0.92, "research paper"),
        ("Recurrent Neural Networks process sequential data", 0.88, "lecture notes"),
        ("Backpropagation calculates gradients for neural network training", 0.85, "textbook"),
        ("Transformers use self-attention mechanisms", 0.78, "research paper"),
        ("Activation functions introduce non-linearity", 0.92, "textbook"),
        ("Dropout helps prevent overfitting in neural networks", 0.85, "research paper"),
    ]
    
    nn_fact_ids = []
    for content, confidence, source in nn_facts:
        fact_id = tracker.add_fact(
            topic_id=nn_topic_id,
            content=content,
            source=source,
            confidence=confidence
        )
        nn_fact_ids.append(fact_id)
    
    # Add facts to Reinforcement Learning topic
    rl_facts = [
        ("Q-learning is a model-free reinforcement learning algorithm", 0.90, "textbook"),
        ("Policy gradient methods directly optimize the policy", 0.85, "research paper"),
        ("Exploration-exploitation trade-off is fundamental in RL", 0.92, "lecture notes"),
        ("Deep Q-Networks combine Q-learning with neural networks", 0.88, "research paper"),
        ("Monte Carlo Tree Search was used in AlphaGo", 0.78, "news article"),
    ]
    
    rl_fact_ids = []
    for content, confidence, source in rl_facts:
        fact_id = tracker.add_fact(
            topic_id=rl_topic_id,
            content=content,
            source=source,
            confidence=confidence
        )
        rl_fact_ids.append(fact_id)
    
    # Add facts to NLP topic
    nlp_facts = [
        ("Word embeddings represent words as vectors", 0.95, "textbook"),
        ("BERT is a transformer-based language model", 0.90, "research paper"),
        ("Named Entity Recognition identifies entities in text", 0.85, "lecture notes"),
        ("Sentiment analysis determines emotional tone in text", 0.82, "blog post"),
        ("Large Language Models are trained on massive text corpora", 0.95, "research paper"),
        ("Token classification assigns labels to individual tokens", 0.80, "textbook"),
    ]
    
    nlp_fact_ids = []
    for content, confidence, source in nlp_facts:
        fact_id = tracker.add_fact(
            topic_id=nlp_topic_id,
            content=content,
            source=source,
            confidence=confidence
        )
        nlp_fact_ids.append(fact_id)
    
    # Add facts to Computer Vision topic
    cv_facts = [
        ("Object detection locates and classifies objects in images", 0.92, "textbook"),
        ("Image segmentation partitions images into segments", 0.88, "research paper"),
        ("Feature extraction identifies important features in images", 0.85, "lecture notes"),
        ("GANs can generate realistic synthetic images", 0.80, "research paper"),
        ("Transfer learning reuses pre-trained models", 0.90, "blog post"),
    ]
    
    cv_fact_ids = []
    for content, confidence, source in cv_facts:
        fact_id = tracker.add_fact(
            topic_id=cv_topic_id,
            content=content,
            source=source,
            confidence=confidence
        )
        cv_fact_ids.append(fact_id)
    
    # Connect related facts
    # Connect ML and NN facts
    tracker.add_related_fact(ml_fact_ids[0], nn_fact_ids[0])  # Supervised learning - Deep learning
    tracker.add_related_fact(ml_fact_ids[6], nn_fact_ids[6])  # Cross-validation - Dropout
    
    # Connect NN and CV facts
    tracker.add_related_fact(nn_fact_ids[1], cv_fact_ids[0])  # CNNs - Object detection
    
    # Connect NN and NLP facts
    tracker.add_related_fact(nn_fact_ids[2], nlp_fact_ids[0])  # RNNs - Word embeddings
    tracker.add_related_fact(nn_fact_ids[4], nlp_fact_ids[1])  # Transformers - BERT
    
    # Connect ML and RL facts
    tracker.add_related_fact(ml_fact_ids[3], rl_fact_ids[0])  # Random Forests - Q-learning
    
    logger.info(f"Created knowledge base with domain ID: {ai_domain_id}")
    return tracker, ai_domain_id


def simulate_knowledge_verification(tracker, domain_id, days=30, actions_per_day=5):
    """
    Simulate knowledge verification and updates over time.
    
    Args:
        tracker: Knowledge tracker instance
        domain_id: Domain ID
        days: Number of days to simulate
        actions_per_day: Actions per day
    """
    # Get all topics in the domain
    topics = tracker.get_topics_by_domain(domain_id)
    
    # Simulate activities over time
    start_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        logger.info(f"Simulating activities for day {day+1} ({current_date.date()})")
        
        # Perform random actions each day
        for _ in range(actions_per_day):
            action_type = random.choice(["verify", "add_fact", "add_topic"])
            
            if action_type == "verify":
                # Verify a random fact
                topic = random.choice(topics)
                facts = tracker.get_facts_by_topic(topic.id)
                if facts:
                    fact = random.choice(facts)
                    # Verify with random confidence adjustment
                    confidence_adjustment = random.uniform(-0.05, 0.1)
                    new_confidence = min(max(fact.confidence + confidence_adjustment, 0.1), 0.99)
                    tracker.verify_fact(fact.id, new_confidence)
                    logger.debug(f"Verified fact: {fact.content[:30]}...")
            
            elif action_type == "add_fact":
                # Add a new fact to a random topic
                topic = random.choice(topics)
                content = f"New research finding from day {day+1}"
                source = random.choice(["new paper", "blog post", "conference", "experiment"])
                confidence = random.uniform(0.6, 0.9)
                fact_id = tracker.add_fact(topic.id, content, source, confidence)
                logger.debug(f"Added new fact to topic {topic.name}")
            
            elif action_type == "add_topic":
                # Add a new topic every few days
                if random.random() < 0.2:  # 20% chance
                    topic_name = f"Emerging AI Area {day}"
                    topic_id = tracker.add_topic(
                        domain_id=domain_id,
                        name=topic_name,
                        description=f"New AI research direction discovered on day {day+1}"
                    )
                    topics.append(tracker.get_topic(topic_id))
                    logger.debug(f"Added new topic: {topic_name}")
    
    logger.info("Completed knowledge verification simulation")


def demonstrate_visualization(tracker, domain_id):
    """
    Demonstrate visualization capabilities.
    
    Args:
        tracker: Knowledge tracker instance
        domain_id: Domain ID
    """
    # Create visualization tool
    vis_tool = VisualizationTool(tracker)
    
    # Get topics
    topics = tracker.get_topics_by_domain(domain_id)
    
    # 1. Domain visualization
    logger.info("Generating domain visualization...")
    fig_domain = vis_tool.visualize_domain(domain_id)
    fig_domain.savefig("domain_visualization.png")
    plt.close(fig_domain)
    
    # 2. Topics over time
    logger.info("Generating topics over time visualization...")
    fig_topics_time = vis_tool.visualize_topics_over_time(domain_id)
    fig_topics_time.savefig("topics_over_time.png")
    plt.close(fig_topics_time)
    
    # 3. Confidence distribution for a topic
    if topics:
        logger.info("Generating confidence distribution visualization...")
        # Use the first topic for the example
        fig_confidence = vis_tool.visualize_confidence_distribution(topics[0].id)
        fig_confidence.savefig("confidence_distribution.png")
        plt.close(fig_confidence)
    
    # 4. Fact verification history
    if topics:
        logger.info("Generating fact verification history visualization...")
        fig_verification = vis_tool.visualize_fact_verification_history(topics[0].id)
        fig_verification.savefig("fact_verification_history.png")
        plt.close(fig_verification)
    
    # 5. Temporal-spatial distribution
    logger.info("Generating temporal-spatial distribution visualization...")
    fig_temporal_spatial = vis_tool.visualize_temporal_spatial_distribution(domain_id)
    fig_temporal_spatial.savefig("temporal_spatial_distribution.png")
    plt.close(fig_temporal_spatial)
    
    logger.info("All visualizations have been saved as PNG files")


def main():
    """Main function to run the knowledge tracker example."""
    logger.info("Starting Knowledge Tracker Example")
    
    try:
        # Create sample knowledge base
        tracker, domain_id = create_sample_knowledge_base()
        
        # Simulate knowledge verification over time
        simulate_knowledge_verification(tracker, domain_id)
        
        # Demonstrate visualization
        demonstrate_visualization(tracker, domain_id)
        
        logger.info("Example completed successfully")
        print("\nExample completed successfully!")
        print("Visualization files have been saved in the current directory.")
        print("You can explore the knowledge base using the KnowledgeTracker API.")
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
        print(f"An error occurred: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 
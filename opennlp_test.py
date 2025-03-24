#!/usr/bin/env python3
"""
Test script for OpenNLP integration.

This script tests the basic functionality of the OpenNLP integration.
It's intended as a quick validation of the setup before running the
full process_hobbit_with_opennlp.py script.
"""

import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if Java is installed
try:
    import jpype
    logger.info(f"JPype version: {jpype.__version__}")
    logger.info(f"Default JVM path: {jpype.getDefaultJVMPath()}")
except ImportError:
    logger.error("JPype is not installed. Please install it using: pip install JPype1")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error loading JPype: {str(e)}")
    logger.error("Java may not be installed or properly configured")
    sys.exit(1)

# Test OpenNLP processor
logger.info("Testing OpenNLP processor...")
try:
    from src.nlp.opennlp.processor import OpenNLPProcessor
    
    # Create and initialize the processor
    processor = OpenNLPProcessor()
    logger.info("Created OpenNLP processor")
    
    # Initialize the processor
    if processor.initialize():
        logger.info("Successfully initialized OpenNLP processor")
    else:
        logger.error("Failed to initialize OpenNLP processor")
        sys.exit(1)
    
    # Test with a simple text
    test_text = """
    Bilbo Baggins was a very well-to-do hobbit who lived in Hobbiton, a village in the Shire.
    One day, Gandalf the Grey came to visit Bilbo and invited him on an adventure with Thorin Oakenshield
    and his company of dwarves. Together, they journeyed to the Lonely Mountain to reclaim the dwarves'
    treasure from the dragon Smaug.
    """
    
    logger.info("Testing entity extraction...")
    entities = processor.extract_entities(test_text)
    logger.info(f"Extracted entities: {entities}")
    
    logger.info("Testing relationship analysis...")
    relationships = processor.analyze_relationships(test_text)
    logger.info(f"Analyzed relationships: {relationships}")
    
    logger.info("Testing event extraction...")
    events = processor.extract_events(test_text)
    logger.info(f"Extracted events: {events}")
    
    logger.info("Testing sentiment analysis...")
    sentiment = processor.analyze_sentiment(test_text)
    logger.info(f"Analyzed sentiment: {sentiment}")
    
    # Clean up
    processor.close()
    logger.info("OpenNLP test completed successfully")
    
except Exception as e:
    logger.error(f"Error testing OpenNLP: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

logger.info("All tests completed successfully") 
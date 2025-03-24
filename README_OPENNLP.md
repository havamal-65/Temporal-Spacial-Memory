# Apache OpenNLP Integration for Narrative Atlas

This branch integrates Apache OpenNLP with the Narrative Atlas framework to provide improved natural language processing capabilities.

## Overview

The Apache OpenNLP integration enhances the Narrative Atlas framework with:

- Improved named entity recognition for characters, locations, and organizations
- Better relationship extraction between entities
- Enhanced event detection and classification
- Sentiment analysis to understand the emotional tone of text segments
- Automatic detection of narrative structure and themes

## Requirements

- Python 3.8+
- Java 8+ (for running Apache OpenNLP)
- JPype1 for Java-Python integration

Install the requirements using:
```bash
pip install -r opennlp_requirements.txt
```

## Getting Started

1. Make sure you have Java installed and available on your system path
2. Run the Hobbit processing script with OpenNLP integration:
   ```bash
   python process_hobbit_with_opennlp.py
   ```
3. Open the generated launcher HTML file to explore the visualizations:
   ```
   Output/the_hobbit_opennlp_launcher.html
   ```

## Architecture

The integration consists of three main components:

1. **OpenNLPProcessor** (`src/nlp/opennlp/processor.py`): Handles the direct interaction with Apache OpenNLP through JPype. It provides methods for entity extraction, relationship analysis, and event detection.

2. **OpenNLPIntegration** (`src/nlp/opennlp/integration.py`): Connects the OpenNLP processor to the Narrative Atlas framework, handling the conversion between OpenNLP's output and the Narrative Atlas data structures.

3. **Processing Script** (`process_hobbit_with_opennlp.py`): Demonstrates the use of the OpenNLP integration by processing "The Hobbit" and generating visualizations.

## Implementation Status

The current implementation includes:

- ✅ Basic framework for OpenNLP integration
- ✅ Entity extraction (characters, locations, organizations)
- ✅ Relationship extraction
- ✅ Event detection
- ✅ Visualization enhancements

Planned improvements:

- 🔲 Full JPype integration for Apache OpenNLP
- 🔲 Automatic model downloading
- 🔲 Improved sentiment analysis
- 🔲 Custom models for literary text analysis

## License

This integration is licensed under the same license as the Narrative Atlas framework.

Apache OpenNLP is licensed under the Apache License 2.0. 
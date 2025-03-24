# Apache OpenNLP Integration Installation Guide

This guide provides step-by-step instructions for setting up the Apache OpenNLP integration for the Narrative Atlas project.

## Prerequisites

Before you begin, ensure you have the following prerequisites installed:

1. **Python 3.8+** - The core language used by the Narrative Atlas framework
2. **Java 8+** - Required to run Apache OpenNLP (which is Java-based)
3. **Git** - For cloning the repository

## Step 1: Check Java Installation

First, verify that Java is properly installed on your system.

### On Windows

```powershell
java -version
```

### On Linux/macOS

```bash
java -version
```

You should see output similar to this (version may vary):
```
openjdk version "11.0.11" 2021-04-20
OpenJDK Runtime Environment (build 11.0.11+9-Ubuntu-0ubuntu2.20.04)
OpenJDK 64-Bit Server VM (build 11.0.11+9-Ubuntu-0ubuntu2.20.04, mixed mode, sharing)
```

If Java is not installed, download and install it from the [Oracle website](https://www.oracle.com/java/technologies/javase-downloads.html) or using your package manager.

## Step 2: Install Python Dependencies

Install the required Python packages:

```bash
pip install -r opennlp_requirements.txt
```

The most important package is JPype1, which provides the Python-Java bridge:

```bash
pip install JPype1>=1.3.0
```

## Step 3: Set Up OpenNLP

The OpenNLP processor will automatically download the required JAR file and models when you first run it. However, if you prefer to set up manually:

1. Create a `lib` directory in your project root:
   ```bash
   mkdir lib
   ```

2. Download Apache OpenNLP from the [official site](https://opennlp.apache.org/download.html) (version 2.2.0+)

3. Extract the ZIP file and locate the `opennlp-tools-2.2.0.jar` file

4. Copy this JAR file to the `lib` directory:
   ```bash
   cp /path/to/opennlp-tools-2.2.0.jar lib/
   ```

## Step 4: Set Up OpenNLP Models

The OpenNLP processor will automatically download required models, but if you prefer to download them manually:

1. Create a models directory:
   ```bash
   mkdir -p models/opennlp
   ```

2. Download the following models from Apache:
   - [English Tokenizer](https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-tokens-1.0-1.9.3.bin)
   - [English Sentence Detector](https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-sentence-1.0-1.9.3.bin)
   - [English POS Tagger](https://dlcdn.apache.org/opennlp/models/ud-models-1.0/opennlp-en-ud-ewt-pos-1.0-1.9.3.bin)
   - [Named Entity Recognizer](https://dlcdn.apache.org/opennlp/models/langdetect/1.8.3/langdetect-183.bin)

3. Save these files to the `models/opennlp` directory with the following names:
   - `en-token.bin`
   - `en-sent.bin`
   - `en-pos-maxent.bin`
   - `en-ner-person.bin`
   - `en-ner-location.bin`
   - `en-ner-organization.bin`
   - `en-ner-date.bin`
   - `en-ner-time.bin`

## Step 5: Test the Installation

Run the test script to verify your installation:

```bash
python opennlp_test.py
```

This will:
1. Check if Java and JPype are properly installed
2. Initialize the OpenNLP processor
3. Test basic functionality with a sample text

If all tests pass, you'll see "All tests completed successfully" at the end.

## Step 6: Process The Hobbit

Once the installation is verified, you can process The Hobbit text:

```bash
python process_hobbit_with_opennlp.py
```

This will create an enhanced narrative visualization using OpenNLP for improved entity extraction, relationship analysis, and event detection.

## Troubleshooting

### Common Issues

1. **Java not found**:
   - Ensure Java is installed and available in your PATH
   - Set the JAVA_HOME environment variable

2. **JPype initialization errors**:
   - Ensure the Java and Python architectures match (both 32-bit or both 64-bit)
   - Check that you have the correct JAR file path

3. **Model loading errors**:
   - Verify that the model files are correctly named and placed in the `models/opennlp` directory
   - Check file permissions

### Getting Help

If you encounter issues, check:
- The project's GitHub issues page
- The Apache OpenNLP documentation: https://opennlp.apache.org/docs/
- JPype documentation: https://jpype.readthedocs.io/ 
import os
import re
import uuid
import json
from datetime import datetime
import sys

# Add the project root to the Python path to find the modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
from src.models.mesh_tube import MeshTube
from src.models.node import Node

# Constants
TITLE = "The Hobbit"
CHAPTER = "Chapter I: An Unexpected Party"
AUTHOR = "J.R.R. Tolkien"

def create_memory_database():
    """Create a new memory database for storing literature entries."""
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Create the database with proper initialization
    db = MeshTube(
        name="literature_memory",
        storage_path=os.path.join(data_dir, 'literature_memory.db')
    )
    return db

def extract_paragraphs(text):
    """Split the text into paragraphs."""
    # Clean up any issues with line breaks and split by paragraph
    text = re.sub(r'\n+', '\n', text)
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def extract_sentences(paragraph):
    """Split a paragraph into sentences."""
    # Basic sentence splitting - this could be improved with NLP libraries
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    return [s.strip() for s in sentences if s.strip()]

def extract_characters(text):
    """Extract character names from the text."""
    characters = set()
    character_patterns = [
        r'Bilbo', r'Gandalf', r'Thorin', r'Dwalin', r'Balin', 
        r'Kili', r'Fili', r'Dori', r'Nori', r'Ori', r'Oin', 
        r'Gloin', r'Bifur', r'Bofur', r'Bombur', r'Baggins', 
        r'Took', r'Belladonna', r'Bungo', r'Smaug', r'Thror', 
        r'Thrain', r'Azog'
    ]
    
    for pattern in character_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            characters.add(match.group(0))
    
    return list(characters)

def extract_locations(text):
    """Extract location names from the text."""
    locations = set()
    location_patterns = [
        r'The Hill', r'Bag-End', r'Under-Hill', r'Dale', 
        r'The Mountain', r'The Water', r'Moria', 
        r'The Blue', r'Mirkwood', r'Withered Heath', r'Front Gate',
        r'Side-door', r'Lower Halls'
    ]
    
    for pattern in location_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            locations.add(match.group(0))
    
    return list(locations)

def extract_key_themes(text):
    """Extract key themes from the text."""
    themes = [
        "Adventure", "Home", "Comfort", "Journey", 
        "Treasure", "Dragon", "Unexpected events",
        "Transformation", "Respectability", "Courage",
        "Heroism", "Magic", "Ordinary vs Extraordinary"
    ]
    
    # Only include themes that actually appear in the text
    return [theme for theme in themes if re.search(r'\b' + re.escape(theme.lower()) + r'\b', text.lower())]

def extract_key_events(paragraphs):
    """Extract key events from the paragraphs."""
    key_events = [
        {"event": "Introduction of Bilbo Baggins and his hobbit-hole", "paragraph_idx": 0},
        {"event": "Description of Bilbo's comfortable home", "paragraph_idx": 1},
        {"event": "Gandalf arrives at Bilbo's door", "paragraph_idx": 10},
        {"event": "Gandalf marks Bilbo's door", "paragraph_idx": 25},
        {"event": "Unexpected arrival of dwarves", "paragraph_idx": 27},
        {"event": "The dwarves eat Bilbo's food", "paragraph_idx": 45},
        {"event": "Thorin explains the quest to reclaim treasure from Smaug", "paragraph_idx": 65},
        {"event": "The map and key are revealed", "paragraph_idx": 70},
        {"event": "The dwarves sing about the Misty Mountains and their lost gold", "paragraph_idx": 80},
        {"event": "Bilbo feels the call to adventure", "paragraph_idx": 85},
        {"event": "Bilbo agrees to join the quest", "paragraph_idx": 90}
    ]
    
    # Adjust paragraph indices to match actual paragraphs
    for event in key_events:
        idx = min(event["paragraph_idx"], len(paragraphs) - 1)
        event["content"] = paragraphs[idx][:200] + "..." if len(paragraphs[idx]) > 200 else paragraphs[idx]
    
    return key_events

def process_text(text):
    """Process the literary text and return structured information."""
    paragraphs = extract_paragraphs(text)
    
    # Create a structured representation of the text
    structured_data = {
        "title": TITLE,
        "chapter": CHAPTER,
        "author": AUTHOR,
        "id": str(uuid.uuid4()),
        "date_processed": datetime.now().isoformat(),
        "paragraphs": paragraphs,
        "characters": extract_characters(text),
        "locations": extract_locations(text),
        "themes": extract_key_themes(text),
        "key_events": extract_key_events(paragraphs),
        "total_paragraphs": len(paragraphs)
    }
    
    return structured_data

def add_to_memory_database(text, title=None):
    """Add a piece of literature to the memory database."""
    db = create_memory_database()
    
    # Generate a unique entry ID
    entry_id = str(uuid.uuid4())
    
    # Create root node
    root_content = {
        'type': 'literature_entry',
        'title': title or 'Untitled',
        'entry_id': entry_id,
        'timestamp': datetime.now().isoformat()
    }
    root_node = db.add_node(content=root_content, time=0, distance=0, angle=0)
    
    # Split text into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Process each paragraph
    for i, paragraph in enumerate(paragraphs):
        # Create paragraph node
        para_content = {
            'type': 'paragraph',
            'content': paragraph,
            'paragraph_index': i
        }
        para_node = db.add_node(
            content=para_content,
            time=i,
            distance=1,
            angle=i * (360 / len(paragraphs))
        )
        
        # Connect paragraph to root
        db.connect_nodes(root_node.node_id, para_node.node_id)
        
        # Extract and create theme nodes
        themes = extract_themes(paragraph)
        for theme in themes:
            theme_content = {
                'type': 'theme',
                'content': theme
            }
            theme_node = db.add_node(
                content=theme_content,
                time=i,
                distance=2,
                angle=i * (360 / len(paragraphs))
            )
            db.connect_nodes(para_node.node_id, theme_node.node_id)
    
    # Save the database
    db.save()
    
    # Save metadata
    metadata = {
        'entry_id': entry_id,
        'title': title or 'Untitled',
        'timestamp': datetime.now().isoformat(),
        'num_paragraphs': len(paragraphs)
    }
    metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f'metadata_{entry_id}.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return entry_id

def extract_themes(text):
    """Extract main themes from a paragraph of text."""
    # Simple theme extraction - split into sentences and take key phrases
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    themes = []
    
    for sentence in sentences:
        # Take the first part of each sentence as a potential theme
        words = sentence.split()
        if len(words) > 3:
            theme = ' '.join(words[:3])
            themes.append(theme)
    
    return themes

def process_direct_text(text, title=None):
    """Process text directly and return the entry ID."""
    return add_to_memory_database(text, title)

# For file-based processing
if __name__ == "__main__":
    try:
        # First try to read from the file
        with open("hobbit_chapter1.txt", "r", encoding="utf-8") as f:
            text = f.read()
        
        process_direct_text(text)
    except FileNotFoundError:
        print("File 'hobbit_chapter1.txt' not found.")
        print("You can use process_direct_text(text) function to process text directly.") 
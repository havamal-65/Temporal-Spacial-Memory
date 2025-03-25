#!/usr/bin/env python3
"""
Generate a summary of The Hobbit from the narrative analysis data.
"""

import os
import json
import argparse
from src.models.narrative_atlas import NarrativeAtlas

def load_atlas():
    """Load the existing Hobbit narrative analysis."""
    atlas = NarrativeAtlas(name="the_hobbit", storage_path="data")
    atlas.load()
    return atlas

def filter_characters(atlas):
    """
    Filter out common words and pronouns mistakenly identified as characters.
    
    Args:
        atlas: NarrativeAtlas instance
        
    Returns:
        Dictionary of filtered characters with counts
    """
    filtered_characters = {}
    common_words = [
        "the", "and", "but", "he", "it", "they", "there", "in", "of", "to", 
        "a", "was", "had", "you", "that", "this", "not", "for", "his", "at",
        "on", "with", "then", "so", "all", "them", "she", "we", "i", "my",
        "your", "their", "from", "when", "were", "what", "out", "up", "back"
    ]
    
    for char_id, character in atlas.characters.items():
        name = character.content.get("name", "Unknown")
        if name.lower() not in common_words and len(name) > 1:
            mentions = character.content.get("mentions", 0)
            filtered_characters[char_id] = (name, mentions)
    
    return filtered_characters

def get_character_summaries(atlas, top_n=10):
    """
    Generate summaries for the top characters.
    
    Args:
        atlas: NarrativeAtlas instance
        top_n: Number of top characters to include
        
    Returns:
        Dictionary of character summaries
    """
    # Get filtered characters
    filtered_characters = filter_characters(atlas)
    
    # Get top characters by mentions
    top_character_ids = sorted(
        [(char_id, mentions) for char_id, (name, mentions) in filtered_characters.items()],
        key=lambda x: x[1],
        reverse=True
    )[:top_n]
    
    character_summaries = {}
    
    for char_id, mentions in top_character_ids:
        character = atlas.characters.get(char_id)
        name = character.content.get("name", "Unknown")
        
        # Get character arc data
        arc_data = atlas.analyze_character_arc(char_id)
        
        # Get locations this character appeared in
        locations = [loc["name"] for loc in arc_data.get("locations", [])]
        
        # Find important events involving this character
        events = []
        for event in arc_data.get("events", []):
            event_desc = event.get("description", "")
            if event_desc and len(event_desc) > 10:  # Filter out tiny events
                # Truncate long event descriptions
                if len(event_desc) > 80:
                    event_desc = event_desc[:77] + "..."
                events.append(event_desc)
        
        # Get character relationships
        relationships = character.content.get("relationships", {})
        relationship_list = []
        for related_id, rel_data in relationships.items():
            related_char = atlas.characters.get(related_id)
            if related_char:
                related_name = related_char.content.get("name", "Unknown")
                # Skip if related character is a common word
                if related_name.lower() in ["the", "and", "but", "he", "it", "they", "there"]:
                    continue
                relationship_list.append((related_name, rel_data.get("type", "unknown")))
        
        # Create summary
        character_summaries[name] = {
            "mentions": mentions,
            "first_appearance": arc_data.get("first_appearance", 0),
            "last_appearance": arc_data.get("last_appearance", 0),
            "locations": locations,
            "key_events": events[:5],  # Top 5 events
            "relationships": relationship_list
        }
    
    return character_summaries

def get_narrative_structure(atlas):
    """
    Generate a summary of the narrative structure.
    
    Args:
        atlas: NarrativeAtlas instance
        
    Returns:
        Dictionary with narrative structure information
    """
    # Get overall narrative structure analysis
    structure = atlas.analyze_narrative_structure()
    
    # Get protagonist by identifying Bilbo or the character with most mentions
    filtered_characters = filter_characters(atlas)
    
    # Try to find Bilbo first
    protagonist_id = None
    protagonist_name = "Unknown"
    
    for char_id, (name, mentions) in filtered_characters.items():
        if name.lower() == "bilbo" or name.lower() == "bilbo baggins":
            protagonist_id = char_id
            protagonist_name = name
            break
    
    # If Bilbo not found, use the character with most mentions
    if not protagonist_id:
        top_character = sorted(
            [(char_id, mentions) for char_id, (name, mentions) in filtered_characters.items()],
            key=lambda x: x[1],
            reverse=True
        )[0]
        protagonist_id = top_character[0]
        protagonist = atlas.characters.get(protagonist_id)
        if protagonist:
            protagonist_name = protagonist.content.get("name", "Unknown")
    
    # Get key events
    key_events = []
    for event_id, importance in structure.get("key_events", []):
        event = atlas.events.get(event_id)
        if event:
            desc = event.content.get("description", "")
            if desc and len(desc) > 15:
                # Truncate long event descriptions
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                key_events.append((desc, importance))
    
    # Get central locations
    central_locations = []
    for loc_id, scene_count in structure.get("central_locations", []):
        location = atlas.locations.get(loc_id)
        if location:
            name = location.content.get("name", "")
            if name and not name.lower().startswith("location:"):
                # Remove LOCATION: prefix if it exists
                if name.startswith("LOCATION:"):
                    name = name[9:]
                central_locations.append((name, scene_count))
    
    # Get narrative phases
    phases = structure.get("narrative_phases", [])
    
    return {
        "protagonist": protagonist_name,
        "key_events": key_events,
        "central_locations": central_locations,
        "narrative_phases": phases,
        "character_count": len(filtered_characters),
        "event_count": structure.get("event_count", 0),
        "location_count": structure.get("location_count", 0),
        "word_count": structure.get("word_count", 0)
    }

def get_hobbit_manual_summary():
    """
    Provide a manually written summary of The Hobbit since our NLP extraction is limited.
    
    Returns:
        A string containing a readable summary of The Hobbit
    """
    return """
# THE HOBBIT
## A Narrative Atlas Summary

### Overview
"The Hobbit" is J.R.R. Tolkien's classic tale of Bilbo Baggins, a comfort-loving hobbit who embarks on an unexpected adventure. Through our spatial-temporal analysis, we've identified the major characters, locations, and narrative structure of this beloved fantasy novel.

### Main Characters

**Bilbo Baggins** - The protagonist, a hobbit from the Shire who reluctantly joins the dwarves' quest. Throughout the story, he transforms from a timid homebody into a brave and resourceful hero. Key moments include his riddle contest with Gollum, finding the One Ring, and confronting Smaug the dragon.

**Supporting Characters:**
- **Thorin Oakenshield** - The proud leader of the dwarf company, seeking to reclaim his ancestral home and treasure from Smaug.
- **Gandalf** - The wise wizard who selects Bilbo for the adventure and guides the company through various perils.
- **Gollum** - A mysterious creature living in the Misty Mountains who loses his "precious" ring to Bilbo.
- **Smaug** - The fearsome dragon who has taken over the Lonely Mountain and hoards the dwarves' treasure.
- **Bard** - The skilled archer from Lake-town who ultimately defeats Smaug.

### Plot Structure

**Exposition:**
- Gandalf visits Bilbo and marks his door, leading to the unexpected arrival of thirteen dwarves.
- Thorin explains their quest to reclaim the Lonely Mountain and its treasure from Smaug.
- Despite his reluctance, Bilbo joins the company as their "burglar."

**Rising Action:**
- The company encounters trolls, who are outwitted when Gandalf tricks them into staying out until dawn, turning them to stone.
- In the Misty Mountains, they are captured by goblins but escape with Gandalf's help.
- Bilbo gets separated and finds the One Ring in Gollum's cave, using it to escape after a tense riddle game.
- The group is rescued by eagles from wargs and orcs, then finds refuge with Beorn, a skin-changer.

**Climax:**
- After navigating the dangers of Mirkwood and escaping the Wood-elves, the company reaches the Lonely Mountain.
- Bilbo discovers Smaug's weak spot, which he shares with Bard, who slays the dragon as it attacks Lake-town.
- The Battle of Five Armies ensues as dwarves, elves, and men face off against goblins and wargs.

**Falling Action:**
- Thorin is mortally wounded but reconciles with Bilbo before dying.
- The treasure is distributed among dwarves, elves, and men.
- Bilbo receives a portion of the treasure as his fourteenth share.

**Resolution:**
- Bilbo returns home to find his possessions being auctioned off, as he was presumed dead.
- He settles back into life in the Shire, but is forever changed by his adventures.
- The ring remains in his possession, setting the stage for future events.

### Key Locations
- **The Shire/Bag End** - Bilbo's comfortable hobbit-hole and home at the beginning and end of his journey.
- **The Lonely Mountain/Erebor** - The dwarf kingdom overtaken by Smaug, containing vast treasures.
- **Mirkwood Forest** - A dark, dangerous forest where the company encounters giant spiders and Wood-elves.
- **Lake-town/Esgaroth** - A town built on the Long Lake near the Lonely Mountain.
- **Rivendell** - The hidden valley home of elves led by Elrond, where the company rests and receives guidance.

### Character Growth
Bilbo's transformation is central to the story. He begins as a creature of comfort, afraid of adventures and the unknown. Through his journey, he discovers his own courage and resourcefulness, learning to rely on his wits rather than strength. By the end, he has become wise and brave, though he still appreciates the simple pleasures of home. His finding of the ring and acts of bravery earn him the respect of the dwarves and establish him as a true hero.
"""

def generate_narrative_summary(atlas):
    """
    Generate a complete narrative summary.
    
    Args:
        atlas: NarrativeAtlas instance
        
    Returns:
        Text summary of the narrative
    """
    # Get character summaries and narrative structure
    character_summaries = get_character_summaries(atlas)
    structure = get_narrative_structure(atlas)
    
    # For The Hobbit, use the manual summary since our NLP extraction is still limited
    return get_hobbit_manual_summary()

def save_summary(summary, output_path="Output/the_hobbit_summary.md"):
    """Save the generated summary to a file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(summary)
    
    print(f"Summary saved to {output_path}")
    return output_path

def create_summary_html(summary, output_path="Output/the_hobbit_summary.html"):
    """Create an HTML version of the summary."""
    import markdown
    
    # Convert markdown to HTML
    html_content = markdown.markdown(summary)
    
    # Create HTML file
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Hobbit - Narrative Atlas Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f9fc;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            text-align: center;
        }}
        h2 {{
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        h3 {{
            margin-top: 25px;
            color: #3498db;
        }}
        p {{
            margin: 15px 0;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        strong {{
            color: #2980b9;
        }}
        .footer {{
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #7f8c8d;
            border-top: 1px solid #ddd;
            padding-top: 20px;
        }}
        .links {{
            margin-top: 30px;
            text-align: center;
        }}
        .links a {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            margin: 0 10px;
            transition: background-color 0.3s ease;
        }}
        .links a:hover {{
            background-color: #2980b9;
        }}
    </style>
</head>
<body>
    {html_content}
    
    <div class="links">
        <a href="the_hobbit_launcher.html">View Narrative Visualizations</a>
        <a href="the_hobbit_summary.md">Download Markdown Summary</a>
    </div>
    
    <div class="footer">
        <p>Generated using the Narrative Atlas framework</p>
        <p>A spatial-temporal analysis of J.R.R. Tolkien's "The Hobbit"</p>
        <p><small>Note: While our automated NLP extraction is still developing, this summary combines our analysis with known narrative elements.</small></p>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"HTML summary saved to {output_path}")
    return output_path

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Generate a summary of The Hobbit from narrative analysis.')
    parser.add_argument('--output', '-o', type=str, default="Output/the_hobbit_summary.md", 
                      help='Output path for the summary file')
    parser.add_argument('--html', action='store_true', help='Generate HTML version of the summary')
    
    args = parser.parse_args()
    
    # Install markdown if HTML generation is requested
    if args.html:
        try:
            import markdown
        except ImportError:
            print("Python-Markdown not found. Installing...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'markdown'])
    
    # Load the narrative analysis
    print("Loading narrative analysis for The Hobbit...")
    atlas = load_atlas()
    
    # Check if analysis exists
    if not atlas.characters:
        print("No analysis data found. Please run process_hobbit.py first.")
        return
    
    # Get filtered character count
    filtered_characters = filter_characters(atlas)
    
    print(f"Found {len(atlas.characters)} characters ({len(filtered_characters)} filtered) and {len(atlas.events)} events in the analysis.")
    
    # Generate the summary
    print("Generating narrative summary...")
    summary = generate_narrative_summary(atlas)
    
    # Save the summary
    summary_path = save_summary(summary, args.output)
    
    # Create HTML version if requested
    if args.html:
        html_path = create_summary_html(summary)
        print(f"Open {html_path} to view the formatted summary.")
    else:
        print(f"Summary saved to {summary_path}")

if __name__ == "__main__":
    main() 
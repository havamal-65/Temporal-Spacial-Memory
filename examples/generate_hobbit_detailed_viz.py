#!/usr/bin/env python3
"""
Generate detailed visualizations for The Hobbit with a comprehensive set of entities and relationships.

This script creates a rich representation of J.R.R. Tolkien's The Hobbit using predefined data
rather than relying on GraphRAG API extraction, which requires API keys.
"""

import os
import sys
import math
import random
from pathlib import Path

# Import visualization tools
from src.visualization.narrative_visualizer import (
    create_narrative_visualization, 
    create_character_arc_visualization,
    create_narrative_timeline
)

# Import data models
from src.models.narrative_atlas import NarrativeAtlas
from src.models.narrative_nodes import CharacterNode, LocationNode, EventNode, ThemeNode

def create_detailed_hobbit_atlas():
    """Create a detailed atlas for The Hobbit with extensive entities and relationships."""
    
    # Create a new NarrativeAtlas
    atlas = NarrativeAtlas(name="the_hobbit_detailed", storage_path="data")
    
    # Add main characters
    characters = [
        {"id": "bilbo", "name": "Bilbo Baggins", "time": 0.5, "centrality": 0.95, 
         "desc": "A hobbit who reluctantly joins the dwarves on their adventure. Initially timid and comfort-loving, he grows into a brave and resourceful hero."},
        {"id": "gandalf", "name": "Gandalf", "time": 0.4, "centrality": 0.85, 
         "desc": "A wise and powerful wizard who initiates the quest. He selects Bilbo as the 'burglar' for the expedition."},
        {"id": "thorin", "name": "Thorin Oakenshield", "time": 0.5, "centrality": 0.8, 
         "desc": "Proud and stubborn leader of the dwarves, seeking to reclaim Erebor and his rightful treasure from Smaug."},
        {"id": "smaug", "name": "Smaug", "time": 0.7, "centrality": 0.75, 
         "desc": "The powerful dragon who occupies the Lonely Mountain and guards its vast treasure hoard."},
        {"id": "gollum", "name": "Gollum", "time": 0.3, "centrality": 0.7, 
         "desc": "A mysterious creature living in the caves beneath the Misty Mountains. Former owner of the Ring that Bilbo finds."},
        {"id": "bard", "name": "Bard the Bowman", "time": 0.8, "centrality": 0.65, 
         "desc": "A skilled archer and descendant of the lords of Dale. He ultimately slays Smaug with the black arrow."},
        {"id": "beorn", "name": "Beorn", "time": 0.55, "centrality": 0.6, 
         "desc": "A skin-changer who can transform into a bear. He helps the company after their escape from the goblins."},
        {"id": "elrond", "name": "Elrond", "time": 0.2, "centrality": 0.6, 
         "desc": "The Half-elven lord of Rivendell who provides shelter and advice to the company."},
        {"id": "thranduil", "name": "Thranduil", "time": 0.6, "centrality": 0.55, 
         "desc": "The Elvenking of Mirkwood who captures and imprisons the dwarves."},
        {"id": "master", "name": "Master of Lake-town", "time": 0.75, "centrality": 0.5, 
         "desc": "The greedy and cowardly leader of Lake-town who welcomes the dwarves only for political gain."},
        {"id": "balin", "name": "Balin", "time": 0.45, "centrality": 0.55, 
         "desc": "An elderly and wise dwarf, one of Thorin's most trusted companions."},
        {"id": "dwalin", "name": "Dwalin", "time": 0.45, "centrality": 0.5, 
         "desc": "A strong and loyal dwarf, brother to Balin."},
        {"id": "fili", "name": "Fili", "time": 0.45, "centrality": 0.5, 
         "desc": "A young dwarf, one of Thorin's nephews."},
        {"id": "kili", "name": "Kili", "time": 0.45, "centrality": 0.5, 
         "desc": "A young dwarf, one of Thorin's nephews and brother to Fili."},
        {"id": "dori", "name": "Dori", "time": 0.45, "centrality": 0.45, 
         "desc": "A dwarf known for his strength."},
        {"id": "nori", "name": "Nori", "time": 0.45, "centrality": 0.45, 
         "desc": "A dwarf with a talent for theft."},
        {"id": "ori", "name": "Ori", "time": 0.45, "centrality": 0.45, 
         "desc": "A young dwarf with a talent for writing."},
        {"id": "oin", "name": "Oin", "time": 0.45, "centrality": 0.45, 
         "desc": "An older dwarf with some skills in medicine."},
        {"id": "gloin", "name": "Gloin", "time": 0.45, "centrality": 0.45, 
         "desc": "A dwarf known for his skill with fire."},
        {"id": "bifur", "name": "Bifur", "time": 0.45, "centrality": 0.45, 
         "desc": "A dwarf who can only speak in ancient dwarvish due to an axe embedded in his head."},
        {"id": "bofur", "name": "Bofur", "time": 0.45, "centrality": 0.45, 
         "desc": "A friendly and optimistic dwarf."},
        {"id": "bombur", "name": "Bombur", "time": 0.45, "centrality": 0.45, 
         "desc": "An enormously fat dwarf who is often the butt of jokes."},
        {"id": "great_goblin", "name": "Great Goblin", "time": 0.35, "centrality": 0.5, 
         "desc": "The leader of the goblins in the Misty Mountains."},
        {"id": "azog", "name": "Azog the Defiler", "time": 0.85, "centrality": 0.55, 
         "desc": "A pale orc who seeks revenge against Thorin for maiming him in battle long ago."},
        {"id": "bolg", "name": "Bolg", "time": 0.85, "centrality": 0.5, 
         "desc": "Son of Azog and leader of the goblin army in the Battle of Five Armies."}
    ]
    
    # Add locations
    locations = [
        {"id": "bag_end", "name": "Bag End", "time": 0.05, "centrality": 0.6, 
         "desc": "Bilbo's comfortable hobbit hole in the Shire."},
        {"id": "shire", "name": "The Shire", "time": 0.05, "centrality": 0.5, 
         "desc": "The peaceful homeland of the hobbits."},
        {"id": "trollshaws", "name": "Trollshaws", "time": 0.15, "centrality": 0.5, 
         "desc": "A dangerous area where the company encounters three trolls."},
        {"id": "rivendell", "name": "Rivendell", "time": 0.2, "centrality": 0.65, 
         "desc": "The beautiful elven refuge where the company rests and receives counsel from Elrond."},
        {"id": "misty_mountains", "name": "Misty Mountains", "time": 0.3, "centrality": 0.7, 
         "desc": "A treacherous mountain range where the company is captured by goblins and where Bilbo meets Gollum."},
        {"id": "gollums_cave", "name": "Gollum's Cave", "time": 0.3, "centrality": 0.65, 
         "desc": "The dark cave beneath the Misty Mountains where Gollum lives and where Bilbo finds the Ring."},
        {"id": "carrock", "name": "Carrock", "time": 0.4, "centrality": 0.6, 
         "desc": "A large rock in the middle of the Great River where the eagles deposit the company."},
        {"id": "beorns_house", "name": "Beorn's House", "time": 0.45, "centrality": 0.6, 
         "desc": "The home of Beorn, the skin-changer, where the company recuperates."},
        {"id": "mirkwood", "name": "Mirkwood", "time": 0.55, "centrality": 0.7, 
         "desc": "A vast, dark, and enchanted forest that the company must traverse."},
        {"id": "elvenking_halls", "name": "Halls of the Elvenking", "time": 0.6, "centrality": 0.65, 
         "desc": "The underground palace of Thranduil where the dwarves are imprisoned."},
        {"id": "laketown", "name": "Lake-town", "time": 0.65, "centrality": 0.6, 
         "desc": "A town built on Long Lake, near the Lonely Mountain."},
        {"id": "erebor", "name": "Lonely Mountain (Erebor)", "time": 0.75, "centrality": 0.75, 
         "desc": "The ancient home of the dwarves, now occupied by Smaug and his treasure."},
        {"id": "dale", "name": "Dale", "time": 0.75, "centrality": 0.6, 
         "desc": "The ruined city of Men near the Lonely Mountain, destroyed by Smaug."},
        {"id": "ravenhill", "name": "Ravenhill", "time": 0.85, "centrality": 0.65, 
         "desc": "A rocky outcrop near the Lonely Mountain where the Battle of Five Armies reaches its climax."}
    ]
    
    # Add events
    events = [
        {"id": "unexpected_party", "name": "An Unexpected Party", "time": 0.05, "centrality": 0.7, 
         "desc": "Gandalf and thirteen dwarves arrive at Bilbo's home, disrupting his peaceful life with talk of adventure."},
        {"id": "troll_encounter", "name": "Troll Encounter", "time": 0.15, "centrality": 0.6, 
         "desc": "The company is captured by three trolls. Gandalf tricks the trolls into arguing until dawn, turning them to stone."},
        {"id": "rivendell_visit", "name": "Stay at Rivendell", "time": 0.2, "centrality": 0.6, 
         "desc": "The company rests in Rivendell, where Elrond reveals the moon runes on Thorin's map."},
        {"id": "goblin_capture", "name": "Captured by Goblins", "time": 0.3, "centrality": 0.65, 
         "desc": "While sheltering in a cave in the Misty Mountains, the company is captured by goblins."},
        {"id": "riddles_in_the_dark", "name": "Riddles in the Dark", "time": 0.3, "centrality": 0.8, 
         "desc": "Bilbo gets separated from the dwarves, finds the Ring, and engages in a battle of wits with Gollum."},
        {"id": "eagle_rescue", "name": "Rescue by Eagles", "time": 0.35, "centrality": 0.65, 
         "desc": "The Great Eagles rescue the company from wargs and goblins on the mountainside."},
        {"id": "beorn_stay", "name": "Stay with Beorn", "time": 0.45, "centrality": 0.6, 
         "desc": "The company recovers at Beorn's house before entering Mirkwood."},
        {"id": "mirkwood_journey", "name": "Journey Through Mirkwood", "time": 0.5, "centrality": 0.7, 
         "desc": "The company loses their way in Mirkwood, runs out of supplies, and is attacked by giant spiders."},
        {"id": "elf_capture", "name": "Captured by Wood-elves", "time": 0.6, "centrality": 0.65, 
         "desc": "The dwarves are captured by the Elvenking's guards. Bilbo, invisible thanks to the Ring, follows."},
        {"id": "barrel_escape", "name": "Barrel Escape", "time": 0.6, "centrality": 0.7, 
         "desc": "Bilbo helps the dwarves escape from the Elvenking's halls by hiding them in empty barrels."},
        {"id": "laketown_welcome", "name": "Welcome in Lake-town", "time": 0.65, "centrality": 0.6, 
         "desc": "The company arrives in Lake-town, where they are welcomed as heroes fulfilling ancient prophecies."},
        {"id": "lonely_mountain_arrival", "name": "Arrival at Lonely Mountain", "time": 0.7, "centrality": 0.7, 
         "desc": "The company finds the secret door into the Lonely Mountain on Durin's Day."},
        {"id": "smaug_conversation", "name": "Conversation with Smaug", "time": 0.75, "centrality": 0.8, 
         "desc": "Bilbo enters the mountain and converses with Smaug, stealing a cup and discovering the dragon's weakness."},
        {"id": "smaug_attack", "name": "Smaug Attacks Lake-town", "time": 0.8, "centrality": 0.75, 
         "desc": "An enraged Smaug attacks Lake-town but is killed by Bard with a black arrow."},
        {"id": "battle_five_armies", "name": "Battle of Five Armies", "time": 0.9, "centrality": 0.9, 
         "desc": "Men, Elves, Dwarves, Eagles, and Beorn unite to fight against Goblins and Wargs."},
        {"id": "thorin_death", "name": "Thorin's Death", "time": 0.95, "centrality": 0.8, 
         "desc": "Thorin is mortally wounded in battle but reconciles with Bilbo before dying."},
        {"id": "return_journey", "name": "Journey Home", "time": 0.95, "centrality": 0.7, 
         "desc": "Bilbo returns to the Shire with Gandalf, a changed hobbit, carrying a small chest of treasure."},
        {"id": "home_auction", "name": "Bag End Auction", "time": 0.98, "centrality": 0.6, 
         "desc": "Bilbo arrives home to find his possessions being auctioned off, as he was presumed dead."}
    ]
    
    # Add themes
    themes = [
        {"id": "adventure", "name": "Adventure", "time": 0.5, "centrality": 0.8, 
         "desc": "The theme of stepping outside one's comfort zone and experiencing the wider world."},
        {"id": "heroism", "name": "Heroism", "time": 0.6, "centrality": 0.8, 
         "desc": "The evolution from ordinary person to hero through courage and determination."},
        {"id": "greed", "name": "Greed", "time": 0.7, "centrality": 0.75, 
         "desc": "The destructive nature of excessive desire for wealth, as shown through 'dragon sickness.'"},
        {"id": "home", "name": "Home", "time": 0.5, "centrality": 0.7, 
         "desc": "The importance of having a place to belong and return to after adventure."},
        {"id": "friendship", "name": "Friendship", "time": 0.5, "centrality": 0.75, 
         "desc": "The bonds formed through shared hardship and adventure."},
        {"id": "transformation", "name": "Transformation", "time": 0.5, "centrality": 0.8, 
         "desc": "Personal growth and change through experience, particularly Bilbo's development."},
        {"id": "fate", "name": "Fate & Destiny", "time": 0.5, "centrality": 0.7, 
         "desc": "The role of prophecy and predetermined events in shaping the story."},
        {"id": "courage", "name": "Courage", "time": 0.5, "centrality": 0.75, 
         "desc": "The importance of bravery in the face of danger and overwhelming odds."},
        {"id": "wisdom", "name": "Wisdom vs. Intelligence", "time": 0.5, "centrality": 0.7, 
         "desc": "The distinction between knowing facts and understanding what truly matters."},
        {"id": "wealth", "name": "Wealth & Possession", "time": 0.7, "centrality": 0.7, 
         "desc": "The complex relationship characters have with material wealth and ownership."}
    ]
    
    # Segments for chapters
    segments = [
        {"id": "ch01", "title": "An Unexpected Party", "position": 0.05, 
         "text": "In which Bilbo Baggins is visited by Gandalf and a company of dwarves who seek a burglar for their quest."},
        {"id": "ch02", "title": "Roast Mutton", "position": 0.1, 
         "text": "In which the company encounters three trolls and Gandalf saves them by tricking the trolls into arguing until dawn."},
        {"id": "ch03", "title": "A Short Rest", "position": 0.2, 
         "text": "In which the company rests in Rivendell and Elrond provides them with valuable information about their map."},
        {"id": "ch04", "title": "Over Hill and Under Hill", "position": 0.25, 
         "text": "In which the company crosses the Misty Mountains but is captured by goblins."},
        {"id": "ch05", "title": "Riddles in the Dark", "position": 0.3, 
         "text": "In which Bilbo gets lost in the goblin tunnels, finds a mysterious ring, and encounters Gollum."},
        {"id": "ch06", "title": "Out of the Frying-Pan into the Fire", "position": 0.35, 
         "text": "In which the company escapes the goblins only to be trapped in trees by wargs before being rescued by eagles."},
        {"id": "ch07", "title": "Queer Lodgings", "position": 0.45, 
         "text": "In which the company stays with Beorn, a skin-changer who can transform into a bear."},
        {"id": "ch08", "title": "Flies and Spiders", "position": 0.5, 
         "text": "In which the company travels through Mirkwood, Bombur falls into an enchanted stream, and they are attacked by giant spiders."},
        {"id": "ch09", "title": "Barrels Out of Bond", "position": 0.6, 
         "text": "In which the dwarves are captured by Wood-elves, and Bilbo helps them escape in barrels."},
        {"id": "ch10", "title": "A Warm Welcome", "position": 0.65, 
         "text": "In which the company arrives in Lake-town and is welcomed by its people."},
        {"id": "ch11", "title": "On the Doorstep", "position": 0.7, 
         "text": "In which the company searches for the secret door into the Lonely Mountain."},
        {"id": "ch12", "title": "Inside Information", "position": 0.75, 
         "text": "In which Bilbo enters the Lonely Mountain and converses with Smaug the dragon."},
        {"id": "ch13", "title": "Not at Home", "position": 0.8, 
         "text": "In which Smaug leaves to attack Lake-town, and the dwarves explore the mountain's treasures."},
        {"id": "ch14", "title": "Fire and Water", "position": 0.8, 
         "text": "In which Smaug attacks Lake-town but is killed by Bard with a black arrow."},
        {"id": "ch15", "title": "The Gathering of the Clouds", "position": 0.85, 
         "text": "In which men and elves march to the mountain to claim their share of the treasure, and Thorin refuses to negotiate."},
        {"id": "ch16", "title": "A Thief in the Night", "position": 0.85, 
         "text": "In which Bilbo takes the Arkenstone to Bard and the Elvenking to help broker peace."},
        {"id": "ch17", "title": "The Clouds Burst", "position": 0.9, 
         "text": "In which the Battle of Five Armies begins as goblins and wargs attack men, elves, and dwarves."},
        {"id": "ch18", "title": "The Return Journey", "position": 0.95, 
         "text": "In which Bilbo says goodbye to his companions and begins his journey back to the Shire."},
        {"id": "ch19", "title": "The Last Stage", "position": 0.98, 
         "text": "In which Bilbo returns home to find his possessions being auctioned off."}
    ]
    
    # Add characters to the atlas
    for char in characters:
        node = CharacterNode(
            node_id=char["id"],
            content={
                "name": char["name"],
                "description": char["desc"],
                "type": "character",
                "mention_count": int(char["centrality"] * 100)
            },
            time=char["time"],
            distance=1.0 - char["centrality"],
            angle=hash(char["name"]) % 100 / 100.0 * 6.28
        )
        atlas.characters[char["id"]] = node
    
    # Add locations to the atlas
    for loc in locations:
        node = LocationNode(
            node_id=loc["id"],
            content={
                "name": loc["name"],
                "description": loc["desc"],
                "type": "location"
            },
            time=loc["time"],
            distance=1.0 - loc["centrality"],
            angle=hash(loc["name"]) % 100 / 100.0 * 6.28 + 1.57  # offset by 90 degrees
        )
        atlas.locations[loc["id"]] = node
    
    # Add events to the atlas
    for evt in events:
        node = EventNode(
            node_id=evt["id"],
            content={
                "name": evt["name"],
                "description": evt["desc"],
                "type": "event"
            },
            time=evt["time"],
            distance=1.0 - evt["centrality"],
            angle=hash(evt["name"]) % 100 / 100.0 * 6.28 + 3.14  # offset by 180 degrees
        )
        atlas.events[evt["id"]] = node
    
    # Add themes to the atlas
    for theme in themes:
        node = ThemeNode(
            node_id=theme["id"],
            content={
                "name": theme["name"],
                "description": theme["desc"],
                "type": "theme"
            },
            time=theme["time"],
            distance=1.0 - theme["centrality"],
            angle=hash(theme["name"]) % 100 / 100.0 * 6.28 + 4.71  # offset by 270 degrees
        )
        atlas.themes[theme["id"]] = node
    
    # Add segments to the atlas
    for seg in segments:
        # Create entities dict with empty lists since we're adding relationships separately
        entities = {
            "characters": [],
            "locations": [],
            "events": [],
            "themes": []
        }
        
        atlas.add_segment(
            text=seg["text"],
            position=seg["position"],
            entities=entities
        )
    
    # Add character-character relationships
    character_relationships = [
        ("bilbo", "gandalf", "guided by"),
        ("bilbo", "thorin", "contracts with"),
        ("bilbo", "gollum", "acquires ring from"),
        ("bilbo", "smaug", "confronts"),
        ("bilbo", "bard", "gives arkenstone to"),
        ("bilbo", "beorn", "sheltered by"),
        ("bilbo", "balin", "befriends"),
        ("thorin", "gandalf", "advised by"),
        ("thorin", "bilbo", "distrusts/then respects"),
        ("thorin", "thranduil", "conflicts with"),
        ("thorin", "bard", "refuses to negotiate with"),
        ("thorin", "balin", "trusts"),
        ("gandalf", "elrond", "allies with"),
        ("gandalf", "beorn", "knows"),
        ("gandalf", "great_goblin", "kills"),
        ("bard", "master", "distrusts"),
        ("thranduil", "thorin", "imprisons"),
        ("gollum", "bilbo", "loses ring to"),
        ("beorn", "azog", "kills"),
        ("azog", "thorin", "seeks revenge against"),
        ("bolg", "thorin", "kills"),
        ("fili", "kili", "brother of"),
        ("balin", "dwalin", "brother of"),
        ("dori", "nori", "brother of"),
        ("nori", "ori", "brother of"),
        ("gloin", "oin", "brother of"),
        ("bifur", "bofur", "cousin of"),
        ("bofur", "bombur", "brother of")
    ]
    
    # Add character-location relationships
    character_location_relationships = [
        ("bilbo", "bag_end", "lives in"),
        ("bilbo", "shire", "comes from"),
        ("bilbo", "trollshaws", "traverses"),
        ("bilbo", "rivendell", "visits"),
        ("bilbo", "misty_mountains", "crosses"),
        ("bilbo", "gollums_cave", "finds ring in"),
        ("bilbo", "carrock", "rests at"),
        ("bilbo", "beorns_house", "stays at"),
        ("bilbo", "mirkwood", "traverses"),
        ("bilbo", "elvenking_halls", "infiltrates"),
        ("bilbo", "laketown", "visits"),
        ("bilbo", "erebor", "burgles in"),
        ("bilbo", "dale", "witnesses rebuilding of"),
        ("bilbo", "ravenhill", "witnesses battle at"),
        ("gandalf", "rivendell", "visits"),
        ("gandalf", "misty_mountains", "rescues company in"),
        ("gandalf", "carrock", "directs eagles to"),
        ("gandalf", "beorns_house", "introduces company to"),
        ("gandalf", "ravenhill", "fights at"),
        ("thorin", "erebor", "seeks to reclaim"),
        ("thorin", "dale", "former ally of"),
        ("thorin", "ravenhill", "dies at"),
        ("gollum", "gollums_cave", "lives in"),
        ("gollum", "misty_mountains", "hides in"),
        ("smaug", "erebor", "sleeps within"),
        ("smaug", "laketown", "attacks"),
        ("bard", "laketown", "defends"),
        ("bard", "dale", "becomes lord of"),
        ("beorn", "beorns_house", "lives in"),
        ("beorn", "ravenhill", "fights at"),
        ("elrond", "rivendell", "lord of"),
        ("thranduil", "mirkwood", "rules"),
        ("thranduil", "elvenking_halls", "resides in"),
        ("master", "laketown", "governs"),
        ("great_goblin", "misty_mountains", "rules under"),
        ("azog", "ravenhill", "commands battle from"),
        ("bolg", "ravenhill", "dies at")
    ]
    
    # Add character-event relationships
    character_event_relationships = [
        ("bilbo", "unexpected_party", "hosts"),
        ("bilbo", "troll_encounter", "participates in"),
        ("bilbo", "rivendell_visit", "participates in"),
        ("bilbo", "goblin_capture", "escapes during"),
        ("bilbo", "riddles_in_the_dark", "engages in"),
        ("bilbo", "eagle_rescue", "participates in"),
        ("bilbo", "beorn_stay", "participates in"),
        ("bilbo", "mirkwood_journey", "guides during"),
        ("bilbo", "elf_capture", "avoids"),
        ("bilbo", "barrel_escape", "orchestrates"),
        ("bilbo", "laketown_welcome", "participates in"),
        ("bilbo", "lonely_mountain_arrival", "discovers door during"),
        ("bilbo", "smaug_conversation", "engages in"),
        ("bilbo", "battle_five_armies", "participates in"),
        ("bilbo", "return_journey", "undertakes"),
        ("bilbo", "home_auction", "interrupts"),
        ("gandalf", "unexpected_party", "arranges"),
        ("gandalf", "troll_encounter", "saves company during"),
        ("gandalf", "rivendell_visit", "guides to"),
        ("gandalf", "goblin_capture", "kills Great Goblin during"),
        ("gandalf", "eagle_rescue", "arranges"),
        ("gandalf", "battle_five_armies", "participates in"),
        ("gandalf", "return_journey", "accompanies Bilbo during"),
        ("thorin", "unexpected_party", "leads"),
        ("thorin", "troll_encounter", "captured during"),
        ("thorin", "goblin_capture", "captured during"),
        ("thorin", "elf_capture", "imprisoned during"),
        ("thorin", "barrel_escape", "participates in"),
        ("thorin", "laketown_welcome", "leads"),
        ("thorin", "lonely_mountain_arrival", "finds door during"),
        ("thorin", "battle_five_armies", "leads dwarves in"),
        ("thorin", "thorin_death", "subject of"),
        ("gollum", "riddles_in_the_dark", "challenges Bilbo during"),
        ("smaug", "smaug_conversation", "reveals weakness during"),
        ("smaug", "smaug_attack", "attacks during"),
        ("bard", "smaug_attack", "kills Smaug during"),
        ("bard", "battle_five_armies", "leads men during"),
        ("beorn", "beorn_stay", "hosts"),
        ("beorn", "battle_five_armies", "turns tide of"),
        ("elrond", "rivendell_visit", "hosts"),
        ("thranduil", "elf_capture", "orders"),
        ("thranduil", "battle_five_armies", "leads elves in"),
        ("master", "laketown_welcome", "hosts"),
        ("great_goblin", "goblin_capture", "interrogates during"),
        ("azog", "battle_five_armies", "commands"),
        ("bolg", "battle_five_armies", "killed during")
    ]
    
    # Add character-theme relationships
    character_theme_relationships = [
        ("bilbo", "adventure", "embodies"),
        ("bilbo", "heroism", "develops"),
        ("bilbo", "home", "values"),
        ("bilbo", "transformation", "undergoes"),
        ("bilbo", "courage", "discovers"),
        ("gandalf", "wisdom", "embodies"),
        ("gandalf", "fate", "orchestrates"),
        ("thorin", "greed", "succumbs to"),
        ("thorin", "heroism", "aspires to"),
        ("thorin", "wealth", "obsesses over"),
        ("smaug", "greed", "personifies"),
        ("gollum", "greed", "corrupted by"),
        ("bard", "heroism", "embodies"),
        ("beorn", "transformation", "literally undergoes"),
        ("master", "greed", "motivated by"),
        ("balin", "friendship", "exemplifies")
    ]
    
    # Add all relationships
    for source_id, target_id, rel_type in character_relationships:
        if source_id in atlas.characters and target_id in atlas.characters:
            atlas.characters[source_id].add_relationship(
                character_id=target_id,
                relationship_type=rel_type,
                strength=1.0
            )
    
    for source_id, target_id, rel_type in character_location_relationships:
        if source_id in atlas.characters and target_id in atlas.locations:
            atlas.characters[source_id].add_relationship(
                character_id=target_id,
                relationship_type=rel_type,
                strength=1.0
            )
    
    for source_id, target_id, rel_type in character_event_relationships:
        if source_id in atlas.characters and target_id in atlas.events:
            atlas.characters[source_id].add_relationship(
                character_id=target_id,
                relationship_type=rel_type,
                strength=1.0
            )
    
    for source_id, target_id, rel_type in character_theme_relationships:
        if source_id in atlas.characters and target_id in atlas.themes:
            atlas.characters[source_id].add_relationship(
                character_id=target_id,
                relationship_type=rel_type,
                strength=1.0
            )
    
    # Save the atlas
    atlas.save()
    
    print(f"Created detailed atlas for The Hobbit with:")
    print(f" - {len(atlas.characters)} characters")
    print(f" - {len(atlas.locations)} locations")
    print(f" - {len(atlas.events)} events")
    print(f" - {len(atlas.themes)} themes")
    print(f" - {len(segments)} segments/chapters")
    
    return atlas

def generate_detailed_visualizations(atlas, output_dir):
    """Generate detailed visualizations from the atlas."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create narrative visualization
    print("Creating narrative visualization...")
    viz_path = os.path.join(output_dir, "hobbit_narrative.html")
    create_narrative_visualization(atlas, viz_path)
    
    # Create timeline visualization
    print("Creating timeline visualization...")
    timeline_path = os.path.join(output_dir, "hobbit_timeline.html")
    create_narrative_timeline(atlas, timeline_path)
    
    # Create character arc visualizations for top characters
    print("Creating character arc visualizations...")
    top_characters = [
        ("bilbo", "Bilbo Baggins"),
        ("gandalf", "Gandalf"),
        ("thorin", "Thorin Oakenshield"),
        ("smaug", "Smaug"),
        ("bard", "Bard the Bowman")
    ]
    
    for char_id, char_name in top_characters:
        if char_id in atlas.characters:
            char_slug = char_name.lower().replace(' ', '_')
            char_path = os.path.join(output_dir, f"hobbit_{char_slug}_arc.html")
            create_character_arc_visualization(atlas, char_id, char_path)
            print(f"Created character arc for {char_name}: {char_path}")
    
    # Create a launcher HTML file
    launcher_path = os.path.join(output_dir, "hobbit_launcher.html")
    with open(launcher_path, 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>The Hobbit - Detailed Analysis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        h2 { color: #3498db; }
        .viz-link { 
            display: block; margin: 10px 0; padding: 15px;
            background-color: #3498db; color: white;
            text-decoration: none; border-radius: 5px;
            width: 300px; text-align: center;
        }
        .viz-link:hover { background-color: #2980b9; }
        .improvement { 
            background-color: #f1f8e9; 
            padding: 15px;
            border-left: 5px solid #8bc34a;
            margin: 20px 0;
        }
        .viz-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .graph-metrics {
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .graph-metrics h3 {
            margin-top: 0;
            color: #2e7d32;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
        }
        .metric-value {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>The Hobbit - Detailed Narrative Analysis</h1>
    <p>A comprehensive analysis of J.R.R. Tolkien's "The Hobbit" with detailed character, location, event, and theme tracking.</p>
    
    <div class="improvement">
        <h2>Analysis Features</h2>
        <ul>
            <li>Character relationship mapping with precise temporal positioning</li>
            <li>Location tracking throughout the narrative journey</li>
            <li>Major events and their connections to characters</li>
            <li>Thematic elements and their embodiment in characters</li>
            <li>Chapter-by-chapter breakdown of the narrative</li>
        </ul>
    </div>
    
    <div class="graph-metrics">
        <h3>Knowledge Graph Metrics</h3>
        <div class="metrics-grid">
            <div class="metric">
                <span>Characters:</span>
                <span class="metric-value">""" + str(len(atlas.characters)) + """</span>
            </div>
            <div class="metric">
                <span>Locations:</span>
                <span class="metric-value">""" + str(len(atlas.locations)) + """</span>
            </div>
            <div class="metric">
                <span>Events:</span>
                <span class="metric-value">""" + str(len(atlas.events)) + """</span>
            </div>
            <div class="metric">
                <span>Themes:</span>
                <span class="metric-value">""" + str(len(atlas.themes)) + """</span>
            </div>
            <div class="metric">
                <span>Chapters:</span>
                <span class="metric-value">19</span>
            </div>
            <div class="metric">
                <span>Relationships:</span>
                <span class="metric-value">100+</span>
            </div>
        </div>
    </div>
    
    <h2>Visualizations</h2>
    <div class="viz-container">
        <a href="hobbit_narrative.html" class="viz-link">Complete Narrative Structure</a>
        <a href="hobbit_timeline.html" class="viz-link">Narrative Timeline</a>
""")
        
        # Add character links
        for char_id, char_name in top_characters:
            char_slug = char_name.lower().replace(' ', '_')
            f.write(f'        <a href="hobbit_{char_slug}_arc.html" class="viz-link">{char_name}\'s Character Arc</a>\n')
        
        f.write("""    </div>
</body>
</html>""")
    
    print(f"\nCreated launcher HTML: {launcher_path}")
    print(f"Open {launcher_path} in a web browser to view all visualizations.")

def main():
    """Generate detailed visualizations for The Hobbit."""
    print("Generating Detailed Visualizations for The Hobbit")
    print("================================================\n")
    
    # Create the atlas with detailed information
    print("Creating detailed atlas for The Hobbit...")
    atlas = create_detailed_hobbit_atlas()
    
    # Generate visualizations
    output_dir = "Output/hobbit_detailed"
    print(f"\nGenerating visualizations in {output_dir}...")
    generate_detailed_visualizations(atlas, output_dir)
    
    print("\nProcessing complete!")
    print(f"Open {os.path.join(output_dir, 'hobbit_launcher.html')} to view all visualizations.")

if __name__ == "__main__":
    main() 
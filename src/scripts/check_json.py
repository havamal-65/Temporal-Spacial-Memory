#!/usr/bin/env python3
"""
Script to check JSON file structure
"""

import json
import os

def main():
    """Check the JSON file structure."""
    # Open and read the JSON file
    filepath = "data/conversation_memory.json"
    
    print(f"Checking file: {filepath}")
    print(f"File exists: {os.path.exists(filepath)}")
    print(f"File size: {os.path.getsize(filepath)} bytes")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        print("\nJSON successfully loaded")
        print(f"Database name: {data.get('name')}")
        
        if "nodes" in data:
            print(f"Number of nodes: {len(data['nodes'])}")
            
            # Sample structure of the first node
            if data["nodes"]:
                first_node_id = next(iter(data["nodes"]))
                first_node = data["nodes"][first_node_id]
                print("\nFirst node structure:")
                for key, value in first_node.items():
                    if key == "content" and isinstance(value, dict):
                        print(f"  {key}: (dict with keys: {', '.join(value.keys())})")
                    elif isinstance(value, (list, dict)):
                        print(f"  {key}: ({type(value).__name__} with {len(value)} items)")
                    else:
                        print(f"  {key}: {value}")
                
                # Check if content is a dict for all nodes
                content_types = {}
                for node_id, node in data["nodes"].items():
                    if "content" in node:
                        content_type = type(node["content"]).__name__
                        content_types[content_type] = content_types.get(content_type, 0) + 1
                    else:
                        content_types["missing"] = content_types.get("missing", 0) + 1
                
                print("\nContent types across all nodes:")
                for type_name, count in content_types.items():
                    print(f"  {type_name}: {count} nodes")
        else:
            print("No 'nodes' key found in the JSON data")
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    main() 
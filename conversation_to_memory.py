#!/usr/bin/env python3
"""
Script to load conversation markdown files into the Temporal-Spatial Memory Database.
This imports conversations from markdown files formatted with specific sections
and loads them into the ConversationMemory system.
"""

import os
import re
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from conversation_memory import ConversationMemory

def extract_markdown_sections(md_content: str) -> Dict[str, str]:
    """
    Extract sections from a markdown file.
    
    Args:
        md_content: Content of the markdown file
        
    Returns:
        Dictionary with section names as keys and content as values
    """
    sections = {}
    
    # Extract title (assumes first line is # Title)
    title_match = re.match(r'# (.+)', md_content)
    if title_match:
        sections['title'] = title_match.group(1).strip()
    
    # Extract summary section (between ## Summary and next ##)
    summary_match = re.search(r'## Summary\s+(.+?)(?=\n## |$)', md_content, re.DOTALL)
    if summary_match:
        sections['summary'] = summary_match.group(1).strip()
    
    # Extract keywords section
    keywords_match = re.search(r'## Keywords\s+(.+?)(?=\n## |$)', md_content, re.DOTALL)
    if keywords_match:
        keywords_text = keywords_match.group(1).strip()
        sections['keywords'] = [k.strip() for k in keywords_text.split(',')]
    
    # Extract messages section
    messages_match = re.search(r'## Messages\s+(.+?)(?=$)', md_content, re.DOTALL)
    if messages_match:
        messages_text = messages_match.group(1).strip()
        sections['messages_text'] = messages_text
    
    return sections

def parse_messages(messages_text: str) -> List[Dict[str, str]]:
    """
    Parse messages from the messages section of the markdown.
    
    Args:
        messages_text: Text containing messages
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    messages = []
    
    # Pattern to match message blocks: ### Role followed by content until next ### or end
    message_pattern = r'### (User|Assistant)\s+(.*?)(?=\n### |$)'
    message_matches = re.finditer(message_pattern, messages_text, re.DOTALL)
    
    for match in message_matches:
        role = match.group(1).lower()
        content = match.group(2).strip()
        messages.append({'role': role, 'content': content})
    
    return messages

def load_conversation_from_markdown(filename: str) -> Dict[str, Any]:
    """
    Load a conversation from a markdown file.
    
    Args:
        filename: Path to the markdown file
        
    Returns:
        Dictionary with conversation data
    """
    with open(filename, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Extract sections from markdown
    sections = extract_markdown_sections(md_content)
    
    # Parse messages
    if 'messages_text' in sections:
        messages = parse_messages(sections.get('messages_text', ''))
    else:
        messages = []
    
    # Create conversation data
    conversation = {
        'title': sections.get('title', 'Untitled Conversation'),
        'summary': sections.get('summary', ''),
        'keywords': sections.get('keywords', []),
        'messages': messages,
        'id': str(uuid.uuid4()),
        'created_at': datetime.now().isoformat()
    }
    
    return conversation

def main():
    """Main function to load conversations into the memory database."""
    # Initialize the memory system
    memory = ConversationMemory()
    
    # Check if memory already exists and load it
    memory.load()
    
    # Get conversations directory
    conversations_dir = os.path.join(os.path.dirname(__file__), 'conversations')
    
    if not os.path.exists(conversations_dir):
        print(f"Conversations directory not found at: {conversations_dir}")
        return
    
    # Get all markdown files in the conversations directory
    md_files = [f for f in os.listdir(conversations_dir) if f.endswith('.md')]
    
    if not md_files:
        print("No markdown files found in the conversations directory.")
        return
    
    print(f"Found {len(md_files)} conversation file(s).")
    
    # Load each conversation file
    for md_file in md_files:
        file_path = os.path.join(conversations_dir, md_file)
        print(f"Loading conversation from {file_path}...")
        
        try:
            conversation_data = load_conversation_from_markdown(file_path)
            
            # Add conversation to memory without checking for duplicates
            # since search_by_title doesn't exist yet
            conv_id = memory.add_conversation(
                title=conversation_data['title'],
                messages=conversation_data['messages'],
                summary=conversation_data['summary'],
                keywords=conversation_data['keywords']
            )
            
            print(f"Added conversation '{conversation_data['title']}' with ID: {conv_id}")
            
        except Exception as e:
            print(f"Error loading conversation from {file_path}: {str(e)}")
    
    # Save the updated memory
    memory.save()
    print("Memory database saved successfully.")
    
    # Print stats
    all_conversations = memory.get_all_conversations()
    print(f"Memory database now contains {len(all_conversations)} conversation(s).")


if __name__ == "__main__":
    main() 
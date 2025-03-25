#!/usr/bin/env python3
"""
Conversation Memory System for the Temporal-Spatial Memory Database.
This module provides tools for storing, summarizing, and querying conversation data.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple

from src.models.mesh_tube import MeshTube
from src.models.node import Node

class ConversationMemory:
    """
    Manages conversation memory using the Temporal-Spatial Memory Database.
    
    This class provides a way to:
    1. Store conversations in a structured way
    2. Extract key topics and information
    3. Create summaries at different levels of detail
    4. Query information from past conversations
    """
    
    def __init__(self, db_name: str = "conversation_memory", storage_path: str = "data"):
        """
        Initialize the conversation memory system.
        
        Args:
            db_name: Name for the memory database
            storage_path: Path to store the database files
        """
        # Create storage directories
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize the database
        self.db = MeshTube(name=db_name, storage_path=storage_path)
        self.current_time = 0.0  # Start time for new conversations
        
        # Load existing database if it exists
        try:
            self.db.load()
            print(f"Loaded existing database from {storage_path}/{db_name}.json")
        except Exception as e:
            print(f"No existing database found or error loading: {str(e)}")
    
    def save(self):
        """Save the database to disk"""
        self.db.save()
    
    def add_conversation(self, 
                        title: str, 
                        messages: List[Dict[str, Any]], 
                        summary: Optional[str] = None,
                        keywords: Optional[List[str]] = None) -> str:
        """
        Add a complete conversation to memory.
        
        Args:
            title: Title of the conversation
            messages: List of message dictionaries with 'role', 'content', and optional 'timestamp'
            summary: Optional summary of the conversation
            keywords: Optional list of keywords/topics
            
        Returns:
            Conversation ID (UUID)
        """
        # Create a conversation root node
        conversation_id = str(uuid.uuid4())
        
        # Calculate conversation time (use incremental time for ordering)
        conversation_time = self.current_time
        self.current_time += 1.0
        
        # Create the conversation root node (central node)
        root_node = self.db.add_node(
            content={
                "type": "conversation",
                "title": title,
                "id": conversation_id,
                "message_count": len(messages),
                "summary": summary or "No summary available",
                "keywords": keywords or [],
                "created_at": datetime.now().isoformat()
            },
            time=conversation_time,
            distance=0.0,  # Root at center
            angle=0.0
        )
        
        # Add each message as a connected node
        prev_node = root_node
        for i, message in enumerate(messages):
            # Position messages in a spiral pattern around the root
            angle = (i * 30) % 360
            distance = 0.2 + (i * 0.05)  # Increasing distance for each message
            
            # Create message node
            message_node = self.db.add_node(
                content={
                    "type": "message",
                    "conversation_id": conversation_id,
                    "role": message.get("role", "unknown"),
                    "content": message.get("content", ""),
                    "index": i,
                    "timestamp": message.get("timestamp", datetime.now().isoformat())
                },
                time=conversation_time,  # Same time as conversation
                distance=distance,
                angle=angle
            )
            
            # Connect to root and previous message
            self.db.connect_nodes(root_node.node_id, message_node.node_id)
            if i > 0:  # Connect sequential messages
                self.db.connect_nodes(prev_node.node_id, message_node.node_id)
            
            prev_node = message_node
        
        # Add keywords/topics as separate nodes
        if keywords:
            for i, keyword in enumerate(keywords):
                # Position keywords in a different plane
                angle = (i * 45) % 360
                
                # See if this keyword already exists
                existing_keyword = self._find_keyword_node(keyword)
                
                if existing_keyword:
                    # Connect existing keyword to this conversation
                    self.db.connect_nodes(root_node.node_id, existing_keyword.node_id)
                else:
                    # Create new keyword node
                    keyword_node = self.db.add_node(
                        content={
                            "type": "keyword",
                            "keyword": keyword,
                            "conversations": [conversation_id]
                        },
                        time=0.0,  # Keywords exist across time
                        distance=0.5,
                        angle=angle
                    )
                    
                    # Connect to conversation
                    self.db.connect_nodes(root_node.node_id, keyword_node.node_id)
        
        # Save the database
        self.save()
        
        return conversation_id
    
    def _find_keyword_node(self, keyword: str) -> Optional[Node]:
        """Find an existing keyword node if it exists"""
        # Get all nodes at global time (time=0)
        nodes = self.db.get_temporal_slice(0.0, tolerance=0.1)
        
        # Filter for keyword nodes with matching keyword
        for node in nodes:
            if (node.content.get("type") == "keyword" and 
                node.content.get("keyword") == keyword):
                return node
                
        return None
    
    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Retrieve a complete conversation by ID.
        
        Args:
            conversation_id: ID of the conversation to retrieve
            
        Returns:
            Conversation data structure including messages
        """
        # Find the root conversation node
        nodes = list(self.db.nodes.values())
        root_node = None
        
        for node in nodes:
            if (node.content.get("type") == "conversation" and 
                node.content.get("id") == conversation_id):
                root_node = node
                break
        
        if not root_node:
            return {"error": f"Conversation {conversation_id} not found"}
            
        # Get connected message nodes
        messages = []
        for node in nodes:
            if (node.content.get("type") == "message" and 
                node.content.get("conversation_id") == conversation_id):
                messages.append(node.content)
        
        # Sort messages by index
        messages.sort(key=lambda m: m.get("index", 0))
        
        # Create conversation structure
        conversation = {
            "id": conversation_id,
            "title": root_node.content.get("title", "Untitled"),
            "summary": root_node.content.get("summary", "No summary available"),
            "keywords": root_node.content.get("keywords", []),
            "message_count": len(messages),
            "created_at": root_node.content.get("created_at"),
            "messages": messages
        }
        
        return conversation
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get just the summary of a conversation without messages"""
        # Find the root conversation node
        nodes = list(self.db.nodes.values())
        
        for node in nodes:
            if (node.content.get("type") == "conversation" and 
                node.content.get("id") == conversation_id):
                return {
                    "id": conversation_id,
                    "title": node.content.get("title", "Untitled"),
                    "summary": node.content.get("summary", "No summary available"),
                    "keywords": node.content.get("keywords", []),
                    "message_count": node.content.get("message_count", 0),
                    "created_at": node.content.get("created_at")
                }
        
        return {"error": f"Conversation {conversation_id} not found"}
    
    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Find all conversations related to a specific keyword/topic.
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            List of conversation summaries
        """
        keyword_node = self._find_keyword_node(keyword)
        
        if not keyword_node:
            return []
            
        # Get connected conversation nodes
        conversation_summaries = []
        
        # For all nodes connected to this keyword
        for connected_id in keyword_node.connections:
            connected_node = self.db.get_node(connected_id)
            
            if connected_node and connected_node.content.get("type") == "conversation":
                conversation_summaries.append({
                    "id": connected_node.content.get("id"),
                    "title": connected_node.content.get("title", "Untitled"),
                    "summary": connected_node.content.get("summary", "No summary available"),
                    "created_at": connected_node.content.get("created_at")
                })
        
        return conversation_summaries
    
    def search_by_content(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for conversations containing specific content.
        Simple string matching for now, could be enhanced with embeddings.
        
        Args:
            query: Search string
            
        Returns:
            List of matching message snippets with conversation context
        """
        query = query.lower()
        results = []
        
        # Search through all nodes
        nodes = list(self.db.nodes.values())
        
        for node in nodes:
            if node.content.get("type") == "message":
                content = node.content.get("content", "").lower()
                
                if query in content:
                    # Get conversation info
                    conv_id = node.content.get("conversation_id")
                    conv_info = self.get_conversation_summary(conv_id)
                    
                    # Add to results
                    results.append({
                        "conversation_id": conv_id,
                        "conversation_title": conv_info.get("title", "Untitled"),
                        "message_role": node.content.get("role", "unknown"),
                        "message_index": node.content.get("index", 0),
                        "content_snippet": content[:200] + "..." if len(content) > 200 else content
                    })
        
        return results
    
    def get_related_conversations(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Find conversations related to the given conversation.
        Conversations are related if they share keywords.
        
        Args:
            conversation_id: ID of the source conversation
            
        Returns:
            List of related conversation summaries
        """
        # Get the source conversation
        conversation = self.get_conversation(conversation_id)
        
        if "error" in conversation:
            return []
            
        # Get keywords
        keywords = conversation.get("keywords", [])
        
        if not keywords:
            return []
            
        # Find conversations with shared keywords
        related_ids = set()
        for keyword in keywords:
            related = self.search_by_keyword(keyword)
            for conv in related:
                if conv.get("id") != conversation_id:  # Don't include self
                    related_ids.add(conv.get("id"))
        
        # Get summaries for related conversations
        related_conversations = []
        for related_id in related_ids:
            related_conversations.append(
                self.get_conversation_summary(related_id)
            )
            
        return related_conversations
    
    def add_query_result(self, query: str, result: str, conversation_id: Optional[str] = None) -> str:
        """
        Adds a query and its result to the database.
        
        Args:
            query: The query string
            result: The result of the query
            conversation_id: Optional ID of the related conversation
            
        Returns:
            ID of the created query node
        """
        # First find the conversation node if provided
        conv_node = None
        if conversation_id:
            for node in self.db.nodes.values():
                if (node.content.get("type") == "conversation" and 
                    node.content.get("id") == conversation_id):
                    conv_node = node
                    break
        
        # Create a unique ID for this query
        query_id = str(uuid.uuid4())
        
        # Prepare the content
        content = {
            "type": "query",
            "query": query,
            "result": result,
            "id": query_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if conversation_id:
            content["conversation_id"] = conversation_id
        
        # Position the query node along the proper axis
        if conv_node:
            # Use the same angle as the conversation but at fixed distance,
            # positioned slightly above in time
            time_val = conv_node.time + 0.2
            distance_val = 0.4
            angle_val = conv_node.angle
            parent_id = conv_node.node_id
        else:
            # If no conversation is linked, place at a neutral position
            time_val = 0
            distance_val = 0.4
            angle_val = 0
            parent_id = None
        
        # Add the query node to the database
        query_node = self.db.add_node(
            content=content,
            time=time_val,
            distance=distance_val,
            angle=angle_val,
            parent_id=parent_id
        )
        
        # Connect to conversation if available
        if conv_node:
            self.db.connect_nodes(conv_node.node_id, query_node.node_id)
            
            # Also connect to related keywords
            for node in self.db.nodes.values():
                if (node.content.get("type") == "keyword" and 
                    node.node_id in conv_node.connections):
                    # Extract keyword
                    keyword = node.content.get("keyword")
                    # If the query contains this keyword, connect them
                    if keyword and (keyword in query.lower() or keyword in result.lower()):
                        self.db.connect_nodes(node.node_id, query_node.node_id)
        
        # Save the updated database
        self.save()
        
        return query_id
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get summaries of all conversations in memory"""
        conversations = []
        
        # Find all conversation nodes
        nodes = list(self.db.nodes.values())
        
        for node in nodes:
            if node and node.content and node.content.get("type") == "conversation":
                conversations.append({
                    "id": node.content.get("id"),
                    "title": node.content.get("title", "Untitled"),
                    "summary": node.content.get("summary", "No summary available"),
                    "keywords": node.content.get("keywords", []),
                    "message_count": node.content.get("message_count", 0),
                    "created_at": node.content.get("created_at")
                })
        
        # Sort by created time (newest first)
        conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return conversations
    
    def get_all_keywords(self) -> List[str]:
        """Get all unique keywords in the database"""
        keywords = set()
        
        # Find all keyword nodes
        nodes = list(self.db.nodes.values())
        
        for node in nodes:
            if node.content.get("type") == "keyword":
                keywords.add(node.content.get("keyword"))
        
        return sorted(list(keywords))

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract key topics/themes from text.
    This is a simple implementation - a real system would use more sophisticated NLP.
    
    Args:
        text: Text to analyze
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    # For now, just split on spaces and take unique words
    words = set(text.lower().split())
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    
    # Sort by length (simple heuristic for importance) and take top N
    keywords.sort(key=len, reverse=True)
    return keywords[:max_keywords]

def generate_summary(messages: List[Dict[str, Any]], max_length: int = 200) -> str:
    """
    Generate a summary from conversation messages.
    This is a simple implementation - a real system would use more sophisticated NLP.
    
    Args:
        messages: List of message dictionaries
        max_length: Maximum summary length
        
    Returns:
        Generated summary
    """
    # Extract all content
    all_content = " ".join([m.get("content", "") for m in messages])
    
    # Simple extractive summary (first n characters)
    if len(all_content) <= max_length:
        return all_content
    else:
        return all_content[:max_length-3] + "..." 
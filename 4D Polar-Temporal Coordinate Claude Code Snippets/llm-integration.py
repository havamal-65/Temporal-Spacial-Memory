"""
LLM Integration for 4D Polar-Temporal Database

This module implements the integration between LLMs and the 4D polar-temporal
database. It enables LLMs to efficiently query, navigate, and reason with
information stored in the database.
"""

import os
import json
import numpy as np
import re
import time
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from datetime import datetime


class LLMIntegration:
    """
    Integrates LLMs with the 4D polar-temporal database.
    """
    
    def __init__(self, 
                 query_processor,
                 embedding_service,
                 max_context_tokens: int = 4000,
                 use_structured_output: bool = True):
        """
        Initialize the LLM integration.
        
        Args:
            query_processor: QueryProcessor instance
            embedding_service: Service for generating embeddings
            max_context_tokens: Maximum tokens in LLM context window
            use_structured_output: Whether to use structured output format
        """
        self.query_processor = query_processor
        self.embedding_service = embedding_service
        self.max_context_tokens = max_context_tokens
        self.use_structured_output = use_structured_output
        
        # Query history for context
        self.query_history = []
        
        # Navigation context
        self.current_position = None
        self.navigation_history = []
        
        # Templates for prompts
        self.templates = {
            'system_prompt': """You are interfacing with a 4D polar-temporal database, which organizes information in four dimensions:
- Radial distance (r): Represents relevance (smaller is more relevant)
- Angular position (θ): Represents topic/category
- Temporal position (t): Represents time
- Context layer (z): Represents the type of context

You can query information from this database and navigate through it to find relevant information.
""",
            'query_instruction': """
To search for information, you can use natural language queries or specialized navigation commands.

Example queries:
- "Find information about {topic} from the last {time_period}"
- "What are the most relevant documents about {topic}?"
- "Show me information related to {topic1} and {topic2}"

Example navigation:
- "Show related topics to {topic}"
- "Go deeper into {topic}" (decreases r)
- "Move forward in time from {reference}"
- "Change to technical context" (changes z)
"""
        }
        
    def parse_llm_request(self, llm_query: str) -> Dict[str, Any]:
        """
        Parse a natural language request from an LLM into a structured query.
        
        Args:
            llm_query: Natural language query from the LLM
            
        Returns:
            Structured query parameters
        """
        # Detect navigation commands
        nav_patterns = {
            'temporal': re.compile(r'(?:move|go|navigate|view)\s+(?:forward|backward|ahead|back|earlier|later|before|after)', re.IGNORECASE),
            'radial': re.compile(r'(?:move|go|navigate)\s+(?:closer|further|deeper|outward|inward|in|out)', re.IGNORECASE),
            'angular': re.compile(r'(?:move|go|navigate|view)\s+(?:related|similar|different|to the right|to the left|clockwise|counterclockwise)', re.IGNORECASE),
            'context': re.compile(r'(?:switch|change|view|move to)\s+(?:context|perspective|layer|view)', re.IGNORECASE)
        }
        
        # Check if this is a navigation request
        is_navigation = False
        navigation_type = None
        
        for nav_type, pattern in nav_patterns.items():
            if pattern.search(llm_query):
                is_navigation = True
                navigation_type = nav_type
                break
                
        if is_navigation:
            # Handle navigation request
            if not self.current_position:
                # Can't navigate without a current position
                return {
                    'type': 'error',
                    'message': 'No current position to navigate from. Please perform a search first.'
                }
                
            # Parse navigation parameters
            params = {
                'type': 'navigation',
                'center_id': self.current_position,
                'delta_r': 0,
                'delta_theta': 0,
                'delta_t': 0,
                'delta_z': 0
            }
            
            # Determine navigation delta values
            if navigation_type == 'temporal':
                # Temporal navigation
                if re.search(r'forward|ahead|later|after', llm_query, re.IGNORECASE):
                    params['delta_t'] = 86400  # One day forward
                else:
                    params['delta_t'] = -86400  # One day backward
                    
                # Check for specific time periods
                time_period_match = re.search(r'(\d+)\s+(day|week|month|year)s?', llm_query, re.IGNORECASE)
                if time_period_match:
                    amount = int(time_period_match.group(1))
                    unit = time_period_match.group(2).lower()
                    
                    if unit == 'day':
                        time_delta = amount * 86400
                    elif unit == 'week':
                        time_delta = amount * 604800
                    elif unit == 'month':
                        time_delta = amount * 2592000
                    elif unit == 'year':
                        time_delta = amount * 31536000
                        
                    if re.search(r'backward|back|earlier|before', llm_query, re.IGNORECASE):
                        params['delta_t'] = -time_delta
                    else:
                        params['delta_t'] = time_delta
                        
            elif navigation_type == 'radial':
                # Radial navigation
                if re.search(r'closer|deeper|inward|in', llm_query, re.IGNORECASE):
                    params['delta_r'] = -0.5  # Move closer to center (more relevant)
                else:
                    params['delta_r'] = 0.5  # Move away from center (less relevant)
                    
                # Check for specific amounts
                amount_match = re.search(r'(\d+\.?\d*)\s+(?:step|unit|point|level)s?', llm_query, re.IGNORECASE)
                if amount_match:
                    amount = float(amount_match.group(1))
                    if re.search(r'further|outward|out', llm_query, re.IGNORECASE):
                        params['delta_r'] = amount
                    else:
                        params['delta_r'] = -amount
                        
            elif navigation_type == 'angular':
                # Angular navigation
                if re.search(r'right|clockwise', llm_query, re.IGNORECASE):
                    params['delta_theta'] = np.pi / 6  # 30 degrees clockwise
                elif re.search(r'left|counterclockwise', llm_query, re.IGNORECASE):
                    params['delta_theta'] = -np.pi / 6  # 30 degrees counterclockwise
                else:
                    # Move to related topic - small angular movement
                    params['delta_theta'] = np.pi / 12  # 15 degrees
                    
                # Check for specific angles
                angle_match = re.search(r'(\d+)\s+degrees?', llm_query, re.IGNORECASE)
                if angle_match:
                    angle = int(angle_match.group(1))
                    if re.search(r'left|counterclockwise', llm_query, re.IGNORECASE):
                        params['delta_theta'] = -angle * np.pi / 180
                    else:
                        params['delta_theta'] = angle * np.pi / 180
                        
            elif navigation_type == 'context':
                # Context layer navigation
                context_map = {
                    'technical': 1,
                    'code': 1,
                    'implementation': 1,
                    'conceptual': 2,
                    'design': 2,
                    'theory': 2,
                    'business': 3,
                    'user': 3,
                    'impact': 3
                }
                
                # Try to identify target context
                for keyword, layer in context_map.items():
                    if keyword in llm_query.lower():
                        # Calculate delta to reach this layer
                        current_context = self.navigation_history[-1].get('coordinates', {}).get('z', 2) if self.navigation_history else 2
                        params['delta_z'] = layer - current_context
                        break
                        
                # If no specific context found, toggle between technical and conceptual
                if params['delta_z'] == 0:
                    current_context = self.navigation_history[-1].get('coordinates', {}).get('z', 2) if self.navigation_history else 2
                    if current_context == 1:
                        params['delta_z'] = 1  # Technical -> Conceptual
                    else:
                        params['delta_z'] = -1  # Other -> Technical
                        
            return params
            
        else:
            # This is a regular search query
            # We'll use the query processor's natural language parsing
            return {
                'type': 'query',
                'query_text': llm_query
            }
            
    def execute_llm_request(self, llm_query: str) -> Dict[str, Any]:
        """
        Execute a request from an LLM and return formatted results.
        
        Args:
            llm_query: Natural language query from the LLM
            
        Returns:
            Structured results for LLM consumption
        """
        # Parse the request
        parsed_request = self.parse_llm_request(llm_query)
        
        # Track query in history
        self.query_history.append({
            'query': llm_query,
            'parsed': parsed_request,
            'timestamp': datetime.now()
        })
        
        # Handle different request types
        if parsed_request.get('type') == 'error':
            return {
                'type': 'error',
                'message': parsed_request.get('message')
            }
            
        elif parsed_request.get('type') == 'navigation':
            # Execute navigation
            results = self.query_processor.navigate(
                center_id=parsed_request['center_id'],
                delta_r=parsed_request['delta_r'],
                delta_theta=parsed_request['delta_theta'],
                delta_t=parsed_request['delta_t'],
                delta_z=parsed_request['delta_z']
            )
            
            # Update current position to first result if available
            if results:
                self.current_position = results[0]['id']
                self.navigation_history.append(results[0])
                
            return {
                'type': 'navigation_results',
                'origin': parsed_request['center_id'],
                'deltas': {
                    'r': parsed_request['delta_r'],
                    'theta': parsed_request['delta_theta'],
                    't': parsed_request['delta_t'],
                    'z': parsed_request['delta_z']
                },
                'results': results
            }
            
        else:  # Regular query
            # Execute query
            results = self.query_processor.execute_query(parsed_request['query_text'])
            
            # Update current position to first result if available
            if results:
                self.current_position = results[0]['id']
                self.navigation_history.append(results[0])
                
            return {
                'type': 'query_results',
                'query': parsed_request['query_text'],
                'results': results
            }
            
    def format_results_for_llm(self, results: Dict[str, Any]) -> str:
        """
        Format results for inclusion in LLM context.
        
        Args:
            results: Query or navigation results
            
        Returns:
            Formatted text for LLM context
        """
        if results['type'] == 'error':
            return f"Error: {results['message']}"
            
        elif results['type'] == 'navigation_results':
            # Format navigation results
            deltas = results['deltas']
            formatted_text = [
                "Navigation Results:",
                f"Starting from item: {results['origin']}",
                f"Movement: r {deltas['r']:+.2f}, θ {deltas['theta']*180/np.pi:+.1f}°, t {deltas['t']/86400:+.1f} days, z {deltas['z']:+d}"
            ]
            
            # Add result items
            if not results['results']:
                formatted_text.append("\nNo items found in this direction.")
            else:
                formatted_text.append("\nItems found:")
                for i, item in enumerate(results['results'][:5]):  # Limit to 5 items
                    coords = item['coordinates']
                    
                    # Format temporal information
                    if 't' in coords:
                        time_str = datetime.fromtimestamp(coords['t']).strftime('%Y-%m-%d')
                    else:
                        time_str = "Unknown time"
                        
                    # Add context layer label
                    context_labels = {1: "Technical", 2: "Conceptual", 3: "Business"}
                    context = context_labels.get(coords.get('z', 0), "Unknown context")
                    
                    # Format item
                    formatted_text.append(f"\n[{i+1}] Item: {item['id']}")
                    
                    # Add metadata if available
                    if 'metadata' in item and item['metadata']:
                        meta = item['metadata']
                        meta_str = []
                        if 'title' in meta:
                            meta_str.append(f"Title: {meta['title']}")
                        if 'author' in meta:
                            meta_str.append(f"Author: {meta['author']}")
                        if meta_str:
                            formatted_text.append("  " + ", ".join(meta_str))
                            
                    # Add coordinates
                    formatted_text.append(f"  Coordinates: r={coords.get('r', 0):.2f}, θ={coords.get('theta', 0)*180/np.pi:.1f}°, {time_str}, {context}")
                    
                    # Add content snippet
                    content = item.get('content', '')
                    if len(content) > 200:
                        content = content[:197] + "..."
                    formatted_text.append(f"  Content: {content}")
                    
                # Add note about additional results
                if len(results['results']) > 5:
                    additional = len(results['results']) - 5
                    formatted_text.append(f"\n... and {additional} more items (not shown)")
                    
            return "\n".join(formatted_text)
            
        elif results['type'] == 'query_results':
            # Format query results
            formatted_text = [
                "Query Results:",
                f"Query: \"{results['query']}\""
            ]
            
            # Add result items
            if not results['results']:
                formatted_text.append("\nNo items found matching this query.")
            else:
                formatted_text.append("\nItems found:")
                for i, item in enumerate(results['results'][:5]):  # Limit to 5 items
                    coords = item['coordinates']
                    
                    # Format temporal information
                    if 't' in coords:
                        time_str = datetime.fromtimestamp(coords['t']).strftime('%Y-%m-%d')
                    else:
                        time_str = "Unknown time"
                        
                    # Add context layer label
                    context_labels = {1: "Technical", 2: "Conceptual", 3: "Business"}
                    context = context_labels.get(coords.get('z', 0), "Unknown context")
                    
                    # Format item
                    formatted_text.append(f"\n[{i+1}] Item: {item['id']}")
                    
                    # Add metadata if available
                    if 'metadata' in item and item['metadata']:
                        meta = item['metadata']
                        meta_str = []
                        if 'title' in meta:
                            meta_str.append(f"Title: {meta['title']}")
                        if 'author' in meta:
                            meta_str.append(f"Author: {meta['author']}")
                        if meta_str:
                            formatted_text.append("  " + ", ".join(meta_str))
                            
                    # Add coordinates and score if available
                    coord_parts = [f"r={coords.get('r', 0):.2f}", f"θ={coords.get('theta', 0)*180/np.pi:.1f}°", time_str, context]
                    if 'score' in item:
                        coord_parts.append(f"score={item['score']:.4f}")
                    formatted_text.append("  " + ", ".join(coord_parts))
                    
                    # Add content snippet
                    content = item.get('content', '')
                    if len(content) > 200:
                        content = content[:197] + "..."
                    formatted_text.append(f"  Content: {content}")
                    
                # Add note about additional results
                if len(results['results']) > 5:
                    additional = len(results['results']) - 5
                    formatted_text.append(f"\n... and {additional} more items (not shown)")
                    
            return "\n".join(formatted_text)
            
        else:
            return f"Unknown result type: {results['type']}"
            
    def generate_visualization_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate data for visualization of results.
        
        Args:
            results: Query or navigation results
            
        Returns:
            Visualization data
        """
        if results['type'] == 'error':
            return {
                'type': 'error',
                'message': results['message']
            }
            
        elif results['type'] in ['navigation_results', 'query_results']:
            # Extract items
            items = results.get('results', [])
            
            # Create visualization data
            vis_data = {
                'type': 'polar_temporal_visualization',
                'items': [],
                'temporal_range': [float('inf'), float('-inf')],  # [min, max]
                'center': None
            }
            
            # Add origin for navigation
            if results['type'] == 'navigation_results' and results.get('origin'):
                vis_data['center'] = results['origin']
                
            # Process items
            for item in items:
                coords = item.get('coordinates', {})
                
                # Skip items without proper coordinates
                if not all(k in coords for k in ['r', 'theta', 't', 'z']):
                    continue
                    
                # Add to visualization data
                vis_item = {
                    'id': item['id'],
                    'r': coords['r'],
                    'theta': coords['theta'],
                    't': coords['t'],
                    'z': coords['z'],
                    'metadata': {
                        'title': item.get('metadata', {}).get('title', item['id']),
                        'content_preview': item.get('content', '')[:50] + '...' if len(item.get('content', '')) > 50 else item.get('content', '')
                    }
                }
                
                vis_data['items'].append(vis_item)
                
                # Update temporal range
                vis_data['temporal_range'][0] = min(vis_data['temporal_range'][0], coords['t'])
                vis_data['temporal_range'][1] = max(vis_data['temporal_range'][1], coords['t'])
                
            return vis_data
        
        else:
            return {
                'type': 'error',
                'message': f"Unknown result type: {results['type']}"
            }
            
    def generate_llm_context(self, 
                           query: str, 
                           max_tokens: int = 4000,
                           include_query_history: bool = True,
                           include_navigation_history: bool = True) -> str:
        """
        Generate context for an LLM based on a query.
        
        Args:
            query: The query to generate context for
            max_tokens: Maximum tokens in the context
            include_query_history: Whether to include query history
            include_navigation_history: Whether to include navigation history
            
        Returns:
            Formatted context string for the LLM
        """
        # Execute query
        results = self.execute_llm_request(query)
        
        # Format results
        formatted_results = self.format_results_for_llm(results)
        
        # Create context parts
        context_parts = [formatted_results]
        
        # Add navigation history if requested
        if include_navigation_history and self.navigation_history:
            history_text = ["Navigation History:"]
            for i, item in enumerate(self.navigation_history[-5:]):  # Last 5 positions
                coords = item.get('coordinates', {})
                
                # Format temporal information
                if 't' in coords:
                    time_str = datetime.fromtimestamp(coords['t']).strftime('%Y-%m-%d')
                else:
                    time_str = "Unknown time"
                    
                # Add context layer label
                context_labels = {1: "Technical", 2: "Conceptual", 3: "Business"}
                context = context_labels.get(coords.get('z', 0), "Unknown context")
                
                # Format position
                history_text.append(
                    f"Position {len(self.navigation_history) - 5 + i + 1}: "
                    f"r={coords.get('r', 0):.2f}, θ={coords.get('theta', 0)*180/np.pi:.1f}°, "
                    f"{time_str}, {context}"
                )
                
            context_parts.append("\n".join(history_text))
            
        # Add query history if requested
        if include_query_history and self.query_history:
            history_text = ["Recent Query History:"]
            for i, query_item in enumerate(self.query_history[-5:]):  # Last 5 queries
                history_text.append(
                    f"Query {len(self.query_history) - 5 + i + 1}: \"{query_item['query']}\""
                )
                
            context_parts.append("\n".join(history_text))
            
        # Combine context parts with separators
        full_context = "\n\n" + "\n\n".join(context_parts)
        
        # Truncate if too long (rough estimate)
        if len(full_context) > max_tokens * 4:  # 4 chars per token rough estimate
            # Keep the most important parts
            # Truncate history sections first
            sections = full_context.split("\n\n")
            truncated_context = sections[0]  # Always keep the current results
            
            # Add as many other sections as will fit
            remaining_length = max_tokens * 4 - len(truncated_context)
            for section in sections[1:]:
                if len(section) + 2 <= remaining_length:  # +2 for the newlines
                    truncated_context += "\n\n" + section
                    remaining_length -= (len(section) + 2)
                else:
                    truncated_context += "\n\n[Additional context truncated due to length limits]"
                    break
                    
            return truncated_context
            
        return full_context
        
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for LLM initialization.
        
        Returns:
            System prompt string
        """
        return self.templates['system_prompt'] + self.templates['query_instruction']
        
    def generate_structured_query(self, 
                                embedding_text: str, 
                                r_min: float = 0,
                                r_max: float = 2.0,
                                theta_tolerance: float = np.pi/6,
                                t_min: Optional[float] = None,
                                t_max: Optional[float] = None,
                                z: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a structured 4D query from text.
        
        Args:
            embedding_text: Text to generate embedding from
            r_min: Minimum relevance radius
            r_max: Maximum relevance radius
            theta_tolerance: Angular tolerance around topic (in radians)
            t_min: Minimum time (optional)
            t_max: Maximum time (optional)
            z: Context layer (optional)
            
        Returns:
            Structured query parameters
        """
        # Generate embedding
        embedding = self.embedding_service.get_embedding(embedding_text)
        
        # Get angular position
        theta = self.query_processor.angular_mapper.calculate_embedding_angle(embedding)
        
        # Calculate angular range
        theta_min = (theta - theta_tolerance) % (2 * np.pi)
        theta_max = (theta + theta_tolerance) % (2 * np.pi)
        
        # Create query
        query = {
            'embedding': embedding,
            'r_min': r_min,
            'r_max': r_max,
            'theta_min': theta_min,
            'theta_max': theta_max,
            'z': z
        }
        
        # Add temporal constraints if provided
        if t_min is not None:
            query['t_min'] = t_min
        if t_max is not None:
            query['t_max'] = t_max
            
        return query


# Example usage with mock components
class MockEmbeddingService:
    def get_embedding(self, text):
        # Return random embedding for example
        return np.random.random(256).astype(np.float32)


# Example usage
if __name__ == "__main__":
    # Create mock components
    embedding_service = MockEmbeddingService()
    
    # Mock query processor with minimal functionality for demonstration
    class MockQueryProcessor:
        def __init__(self):
            self.angular_mapper = type('obj', (object,), {
                'calculate_embedding_angle': lambda self, embedding: np.random.random() * 2 * np.pi
            })()
            
        def execute_query(self, query_text):
            time.sleep(0.5)  # Simulate processing
            return [
                {
                    'id': f"result_{i}",
                    'content': f"Content for result {i} related to '{query_text}'",
                    'coordinates': {
                        'r': np.random.random() * 2,
                        'theta': np.random.random() * 2 * np.pi,
                        't': time.time() - np.random.random() * 86400 * 30,  # Random time in last 30 days
                        'z': np.random.randint(1, 4)
                    },
                    'metadata': {
                        'title': f"Result {i} for '{query_text}'",
                        'author': 'Mock Author'
                    },
                    'score': np.random.random()
                }
                for i in range(3)
            ]
            
        def navigate(self, center_id, delta_r, delta_theta, delta_t, delta_z, limit=10):
            time.sleep(0.5)  # Simulate processing
            return [
                {
                    'id': f"nav_result_{i}",
                    'content': f"Navigation result {i} from {center_id}",
                    'coordinates': {
                        'r': 1.0 + delta_r + np.random.random() * 0.5,
                        'theta': (np.pi/4 + delta_theta + np.random.random() * 0.2) % (2 * np.pi),
                        't': time.time() + delta_t + np.random.random() * 3600,
                        'z': 2 + delta_z
                    },
                    'metadata': {
                        'title': f"Navigation Result {i}",
                        'source': 'Navigation'
                    },
                    'score': np.random.random()
                }
                for i in range(2)
            ]
    
    # Create mock query processor
    query_processor = MockQueryProcessor()
    
    # Create LLM integration
    llm_integration = LLMIntegration(
        query_processor=query_processor,
        embedding_service=embedding_service
    )
    
    # Test query handling
    print("\nTesting query handling:")
    query_result = llm_integration.execute_llm_request("Find information about machine learning")
    print(llm_integration.format_results_for_llm(query_result))
    
    # Test navigation
    print("\nTesting navigation:")
    nav_result = llm_integration.execute_llm_request("Move forward in time by 2 days")
    print(llm_integration.format_results_for_llm(nav_result))
    
    # Test context generation
    print("\nTesting context generation:")
    context = llm_integration.generate_llm_context("Show related topics to neural networks")
    print(f"Context length: {len(context)} characters")
    print(context[:500] + "..." if len(context) > 500 else context)
    
    # Test system prompt
    print("\nSystem prompt for LLM initialization:")
    print(llm_integration.get_system_prompt())
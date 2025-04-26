"""
Query Processor for 4D Polar-Temporal Database

This module translates high-level queries into 4D coordinate space operations,
processes them, and returns results. It integrates the various components
of the system and provides an interface for LLMs to query the database.
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
import json
import re


class QueryProcessor:
    """
    Processes queries for the 4D polar-temporal database system.
    """
    
    def __init__(self,
                 faiss_adapter,
                 relevance_calculator,
                 angular_mapper,
                 embedding_service,
                 content_store):
        """
        Initialize the query processor.
        
        Args:
            faiss_adapter: FaissPolarTemporalAdapter instance
            relevance_calculator: RelevanceCalculator instance
            angular_mapper: AngularMapper instance
            embedding_service: Service for generating embeddings
            content_store: Storage system for content retrieval
        """
        self.faiss_adapter = faiss_adapter
        self.relevance_calculator = relevance_calculator
        self.angular_mapper = angular_mapper
        self.embedding_service = embedding_service
        self.content_store = content_store
        
        # Query history for context
        self.query_history = []
        
        # Query parser patterns
        self.patterns = {
            'temporal': re.compile(r'(?:from|after|before|between)\s+([a-zA-Z0-9\s,.]+)(?:\s+(?:to|and)\s+([a-zA-Z0-9\s,.]+))?', re.IGNORECASE),
            'topic': re.compile(r'(?:about|regarding|on the topic of|related to)\s+([a-zA-Z0-9\s,]+)', re.IGNORECASE),
            'relevance': re.compile(r'(?:most relevant|important|key|critical)\s+([a-zA-Z0-9\s,]+)', re.IGNORECASE),
            'context': re.compile(r'(?:in the context of|from the perspective of|in terms of)\s+([a-zA-Z0-9\s,]+)', re.IGNORECASE)
        }
        
    def parse_natural_language_query(self, query_text: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured parameters.
        
        Args:
            query_text: Natural language query string
            
        Returns:
            Dictionary of query parameters
        """
        query_params = {
            'r_min': 0,
            'r_max': float('inf'),
            'theta_min': 0,
            'theta_max': 2 * np.pi,
            't_min': float('-inf'),
            't_max': float('inf'),
            'z': None,
            'limit': 10,
            'topics': [],
            'central_concept': None
        }
        
        # Extract temporal constraints
        temporal_match = self.patterns['temporal'].search(query_text)
        if temporal_match:
            time_start = temporal_match.group(1).strip()
            time_end = temporal_match.group(2).strip() if temporal_match.group(2) else None
            
            # Convert to datetime or relative time
            query_params['t_min'] = self._parse_time_reference(time_start, is_start=True)
            
            if time_end:
                query_params['t_max'] = self._parse_time_reference(time_end, is_start=False)
            else:
                # If only one time point specified, interpret based on preposition
                preposition = re.search(r'(from|after|before|between)\s+', temporal_match.group(0), re.IGNORECASE)
                if preposition:
                    prep = preposition.group(1).lower()
                    if prep == 'before':
                        query_params['t_max'] = query_params['t_min']
                        query_params['t_min'] = float('-inf')
                    elif prep in ('from', 'after', 'between'):
                        query_params['t_max'] = float('inf')
        
        # Extract topic/category constraints
        topic_match = self.patterns['topic'].search(query_text)
        if topic_match:
            topics = topic_match.group(1).split(',')
            query_params['topics'] = [t.strip() for t in topics]
            
            # If we have topics, calculate angular range
            if query_params['topics']:
                theta_values = []
                for topic in query_params['topics']:
                    # Get angle for this topic
                    topic_embedding = self.embedding_service.get_embedding(topic)
                    theta = self.angular_mapper.calculate_embedding_angle(topic_embedding)
                    theta_values.append(theta)
                
                # Set angular range based on topics
                if len(theta_values) == 1:
                    # Single topic - use a sector around it
                    center = theta_values[0]
                    width = np.pi / 6  # 30 degrees
                    query_params['theta_min'] = (center - width) % (2 * np.pi)
                    query_params['theta_max'] = (center + width) % (2 * np.pi)
                else:
                    # Multiple topics - find the convex angular region
                    sorted_thetas = sorted(theta_values)
                    
                    # Find the largest gap
                    gaps = [(sorted_thetas[(i+1) % len(sorted_thetas)] - sorted_thetas[i]) % (2 * np.pi)
                            for i in range(len(sorted_thetas))]
                    largest_gap_idx = np.argmax(gaps)
                    
                    # Set the range to exclude the largest gap
                    query_params['theta_min'] = sorted_thetas[(largest_gap_idx + 1) % len(sorted_thetas)]
                    query_params['theta_max'] = sorted_thetas[largest_gap_idx]
        
        # Extract relevance constraints
        relevance_match = self.patterns['relevance'].search(query_text)
        if relevance_match:
            central_concept = relevance_match.group(1).strip()
            query_params['central_concept'] = central_concept
            
            # Limit to highly relevant items
            query_params['r_max'] = 2.0  # Only fairly relevant items
        
        # Extract context layer
        context_match = self.patterns['context'].search(query_text)
        if context_match:
            context_type = context_match.group(1).strip().lower()
            
            # Map context type to z value
            context_map = {
                'technical': 1,
                'implementation': 1,
                'code': 1,
                'conceptual': 2,
                'design': 2,
                'theory': 2,
                'business': 3,
                'user': 3,
                'impact': 3
            }
            
            for key, value in context_map.items():
                if key in context_type:
                    query_params['z'] = value
                    break
        
        # Extract limit if specified
        limit_match = re.search(r'(?:top|limit)\s+(\d+)', query_text, re.IGNORECASE)
        if limit_match:
            query_params['limit'] = int(limit_match.group(1))
            
        return query_params
        
    def _parse_time_reference(self, time_str: str, is_start: bool = True) -> float:
        """
        Parse a time reference from text to a numeric value.
        
        Args:
            time_str: String describing a time point
            is_start: Whether this is the start or end of a range
            
        Returns:
            Numeric time value
        """
        # Handle relative time references
        if 'day' in time_str or 'yesterday' in time_str:
            days = 1
            if 'yesterday' not in time_str:
                # Extract number of days
                days_match = re.search(r'(\d+)\s+days?', time_str)
                if days_match:
                    days = int(days_match.group(1))
            
            # Convert to timestamp relative to now
            now = datetime.now().timestamp()
            seconds_per_day = 86400
            return now - (days * seconds_per_day)
            
        elif 'week' in time_str:
            weeks = 1
            weeks_match = re.search(r'(\d+)\s+weeks?', time_str)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                
            now = datetime.now().timestamp()
            seconds_per_week = 604800
            return now - (weeks * seconds_per_week)
            
        elif 'month' in time_str:
            months = 1
            months_match = re.search(r'(\d+)\s+months?', time_str)
            if months_match:
                months = int(months_match.group(1))
                
            now = datetime.now().timestamp()
            seconds_per_month = 2592000  # 30 days
            return now - (months * seconds_per_month)
            
        elif 'year' in time_str:
            years = 1
            years_match = re.search(r'(\d+)\s+years?', time_str)
            if years_match:
                years = int(years_match.group(1))
                
            now = datetime.now().timestamp()
            seconds_per_year = 31536000
            return now - (years * seconds_per_year)
            
        # Handle absolute date references
        try:
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%B %d, %Y',
                '%b %d, %Y'
            ]
            
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    
                    # For a start date, use the beginning of the day
                    # For an end date, use the end of the day
                    if is_start:
                        dt = dt.replace(hour=0, minute=0, second=0)
                    else:
                        dt = dt.replace(hour=23, minute=59, second=59)
                        
                    return dt.timestamp()
                except ValueError:
                    continue
                    
            # If no format matched, use the current timestamp
            return datetime.now().timestamp()
                
        except Exception as e:
            print(f"Error parsing time reference '{time_str}': {e}")
            # Default to current time
            return datetime.now().timestamp()
            
    def execute_query(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Execute a natural language query.
        
        Args:
            query_text: Natural language query
            
        Returns:
            List of result items with metadata
        """
        # Save to history
        self.query_history.append({
            'text': query_text,
            'timestamp': datetime.now()
        })
        
        # Parse the query
        query_params = self.parse_natural_language_query(query_text)
        
        # Generate query embedding
        query_embedding = self.embedding_service.get_embedding(query_text)
        
        # Get central concept ID if specified
        central_id = None
        if query_params['central_concept']:
            # Try to find the concept in our database
            concept_embedding = self.embedding_service.get_embedding(query_params['central_concept'])
            similar_items = self.faiss_adapter.get_similar_items(concept_embedding, k=1)
            
            if similar_items:
                central_id = similar_items[0][0]
        
        # Execute the combined query
        results = self.faiss_adapter.combined_query(
            query_embedding=query_embedding,
            r_min=query_params['r_min'],
            r_max=query_params['r_max'],
            theta_min=query_params['theta_min'],
            theta_max=query_params['theta_max'],
            t_min=query_params['t_min'],
            t_max=query_params['t_max'],
            z=query_params['z'],
            k=query_params['limit']
        )
        
        # Fetch full content and metadata for results
        enriched_results = []
        for item_id, score in results:
            # Get coordinates
            coords = self.faiss_adapter.id_to_coordinates.get(item_id, {})
            
            # Get content
            content = self.content_store.get_content(item_id)
            
            # Get metadata
            metadata = self.faiss_adapter.faiss_engine.metadata.get(item_id, {})
            
            # Add to results
            enriched_results.append({
                'id': item_id,
                'score': float(score),
                'coordinates': {
                    'r': coords.get('r', 0),
                    'theta': coords.get('theta', 0),
                    't': coords.get('t', 0),
                    'z': coords.get('z', 0)
                },
                'content': content,
                'metadata': metadata
            })
            
        return enriched_results
        
    def navigate(self,
                center_id: str,
                delta_r: float = 0,
                delta_theta: float = 0,
                delta_t: float = 0,
                delta_z: int = 0,
                limit: int = 10) -> List[Dict[str, Any]]:
        """
        Navigate from a center point in the 4D space.
        
        Args:
            center_id: ID of the center item
            delta_r: Change in radial position
            delta_theta: Change in angular position
            delta_t: Change in temporal position
            delta_z: Change in context layer
            limit: Maximum number of results
            
        Returns:
            List of result items with metadata
        """
        # Get coordinates of center item
        coords = self.faiss_adapter.id_to_coordinates.get(center_id)
        if not coords:
            return []
            
        # Calculate target coordinates
        target_r = max(0, coords['r'] + delta_r)
        target_theta = (coords['theta'] + delta_theta) % (2 * np.pi)
        target_t = coords['t'] + delta_t
        target_z = max(1, coords['z'] + delta_z)
        
        # Define search ranges around the target
        r_range = 0.5
        theta_range = np.pi / 12  # 15 degrees
        t_range = abs(delta_t) * 0.2 if delta_t != 0 else 10
        
        # Query for items near the target
        results = self.faiss_adapter.combined_query(
            query_embedding=None,  # No semantic similarity for navigation
            r_min=max(0, target_r - r_range),
            r_max=target_r + r_range,
            theta_min=(target_theta - theta_range) % (2 * np.pi),
            theta_max=(target_theta + theta_range) % (2 * np.pi),
            t_min=target_t - t_range,
            t_max=target_t + t_range,
            z=int(target_z) if delta_z != 0 else None,
            k=limit
        )
        
        # Fetch full content and metadata for results
        enriched_results = []
        for item_id, score in results:
            # Skip the center item
            if item_id == center_id:
                continue
                
            # Get coordinates
            item_coords = self.faiss_adapter.id_to_coordinates.get(item_id, {})
            
            # Get content
            content = self.content_store.get_content(item_id)
            
            # Get metadata
            metadata = self.faiss_adapter.faiss_engine.metadata.get(item_id, {})
            
            # Calculate coordinate deltas from center
            deltas = {
                'r': item_coords.get('r', 0) - coords['r'],
                'theta': (item_coords.get('theta', 0) - coords['theta'] + np.pi) % (2 * np.pi) - np.pi,  # Normalize to [-π, π]
                't': item_coords.get('t', 0) - coords['t'],
                'z': item_coords.get('z', 0) - coords['z']
            }
            
            # Add to results
            enriched_results.append({
                'id': item_id,
                'score': float(score),
                'coordinates': {
                    'r': item_coords.get('r', 0),
                    'theta': item_coords.get('theta', 0),
                    't': item_coords.get('t', 0),
                    'z': item_coords.get('z', 0)
                },
                'deltas': deltas,
                'content': content,
                'metadata': metadata
            })
            
        # Sort by closest to the intended navigation direction
        primary_dimension = 'r' if delta_r != 0 else 't' if delta_t != 0 else 'theta' if delta_theta != 0 else 'z'
        primary_delta = delta_r if delta_r != 0 else delta_t if delta_t != 0 else delta_theta if delta_theta != 0 else delta_z
        
        enriched_results.sort(key=lambda x: 
            abs(x['deltas'][primary_dimension] - primary_delta)
        )
        
        return enriched_results
        
    def specialized_query(self, query_type: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute a specialized type of query.
        
        Args:
            query_type: Type of specialized query
            **kwargs: Parameters specific to the query type
            
        Returns:
            List of result items with metadata
        """
        if query_type == 'temporal_evolution':
            # Trace the evolution of a concept over time
            concept = kwargs.get('concept')
            time_start = kwargs.get('time_start', 0)
            time_end = kwargs.get('time_end', float('inf'))
            time_steps = kwargs.get('time_steps', 10)
            
            # Generate concept embedding
            concept_embedding = self.embedding_service.get_embedding(concept)
            
            # Find concept in database
            similar_items = self.faiss_adapter.get_similar_items(concept_embedding, k=1)
            if not similar_items:
                return []
                
            center_id = similar_items[0][0]
            center_coords = self.faiss_adapter.id_to_coordinates.get(center_id, {})
            
            # Calculate time windows
            time_range = time_end - time_start
            window_size = time_range / time_steps
            
            results = []
            
            for i in range(time_steps):
                t_min = time_start + i * window_size
                t_max = t_min + window_size
                
                # Query for items in this time window
                window_results = self.faiss_adapter.combined_query(
                    query_embedding=concept_embedding,
                    r_min=0,
                    r_max=1.5,  # Only fairly relevant items
                    theta_min=(center_coords.get('theta', 0) - np.pi/6) % (2 * np.pi),
                    theta_max=(center_coords.get('theta', 0) + np.pi/6) % (2 * np.pi),
                    t_min=t_min,
                    t_max=t_max,
                    z=None,
                    k=5
                )
                
                # Get the most relevant item for this time window
                if window_results:
                    item_id, score = window_results[0]
                    
                    # Get content and metadata
                    coords = self.faiss_adapter.id_to_coordinates.get(item_id, {})
                    content = self.content_store.get_content(item_id)
                    metadata = self.faiss_adapter.faiss_engine.metadata.get(item_id, {})
                    
                    results.append({
                        'id': item_id,
                        'score': float(score),
                        'coordinates': {
                            'r': coords.get('r', 0),
                            'theta': coords.get('theta', 0),
                            't': coords.get('t', 0),
                            'z': coords.get('z', 0)
                        },
                        'content': content,
                        'metadata': metadata,
                        'time_window': {
                            'start': t_min,
                            'end': t_max
                        }
                    })
            
            return results
            
        elif query_type == 'conceptual_map':
            # Generate a conceptual map around a central concept
            concept = kwargs.get('concept')
            radius = kwargs.get('radius', 2.0)
            angular_divisions = kwargs.get('angular_divisions', 8)
            
            # Generate concept embedding
            concept_embedding = self.embedding_service.get_embedding(concept)
            
            # Find concept in database
            similar_items = self.faiss_adapter.get_similar_items(concept_embedding, k=1)
            if not similar_items:
                return []
                
            center_id = similar_items[0][0]
            center_coords = self.faiss_adapter.id_to_coordinates.get(center_id, {})
            
            results = [{
                'id': center_id,
                'is_center': True,
                'coordinates': center_coords,
                'content': self.content_store.get_content(center_id),
                'metadata': self.faiss_adapter.faiss_engine.metadata.get(center_id, {})
            }]
            
            # Divide the circle into sectors
            sector_width = 2 * np.pi / angular_divisions
            
            for i in range(angular_divisions):
                sector_center = (i * sector_width) % (2 * np.pi)
                sector_min = (sector_center - sector_width/2) % (2 * np.pi)
                sector_max = (sector_center + sector_width/2) % (2 * np.pi)
                
                # Query for items in this sector
                sector_results = self.faiss_adapter.combined_query(
                    query_embedding=concept_embedding,
                    r_min=0,
                    r_max=radius,
                    theta_min=sector_min,
                    theta_max=sector_max,
                    t_min=float('-inf'),
                    t_max=float('inf'),
                    z=None,
                    k=3
                )
                
                # Add the most relevant item for this sector
                if sector_results:
                    for item_id, score in sector_results:
                        if item_id != center_id:  # Skip center
                            coords = self.faiss_adapter.id_to_coordinates.get(item_id, {})
                            content = self.content_store.get_content(item_id)
                            metadata = self.faiss_adapter.faiss_engine.metadata.get(item_id, {})
                            
                            results.append({
                                'id': item_id,
                                'is_center': False,
                                'sector': i,
                                'sector_angle': sector_center,
                                'score': float(score),
                                'coordinates': coords,
                                'content': content,
                                'metadata': metadata
                            })
                            break
            
            return results
            
        else:
            raise ValueError(f"Unknown specialized query type: {query_type}")
            
    def get_query_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent query history.
        
        Args:
            limit: Maximum number of history items to return
            
        Returns:
            List of recent queries with timestamps
        """
        return self.query_history[-limit:]
        
    def generate_llm_context(self, 
                            query_text: str, 
                            max_tokens: int = 4000) -> str:
        """
        Generate context for an LLM based on a query.
        
        Args:
            query_text: The query to generate context for
            max_tokens: Maximum tokens in the context
            
        Returns:
            Formatted context string for the LLM
        """
        # Execute the query
        results = self.execute_query(query_text)
        
        if not results:
            return "No relevant information found."
            
        # Format results for LLM
        context_parts = ["Relevant information based on your query:"]
        
        for i, result in enumerate(results):
            # Extract key information
            content = result['content']
            coords = result['coordinates']
            metadata = result['metadata']
            
            # Truncate content if needed
            max_content_len = 300
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."
                
            # Format metadata
            meta_str = ""
            if metadata.get('title'):
                meta_str += f"Title: {metadata['title']}"
            if metadata.get('author'):
                meta_str += f", Author: {metadata['author']}"
            if metadata.get('date'):
                meta_str += f", Date: {metadata['date']}"
                
            # Add to context
            context_parts.append(
                f"\n[{i+1}] {meta_str}\n"
                f"Relevance: {1.0 - coords['r']:.2f}, "
                f"Topic angle: {coords['theta']*180/np.pi:.1f}°, "
                f"Time: {datetime.fromtimestamp(coords['t']).strftime('%Y-%m-%d')}\n"
                f"Content: {content}\n"
            )
            
            # Check if we've exceeded the token limit (rough estimate)
            if sum(len(part) for part in context_parts) > max_tokens * 4:  # 4 chars per token rough estimate
                context_parts.append(f"\n[Note: Additional relevant information truncated due to length constraints]")
                break
                
        return "\n".join(context_parts)


# Mock embedding service for example
class MockEmbeddingService:
    def get_embedding(self, text):
        # Return random embedding for example
        return np.random.random(256).astype(np.float32)


# Mock content store for example
class MockContentStore:
    def get_content(self, item_id):
        # Return placeholder content for example
        return f"This is the content for {item_id}"


# Example usage
if __name__ == "__main__":
    from relevance_calculator import RelevanceCalculator
    from angular_mapper import AngularMapper
    from faiss_integration import FaissIntegration, FaissPolarTemporalAdapter
    
    # Mock components for example
    faiss_engine = FaissIntegration(embedding_dim=256, use_gpu=False)
    adapter = FaissPolarTemporalAdapter(faiss_engine)
    relevance_calculator = RelevanceCalculator(embedding_dim=256)
    angular_mapper = AngularMapper(embedding_dim=256)
    embedding_service = MockEmbeddingService()
    content_store = MockContentStore()
    
    # Add some test items
    for i in range(100):
        item_id = f"item_{i}"
        embedding = np.random.random(256).astype(np.float32)
        r = np.random.uniform(0, 3)
        theta = np.random.uniform(0, 2 * np.pi)
        t = np.random.uniform(datetime(2020, 1, 1).timestamp(), datetime(2023, 12, 31).timestamp())
        z = np.random.randint(1, 4)
        
        adapter.add_item_with_coordinates(
            item_id=item_id,
            embedding=embedding,
            r=r,
            theta=theta,
            t=t,
            z=z
        )
    
    # Create the query processor
    processor = QueryProcessor(
        faiss_adapter=adapter,
        relevance_calculator=relevance_calculator,
        angular_mapper=angular_mapper,
        embedding_service=embedding_service,
        content_store=content_store
    )
    
    # Test natural language queries
    queries = [
        "Find information about machine learning from the last 2 years",
        "What are the most relevant documents about data science in the context of business?",
        "Show me information related to neural networks and deep learning before 2022",
        "What's the most important development in AI from the technical perspective?"
    ]
    
    for query in queries:
        print(f"\nExecuting query: '{query}'")
        params = processor.parse_natural_language_query(query)
        print(f"Parsed parameters: {json.dumps(params, default=str, indent=2)}")
        
        results = processor.execute_query(query)
        print(f"Found {len(results)} results")
        
        if results:
            print(f"Top result: {results[0]['id']}")
            print(f"  Relevance: {1.0 - results[0]['coordinates']['r']:.2f}")
            print(f"  Topic angle: {results[0]['coordinates']['theta']*180/np.pi:.1f}°")
            print(f"  Time: {datetime.fromtimestamp(results[0]['coordinates']['t']).strftime('%Y-%m-%d')}")
            if results[0]['coordinates']['z'] == 1:
                print("  Context: Technical")
            elif results[0]['coordinates']['z'] == 2:
                print("  Context: Conceptual")
            elif results[0]['coordinates']['z'] == 3:
                print("  Context: Business")
            
    # Test specialized queries
    print("\nExecuting temporal evolution query")
    evolution_results = processor.specialized_query(
        query_type="temporal_evolution",
        concept="machine learning",
        time_start=datetime(2020, 1, 1).timestamp(),
        time_end=datetime(2023, 12, 31).timestamp(),
        time_steps=4
    )
    print(f"Found {len(evolution_results)} evolution points")
    
    print("\nExecuting conceptual map query")
    map_results = processor.specialized_query(
        query_type="conceptual_map",
        concept="data science",
        radius=2.0,
        angular_divisions=6
    )
    print(f"Found {len(map_results)} map points")
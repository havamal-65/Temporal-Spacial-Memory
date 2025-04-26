"""
Angular Topic Mapper for 4D Polar-Temporal Database

This module maps topics/categories to angular positions (θ dimension).
It implements multiple strategies for determining angular positions:
1. Embedding projection
2. Topic modeling
3. Hierarchical category assignment
"""

import numpy as np
import umap
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
import networkx as nx
from typing import Dict, List, Tuple, Optional, Union, Set
import math


class AngularMapper:
    """
    Maps topics and content to angular positions in the polar-temporal space.
    """
    
    def __init__(self, 
                 embedding_dim: int = 1536,
                 n_topics: int = 20,
                 mapping_strategy: str = 'hybrid'):
        """
        Initialize the angular mapper.
        
        Args:
            embedding_dim: Dimension of embeddings
            n_topics: Number of topics for topic modeling
            mapping_strategy: Strategy for mapping ('embedding', 'topics', 'hierarchical', or 'hybrid')
        """
        self.embedding_dim = embedding_dim
        self.n_topics = n_topics
        self.mapping_strategy = mapping_strategy
        
        # Initialize UMAP for dimensionality reduction of embeddings
        self.umap_model = umap.UMAP(
            n_components=2,
            random_state=42,
            min_dist=0.1,
            metric='cosine'
        )
        
        # Initialize topic model
        self.lda_model = None
        self.vectorizer = CountVectorizer(
            max_features=10000,
            stop_words='english'
        )
        
        # Storage for calculated angles
        self.id_to_theta = {}
        self.topic_to_theta = {}
        
        # Topic similarity graph
        self.topic_graph = nx.Graph()
        
        # Category hierarchy for hierarchical mapping
        self.category_hierarchy = {}
        self.category_to_theta = {}
        
        # Track which sections of the angular space are occupied
        self.occupied_sectors = []  # List of (start_angle, end_angle) tuples
        
    def initialize_topic_model(self, texts: List[str]) -> None:
        """
        Initialize the topic model with a corpus of texts.
        
        Args:
            texts: List of text documents for training the topic model
        """
        # Create document-term matrix
        dtm = self.vectorizer.fit_transform(texts)
        
        # Fit LDA model
        self.lda_model = LatentDirichletAllocation(
            n_components=self.n_topics,
            random_state=42,
            max_iter=20
        )
        self.lda_model.fit(dtm)
        
        # Initialize topic angles by distributing them evenly
        for topic_idx in range(self.n_topics):
            angle = (topic_idx / self.n_topics) * 2 * np.pi
            self.topic_to_theta[topic_idx] = angle
            self.topic_graph.add_node(topic_idx)
        
        # Calculate topic similarities to build the topic graph
        topic_term_matrix = self.lda_model.components_
        for i in range(self.n_topics):
            for j in range(i+1, self.n_topics):
                # Calculate cosine similarity between topic vectors
                similarity = np.dot(topic_term_matrix[i], topic_term_matrix[j]) / (
                    np.linalg.norm(topic_term_matrix[i]) * np.linalg.norm(topic_term_matrix[j])
                )
                if similarity > 0.2:  # Only connect similar topics
                    self.topic_graph.add_edge(i, j, weight=similarity)
    
    def initialize_category_hierarchy(self, 
                                     hierarchy: Dict[str, Union[List[str], Dict]]) -> None:
        """
        Initialize the hierarchical category structure.
        
        Args:
            hierarchy: Dictionary representing category hierarchy
                       e.g. {'science': ['physics', 'biology'], 'arts': {...}}
        """
        self.category_hierarchy = hierarchy
        
        # Assign base angles to top-level categories
        top_categories = list(hierarchy.keys())
        for i, category in enumerate(top_categories):
            base_angle = (i / len(top_categories)) * 2 * np.pi
            self.category_to_theta[category] = base_angle
            self.occupied_sectors.append(
                (base_angle, base_angle + (2 * np.pi / len(top_categories)))
            )
            
            # Process subcategories recursively
            self._assign_subcategory_angles(
                category, 
                hierarchy[category], 
                base_angle, 
                2 * np.pi / len(top_categories)
            )
    
    def _assign_subcategory_angles(self, 
                                  parent: str, 
                                  children: Union[List[str], Dict], 
                                  parent_angle: float, 
                                  sector_width: float,
                                  depth: int = 1) -> None:
        """
        Recursively assign angles to subcategories.
        
        Args:
            parent: Parent category name
            children: List of subcategories or dict of nested hierarchies
            parent_angle: Base angle of the parent category
            sector_width: Angular width allocated to parent
            depth: Current depth in the hierarchy
        """
        if isinstance(children, list):
            # Divide parent sector among children
            child_width = sector_width / len(children)
            for i, child in enumerate(children):
                child_angle = parent_angle + i * child_width + (child_width / 2)
                self.category_to_theta[child] = child_angle
        
        elif isinstance(children, dict):
            # Process dictionary of nested subcategories
            subcategories = list(children.keys())
            child_width = sector_width / len(subcategories)
            
            for i, subcategory in enumerate(subcategories):
                base_angle = parent_angle + i * child_width
                full_category = f"{parent}.{subcategory}"
                self.category_to_theta[full_category] = base_angle + (child_width / 2)
                
                # Recurse for further subcategories
                self._assign_subcategory_angles(
                    full_category,
                    children[subcategory],
                    base_angle,
                    child_width,
                    depth + 1
                )
    
    def optimize_topic_angles(self) -> None:
        """
        Optimize topic angles based on topic similarity graph.
        Places similar topics in adjacent angular positions.
        """
        # Use force-directed layout to position nodes on a circle
        pos = nx.spring_layout(self.topic_graph, dim=2, seed=42)
        
        # Convert cartesian positions to angles
        for topic_idx, position in pos.items():
            x, y = position
            theta = math.atan2(y, x) % (2 * np.pi)
            self.topic_to_theta[topic_idx] = theta
    
    def calculate_embedding_angle(self, embedding: np.ndarray) -> float:
        """
        Project embedding to 2D and convert to angle.
        
        Args:
            embedding: High-dimensional embedding vector
            
        Returns:
            Angular position (θ) in [0, 2π)
        """
        # Reshape for UMAP
        embedding = embedding.reshape(1, -1)
        
        # Project to 2D if we have enough samples for UMAP
        if hasattr(self.umap_model, 'embedding_') and self.umap_model.embedding_.shape[0] > 0:
            projection = self.umap_model.transform(embedding)
        else:
            # Not enough samples yet, use PCA-like projection for now
            projection = np.random.random((1, 2))
        
        # Convert to polar coordinates
        x, y = projection[0]
        theta = math.atan2(y, x) % (2 * np.pi)
        
        return theta
    
    def calculate_topic_angle(self, text: str) -> float:
        """
        Calculate angular position based on topic distribution.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Angular position (θ) in [0, 2π)
        """
        if self.lda_model is None:
            # Default to random if topic model isn't initialized
            return np.random.random() * 2 * np.pi
        
        # Vectorize text
        dtm = self.vectorizer.transform([text])
        
        # Get topic distribution
        topic_dist = self.lda_model.transform(dtm)[0]
        
        # Calculate weighted average angle
        weighted_angle = 0
        total_weight = 0
        
        for topic_idx, weight in enumerate(topic_dist):
            if weight > 0.05:  # Ignore negligible topics
                theta = self.topic_to_theta.get(topic_idx, 0)
                weighted_angle += theta * weight
                total_weight += weight
        
        if total_weight > 0:
            avg_angle = weighted_angle / total_weight
            return avg_angle
        else:
            return np.random.random() * 2 * np.pi
    
    def calculate_category_angle(self, categories: List[str]) -> float:
        """
        Calculate angular position based on hierarchical categories.
        
        Args:
            categories: List of categories applicable to the content
            
        Returns:
            Angular position (θ) in [0, 2π)
        """
        if not categories or not self.category_to_theta:
            return np.random.random() * 2 * np.pi
            
        # Get valid categories that exist in our mapping
        valid_categories = [c for c in categories if c in self.category_to_theta]
        
        if not valid_categories:
            return np.random.random() * 2 * np.pi
            
        # Calculate average angle of all applicable categories
        angles = [self.category_to_theta[c] for c in valid_categories]
        
        # Handle circular averaging correctly
        sin_sum = sum(math.sin(angle) for angle in angles)
        cos_sum = sum(math.cos(angle) for angle in angles)
        
        avg_angle = math.atan2(sin_sum, cos_sum) % (2 * np.pi)
        return avg_angle
    
    def calculate_hybrid_angle(self, 
                              embedding: np.ndarray, 
                              text: str, 
                              categories: Optional[List[str]] = None) -> float:
        """
        Calculate angular position using a hybrid of multiple strategies.
        
        Args:
            embedding: Vector embedding
            text: Text content
            categories: Optional list of categories
            
        Returns:
            Angular position (θ) in [0, 2π)
        """
        angles = []
        weights = []
        
        # Get embedding-based angle
        embedding_angle = self.calculate_embedding_angle(embedding)
        angles.append(embedding_angle)
        weights.append(0.4)  # 40% weight for embedding
        
        # Get topic-based angle
        topic_angle = self.calculate_topic_angle(text)
        angles.append(topic_angle)
        weights.append(0.4)  # 40% weight for topics
        
        # Get category-based angle (if available)
        if categories:
            category_angle = self.calculate_category_angle(categories)
            angles.append(category_angle)
            weights.append(0.2)  # 20% weight for categories
        else:
            # Redistribute weight if no categories
            weights = [0.5, 0.5, 0]
        
        # Calculate weighted circular mean
        sin_sum = sum(w * math.sin(a) for a, w in zip(angles, weights))
        cos_sum = sum(w * math.cos(a) for a, w in zip(angles, weights))
        
        hybrid_angle = math.atan2(sin_sum, cos_sum) % (2 * np.pi)
        return hybrid_angle
    
    def get_angle(self, 
                 item_id: str, 
                 embedding: np.ndarray, 
                 text: str, 
                 categories: Optional[List[str]] = None) -> float:
        """
        Get angular position for an item using the configured strategy.
        
        Args:
            item_id: Unique identifier for the item
            embedding: Vector embedding
            text: Text content
            categories: Optional list of categories
            
        Returns:
            Angular position (θ) in [0, 2π)
        """
        # Return cached angle if available
        if item_id in self.id_to_theta:
            return self.id_to_theta[item_id]
        
        # Calculate angle based on selected strategy
        if self.mapping_strategy == 'embedding':
            theta = self.calculate_embedding_angle(embedding)
        elif self.mapping_strategy == 'topics':
            theta = self.calculate_topic_angle(text)
        elif self.mapping_strategy == 'hierarchical':
            theta = self.calculate_category_angle(categories or [])
        else:  # hybrid
            theta = self.calculate_hybrid_angle(embedding, text, categories)
        
        # Cache and return
        self.id_to_theta[item_id] = theta
        return theta
    
    def get_items_in_sector(self, 
                           center_angle: float, 
                           width: float = 0.5) -> List[str]:
        """
        Get items within an angular sector.
        
        Args:
            center_angle: Center of the angular sector
            width: Width of the sector in radians
            
        Returns:
            List of item IDs within the sector
        """
        half_width = width / 2
        start_angle = (center_angle - half_width) % (2 * np.pi)
        end_angle = (center_angle + half_width) % (2 * np.pi)
        
        results = []
        
        for item_id, theta in self.id_to_theta.items():
            # Check if angle is within sector, handling wrap-around
            if start_angle <= end_angle:
                if start_angle <= theta <= end_angle:
                    results.append(item_id)
            else:
                if theta >= start_angle or theta <= end_angle:
                    results.append(item_id)
        
        return results


# Example usage
if __name__ == "__main__":
    # Create angular mapper
    mapper = AngularMapper(embedding_dim=256, n_topics=10, mapping_strategy='hybrid')
    
    # Initialize with sample texts
    sample_texts = [
        "Machine learning algorithms can automatically learn and improve from experience.",
        "Deep neural networks have achieved remarkable results in computer vision tasks.",
        "Natural language processing enables computers to understand human language.",
        "Reinforcement learning is inspired by behavioral psychology.",
        "Unsupervised learning finds hidden patterns in unlabeled data.",
        "The history of art spans back to prehistoric cave paintings.",
        "Renaissance art was characterized by realism and perspective techniques.",
        "Impressionism focused on capturing light and color in everyday scenes.",
        "Modern art movements include cubism, surrealism, and abstract expressionism.",
        "Contemporary art often challenges traditional boundaries and conventions."
    ]
    mapper.initialize_topic_model(sample_texts)
    
    # Initialize category hierarchy
    hierarchy = {
        "technology": ["ai", "programming", "data_science"],
        "arts": ["visual_arts", "music", "literature"],
        "science": ["physics", "biology", "chemistry"],
        "business": ["finance", "marketing", "management"]
    }
    mapper.initialize_category_hierarchy(hierarchy)
    
    # Generate a random embedding
    embedding = np.random.random(256).astype(np.float32)
    
    # Calculate angle with different methods
    text = "Deep learning techniques for natural language processing"
    categories = ["technology", "ai"]
    
    embedding_angle = mapper.calculate_embedding_angle(embedding)
    topic_angle = mapper.calculate_topic_angle(text)
    category_angle = mapper.calculate_category_angle(categories)
    hybrid_angle = mapper.calculate_hybrid_angle(embedding, text, categories)
    
    print(f"Embedding angle: {embedding_angle:.4f} rad ({math.degrees(embedding_angle):.1f}°)")
    print(f"Topic angle: {topic_angle:.4f} rad ({math.degrees(topic_angle):.1f}°)")
    print(f"Category angle: {category_angle:.4f} rad ({math.degrees(category_angle):.1f}°)")
    print(f"Hybrid angle: {hybrid_angle:.4f} rad ({math.degrees(hybrid_angle):.1f}°)")
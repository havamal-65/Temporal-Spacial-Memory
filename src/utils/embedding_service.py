"""
Embedding Service Utility

This module provides utilities for generating vector embeddings from text.
It supports multiple embedding services including local models and API-based ones.
"""

import numpy as np
import logging
import hashlib
import os
import time
from typing import List, Dict, Any, Optional, Union
from functools import lru_cache
from langchain_core.embeddings import Embeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EmbeddingService')

# Base class for embedding services - Inherit from Langchain's base
class EmbeddingService(Embeddings): # Inherit from langchain_core.embeddings.Embeddings
    """Base class for all embedding services, conforming to Langchain's Embeddings interface."""
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the embedding service.
        
        Args:
            embedding_dim: Dimension of the embedding vectors
        """
        self.embedding_dim = embedding_dim
    
    # Rename get_embedding to embed_query and adjust return type
    def embed_query(self, text: str) -> List[float]: 
        """
        Generate an embedding for a single query text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        raise NotImplementedError
    
    # Rename get_embeddings to embed_documents and adjust return type
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of lists of floats representing the embeddings
        """
        raise NotImplementedError


class MockEmbeddingService(EmbeddingService):
    """
    Mock embedding service that generates deterministic embeddings based on text hashing.
    This is used for testing and development when a real embedding service is not available.
    """
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the mock embedding service.
        
        Args:
            embedding_dim: Dimension of the embedding vectors
        """
        super().__init__(embedding_dim)
        logger.info(f"Initialized MockEmbeddingService with dimension {embedding_dim}")
    
    # Implement embed_query (renamed from get_embedding)
    def embed_query(self, text: str) -> List[float]:
        """
        Generate a mock embedding for a single query text.
        Conforms to Langchain Embeddings interface.
        """
        if not text:
            return [0.0] * self.embedding_dim # Return list of floats
        
        # Create a hash of the text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Use the hash to seed the random number generator for deterministic output
        seed = int(text_hash, 16) % (2**32)
        rng = np.random.RandomState(seed)
        
        # Generate a random vector
        vector = rng.randn(self.embedding_dim)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector.tolist() # Convert numpy array to list of floats
    
    # Implement embed_documents (renamed from get_embeddings)
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate mock embeddings for multiple texts.
        Conforms to Langchain Embeddings interface.
        """
        # Use the single embed_query logic for each text
        return [self.embed_query(text) for text in texts]


class LangchainEmbeddingService(EmbeddingService):
    """
    Embedding service that uses LangChain's embedding models.
    This provides an interface to various embedding services through LangChain.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_size: int = 1000):
        """
        Initialize the LangChain embedding service.
        
        Args:
            model_name: Name of the embedding model to use (default: all-MiniLM-L6-v2)
            cache_size: Size of the LRU cache for embeddings
        """
        # Set up model-specific dimensions
        model_dimensions = {
            "all-MiniLM-L6-v2": 384,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "all-mpnet-base-v2": 768,
            "paraphrase-multilingual-MiniLM-L12-v2": 384
        }
        
        # Get embedding dimension based on model
        embedding_dim = model_dimensions.get(model_name, 384)
        super().__init__(embedding_dim)
        
        # Initialize cache for embeddings (now caching embed_query)
        self._cache_embed_query = lru_cache(maxsize=cache_size)(self._embed_query_uncached)
        
        try:
            if "text-embedding" in model_name.lower():
                # OpenAI embeddings
                from langchain_openai import OpenAIEmbeddings
                api_key = os.environ.get("OPENAI_API_KEY")
                
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found in environment variables")
                
                self.embeddings = OpenAIEmbeddings(
                    model=model_name,
                    openai_api_key=api_key
                )
                logger.info(f"Initialized OpenAI embedding model: {model_name}")
            else:
                # Sentence-Transformers using HuggingFace
                from langchain_huggingface import HuggingFaceEmbeddings
                
                self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
                logger.info(f"Initialized HuggingFace embedding model: {model_name}")
            
        except ImportError:
            logger.error("Required dependencies not available. Install with 'pip install langchain-community langchain-huggingface transformers sentence-transformers'")
            raise
        except Exception as e:
            logger.error(f"Error initializing embedding model: {str(e)}")
            raise
    
    # Implement embed_query using cache
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text using cache."""
        # Use the cached version of the internal method
        return self._cache_embed_query(text)

    # Internal method for uncached query embedding
    def _embed_query_uncached(self, text: str) -> List[float]:
        """
        Generate embedding for query without using cache.
        """
        if not text:
            return [0.0] * self.embedding_dim
        
        # Use the embed_query method of the underlying Langchain model
        embedding = self.embeddings.embed_query(text) 
        
        # Ensure it's a list of floats (should be, but good practice)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        return embedding
    
    # Implement embed_documents
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        Uses the embed_documents method of the underlying Langchain model.
        """
        if not texts:
             return []
        
        # Use the embed_documents method of the underlying Langchain model
        embeddings = self.embeddings.embed_documents(texts)
        
        # Ensure it's a list of lists of floats
        if embeddings and isinstance(embeddings[0], np.ndarray):
             embeddings = [e.tolist() for e in embeddings]
            
        return embeddings


class CascadingEmbeddingService(EmbeddingService):
    """
    Cascading embedding service that tries multiple services in sequence.
    If the primary service fails, it falls back to the next one.
    """
    
    def __init__(self, services: List[EmbeddingService]):
        """
        Initialize with a list of embedding services to try in order.
        
        Args:
            services: List of embedding services to try in order of preference
        """
        if not services:
            raise ValueError("At least one embedding service must be provided")
        
        super().__init__(services[0].embedding_dim)
        self.services = services
        logger.info(f"Initialized CascadingEmbeddingService with {len(services)} fallback services")
    
    def embed_query(self, text: str) -> List[float]:
        """
        Try to get embedding from each service in order until one succeeds.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        for i, service in enumerate(self.services):
            try:
                return service.embed_query(text)
            except Exception as e:
                logger.warning(f"Service {i} failed: {str(e)}")
                if i == len(self.services) - 1:
                    # This was the last service, re-raise the exception
                    raise
        
        # This should never happen if there's at least one service
        raise RuntimeError("All embedding services failed")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Try to get embeddings from each service in order until one succeeds.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of lists of floats representing the embeddings
        """
        for i, service in enumerate(self.services):
            try:
                return service.embed_documents(texts)
            except Exception as e:
                logger.warning(f"Service {i} failed for batch: {str(e)}")
                if i == len(self.services) - 1:
                    # This was the last service, re-raise the exception
                    raise
        
        # This should never happen if there's at least one service
        raise RuntimeError("All embedding services failed")


# Factory function to create the appropriate embedding service
def create_embedding_service(service_type: str = "mock", **kwargs) -> EmbeddingService:
    """
    Create an embedding service of the specified type.
    
    Args:
        service_type: Type of embedding service to create ("mock", "langchain", or "cascading")
        **kwargs: Additional arguments to pass to the embedding service constructor
            - model_name: Name of the embedding model to use (for 'langchain')
            - cache_size: Size of the LRU cache (for 'langchain')
            - embedding_dim: Dimension of the embedding vectors (for 'mock')
            - services: List of services to cascade through (for 'cascading')
        
    Returns:
        An embedding service instance
    """
    if service_type.lower() == "mock":
        return MockEmbeddingService(**kwargs)
    elif service_type.lower() == "langchain":
        return LangchainEmbeddingService(**kwargs)
    elif service_type.lower() == "cascading":
        services = kwargs.pop("services", [])
        if not services:
            # Create default cascade: try langchain first, fall back to mock
            services = [
                LangchainEmbeddingService(**kwargs),
                MockEmbeddingService(embedding_dim=kwargs.get("embedding_dim", 384))
            ]
        return CascadingEmbeddingService(services=services)
    else:
        logger.warning(f"Unknown embedding service type '{service_type}'. Defaulting to mock.")
        return MockEmbeddingService() 
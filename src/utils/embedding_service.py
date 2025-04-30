"""
Embedding Service Utility

This module provides utilities for generating vector embeddings from text.
It supports multiple embedding services including local models and API-based ones.
"""

import os
import numpy as np
import logging
import hashlib
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

    # Add necessary methods from Langchain Embeddings interface
    # These might be needed if the service is passed directly to Langchain components
    # that expect these methods.
    def __call__(self, text: str) -> List[float]:
        return self.embed_query(text)


class LangchainEmbeddingService(EmbeddingService):
    """
    Embedding service that uses LangChain's embedding models.
    This provides an interface to various embedding services through LangChain.
    """
    
    def __init__(self, 
                 model_provider: str = 'openai', # Default or specify (openai, ollama, sentence_transformer)
                 model_name: Optional[str] = None, 
                 cache_dir: str = './cache/embeddings', 
                 cache_size: int = 1000, 
                 **kwargs):
        
        self.model_provider = model_provider.lower()
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.cache_size = cache_size # Note: Cache size might not be directly applicable to all stores
        self.kwargs = kwargs
        
        # --- Dynamic Imports ---
        try:
            from langchain.embeddings import CacheBackedEmbeddings
            from langchain.storage import LocalFileStore
        except ImportError:
            logger.error("Langchain or required storage components not installed. Please install langchain, langchain-community, langchain-openai etc.")
            raise
        # --- End Dynamic Imports ---
        
        # Initialize the underlying embedding model
        underlying_embedder = self._initialize_underlying_embedder()
        
        # Determine embedding dimension (crucial for base class)
        # This often requires a trial embedding or checking model metadata if available
        try:
            # Attempt to get dimension from the underlying model if attribute exists
            if hasattr(underlying_embedder, 'client') and hasattr(underlying_embedder.client, 'dimensions'):
                 _embedding_dim = underlying_embedder.client.dimensions
            elif hasattr(underlying_embedder, 'embedding_dim'): # Some models might have it directly
                 _embedding_dim = underlying_embedder.embedding_dim
            else:
                # Fallback: embed a dummy text to find dimension
                logger.warning("Could not directly determine embedding dimension. Performing trial embedding.")
                dummy_embedding = underlying_embedder.embed_query("dimension_check")
                _embedding_dim = len(dummy_embedding)
            logger.info(f"Determined embedding dimension: {_embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to determine embedding dimension: {e}", exc_info=True)
            raise ValueError("Could not determine embedding dimension for the selected model.") from e
            
        # Initialize the base class with the determined dimension
        super().__init__(embedding_dim=_embedding_dim)
        
        # --- Setup Cache --- 
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize the cache store
        # Note: LocalFileStore doesn't have a size limit; cache management is manual or based on access time
        store = LocalFileStore(self.cache_dir)
        
        # Initialize the cached embedder
        self.cached_embedder = CacheBackedEmbeddings.from_bytes_store(
            underlying_embedder,
            store,
            namespace=f"{self.model_provider}_{self.model_name or 'default'}" # Use model details for namespace
        )
        # --- End Cache Setup ---

    def _initialize_underlying_embedder(self):
        """Initialize the specific Langchain embedder based on provider."""
        logger.info(f"Initializing underlying embedder: provider={self.model_provider}, model={self.model_name}")
        if self.model_provider == 'openai':
            try:
                from langchain_openai import OpenAIEmbeddings
                # Pass model_name if provided, otherwise let Langchain use its default
                return OpenAIEmbeddings(model=self.model_name) if self.model_name else OpenAIEmbeddings()
            except ImportError:
                logger.error("langchain-openai not installed. Run 'pip install langchain-openai'")
                raise
        elif self.model_provider == 'ollama':
            try:
                from langchain_community.embeddings import OllamaEmbeddings
                # Pass model_name if provided, otherwise let Langchain use its default
                # Check Ollama documentation for relevant kwargs
                return OllamaEmbeddings(model=self.model_name) if self.model_name else OllamaEmbeddings()
            except ImportError:
                logger.error("langchain-community (for Ollama) not installed. Run 'pip install langchain-community'")
                raise
        elif self.model_provider == 'sentence_transformer' or self.model_provider == 'huggingface':
            try:
                from langchain_community.embeddings import SentenceTransformerEmbeddings
                # Default to a common SentenceTransformer model if none specified
                model_name_to_use = self.model_name or 'all-MiniLM-L6-v2' 
                logger.info(f"Using SentenceTransformer model: {model_name_to_use}")
                # Check SentenceTransformerEmbeddings documentation for relevant kwargs (e.g., device)
                return SentenceTransformerEmbeddings(model_name=model_name_to_use, **self.kwargs)
            except ImportError:
                 logger.error("langchain-community and sentence-transformers not installed. Run 'pip install langchain-community sentence-transformers'")
                 raise
        else:
            raise ValueError(f"Unsupported embedding model provider: {self.model_provider}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs using the cached embedder."""
        logger.debug(f"Embedding {len(texts)} documents...")
        embeddings = self.cached_embedder.embed_documents(texts)
        logger.debug("Document embedding complete.")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed query text using the cached embedder."""
        logger.debug("Embedding query...")
        embedding = self.cached_embedder.embed_query(text)
        logger.debug("Query embedding complete.")
        return embedding


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
def create_embedding_service(service_type: str = 'langchain', **kwargs) -> EmbeddingService:
    """
    Create an embedding service of the specified type.
    
    Args:
        service_type: Type of embedding service to create ("langchain", or "cascading")
        **kwargs: Additional arguments to pass to the embedding service constructor
            - model_provider: Provider of the embedding model (for 'langchain')
            - model_name: Name of the embedding model to use (for 'langchain')
            - cache_dir: Directory for caching embeddings (for 'langchain')
            - cache_size: Size of the LRU cache (for 'langchain')
            - services: List of services to cascade through (for 'cascading')
        
    Returns:
        An embedding service instance
    """
    service_type = service_type.lower()
    logger.info(f"Creating embedding service of type: {service_type}")
    
    if service_type == 'langchain':
        # Extract relevant kwargs for LangchainEmbeddingService
        # Default provider can be set here or based on environment
        provider = kwargs.get('model_provider', os.getenv('EMBEDDING_PROVIDER', 'sentence_transformer'))
        model = kwargs.get('model_name', os.getenv('EMBEDDING_MODEL_NAME'))
        cache_dir = kwargs.get('cache_dir', os.getenv('EMBEDDING_CACHE_DIR', './cache/embeddings'))
        cache_size = kwargs.get('cache_size', int(os.getenv('EMBEDDING_CACHE_SIZE', 1000)))
        
        # Prepare remaining kwargs, removing the ones explicitly handled
        remaining_kwargs = kwargs.copy()
        remaining_kwargs.pop('model_provider', None)
        remaining_kwargs.pop('model_name', None)
        remaining_kwargs.pop('cache_dir', None)
        remaining_kwargs.pop('cache_size', None)
        
        logger.info(f"Creating LangchainEmbeddingService: provider={provider}, model={model}, cache={cache_dir}")
        
        return LangchainEmbeddingService(
            model_provider=provider,
            model_name=model,
            cache_dir=cache_dir,
            cache_size=cache_size,
            # Pass only the *remaining* kwargs
            **remaining_kwargs 
        )
    elif service_type == 'cascading':
        services = kwargs.pop("services", [])
        if not services:
            # Create default cascade: try langchain first, fall back to mock
            # Ensure base EmbeddingService is used for fallback if needed, 
            # or raise error if cascade requires multiple functional services.
            # For now, assume LangchainEmbeddingService is the primary.
            default_kwargs = kwargs.copy() # Use remaining kwargs for default Langchain
            services = [
                LangchainEmbeddingService(**default_kwargs),
                # Consider if a *simple* base EmbeddingService as fallback makes sense,
                # or if cascading implies multiple *functional* services are expected.
                # Using a base EmbeddingService here might hide errors if Langchain fails.
                # Let's assume cascading implies multiple *configured* services passed in.
                # Raising an error if services list is empty might be better.
                 # EmbeddingService(embedding_dim=kwargs.get("embedding_dim", 384))
            ]
            if not services[0]: # Check if default Langchain could be created
                 raise ValueError("Cascading service requires at least one functional service configuration.")
        return CascadingEmbeddingService(services=services)
    else:
        raise ValueError(f"Unsupported embedding service type: {service_type}") 
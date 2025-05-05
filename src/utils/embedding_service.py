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
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from functools import lru_cache
from langchain_core.embeddings import Embeddings

# Local imports
from src.data_models import PolarTemporalCoordinate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EmbeddingService')

# Base class for embedding services - Inherit from Langchain's base
class EmbeddingService(Embeddings): # Inherit from langchain_core.embeddings.Embeddings
    """Base class for all embedding services, conforming to Langchain's Embeddings interface."""
    
    def __init__(self, embedding_dim: int = 384, store_polar_coords: bool = True):
        """
        Initialize the embedding service.
        
        Args:
            embedding_dim: Dimension of the embedding vectors
            store_polar_coords: Whether to store polar coordinate representations
        """
        self.embedding_dim = embedding_dim
        self.store_polar_coords = store_polar_coords
        self.embedding_to_coords_cache = {}  # Cache mapping from embedding hash to coordinates
    
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
        
    def _hash_embedding(self, embedding: np.ndarray) -> str:
        """
        Create a stable hash representation of an embedding for caching.
        
        Args:
            embedding: The vector embedding to hash
            
        Returns:
            A hash string that uniquely identifies this embedding
        """
        # Convert embedding to bytes through a specific representation
        embedding_bytes = embedding.tobytes()
        
        # Create hash
        hash_obj = hashlib.sha256(embedding_bytes)
        return hash_obj.hexdigest()
        
    def store_coordinate_for_embedding(self, 
                                      embedding: np.ndarray, 
                                      coordinate: PolarTemporalCoordinate) -> None:
        """
        Store the polar-temporal coordinate representation for an embedding.
        
        Args:
            embedding: The vector embedding
            coordinate: The corresponding polar-temporal coordinate
        """
        if not self.store_polar_coords:
            return
            
        embedding_hash = self._hash_embedding(embedding)
        self.embedding_to_coords_cache[embedding_hash] = coordinate.to_dict()
        logger.debug(f"Stored polar coordinate for embedding: r={coordinate.r:.4f}, theta={coordinate.theta:.4f}")
        
    def get_coordinate_for_embedding(self, 
                                   embedding: np.ndarray) -> Optional[PolarTemporalCoordinate]:
        """
        Retrieve the polar-temporal coordinate for a given embedding, if it exists in cache.
        
        Args:
            embedding: The vector embedding to retrieve coordinates for
            
        Returns:
            The cached PolarTemporalCoordinate object or None if not found
        """
        if not self.store_polar_coords:
            return None
            
        embedding_hash = self._hash_embedding(embedding)
        coord_dict = self.embedding_to_coords_cache.get(embedding_hash)
        
        if coord_dict:
            logger.debug(f"Found cached polar coordinate for embedding hash: {embedding_hash[:8]}")
            return PolarTemporalCoordinate.from_dict(coord_dict)
        
        return None
        
    def embed_with_coordinates(self, 
                             text: str,
                             coordinate_mapper=None,
                             metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[float], Optional[PolarTemporalCoordinate]]:
        """
        Generate both an embedding and its polar-temporal coordinate representation.
        
        Args:
            text: Text to embed
            coordinate_mapper: CoordinateMapper instance to use (required if coords not in cache)
            metadata: Metadata needed for coordinate transformation
            
        Returns:
            Tuple of (embedding, polar_coordinate) where coordinate may be None if mapping fails
        """
        # Get the embedding first
        embedding_list = self.embed_query(text)
        embedding_array = np.array(embedding_list)
        
        # Check cache first
        coordinate = self.get_coordinate_for_embedding(embedding_array)
        
        # If not in cache and we have a coordinate mapper, generate and store
        if coordinate is None and coordinate_mapper is not None:
            try:
                if metadata is None:
                    metadata = {}  # Use empty dict as fallback
                
                # Use the mapper to transform the embedding to coordinates
                coordinate = coordinate_mapper.transform_vector_to_polar_temporal(
                    embedding=embedding_array, 
                    metadata=metadata
                )
                
                # Cache the result
                self.store_coordinate_for_embedding(embedding_array, coordinate)
                logger.debug(f"Generated new polar coordinate for text: r={coordinate.r:.4f}, theta={coordinate.theta:.4f}")
            except Exception as e:
                logger.error(f"Failed to transform embedding to coordinates: {e}")
                # Return raw embedding but no coordinate
                return embedding_list, None
        
        return embedding_list, coordinate
        
    def save_coordinate_cache(self, cache_file: str) -> bool:
        """
        Save the coordinate cache to a file.
        
        Args:
            cache_file: Path to save the cache
            
        Returns:
            True if successful, False otherwise
        """
        if not self.store_polar_coords or not self.embedding_to_coords_cache:
            logger.warning("No coordinate cache to save or caching disabled")
            return False
            
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.embedding_to_coords_cache, f)
            logger.info(f"Saved coordinate cache with {len(self.embedding_to_coords_cache)} entries to {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save coordinate cache: {e}")
            return False
            
    def load_coordinate_cache(self, cache_file: str) -> bool:
        """
        Load the coordinate cache from a file.
        
        Args:
            cache_file: Path to load the cache from
            
        Returns:
            True if successful, False otherwise
        """
        if not self.store_polar_coords:
            logger.warning("Coordinate caching is disabled, not loading cache file")
            return False
            
        if not os.path.exists(cache_file):
            logger.warning(f"Coordinate cache file not found: {cache_file}")
            return False
            
        try:
            with open(cache_file, 'r') as f:
                self.embedding_to_coords_cache = json.load(f)
            logger.info(f"Loaded coordinate cache with {len(self.embedding_to_coords_cache)} entries from {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load coordinate cache: {e}")
            self.embedding_to_coords_cache = {}  # Reset on error
            return False


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
                 store_polar_coords: bool = True,
                 polar_coords_cache_file: Optional[str] = None,
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
        super().__init__(embedding_dim=_embedding_dim, store_polar_coords=store_polar_coords)
        
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
        
        # Load coordinate cache if specified
        if polar_coords_cache_file:
            self.load_coordinate_cache(polar_coords_cache_file)

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
        
    def embed_documents_with_coordinates(self, 
                                       texts: List[str],
                                       coordinate_mapper=None,
                                       metadata: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None) -> List[Tuple[List[float], Optional[PolarTemporalCoordinate]]]:
        """
        Generate both embeddings and their polar-temporal coordinate representations for multiple texts.
        
        Args:
            texts: List of texts to embed
            coordinate_mapper: CoordinateMapper instance to use
            metadata: Either a single metadata dict to use for all texts, or a list of metadata dicts
            
        Returns:
            List of tuples (embedding, polar_coordinate) where coordinate may be None if mapping fails
        """
        # Get embeddings first
        embedding_lists = self.embed_documents(texts)
        results = []
        
        # Process each embedding
        for i, emb_list in enumerate(embedding_lists):
            embedding_array = np.array(emb_list)
            
            # Check cache first
            coordinate = self.get_coordinate_for_embedding(embedding_array)
            
            # If not in cache and we have a coordinate mapper, generate and store
            if coordinate is None and coordinate_mapper is not None:
                try:
                    # Determine which metadata to use
                    meta = {}
                    if isinstance(metadata, list) and i < len(metadata):
                        meta = metadata[i]
                    elif isinstance(metadata, dict):
                        meta = metadata
                    
                    # Use the mapper to transform the embedding to coordinates
                    coordinate = coordinate_mapper.transform_vector_to_polar_temporal(
                        embedding=embedding_array, 
                        metadata=meta
                    )
                    
                    # Cache the result
                    self.store_coordinate_for_embedding(embedding_array, coordinate)
                except Exception as e:
                    logger.error(f"Failed to transform embedding to coordinates for text {i}: {e}")
                    # No coordinate for this embedding
                    coordinate = None
            
            results.append((emb_list, coordinate))
        
        return results


class CascadingEmbeddingService(EmbeddingService):
    """
    Cascading embedding service that tries multiple services in sequence.
    If the primary service fails, it falls back to the next one.
    """
    
    def __init__(self, services: List[EmbeddingService], store_polar_coords: bool = True):
        """
        Initialize with a list of embedding services to try in order.
        
        Args:
            services: List of embedding services to try in order of preference
            store_polar_coords: Whether to store polar coordinate representations
        """
        if not services:
            raise ValueError("At least one embedding service must be provided")
        
        super().__init__(services[0].embedding_dim, store_polar_coords=store_polar_coords)
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
            - store_polar_coords: Whether to store polar coordinate representations
            - polar_coords_cache_file: File to load/save polar coordinate cache
            - services: List of services to cascade through (for 'cascading')
        
    Returns:
        An embedding service instance
    """
    service_type = service_type.lower()
    logger.info(f"Creating embedding service of type: {service_type}")
    
    # Extract polar coordinate settings
    store_polar_coords = kwargs.pop('store_polar_coords', 
                                   bool(os.getenv('STORE_POLAR_COORDS', 'True').lower() == 'true'))
    polar_coords_cache_file = kwargs.pop('polar_coords_cache_file', 
                                        os.getenv('POLAR_COORDS_CACHE_FILE'))
    
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
            store_polar_coords=store_polar_coords,
            polar_coords_cache_file=polar_coords_cache_file,
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
                LangchainEmbeddingService(
                    store_polar_coords=store_polar_coords,
                    polar_coords_cache_file=polar_coords_cache_file,
                    **default_kwargs
                ),
                # Consider if a *simple* base EmbeddingService as fallback makes sense,
                # or if cascading implies multiple *functional* services are expected.
                # Using a base EmbeddingService here might hide errors if Langchain fails.
                # Let's assume cascading implies multiple *configured* services passed in.
                # Raising an error if services list is empty might be better.
                 # EmbeddingService(embedding_dim=kwargs.get("embedding_dim", 384))
            ]
            if not services[0]: # Check if default Langchain could be created
                 raise ValueError("Cascading service requires at least one functional service configuration.")
        return CascadingEmbeddingService(services=services, store_polar_coords=store_polar_coords)
    else:
        raise ValueError(f"Unsupported embedding service type: {service_type}") 
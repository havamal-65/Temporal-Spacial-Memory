"""
Dimension Reducer Utility

This module provides utilities for reducing the dimensionality of vector embeddings
to optimize storage while preserving the semantic structure.
"""

import numpy as np
import logging
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.random_projection import GaussianRandomProjection
from sklearn.manifold import TSNE
import umap
import joblib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DimensionReducer')

class DimensionReducer:
    """
    Utility for reducing embedding dimensions while preserving semantic structure.
    Supports multiple reduction techniques and can be saved/loaded.
    """
    
    SUPPORTED_METHODS = ['pca', 'truncated_svd', 'random_projection', 'tsne', 'umap']
    
    def __init__(self, 
                method: str = 'pca', 
                target_dim: int = 50,
                random_state: int = 42,
                **kwargs):
        """
        Initialize the dimension reducer.
        
        Args:
            method: Reduction method ('pca', 'truncated_svd', 'random_projection', 'tsne', 'umap')
            target_dim: Target dimensionality after reduction
            random_state: Random seed for reproducibility
            **kwargs: Additional arguments for the specific reduction method
        """
        self.method = method.lower()
        self.target_dim = target_dim
        self.random_state = random_state
        self.kwargs = kwargs
        self.reducer = None
        self.is_fitted = False
        
        if self.method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported dimension reduction method: {method}. "
                           f"Supported methods: {', '.join(self.SUPPORTED_METHODS)}")
        
        self._initialize_reducer()
        
    def _initialize_reducer(self):
        """Initialize the appropriate reducer based on the selected method."""
        if self.method == 'pca':
            self.reducer = PCA(
                n_components=self.target_dim,
                random_state=self.random_state,
                **{k: v for k, v in self.kwargs.items() if k in ['svd_solver', 'tol', 'iterated_power']}
            )
        elif self.method == 'truncated_svd':
            self.reducer = TruncatedSVD(
                n_components=self.target_dim,
                random_state=self.random_state,
                **{k: v for k, v in self.kwargs.items() if k in ['algorithm', 'tol', 'n_iter']}
            )
        elif self.method == 'random_projection':
            self.reducer = GaussianRandomProjection(
                n_components=self.target_dim,
                random_state=self.random_state,
                **{k: v for k, v in self.kwargs.items() if k in ['eps']}
            )
        elif self.method == 'tsne':
            self.reducer = TSNE(
                n_components=self.target_dim,
                random_state=self.random_state,
                **{k: v for k, v in self.kwargs.items() 
                   if k in ['perplexity', 'early_exaggeration', 'learning_rate', 'n_iter']}
            )
        elif self.method == 'umap':
            try:
                self.reducer = umap.UMAP(
                    n_components=self.target_dim,
                    random_state=self.random_state,
                    **{k: v for k, v in self.kwargs.items() 
                       if k in ['n_neighbors', 'min_dist', 'metric', 'spread']}
                )
            except ImportError:
                logger.error("UMAP not installed. Please install with 'pip install umap-learn'")
                raise
    
    def fit(self, embeddings: np.ndarray) -> 'DimensionReducer':
        """
        Fit the dimension reducer to a set of embeddings.
        
        Args:
            embeddings: Array of shape (n_samples, n_features) containing the embeddings
            
        Returns:
            Self for method chaining
        """
        if embeddings.ndim != 2:
            raise ValueError(f"Expected 2D array of embeddings, got shape {embeddings.shape}")
            
        logger.info(f"Fitting {self.method} dimension reducer to {embeddings.shape[0]} embeddings "
                   f"from {embeddings.shape[1]} to {self.target_dim} dimensions")
        
        try:
            self.reducer.fit(embeddings)
            self.is_fitted = True
            logger.info(f"Successfully fitted {self.method} dimension reducer")
            
            # Log explained variance if available
            if hasattr(self.reducer, 'explained_variance_ratio_'):
                total_variance = sum(self.reducer.explained_variance_ratio_)
                logger.info(f"Explained variance: {total_variance:.4f}")
                
            return self
        except Exception as e:
            logger.error(f"Error fitting {self.method} dimension reducer: {e}")
            raise
    
    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Transform embeddings to lower dimension.
        
        Args:
            embeddings: Array of shape (n_samples, n_features) containing the embeddings
            
        Returns:
            Array of shape (n_samples, target_dim) containing the reduced embeddings
        """
        if not self.is_fitted:
            raise ValueError(f"{self.method} dimension reducer not fitted yet")
            
        if embeddings.ndim != 2:
            raise ValueError(f"Expected 2D array of embeddings, got shape {embeddings.shape}")
            
        logger.debug(f"Transforming {embeddings.shape[0]} embeddings from {embeddings.shape[1]} to {self.target_dim} dimensions")
        
        try:
            return self.reducer.transform(embeddings)
        except Exception as e:
            logger.error(f"Error transforming embeddings with {self.method}: {e}")
            raise
    
    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Fit the dimension reducer and transform embeddings in one operation.
        
        Args:
            embeddings: Array of shape (n_samples, n_features) containing the embeddings
            
        Returns:
            Array of shape (n_samples, target_dim) containing the reduced embeddings
        """
        logger.info(f"Fitting and transforming {embeddings.shape[0]} embeddings "
                   f"from {embeddings.shape[1]} to {self.target_dim} dimensions")
        
        try:
            reduced = self.reducer.fit_transform(embeddings)
            self.is_fitted = True
            
            # Log explained variance if available
            if hasattr(self.reducer, 'explained_variance_ratio_'):
                total_variance = sum(self.reducer.explained_variance_ratio_)
                logger.info(f"Explained variance: {total_variance:.4f}")
                
            return reduced
        except Exception as e:
            logger.error(f"Error fitting and transforming with {self.method}: {e}")
            raise
    
    def inverse_transform(self, reduced_embeddings: np.ndarray) -> Optional[np.ndarray]:
        """
        Transform reduced embeddings back to original dimension.
        Only available for certain methods (PCA, TruncatedSVD).
        
        Args:
            reduced_embeddings: Array of shape (n_samples, target_dim) containing reduced embeddings
            
        Returns:
            Array of shape (n_samples, original_dim) containing reconstructed embeddings,
            or None if inverse transform is not available for this method
        """
        if not self.is_fitted:
            raise ValueError(f"{self.method} dimension reducer not fitted yet")
            
        if self.method not in ['pca', 'truncated_svd']:
            logger.warning(f"Inverse transform not available for {self.method}")
            return None
            
        logger.debug(f"Inverse transforming {reduced_embeddings.shape[0]} embeddings")
        
        try:
            return self.reducer.inverse_transform(reduced_embeddings)
        except Exception as e:
            logger.error(f"Error inverse transforming embeddings with {self.method}: {e}")
            raise
    
    def save(self, filepath: str) -> bool:
        """
        Save the fitted dimension reducer to a file.
        
        Args:
            filepath: Path to save the reducer
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_fitted:
            logger.warning(f"Saving unfitted {self.method} dimension reducer")
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            joblib.dump(self.reducer, filepath)
            logger.info(f"Saved {self.method} dimension reducer to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving {self.method} dimension reducer: {e}")
            return False
    
    @classmethod
    def load(cls, filepath: str, method: str = None) -> 'DimensionReducer':
        """
        Load a fitted dimension reducer from a file.
        
        Args:
            filepath: Path to load the reducer from
            method: Reducer method (optional, for initialization only)
            
        Returns:
            Loaded DimensionReducer instance
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dimension reducer file not found: {filepath}")
            
        try:
            reducer_model = joblib.load(filepath)
            
            # Determine method from the loaded model if not provided
            if method is None:
                if isinstance(reducer_model, PCA):
                    method = 'pca'
                elif isinstance(reducer_model, TruncatedSVD):
                    method = 'truncated_svd'
                elif isinstance(reducer_model, GaussianRandomProjection):
                    method = 'random_projection'
                elif isinstance(reducer_model, TSNE):
                    method = 'tsne'
                elif hasattr(reducer_model, '__class__') and 'UMAP' in reducer_model.__class__.__name__:
                    method = 'umap'
                else:
                    raise ValueError(f"Unknown reducer type: {type(reducer_model)}")
            
            # Create instance and set attributes
            target_dim = reducer_model.n_components
            instance = cls(method=method, target_dim=target_dim)
            instance.reducer = reducer_model
            instance.is_fitted = True
            
            logger.info(f"Loaded {method} dimension reducer from {filepath}")
            return instance
        except Exception as e:
            logger.error(f"Error loading dimension reducer: {e}")
            raise

def create_dimension_reducer(method: str = 'pca', 
                          target_dim: int = 50, 
                          random_state: int = 42,
                          **kwargs) -> DimensionReducer:
    """
    Factory function to create a dimension reducer.
    
    Args:
        method: Reduction method ('pca', 'truncated_svd', 'random_projection', 'tsne', 'umap')
        target_dim: Target dimensionality after reduction
        random_state: Random seed for reproducibility
        **kwargs: Additional arguments for the specific reduction method
        
    Returns:
        A DimensionReducer instance
    """
    # Get values from environment if available
    env_method = os.getenv('DIMENSION_REDUCTION_METHOD')
    env_target_dim = os.getenv('DIMENSION_REDUCTION_TARGET_DIM')
    env_random_state = os.getenv('DIMENSION_REDUCTION_RANDOM_STATE')
    
    # Use environment values if provided
    if env_method:
        method = env_method
    if env_target_dim:
        target_dim = int(env_target_dim)
    if env_random_state:
        random_state = int(env_random_state)
    
    return DimensionReducer(
        method=method,
        target_dim=target_dim,
        random_state=random_state,
        **kwargs
    ) 
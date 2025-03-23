"""
Client-side caching for the database client.

This module provides a caching system to reduce network requests
and improve performance for frequently accessed data.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Generic, TypeVar, Callable, Tuple
from datetime import datetime, timedelta
import logging
import weakref
from uuid import UUID
import copy
import hashlib
import json

from ..core.node_v2 import Node
from .config import CacheConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type variable for cache entries


class CacheEntry(Generic[T]):
    """Represents a cached item with metadata."""
    
    def __init__(self, key: str, value: T, ttl: timedelta):
        """
        Initialize a cache entry.
        
        Args:
            key: Cache key
            value: Cached value
            ttl: Time-to-live for this entry
        """
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.last_accessed = self.created_at
        self.expires_at = self.created_at + ttl
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """
        Check if the entry is expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.now() > self.expires_at
    
    def access(self) -> None:
        """Record an access to this entry."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def needs_refresh(self, refresh_ahead_time: timedelta) -> bool:
        """
        Check if the entry needs refreshing soon.
        
        Args:
            refresh_ahead_time: How long before expiry to refresh
            
        Returns:
            True if the entry should be refreshed, False otherwise
        """
        return datetime.now() > (self.expires_at - refresh_ahead_time)
    
    def extend_ttl(self, ttl: timedelta) -> None:
        """
        Extend the time-to-live of this entry.
        
        Args:
            ttl: Additional time-to-live to add
        """
        self.expires_at = datetime.now() + ttl


class ClientCache:
    """
    Client-side cache for database operations.
    
    This cache reduces network requests by storing frequently accessed
    data locally, with automatic expiry and refresh capabilities.
    """
    
    def __init__(self, config: CacheConfig):
        """
        Initialize the client cache.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.enabled = config.enabled
        
        # Main cache storage: key -> CacheEntry
        self.cache: Dict[str, CacheEntry] = {}
        
        # Query result cache: query_hash -> list of node ids
        self.query_cache: Dict[str, CacheEntry[List[UUID]]] = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Refresh registry (to avoid duplicate refreshes)
        self.refreshing: Set[str] = set()
        
        # Background refresh thread
        self.refresh_thread = None
        self.refresh_stop_event = threading.Event()
        
        # Start maintenance thread
        if self.enabled:
            self._start_refresh_thread()
    
    def _start_refresh_thread(self) -> None:
        """Start the background refresh thread."""
        if self.refresh_thread is None and self.config.refresh_ahead:
            self.refresh_stop_event.clear()
            self.refresh_thread = threading.Thread(
                target=self._refresh_loop,
                daemon=True,
                name="ClientCache-Refresh"
            )
            self.refresh_thread.start()
            logger.debug("Started cache refresh thread")
    
    def _refresh_loop(self) -> None:
        """Background refresh loop."""
        while not self.refresh_stop_event.is_set():
            # Sleep for a bit
            self.refresh_stop_event.wait(30)  # Check every 30 seconds
            
            if not self.refresh_stop_event.is_set():
                try:
                    self._cleanup_expired()
                    if self.config.refresh_ahead:
                        self._refresh_soon_to_expire()
                except Exception as e:
                    logger.error(f"Error in cache refresh: {e}")
    
    def _cleanup_expired(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self.lock:
            now = datetime.now()
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            expired_query_keys = [k for k, v in self.query_cache.items() if v.is_expired()]
            
            # Remove expired entries
            for key in expired_keys:
                del self.cache[key]
            
            for key in expired_query_keys:
                del self.query_cache[key]
            
            return len(expired_keys) + len(expired_query_keys)
    
    def _refresh_soon_to_expire(self) -> None:
        """Identify and refresh entries that will expire soon."""
        # This is a placeholder - actual implementation would need a callback
        # mechanism to refresh entries, which would depend on the client implementation
        pass
    
    def make_key(self, *args: Any, **kwargs: Any) -> str:
        """
        Create a cache key from arguments.
        
        Args:
            *args: Positional arguments to include in the key
            **kwargs: Keyword arguments to include in the key
            
        Returns:
            A string key
        """
        # Convert args and kwargs to string representation
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
        
        # Create a hash of the combined string
        key_str = f"{args_str}|{kwargs_str}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def hash_query(self, query: Any) -> str:
        """
        Create a hash for a query.
        
        Args:
            query: The query to hash
            
        Returns:
            A hash string representing the query
        """
        # Convert query to a string representation
        # This is a simplified implementation - a real implementation would
        # need to handle different query types and ensure consistent hashing
        query_str = str(query)
        return hashlib.md5(query_str.encode('utf-8')).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value if found and not expired, None otherwise
        """
        if not self.enabled:
            return None
        
        with self.lock:
            entry = self.cache.get(key)
            
            if entry and not entry.is_expired():
                # Record access
                entry.access()
                
                # Return a copy to avoid modifying the cached value
                return copy.deepcopy(entry.value)
            
            # Entry not found or expired
            if entry:
                # Remove expired entry
                del self.cache[key]
            
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Put a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL, defaults to configured TTL
        """
        if not self.enabled:
            return
        
        with self.lock:
            # Check cache size limits
            if len(self.cache) >= self.config.max_items:
                self._evict_items()
            
            # Use configured TTL if not specified
            if ttl is None:
                ttl = self.config.ttl
            
            # Create and store entry
            self.cache[key] = CacheEntry(key, copy.deepcopy(value), ttl)
    
    def cache_query_result(self, query_hash: str, node_ids: List[UUID]) -> None:
        """
        Cache the results of a query.
        
        Args:
            query_hash: Hash of the query
            node_ids: List of node IDs in the result
        """
        if not self.enabled:
            return
        
        with self.lock:
            # Check cache size limits
            if len(self.query_cache) >= self.config.max_items:
                self._evict_query_items()
            
            # Create and store entry
            self.query_cache[query_hash] = CacheEntry(query_hash, node_ids, self.config.ttl)
    
    def get_query_result(self, query_hash: str) -> Optional[List[UUID]]:
        """
        Get cached query results.
        
        Args:
            query_hash: Hash of the query
            
        Returns:
            List of node IDs if found and not expired, None otherwise
        """
        if not self.enabled:
            return None
        
        with self.lock:
            entry = self.query_cache.get(query_hash)
            
            if entry and not entry.is_expired():
                # Record access
                entry.access()
                
                # Return a copy of the node IDs
                return entry.value.copy()
            
            # Entry not found or expired
            if entry:
                # Remove expired entry
                del self.query_cache[query_hash]
            
            return None
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if an entry was invalidated, False otherwise
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def invalidate_query(self, query_hash: str) -> bool:
        """
        Invalidate a cached query result.
        
        Args:
            query_hash: Query hash to invalidate
            
        Returns:
            True if an entry was invalidated, False otherwise
        """
        with self.lock:
            if query_hash in self.query_cache:
                del self.query_cache[query_hash]
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match against keys
            
        Returns:
            Number of entries invalidated
        """
        import re
        regex = re.compile(pattern)
        
        with self.lock:
            # Find matching keys
            matching_keys = [k for k in self.cache.keys() if regex.search(k)]
            matching_query_keys = [k for k in self.query_cache.keys() if regex.search(k)]
            
            # Remove matching entries
            for key in matching_keys:
                del self.cache[key]
            
            for key in matching_query_keys:
                del self.query_cache[key]
            
            return len(matching_keys) + len(matching_query_keys)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            self.cache.clear()
            self.query_cache.clear()
    
    def _evict_items(self) -> int:
        """
        Evict items from the cache when it's full.
        
        Returns:
            Number of items evicted
        """
        with self.lock:
            # Sort by last accessed (oldest first)
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest 25% of items
            to_remove = max(1, len(self.cache) // 4)
            for i in range(to_remove):
                if i < len(sorted_items):
                    key, _ = sorted_items[i]
                    if key in self.cache:
                        del self.cache[key]
            
            return to_remove
    
    def _evict_query_items(self) -> int:
        """
        Evict query items from the cache when it's full.
        
        Returns:
            Number of items evicted
        """
        with self.lock:
            # Sort by last accessed (oldest first)
            sorted_items = sorted(
                self.query_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest 25% of items
            to_remove = max(1, len(self.query_cache) // 4)
            for i in range(to_remove):
                if i < len(sorted_items):
                    key, _ = sorted_items[i]
                    if key in self.query_cache:
                        del self.query_cache[key]
            
            return to_remove
    
    def size(self) -> Tuple[int, int]:
        """
        Get the current size of the cache.
        
        Returns:
            Tuple of (node_cache_size, query_cache_size)
        """
        with self.lock:
            return len(self.cache), len(self.query_cache)
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self.lock:
            node_cache_size = len(self.cache)
            query_cache_size = len(self.query_cache)
            
            # Calculate average age
            now = datetime.now()
            node_avg_age = 0.0
            query_avg_age = 0.0
            
            if node_cache_size > 0:
                node_avg_age = sum((now - entry.created_at).total_seconds() 
                                  for entry in self.cache.values()) / node_cache_size
            
            if query_cache_size > 0:
                query_avg_age = sum((now - entry.created_at).total_seconds() 
                                   for entry in self.query_cache.values()) / query_cache_size
            
            return {
                "node_cache_size": node_cache_size,
                "query_cache_size": query_cache_size,
                "node_avg_age_seconds": node_avg_age,
                "query_avg_age_seconds": query_avg_age,
                "enabled": self.enabled,
                "max_items": self.config.max_items,
                "ttl_seconds": self.config.ttl.total_seconds(),
                "refresh_ahead": self.config.refresh_ahead,
            }
    
    def close(self) -> None:
        """Stop background threads and clean up resources."""
        # Stop refresh thread
        if self.refresh_thread is not None:
            self.refresh_stop_event.set()
            self.refresh_thread.join(timeout=2.0)
            self.refresh_thread = None
        
        # Clear cache
        with self.lock:
            self.cache.clear()
            self.query_cache.clear()


def cached(ttl: Optional[timedelta] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Optional time-to-live for cached results
        
    Returns:
        Decorated function
    """
    def decorator(func):
        cache_dict = {}
        cache_lock = threading.RLock()
        
        def clear_cache():
            with cache_lock:
                cache_dict.clear()
        
        func.clear_cache = clear_cache
        
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            
            cache_key = hashlib.md5("_".join(key_parts).encode('utf-8')).hexdigest()
            
            with cache_lock:
                # Check if result is cached
                if cache_key in cache_dict:
                    entry = cache_dict[cache_key]
                    if not entry.is_expired():
                        entry.access()
                        return copy.deepcopy(entry.value)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                effective_ttl = ttl if ttl is not None else timedelta(minutes=5)
                cache_dict[cache_key] = CacheEntry(cache_key, copy.deepcopy(result), effective_ttl)
                
                return result
        
        return wrapper
    
    return decorator 
"""
Client configuration system.

This module provides configuration options for the database client,
allowing customization of connection settings, caching, and retries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_attempts: int = 3
    """Maximum number of retry attempts."""
    
    base_delay: float = 1.0
    """Base delay between retries in seconds."""
    
    max_delay: float = 30.0
    """Maximum delay between retries in seconds."""
    
    backoff_factor: float = 2.0
    """Exponential backoff factor."""
    
    retry_on_exceptions: List[str] = field(default_factory=lambda: [
        "ConnectionError", "Timeout", "ServerError"
    ])
    """List of exception types to retry on."""


@dataclass
class ConnectionConfig:
    """Configuration for database connections."""
    
    url: str = "localhost:8000"
    """Database server URL."""
    
    api_key: Optional[str] = None
    """API key for authentication."""
    
    timeout: float = 30.0
    """Connection timeout in seconds."""
    
    min_connections: int = 2
    """Minimum number of connections to maintain in the pool."""
    
    max_connections: int = 10
    """Maximum number of connections in the pool."""
    
    max_age: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    """Maximum age of a connection before recycling."""
    
    idle_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    """Maximum idle time before recycling a connection."""
    
    ssl_verify: bool = True
    """Whether to verify SSL certificates."""
    
    ssl_cert_path: Optional[str] = None
    """Path to SSL certificate file."""


@dataclass
class CacheConfig:
    """Configuration for client-side caching."""
    
    enabled: bool = True
    """Whether caching is enabled."""
    
    max_items: int = 1000
    """Maximum number of items to cache."""
    
    ttl: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    """Time-to-live for cached items."""
    
    refresh_ahead: bool = False
    """Whether to refresh items before they expire."""
    
    refresh_ahead_time: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    """How long before expiry to refresh items."""


@dataclass
class LoggingConfig:
    """Configuration for client logging."""
    
    level: str = "INFO"
    """Logging level."""
    
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """Log format string."""
    
    log_file: Optional[str] = None
    """Path to log file."""
    
    log_requests: bool = False
    """Whether to log all requests."""
    
    log_responses: bool = False
    """Whether to log all responses."""


@dataclass
class ClientConfig:
    """Main configuration for the database client."""
    
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    """Connection configuration."""
    
    retry: RetryConfig = field(default_factory=RetryConfig)
    """Retry configuration."""
    
    cache: CacheConfig = field(default_factory=CacheConfig)
    """Cache configuration."""
    
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    """Logging configuration."""
    
    default_query_timeout: float = 60.0
    """Default timeout for queries in seconds."""
    
    default_batch_size: int = 1000
    """Default batch size for operations."""
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ClientConfig':
        """
        Create a configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            ClientConfig instance
        """
        # Create base config
        config = cls()
        
        # Apply connection config
        if "connection" in config_dict:
            conn_dict = config_dict["connection"]
            
            # Handle timedelta conversions
            if "max_age" in conn_dict:
                if isinstance(conn_dict["max_age"], (int, float)):
                    conn_dict["max_age"] = timedelta(seconds=conn_dict["max_age"])
            
            if "idle_timeout" in conn_dict:
                if isinstance(conn_dict["idle_timeout"], (int, float)):
                    conn_dict["idle_timeout"] = timedelta(seconds=conn_dict["idle_timeout"])
            
            config.connection = ConnectionConfig(**conn_dict)
        
        # Apply retry config
        if "retry" in config_dict:
            config.retry = RetryConfig(**config_dict["retry"])
        
        # Apply cache config
        if "cache" in config_dict:
            cache_dict = config_dict["cache"]
            
            # Handle timedelta conversions
            if "ttl" in cache_dict:
                if isinstance(cache_dict["ttl"], (int, float)):
                    cache_dict["ttl"] = timedelta(seconds=cache_dict["ttl"])
            
            if "refresh_ahead_time" in cache_dict:
                if isinstance(cache_dict["refresh_ahead_time"], (int, float)):
                    cache_dict["refresh_ahead_time"] = timedelta(seconds=cache_dict["refresh_ahead_time"])
            
            config.cache = CacheConfig(**cache_dict)
        
        # Apply logging config
        if "logging" in config_dict:
            config.logging = LoggingConfig(**config_dict["logging"])
        
        # Apply top-level configs
        if "default_query_timeout" in config_dict:
            config.default_query_timeout = config_dict["default_query_timeout"]
        
        if "default_batch_size" in config_dict:
            config.default_batch_size = config_dict["default_batch_size"]
        
        return config
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ClientConfig':
        """
        Create a configuration from a JSON string.
        
        Args:
            json_str: JSON configuration string
            
        Returns:
            ClientConfig instance
        """
        try:
            config_dict = json.loads(json_str)
            return cls.from_dict(config_dict)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON configuration: {e}")
            return cls()
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ClientConfig':
        """
        Create a configuration from a JSON file.
        
        Args:
            file_path: Path to JSON configuration file
            
        Returns:
            ClientConfig instance
        """
        if not os.path.exists(file_path):
            logger.warning(f"Configuration file {file_path} not found, using defaults")
            return cls()
        
        try:
            with open(file_path, 'r') as f:
                config_json = f.read()
            return cls.from_json(config_json)
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        # Helper function to convert timedeltas to seconds
        def convert_timedeltas(obj):
            if isinstance(obj, timedelta):
                return obj.total_seconds()
            elif isinstance(obj, dict):
                return {k: convert_timedeltas(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_timedeltas(item) for item in obj]
            else:
                return obj
        
        # Convert to dict and handle timedeltas
        result = {
            "connection": {
                "url": self.connection.url,
                "api_key": self.connection.api_key,
                "timeout": self.connection.timeout,
                "min_connections": self.connection.min_connections,
                "max_connections": self.connection.max_connections,
                "max_age": self.connection.max_age,
                "idle_timeout": self.connection.idle_timeout,
                "ssl_verify": self.connection.ssl_verify,
                "ssl_cert_path": self.connection.ssl_cert_path
            },
            "retry": {
                "max_attempts": self.retry.max_attempts,
                "base_delay": self.retry.base_delay,
                "max_delay": self.retry.max_delay,
                "backoff_factor": self.retry.backoff_factor,
                "retry_on_exceptions": self.retry.retry_on_exceptions
            },
            "cache": {
                "enabled": self.cache.enabled,
                "max_items": self.cache.max_items,
                "ttl": self.cache.ttl,
                "refresh_ahead": self.cache.refresh_ahead,
                "refresh_ahead_time": self.cache.refresh_ahead_time
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "log_file": self.logging.log_file,
                "log_requests": self.logging.log_requests,
                "log_responses": self.logging.log_responses
            },
            "default_query_timeout": self.default_query_timeout,
            "default_batch_size": self.default_batch_size
        }
        
        return convert_timedeltas(result)
    
    def to_json(self, pretty: bool = True) -> str:
        """
        Convert the configuration to a JSON string.
        
        Args:
            pretty: Whether to format the JSON for readability
            
        Returns:
            JSON string representation
        """
        config_dict = self.to_dict()
        
        if pretty:
            return json.dumps(config_dict, indent=2)
        else:
            return json.dumps(config_dict)
    
    def save_to_file(self, file_path: str, pretty: bool = True) -> bool:
        """
        Save the configuration to a file.
        
        Args:
            file_path: Path to save to
            pretty: Whether to format the JSON for readability
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                f.write(self.to_json(pretty=pretty))
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {file_path}: {e}")
            return False
    
    def configure_logging(self) -> None:
        """Configure logging based on the configuration."""
        log_format = self.logging.format
        log_level = getattr(logging, self.logging.level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(console_handler)
        
        # Add file handler if specified
        if self.logging.log_file:
            try:
                file_handler = logging.FileHandler(self.logging.log_file)
                file_handler.setFormatter(logging.Formatter(log_format))
                root_logger.addHandler(file_handler)
            except Exception as e:
                logger.error(f"Failed to set up log file {self.logging.log_file}: {e}") 
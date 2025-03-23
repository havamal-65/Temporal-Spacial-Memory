"""
Connection pooling for database client.

This module provides a connection pool for efficient management of
database connections, reducing connection overhead for concurrent access.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
import logging
from queue import Queue, Empty
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class Connection:
    """Represents a single database connection."""
    
    def __init__(self, url: str, timeout: float = 30.0):
        """
        Initialize a connection.
        
        Args:
            url: The database URL to connect to
            timeout: Connection timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_used_at = self.created_at
        self.is_active = False
        self.error_count = 0
        self.max_errors = 3
    
    def connect(self) -> bool:
        """
        Establish the connection.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # TODO: Implement actual connection logic
            # For now, just simulate a connection
            time.sleep(0.1)
            self.is_active = True
            self.last_used_at = datetime.now()
            logger.debug(f"Connection {self.id} established to {self.url}")
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to connect {self.id}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close the connection."""
        try:
            # TODO: Implement actual disconnection logic
            self.is_active = False
            logger.debug(f"Connection {self.id} closed")
        except Exception as e:
            logger.error(f"Error closing connection {self.id}: {e}")
    
    def reset(self) -> bool:
        """
        Reset the connection.
        
        Returns:
            True if reset successfully, False otherwise
        """
        self.disconnect()
        return self.connect()
    
    def is_expired(self, max_age: timedelta) -> bool:
        """
        Check if the connection is expired.
        
        Args:
            max_age: Maximum connection age
            
        Returns:
            True if expired, False otherwise
        """
        return (datetime.now() - self.created_at) > max_age
    
    def is_idle(self, idle_timeout: timedelta) -> bool:
        """
        Check if the connection is idle.
        
        Args:
            idle_timeout: Maximum idle time
            
        Returns:
            True if idle, False otherwise
        """
        return (datetime.now() - self.last_used_at) > idle_timeout
    
    def is_healthy(self) -> bool:
        """
        Check if the connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return self.is_active and self.error_count < self.max_errors


class ConnectionPool:
    """
    Manages a pool of database connections.
    
    This class provides efficient connection management for concurrent
    database access, reducing the overhead of creating and closing connections.
    """
    
    def __init__(self, 
                url: str, 
                min_connections: int = 2,
                max_connections: int = 10,
                max_age: timedelta = timedelta(minutes=30),
                idle_timeout: timedelta = timedelta(minutes=5),
                connection_timeout: float = 30.0):
        """
        Initialize a connection pool.
        
        Args:
            url: The database URL to connect to
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            max_age: Maximum age of a connection before recycling
            idle_timeout: Maximum idle time before recycling
            connection_timeout: Connection timeout in seconds
        """
        self.url = url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_age = max_age
        self.idle_timeout = idle_timeout
        self.connection_timeout = connection_timeout
        
        # Available connections
        self.available_connections: Queue = Queue()
        
        # Active connections (currently in use)
        self.active_connections: Dict[str, Connection] = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Maintenance thread
        self.maintenance_thread = None
        self.maintenance_stop_event = threading.Event()
        
        # Initialize the pool
        self._initialize_pool()
        self._start_maintenance_thread()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool with min_connections."""
        with self.lock:
            for _ in range(self.min_connections):
                connection = Connection(self.url, self.connection_timeout)
                if connection.connect():
                    self.available_connections.put(connection)
                    logger.debug(f"Added initial connection {connection.id} to pool")
    
    def _start_maintenance_thread(self) -> None:
        """Start the maintenance thread."""
        if self.maintenance_thread is None:
            self.maintenance_stop_event.clear()
            self.maintenance_thread = threading.Thread(
                target=self._maintenance_loop,
                daemon=True,
                name="ConnectionPool-Maintenance"
            )
            self.maintenance_thread.start()
            logger.debug("Started connection pool maintenance thread")
    
    def _maintenance_loop(self) -> None:
        """Maintenance loop to manage connections."""
        while not self.maintenance_stop_event.is_set():
            # Sleep for a bit
            self.maintenance_stop_event.wait(60)  # Check every minute
            
            if not self.maintenance_stop_event.is_set():
                try:
                    self._perform_maintenance()
                except Exception as e:
                    logger.error(f"Error in connection pool maintenance: {e}")
    
    def _perform_maintenance(self) -> None:
        """Perform maintenance on the connection pool."""
        with self.lock:
            # Check if we need to add more connections
            available_count = self.available_connections.qsize()
            
            if available_count < self.min_connections:
                # Add more connections
                to_add = self.min_connections - available_count
                for _ in range(to_add):
                    connection = Connection(self.url, self.connection_timeout)
                    if connection.connect():
                        self.available_connections.put(connection)
                        logger.debug(f"Added connection {connection.id} to pool during maintenance")
            
            # Remove expired or idle connections, but keep min_connections
            if available_count > self.min_connections:
                # Get all connections
                connections = []
                try:
                    while True:
                        connections.append(self.available_connections.get_nowait())
                except Empty:
                    pass
                
                # Filter out expired or idle connections
                good_connections = []
                for conn in connections:
                    if (conn.is_expired(self.max_age) or 
                        conn.is_idle(self.idle_timeout) or 
                        not conn.is_healthy()):
                        conn.disconnect()
                        logger.debug(f"Removed connection {conn.id} during maintenance")
                    else:
                        good_connections.append(conn)
                
                # Add back good connections
                for conn in good_connections:
                    self.available_connections.put(conn)
                
                # Add new connections if needed
                while self.available_connections.qsize() < self.min_connections:
                    connection = Connection(self.url, self.connection_timeout)
                    if connection.connect():
                        self.available_connections.put(connection)
                        logger.debug(f"Added replacement connection {connection.id}")
    
    def get_connection(self, timeout: float = 5.0) -> Optional[Connection]:
        """
        Get a connection from the pool.
        
        Args:
            timeout: Time to wait for a connection in seconds
            
        Returns:
            A connection if available, None otherwise
            
        Raises:
            TimeoutError: If no connection becomes available within timeout
        """
        try:
            # Try to get a connection from the pool
            connection = self.available_connections.get(timeout=timeout)
            
            # Check if the connection is still good
            if not connection.is_active or connection.is_expired(self.max_age):
                # Connection is expired or inactive, create a new one
                connection.disconnect()
                connection = Connection(self.url, self.connection_timeout)
                if not connection.connect():
                    raise ConnectionError(f"Failed to connect to {self.url}")
            
            # Mark as active
            with self.lock:
                self.active_connections[connection.id] = connection
            
            connection.last_used_at = datetime.now()
            return connection
        except Empty:
            # No connection available, try to create a new one if below max_connections
            with self.lock:
                total_connections = (self.available_connections.qsize() + 
                                   len(self.active_connections))
                
                if total_connections < self.max_connections:
                    # Create a new connection
                    connection = Connection(self.url, self.connection_timeout)
                    if connection.connect():
                        self.active_connections[connection.id] = connection
                        return connection
            
            # Could not create a new connection
            raise TimeoutError(f"Timed out waiting for a connection to {self.url}")
    
    def release_connection(self, connection: Connection) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            connection: The connection to release
        """
        with self.lock:
            # Remove from active connections
            if connection.id in self.active_connections:
                del self.active_connections[connection.id]
            
            # Check if the connection is still good
            if connection.is_healthy() and not connection.is_expired(self.max_age):
                # Add back to the pool
                self.available_connections.put(connection)
            else:
                # Close the connection
                connection.disconnect()
                
                # Create a replacement if needed
                if self.available_connections.qsize() < self.min_connections:
                    new_connection = Connection(self.url, self.connection_timeout)
                    if new_connection.connect():
                        self.available_connections.put(new_connection)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        # Stop maintenance thread
        if self.maintenance_thread is not None:
            self.maintenance_stop_event.set()
            self.maintenance_thread.join(timeout=2.0)
            self.maintenance_thread = None
        
        with self.lock:
            # Close active connections
            for conn_id, conn in list(self.active_connections.items()):
                conn.disconnect()
            self.active_connections.clear()
            
            # Close available connections
            try:
                while True:
                    conn = self.available_connections.get_nowait()
                    conn.disconnect()
            except Empty:
                pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all() 
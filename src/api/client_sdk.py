"""
Python Client SDK for the Temporal-Spatial Memory Database API.

This module provides a client for interacting with the database API.
"""

import time
import json
import logging
import random
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Implementation of the circuit breaker pattern to prevent repeated calls to failing services.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30, 
                 fallback_function: Optional[callable] = None):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Time in seconds before trying to close the circuit again
            fallback_function: Function to call when circuit is open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback_function = fallback_function
        
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0
    
    def execute(self, function: callable, *args, **kwargs):
        """
        Execute the given function with circuit breaker protection.
        
        Args:
            function: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Function result or fallback result if circuit is open
            
        Raises:
            Exception: If circuit is open and no fallback is provided
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit moving to HALF_OPEN state")
                self.state = "HALF_OPEN"
            else:
                if self.fallback_function:
                    logger.info("Circuit OPEN, using fallback")
                    return self.fallback_function(*args, **kwargs)
                else:
                    raise Exception("Circuit is OPEN")
        
        try:
            result = function(*args, **kwargs)
            
            # If we're in HALF_OPEN and the call succeeded, close the circuit
            if self.state == "HALF_OPEN":
                logger.info("Circuit moving to CLOSED state")
                self.state = "CLOSED"
                self.failures = 0
            
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                logger.warning(f"Circuit moving to OPEN state after {self.failures} failures")
                self.state = "OPEN"
            
            if self.fallback_function:
                logger.info(f"Call failed, using fallback: {str(e)}")
                return self.fallback_function(*args, **kwargs)
            else:
                raise e

class TemporalSpatialClient:
    """
    Client for interacting with the Temporal-Spatial Memory Database API.
    """
    
    def __init__(self, base_url: str, username: str = None, password: str = None, 
                 token: str = None, max_retries: int = 3, timeout: float = 10.0,
                 circuit_breaker_threshold: int = 5, circuit_breaker_timeout: float = 30):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API
            username: Username for authentication
            password: Password for authentication
            token: Authentication token (if already authenticated)
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            circuit_breaker_threshold: Number of failures before circuit opens
            circuit_breaker_timeout: Time in seconds before trying to close the circuit again
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.timeout = timeout
        
        # Set up connection pooling and retries
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["GET", "POST", "PUT", "DELETE"]
        )
        
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set up circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
            fallback_function=self._circuit_breaker_fallback
        )
        
        # Initialize token if credentials provided
        if self.username and self.password and not self.token:
            self.authenticate()
    
    def _circuit_breaker_fallback(self, *args, **kwargs):
        """Fallback function for circuit breaker."""
        logger.error("Circuit breaker fallback: API is unavailable")
        return None
    
    def _make_request(self, method: str, endpoint: str, data: Any = None, 
                     params: Dict[str, Any] = None) -> Any:
        """
        Make a request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            
        Returns:
            API response as JSON
            
        Raises:
            requests.RequestException: If the request fails
        """
        url = urljoin(self.base_url, endpoint)
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        def _do_request():
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            # Raise exception for 4xx/5xx status codes
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return None
        
        # Execute request with circuit breaker
        return self.circuit_breaker.execute(_do_request)
    
    def authenticate(self) -> str:
        """
        Authenticate with the API.
        
        Returns:
            Access token
            
        Raises:
            requests.RequestException: If authentication fails
        """
        if not self.username or not self.password:
            raise ValueError("Username and password required for authentication")
        
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = self._make_request("POST", "token", data=data)
        
        if response and "access_token" in response:
            self.token = response["access_token"]
            return self.token
        
        raise ValueError("Authentication failed")
    
    def create_node(self, content: Any, spatial_coordinates: List[float] = None,
                   temporal_coordinate: float = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new node.
        
        Args:
            content: Node content
            spatial_coordinates: Spatial coordinates [x, y, z]
            temporal_coordinate: Temporal coordinate (Unix timestamp)
            metadata: Additional metadata
            
        Returns:
            Created node
            
        Raises:
            requests.RequestException: If the request fails
        """
        data = {
            "content": content,
            "spatial_coordinates": spatial_coordinates,
            "temporal_coordinate": temporal_coordinate,
            "metadata": metadata or {}
        }
        
        return self._make_request("POST", "nodes", data=data)
    
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data
            
        Raises:
            requests.RequestException: If the request fails
        """
        return self._make_request("GET", f"nodes/{node_id}")
    
    def update_node(self, node_id: str, content: Any, spatial_coordinates: List[float] = None,
                   temporal_coordinate: float = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update a node.
        
        Args:
            node_id: Node ID
            content: Updated content
            spatial_coordinates: Updated spatial coordinates
            temporal_coordinate: Updated temporal coordinate
            metadata: Updated metadata
            
        Returns:
            Updated node
            
        Raises:
            requests.RequestException: If the request fails
        """
        data = {
            "content": content,
            "spatial_coordinates": spatial_coordinates,
            "temporal_coordinate": temporal_coordinate,
            "metadata": metadata or {}
        }
        
        return self._make_request("PUT", f"nodes/{node_id}", data=data)
    
    def delete_node(self, node_id: str) -> None:
        """
        Delete a node.
        
        Args:
            node_id: Node ID
            
        Raises:
            requests.RequestException: If the request fails
        """
        self._make_request("DELETE", f"nodes/{node_id}")
    
    def query(self, spatial_criteria: Dict[str, Any] = None, temporal_criteria: Dict[str, Any] = None,
             limit: int = 100, offset: int = 0, sort_by: str = None, 
             sort_order: str = "asc") -> Dict[str, Any]:
        """
        Execute a query.
        
        Args:
            spatial_criteria: Spatial query criteria
            temporal_criteria: Temporal query criteria
            limit: Maximum number of results to return
            offset: Result offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Query results
            
        Raises:
            requests.RequestException: If the request fails
        """
        data = {
            "spatial_criteria": spatial_criteria,
            "temporal_criteria": temporal_criteria,
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        return self._make_request("POST", "query", data=data)
    
    def spatial_query(self, point: List[float] = None, distance: float = None,
                     region: Tuple[List[float], List[float]] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Execute a spatial query.
        
        Args:
            point: Center point for nearest neighbor query [x, y, z]
            distance: Maximum distance for nearest neighbor query
            region: Region for range query ([min_x, min_y, min_z], [max_x, max_y, max_z])
            limit: Maximum number of results to return
            
        Returns:
            Query results
            
        Raises:
            requests.RequestException: If the request fails
            ValueError: If neither point nor region is provided
        """
        if not point and not region:
            raise ValueError("Either point or region must be provided")
        
        spatial_criteria = {}
        
        if point:
            spatial_criteria["point"] = point
            if distance:
                spatial_criteria["distance"] = distance
        
        if region:
            spatial_criteria["region"] = {
                "lower": region[0],
                "upper": region[1]
            }
        
        return self.query(spatial_criteria=spatial_criteria, limit=limit)
    
    def temporal_query(self, start_time: Union[float, datetime], end_time: Union[float, datetime] = None,
                      limit: int = 100) -> Dict[str, Any]:
        """
        Execute a temporal query.
        
        Args:
            start_time: Start time (Unix timestamp or datetime)
            end_time: End time (Unix timestamp or datetime)
            limit: Maximum number of results to return
            
        Returns:
            Query results
            
        Raises:
            requests.RequestException: If the request fails
        """
        # Convert datetime to timestamp if needed
        if isinstance(start_time, datetime):
            start_time = start_time.timestamp()
        
        if end_time is None:
            end_time = time.time()
        elif isinstance(end_time, datetime):
            end_time = end_time.timestamp()
        
        temporal_criteria = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        return self.query(temporal_criteria=temporal_criteria, limit=limit)
    
    def combined_query(self, spatial_criteria: Dict[str, Any], temporal_criteria: Dict[str, Any],
                      limit: int = 100) -> Dict[str, Any]:
        """
        Execute a combined spatial and temporal query.
        
        Args:
            spatial_criteria: Spatial query criteria
            temporal_criteria: Temporal query criteria
            limit: Maximum number of results to return
            
        Returns:
            Query results
            
        Raises:
            requests.RequestException: If the request fails
        """
        return self.query(
            spatial_criteria=spatial_criteria,
            temporal_criteria=temporal_criteria,
            limit=limit
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Statistics
            
        Raises:
            requests.RequestException: If the request fails
        """
        return self._make_request("GET", "stats")
    
    def close(self) -> None:
        """Close the client session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 
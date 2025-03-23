"""
API client for the Temporal-Spatial Knowledge Database.

This module handles all interactions with the database API, including
HTTP requests, authentication, and error handling.
"""

import time
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import threading
import urllib.parse

from .config import ClientConfig, RetryConfig
from .connection_pool import Connection, ConnectionPool
from ..core.node_v2 import Node

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                response: Optional[Any] = None):
        """
        Initialize an API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response: Response object
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(ApiError):
    """Raised when authentication fails."""
    pass


class ConnectionError(ApiError):
    """Raised when a connection cannot be established."""
    pass


class RequestError(ApiError):
    """Raised when a request fails."""
    pass


class ServerError(ApiError):
    """Raised when the server returns an error."""
    pass


class TimeoutError(ApiError):
    """Raised when a request times out."""
    pass


class RateLimitError(ApiError):
    """Raised when rate limits are exceeded."""
    pass


class ApiClient:
    """
    Client for interacting with the database API.
    
    This class handles all low-level API interactions, including authentication,
    request formatting, and error handling.
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize an API client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        
        # Set up connection pool
        self.connection_pool = ConnectionPool(
            url=config.connection.url,
            min_connections=config.connection.min_connections,
            max_connections=config.connection.max_connections,
            max_age=config.connection.max_age,
            idle_timeout=config.connection.idle_timeout,
            connection_timeout=config.connection.timeout
        )
        
        # Set up session cache
        self.session_token: Optional[str] = None
        self.session_expiry: Optional[datetime] = None
        self.auth_lock = threading.RLock()
        
        # Headers
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"TSDatabaseClient/1.0"
        }
        
        # Configure logging
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure API client logging."""
        log_level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
        logger.setLevel(log_level)
    
    def _get_auth_header(self) -> Dict[str, str]:
        """
        Get authentication headers.
        
        Returns:
            Dictionary of authentication headers
        """
        with self.auth_lock:
            # Check if we need to refresh the session
            if self._needs_auth_refresh():
                self._refresh_auth()
            
            if self.session_token:
                return {"Authorization": f"Bearer {self.session_token}"}
            elif self.config.connection.api_key:
                return {"X-API-Key": self.config.connection.api_key}
            
            return {}
    
    def _needs_auth_refresh(self) -> bool:
        """
        Check if authentication needs refreshing.
        
        Returns:
            True if auth needs refreshing, False otherwise
        """
        if not self.session_token:
            return True
        
        if not self.session_expiry:
            return True
        
        # Refresh if less than 5 minutes remaining
        refresh_threshold = timedelta(minutes=5)
        return datetime.now() > (self.session_expiry - refresh_threshold)
    
    def _refresh_auth(self) -> None:
        """Refresh authentication token."""
        if not self.config.connection.api_key:
            return
        
        try:
            response = self._make_request(
                "POST",
                "/auth/token",
                data={"api_key": self.config.connection.api_key},
                auth_required=False
            )
            
            if response.get("token"):
                self.session_token = response["token"]
                
                # Set expiry if provided, otherwise default to 1 hour
                if "expires_at" in response:
                    self.session_expiry = datetime.fromisoformat(response["expires_at"])
                else:
                    self.session_expiry = datetime.now() + timedelta(hours=1)
                
                logger.debug("Authentication refreshed successfully")
            else:
                logger.error("Failed to refresh authentication: no token in response")
                self.session_token = None
                self.session_expiry = None
        except Exception as e:
            logger.error(f"Failed to refresh authentication: {e}")
            self.session_token = None
            self.session_expiry = None
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build a full URL from an endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Full URL
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        
        # Get base URL from config
        base_url = self.config.connection.url
        
        # Ensure base URL doesn't end with /
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        
        # Check if base URL includes protocol, add https:// if not
        if "://" not in base_url:
            base_url = f"https://{base_url}"
        
        return f"{base_url}{endpoint}"
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     auth_required: bool = True,
                     timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Make an API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request data
            headers: Additional headers
            auth_required: Whether authentication is required
            timeout: Request timeout in seconds
            
        Returns:
            Response data
            
        Raises:
            Various ApiError subclasses for different error conditions
        """
        # Build URL
        url = self._build_url(endpoint)
        
        # Build headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        if auth_required:
            auth_headers = self._get_auth_header()
            request_headers.update(auth_headers)
        
        # Convert data to JSON
        json_data = json.dumps(data) if data else None
        
        # Set timeout
        if timeout is None:
            timeout = self.config.connection.timeout
        
        # Log request
        if self.config.logging.log_requests:
            logger.debug(f"API Request: {method} {url}")
            if params:
                logger.debug(f"  Params: {params}")
            if data:
                logger.debug(f"  Data: {data}")
        
        # Attempt the request with retries
        return self._make_request_with_retry(
            method, url, params, json_data, request_headers, timeout
        )
    
    def _make_request_with_retry(self,
                                method: str,
                                url: str,
                                params: Optional[Dict[str, Any]],
                                json_data: Optional[str],
                                headers: Dict[str, str],
                                timeout: float) -> Dict[str, Any]:
        """
        Make a request with retry logic.
        
        Args:
            method: HTTP method
            url: Full URL
            params: Query parameters
            json_data: JSON data
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Response data
            
        Raises:
            Various ApiError subclasses for different error conditions
        """
        retry_config = self.config.retry
        attempts = 0
        last_error = None
        
        while attempts < retry_config.max_attempts:
            attempts += 1
            
            try:
                # Get a connection from the pool
                conn = self.connection_pool.get_connection()
                
                try:
                    # Make the request
                    response = requests.request(
                        method=method,
                        url=url,
                        params=params,
                        data=json_data,
                        headers=headers,
                        timeout=timeout,
                        verify=self.config.connection.ssl_verify
                    )
                    
                    # Handle response
                    return self._handle_response(response)
                finally:
                    # Release the connection back to the pool
                    self.connection_pool.release_connection(conn)
            except requests.exceptions.Timeout as e:
                last_error = TimeoutError(f"Request timed out: {e}", None, None)
            except requests.exceptions.ConnectionError as e:
                last_error = ConnectionError(f"Connection error: {e}", None, None)
            except requests.exceptions.RequestException as e:
                last_error = RequestError(f"Request error: {e}", None, None)
            except Exception as e:
                last_error = ApiError(f"Unexpected error: {e}", None, None)
            
            # Should we retry?
            if not self._should_retry(last_error, attempts, retry_config):
                break
            
            # Calculate retry delay
            delay = self._calculate_retry_delay(attempts, retry_config)
            logger.debug(f"Retrying in {delay} seconds (attempt {attempts}/{retry_config.max_attempts})")
            time.sleep(delay)
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise ApiError("All retry attempts failed", None, None)
    
    def _should_retry(self, 
                     error: ApiError, 
                     attempt: int,
                     retry_config: RetryConfig) -> bool:
        """
        Determine if a request should be retried.
        
        Args:
            error: The error that occurred
            attempt: Current attempt number
            retry_config: Retry configuration
            
        Returns:
            True if the request should be retried, False otherwise
        """
        # Never retry if we've reached max attempts
        if attempt >= retry_config.max_attempts:
            return False
        
        # Check error type
        error_type = error.__class__.__name__
        return error_type in retry_config.retry_on_exceptions
    
    def _calculate_retry_delay(self, attempt: int, retry_config: RetryConfig) -> float:
        """
        Calculate the delay before the next retry.
        
        Args:
            attempt: Current attempt number
            retry_config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff with jitter
        base_delay = retry_config.base_delay
        max_delay = retry_config.max_delay
        factor = retry_config.backoff_factor
        
        # Calculate exponential delay
        delay = base_delay * (factor ** (attempt - 1))
        
        # Apply maximum
        delay = min(delay, max_delay)
        
        # Add jitter (±10%)
        jitter = delay * 0.1
        delay = delay - jitter + (2 * jitter * (time.time() % 1))
        
        return delay
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle an API response.
        
        Args:
            response: Response object
            
        Returns:
            Response data
            
        Raises:
            Various ApiError subclasses for different error conditions
        """
        # Log response
        if self.config.logging.log_responses:
            logger.debug(f"API Response: {response.status_code}")
            logger.debug(f"  Headers: {response.headers}")
            try:
                logger.debug(f"  Body: {response.text[:500]}...")
            except:
                pass
        
        # Handle different status codes
        if response.status_code == 200:
            # Success
            try:
                return response.json()
            except ValueError:
                return {"text": response.text}
        elif response.status_code == 204:
            # No content
            return {}
        elif response.status_code == 400:
            # Bad request
            raise RequestError("Bad request", response.status_code, response)
        elif response.status_code == 401:
            # Unauthorized
            self.session_token = None
            self.session_expiry = None
            raise AuthenticationError("Unauthorized", response.status_code, response)
        elif response.status_code == 403:
            # Forbidden
            raise AuthenticationError("Forbidden", response.status_code, response)
        elif response.status_code == 404:
            # Not found
            raise RequestError("Resource not found", response.status_code, response)
        elif response.status_code == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After", "60")
            try:
                retry_seconds = int(retry_after)
            except ValueError:
                retry_seconds = 60
            
            raise RateLimitError(
                f"Rate limit exceeded, retry after {retry_seconds} seconds",
                response.status_code,
                response
            )
        elif 500 <= response.status_code < 600:
            # Server error
            raise ServerError(
                f"Server error: {response.status_code}",
                response.status_code,
                response
            )
        else:
            # Other error
            raise ApiError(
                f"Unexpected status code: {response.status_code}",
                response.status_code,
                response
            )
    
    def get(self, 
           endpoint: str, 
           params: Optional[Dict[str, Any]] = None,
           **kwargs) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional parameters for _make_request
            
        Returns:
            Response data
        """
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    def post(self, 
            endpoint: str, 
            data: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None,
            **kwargs) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            **kwargs: Additional parameters for _make_request
            
        Returns:
            Response data
        """
        return self._make_request("POST", endpoint, params=params, data=data, **kwargs)
    
    def put(self, 
           endpoint: str, 
           data: Optional[Dict[str, Any]] = None,
           params: Optional[Dict[str, Any]] = None,
           **kwargs) -> Dict[str, Any]:
        """
        Make a PUT request.
        
        Args:
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            **kwargs: Additional parameters for _make_request
            
        Returns:
            Response data
        """
        return self._make_request("PUT", endpoint, params=params, data=data, **kwargs)
    
    def delete(self, 
              endpoint: str, 
              params: Optional[Dict[str, Any]] = None,
              **kwargs) -> Dict[str, Any]:
        """
        Make a DELETE request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional parameters for _make_request
            
        Returns:
            Response data
        """
        return self._make_request("DELETE", endpoint, params=params, **kwargs)
    
    def close(self) -> None:
        """Close the API client and release resources."""
        self.connection_pool.close_all()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 
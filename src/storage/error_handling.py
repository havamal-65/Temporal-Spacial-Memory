"""
Error handling utilities for the Temporal-Spatial Knowledge Database.

This module provides error handling utilities, including retry mechanisms for
transient errors and circuit breakers for persistent failures.
"""

import time
import random
import threading
import logging
from typing import Callable, TypeVar, Any, Optional, Dict, List, Set, Union, Type
from functools import wraps
import traceback

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar('T')


class RetryableError(Exception):
    """Base class for errors that can be retried."""
    pass


class PermanentError(Exception):
    """Base class for errors that should not be retried."""
    pass


class StorageConnectionError(RetryableError):
    """Error connecting to storage backend."""
    pass


class NodeNotFoundError(Exception):
    """Error when a node cannot be found."""
    pass


class CircuitBreakerError(Exception):
    """Error raised when circuit breaker is open."""
    pass


class RetryStrategy:
    """
    Base class for retry strategies.
    
    Retry strategies determine how to delay between retry attempts.
    """
    
    def get_delay(self, attempt: int) -> float:
        """
        Get the delay before the next retry attempt.
        
        Args:
            attempt: The retry attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        raise NotImplementedError


class FixedRetryStrategy(RetryStrategy):
    """Retry with a fixed delay between attempts."""
    
    def __init__(self, delay: float = 1.0):
        """
        Initialize a fixed retry strategy.
        
        Args:
            delay: Delay in seconds between attempts
        """
        self.delay = delay
    
    def get_delay(self, attempt: int) -> float:
        """Get fixed delay regardless of attempt number."""
        return self.delay


class ExponentialBackoffStrategy(RetryStrategy):
    """Retry with exponential backoff between attempts."""
    
    def __init__(self, 
                 initial_delay: float = 0.1, 
                 max_delay: float = 60.0, 
                 backoff_factor: float = 2.0,
                 jitter: bool = True):
        """
        Initialize an exponential backoff strategy.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Factor to multiply delay by for each attempt
            jitter: Whether to add random jitter to the delay
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Get exponentially increasing delay."""
        delay = min(self.initial_delay * (self.backoff_factor ** attempt), self.max_delay)
        
        if self.jitter:
            # Add random jitter of up to 20%
            jitter_factor = 1.0 + (random.random() * 0.2)
            delay *= jitter_factor
        
        return delay


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    The circuit breaker prevents repeated failures by "opening the circuit"
    after a threshold of failures is reached, preventing further attempts for
    a cooldown period.
    """
    
    # Circuit states
    CLOSED = 'CLOSED'  # Normal operation
    OPEN = 'OPEN'      # Circuit is open, calls fail fast
    HALF_OPEN = 'HALF_OPEN'  # Testing if the circuit can be closed again
    
    def __init__(self, 
                 failure_threshold: int = 5, 
                 recovery_timeout: float = 30.0,
                 retry_timeout: float = 60.0):
        """
        Initialize a circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds to wait before trying again
            retry_timeout: Time in seconds to reset failure count
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.retry_timeout = retry_timeout
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = self.CLOSED
        self.lock = threading.RLock()
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to apply circuit breaker to a function.
        
        Args:
            func: The function to wrap
            
        Returns:
            Wrapped function with circuit breaker protection
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with self.lock:
                if self.state == self.OPEN:
                    # Check if recovery timeout has elapsed
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = self.HALF_OPEN
                    else:
                        raise CircuitBreakerError(f"Circuit breaker is open until {time.ctime(self.last_failure_time + self.recovery_timeout)}")
            
            try:
                result = func(*args, **kwargs)
                
                with self.lock:
                    if self.state == self.HALF_OPEN:
                        # Success, close the circuit
                        self.state = self.CLOSED
                        self.failure_count = 0
                    
                    # Reset failure count if retry timeout has elapsed
                    if time.time() - self.last_failure_time > self.retry_timeout:
                        self.failure_count = 0
                
                return result
            
            except Exception as e:
                with self.lock:
                    self.last_failure_time = time.time()
                    self.failure_count += 1
                    
                    # Open the circuit if failure threshold is reached
                    if self.state != self.OPEN and self.failure_count >= self.failure_threshold:
                        self.state = self.OPEN
                        logger.warning(f"Circuit breaker opened due to {self.failure_count} failures")
                
                raise
        
        return wrapper


def retry(max_attempts: int = 3, 
          retry_strategy: Optional[RetryStrategy] = None,
          retryable_exceptions: Optional[List[Type[Exception]]] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        retry_strategy: Strategy for determining retry delays
        retryable_exceptions: List of exception types to retry on
        
    Returns:
        Decorator function
    """
    if retry_strategy is None:
        retry_strategy = ExponentialBackoffStrategy()
    
    if retryable_exceptions is None:
        retryable_exceptions = [RetryableError, StorageConnectionError]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            last_exception = None
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except tuple(retryable_exceptions) as e:
                    attempts += 1
                    last_exception = e
                    
                    if attempts >= max_attempts:
                        logger.warning(f"Failed after {attempts} attempts: {e}")
                        break
                    
                    delay = retry_strategy.get_delay(attempts - 1)
                    logger.info(f"Retry {attempts}/{max_attempts} after {delay:.2f}s: {e}")
                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable exception
                    if isinstance(e, PermanentError):
                        logger.warning(f"Permanent error, not retrying: {e}")
                    else:
                        logger.warning(f"Unexpected error, not retrying: {e}")
                    raise
            
            # If we get here, we've exhausted our retries
            if last_exception:
                logger.error(f"Max retries ({max_attempts}) exceeded: {last_exception}")
                raise last_exception
            
            # This should never happen, but just in case
            raise RuntimeError("Max retries exceeded, but no exception was raised")
        
        return wrapper
    
    return decorator


class ErrorTracker:
    """
    Tracks errors and their frequency.
    
    This can be used to detect patterns in errors and adjust behavior
    accordingly.
    """
    
    def __init__(self, window_size: int = 100, error_threshold: float = 0.5):
        """
        Initialize an error tracker.
        
        Args:
            window_size: Number of operations to track
            error_threshold: Threshold for error rate before alerting
        """
        self.window_size = window_size
        self.error_threshold = error_threshold
        
        self.operations = []  # List of (timestamp, success) tuples
        self.error_counts: Dict[str, int] = {}  # Error type -> count
        self.lock = threading.RLock()
    
    def record_success(self) -> None:
        """Record a successful operation."""
        with self.lock:
            self._add_operation(True)
    
    def record_error(self, error: Exception) -> None:
        """
        Record a failed operation.
        
        Args:
            error: The exception that occurred
        """
        with self.lock:
            self._add_operation(False)
            
            # Track error type
            error_type = type(error).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def _add_operation(self, success: bool) -> None:
        """Add an operation to the history."""
        now = time.time()
        self.operations.append((now, success))
        
        # Trim history if needed
        if len(self.operations) > self.window_size:
            self.operations = self.operations[-self.window_size:]
    
    def get_error_rate(self) -> float:
        """
        Get the current error rate.
        
        Returns:
            Error rate as a fraction (0.0 to 1.0)
        """
        with self.lock:
            if not self.operations:
                return 0.0
            
            failures = sum(1 for _, success in self.operations if not success)
            return failures / len(self.operations)
    
    def should_alert(self) -> bool:
        """
        Check if the error rate exceeds the threshold.
        
        Returns:
            True if the error rate exceeds the threshold
        """
        return self.get_error_rate() >= self.error_threshold
    
    def get_most_common_error(self) -> Optional[str]:
        """
        Get the most common error type.
        
        Returns:
            Most common error type, or None if no errors
        """
        with self.lock:
            if not self.error_counts:
                return None
            
            return max(self.error_counts.items(), key=lambda x: x[1])[0] 
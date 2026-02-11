"""Retry decorator for handling transient failures."""

import time
import functools
from typing import Callable, Union, Tuple, Type, Optional
import random


def retry(max_attempts: int = 3,
          delay: float = 1.0,
          backoff: float = 2.0,
          jitter: bool = True,
          exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
          on_retry: Optional[Callable] = None):
    """
    Retry decorator with exponential backoff and jitter.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for exponential backoff
        jitter: Add random jitter to delay
        exceptions: Exception types to catch and retry
        on_retry: Callback function called on each retry
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Don't sleep after the last attempt
                    if attempt == max_attempts - 1:
                        break
                        
                    # Calculate delay with backoff and optional jitter
                    current_delay = delay * (backoff ** attempt)
                    
                    if jitter:
                        # Add ±25% jitter
                        jitter_range = current_delay * 0.25
                        current_delay += random.uniform(-jitter_range, jitter_range)
                        
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e, current_delay)
                        
                    time.sleep(current_delay)
                    
            # If we got here, all retries failed
            raise last_exception
            
        return wrapper
    return decorator


def async_retry(max_attempts: int = 3,
                delay: float = 1.0,
                backoff: float = 2.0,
                jitter: bool = True,
                exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
                on_retry: Optional[Callable] = None):
    """
    Async retry decorator with exponential backoff and jitter.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for exponential backoff
        jitter: Add random jitter to delay
        exceptions: Exception types to catch and retry
        on_retry: Callback function called on each retry
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Don't sleep after the last attempt
                    if attempt == max_attempts - 1:
                        break
                        
                    # Calculate delay with backoff and optional jitter
                    current_delay = delay * (backoff ** attempt)
                    
                    if jitter:
                        # Add ±25% jitter
                        jitter_range = current_delay * 0.25
                        current_delay += random.uniform(-jitter_range, jitter_range)
                        
                    # Call retry callback if provided
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt + 1, e, current_delay)
                        else:
                            on_retry(attempt + 1, e, current_delay)
                            
                    await asyncio.sleep(current_delay)
                    
            # If we got here, all retries failed
            raise last_exception
            
        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry logic."""
    
    def __init__(self, max_attempts: int = 3, delay: float = 1.0, 
                 backoff: float = 2.0, jitter: bool = True,
                 exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception):
        """Initialize retry context."""
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.jitter = jitter
        self.exceptions = exceptions
        self.attempt = 0
        self.last_exception = None
        
    def __enter__(self):
        """Enter retry context."""
        self.attempt += 1
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit retry context."""
        if exc_type is None:
            return True  # Success, don't retry
            
        if not issubclass(exc_type, self.exceptions):
            return False  # Don't handle this exception
            
        self.last_exception = exc_val
        
        if self.attempt >= self.max_attempts:
            return False  # Max attempts reached
            
        # Calculate delay
        current_delay = self.delay * (self.backoff ** (self.attempt - 1))
        
        if self.jitter:
            jitter_range = current_delay * 0.25
            current_delay += random.uniform(-jitter_range, jitter_range)
            
        time.sleep(current_delay)
        return True  # Suppress exception and retry
        
    def should_retry(self) -> bool:
        """Check if should retry."""
        return self.attempt < self.max_attempts


# Convenience functions for common retry patterns
def retry_on_connection_error(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator for connection errors."""
    import requests
    connection_exceptions = (
        requests.ConnectionError,
        requests.Timeout,
        requests.HTTPError
    )
    return retry(max_attempts=max_attempts, delay=delay, exceptions=connection_exceptions)


def retry_on_rate_limit(max_attempts: int = 5, delay: float = 2.0):
    """Retry decorator for rate limit errors."""
    import requests
    rate_limit_exceptions = (
        requests.HTTPError,
    )
    
    def is_rate_limit_error(response):
        return response.status_code == 429
        
    return retry(max_attempts=max_attempts, delay=delay, backoff=2.5, 
                exceptions=rate_limit_exceptions)


def retry_with_logging(logger, max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator with logging."""
    
    def on_retry_callback(attempt, exception, delay):
        logger.warning(f"Attempt {attempt} failed: {exception}. Retrying in {delay:.2f}s")
        
    return retry(max_attempts=max_attempts, delay=delay, on_retry=on_retry_callback)
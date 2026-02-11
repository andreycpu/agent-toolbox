"""Rate limiting utilities for controlling API calls and resource usage."""

import time
import threading
from collections import defaultdict, deque
from typing import Optional, Dict, Any, Callable
import functools


class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    
    def __init__(self, max_calls: int, time_window: float, burst_capacity: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
            burst_capacity: Maximum burst capacity (defaults to max_calls)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.burst_capacity = burst_capacity or max_calls
        self.tokens = float(self.burst_capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()
        
    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the rate limiter.
        
        Args:
            tokens: Number of tokens to acquire
            blocking: Whether to block if tokens not available
            timeout: Maximum time to wait for tokens (when blocking)
            
        Returns:
            True if tokens acquired, False otherwise
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                current_time = time.time()
                
                # Add tokens based on elapsed time
                elapsed = current_time - self.last_update
                self.tokens = min(
                    self.burst_capacity,
                    self.tokens + (elapsed * self.max_calls / self.time_window)
                )
                self.last_update = current_time
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                    
            if not blocking:
                return False
                
            if timeout and (time.time() - start_time) >= timeout:
                return False
                
            # Calculate sleep time based on token generation rate
            tokens_needed = tokens - self.tokens
            sleep_time = min(0.1, tokens_needed * self.time_window / self.max_calls)
            time.sleep(sleep_time)
            
    def get_tokens_available(self) -> int:
        """Get number of tokens currently available."""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_update
            self.tokens = min(
                self.burst_capacity,
                self.tokens + (elapsed * self.max_calls / self.time_window)
            )
            self.last_update = current_time
            return int(self.tokens)
            
    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class SlidingWindowRateLimiter:
    """Rate limiter using sliding window algorithm."""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize sliding window rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = threading.Lock()
        
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a call.
        
        Args:
            blocking: Whether to block if rate limit exceeded
            timeout: Maximum time to wait (when blocking)
            
        Returns:
            True if call allowed, False otherwise
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                current_time = time.time()
                
                # Remove old calls outside the time window
                while self.calls and current_time - self.calls[0] > self.time_window:
                    self.calls.popleft()
                    
                # Check if we can make the call
                if len(self.calls) < self.max_calls:
                    self.calls.append(current_time)
                    return True
                    
            if not blocking:
                return False
                
            if timeout and (time.time() - start_time) >= timeout:
                return False
                
            # Sleep until the oldest call expires
            if self.calls:
                sleep_time = min(0.1, self.time_window - (current_time - self.calls[0]))
                time.sleep(max(0.01, sleep_time))
            else:
                time.sleep(0.01)
                
    def get_calls_remaining(self) -> int:
        """Get number of calls remaining in current window."""
        with self.lock:
            current_time = time.time()
            # Remove old calls
            while self.calls and current_time - self.calls[0] > self.time_window:
                self.calls.popleft()
            return max(0, self.max_calls - len(self.calls))


class MultiKeyRateLimiter:
    """Rate limiter with separate limits for different keys."""
    
    def __init__(self, max_calls: int, time_window: float, limiter_type: str = 'token_bucket'):
        """
        Initialize multi-key rate limiter.
        
        Args:
            max_calls: Maximum calls per key
            time_window: Time window in seconds
            limiter_type: 'token_bucket' or 'sliding_window'
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.limiter_type = limiter_type
        self.limiters: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
    def acquire(self, key: str, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission for specific key.
        
        Args:
            key: Identifier for rate limit bucket
            blocking: Whether to block if rate limit exceeded
            timeout: Maximum time to wait
            
        Returns:
            True if call allowed, False otherwise
        """
        with self.lock:
            if key not in self.limiters:
                if self.limiter_type == 'sliding_window':
                    self.limiters[key] = SlidingWindowRateLimiter(self.max_calls, self.time_window)
                else:
                    self.limiters[key] = RateLimiter(self.max_calls, self.time_window)
                    
        return self.limiters[key].acquire(blocking=blocking, timeout=timeout)
        
    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get rate limiter stats for a key."""
        if key not in self.limiters:
            return {'calls_remaining': self.max_calls}
            
        limiter = self.limiters[key]
        if isinstance(limiter, SlidingWindowRateLimiter):
            return {'calls_remaining': limiter.get_calls_remaining()}
        else:
            return {'tokens_available': limiter.get_tokens_available()}


def rate_limited(max_calls: int, time_window: float, key_func: Optional[Callable] = None):
    """
    Decorator to rate limit function calls.
    
    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds
        key_func: Function to extract rate limit key from args/kwargs
    """
    if key_func:
        limiter = MultiKeyRateLimiter(max_calls, time_window)
    else:
        limiter = RateLimiter(max_calls, time_window)
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
                if not limiter.acquire(key):
                    raise Exception(f"Rate limit exceeded for key: {key}")
            else:
                if not limiter.acquire():
                    raise Exception("Rate limit exceeded")
                    
            return func(*args, **kwargs)
            
        wrapper._rate_limiter = limiter  # Expose limiter for inspection
        return wrapper
    return decorator


# Convenience decorators for common patterns
def api_rate_limit(calls_per_minute: int):
    """Rate limit API calls per minute."""
    return rate_limited(calls_per_minute, 60.0)


def user_rate_limit(calls_per_hour: int):
    """Rate limit by user ID (expects user_id in kwargs)."""
    def extract_user_id(*args, **kwargs):
        return kwargs.get('user_id', 'default')
    return rate_limited(calls_per_hour, 3600.0, key_func=extract_user_id)


def ip_rate_limit(calls_per_minute: int):
    """Rate limit by IP address (expects ip_address in kwargs)."""
    def extract_ip(*args, **kwargs):
        return kwargs.get('ip_address', 'default')
    return rate_limited(calls_per_minute, 60.0, key_func=extract_ip)
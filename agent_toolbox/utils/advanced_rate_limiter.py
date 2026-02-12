"""Advanced rate limiting with multiple algorithms and strategies."""

import time
import threading
from typing import Dict, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    
    max_requests: int
    time_window: float  # seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    burst_allowance: int = 0  # Extra requests allowed in burst
    backoff_factor: float = 1.5  # Exponential backoff multiplier
    max_backoff: float = 300.0  # Maximum backoff time in seconds
    adaptive_threshold: float = 0.8  # Threshold for adaptive rate limiting
    
    
class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: float = 0):
        super().__init__(message)
        self.retry_after = retry_after


class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, max_tokens: int, refill_rate: float):
        """Initialize token bucket."""
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = threading.RLock()
        
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
                
            return False
            
    def wait_time(self, tokens: int = 1) -> float:
        """Calculate time to wait for tokens."""
        with self._lock:
            if self.tokens >= tokens:
                return 0
                
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate


class LeakyBucket:
    """Leaky bucket rate limiter."""
    
    def __init__(self, capacity: int, leak_rate: float):
        """Initialize leaky bucket."""
        self.capacity = capacity
        self.leak_rate = leak_rate  # requests per second
        self.level = 0
        self.last_leak = time.time()
        self._lock = threading.RLock()
        
    def acquire(self, amount: int = 1) -> bool:
        """Try to add to bucket."""
        with self._lock:
            now = time.time()
            
            # Leak based on elapsed time
            elapsed = now - self.last_leak
            leaked = elapsed * self.leak_rate
            self.level = max(0, self.level - leaked)
            self.last_leak = now
            
            if self.level + amount <= self.capacity:
                self.level += amount
                return True
                
            return False
            
    def wait_time(self, amount: int = 1) -> float:
        """Calculate time to wait for capacity."""
        with self._lock:
            if self.level + amount <= self.capacity:
                return 0
                
            overflow = (self.level + amount) - self.capacity
            return overflow / self.leak_rate


class SlidingWindowLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_size: float):
        """Initialize sliding window limiter."""
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = deque()
        self._lock = threading.RLock()
        
    def acquire(self) -> bool:
        """Try to make a request."""
        with self._lock:
            now = time.time()
            
            # Remove expired requests
            while self.requests and self.requests[0] < now - self.window_size:
                self.requests.popleft()
                
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
                
            return False
            
    def wait_time(self) -> float:
        """Calculate time to wait for next request."""
        with self._lock:
            if len(self.requests) < self.max_requests:
                return 0
                
            oldest_request = self.requests[0]
            return (oldest_request + self.window_size) - time.time()


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load."""
    
    def __init__(self, base_config: RateLimitConfig):
        """Initialize adaptive rate limiter."""
        self.base_config = base_config
        self.current_limit = base_config.max_requests
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = time.time()
        self.adjustment_interval = 60.0  # seconds
        self._lock = threading.RLock()
        
        # Create underlying limiter
        self.limiter = TokenBucket(base_config.max_requests, 
                                 base_config.max_requests / base_config.time_window)
        
    def acquire(self) -> bool:
        """Try to acquire with adaptive adjustment."""
        with self._lock:
            # Check if we need to adjust limits
            self._adjust_limits()
            
            return self.limiter.acquire()
            
    def report_success(self):
        """Report successful operation."""
        with self._lock:
            self.success_count += 1
            
    def report_failure(self):
        """Report failed operation."""
        with self._lock:
            self.failure_count += 1
            
    def _adjust_limits(self):
        """Adjust rate limits based on success/failure rates."""
        now = time.time()
        if now - self.last_adjustment < self.adjustment_interval:
            return
            
        total_requests = self.success_count + self.failure_count
        if total_requests == 0:
            return
            
        success_rate = self.success_count / total_requests
        
        # Increase limit if success rate is high
        if success_rate > 0.9:
            new_limit = min(self.current_limit * 1.2, self.base_config.max_requests * 2)
        # Decrease limit if success rate is low
        elif success_rate < self.base_config.adaptive_threshold:
            new_limit = max(self.current_limit * 0.8, self.base_config.max_requests * 0.1)
        else:
            new_limit = self.current_limit
            
        if new_limit != self.current_limit:
            self.current_limit = int(new_limit)
            self.limiter = TokenBucket(self.current_limit,
                                     self.current_limit / self.base_config.time_window)
            logger.info(f"Adjusted rate limit to {self.current_limit} (success rate: {success_rate:.2%})")
            
        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = now


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and hierarchical limits."""
    
    def __init__(self):
        """Initialize advanced rate limiter."""
        self.limiters: Dict[str, Any] = {}
        self.hierarchical_limits: Dict[str, Dict[str, RateLimitConfig]] = defaultdict(dict)
        self.global_limiters: Dict[str, Any] = {}
        self.backoff_times: Dict[str, float] = defaultdict(float)
        self._lock = threading.RLock()
        
    def add_limiter(self, 
                   name: str,
                   config: RateLimitConfig,
                   scope: str = "default") -> None:
        """Add a rate limiter."""
        with self._lock:
            key = f"{scope}:{name}"
            
            if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                limiter = TokenBucket(config.max_requests + config.burst_allowance,
                                    config.max_requests / config.time_window)
            elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
                limiter = LeakyBucket(config.max_requests + config.burst_allowance,
                                    config.max_requests / config.time_window)
            elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                limiter = SlidingWindowLimiter(config.max_requests, config.time_window)
            elif config.algorithm == RateLimitAlgorithm.ADAPTIVE:
                limiter = AdaptiveRateLimiter(config)
            else:  # Fixed window
                limiter = SlidingWindowLimiter(config.max_requests, config.time_window)
                
            self.limiters[key] = limiter
            logger.info(f"Added {config.algorithm.value} rate limiter: {key}")
            
    def add_hierarchical_limit(self,
                              user_id: str,
                              resource: str, 
                              config: RateLimitConfig) -> None:
        """Add hierarchical rate limit (per-user, per-resource)."""
        with self._lock:
            self.hierarchical_limits[user_id][resource] = config
            
    def check_limits(self, 
                    name: str,
                    scope: str = "default",
                    user_id: Optional[str] = None,
                    resource: Optional[str] = None) -> bool:
        """Check if request is allowed by all applicable limits."""
        with self._lock:
            key = f"{scope}:{name}"
            
            # Check main limiter
            if key in self.limiters:
                if not self.limiters[key].acquire():
                    return False
                    
            # Check hierarchical limits
            if user_id and resource:
                if user_id in self.hierarchical_limits:
                    if resource in self.hierarchical_limits[user_id]:
                        config = self.hierarchical_limits[user_id][resource]
                        user_key = f"user:{user_id}:{resource}"
                        
                        if user_key not in self.limiters:
                            self.add_limiter(f"{user_id}:{resource}", config, "user")
                            
                        if not self.limiters[user_key].acquire():
                            return False
                            
            # Check global limiters
            for global_key, limiter in self.global_limiters.items():
                if not limiter.acquire():
                    return False
                    
            return True
            
    def wait_time(self, 
                 name: str,
                 scope: str = "default",
                 user_id: Optional[str] = None,
                 resource: Optional[str] = None) -> float:
        """Calculate minimum wait time for all applicable limits."""
        with self._lock:
            max_wait = 0.0
            key = f"{scope}:{name}"
            
            # Check main limiter
            if key in self.limiters:
                wait_time = getattr(self.limiters[key], 'wait_time', lambda: 0)()
                max_wait = max(max_wait, wait_time)
                
            # Check hierarchical limits  
            if user_id and resource:
                if user_id in self.hierarchical_limits:
                    if resource in self.hierarchical_limits[user_id]:
                        user_key = f"user:{user_id}:{resource}"
                        if user_key in self.limiters:
                            wait_time = getattr(self.limiters[user_key], 'wait_time', lambda: 0)()
                            max_wait = max(max_wait, wait_time)
                            
            return max_wait
            
    def acquire_with_backoff(self,
                           name: str,
                           scope: str = "default",
                           user_id: Optional[str] = None,
                           resource: Optional[str] = None,
                           max_attempts: int = 3) -> bool:
        """Acquire with exponential backoff."""
        key = f"{scope}:{name}:{user_id}:{resource}"
        
        for attempt in range(max_attempts):
            if self.check_limits(name, scope, user_id, resource):
                # Reset backoff on success
                self.backoff_times[key] = 0
                return True
                
            if attempt < max_attempts - 1:
                # Calculate backoff time
                if key not in self.backoff_times:
                    self.backoff_times[key] = 1.0
                else:
                    config = self._get_config(name, scope)
                    if config:
                        self.backoff_times[key] = min(
                            self.backoff_times[key] * config.backoff_factor,
                            config.max_backoff
                        )
                        
                logger.debug(f"Rate limited, backing off for {self.backoff_times[key]:.2f}s")
                time.sleep(self.backoff_times[key])
                
        return False
        
    def _get_config(self, name: str, scope: str) -> Optional[RateLimitConfig]:
        """Get configuration for a limiter."""
        # This would need to be implemented to store configs
        return None
        
    def decorator(self, 
                 name: str,
                 scope: str = "default",
                 user_id_param: Optional[str] = None,
                 resource_param: Optional[str] = None,
                 raise_on_limit: bool = True):
        """Decorator for rate limiting functions."""
        def decorator_wrapper(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Extract user_id and resource from parameters
                user_id = kwargs.get(user_id_param) if user_id_param else None
                resource = kwargs.get(resource_param) if resource_param else None
                
                if self.check_limits(name, scope, user_id, resource):
                    try:
                        result = func(*args, **kwargs)
                        # Report success for adaptive limiters
                        key = f"{scope}:{name}"
                        if key in self.limiters:
                            limiter = self.limiters[key]
                            if hasattr(limiter, 'report_success'):
                                limiter.report_success()
                        return result
                    except Exception as e:
                        # Report failure for adaptive limiters
                        key = f"{scope}:{name}"
                        if key in self.limiters:
                            limiter = self.limiters[key]
                            if hasattr(limiter, 'report_failure'):
                                limiter.report_failure()
                        raise
                else:
                    if raise_on_limit:
                        wait_time = self.wait_time(name, scope, user_id, resource)
                        raise RateLimitExceeded(
                            f"Rate limit exceeded for {name}",
                            retry_after=wait_time
                        )
                    return None
                    
            return wrapper
        return decorator_wrapper
        
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            stats = {
                'total_limiters': len(self.limiters),
                'hierarchical_users': len(self.hierarchical_limits),
                'global_limiters': len(self.global_limiters),
                'active_backoffs': len([t for t in self.backoff_times.values() if t > 0])
            }
            
            # Add per-limiter stats
            limiter_stats = {}
            for key, limiter in self.limiters.items():
                if hasattr(limiter, 'tokens'):
                    limiter_stats[key] = {
                        'type': 'token_bucket',
                        'tokens': limiter.tokens,
                        'max_tokens': limiter.max_tokens
                    }
                elif hasattr(limiter, 'level'):
                    limiter_stats[key] = {
                        'type': 'leaky_bucket', 
                        'level': limiter.level,
                        'capacity': limiter.capacity
                    }
                elif hasattr(limiter, 'requests'):
                    limiter_stats[key] = {
                        'type': 'sliding_window',
                        'current_requests': len(limiter.requests),
                        'max_requests': limiter.max_requests
                    }
                    
            stats['limiters'] = limiter_stats
            return stats


# Global rate limiter instance
_global_rate_limiter = None


def get_global_rate_limiter() -> AdvancedRateLimiter:
    """Get the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = AdvancedRateLimiter()
    return _global_rate_limiter


def rate_limit(name: str,
              max_requests: int,
              time_window: float,
              algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET,
              scope: str = "default"):
    """Decorator for easy rate limiting."""
    limiter = get_global_rate_limiter()
    
    config = RateLimitConfig(
        max_requests=max_requests,
        time_window=time_window,
        algorithm=algorithm
    )
    
    limiter.add_limiter(name, config, scope)
    
    return limiter.decorator(name, scope)
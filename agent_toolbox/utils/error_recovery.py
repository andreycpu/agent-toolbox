"""Error recovery patterns including circuit breaker, retry, and fallback strategies."""

import time
import random
import threading
from typing import Callable, Any, Optional, Dict, List, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryStrategy(Enum):
    """Retry strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    JITTER = "jitter"


@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    stop_on: List[Type[Exception]] = field(default_factory=list)
    
    
@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3  # For half-open state
    monitoring_window: float = 300.0  # 5 minutes
    expected_exception: Type[Exception] = Exception


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanism."""
    
    fallback_func: Optional[Callable] = None
    fallback_value: Any = None
    cache_fallback: bool = True
    async_fallback: bool = False


class RetryMechanism:
    """Retry mechanism with multiple strategies."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should stop on this exception
                if any(isinstance(e, exc_type) for exc_type in self.config.stop_on):
                    logger.info(f"Stopping retry due to {type(e).__name__}: {str(e)}")
                    raise e
                    
                # Check if this exception should trigger retry
                if not any(isinstance(e, exc_type) for exc_type in self.config.exceptions):
                    logger.info(f"Not retrying for {type(e).__name__}: {str(e)}")
                    raise e
                    
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with {type(e).__name__}: {str(e)}. "
                                 f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    
        logger.error(f"All {self.config.max_attempts} attempts failed")
        if last_exception:
            raise last_exception
            
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy."""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci_delay(attempt)
        elif self.config.strategy == RetryStrategy.JITTER:
            base_delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
            delay = base_delay + random.uniform(0, base_delay * 0.1)
        else:
            delay = self.config.base_delay
            
        # Apply jitter if enabled
        if self.config.jitter and self.config.strategy != RetryStrategy.JITTER:
            jitter = random.uniform(-delay * 0.1, delay * 0.1)
            delay += jitter
            
        return min(delay, self.config.max_delay)
        
    def _fibonacci_delay(self, attempt: int) -> float:
        """Calculate Fibonacci-based delay."""
        if attempt == 0:
            return self.config.base_delay
        elif attempt == 1:
            return self.config.base_delay
            
        a, b = 1, 1
        for _ in range(attempt - 1):
            a, b = b, a + b
            
        return self.config.base_delay * b


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.failure_times = []
        self._lock = threading.RLock()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        with self._lock:
            self._update_state()
            
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open. Last failure: {self.last_failure_time}"
                )
                
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except Exception as e:
                if isinstance(e, self.config.expected_exception):
                    self._on_failure()
                raise e
                
    def _update_state(self):
        """Update circuit breaker state."""
        now = time.time()
        
        # Clean old failures outside monitoring window
        cutoff_time = now - self.config.monitoring_window
        self.failure_times = [t for t in self.failure_times if t > cutoff_time]
        self.failure_count = len(self.failure_times)
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                now - self.last_failure_time >= self.config.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")
                
        elif self.state == CircuitState.HALF_OPEN:
            # Check if enough successes to close circuit
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.failure_times = []
                logger.info("Circuit breaker closed after successful recovery")
                
    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self.failure_count = max(0, self.failure_count - 1)
            
    def _on_failure(self):
        """Handle failed execution."""
        now = time.time()
        self.failure_times.append(now)
        self.failure_count += 1
        self.last_failure_time = now
        
        if (self.state == CircuitState.CLOSED and 
            self.failure_count >= self.config.failure_threshold):
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened due to {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state opens the circuit
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning("Circuit breaker opened from HALF_OPEN state")
            
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        with self._lock:
            self._update_state()
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time,
                'time_until_retry': (
                    max(0, self.config.recovery_timeout - (time.time() - self.last_failure_time))
                    if self.last_failure_time and self.state == CircuitState.OPEN
                    else 0
                )
            }
            
    def reset(self):
        """Reset circuit breaker to closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.failure_times = []
            logger.info("Circuit breaker reset to CLOSED state")


class FallbackMechanism:
    """Fallback mechanism for graceful degradation."""
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self._cache = {}
        self._lock = threading.RLock()
        
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with fallback on failure."""
        cache_key = self._generate_cache_key(func, args, kwargs)
        
        try:
            result = func(*args, **kwargs)
            
            # Cache successful result for fallback
            if self.config.cache_fallback:
                with self._lock:
                    self._cache[cache_key] = result
                    
            return result
            
        except Exception as e:
            logger.warning(f"Primary function failed: {str(e)}. Attempting fallback...")
            
            # Try cached result first
            if self.config.cache_fallback:
                with self._lock:
                    if cache_key in self._cache:
                        logger.info("Using cached fallback result")
                        return self._cache[cache_key]
                        
            # Try fallback function
            if self.config.fallback_func:
                try:
                    if self.config.async_fallback:
                        import asyncio
                        if asyncio.iscoroutinefunction(self.config.fallback_func):
                            # Run async fallback in thread
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run, 
                                    self.config.fallback_func(*args, **kwargs)
                                )
                                result = future.result()
                        else:
                            result = self.config.fallback_func(*args, **kwargs)
                    else:
                        result = self.config.fallback_func(*args, **kwargs)
                        
                    logger.info("Fallback function succeeded")
                    return result
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback function also failed: {str(fallback_error)}")
                    
            # Return fallback value if available
            if self.config.fallback_value is not None:
                logger.info("Using fallback value")
                return self.config.fallback_value
                
            # If no fallback available, re-raise original exception
            raise e
            
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call."""
        func_name = getattr(func, '__name__', str(func))
        args_hash = hash(str(args) + str(sorted(kwargs.items())))
        return f"{func_name}:{args_hash}"
        
    def clear_cache(self):
        """Clear fallback cache."""
        with self._lock:
            self._cache.clear()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class ErrorRecovery:
    """Comprehensive error recovery system."""
    
    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 circuit_config: Optional[CircuitBreakerConfig] = None,
                 fallback_config: Optional[FallbackConfig] = None):
        """Initialize error recovery system."""
        
        self.retry_mechanism = RetryMechanism(retry_config) if retry_config else None
        self.circuit_breaker = CircuitBreaker(circuit_config) if circuit_config else None
        self.fallback_mechanism = FallbackMechanism(fallback_config) if fallback_config else None
        
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retries_used': 0,
            'circuit_breaker_opens': 0,
            'fallbacks_used': 0
        }
        self._lock = threading.RLock()
        
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with comprehensive error recovery."""
        
        with self._lock:
            self.stats['total_calls'] += 1
            
        def wrapped_func(*args, **kwargs):
            # Execute through circuit breaker if available
            if self.circuit_breaker:
                try:
                    return self.circuit_breaker.call(func, *args, **kwargs)
                except CircuitBreakerOpenError:
                    with self._lock:
                        self.stats['circuit_breaker_opens'] += 1
                    raise
            else:
                return func(*args, **kwargs)
                
        try:
            # Apply retry mechanism if available
            if self.retry_mechanism:
                original_attempt_count = 0
                
                def counting_func(*args, **kwargs):
                    nonlocal original_attempt_count
                    original_attempt_count += 1
                    if original_attempt_count > 1:
                        with self._lock:
                            self.stats['retries_used'] += 1
                    return wrapped_func(*args, **kwargs)
                    
                result = self.retry_mechanism.execute(counting_func, *args, **kwargs)
            else:
                result = wrapped_func(*args, **kwargs)
                
            with self._lock:
                self.stats['successful_calls'] += 1
            return result
            
        except Exception as e:
            with self._lock:
                self.stats['failed_calls'] += 1
                
            # Try fallback mechanism if available
            if self.fallback_mechanism:
                try:
                    result = self.fallback_mechanism.execute(func, *args, **kwargs)
                    with self._lock:
                        self.stats['fallbacks_used'] += 1
                        self.stats['successful_calls'] += 1
                    return result
                except Exception:
                    # Fallback also failed, re-raise original exception
                    pass
                    
            raise e
            
    def get_stats(self) -> Dict[str, Any]:
        """Get error recovery statistics."""
        with self._lock:
            stats = self.stats.copy()
            
            if stats['total_calls'] > 0:
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls']
                stats['failure_rate'] = stats['failed_calls'] / stats['total_calls']
            else:
                stats['success_rate'] = 0
                stats['failure_rate'] = 0
                
            # Add circuit breaker stats if available
            if self.circuit_breaker:
                stats['circuit_breaker'] = self.circuit_breaker.get_state()
                
            return stats
            
    def reset_stats(self):
        """Reset statistics."""
        with self._lock:
            self.stats = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'retries_used': 0,
                'circuit_breaker_opens': 0,
                'fallbacks_used': 0
            }
            
    def reset_circuit_breaker(self):
        """Reset circuit breaker if available."""
        if self.circuit_breaker:
            self.circuit_breaker.reset()


def with_retry(max_attempts: int = 3,
              strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
              base_delay: float = 1.0,
              exceptions: List[Type[Exception]] = None):
    """Decorator for retry functionality."""
    
    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        exceptions=exceptions or [Exception]
    )
    
    retry_mechanism = RetryMechanism(config)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return retry_mechanism.execute(func, *args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(failure_threshold: int = 5,
                        recovery_timeout: float = 60.0,
                        expected_exception: Type[Exception] = Exception):
    """Decorator for circuit breaker functionality."""
    
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )
    
    circuit_breaker = CircuitBreaker(config)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def with_fallback(fallback_func: Optional[Callable] = None,
                 fallback_value: Any = None):
    """Decorator for fallback functionality."""
    
    config = FallbackConfig(
        fallback_func=fallback_func,
        fallback_value=fallback_value
    )
    
    fallback_mechanism = FallbackMechanism(config)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return fallback_mechanism.execute(func, *args, **kwargs)
        return wrapper
    return decorator


def resilient(retry_attempts: int = 3,
             circuit_breaker_threshold: int = 5,
             fallback_value: Any = None):
    """Decorator combining all error recovery mechanisms."""
    
    retry_config = RetryConfig(max_attempts=retry_attempts)
    circuit_config = CircuitBreakerConfig(failure_threshold=circuit_breaker_threshold)
    fallback_config = FallbackConfig(fallback_value=fallback_value)
    
    recovery = ErrorRecovery(retry_config, circuit_config, fallback_config)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return recovery.execute(func, *args, **kwargs)
        return wrapper
    return decorator
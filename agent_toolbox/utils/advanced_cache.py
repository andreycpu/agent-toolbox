"""Advanced caching with multiple strategies and layers."""

import time
import hashlib
import pickle
import json
import threading
from typing import Any, Optional, Dict, Callable, Union, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on access patterns


class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"
    FILE = "file"
    SQLITE = "sqlite"


@dataclass
class CacheConfig:
    """Cache configuration."""
    
    max_size: int = 1000
    default_ttl: float = 3600.0  # 1 hour
    strategy: CacheStrategy = CacheStrategy.LRU
    backend: CacheBackend = CacheBackend.MEMORY
    
    # Advanced options
    lazy_expiration: bool = True
    compression: bool = False
    serialization: str = "pickle"  # pickle, json, msgpack
    
    # Multi-level cache
    l1_cache: Optional['CacheConfig'] = None
    l2_cache: Optional['CacheConfig'] = None
    
    # Distributed cache
    consistency_model: str = "eventual"  # strong, eventual, none
    
    def __post_init__(self):
        if self.l1_cache and not self.l2_cache:
            # Auto-configure L2 cache
            self.l2_cache = CacheConfig(
                max_size=self.max_size * 10,
                default_ttl=self.default_ttl * 2,
                backend=CacheBackend.FILE
            )


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
        
    @property
    def age(self) -> float:
        """Get entry age in seconds."""
        return time.time() - self.created_at
        
    def touch(self):
        """Update last access time and increment count."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackendInterface(ABC):
    """Abstract interface for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
        
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set key-value pair."""
        pass
        
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key."""
        pass
        
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        pass
        
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all keys."""
        pass
        
    @abstractmethod
    def size(self) -> int:
        """Get number of entries."""
        pass


class MemoryCacheBackend(CacheBackendInterface):
    """In-memory cache backend."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.store: Dict[str, CacheEntry] = {}
        self.access_order = OrderedDict()  # For LRU
        self.frequency_counter: Dict[str, int] = {}  # For LFU
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.store:
                return None
                
            entry = self.store[key]
            
            # Check expiration
            if entry.is_expired:
                if self.config.lazy_expiration:
                    self._evict(key)
                    return None
                    
            # Update access patterns
            entry.touch()
            self._update_access_patterns(key)
            
            return entry.value
            
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        with self._lock:
            # Calculate size
            try:
                size = len(pickle.dumps(value)) if self.config.serialization == "pickle" else len(str(value))
            except:
                size = 0
                
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl or self.config.default_ttl,
                size=size
            )
            
            # Evict if necessary
            if len(self.store) >= self.config.max_size and key not in self.store:
                self._evict_lru()
                
            # Store entry
            self.store[key] = entry
            self._update_access_patterns(key)
            
            logger.debug(f"Cached {key} (size: {size} bytes)")
            return True
            
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self.store:
                self._evict(key)
                return True
            return False
            
    def clear(self) -> None:
        with self._lock:
            self.store.clear()
            self.access_order.clear()
            self.frequency_counter.clear()
            
    def keys(self) -> List[str]:
        with self._lock:
            return list(self.store.keys())
            
    def size(self) -> int:
        with self._lock:
            return len(self.store)
            
    def _update_access_patterns(self, key: str):
        """Update access patterns for eviction strategies."""
        # Update LRU order
        if key in self.access_order:
            del self.access_order[key]
        self.access_order[key] = time.time()
        
        # Update LFU frequency
        self.frequency_counter[key] = self.frequency_counter.get(key, 0) + 1
        
    def _evict(self, key: str):
        """Evict a specific key."""
        if key in self.store:
            del self.store[key]
        if key in self.access_order:
            del self.access_order[key]
        if key in self.frequency_counter:
            del self.frequency_counter[key]
            
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.access_order:
            return
            
        if self.config.strategy == CacheStrategy.LRU:
            oldest_key = next(iter(self.access_order))
            self._evict(oldest_key)
        elif self.config.strategy == CacheStrategy.LFU:
            # Find least frequently used
            min_freq = min(self.frequency_counter.values()) if self.frequency_counter else 0
            lfu_keys = [k for k, v in self.frequency_counter.items() if v == min_freq]
            if lfu_keys:
                self._evict(lfu_keys[0])
        elif self.config.strategy == CacheStrategy.FIFO:
            # Evict oldest by creation time
            oldest_key = min(self.store.keys(), key=lambda k: self.store[k].created_at)
            self._evict(oldest_key)
        elif self.config.strategy == CacheStrategy.TTL:
            # Evict expired entries first
            now = time.time()
            expired_keys = [k for k, v in self.store.items() if v.is_expired]
            if expired_keys:
                self._evict(expired_keys[0])
            else:
                # Fall back to LRU
                oldest_key = next(iter(self.access_order))
                self._evict(oldest_key)


class RedisCacheBackend(CacheBackendInterface):
    """Redis cache backend."""
    
    def __init__(self, config: CacheConfig, host: str = "localhost", port: int = 6379):
        self.config = config
        try:
            import redis
            self.client = redis.Redis(host=host, port=port, decode_responses=False)
            self.client.ping()  # Test connection
        except ImportError:
            raise ImportError("redis package required for Redis backend")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
            
    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(key)
            if data is None:
                return None
                
            if self.config.serialization == "pickle":
                return pickle.loads(data)
            elif self.config.serialization == "json":
                return json.loads(data.decode('utf-8'))
            else:
                return data.decode('utf-8')
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
            
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        try:
            if self.config.serialization == "pickle":
                data = pickle.dumps(value)
            elif self.config.serialization == "json":
                data = json.dumps(value).encode('utf-8')
            else:
                data = str(value).encode('utf-8')
                
            ttl = ttl or self.config.default_ttl
            return self.client.setex(key, int(ttl), data)
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
            
    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
            
    def clear(self) -> None:
        try:
            self.client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {str(e)}")
            
    def keys(self) -> List[str]:
        try:
            return [k.decode('utf-8') for k in self.client.keys()]
        except Exception as e:
            logger.error(f"Redis keys error: {str(e)}")
            return []
            
    def size(self) -> int:
        try:
            return self.client.dbsize()
        except Exception as e:
            logger.error(f"Redis size error: {str(e)}")
            return 0


class FileCacheBackend(CacheBackendInterface):
    """File-based cache backend."""
    
    def __init__(self, config: CacheConfig, cache_dir: str = "/tmp/agent_cache"):
        self.config = config
        self.cache_dir = cache_dir
        self._lock = threading.RLock()
        
        import os
        os.makedirs(cache_dir, exist_ok=True)
        
    def _get_file_path(self, key: str) -> str:
        """Get file path for key."""
        # Use hash to avoid filesystem issues
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{self.cache_dir}/{key_hash}.cache"
        
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                import os
                if not os.path.exists(file_path):
                    return None
                    
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    
                # Check expiration
                if 'ttl' in data and time.time() - data['created_at'] > data['ttl']:
                    os.remove(file_path)
                    return None
                    
                return data['value']
                
            except Exception as e:
                logger.error(f"File cache get error: {str(e)}")
                return None
                
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                data = {
                    'key': key,
                    'value': value,
                    'created_at': time.time(),
                    'ttl': ttl or self.config.default_ttl
                }
                
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
                    
                return True
                
            except Exception as e:
                logger.error(f"File cache set error: {str(e)}")
                return False
                
    def delete(self, key: str) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                import os
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                return False
                
            except Exception as e:
                logger.error(f"File cache delete error: {str(e)}")
                return False
                
    def clear(self) -> None:
        with self._lock:
            try:
                import os
                import glob
                cache_files = glob.glob(f"{self.cache_dir}/*.cache")
                for file_path in cache_files:
                    os.remove(file_path)
                    
            except Exception as e:
                logger.error(f"File cache clear error: {str(e)}")
                
    def keys(self) -> List[str]:
        with self._lock:
            keys = []
            try:
                import os
                import glob
                cache_files = glob.glob(f"{self.cache_dir}/*.cache")
                
                for file_path in cache_files:
                    try:
                        with open(file_path, 'rb') as f:
                            data = pickle.load(f)
                            keys.append(data.get('key', ''))
                    except:
                        continue
                        
            except Exception as e:
                logger.error(f"File cache keys error: {str(e)}")
                
            return keys
            
    def size(self) -> int:
        with self._lock:
            try:
                import glob
                cache_files = glob.glob(f"{self.cache_dir}/*.cache")
                return len(cache_files)
            except Exception as e:
                logger.error(f"File cache size error: {str(e)}")
                return 0


class MultiLevelCache:
    """Multi-level cache with L1 and L2 layers."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        
        # Initialize L1 cache (fast, small)
        if config.l1_cache:
            self.l1 = self._create_backend(config.l1_cache)
        else:
            l1_config = CacheConfig(
                max_size=min(config.max_size, 100),
                default_ttl=config.default_ttl,
                backend=CacheBackend.MEMORY
            )
            self.l1 = self._create_backend(l1_config)
            
        # Initialize L2 cache (slower, larger)
        if config.l2_cache:
            self.l2 = self._create_backend(config.l2_cache)
        else:
            l2_config = CacheConfig(
                max_size=config.max_size * 10,
                default_ttl=config.default_ttl * 2,
                backend=CacheBackend.FILE
            )
            self.l2 = self._create_backend(l2_config)
            
        self.stats = {
            'l1_hits': 0,
            'l1_misses': 0,
            'l2_hits': 0,
            'l2_misses': 0,
            'promotions': 0
        }
        
    def _create_backend(self, config: CacheConfig) -> CacheBackendInterface:
        """Create cache backend based on config."""
        if config.backend == CacheBackend.MEMORY:
            return MemoryCacheBackend(config)
        elif config.backend == CacheBackend.REDIS:
            return RedisCacheBackend(config)
        elif config.backend == CacheBackend.FILE:
            return FileCacheBackend(config)
        else:
            raise ValueError(f"Unsupported backend: {config.backend}")
            
    def get(self, key: str) -> Optional[Any]:
        """Get value with multi-level lookup."""
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value
            
        self.stats['l1_misses'] += 1
        
        # Try L2
        value = self.l2.get(key)
        if value is not None:
            self.stats['l2_hits'] += 1
            # Promote to L1
            self.l1.set(key, value)
            self.stats['promotions'] += 1
            return value
            
        self.stats['l2_misses'] += 1
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in both levels."""
        # Set in L1 first
        l1_success = self.l1.set(key, value, ttl)
        
        # Set in L2
        l2_success = self.l2.set(key, value, ttl)
        
        return l1_success or l2_success
        
    def delete(self, key: str) -> bool:
        """Delete from both levels."""
        l1_deleted = self.l1.delete(key)
        l2_deleted = self.l2.delete(key)
        return l1_deleted or l2_deleted
        
    def clear(self) -> None:
        """Clear both levels."""
        self.l1.clear()
        self.l2.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = (self.stats['l1_hits'] + self.stats['l1_misses'] + 
                         self.stats['l2_hits'] + self.stats['l2_misses'])
        
        if total_requests > 0:
            hit_rate = (self.stats['l1_hits'] + self.stats['l2_hits']) / total_requests
            l1_hit_rate = self.stats['l1_hits'] / total_requests
        else:
            hit_rate = 0
            l1_hit_rate = 0
            
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'l1_hit_rate': l1_hit_rate,
            'l1_size': self.l1.size(),
            'l2_size': self.l2.size()
        }


class AdvancedCache:
    """Advanced cache with multiple strategies and features."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        
        # Create cache backend
        if config.l1_cache or config.l2_cache:
            self.backend = MultiLevelCache(config)
        else:
            self.backend = self._create_backend(config)
            
        self._lock = threading.RLock()
        
    def _create_backend(self, config: CacheConfig) -> CacheBackendInterface:
        """Create single cache backend."""
        if config.backend == CacheBackend.MEMORY:
            return MemoryCacheBackend(config)
        elif config.backend == CacheBackend.REDIS:
            return RedisCacheBackend(config)
        elif config.backend == CacheBackend.FILE:
            return FileCacheBackend(config)
        else:
            raise ValueError(f"Unsupported backend: {config.backend}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        value = self.backend.get(key)
        return value if value is not None else default
        
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set key-value pair."""
        return self.backend.set(key, value, ttl)
        
    def delete(self, key: str) -> bool:
        """Delete key."""
        return self.backend.delete(key)
        
    def clear(self) -> None:
        """Clear all entries."""
        self.backend.clear()
        
    def memoize(self, ttl: Optional[float] = None, key_func: Optional[Callable] = None):
        """Decorator for function memoization."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                    
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                    
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
                
            return wrapper
        return decorator
        
    def cache_aside(self, 
                   key: str,
                   loader_func: Callable[[], Any],
                   ttl: Optional[float] = None) -> Any:
        """Cache-aside pattern implementation."""
        # Try to get from cache
        value = self.get(key)
        if value is not None:
            return value
            
        # Load from source
        value = loader_func()
        
        # Cache the result
        self.set(key, value, ttl)
        return value
        
    def write_through(self,
                     key: str,
                     value: Any,
                     writer_func: Callable[[str, Any], None],
                     ttl: Optional[float] = None) -> bool:
        """Write-through pattern implementation."""
        # Write to both cache and backing store
        cache_success = self.set(key, value, ttl)
        
        try:
            writer_func(key, value)
            return cache_success
        except Exception as e:
            # Remove from cache if write fails
            self.delete(key)
            raise e
            
    def write_behind(self,
                    key: str,
                    value: Any,
                    writer_func: Callable[[str, Any], None],
                    ttl: Optional[float] = None,
                    delay: float = 1.0) -> bool:
        """Write-behind pattern implementation."""
        # Write to cache immediately
        cache_success = self.set(key, value, ttl)
        
        # Schedule async write to backing store
        import threading
        
        def delayed_write():
            time.sleep(delay)
            try:
                writer_func(key, value)
            except Exception as e:
                logger.error(f"Write-behind failed for key {key}: {str(e)}")
                
        thread = threading.Thread(target=delayed_write)
        thread.daemon = True
        thread.start()
        
        return cache_success
        
    def bulk_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys at once."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
        
    def bulk_set(self, items: Dict[str, Any], ttl: Optional[float] = None) -> int:
        """Set multiple key-value pairs."""
        success_count = 0
        for key, value in items.items():
            if self.set(key, value, ttl):
                success_count += 1
        return success_count
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self.backend, 'get_stats'):
            return self.backend.get_stats()
        else:
            return {
                'size': self.backend.size(),
                'backend': self.config.backend.value
            }


# Global cache instance
_global_cache = None


def get_global_cache() -> AdvancedCache:
    """Get the global cache instance."""
    global _global_cache
    if _global_cache is None:
        config = CacheConfig()
        _global_cache = AdvancedCache(config)
    return _global_cache


def cached(ttl: Optional[float] = None, key_func: Optional[Callable] = None):
    """Simple caching decorator using global cache."""
    cache = get_global_cache()
    return cache.memoize(ttl, key_func)
"""Caching utilities for agent tasks."""

import time
import pickle
import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Dict, Callable, Union
import functools
import threading


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 3600):
        """Initialize cache with default TTL in seconds."""
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
                
            entry = self._cache[key]
            
            # Check if expired
            if entry['expires_at'] < time.time():
                del self._cache[key]
                return None
                
            return entry['value']
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
            
        expires_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
            
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry['expires_at'] < current_time:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self._cache[key]
                
        return len(expired_keys)
        
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'entries': len(self._cache),
                'memory_usage_bytes': len(str(self._cache).encode('utf-8'))
            }


class FileCache:
    """File-based cache with persistence."""
    
    def __init__(self, cache_dir: Union[str, Path] = ".cache", default_ttl: int = 3600):
        """Initialize file cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                entry = pickle.load(f)
                
            # Check if expired
            if entry['expires_at'] < time.time():
                cache_path.unlink()
                return None
                
            return entry['value']
        except (pickle.PickleError, FileNotFoundError, KeyError):
            return None
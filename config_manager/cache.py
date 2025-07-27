"""
Configuration caching system for ConfigManager.

This module provides caching capabilities to improve performance,
especially for remote configuration sources and expensive operations.
"""

import time
import threading
import pickle
import hashlib
import json
from typing import Any, Dict, Optional, Union, Protocol, runtime_checkable
from pathlib import Path
from abc import ABC, abstractmethod


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for cache backend implementations."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in the cache with optional TTL."""
        ...
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        ...
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        ...
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        ...


class CacheEntry:
    """Represents a cached configuration entry with metadata."""
    
    def __init__(self, value: Any, ttl: Optional[float] = None):
        """
        Initialize a cache entry.
        
        Args:
            value: The cached value.
            ttl: Time to live in seconds (None for no expiration).
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Access the cached value and update metadata."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def __repr__(self) -> str:
        return f"CacheEntry(ttl={self.ttl}, accessed={self.access_count}x, age={time.time() - self.created_at:.1f}s)"


class MemoryCache(CacheBackend):
    """In-memory cache backend with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of entries to store.
            default_ttl: Default TTL in seconds for entries without explicit TTL.
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in the cache."""
        with self._lock:
            # Use default TTL if none specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Evict if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        with self._lock:
            self._cache.clear()
    
    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired():
                del self._cache[key]
                return False
            
            return True
    
    def has_key(self, key: str) -> bool:
        """Alias for exists method."""
        return self.exists(key)
    
    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'valid_entries': total_entries - expired_entries,
                'max_size': self.max_size,
                'total_accesses': total_accesses,
                'hit_ratio': 0.0 if total_accesses == 0 else 
                           sum(entry.access_count for entry in self._cache.values() 
                               if not entry.is_expired()) / total_accesses
            }


class FileCache(CacheBackend):
    """File-based cache backend for persistent caching."""
    
    def __init__(self, cache_dir: Union[str, Path] = ".config_cache", 
                 default_ttl: Optional[float] = None, 
                 max_files: int = 1000):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files.
            default_ttl: Default TTL in seconds.
            max_files: Maximum number of cache files.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.max_files = max_files
        self._lock = threading.RLock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Create a safe filename from the key
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the file cache."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                entry_data = pickle.load(f)
            
            entry = CacheEntry(entry_data['value'], entry_data['ttl'])
            entry.created_at = entry_data['created_at']
            entry.access_count = entry_data['access_count']
            entry.last_accessed = entry_data['last_accessed']
            
            if entry.is_expired():
                cache_path.unlink(missing_ok=True)
                return None
            
            # Update access metadata
            entry.access()
            self._save_entry(key, entry)
            
            return entry.value
            
        except (IOError, pickle.PickleError, KeyError):
            # Remove corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in the file cache."""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # Clean up old files if at max
            self._cleanup_if_needed()
            
            entry = CacheEntry(value, ttl)
            self._save_entry(key, entry)
    
    def _save_entry(self, key: str, entry: CacheEntry) -> None:
        """Save a cache entry to file."""
        cache_path = self._get_cache_path(key)
        
        try:
            entry_data = {
                'value': entry.value,
                'ttl': entry.ttl,
                'created_at': entry.created_at,
                'access_count': entry.access_count,
                'last_accessed': entry.last_accessed
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(entry_data, f)
        except (IOError, pickle.PickleError):
            # Ignore errors saving cache
            pass
    
    def delete(self, key: str) -> None:
        """Delete a value from the file cache."""
        cache_path = self._get_cache_path(key)
        cache_path.unlink(missing_ok=True)
    
    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
    
    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        return self.get(key) is not None
    
    def has_key(self, key: str) -> bool:
        """Alias for exists method."""
        return self.exists(key)
    
    def _cleanup_expired(self) -> None:
        """Clean up expired cache files."""
        with self._lock:
            cache_files = list(self.cache_dir.glob("*.cache"))
            for cache_file in cache_files:
                # Try to load and check expiration
                try:
                    with open(cache_file, 'rb') as f:
                        entry_data = pickle.load(f)
                    
                    entry = CacheEntry(entry_data['value'], entry_data['ttl'])
                    entry.created_at = entry_data['created_at']
                    
                    if entry.is_expired():
                        cache_file.unlink(missing_ok=True)
                        
                except (IOError, pickle.PickleError, KeyError):
                    # Remove corrupted files
                    cache_file.unlink(missing_ok=True)
    
    def _cleanup_if_needed(self) -> None:
        """Clean up old cache files if we're at the limit."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        
        if len(cache_files) >= self.max_files:
            # Sort by modification time and remove oldest
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            files_to_remove = cache_files[:len(cache_files) - self.max_files + 1]
            
            for cache_file in files_to_remove:
                cache_file.unlink(missing_ok=True)


class NullCache(CacheBackend):
    """Null cache backend that doesn't cache anything."""
    
    def get(self, key: str) -> Optional[Any]:
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        pass
    
    def delete(self, key: str) -> None:
        pass
    
    def clear(self) -> None:
        pass
    
    def exists(self, key: str) -> bool:
        return False
    
    def has_key(self, key: str) -> bool:
        """Alias for exists method."""
        return self.exists(key)


class ConfigCache:
    """High-level configuration cache manager."""
    
    def __init__(self, 
                 backend: Optional[CacheBackend] = None,
                 default_ttl: Optional[float] = 300.0,  # 5 minutes
                 enabled: bool = True):
        """
        Initialize configuration cache.
        
        Args:
            backend: Cache backend to use (MemoryCache if None).
            default_ttl: Default TTL in seconds.
            enabled: Whether caching is enabled.
        """
        self.enabled = enabled
        self.default_ttl = default_ttl
        
        if not enabled:
            self.backend = NullCache()
        elif backend is None:
            self.backend = MemoryCache(default_ttl=default_ttl)
        else:
            self.backend = backend
        
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self._stats_lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if not self.enabled:
            return None
        
        value = self.backend.get(key)
        
        with self._stats_lock:
            if value is not None:
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in the cache."""
        if not self.enabled:
            return
        
        if ttl is None:
            ttl = self.default_ttl
        
        self.backend.set(key, value, ttl)
        
        with self._stats_lock:
            self._stats['sets'] += 1
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        if not self.enabled:
            return
        
        self.backend.delete(key)
        
        with self._stats_lock:
            self._stats['deletes'] += 1
    
    def clear(self) -> None:
        """Clear all cached values."""
        if not self.enabled:
            return
        
        self.backend.clear()
        
        with self._stats_lock:
            self._stats = {k: 0 for k in self._stats}
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        if not self.enabled:
            return False
        
        return self.backend.exists(key)
    
    def cache_config(self, source_id: str, config_data: Any, ttl: Optional[float] = None) -> None:
        """
        Cache configuration data for a source.
        
        Args:
            source_id: Identifier for the configuration source.
            config_data: Configuration data to cache.
            ttl: Time to live in seconds.
        """
        cache_key = self.get_cache_key(source_id)
        self.set(cache_key, config_data, ttl)
    
    def get_config(self, source_id: str) -> Optional[Any]:
        """
        Get cached configuration data for a source.
        
        Args:
            source_id: Identifier for the configuration source.
            
        Returns:
            Cached configuration data or None if not found.
        """
        cache_key = self.get_cache_key(source_id)
        return self.get(cache_key)
    
    def invalidate(self, source_id: str) -> None:
        """
        Invalidate cached configuration for a source.
        
        Args:
            source_id: Identifier for the configuration source.
        """
        cache_key = self.get_cache_key(source_id)
        self.delete(cache_key)
    
    def is_cached(self, source_id: str) -> bool:
        """
        Check if configuration is cached for a source.
        
        Args:
            source_id: Identifier for the configuration source.
            
        Returns:
            True if configuration is cached, False otherwise.
        """
        cache_key = self.get_cache_key(source_id)
        return self.exists(cache_key)
    
    def get_cache_key(self, source_id: str, config_hash: Optional[str] = None) -> str:
        """
        Generate a cache key for a configuration source.
        
        Args:
            source_id: Identifier for the configuration source.
            config_hash: Optional hash of configuration content.
            
        Returns:
            Cache key string.
        """
        if config_hash:
            return f"config:{source_id}:{config_hash}"
        else:
            return f"config:{source_id}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        total_requests = stats['hits'] + stats['misses']
        hit_ratio = 0.0 if total_requests == 0 else stats['hits'] / total_requests
        
        result = {
            **stats,
            'total_requests': total_requests,
            'hit_ratio': hit_ratio,
            'enabled': self.enabled
        }
        
        # Add backend-specific stats if available
        if hasattr(self.backend, 'get_stats') and callable(getattr(self.backend, 'get_stats')):
            result['backend_stats'] = self.backend.get_stats()  # type: ignore
        
        return result
    
    def enable(self) -> None:
        """Enable caching."""
        if not self.enabled and isinstance(self.backend, NullCache):
            self.backend = MemoryCache(default_ttl=self.default_ttl)
        self.enabled = True
    
    def disable(self) -> None:
        """Disable caching."""
        self.enabled = False
        if not isinstance(self.backend, NullCache):
            self.backend.clear()


# Global cache instance
_global_cache: Optional[ConfigCache] = None


def get_global_cache() -> ConfigCache:
    """Get the global configuration cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ConfigCache()
    return _global_cache


def set_global_cache(cache: ConfigCache) -> None:
    """Set the global configuration cache instance."""
    global _global_cache
    _global_cache = cache


def clear_global_cache() -> None:
    """Clear the global configuration cache instance."""
    global _global_cache
    _global_cache = None


def create_cache_key(*parts: str) -> str:
    """Create a cache key from multiple parts with hash."""
    key_base = ":".join(str(part) for part in parts)
    key_hash = hashlib.md5(key_base.encode()).hexdigest()
    return f"{key_base}:{key_hash}"


def hash_config_data(data: Any) -> str:
    """Create a hash of configuration data for cache keys."""
    try:
        # Convert to JSON for consistent hashing
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()
    except (TypeError, ValueError):
        # Fallback to string representation
        return hashlib.md5(str(data).encode()).hexdigest()

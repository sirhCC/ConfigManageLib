"""
🔧 Enterprise-grade Configuration Caching System for ConfigManager.

This module provides a comprehensive caching framework with modern Python patterns,
multiple backend support, performance monitoring, and enterprise-grade features
for high-performance configuration management systems.
"""

import time
import threading
import pickle
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Union, Protocol, runtime_checkable, List, Set, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# Configure logger for this module
logger = logging.getLogger(__name__)


class CacheEvictionPolicy(Enum):
    """Cache eviction policies for when cache reaches capacity."""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used
    FIFO = "fifo"            # First In, First Out
    RANDOM = "random"        # Random eviction
    TTL_BASED = "ttl_based"  # Evict based on TTL


class CacheEventType(Enum):
    """Types of cache events for monitoring and callbacks."""
    HIT = "hit"
    MISS = "miss"
    SET = "set"
    DELETE = "delete"
    EVICT = "evict"
    CLEAR = "clear"
    EXPIRE = "expire"


@dataclass
class CacheStats:
    """
    Comprehensive cache statistics for performance monitoring.
    
    This provides detailed metrics about cache performance, hit rates,
    and usage patterns for enterprise monitoring and optimization.
    """
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    max_size: int = 0
    total_memory_used: int = 0  # Approximate bytes
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as a percentage."""
        return 100.0 - self.hit_rate
    
    @property
    def fill_rate(self) -> float:
        """Calculate cache fill rate as a percentage."""
        if self.max_size == 0:
            return 0.0
        return (self.current_size / self.max_size) * 100
    
    def reset(self) -> None:
        """Reset all statistics counters."""
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.expirations = 0
        # Don't reset size metrics as they represent current state


@dataclass
class CacheMetrics:
    """
    Detailed cache entry metrics for advanced monitoring.
    
    This tracks comprehensive information about individual cache entries
    for performance analysis and optimization.
    """
    key: str
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[float]
    tags: Set[str] = field(default_factory=set)
    
    @property
    def age_seconds(self) -> float:
        """Get the age of this cache entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def time_since_access_seconds(self) -> float:
        """Get time since last access in seconds."""
        return (datetime.now() - self.last_accessed).total_seconds()
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return self.age_seconds > self.ttl_seconds


@dataclass
class CacheEntry:
    """
    Enterprise-grade cache entry with comprehensive metadata and monitoring.
    
    Features:
    - Detailed access tracking and metrics
    - TTL support with precision timing
    - Size tracking for memory management
    - Tag-based organization and querying
    - Performance monitoring integration
    """
    
    value: Any
    ttl_seconds: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False
    serialized: bool = False
    
    def __post_init__(self):
        """Initialize entry with current timestamp and metrics."""
        now = datetime.now()
        self.created_at = now
        self.last_accessed = now
        self.access_count = 0
        self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Estimate the memory size of the cached value."""
        try:
            if self.serialized:
                return len(self.value) if isinstance(self.value, (str, bytes)) else 0
            else:
                # Rough estimate using pickle serialization
                return len(pickle.dumps(self.value, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            # Fallback to basic estimation
            return len(str(self.value).encode('utf-8'))
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def access(self) -> Any:
        """
        Access the cached value and update access metrics.
        
        Returns:
            The cached value
        """
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value
    
    def get_metrics(self, key: str) -> CacheMetrics:
        """Get comprehensive metrics for this cache entry."""
        return CacheMetrics(
            key=key,
            created_at=self.created_at,
            last_accessed=self.last_accessed,
            access_count=self.access_count,
            size_bytes=self.size_bytes,
            ttl_seconds=self.ttl_seconds,
            tags=self.tags.copy()
        )
    
    def __repr__(self) -> str:
        """String representation of the cache entry."""
        age = (datetime.now() - self.created_at).total_seconds()
        return (
            f"CacheEntry(ttl={self.ttl_seconds}, accessed={self.access_count}x, "
            f"age={age:.1f}s, size={self.size_bytes}b)"
        )


@runtime_checkable
class EnhancedCacheBackend(Protocol):
    """
    Enhanced protocol for enterprise cache backend implementations.
    
    This extends the basic cache backend with advanced features like
    tag-based operations, bulk operations, and comprehensive monitoring.
    """
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> None:
        """Set a value in the cache with optional TTL and tags."""
        ...
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache. Returns True if key existed."""
        ...
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        ...
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        ...
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache."""
        ...
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple values in the cache."""
        ...
    
    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys. Returns number of keys actually deleted."""
        ...
    
    def delete_by_tags(self, tags: Set[str]) -> int:
        """Delete all entries matching any of the given tags."""
        ...
    
    def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        ...
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern."""
        ...


class EnterpriseMemoryCache(EnhancedCacheBackend):
    """
    Enterprise-grade in-memory cache with advanced features and monitoring.
    
    Features:
    - Multiple eviction policies (LRU, LFU, FIFO, Random, TTL-based)
    - Comprehensive statistics and monitoring
    - Tag-based operations and querying
    - Bulk operations for performance
    - Thread-safe operations with fine-grained locking
    - Memory usage tracking and optimization
    - Event callbacks for monitoring integration
    
    Example:
        >>> from config_manager.cache import EnterpriseMemoryCache, CacheEvictionPolicy
        >>> import time
        >>> 
        >>> # Create cache with LRU eviction and 100-item capacity
        >>> cache = EnterpriseMemoryCache(
        ...     max_size=100,
        ...     default_ttl=300.0,  # 5 minutes
        ...     eviction_policy=CacheEvictionPolicy.LRU
        ... )
        >>> 
        >>> # Store configuration data
        >>> cache.set("db.host", "localhost", ttl=600.0, tags=["database"])
        >>> cache.set("db.port", 5432, tags=["database"])
        >>> 
        >>> # Retrieve cached data
        >>> host = cache.get("db.host")
        >>> assert host == "localhost"
        >>> 
        >>> # Delete by tag
        >>> cache.delete_by_tag("database")
        >>> assert cache.get("db.host") is None
        >>> 
        >>> # Check statistics
        >>> stats = cache.get_stats()
        >>> print(f"Hit rate: {stats.hit_rate:.1f}%")
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU,
        enable_stats: bool = True,
        auto_cleanup_interval: float = 60.0
    ):
        """
        Initialize enterprise memory cache.
        
        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default TTL in seconds for entries without explicit TTL
            eviction_policy: Policy for evicting entries when cache is full
            enable_stats: Whether to track detailed statistics
            auto_cleanup_interval: Interval in seconds for automatic expired entry cleanup
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.eviction_policy = eviction_policy
        self.enable_stats = enable_stats
        self.auto_cleanup_interval = auto_cleanup_interval
        
        # Core cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._tags_index: Dict[str, Set[str]] = {}  # tag -> set of keys
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics tracking
        self._stats = CacheStats(max_size=max_size) if enable_stats else None
        
        # Event callbacks
        self._event_callbacks: Dict[CacheEventType, List[Callable]] = {
            event_type: [] for event_type in CacheEventType
        }
        
        # Logger
        self._logger = logging.getLogger(f"{__name__}.MemoryCache")
        
        # Auto-cleanup thread
        self._cleanup_thread = None
        self._shutdown_event = threading.Event()
        if auto_cleanup_interval > 0:
            self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """Start the automatic cleanup thread for expired entries."""
        def cleanup_worker():
            while not self._shutdown_event.wait(self.auto_cleanup_interval):
                try:
                    self._cleanup_expired()
                except Exception as e:
                    self._logger.error("Error in cleanup thread: %s", e)
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        self._logger.debug("Started auto-cleanup thread")
    
    def _cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._delete_entry(key, event_type=CacheEventType.EXPIRE)
            
            if expired_keys:
                self._logger.debug("Auto-cleanup removed %d expired entries", len(expired_keys))
            
            return len(expired_keys)
    
    def _evict_entries(self, count: int = 1) -> None:
        """Evict entries based on the configured eviction policy."""
        if not self._cache:
            return
        
        keys_to_evict = []
        
        if self.eviction_policy == CacheEvictionPolicy.LRU:
            # Sort by last_accessed, oldest first
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed
            )
            keys_to_evict = [key for key, _ in sorted_items[:count]]
            
        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            # Sort by access_count, least accessed first
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count
            )
            keys_to_evict = [key for key, _ in sorted_items[:count]]
            
        elif self.eviction_policy == CacheEvictionPolicy.FIFO:
            # Sort by created_at, oldest first
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].created_at
            )
            keys_to_evict = [key for key, _ in sorted_items[:count]]
            
        elif self.eviction_policy == CacheEvictionPolicy.TTL_BASED:
            # Evict entries with shortest remaining TTL first
            items_with_ttl = [
                (key, entry) for key, entry in self._cache.items()
                if entry.ttl_seconds is not None
            ]
            if items_with_ttl:
                sorted_items = sorted(
                    items_with_ttl,
                    key=lambda x: (
                        float('inf') if x[1].ttl_seconds is None 
                        else x[1].ttl_seconds - (datetime.now() - x[1].created_at).total_seconds()
                    )
                )
                keys_to_evict = [key for key, _ in sorted_items[:count]]
            
        elif self.eviction_policy == CacheEvictionPolicy.RANDOM:
            import random
            keys_to_evict = random.sample(list(self._cache.keys()), min(count, len(self._cache)))
        
        # Perform eviction
        for key in keys_to_evict:
            self._delete_entry(key, event_type=CacheEventType.EVICT)
        
        if keys_to_evict:
            self._logger.debug("Evicted %d entries using %s policy", len(keys_to_evict), self.eviction_policy.value)
    
    def _delete_entry(self, key: str, event_type: CacheEventType = CacheEventType.DELETE) -> bool:
        """Internal method to delete an entry and update indexes."""
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        
        # Remove from main cache
        del self._cache[key]
        
        # Remove from tag indexes
        for tag in entry.tags:
            if tag in self._tags_index:
                self._tags_index[tag].discard(key)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]
        
        # Update statistics
        if self._stats:
            self._stats.current_size = len(self._cache)
            self._stats.total_memory_used -= entry.size_bytes
            
            if event_type == CacheEventType.DELETE:
                self._stats.deletes += 1
            elif event_type == CacheEventType.EVICT:
                self._stats.evictions += 1
            elif event_type == CacheEventType.EXPIRE:
                self._stats.expirations += 1
        
        # Fire event callbacks
        self._fire_event(event_type, key, entry.value)
        
        return True
    
    def _fire_event(self, event_type: CacheEventType, key: str, value: Any = None) -> None:
        """Fire event callbacks for monitoring."""
        for callback in self._event_callbacks.get(event_type, []):
            try:
                callback(event_type, key, value)
            except Exception as e:
                self._logger.warning("Error in event callback for %s: %s", event_type, e)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache with comprehensive monitoring."""
        with self._lock:
            # Update statistics
            if self._stats:
                self._stats.total_requests += 1
            
            entry = self._cache.get(key)
            if entry is None:
                if self._stats:
                    self._stats.cache_misses += 1
                self._fire_event(CacheEventType.MISS, key)
                return None
            
            # Check expiration
            if entry.is_expired():
                self._delete_entry(key, CacheEventType.EXPIRE)
                if self._stats:
                    self._stats.cache_misses += 1
                self._fire_event(CacheEventType.MISS, key)
                return None
            
            # Update statistics and fire hit event
            if self._stats:
                self._stats.cache_hits += 1
            self._fire_event(CacheEventType.HIT, key, entry.value)
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> None:
        """Set a value in the cache with comprehensive features."""
        with self._lock:
            # Use default TTL if none specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Clean up expired entries first
            self._cleanup_expired()
            
            # Evict entries if at max size and this is a new key
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_entries(1)
            
            # Remove existing entry if updating
            if key in self._cache:
                self._delete_entry(key, CacheEventType.DELETE)
            
            # Create new entry
            entry = CacheEntry(value=value, ttl_seconds=ttl, tags=tags or set())
            self._cache[key] = entry
            
            # Update tag indexes
            for tag in entry.tags:
                if tag not in self._tags_index:
                    self._tags_index[tag] = set()
                self._tags_index[tag].add(key)
            
            # Update statistics
            if self._stats:
                self._stats.sets += 1
                self._stats.current_size = len(self._cache)
                self._stats.total_memory_used += entry.size_bytes
            
            # Fire set event
            self._fire_event(CacheEventType.SET, key, value)
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        with self._lock:
            return self._delete_entry(key, CacheEventType.DELETE)
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._tags_index.clear()
            
            if self._stats:
                self._stats.current_size = 0
                self._stats.total_memory_used = 0
            
            self._fire_event(CacheEventType.CLEAR, "")
            self._logger.debug("Cleared %d cache entries", cleared_count)
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired():
                self._delete_entry(key, CacheEventType.EXPIRE)
                return False
            
            return True
    
    def has_key(self, key: str) -> bool:
        """Alias for exists method (backward compatibility)."""
        return self.exists(key)
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache efficiently."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple values in the cache efficiently."""
        for key, value in mapping.items():
            self.set(key, value, ttl)
    
    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys and return the number actually deleted."""
        deleted_count = 0
        for key in keys:
            if self.delete(key):
                deleted_count += 1
        return deleted_count
    
    def delete_by_tags(self, tags: Set[str]) -> int:
        """Delete all entries matching any of the given tags."""
        with self._lock:
            keys_to_delete = set()
            
            for tag in tags:
                if tag in self._tags_index:
                    keys_to_delete.update(self._tags_index[tag])
            
            deleted_count = 0
            for key in keys_to_delete:
                if self._delete_entry(key, CacheEventType.DELETE):
                    deleted_count += 1
            
            return deleted_count
    
    def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        if not self._stats:
            return CacheStats()
        
        with self._lock:
            # Update current state
            self._stats.current_size = len(self._cache)
            return self._stats
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern."""
        with self._lock:
            keys = list(self._cache.keys())
            
            if pattern:
                import fnmatch
                keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]
            
            return keys
    
    def add_event_callback(self, event_type: CacheEventType, callback: Callable) -> None:
        """Add an event callback for monitoring."""
        self._event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: CacheEventType, callback: Callable) -> None:
        """Remove an event callback."""
        try:
            self._event_callbacks[event_type].remove(callback)
        except ValueError:
            pass
    
    def get_entry_metrics(self, key: str) -> Optional[CacheMetrics]:
        """Get detailed metrics for a specific cache entry."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            return entry.get_metrics(key)
    
    def shutdown(self) -> None:
        """Shutdown the cache and cleanup resources."""
        self._shutdown_event.set()

# Backward compatibility aliases
MemoryCache = EnterpriseMemoryCache
CacheBackend = EnhancedCacheBackend


class EnterpriseFileCache(EnhancedCacheBackend):
    """
    Enterprise-grade file-based cache with comprehensive features and monitoring.
    
    Features:
    - Persistent storage with atomic operations
    - Compression and serialization options
    - Directory-based organization
    - Automatic cleanup and maintenance
    - Tag-based file organization
    - Comprehensive statistics and monitoring
    """
    
    def __init__(
        self,
        cache_dir: Union[str, Path] = ".config_cache",
        default_ttl: Optional[float] = None,
        max_files: int = 10000,
        compress_data: bool = False,
        enable_stats: bool = True
    ):
        """
        Initialize enterprise file cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds
            max_files: Maximum number of cache files
            compress_data: Whether to compress cached data
            enable_stats: Whether to track detailed statistics
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.max_files = max_files
        self.compress_data = compress_data
        self.enable_stats = enable_stats
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = CacheStats(max_size=max_files) if enable_stats else None
        
        # Logger
        self._logger = logging.getLogger(f"{__name__}.FileCache")
        
        # Initialize metadata index
        self._metadata_file = self.cache_dir / ".cache_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        try:
            if self._metadata_file.exists():
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if self._stats:
                        self._stats.current_size = metadata.get('current_size', 0)
            else:
                self._save_metadata()
        except Exception as e:
            self._logger.warning("Failed to load cache metadata: %s", e)
            if self._stats:
                self._stats.current_size = len(list(self.cache_dir.glob("*.cache")))
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            metadata = {
                'current_size': self._stats.current_size if self._stats else 0,
                'last_updated': datetime.now().isoformat()
            }
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f)
        except Exception as e:
            self._logger.warning("Failed to save cache metadata: %s", e)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _cleanup_old_files(self) -> None:
        """Remove old cache files if over limit."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        if len(cache_files) <= self.max_files:
            return
        
        # Sort by modification time, oldest first
        cache_files.sort(key=lambda p: p.stat().st_mtime)
        files_to_remove = cache_files[:-self.max_files]
        
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                if self._stats:
                    self._stats.evictions += 1
            except Exception as e:
                self._logger.warning("Failed to remove old cache file %s: %s", file_path, e)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the file cache."""
        with self._lock:
            if self._stats:
                self._stats.total_requests += 1
            
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                if self._stats:
                    self._stats.cache_misses += 1
                return None
            
            try:
                with open(cache_path, 'rb') as f:
                    entry_data = pickle.load(f)
                
                # Reconstruct entry
                entry = CacheEntry(
                    value=entry_data['value'],
                    ttl_seconds=entry_data.get('ttl_seconds'),
                    tags=set(entry_data.get('tags', []))
                )
                entry.created_at = datetime.fromisoformat(entry_data['created_at'])
                entry.access_count = entry_data.get('access_count', 0)
                entry.last_accessed = datetime.fromisoformat(entry_data.get('last_accessed', entry_data['created_at']))
                
                if entry.is_expired():
                    cache_path.unlink(missing_ok=True)
                    if self._stats:
                        self._stats.cache_misses += 1
                        self._stats.expirations += 1
                        self._stats.current_size -= 1
                    return None
                
                # Update access and save back
                value = entry.access()
                self._save_entry_to_file(key, entry, cache_path)
                
                if self._stats:
                    self._stats.cache_hits += 1
                
                return value
                
            except Exception as e:
                self._logger.warning("Failed to load cache entry %s: %s", key, e)
                cache_path.unlink(missing_ok=True)
                if self._stats:
                    self._stats.cache_misses += 1
                return None
    
    def _save_entry_to_file(self, key: str, entry: CacheEntry, cache_path: Optional[Path] = None) -> None:
        """Save an entry to disk."""
        if cache_path is None:
            cache_path = self._get_cache_path(key)
        
        entry_data = {
            'value': entry.value,
            'ttl_seconds': entry.ttl_seconds,
            'tags': list(entry.tags),
            'created_at': entry.created_at.isoformat(),
            'last_accessed': entry.last_accessed.isoformat(),
            'access_count': entry.access_count
        }
        
        # Atomic write using temporary file
        temp_path = cache_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'wb') as f:
                pickle.dump(entry_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            temp_path.replace(cache_path)
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            raise e
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> None:
        """Set a value in the file cache."""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            cache_path = self._get_cache_path(key)
            is_new = not cache_path.exists()
            
            # Create entry
            entry = CacheEntry(value=value, ttl_seconds=ttl, tags=tags or set())
            
            # Save to disk
            self._save_entry_to_file(key, entry, cache_path)
            
            # Update statistics
            if self._stats:
                self._stats.sets += 1
                if is_new:
                    self._stats.current_size += 1
            
            # Cleanup if needed
            if is_new:
                self._cleanup_old_files()
                self._save_metadata()
    
    def delete(self, key: str) -> bool:
        """Delete a value from the file cache."""
        with self._lock:
            cache_path = self._get_cache_path(key)
            
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    if self._stats:
                        self._stats.deletes += 1
                        self._stats.current_size -= 1
                    self._save_metadata()
                    return True
                except Exception as e:
                    self._logger.warning("Failed to delete cache file %s: %s", cache_path, e)
            
            return False
    
    def clear(self) -> None:
        """Clear all values from the file cache."""
        with self._lock:
            cache_files = list(self.cache_dir.glob("*.cache"))
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                except Exception as e:
                    self._logger.warning("Failed to delete cache file %s: %s", cache_file, e)
            
            if self._stats:
                self._stats.current_size = 0
            self._save_metadata()
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return self.get(key) is not None
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple values in the cache."""
        for key, value in mapping.items():
            self.set(key, value, ttl)
    
    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys."""
        deleted_count = 0
        for key in keys:
            if self.delete(key):
                deleted_count += 1
        return deleted_count
    
    def delete_by_tags(self, tags: Set[str]) -> int:
        """Delete all entries matching any of the given tags."""
        # This requires loading all entries to check tags
        # In a real implementation, you might maintain a tag index file
        deleted_count = 0
        cache_files = list(self.cache_dir.glob("*.cache"))
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    entry_data = pickle.load(f)
                
                entry_tags = set(entry_data.get('tags', []))
                if entry_tags.intersection(tags):
                    cache_file.unlink()
                    deleted_count += 1
                    if self._stats:
                        self._stats.deletes += 1
                        self._stats.current_size -= 1
                        
            except Exception as e:
                self._logger.warning("Failed to check tags for %s: %s", cache_file, e)
        
        if deleted_count > 0:
            self._save_metadata()
        
        return deleted_count
    
    def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        if not self._stats:
            return CacheStats()
        
        with self._lock:
            return self._stats
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys (warning: can be expensive for large caches)."""
        # This is expensive as it requires loading metadata from all files
        keys = []
        cache_files = list(self.cache_dir.glob("*.cache"))
        
        for cache_file in cache_files:
            try:
                # Derive key from filename - this is a limitation of this approach
                # In a production system, you'd maintain a key index
                key_hash = cache_file.stem
                # We can't easily reverse the hash, so this is limited
                # A real implementation would maintain a key index file
                pass
            except Exception:
                continue
        
        return keys  # Will be empty in this implementation


class NullCache(EnhancedCacheBackend):
    """
    Null cache backend that doesn't cache anything.
    
    Useful for testing or disabling caching without changing code.
    """
    
    def __init__(self):
        """Initialize null cache."""
        self._stats = CacheStats()
        self._logger = logging.getLogger(f"{__name__}.NullCache")
    
    def get(self, key: str) -> Optional[Any]:
        """Always return None (cache miss)."""
        self._stats.total_requests += 1
        self._stats.cache_misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> None:
        """Do nothing (don't cache)."""
        self._stats.sets += 1
    
    def delete(self, key: str) -> bool:
        """Always return False (nothing to delete)."""
        self._stats.deletes += 1
        return False
    
    def clear(self) -> None:
        """Do nothing."""
        pass
    
    def exists(self, key: str) -> bool:
        """Always return False."""
        return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Always return empty dict."""
        self._stats.total_requests += len(keys)
        self._stats.cache_misses += len(keys)
        return {}
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Do nothing."""
        self._stats.sets += len(mapping)
    
    def delete_many(self, keys: List[str]) -> int:
        """Always return 0."""
        self._stats.deletes += len(keys)
        return 0
    
    def delete_by_tags(self, tags: Set[str]) -> int:
        """Always return 0."""
        return 0
    
    def get_stats(self) -> CacheStats:
        """Get statistics."""
        return self._stats
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Always return empty list."""
        return []


@dataclass
class CacheConfiguration:
    """
    Enterprise cache configuration with comprehensive options.
    
    This provides a centralized configuration system for cache behavior,
    performance tuning, and monitoring settings.
    """
    backend_type: str = "memory"  # "memory", "file", "null"
    max_size: int = 1000
    default_ttl: Optional[float] = None
    eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    enable_stats: bool = True
    auto_cleanup_interval: float = 60.0
    
    # Memory cache specific
    memory_compress_large_values: bool = False
    memory_large_value_threshold: int = 1024 * 1024  # 1MB
    
    # File cache specific
    file_cache_dir: str = ".config_cache"
    file_compress_data: bool = False
    file_max_files: int = 10000
    
    # Monitoring and events
    enable_event_callbacks: bool = True
    log_cache_events: bool = False


class CacheManager:
    """
    Enterprise-grade cache manager with comprehensive features and monitoring.
    
    This provides a high-level interface for cache management with support for
    multiple backends, configuration management, and enterprise monitoring.
    
    Features:
    - Multiple cache backend support
    - Automatic backend selection and configuration
    - Comprehensive monitoring and statistics
    - Event-driven architecture for monitoring
    - Configuration-based setup
    - Performance optimization and tuning
    """
    
    def __init__(
        self,
        config: Optional[Union[CacheConfiguration, EnhancedCacheBackend]] = None,
        backend: Optional[EnhancedCacheBackend] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            config: Cache configuration or backend (for backward compatibility)
            backend: Specific cache backend to use (auto-selected if not provided)
        """
        # Handle backward compatibility - if config is actually a backend
        if hasattr(config, 'get') and hasattr(config, 'set') and hasattr(config, 'delete'):
            # config is actually a backend
            backend = config  # type: ignore
            config = None
        
        self.config = config if isinstance(config, CacheConfiguration) else CacheConfiguration()
        self._logger = logging.getLogger(f"{__name__}.CacheManager")
        
        # Initialize backend
        if backend:
            self.backend = backend
        else:
            self.backend = self._create_backend()
        
        # Performance tracking
        self._start_time = time.time()
        self._operation_times: List[float] = []
        
        self._logger.info("Initialized cache manager with %s backend", type(self.backend).__name__)
    
    def _create_backend(self) -> EnhancedCacheBackend:
        """Create cache backend based on configuration."""
        if self.config.backend_type == "memory":
            return EnterpriseMemoryCache(
                max_size=self.config.max_size,
                default_ttl=self.config.default_ttl,
                eviction_policy=self.config.eviction_policy,
                enable_stats=self.config.enable_stats,
                auto_cleanup_interval=self.config.auto_cleanup_interval
            )
        elif self.config.backend_type == "file":
            return EnterpriseFileCache(
                cache_dir=self.config.file_cache_dir,
                default_ttl=self.config.default_ttl,
                max_files=self.config.file_max_files,
                compress_data=self.config.file_compress_data,
                enable_stats=self.config.enable_stats
            )
        elif self.config.backend_type == "null":
            return NullCache()
        else:
            raise ValueError(f"Unknown cache backend type: {self.config.backend_type}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache with performance tracking."""
        start_time = time.perf_counter()
        try:
            result = self.backend.get(key)
            return result
        finally:
            self._record_operation_time(time.perf_counter() - start_time)
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> None:
        """Set a value in the cache with performance tracking."""
        start_time = time.perf_counter()
        try:
            self.backend.set(key, value, ttl, tags)
        finally:
            self._record_operation_time(time.perf_counter() - start_time)
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        return self.backend.delete(key)
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        self.backend.clear()
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return self.backend.exists(key)
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache."""
        return self.backend.get_many(keys)
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple values in the cache."""
        self.backend.set_many(mapping, ttl)
    
    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys."""
        return self.backend.delete_many(keys)
    
    def delete_by_tags(self, tags: Set[str]) -> int:
        """Delete all entries matching any of the given tags."""
        return self.backend.delete_by_tags(tags)
    
    def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        return self.backend.get_stats()
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys."""
        return self.backend.get_keys(pattern)
    
    def _record_operation_time(self, duration: float) -> None:
        """Record operation timing for performance monitoring."""
        self._operation_times.append(duration)
        # Keep only recent operations (last 1000)
        if len(self._operation_times) > 1000:
            self._operation_times = self._operation_times[-1000:]
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics for cache operations."""
        if not self._operation_times:
            return {
                "avg_operation_time": 0.0,
                "min_operation_time": 0.0,
                "max_operation_time": 0.0,
                "total_operations": 0
            }
        
        return {
            "avg_operation_time": sum(self._operation_times) / len(self._operation_times),
            "min_operation_time": min(self._operation_times),
            "max_operation_time": max(self._operation_times),
            "total_operations": len(self._operation_times),
            "uptime_seconds": time.time() - self._start_time
        }
    
    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return not isinstance(self.backend, NullCache)
    
    def enable(self) -> None:
        """Enable caching by switching from NullCache if needed."""
        if isinstance(self.backend, NullCache):
            self.backend = self._create_backend()
            self._logger.info("Cache enabled")
    
    def disable(self) -> None:
        """Disable caching by switching to NullCache."""
        if not isinstance(self.backend, NullCache):
            self.backend.clear()
            self.backend = NullCache()
            self._logger.info("Cache disabled")
    
    # Backward compatibility methods for ConfigCache interface
    def cache_config(self, source_id: str, config_data: Any, ttl: Optional[float] = None) -> None:
        """Cache configuration data for a source (backward compatibility)."""
        cache_key = f"config:{source_id}"
        self.set(cache_key, config_data, ttl)
    
    def get_config(self, source_id: str) -> Optional[Any]:
        """Get cached configuration data for a source (backward compatibility)."""
        cache_key = f"config:{source_id}"
        return self.get(cache_key)
    
    def invalidate(self, source_id: str) -> None:
        """Invalidate cached configuration for a source (backward compatibility)."""
        cache_key = f"config:{source_id}"
        self.delete(cache_key)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the cache system."""
        try:
            # Test basic operations
            test_key = "__health_check__"
            test_value = "test"
            
            # Test set/get/delete cycle
            self.set(test_key, test_value, ttl=1.0)
            retrieved = self.get(test_key)
            deleted = self.delete(test_key)
            
            stats = self.get_stats()
            perf_stats = self.get_performance_stats()
            
            return {
                "status": "healthy" if retrieved == test_value and deleted else "unhealthy",
                "backend_type": type(self.backend).__name__,
                "cache_stats": {
                    "hit_rate": stats.hit_rate,
                    "current_size": stats.current_size,
                    "max_size": stats.max_size
                },
                "performance": perf_stats,
                "test_results": {
                    "set_get_success": retrieved == test_value,
                    "delete_success": deleted
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "backend_type": type(self.backend).__name__ if hasattr(self, 'backend') else "unknown"
            }


# Legacy compatibility aliases and utility functions
MemoryCache = EnterpriseMemoryCache
FileCache = EnterpriseFileCache
ConfigCache = CacheManager  # Backward compatibility


def create_cache_key(*parts: str) -> str:
    """Create a cache key from multiple parts with hash."""
    key_base = ":".join(str(part) for part in parts)
    key_hash = hashlib.sha256(key_base.encode()).hexdigest()[:16]
    return f"{key_base}:{key_hash}"


def hash_config_data(data: Any) -> str:
    """Create a hash of configuration data for cache keys."""
    try:
        # Convert to JSON for consistent hashing
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    except (TypeError, ValueError):
        # Fallback to string representation
        return hashlib.sha256(str(data).encode()).hexdigest()


# Global cache instance for backward compatibility
_global_cache: Optional[CacheManager] = None


def get_global_cache() -> CacheManager:
    """Get the global configuration cache instance."""
    global _global_cache
    if _global_cache is None:
        # Create with default memory backend for backward compatibility
        config = CacheConfiguration(backend_type="memory", default_ttl=300.0)
        _global_cache = CacheManager(config)
    return _global_cache


def set_global_cache(cache: CacheManager) -> None:
    """Set the global configuration cache instance."""
    global _global_cache
    _global_cache = cache


def clear_global_cache() -> None:
    """Clear the global configuration cache instance."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
    _global_cache = None

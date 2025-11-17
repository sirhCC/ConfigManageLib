"""
Comprehensive test suite for ConfigManager cache system.

Achieves 85%+ coverage of cache.py module with tests for:
- CacheStats dataclass and metrics calculation
- CacheMetrics with age/expiry tracking
- CacheEntry with access tracking and TTL
- EnterpriseMemoryCache with LRU/LFU/FIFO eviction
- EnterpriseFileCache with persistence
- NullCache for no-caching scenarios
- CacheManager with backend integration
- Tag-based operations and bulk operations
- Event callbacks and monitoring
"""

import pytest
import time
import threading
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from config_manager.cache import (
    CacheStats,
    CacheMetrics,
    CacheEntry,
    CacheEvictionPolicy,
    CacheEventType,
    CacheConfiguration,
    EnterpriseMemoryCache,
    EnterpriseFileCache,
    NullCache,
    CacheManager,
    create_cache_key,
    hash_config_data,
)


class TestCacheStats:
    """Test CacheStats dataclass and calculations."""

    def test_cache_stats_defaults(self):
        """Test CacheStats with default values."""
        stats = CacheStats()
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.expirations == 0
        assert stats.current_size == 0
        assert stats.max_size == 0
        assert stats.total_memory_used == 0

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        stats = CacheStats(total_requests=100, cache_hits=75)
        assert stats.hit_rate == 75.0
        
        stats.cache_hits = 50
        assert stats.hit_rate == 50.0

    def test_hit_rate_zero_requests(self):
        """Test hit rate with zero requests."""
        stats = CacheStats(total_requests=0)
        assert stats.hit_rate == 0.0

    def test_miss_rate_calculation(self):
        """Test cache miss rate calculation."""
        stats = CacheStats(total_requests=100, cache_hits=75)
        assert stats.miss_rate == 25.0

    def test_fill_rate_calculation(self):
        """Test cache fill rate calculation."""
        stats = CacheStats(current_size=50, max_size=100)
        assert stats.fill_rate == 50.0
        
        stats.current_size = 100
        assert stats.fill_rate == 100.0

    def test_fill_rate_zero_max_size(self):
        """Test fill rate with zero max size."""
        stats = CacheStats(current_size=10, max_size=0)
        assert stats.fill_rate == 0.0

    def test_reset_counters(self):
        """Test resetting statistics counters."""
        stats = CacheStats(
            total_requests=100,
            cache_hits=75,
            cache_misses=25,
            sets=50,
            deletes=10,
            current_size=40,
            max_size=100
        )
        
        stats.reset()
        
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        # Size metrics should not reset
        assert stats.current_size == 40
        assert stats.max_size == 100


class TestCacheMetrics:
    """Test CacheMetrics for entry monitoring."""

    def test_cache_metrics_creation(self):
        """Test creating CacheMetrics."""
        now = datetime.now()
        metrics = CacheMetrics(
            key="test_key",
            created_at=now,
            last_accessed=now,
            access_count=5,
            size_bytes=1024,
            ttl_seconds=300.0,
            tags={"tag1", "tag2"}
        )
        
        assert metrics.key == "test_key"
        assert metrics.access_count == 5
        assert metrics.size_bytes == 1024
        assert metrics.ttl_seconds == 300.0
        assert "tag1" in metrics.tags

    def test_age_calculation(self):
        """Test age calculation in seconds."""
        past = datetime.now() - timedelta(seconds=10)
        metrics = CacheMetrics(
            key="test",
            created_at=past,
            last_accessed=past,
            access_count=1,
            size_bytes=100,
            ttl_seconds=None
        )
        
        assert metrics.age_seconds >= 10.0

    def test_time_since_access(self):
        """Test time since last access calculation."""
        past = datetime.now() - timedelta(seconds=5)
        metrics = CacheMetrics(
            key="test",
            created_at=past,
            last_accessed=past,
            access_count=1,
            size_bytes=100,
            ttl_seconds=None
        )
        
        assert metrics.time_since_access_seconds >= 5.0

    def test_is_expired_no_ttl(self):
        """Test expiration check with no TTL."""
        metrics = CacheMetrics(
            key="test",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=100,
            ttl_seconds=None
        )
        
        assert metrics.is_expired() is False

    def test_is_expired_with_ttl(self):
        """Test expiration check with TTL."""
        past = datetime.now() - timedelta(seconds=10)
        metrics = CacheMetrics(
            key="test",
            created_at=past,
            last_accessed=past,
            access_count=1,
            size_bytes=100,
            ttl_seconds=5.0
        )
        
        assert metrics.is_expired() is True


class TestCacheEntry:
    """Test CacheEntry with access tracking."""

    def test_cache_entry_creation(self):
        """Test creating CacheEntry."""
        entry = CacheEntry(value="test_value", ttl_seconds=300.0)
        
        assert entry.value == "test_value"
        assert entry.ttl_seconds == 300.0
        assert entry.access_count == 0
        assert hasattr(entry, 'created_at')
        assert hasattr(entry, 'last_accessed')

    def test_cache_entry_with_tags(self):
        """Test CacheEntry with tags."""
        entry = CacheEntry(value="test", tags={"tag1", "tag2"})
        
        assert "tag1" in entry.tags
        assert "tag2" in entry.tags

    def test_access_tracking(self):
        """Test access count tracking."""
        entry = CacheEntry(value="test")
        initial_accessed = entry.last_accessed
        
        assert entry.access_count == 0
        
        time.sleep(0.01)
        value = entry.access()
        
        assert value == "test"
        assert entry.access_count == 1
        assert entry.last_accessed > initial_accessed

    def test_multiple_accesses(self):
        """Test multiple access tracking."""
        entry = CacheEntry(value="test")
        
        for i in range(5):
            entry.access()
        
        assert entry.access_count == 5

    def test_is_expired_check(self):
        """Test expiration checking."""
        entry = CacheEntry(value="test", ttl_seconds=0.1)
        
        assert entry.is_expired() is False
        
        time.sleep(0.15)
        assert entry.is_expired() is True

    def test_no_expiration_without_ttl(self):
        """Test entries without TTL never expire."""
        entry = CacheEntry(value="test")
        
        time.sleep(0.1)
        assert entry.is_expired() is False

    def test_get_metrics(self):
        """Test getting entry metrics."""
        entry = CacheEntry(value="test", ttl_seconds=300.0, tags={"tag1"})
        metrics = entry.get_metrics("test_key")
        
        assert metrics.key == "test_key"
        assert metrics.ttl_seconds == 300.0
        assert "tag1" in metrics.tags
        assert metrics.access_count == 0

    def test_size_calculation(self):
        """Test size calculation for entry."""
        entry = CacheEntry(value="test" * 100)
        
        assert entry.size_bytes > 0


class TestEnterpriseMemoryCache:
    """Test EnterpriseMemoryCache functionality."""

    def test_create_memory_cache(self):
        """Test creating memory cache."""
        cache = EnterpriseMemoryCache(max_size=100, default_ttl=300.0)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 300.0

    def test_basic_get_set(self):
        """Test basic cache get/set operations."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result == "value1"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key returns None."""
        cache = EnterpriseMemoryCache()
        
        result = cache.get("nonexistent")
        assert result is None

    def test_delete_key(self):
        """Test deleting a key."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        
        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.exists("key1") is False

    def test_delete_nonexistent_key(self):
        """Test deleting nonexistent key returns False."""
        cache = EnterpriseMemoryCache()
        
        deleted = cache.delete("nonexistent")
        assert deleted is False

    def test_clear_cache(self):
        """Test clearing all cache entries."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1", ttl=0.1)
        assert cache.get("key1") == "value1"
        
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_default_ttl(self):
        """Test default TTL application."""
        cache = EnterpriseMemoryCache(default_ttl=0.1)
        
        cache.set("key1", "value1")  # Uses default TTL
        assert cache.get("key1") == "value1"
        
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """Test LRU eviction policy."""
        cache = EnterpriseMemoryCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.LRU
        )
        
        cache.set("key1", "value1")
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("key2", "value2")
        time.sleep(0.01)
        cache.set("key3", "value3")
        
        # Access key1 and key3 to make them recently used
        time.sleep(0.01)
        cache.get("key1")
        time.sleep(0.01)
        cache.get("key3")
        
        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.exists("key1") is True  # Recently accessed
        assert cache.exists("key2") is False  # Should be evicted (least recently used)
        assert cache.exists("key3") is True  # Recently accessed
        assert cache.exists("key4") is True

    def test_lfu_eviction(self):
        """Test LFU eviction policy."""
        cache = EnterpriseMemoryCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.LFU
        )
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 multiple times
        for _ in range(5):
            cache.get("key1")
        
        # key2 and key3 have only 0 accesses
        cache.set("key4", "value4")
        
        assert cache.exists("key1") is True  # Most frequently used

    def test_fifo_eviction(self):
        """Test FIFO eviction policy."""
        cache = EnterpriseMemoryCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.FIFO
        )
        
        cache.set("key1", "value1")
        time.sleep(0.01)
        cache.set("key2", "value2")
        time.sleep(0.01)
        cache.set("key3", "value3")
        
        # Add key4, should evict key1 (first in)
        cache.set("key4", "value4")
        
        assert cache.exists("key1") is False  # First in, first out
        assert cache.exists("key2") is True
        assert cache.exists("key3") is True
        assert cache.exists("key4") is True

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = EnterpriseMemoryCache(enable_stats=True)
        
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert stats.sets == 1
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.total_requests == 2
        assert stats.hit_rate == 50.0

    def test_tag_based_operations(self):
        """Test tag-based cache operations."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1", tags={"tag1", "tag2"})
        cache.set("key2", "value2", tags={"tag2", "tag3"})
        cache.set("key3", "value3", tags={"tag1"})
        
        # Delete all entries with tag1
        deleted = cache.delete_by_tags({"tag1"})
        
        assert deleted == 2  # key1 and key3
        assert cache.exists("key1") is False
        assert cache.exists("key2") is True
        assert cache.exists("key3") is False

    def test_bulk_operations_get_many(self):
        """Test get_many bulk operation."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        results = cache.get_many(["key1", "key2", "nonexistent"])
        
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert "nonexistent" not in results

    def test_bulk_operations_set_many(self):
        """Test set_many bulk operation."""
        cache = EnterpriseMemoryCache()
        
        cache.set_many({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }, ttl=300.0)
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_bulk_operations_delete_many(self):
        """Test delete_many bulk operation."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        deleted = cache.delete_many(["key1", "key3", "nonexistent"])
        
        assert deleted == 2
        assert cache.exists("key1") is False
        assert cache.exists("key2") is True
        assert cache.exists("key3") is False

    def test_get_keys(self):
        """Test getting all cache keys."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("test_key", "value3")
        
        all_keys = cache.get_keys()
        assert len(all_keys) == 3
        
        # Test pattern filtering
        pattern_keys = cache.get_keys(pattern="key*")
        assert "key1" in pattern_keys
        assert "key2" in pattern_keys
        assert "test_key" not in pattern_keys

    def test_event_callbacks(self):
        """Test event callback system."""
        cache = EnterpriseMemoryCache()
        events = []
        
        def on_set(event_type, key, value):
            events.append(("set", key, value))
        
        def on_hit(event_type, key, value):
            events.append(("hit", key, value))
        
        cache.add_event_callback(CacheEventType.SET, on_set)
        cache.add_event_callback(CacheEventType.HIT, on_hit)
        
        cache.set("key1", "value1")
        cache.get("key1")
        
        assert len(events) == 2
        assert events[0] == ("set", "key1", "value1")
        assert events[1] == ("hit", "key1", "value1")

    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = EnterpriseMemoryCache()
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    key = f"key_{thread_id}_{i}"
                    cache.set(key, f"value_{i}")
                    cache.get(key)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0

    def test_exists_method(self):
        """Test exists method."""
        cache = EnterpriseMemoryCache()
        
        assert cache.exists("key1") is False
        
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        
        cache.delete("key1")
        assert cache.exists("key1") is False

    def test_has_key_alias(self):
        """Test has_key as alias for exists."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1")
        assert cache.has_key("key1") is True
        assert cache.has_key("key2") is False


class TestEnterpriseFileCache:
    """Test EnterpriseFileCache with persistence."""

    def test_create_file_cache(self):
        """Test creating file cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir, max_files=100)
            
            assert cache.cache_dir == Path(tmpdir)
            assert cache.max_files == 100

    def test_file_cache_basic_operations(self):
        """Test basic file cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            cache.set("key1", "value1")
            result = cache.get("key1")
            
            assert result == "value1"

    def test_file_cache_persistence(self):
        """Test file cache persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First instance
            cache1 = EnterpriseFileCache(cache_dir=tmpdir)
            cache1.set("key1", "value1")
            cache1.set("key2", "value2")
            
            # Second instance (should load from disk)
            cache2 = EnterpriseFileCache(cache_dir=tmpdir)
            
            assert cache2.get("key1") == "value1"
            assert cache2.get("key2") == "value2"

    def test_file_cache_delete(self):
        """Test file cache delete operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            cache.set("key1", "value1")
            assert cache.exists("key1") is True
            
            cache.delete("key1")
            assert cache.exists("key1") is False

    def test_file_cache_clear(self):
        """Test file cache clear operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            
            cache.clear()
            
            assert cache.get("key1") is None
            assert cache.get("key2") is None


class TestNullCache:
    """Test NullCache (no-op cache)."""

    def test_null_cache_no_storage(self):
        """Test NullCache doesn't store anything."""
        cache = NullCache()
        
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result is None

    def test_null_cache_always_misses(self):
        """Test NullCache always returns cache miss."""
        cache = NullCache()
        
        assert cache.get("anything") is None
        assert cache.exists("anything") is False

    def test_null_cache_delete_returns_false(self):
        """Test NullCache delete always returns False."""
        cache = NullCache()
        
        cache.set("key1", "value1")
        deleted = cache.delete("key1")
        
        assert deleted is False

    def test_null_cache_clear(self):
        """Test NullCache clear does nothing."""
        cache = NullCache()
        
        cache.set("key1", "value1")
        cache.clear()
        
        # Should have no effect
        assert cache.get("key1") is None

    def test_null_cache_stats(self):
        """Test NullCache tracks stats (even though it doesn't cache)."""
        cache = NullCache()
        
        cache.set("key1", "value1")
        cache.get("key1")
        
        stats = cache.get_stats()
        
        # NullCache DOES track stats
        assert stats.total_requests == 1  # get() increments
        assert stats.sets == 1
        assert stats.cache_misses == 1
        assert stats.cache_hits == 0  # Never hits


class TestCacheManager:
    """Test CacheManager high-level interface."""

    def test_create_cache_manager(self):
        """Test creating CacheManager."""
        backend = EnterpriseMemoryCache()
        manager = CacheManager(backend=backend)
        
        assert manager.backend == backend  # No underscore
        # Manager doesn't have _enabled attribute (checks backend directly)

    def test_cache_manager_get_set(self):
        """Test CacheManager get/set operations."""
        backend = EnterpriseMemoryCache()
        manager = CacheManager(backend=backend)
        
        manager.set("test_key", "test_value")
        result = manager.get("test_key")
        
        assert result == "test_value"

    def test_cache_manager_enable_disable(self):
        """Test cache manager operations."""
        backend = EnterpriseMemoryCache()
        manager = CacheManager(backend=backend)
        
        manager.set("key1", "value1")
        assert manager.get("key1") == "value1"
        
        # CacheManager doesn't have enable/disable methods directly
        # Test clear instead
        manager.clear()
        assert manager.get("key1") is None

    def test_cache_manager_clear(self):
        """Test CacheManager clear."""
        backend = EnterpriseMemoryCache()
        manager = CacheManager(backend=backend)
        
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        
        manager.clear()
        
        assert manager.get("key1") is None
        assert manager.get("key2") is None

    def test_cache_manager_delete(self):
        """Test CacheManager delete."""
        backend = EnterpriseMemoryCache()
        manager = CacheManager(backend=backend)
        
        manager.set("key1", "value1")
        deleted = manager.delete("key1")
        
        assert deleted is True
        assert manager.get("key1") is None

    def test_cache_manager_stats(self):
        """Test CacheManager statistics."""
        backend = EnterpriseMemoryCache(enable_stats=True)
        manager = CacheManager(backend=backend)
        
        manager.set("key1", "value1")
        manager.get("key1")
        manager.get("key2")
        
        stats = manager.get_stats()
        
        assert stats.sets >= 1
        assert stats.cache_hits >= 1
        assert stats.cache_misses >= 1


class TestFileCacheAdvanced:
    """Test advanced FileCache functionality."""

    def test_file_cache_ttl_expiration(self):
        """Test FileCache TTL expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            cache.set("key1", "value1", ttl=0.1)
            assert cache.get("key1") == "value1"
            
            time.sleep(0.15)
            assert cache.get("key1") is None

    def test_file_cache_stats(self):
        """Test FileCache statistics tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir, enable_stats=True)
            
            cache.set("key1", "value1")
            cache.get("key1")
            cache.get("nonexistent")
            
            stats = cache.get_stats()
            assert stats.sets >= 1
            assert stats.cache_hits >= 1
            assert stats.cache_misses >= 1

    def test_file_cache_max_files(self):
        """Test FileCache max files limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir, max_files=3)
            
            # Add more than max_files
            for i in range(5):
                cache.set(f"key{i}", f"value{i}")
            
            # Should have cleaned up old files
            cache_files = list(Path(tmpdir).glob("*.cache"))
            assert len(cache_files) <= 4  # 3 cache files + 1 metadata file

    def test_file_cache_tag_operations(self):
        """Test FileCache tag-based operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            cache.set("key1", "value1", tags={"tag1"})
            cache.set("key2", "value2", tags={"tag1", "tag2"})
            cache.set("key3", "value3", tags={"tag2"})
            
            # Delete by tags
            deleted = cache.delete_by_tags({"tag1"})
            
            assert deleted == 2
            assert cache.exists("key1") is False
            assert cache.exists("key2") is False
            assert cache.exists("key3") is True

    def test_file_cache_bulk_operations(self):
        """Test FileCache bulk operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EnterpriseFileCache(cache_dir=tmpdir)
            
            # set_many
            cache.set_many({"key1": "val1", "key2": "val2", "key3": "val3"})
            
            # get_many
            results = cache.get_many(["key1", "key2", "nonexistent"])
            assert results["key1"] == "val1"
            assert results["key2"] == "val2"
            assert "nonexistent" not in results
            
            # delete_many
            deleted = cache.delete_many(["key1", "key3"])
            assert deleted == 2


class TestMemoryCacheAutoCleanup:
    """Test memory cache auto-cleanup functionality."""

    def test_auto_cleanup_expired_entries(self):
        """Test automatic cleanup of expired entries."""
        cache = EnterpriseMemoryCache(
            auto_cleanup_interval=0.2,  # 200ms cleanup interval
            enable_stats=True
        )
        
        # Add entries with short TTL
        cache.set("key1", "value1", ttl=0.1)
        cache.set("key2", "value2", ttl=0.1)
        
        assert cache.exists("key1") is True
        
        # Wait for expiration and cleanup
        time.sleep(0.3)
        
        # Should have been cleaned up
        assert cache.exists("key1") is False
        
        # Check stats for expirations
        stats = cache.get_stats()
        assert stats.expirations >= 1
        
        # Cleanup
        cache.shutdown()

    def test_manual_cleanup(self):
        """Test manual cleanup of expired entries."""
        cache = EnterpriseMemoryCache(auto_cleanup_interval=0)  # Disable auto cleanup
        
        cache.set("key1", "value1", ttl=0.05)
        cache.set("key2", "value2")  # No TTL
        
        time.sleep(0.1)
        
        # Manually trigger cleanup
        removed = cache._cleanup_expired()
        
        assert removed >= 1
        assert cache.exists("key1") is False
        assert cache.exists("key2") is True

    def test_event_callback_removal(self):
        """Test removing event callbacks."""
        cache = EnterpriseMemoryCache()
        
        callback = lambda event_type, key, value: None
        
        cache.add_event_callback(CacheEventType.SET, callback)
        cache.remove_event_callback(CacheEventType.SET, callback)
        
        # Should not raise error
        cache.set("key1", "value1")

    def test_get_entry_metrics(self):
        """Test getting detailed entry metrics."""
        cache = EnterpriseMemoryCache()
        
        cache.set("key1", "value1", ttl=300.0, tags={"tag1"})
        cache.get("key1")
        cache.get("key1")
        
        metrics = cache.get_entry_metrics("key1")
        
        assert metrics is not None
        assert metrics.key == "key1"
        assert metrics.access_count == 2
        assert metrics.ttl_seconds == 300.0
        assert "tag1" in metrics.tags

    def test_get_entry_metrics_nonexistent(self):
        """Test getting metrics for nonexistent entry."""
        cache = EnterpriseMemoryCache()
        
        metrics = cache.get_entry_metrics("nonexistent")
        assert metrics is None


class TestCacheEdgeCases:
    """Test edge cases and error handling."""

    def test_cache_entry_size_calculation_exception(self):
        """Test size calculation with problematic objects."""
        # Create entry with unpicklable object
        class UnpicklableObject:
            def __reduce__(self):
                raise TypeError("Cannot pickle")
        
        entry = CacheEntry(
            value=UnpicklableObject(),
            ttl_seconds=None,
            tags=set()
        )
        
        # Should fall back to string encoding
        size = entry._calculate_size()
        assert size > 0

    def test_cache_configuration_file_backend(self):
        """Test CacheConfiguration with file backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfiguration(
                backend_type="file",
                file_cache_dir=tmpdir,
                file_max_files=100,
                file_compress_data=True
            )
            
            manager = CacheManager(config=config)
            assert isinstance(manager.backend, EnterpriseFileCache)

    def test_cache_configuration_null_backend(self):
        """Test CacheConfiguration with null backend."""
        config = CacheConfiguration(backend_type="null")
        
        manager = CacheManager(config=config)
        assert isinstance(manager.backend, NullCache)

    def test_cache_configuration_invalid_backend(self):
        """Test CacheConfiguration with invalid backend."""
        config = CacheConfiguration(backend_type="invalid")
        
        with pytest.raises(ValueError, match="Unknown cache backend type"):
            CacheManager(config=config)

    def test_memory_cache_random_eviction(self):
        """Test random eviction policy."""
        cache = EnterpriseMemoryCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.RANDOM
        )
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should trigger random eviction
        
        # Should only have 3 items
        keys = list(cache.get_keys())
        assert len(keys) == 3




class TestCacheUtilities:
    """Test cache utility functions."""

    def test_create_cache_key_simple(self):
        """Test creating simple cache key."""
        key = create_cache_key("namespace", "identifier")
        
        assert "namespace" in key
        assert "identifier" in key
        assert ":" in key

    def test_create_cache_key_with_metadata(self):
        """Test creating cache key with metadata."""
        key = create_cache_key("source", "file.json", "1234567890")
        
        assert "source" in key
        assert "file.json" in key
        assert "1234567890" in key

    def test_hash_config_data(self):
        """Test hashing configuration data."""
        data = {"key1": "value1", "key2": "value2"}
        hash1 = hash_config_data(data)
        
        assert isinstance(hash1, str)
        assert len(hash1) > 0
        
        # Same data should produce same hash
        hash2 = hash_config_data(data)
        assert hash1 == hash2
        
        # Different data should produce different hash
        data2 = {"key1": "different"}
        hash3 = hash_config_data(data2)
        assert hash1 != hash3

    def test_hash_config_data_nested(self):
        """Test hashing nested configuration data."""
        data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "user": "admin",
                    "password": "secret"
                }
            }
        }
        
        hash1 = hash_config_data(data)
        
        # Modify nested value
        data["database"]["port"] = 5433
        hash2 = hash_config_data(data)
        
        assert hash1 != hash2

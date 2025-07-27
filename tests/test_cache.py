"""
Tests for the configuration caching system.
"""

import unittest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from config_manager.cache import (
    CacheBackend, MemoryCache, FileCache, NullCache, ConfigCache,
    create_cache_key, get_global_cache, set_global_cache, clear_global_cache
)
from config_manager.config_manager import ConfigManager
from config_manager.sources import JsonSource


class TestCacheKey(unittest.TestCase):
    """Test cache key generation."""
    
    def test_simple_key(self):
        """Test simple cache key generation."""
        key = create_cache_key("test", "data")
        expected = "test:data:d81b4a67e3bc2c6b1ee64b3fced2fd8b"
        self.assertEqual(key, expected)
    
    def test_complex_key(self):
        """Test complex cache key with multiple parts."""
        key = create_cache_key("config", "file.json", "123456", "extra")
        # Should include all parts in the hash
        self.assertTrue(key.startswith("config:file.json:123456:extra:"))
        self.assertEqual(len(key.split(":")[-1]), 32)  # MD5 hash length
    
    def test_empty_parts(self):
        """Test cache key with empty parts."""
        key = create_cache_key("test", "", "data")
        self.assertTrue(key.startswith("test::data:"))


class TestMemoryCache(unittest.TestCase):
    """Test memory cache implementation."""
    
    def setUp(self):
        """Set up test cache."""
        self.cache = MemoryCache(max_size=3, default_ttl=1.0)
    
    def test_basic_operations(self):
        """Test basic cache operations."""
        # Test get on empty cache
        self.assertIsNone(self.cache.get("key1"))
        
        # Test set and get
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # Test has_key
        self.assertTrue(self.cache.has_key("key1"))
        self.assertFalse(self.cache.has_key("nonexistent"))
        
        # Test delete
        self.cache.delete("key1")
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.has_key("key1"))
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        self.cache.set("key1", "value1", ttl=0.1)
        self.assertEqual(self.cache.get("key1"), "value1")
        
        time.sleep(0.15)
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.has_key("key1"))
    
    def test_lru_eviction(self):
        """Test LRU eviction."""
        # Fill cache to capacity
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        self.cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        self.cache.set("key4", "value4")
        
        self.assertTrue(self.cache.has_key("key1"))
        self.assertFalse(self.cache.has_key("key2"))  # Evicted
        self.assertTrue(self.cache.has_key("key3"))
        self.assertTrue(self.cache.has_key("key4"))
    
    def test_clear(self):
        """Test cache clearing."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(len(self.cache._cache), 0)
    
    def test_stats(self):
        """Test cache statistics."""
        stats = self.cache.get_stats()
        initial_hits = stats["hits"]
        initial_misses = stats["misses"]
        
        # Test miss
        self.cache.get("nonexistent")
        stats = self.cache.get_stats()
        self.assertEqual(stats["misses"], initial_misses + 1)
        
        # Test hit
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], initial_hits + 1)
        
        # Check other stats
        self.assertIn("size", stats)
        self.assertIn("max_size", stats)
        self.assertIn("evictions", stats)
    
    def test_thread_safety(self):
        """Test thread safety."""
        def worker(start_key: int):
            for i in range(10):
                key = f"key_{start_key}_{i}"
                value = f"value_{start_key}_{i}"
                self.cache.set(key, value)
                self.assertEqual(self.cache.get(key), value)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Cache should still be functional
        self.cache.set("test", "value")
        self.assertEqual(self.cache.get("test"), "value")


class TestFileCache(unittest.TestCase):
    """Test file cache implementation."""
    
    def setUp(self):
        """Set up test cache."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = FileCache(cache_dir=self.temp_dir, default_ttl=1.0)
    
    def tearDown(self):
        """Clean up test cache."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_operations(self):
        """Test basic cache operations."""
        # Test get on empty cache
        self.assertIsNone(self.cache.get("key1"))
        
        # Test set and get
        self.cache.set("key1", {"test": "data"})
        result = self.cache.get("key1")
        self.assertEqual(result, {"test": "data"})
        
        # Test has_key
        self.assertTrue(self.cache.has_key("key1"))
        self.assertFalse(self.cache.has_key("nonexistent"))
        
        # Test delete
        self.cache.delete("key1")
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.has_key("key1"))
    
    def test_persistence(self):
        """Test cache persistence across instances."""
        # Set data in first instance
        self.cache.set("persistent_key", {"data": "persisted"})
        
        # Create new cache instance with same directory
        new_cache = FileCache(cache_dir=self.temp_dir)
        result = new_cache.get("persistent_key")
        self.assertEqual(result, {"data": "persisted"})
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        self.cache.set("key1", "value1", ttl=0.1)
        self.assertEqual(self.cache.get("key1"), "value1")
        
        time.sleep(0.15)
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.has_key("key1"))
    
    def test_cleanup(self):
        """Test automatic cleanup of expired entries."""
        # Set items with short TTL
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}", ttl=0.1)
        
        time.sleep(0.15)
        
        # Trigger cleanup
        self.cache._cleanup_expired()
        
        # All should be gone
        for i in range(5):
            self.assertIsNone(self.cache.get(f"key_{i}"))
    
    def test_clear(self):
        """Test cache clearing."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        
        # Cache directory should be empty except for metadata
        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 0)


class TestNullCache(unittest.TestCase):
    """Test null cache implementation."""
    
    def setUp(self):
        """Set up test cache."""
        self.cache = NullCache()
    
    def test_no_operations(self):
        """Test that null cache doesn't store anything."""
        # All operations should be no-ops
        self.cache.set("key1", "value1")
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.has_key("key1"))
        
        # Delete should not fail
        self.cache.delete("key1")
        
        # Clear should not fail
        self.cache.clear()
    
    def test_stats(self):
        """Test null cache statistics."""
        stats = self.cache.get_stats()
        expected = {
            "type": "null",
            "enabled": True,
            "hits": 0,
            "misses": 0,
            "size": 0
        }
        self.assertEqual(stats, expected)


class TestConfigCache(unittest.TestCase):
    """Test configuration cache manager."""
    
    def setUp(self):
        """Set up test cache."""
        self.backend = MemoryCache(max_size=10)
        self.cache = ConfigCache(backend=self.backend)
    
    def test_basic_operations(self):
        """Test basic cache operations."""
        # Test cache and retrieve
        data = {"test": "data"}
        self.cache.cache_config("source1", data)
        
        result = self.cache.get_config("source1")
        self.assertEqual(result, data)
        
        # Test cache miss
        self.assertIsNone(self.cache.get_config("nonexistent"))
    
    def test_invalidation(self):
        """Test cache invalidation."""
        self.cache.cache_config("source1", {"test": "data"})
        self.assertTrue(self.cache.is_cached("source1"))
        
        self.cache.invalidate("source1")
        self.assertFalse(self.cache.is_cached("source1"))
        self.assertIsNone(self.cache.get_config("source1"))
    
    def test_enable_disable(self):
        """Test enabling and disabling cache."""
        # Cache something while enabled
        self.cache.cache_config("source1", {"test": "data"})
        self.assertEqual(self.cache.get_config("source1"), {"test": "data"})
        
        # Disable cache
        self.cache.disable()
        self.assertIsNone(self.cache.get_config("source1"))
        
        # Re-enable cache
        self.cache.enable()
        # Data should still be in backend
        self.assertEqual(self.cache.get_config("source1"), {"test": "data"})
    
    def test_stats(self):
        """Test cache statistics."""
        stats = self.cache.get_stats()
        self.assertIn("backend", stats)
        self.assertIn("enabled", stats)
        self.assertEqual(stats["enabled"], True)
    
    def test_with_ttl(self):
        """Test cache with TTL."""
        self.cache.cache_config("source1", {"test": "data"}, ttl=0.1)
        self.assertEqual(self.cache.get_config("source1"), {"test": "data"})
        
        time.sleep(0.15)
        self.assertIsNone(self.cache.get_config("source1"))


class TestGlobalCache(unittest.TestCase):
    """Test global cache functionality."""
    
    def setUp(self):
        """Set up tests."""
        clear_global_cache()
    
    def tearDown(self):
        """Clean up tests."""
        clear_global_cache()
    
    def test_global_cache_operations(self):
        """Test global cache operations."""
        # Initially should be None
        self.assertIsNone(get_global_cache())
        
        # Set global cache
        cache = ConfigCache(MemoryCache())
        set_global_cache(cache)
        
        # Should return the same instance
        self.assertIs(get_global_cache(), cache)
        
        # Clear global cache
        clear_global_cache()
        self.assertIsNone(get_global_cache())


class TestConfigManagerCaching(unittest.TestCase):
    """Test ConfigManager caching integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # Create test config file
        with open(self.config_file, 'w') as f:
            f.write('{"test_key": "test_value", "number": 42}')
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        clear_global_cache()
    
    def test_cache_enabled_by_default(self):
        """Test that caching is enabled by default."""
        cm = ConfigManager()
        self.assertTrue(cm.is_caching_enabled())
    
    def test_custom_cache(self):
        """Test ConfigManager with custom cache."""
        custom_cache = ConfigCache(MemoryCache(max_size=5))
        cm = ConfigManager(cache=custom_cache)
        
        # Should use the custom cache
        self.assertIs(cm._cache, custom_cache)
    
    def test_disable_caching(self):
        """Test disabling caching."""
        cm = ConfigManager(enable_caching=False)
        self.assertFalse(cm.is_caching_enabled())
    
    def test_cache_management_methods(self):
        """Test cache management methods."""
        cm = ConfigManager()
        
        # Test cache stats
        stats = cm.get_cache_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("backend", stats)
        
        # Test cache control
        cm.disable_caching()
        self.assertFalse(cm.is_caching_enabled())
        
        cm.enable_caching()
        self.assertTrue(cm.is_caching_enabled())
        
        # Test cache clearing
        cm.clear_cache()  # Should not raise
    
    def test_cached_source_loading(self):
        """Test that source loading uses cache."""
        cache = ConfigCache(MemoryCache())
        cm = ConfigManager(cache=cache)
        
        # Add source
        source = JsonSource(self.config_file)
        cm.add_source(source)
        
        # Load config (should cache)
        config1 = cm.get_config()
        
        # Load again (should hit cache)
        config2 = cm.get_config()
        
        self.assertEqual(config1, config2)
        
        # Check that cache was used
        stats = cm.get_cache_stats()
        self.assertGreater(stats["backend"]["hits"], 0)
    
    def test_cache_invalidation_on_file_change(self):
        """Test cache invalidation when file changes."""
        cache = ConfigCache(MemoryCache())
        cm = ConfigManager(cache=cache)
        
        source = JsonSource(self.config_file)
        cm.add_source(source)
        
        # Load initial config
        config1 = cm.get_config()
        self.assertEqual(config1["test_key"], "test_value")
        
        # Modify file
        time.sleep(0.01)  # Ensure different mtime
        with open(self.config_file, 'w') as f:
            f.write('{"test_key": "modified_value", "number": 42}')
        
        # Reload - should detect file change and update
        cm.reload()
        config2 = cm.get_config()
        self.assertEqual(config2["test_key"], "modified_value")
    
    def test_cache_key_generation(self):
        """Test cache key generation for sources."""
        cm = ConfigManager()
        source = JsonSource(self.config_file)
        
        # Should generate consistent cache key
        key1 = cm.get_cache_key_for_source(source)
        key2 = cm.get_cache_key_for_source(source)
        self.assertEqual(key1, key2)
        
        # Key should include file path and mtime
        self.assertIn("json_source", key1)
    
    @patch('config_manager.config_manager.time.time')
    def test_cache_performance(self, mock_time):
        """Test that caching improves performance."""
        mock_time.return_value = 1000.0
        
        # Create a mock source that tracks load calls
        class SlowSource:
            def __init__(self):
                self.load_count = 0
                self._file_path = self.config_file
            
            def load(self):
                self.load_count += 1
                time.sleep(0.01)  # Simulate slow loading
                return {"slow": "data"}
        
        cache = ConfigCache(MemoryCache())
        cm = ConfigManager(cache=cache)
        
        slow_source = SlowSource()
        cm.add_source(slow_source)
        
        # First load - should hit source
        start_time = time.time()
        cm.get_config()
        first_load_time = time.time() - start_time
        self.assertEqual(slow_source.load_count, 1)
        
        # Second load - should hit cache
        start_time = time.time()
        cm.get_config()
        second_load_time = time.time() - start_time
        self.assertEqual(slow_source.load_count, 1)  # No additional load
        
        # Cache should be faster
        self.assertLess(second_load_time, first_load_time)


if __name__ == '__main__':
    unittest.main()

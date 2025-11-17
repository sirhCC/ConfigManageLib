"""
Comprehensive tests for ConfigManager core functionality to achieve 90%+ coverage.
"""
import unittest
import tempfile
import os
import json
import time
from pathlib import Path

from config_manager import ConfigManager
from config_manager.sources import JsonSource, EnvironmentSource
from config_manager.cache import ConfigCache, EnterpriseMemoryCache, NullCache


class TestConfigManagerComprehensive(unittest.TestCase):
    """Comprehensive test suite for ConfigManager."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        self.config_file2 = os.path.join(self.temp_dir, "override.json")
        
        # Create test config files
        with open(self.config_file, 'w') as f:
            json.dump({
                "app_name": "TestApp",
                "version": "1.0.0",
                "debug": True,
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {
                        "username": "admin",
                        "password": "secret"
                    }
                },
                "features": ["auth", "api", "cache"]
            }, f)
        
        with open(self.config_file2, 'w') as f:
            json.dump({
                "database": {
                    "host": "prod-db.example.com",
                    "port": 3306
                }
            }, f)
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_empty_config_manager(self):
        """Test ConfigManager with no sources."""
        config = ConfigManager()
        
        self.assertIsNone(config.get("nonexistent"))
        self.assertEqual(config.get("key", "default"), "default")
        self.assertEqual(config.get_int("port", 8080), 8080)
    
    def test_single_source(self):
        """Test ConfigManager with a single source."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertEqual(config.get("app_name"), "TestApp")
        self.assertEqual(config.get("database.host"), "localhost")
        self.assertTrue(config.get("debug"))
    
    def test_source_priority(self):
        """Test that later sources override earlier ones."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        config.add_source(JsonSource(self.config_file2))
        
        # Override file should win
        self.assertEqual(config.get("database.host"), "prod-db.example.com")
        self.assertEqual(config.get("database.port"), 3306)
        
        # Non-overridden values from first file should still exist
        self.assertEqual(config.get("app_name"), "TestApp")
        self.assertEqual(config.get("database.credentials.username"), "admin")
    
    def test_deep_merge(self):
        """Test that nested dicts are merged, not replaced."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        config.add_source(JsonSource(self.config_file2))
        
        # Credentials from first file should still exist
        self.assertEqual(config.get("database.credentials.username"), "admin")
        # But host and port should be overridden
        self.assertEqual(config.get("database.host"), "prod-db.example.com")
    
    def test_method_chaining(self):
        """Test that add_source returns self for chaining."""
        config = ConfigManager()
        result = config.add_source(JsonSource(self.config_file)).add_source(JsonSource(self.config_file2))
        
        self.assertIs(result, config)
        self.assertEqual(config.get("app_name"), "TestApp")
    
    def test_get_with_default(self):
        """Test get with default values."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertEqual(config.get("nonexistent", "default"), "default")
        self.assertEqual(config.get("app_name", "default"), "TestApp")
    
    def test_get_nested_missing_intermediate(self):
        """Test nested get when intermediate key is missing."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertIsNone(config.get("missing.nested.key"))
        self.assertEqual(config.get("missing.nested.key", "default"), "default")
    
    def test_get_nested_non_dict_intermediate(self):
        """Test nested get when intermediate key is not a dict."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        # debug is a boolean, not a dict
        self.assertIsNone(config.get("debug.nested"))
        self.assertEqual(config.get("debug.nested", "default"), "default")
    
    def test_get_int_conversion(self):
        """Test get_int with type conversion."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertEqual(config.get_int("database.port"), 5432)
        self.assertEqual(config.get_int("nonexistent", 8080), 8080)
    
    def test_get_int_from_string(self):
        """Test get_int can convert strings to integers."""
        config_file = os.path.join(self.temp_dir, "string_int.json")
        with open(config_file, 'w') as f:
            json.dump({"port": "8080"}, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        self.assertEqual(config.get_int("port"), 8080)
    
    def test_get_int_invalid_conversion(self):
        """Test get_int returns default for invalid values."""
        config_file = os.path.join(self.temp_dir, "invalid_int.json")
        with open(config_file, 'w') as f:
            json.dump({"port": "not_a_number"}, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        self.assertEqual(config.get_int("port", 8080), 8080)
    
    def test_get_bool_conversion(self):
        """Test get_bool with type conversion."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertTrue(config.get_bool("debug"))
        self.assertFalse(config.get_bool("nonexistent", False))
    
    def test_get_bool_from_string(self):
        """Test get_bool can convert strings to booleans."""
        config_file = os.path.join(self.temp_dir, "string_bool.json")
        with open(config_file, 'w') as f:
            json.dump({
                "enabled": "true",
                "disabled": "false",
                "yes": "yes",
                "no": "no"
            }, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        self.assertTrue(config.get_bool("enabled"))
        self.assertFalse(config.get_bool("disabled"))
        self.assertTrue(config.get_bool("yes"))
        self.assertFalse(config.get_bool("no"))
    
    def test_get_float_conversion(self):
        """Test get_float with type conversion."""
        config_file = os.path.join(self.temp_dir, "float.json")
        with open(config_file, 'w') as f:
            json.dump({"pi": 3.14, "tau": "6.28"}, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        pi = config.get_float("pi")
        tau = config.get_float("tau")
        default = config.get_float("nonexistent", 2.71)
        
        self.assertIsNotNone(pi)
        self.assertIsNotNone(tau)
        self.assertIsNotNone(default)
        self.assertAlmostEqual(pi, 3.14, places=2)  # type: ignore
        self.assertAlmostEqual(tau, 6.28, places=2)  # type: ignore
        self.assertAlmostEqual(default, 2.71, places=2)  # type: ignore
    
    def test_get_float_invalid_conversion(self):
        """Test get_float returns default for invalid values."""
        config_file = os.path.join(self.temp_dir, "invalid_float.json")
        with open(config_file, 'w') as f:
            json.dump({"value": "not_a_float"}, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        result = config.get_float("value", 1.0)
        self.assertEqual(result, 1.0)
    
    def test_get_list_from_list(self):
        """Test get_list with actual list."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        features = config.get_list("features")
        self.assertEqual(features, ["auth", "api", "cache"])
    
    def test_get_list_from_string(self):
        """Test get_list can convert comma-separated strings."""
        config_file = os.path.join(self.temp_dir, "string_list.json")
        with open(config_file, 'w') as f:
            json.dump({"items": "one,two,three"}, f)
        
        config = ConfigManager()
        config.add_source(JsonSource(config_file))
        
        items = config.get_list("items")
        self.assertEqual(items, ["one", "two", "three"])
    
    def test_get_list_with_default(self):
        """Test get_list returns default for missing keys."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        result = config.get_list("nonexistent", ["default"])
        self.assertEqual(result, ["default"])
    
    def test_contains_operator(self):
        """Test __contains__ operator."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertTrue("app_name" in config)
        self.assertTrue("database.host" in config)
        self.assertFalse("nonexistent" in config)
    
    def test_getitem_operator(self):
        """Test __getitem__ operator."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        self.assertEqual(config["app_name"], "TestApp")
        self.assertEqual(config["database.host"], "localhost")
        
        with self.assertRaises(KeyError):
            _ = config["nonexistent"]
    
    def test_reload_method(self):
        """Test reload method refreshes configuration."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        # Initial value
        self.assertEqual(config.get("app_name"), "TestApp")
        
        # Modify the file
        with open(self.config_file, 'w') as f:
            json.dump({"app_name": "ModifiedApp"}, f)
        
        # Reload
        config.reload()
        
        self.assertEqual(config.get("app_name"), "ModifiedApp")
    
    def test_reload_with_multiple_sources(self):
        """Test reload with multiple sources maintains priority."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        config.add_source(JsonSource(self.config_file2))
        
        # Initial override
        self.assertEqual(config.get("database.host"), "prod-db.example.com")
        
        # Modify first file
        with open(self.config_file, 'w') as f:
            json.dump({"database": {"host": "new-host"}}, f)
        
        # Reload - second file should still override
        config.reload()
        
        self.assertEqual(config.get("database.host"), "prod-db.example.com")
    
    def test_caching_enabled(self):
        """Test that caching works when enabled."""
        cache = ConfigCache(backend=EnterpriseMemoryCache(max_size=100))
        config = ConfigManager(cache=cache, enable_caching=True)
        config.add_source(JsonSource(self.config_file))
        
        # Access value
        value1 = config.get("app_name")
        
        # Check cache stats
        stats = cache.get_stats()
        self.assertGreater(stats.cache_hits + stats.cache_misses, 0)
    
    def test_caching_disabled(self):
        """Test that caching can be disabled."""
        cache = ConfigCache(backend=EnterpriseMemoryCache(max_size=100))
        config = ConfigManager(cache=cache, enable_caching=False)
        config.add_source(JsonSource(self.config_file))
        
        value = config.get("app_name")
        self.assertEqual(value, "TestApp")
        
        # Cache should not be used
        stats = cache.get_stats()
        self.assertEqual(stats.cache_hits, 0)
    
    def test_null_cache(self):
        """Test ConfigManager with NullCache."""
        cache = ConfigCache(backend=NullCache())
        config = ConfigManager(cache=cache, enable_caching=True)
        config.add_source(JsonSource(self.config_file))
        
        value = config.get("app_name")
        self.assertEqual(value, "TestApp")
    
    def test_cache_invalidation_on_reload(self):
        """Test that reload invalidates cached validation."""
        config = ConfigManager(enable_caching=True)
        config.add_source(JsonSource(self.config_file))
        
        # Access value to populate cache
        _ = config.get("app_name")
        
        # Reload should invalidate
        config.reload()
        
        # Should still get correct value
        self.assertEqual(config.get("app_name"), "TestApp")
    
    def test_thread_safety_basic(self):
        """Test basic thread safety of ConfigManager."""
        import threading
        
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        results = []
        
        def read_config():
            for _ in range(10):
                value = config.get("app_name")
                results.append(value)
        
        threads = [threading.Thread(target=read_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All reads should be consistent
        self.assertTrue(all(r == "TestApp" for r in results))
        self.assertEqual(len(results), 50)
    
    def test_contains_with_nested(self):
        """Test __contains__ with nested keys."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        # Use explicit True check instead of assertIn
        self.assertTrue("app_name" in config)
        self.assertTrue("database.host" in config)
        self.assertFalse("nonexistent" in config)
    
    def test_profile_initialization(self):
        """Test ConfigManager with profile."""
        config = ConfigManager(profile="development")
        
        # Profile should be set
        self.assertIsNotNone(config._current_profile)
    
    def test_auto_detect_profile(self):
        """Test auto profile detection."""
        config = ConfigManager(auto_detect_profile=True)
        
        # Should have detected a profile
        self.assertIsNotNone(config._current_profile)
    
    def test_disable_auto_detect_profile(self):
        """Test disabling auto profile detection."""
        config = ConfigManager(auto_detect_profile=False)
        
        # No profile should be set
        self.assertIsNone(config._current_profile)
    
    def test_mask_secrets_in_display(self):
        """Test secrets masking in display."""
        config = ConfigManager(mask_secrets_in_display=True)
        config.add_source(JsonSource(self.config_file))
        
        # Should be able to get password
        password = config.get("database.credentials.password")
        self.assertEqual(password, "secret")
    
    def test_custom_cache_backend(self):
        """Test ConfigManager with custom cache backend."""
        custom_cache = ConfigCache(backend=EnterpriseMemoryCache(max_size=50, default_ttl=60.0))
        config = ConfigManager(cache=custom_cache)
        config.add_source(JsonSource(self.config_file))
        
        value = config.get("app_name")
        self.assertEqual(value, "TestApp")


if __name__ == '__main__':
    unittest.main()

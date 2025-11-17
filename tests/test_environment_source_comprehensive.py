"""
Comprehensive tests for EnvironmentSource to achieve 90%+ coverage.
"""
import unittest
import os
from config_manager.sources.environment import EnvironmentSource


class TestEnvironmentSourceComprehensive(unittest.TestCase):
    """Comprehensive test suite for EnvironmentSource."""
    
    def setUp(self):
        """Set up test environment variables."""
        # Basic test variables
        os.environ["TEST_SIMPLE"] = "simple_value"
        os.environ["TEST_INT"] = "42"
        os.environ["TEST_FLOAT"] = "3.14"
        os.environ["TEST_BOOL_TRUE"] = "true"
        os.environ["TEST_BOOL_FALSE"] = "false"
        os.environ["TEST_LIST"] = "item1,item2,item3"
        
        # Nested structure tests
        os.environ["TEST_DATABASE_HOST"] = "localhost"
        os.environ["TEST_DATABASE_PORT"] = "5432"
        os.environ["TEST_DATABASE_CREDENTIALS_USERNAME"] = "admin"
        os.environ["TEST_DATABASE_CREDENTIALS_PASSWORD"] = "secret"
        
        # Boolean variations
        os.environ["TEST_BOOL_YES"] = "yes"
        os.environ["TEST_BOOL_NO"] = "no"
        os.environ["TEST_BOOL_ON"] = "on"
        os.environ["TEST_BOOL_OFF"] = "off"
        os.environ["TEST_BOOL_1"] = "1"
        os.environ["TEST_BOOL_0"] = "0"
        os.environ["TEST_BOOL_ENABLED"] = "enabled"
        os.environ["TEST_BOOL_DISABLED"] = "disabled"
        
        # Numeric edge cases
        os.environ["TEST_NEGATIVE_INT"] = "-123"
        os.environ["TEST_NEGATIVE_FLOAT"] = "-45.67"
        
        # URL patterns
        os.environ["TEST_HTTP_URL"] = "https://example.com/api"
        os.environ["TEST_DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
        os.environ["TEST_REDIS_URL"] = "redis://localhost:6379"
        
        # Empty and whitespace
        os.environ["TEST_EMPTY"] = ""
        os.environ["TEST_WHITESPACE"] = "   "
        
        # Multiple prefixes test
        os.environ["APP_KEY"] = "app_value"
        os.environ["API_KEY"] = "api_value"
        os.environ["DB_KEY"] = "db_value"
        
        # Case sensitivity tests
        os.environ["test_lower"] = "lower_value"
        os.environ["TEST_UPPER"] = "upper_value"
    
    def tearDown(self):
        """Clean up test environment variables."""
        env_vars_to_remove = [
            "TEST_SIMPLE", "TEST_INT", "TEST_FLOAT", "TEST_BOOL_TRUE", "TEST_BOOL_FALSE",
            "TEST_LIST", "TEST_DATABASE_HOST", "TEST_DATABASE_PORT",
            "TEST_DATABASE_CREDENTIALS_USERNAME", "TEST_DATABASE_CREDENTIALS_PASSWORD",
            "TEST_BOOL_YES", "TEST_BOOL_NO", "TEST_BOOL_ON", "TEST_BOOL_OFF",
            "TEST_BOOL_1", "TEST_BOOL_0", "TEST_BOOL_ENABLED", "TEST_BOOL_DISABLED",
            "TEST_NEGATIVE_INT", "TEST_NEGATIVE_FLOAT",
            "TEST_HTTP_URL", "TEST_DATABASE_URL", "TEST_REDIS_URL",
            "TEST_EMPTY", "TEST_WHITESPACE",
            "APP_KEY", "API_KEY", "DB_KEY",
            "test_lower", "TEST_UPPER"
        ]
        for var in env_vars_to_remove:
            if var in os.environ:
                del os.environ[var]
    
    def test_basic_loading_with_prefix(self):
        """Test basic loading with prefix stripping."""
        source = EnvironmentSource(prefix="TEST_", nested=False)
        config = source.load()
        
        # Keys are now normalized to lowercase
        self.assertEqual(config["simple"], "simple_value")
        self.assertIn("int", config)
        self.assertNotIn("app_key", config)  # Different prefix
    
    def test_nested_structure_creation(self):
        """Test nested structure creation from underscores."""
        source = EnvironmentSource(prefix="TEST_", nested=True)
        config = source.load()
        
        # Check nested database structure
        self.assertIn("database", config)
        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["database"]["port"], 5432)  # Should be parsed as int
        
        # Check deeply nested credentials
        self.assertIn("credentials", config["database"])
        self.assertEqual(config["database"]["credentials"]["username"], "admin")
        self.assertEqual(config["database"]["credentials"]["password"], "secret")
    
    def test_type_parsing_boolean(self):
        """Test boolean value parsing."""
        source = EnvironmentSource(prefix="TEST_", nested=False, parse_values=True)
        config = source.load()
        
        # Test various boolean representations
        self.assertTrue(config["bool_true"])
        self.assertFalse(config["bool_false"])
        self.assertTrue(config["bool_yes"])
        self.assertFalse(config["bool_no"])
        self.assertTrue(config["bool_on"])
        self.assertFalse(config["bool_off"])
        self.assertTrue(config["bool_1"])
        self.assertFalse(config["bool_0"])
        self.assertTrue(config["bool_enabled"])
        self.assertFalse(config["bool_disabled"])
    
    def test_type_parsing_numeric(self):
        """Test numeric value parsing."""
        source = EnvironmentSource(prefix="TEST_", nested=False, parse_values=True)
        config = source.load()
        
        # Integers
        self.assertEqual(config["int"], 42)
        self.assertIsInstance(config["int"], int)
        
        # Floats
        self.assertEqual(config["float"], 3.14)
        self.assertIsInstance(config["float"], float)
        
        # Negative numbers
        self.assertEqual(config["negative_int"], -123)
        self.assertEqual(config["negative_float"], -45.67)
    
    def test_type_parsing_lists(self):
        """Test list parsing from comma-separated values."""
        source = EnvironmentSource(prefix="TEST_", nested=False, parse_values=True)
        config = source.load()
        
        self.assertEqual(config["list"], ["item1", "item2", "item3"])
        self.assertIsInstance(config["list"], list)
    
    def test_url_preservation(self):
        """Test that URLs are preserved as strings."""
        source = EnvironmentSource(prefix="TEST_", nested=False, parse_values=True)
        config = source.load()
        
        self.assertEqual(config["http_url"], "https://example.com/api")
        self.assertEqual(config["database_url"], "postgresql://user:pass@localhost:5432/db")
        self.assertEqual(config["redis_url"], "redis://localhost:6379")
        self.assertIsInstance(config["http_url"], str)
    
    def test_parse_values_disabled(self):
        """Test with parse_values=False."""
        source = EnvironmentSource(prefix="TEST_", nested=False, parse_values=False)
        config = source.load()
        
        # Everything should be strings
        self.assertEqual(config["int"], "42")
        self.assertEqual(config["bool_true"], "true")
        self.assertIsInstance(config["int"], str)
    
    def test_strip_prefix_disabled(self):
        """Test with strip_prefix=False."""
        source = EnvironmentSource(prefix="TEST_", nested=False, strip_prefix=False)
        config = source.load()
        
        # Keys should include prefix (normalized to lowercase)
        self.assertIn("test_simple", config)
        self.assertNotIn("simple", config)
    
    def test_multiple_prefixes(self):
        """Test loading from multiple prefixes."""
        source = EnvironmentSource(prefixes=["APP_", "API_", "DB_"], nested=False)
        config = source.load()
        
        self.assertEqual(config["key"], "db_value")  # Last match wins
        self.assertIn("key", config)
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive prefix matching."""
        source = EnvironmentSource(prefix="test_", nested=False, case_sensitive=False)
        config = source.load()
        
        # Should match both test_ and TEST_
        # Keys are stripped of prefix and normalized to lowercase
        self.assertIn("lower", config)
        self.assertIn("upper", config)
    
    def test_case_sensitive_matching(self):
        """Test case-sensitive prefix matching (default)."""
        # On Windows, environment variable names are case-insensitive at OS level
        # Both test_lower and TEST_UPPER can match depending on OS behavior
        # With case_sensitive=True and prefix TEST_, this tests the prefix matching
        source = EnvironmentSource(prefix="TEST_", nested=False, case_sensitive=True)
        config = source.load()
        
        # Should match TEST_UPPER since prefix is TEST_ (key normalized to lowercase)
        self.assertIn("upper", config)
        # On Windows, both test_lower and TEST_UPPER might be present due to OS case-insensitivity
        # so we just verify that case-sensitive prefix matching works for the expected variable
    
    def test_no_prefix_loads_all(self):
        """Test that no prefixes configured loads all environment variables."""
        source = EnvironmentSource(prefixes=[], nested=False)
        config = source.load()
        
        # Should contain test variables and system variables (keys normalized to lowercase)
        self.assertIn("test_simple", config)
        self.assertGreater(len(config), 10)  # Should have many env vars
    
    def test_empty_and_whitespace_values(self):
        """Test handling of empty and whitespace values."""
        source = EnvironmentSource(prefix="TEST_", nested=False)
        config = source.load()
        
        self.assertEqual(config["empty"], "")
        self.assertEqual(config["whitespace"], "")  # Should be stripped
    
    def test_custom_list_separator(self):
        """Test custom list separator."""
        os.environ["TEST_PIPE_LIST"] = "a|b|c"
        source = EnvironmentSource(prefix="TEST_", nested=False, list_separator="|")
        config = source.load()
        
        self.assertEqual(config["pipe_list"], ["a", "b", "c"])
        del os.environ["TEST_PIPE_LIST"]
    
    def test_is_available(self):
        """Test is_available method."""
        source = EnvironmentSource(prefix="TEST_")
        self.assertTrue(source.is_available())
    
    def test_get_matched_variables(self):
        """Test get_matched_variables method."""
        source = EnvironmentSource(prefix="TEST_")
        matched = source.get_matched_variables()
        
        # get_matched_variables returns original env var names (not normalized)
        self.assertIn("TEST_SIMPLE", matched)
        self.assertIn("TEST_INT", matched)
        self.assertNotIn("APP_KEY", matched)
    
    def test_get_prefix_info(self):
        """Test get_prefix_info method."""
        source = EnvironmentSource(prefix="TEST_", nested=True, parse_values=True)
        info = source.get_prefix_info()
        
        self.assertEqual(info["prefixes"], ["TEST_"])
        self.assertTrue(info["nested"])
        self.assertTrue(info["parse_values"])
        self.assertTrue(info["case_sensitive"])
    
    def test_validate_environment(self):
        """Test validate_environment method."""
        source = EnvironmentSource(prefix="TEST_")
        validation = source.validate_environment()
        
        self.assertGreater(validation["total_env_vars"], 0)
        self.assertGreater(validation["matched_vars"], 0)
        self.assertTrue(validation["configuration_valid"])
        # validate_environment returns original env var names (not normalized)
        self.assertIn("TEST_SIMPLE", validation["matched_variables"])
    
    def test_nested_with_single_part_key(self):
        """Test nested mode with keys that have no underscores."""
        os.environ["TEST_SINGLE"] = "value"
        source = EnvironmentSource(prefix="TEST_", nested=True)
        config = source.load()
        
        # Single part key should not be nested (normalized to lowercase)
        self.assertIn("single", config)
        del os.environ["TEST_SINGLE"]
    
    def test_metadata_tracking(self):
        """Test that source metadata is tracked."""
        source = EnvironmentSource(prefix="TEST_")
        config = source.load()
        
        metadata = source.get_metadata()
        self.assertEqual(metadata.source_type, "environment")
        self.assertIsNotNone(metadata.last_loaded)
        self.assertGreater(metadata.load_count, 0)


if __name__ == '__main__':
    unittest.main()


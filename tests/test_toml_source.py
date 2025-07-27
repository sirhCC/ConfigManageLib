"""Tests for the TOML source."""

import unittest
import tempfile
import os
from config_manager.sources.toml_source import TomlSource


class TestTomlSource(unittest.TestCase):
    """Test the TomlSource class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for filename in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, filename))
        os.rmdir(self.temp_dir)
    
    def test_toml_source_load(self):
        """Test that TOML source loads configuration correctly."""
        toml_file = os.path.join(self.temp_dir, "config.toml")
        toml_content = '''
# Application configuration
app_name = "MyApp"
version = "1.2.3"
debug = true
port = 8080
timeout = 30.5

# Features list
features = ["auth", "api", "logging"]

# Database configuration
[database]
host = "localhost"
port = 5432
name = "mydb"
ssl = false

# Nested configuration
[server.ssl]
enabled = true
cert_file = "/path/to/cert.pem"
key_file = "/path/to/key.pem"
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        config = source.load()
        
        # Test basic values
        self.assertEqual(config["app_name"], "MyApp")
        self.assertEqual(config["version"], "1.2.3")
        self.assertTrue(config["debug"])
        self.assertEqual(config["port"], 8080)
        self.assertEqual(config["timeout"], 30.5)
        
        # Test section
        self.assertIn("database", config)
        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["database"]["port"], 5432)
        self.assertEqual(config["database"]["name"], "mydb")
        self.assertFalse(config["database"]["ssl"])
        
        # Test array
        self.assertEqual(config["features"], ["auth", "api", "logging"])
        
        # Test nested section
        self.assertIn("server", config)
        self.assertIn("ssl", config["server"])
        self.assertTrue(config["server"]["ssl"]["enabled"])
        self.assertEqual(config["server"]["ssl"]["cert_file"], "/path/to/cert.pem")
        self.assertEqual(config["server"]["ssl"]["key_file"], "/path/to/key.pem")
    
    def test_toml_source_missing_file(self):
        """Test that TOML source handles missing files gracefully."""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.toml")
        source = TomlSource(non_existent_file)
        
        with self.assertRaises(FileNotFoundError):
            source.load()
    
    def test_toml_source_empty_file(self):
        """Test that TOML source handles empty files gracefully."""
        empty_file = os.path.join(self.temp_dir, "empty.toml")
        
        with open(empty_file, 'w') as f:
            f.write("")  # Empty file
        
        source = TomlSource(empty_file)
        config = source.load()
        
        self.assertEqual(config, {})
    
    def test_toml_source_comments_and_whitespace(self):
        """Test that TOML source handles comments and whitespace correctly."""
        toml_file = os.path.join(self.temp_dir, "config_with_comments.toml")
        toml_content = '''
# This is a comment
# Another comment

app_name = "TestApp"  # Inline comment

# Empty lines above and below

debug = false

[section]
# Comment in section
key = "value"
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        config = source.load()
        
        self.assertEqual(config["app_name"], "TestApp")
        self.assertFalse(config["debug"])
        self.assertEqual(config["section"]["key"], "value")
    
    def test_toml_source_data_types(self):
        """Test that TOML source handles different data types correctly."""
        toml_file = os.path.join(self.temp_dir, "types.toml")
        toml_content = '''
# String values
name = "John Doe"
description = 'Single quotes work too'

# Numeric values
age = 30
height = 5.9
negative = -42
float_val = 3.14159

# Boolean values
active = true
disabled = false

# Arrays
tags = ["python", "config", "toml"]
numbers = [1, 2, 3, 4, 5]
mixed = ["string", 42, true]
empty_array = []
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        config = source.load()
        
        # Test strings
        self.assertEqual(config["name"], "John Doe")
        self.assertEqual(config["description"], "Single quotes work too")
        
        # Test numbers
        self.assertEqual(config["age"], 30)
        self.assertEqual(config["height"], 5.9)
        self.assertEqual(config["negative"], -42)
        self.assertEqual(config["float_val"], 3.14159)
        
        # Test booleans
        self.assertTrue(config["active"])
        self.assertFalse(config["disabled"])
        
        # Test arrays
        self.assertEqual(config["tags"], ["python", "config", "toml"])
        self.assertEqual(config["numbers"], [1, 2, 3, 4, 5])
        self.assertEqual(config["mixed"], ["string", 42, True])
        self.assertEqual(config["empty_array"], [])
    
    def test_toml_source_nested_sections(self):
        """Test that TOML source handles nested sections correctly."""
        toml_file = os.path.join(self.temp_dir, "nested.toml")
        toml_content = '''
[app]
name = "MyApp"
version = "1.0.0"

[app.database]
host = "localhost"
port = 5432

[app.database.credentials]
username = "admin"
password = "secret"

[logging]
level = "INFO"

[logging.handlers]
console = true
file = false
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        config = source.load()
        
        # Test nested access
        self.assertEqual(config["app"]["name"], "MyApp")
        self.assertEqual(config["app"]["database"]["host"], "localhost")
        self.assertEqual(config["app"]["database"]["port"], 5432)
        self.assertEqual(config["app"]["database"]["credentials"]["username"], "admin")
        self.assertEqual(config["app"]["database"]["credentials"]["password"], "secret")
        
        self.assertEqual(config["logging"]["level"], "INFO")
        self.assertTrue(config["logging"]["handlers"]["console"])
        self.assertFalse(config["logging"]["handlers"]["file"])
    
    def test_toml_source_invalid_syntax(self):
        """Test that TOML source handles invalid syntax gracefully."""
        toml_file = os.path.join(self.temp_dir, "invalid.toml")
        toml_content = '''
app_name = "MyApp"
invalid line without equals
port = 8080
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        
        with self.assertRaises(ValueError) as cm:
            source.load()
        
        self.assertIn("Invalid TOML syntax", str(cm.exception))
    
    def test_toml_source_string_representation(self):
        """Test the string representation of TomlSource."""
        toml_file = os.path.join(self.temp_dir, "test.toml")
        
        # Create empty file
        with open(toml_file, 'w') as f:
            f.write("")
        
        source = TomlSource(toml_file)
        
        str_repr = str(source)
        self.assertIn("TomlSource", str_repr)
        self.assertIn(toml_file, str_repr)
        self.assertIn("parser=", str_repr)
        
        # repr should be the same as str
        self.assertEqual(str(source), repr(source))
    
    def test_toml_source_with_config_manager(self):
        """Test TOML source integration with ConfigManager."""
        from config_manager import ConfigManager
        
        toml_file = os.path.join(self.temp_dir, "app_config.toml")
        toml_content = '''
app_name = "IntegrationTest"
debug = true
port = 9000

[database]
host = "db.example.com"
port = 5432
name = "testdb"

[features]
auth = true
api = true
logging = false
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        config = ConfigManager()
        config.add_source(TomlSource(toml_file))
        
        # Test basic access
        self.assertEqual(config.get("app_name"), "IntegrationTest")
        self.assertTrue(config.get_bool("debug"))
        self.assertEqual(config.get_int("port"), 9000)
        
        # Test nested access
        self.assertEqual(config.get("database.host"), "db.example.com")
        self.assertEqual(config.get_int("database.port"), 5432)
        self.assertEqual(config.get("database.name"), "testdb")
        
        self.assertTrue(config.get_bool("features.auth"))
        self.assertTrue(config.get_bool("features.api"))
        self.assertFalse(config.get_bool("features.logging"))
    
    def test_toml_source_fallback_parser(self):
        """Test the simple fallback TOML parser."""
        toml_file = os.path.join(self.temp_dir, "simple.toml")
        toml_content = '''
# Simple TOML file for fallback parser testing
name = "FallbackTest"
count = 42
ratio = 3.14
enabled = true
disabled = false
items = ["one", "two", "three"]

[section]
key = "value"
number = 123
'''
        
        with open(toml_file, 'w') as f:
            f.write(toml_content)
        
        source = TomlSource(toml_file)
        
        # Force use of simple parser for testing
        source._toml_parser = ("simple", None)
        
        config = source.load()
        
        # Test that simple parser works
        self.assertEqual(config["name"], "FallbackTest")
        self.assertEqual(config["count"], 42)
        self.assertEqual(config["ratio"], 3.14)
        self.assertTrue(config["enabled"])
        self.assertFalse(config["disabled"])
        self.assertEqual(config["items"], ["one", "two", "three"])
        self.assertEqual(config["section"]["key"], "value")
        self.assertEqual(config["section"]["number"], 123)


if __name__ == '__main__':
    unittest.main()

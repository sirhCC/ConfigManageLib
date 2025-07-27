"""Tests for ConfigManager schema integration."""

import unittest
import tempfile
import os
import json
from config_manager.config_manager import ConfigManager
from config_manager.schema import Schema, String, Integer, Float, Boolean, ListField
from config_manager.validation import ValidationError, RangeValidator
from config_manager.sources.json_source import JsonSource
from config_manager.sources.environment import EnvironmentSource
from config_manager.sources.base import BaseSource


class MockEnvironmentSource(BaseSource):
    """Mock environment source for testing."""
    
    def __init__(self, data: dict):
        self._data = data
    
    def load(self):
        return self._data


class TestConfigManagerSchema(unittest.TestCase):
    """Test ConfigManager integration with schema validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for filename in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, filename))
        os.rmdir(self.temp_dir)
    
    def test_config_manager_with_schema(self):
        """Test ConfigManager with schema validation."""
        # Create a schema
        schema = Schema({
            "app_name": String(required=True),
            "port": Integer(default=8080, validators=[RangeValidator(min_value=1024, max_value=65535)]),
            "debug": Boolean(default=False)
        })
        
        # Create config file
        config_file = os.path.join(self.temp_dir, "config.json")
        config_data = {
            "app_name": "TestApp",
            "port": 3000
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Create ConfigManager with schema
        config = ConfigManager(schema=schema)
        config.add_source(JsonSource(config_file))
        
        # Test validated configuration
        validated_config = config.validate()
        self.assertEqual(validated_config["app_name"], "TestApp")
        self.assertEqual(validated_config["port"], 3000)
        self.assertEqual(validated_config["debug"], False)  # Default applied
    
    def test_config_manager_validation_error(self):
        """Test ConfigManager with validation error."""
        # Create a schema with strict validation
        schema = Schema({
            "port": Integer(required=True, validators=[RangeValidator(min_value=1024, max_value=65535)])
        })
        
        # Create config file with invalid data
        config_file = os.path.join(self.temp_dir, "config.json")
        config_data = {
            "port": 80  # Invalid: below minimum
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Create ConfigManager with schema
        config = ConfigManager(schema=schema)
        config.add_source(JsonSource(config_file))
        
        # Test validation error
        with self.assertRaises(ValidationError):
            config.validate()
        
        # Test non-raising validation
        result = config.validate(raise_on_error=False)
        self.assertEqual(result["port"], 80)  # Returns original config
    
    def test_config_manager_is_valid(self):
        """Test ConfigManager is_valid method."""
        # Create a schema
        schema = Schema({
            "name": String(required=True),
            "age": Integer(validators=[RangeValidator(min_value=0, max_value=150)])
        })
        
        # Valid config
        config_file = os.path.join(self.temp_dir, "valid_config.json")
        valid_data = {"name": "John", "age": 30}
        with open(config_file, 'w') as f:
            json.dump(valid_data, f)
        
        config = ConfigManager(schema=schema)
        config.add_source(JsonSource(config_file))
        self.assertTrue(config.is_valid())
        
        # Invalid config
        invalid_config_file = os.path.join(self.temp_dir, "invalid_config.json")
        invalid_data = {"age": 200}  # Missing required name, invalid age
        with open(invalid_config_file, 'w') as f:
            json.dump(invalid_data, f)
        
        invalid_config = ConfigManager(schema=schema)
        invalid_config.add_source(JsonSource(invalid_config_file))
        self.assertFalse(invalid_config.is_valid())
    
    def test_config_manager_validation_errors(self):
        """Test ConfigManager get_validation_errors method."""
        # Create a schema
        schema = Schema({
            "name": String(required=True),
            "age": Integer(validators=[RangeValidator(min_value=0, max_value=150)])
        })
        
        # Valid config
        valid_config = ConfigManager(schema=schema)
        valid_config.add_source(MockEnvironmentSource({"name": "John", "age": "30"}))
        errors = valid_config.get_validation_errors()
        self.assertEqual(len(errors), 0)
        
        # Invalid config
        invalid_config = ConfigManager(schema=schema)
        invalid_config.add_source(MockEnvironmentSource({"age": "200"}))  # Missing name, invalid age
        errors = invalid_config.get_validation_errors()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("name" in error for error in errors))
    
    def test_config_manager_set_schema(self):
        """Test ConfigManager set_schema method."""
        config = ConfigManager()
        
        # Initially no schema
        self.assertTrue(config.is_valid())  # Should be True without schema
        
        # Set schema
        schema = Schema({
            "required_field": String(required=True)
        })
        config.set_schema(schema)
        
        # Now should fail validation (no required field)
        self.assertFalse(config.is_valid())
        
        # Add valid data
        config.add_source(MockEnvironmentSource({"required_field": "value"}))
        self.assertTrue(config.is_valid())
    
    def test_config_manager_schema_with_type_conversion(self):
        """Test ConfigManager schema with type conversion."""
        schema = Schema({
            "port": Integer(),
            "timeout": Float(),
            "debug": Boolean(),
            "features": ListField()
        })
        
        # Config with string values that need conversion
        config = ConfigManager(schema=schema)
        config.add_source(MockEnvironmentSource({
            "port": "8080",
            "timeout": "30.5",
            "debug": "true",
            "features": "feature1,feature2,feature3"
        }))
        
        validated = config.validate()
        self.assertEqual(validated["port"], 8080)
        self.assertEqual(validated["timeout"], 30.5)
        self.assertEqual(validated["debug"], True)
        self.assertEqual(validated["features"], ["feature1", "feature2", "feature3"])
    
    def test_config_manager_nested_schema(self):
        """Test ConfigManager with nested schema."""
        database_schema = Schema({
            "host": String(default="localhost"),
            "port": Integer(default=5432),
            "name": String(required=True)
        })
        
        app_schema = Schema({
            "app_name": String(required=True),
            "database": database_schema
        })
        
        config_file = os.path.join(self.temp_dir, "nested_config.json")
        config_data = {
            "app_name": "MyApp",
            "database": {
                "name": "mydb",
                "port": 3306
            }
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = ConfigManager(schema=app_schema)
        config.add_source(JsonSource(config_file))
        
        validated = config.validate()
        self.assertEqual(validated["app_name"], "MyApp")
        self.assertEqual(validated["database"]["host"], "localhost")  # Default
        self.assertEqual(validated["database"]["port"], 3306)
        self.assertEqual(validated["database"]["name"], "mydb")
    
    def test_config_manager_validation_cache(self):
        """Test that validation results are cached."""
        schema = Schema({
            "name": String(required=True)
        })
        
        config = ConfigManager(schema=schema)
        config.add_source(MockEnvironmentSource({"name": "test"}))
        
        # First validation
        result1 = config.validate()
        
        # Second validation should return the same cached result
        result2 = config.validate()
        self.assertIs(result1, result2)  # Should be the same object
        
        # After adding a new source, cache should be invalidated
        config.add_source(MockEnvironmentSource({"extra": "value"}))
        result3 = config.validate()
        self.assertIsNot(result1, result3)  # Should be different objects
    
    def test_config_manager_reload_invalidates_cache(self):
        """Test that reload invalidates validation cache."""
        schema = Schema({
            "name": String(required=True)
        })
        
        config_file = os.path.join(self.temp_dir, "reload_config.json")
        config_data = {"name": "original"}
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = ConfigManager(schema=schema)
        config.add_source(JsonSource(config_file))
        
        # First validation
        result1 = config.validate()
        self.assertEqual(result1["name"], "original")
        
        # Modify config file
        config_data["name"] = "modified"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Reload should invalidate cache
        config.reload()
        result2 = config.validate()
        self.assertEqual(result2["name"], "modified")
        self.assertIsNot(result1, result2)


if __name__ == '__main__':
    unittest.main()

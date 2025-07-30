"""
Modern pytest-based tests for ConfigManager core functionality.

This module demonstrates the new pytest testing approach with fixtures,
parametrized tests, and modern Python testing patterns.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from config_manager import ConfigManager
from config_manager.sources.json_source import JsonSource
from config_manager.sources.environment import EnvironmentSource
from config_manager.validation import ValidationError
from tests.conftest import (
    sample_config_data,
    nested_config_data,
    create_temp_json_file,
    setup_test_environment_vars,
    cleanup_test_environment_vars,
    create_config_manager,
    create_json_config_manager,
    create_env_config_manager,
    BaseConfigManagerTest
)


class TestConfigManagerCore(BaseConfigManagerTest):
    """Core ConfigManager functionality tests using pytest patterns."""
    
    def test_empty_config_manager(self):
        """Test that empty ConfigManager returns None/defaults for missing keys."""
        config = create_config_manager()
        
        assert config.get('missing_key') is None
        assert config.get('missing_key', 'default') == 'default'
        assert config.get_int('missing_int', 42) == 42
        assert config.get_bool('missing_bool', True) is True
        assert config.get_list('missing_list', ['default']) == ['default']
    
    def test_config_manager_with_json_source(self):
        """Test ConfigManager with JSON source integration."""
        # Create test data and temp file
        test_data = sample_config_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_path = f.name
        
        try:
            # Create ConfigManager with JSON source
            config = create_json_config_manager(temp_path)
            
            # Test basic value retrieval
            assert config.get('app_name') == 'TestApp'
            assert config.get('version') == '1.0.0'
            assert config.get_bool('debug') is True
            assert config.get_int('port') == 8080
            
            # Test nested value retrieval
            assert config.get('database.host') == 'localhost'
            assert config.get_int('database.port') == 5432
            assert config.get('database.name') == 'testdb'
            assert config.get_bool('database.ssl_enabled') is True
            
            # Test deeply nested values
            assert config.get('database.credentials.username') == 'testuser'
            assert config.get('database.credentials.password') == 'testpass'
            
            # Test list handling
            features = config.get_list('features')
            assert features == ['auth', 'api', 'logging']
            
        finally:
            # Cleanup
            os.unlink(temp_path)
    
    def test_config_manager_with_environment_source(self):
        """Test ConfigManager with environment variable source."""
        # Setup environment variables
        env_vars = setup_test_environment_vars()
        
        try:
            # Create ConfigManager with environment source
            config = create_env_config_manager()
            
            # Test basic value retrieval
            assert config.get('app_name') == 'TestApp'
            assert config.get_bool('debug') is True
            assert config.get_int('port') == 8080
            
            # Test nested value retrieval (using underscore notation)
            assert config.get('database_host') == 'localhost'
            assert config.get_int('database_port') == 5432
            
            # Test type conversions
            assert config.get_int('int_value') == 42
            assert config.get_float('float_value') == 3.14
            assert config.get_bool('bool_true') is True
            assert config.get_bool('bool_false') is False
            
            # Test list parsing
            features = config.get_list('features')
            assert features == ['auth', 'api', 'logging']
            
            # Test empty string handling
            assert config.get('empty') == ''
            
        finally:
            cleanup_test_environment_vars()
    
    def test_source_priority_override(self):
        """Test that later sources override earlier ones."""
        # Create JSON test data
        json_data = {
            "app_name": "JSONApp",
            "port": 3000,
            "json_only": "json_value"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f, indent=2)
            temp_json_path = f.name
        
        # Setup environment variables with some overlapping keys
        env_vars = {
            "TEST_PREFIX_APP_NAME": "EnvApp",
            "TEST_PREFIX_PORT": "8080",
            "TEST_PREFIX_ENV_ONLY": "env_value"
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            # Create ConfigManager with both sources
            config = ConfigManager()
            config.add_source(JsonSource(temp_json_path))  # Lower priority
            config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))  # Higher priority
            
            # Environment should override JSON for overlapping keys
            assert config.get('app_name') == 'EnvApp'  # From environment
            assert config.get_int('port') == 8080  # From environment
            
            # Unique keys should still work
            assert config.get('json_only') == 'json_value'  # From JSON
            assert config.get('env_only') == 'env_value'  # From environment
            
        finally:
            # Cleanup
            os.unlink(temp_json_path)
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]


@pytest.mark.parametrize("key,expected_value,value_type", [
    ('app_name', 'TestApp', str),
    ('version', '1.0.0', str),
    ('debug', True, bool),
    ('port', 8080, int),
    ('database.host', 'localhost', str),
    ('database.port', 5432, int),
    ('database.ssl_enabled', True, bool),
    ('numeric_values.int_value', 42, int),
    ('numeric_values.float_value', 3.14, float),
    ('numeric_values.negative_int', -10, int),
    ('numeric_values.zero_value', 0, int),
])
def test_config_value_types(key: str, expected_value: Any, value_type: type):
    """Parametrized test for different config value types."""
    test_data = sample_config_data()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        temp_path = f.name
    
    try:
        config = create_json_config_manager(temp_path)
        
        # Get the value and check type
        value = config.get(key)
        assert value == expected_value
        assert isinstance(value, value_type)
        
        # Test appropriate getter method
        if value_type == int:
            assert config.get_int(key) == expected_value
        elif value_type == float:
            assert config.get_float(key) == expected_value
        elif value_type == bool:
            assert config.get_bool(key) == expected_value
        elif value_type == str:
            assert config.get(key) == expected_value
        
    finally:
        os.unlink(temp_path)


@pytest.mark.parametrize("missing_key,default_value", [
    ('missing_string', 'default_string'),
    ('missing_int', 42),
    ('missing_float', 3.14),
    ('missing_bool', True),
    ('missing_list', ['default', 'list']),
    ('deeply.nested.missing.key', 'deep_default'),
])
def test_config_defaults(missing_key: str, default_value: Any):
    """Parametrized test for default value handling."""
    config = create_config_manager()
    
    # Test that missing keys return defaults
    assert config.get(missing_key, default_value) == default_value
    
    # Test type-specific getters with defaults
    if isinstance(default_value, int):
        assert config.get_int(missing_key, default_value) == default_value
    elif isinstance(default_value, float):
        assert config.get_float(missing_key, default_value) == default_value
    elif isinstance(default_value, bool):
        assert config.get_bool(missing_key, default_value) == default_value
    elif isinstance(default_value, list):
        assert config.get_list(missing_key, default_value) == default_value


class TestConfigManagerErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_file(self):
        """Test handling of invalid JSON files."""
        # Create invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json, content}')
            temp_path = f.name
        
        try:
            config = ConfigManager()
            
            # Should raise an exception when trying to add invalid JSON source
            with pytest.raises(Exception):  # Could be JSONDecodeError or similar
                config.add_source(JsonSource(temp_path))
                
        finally:
            os.unlink(temp_path)
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        config = ConfigManager()
        
        # Should raise an exception for nonexistent file
        with pytest.raises(FileNotFoundError):
            config.add_source(JsonSource('/nonexistent/path/config.json'))
    
    def test_type_conversion_errors(self):
        """Test type conversion error handling."""
        test_data = {
            "string_value": "not_a_number",
            "invalid_bool": "maybe",
            "invalid_list": {"not": "a_list"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_path = f.name
        
        try:
            config = create_json_config_manager(temp_path)
            
            # Should handle conversion errors gracefully
            # (Implementation may vary - might return None, raise, or use defaults)
            with pytest.raises((ValueError, TypeError)) or pytest.warns():
                config.get_int('string_value')
            
        finally:
            os.unlink(temp_path)


class TestConfigManagerDeepNesting:
    """Test deeply nested configuration access."""
    
    def test_deep_nested_access(self):
        """Test accessing deeply nested configuration values."""
        test_data = nested_config_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_path = f.name
        
        try:
            config = create_json_config_manager(temp_path)
            
            # Test deep nested access
            assert config.get('level1.level2.level3.level4.deep_value') == 'found_me'
            
            # Test nested list access
            deep_list = config.get_list('level1.level2.level3.level4.deep_list')
            assert deep_list == [1, 2, 3, 4, 5]
            
            # Test nested dict access
            assert config.get('level1.level2.level3.level4.deep_dict.a') == 'alpha'
            assert config.get('level1.level2.level3.level4.deep_dict.b') == 'beta'
            assert config.get('level1.level2.level3.level4.deep_dict.c') == 'gamma'
            
        finally:
            os.unlink(temp_path)
    
    def test_partial_nested_path(self):
        """Test accessing partial nested paths."""
        test_data = nested_config_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_path = f.name
        
        try:
            config = create_json_config_manager(temp_path)
            
            # Should be able to get intermediate nested objects
            level3_data = config.get('level1.level2.level3')
            assert isinstance(level3_data, dict)
            assert 'level4' in level3_data
            
            # Should be able to get the deep dict directly
            deep_dict = config.get('level1.level2.level3.level4.deep_dict')
            assert deep_dict == {"a": "alpha", "b": "beta", "c": "gamma"}
            
        finally:
            os.unlink(temp_path)


class TestConfigManagerListHandling:
    """Test list value handling and parsing."""
    
    def test_list_from_json(self):
        """Test list handling from JSON source."""
        test_data = sample_config_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_path = f.name
        
        try:
            config = create_json_config_manager(temp_path)
            
            # Test direct list access
            features = config.get_list('features')
            assert features == ['auth', 'api', 'logging']
            assert isinstance(features, list)
            
            # Test comma-separated string conversion to list
            string_list = config.get_list('string_list')
            assert string_list == ['item1', 'item2', 'item3']
            
        finally:
            os.unlink(temp_path)
    
    def test_list_from_environment(self):
        """Test list parsing from environment variables."""
        os.environ['TEST_PREFIX_LIST_VAR'] = 'item1,item2,item3'
        os.environ['TEST_PREFIX_SINGLE_ITEM'] = 'single'
        os.environ['TEST_PREFIX_EMPTY_LIST'] = ''
        
        try:
            config = ConfigManager()
            config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))
            
            # Test comma-separated list parsing
            list_var = config.get_list('list_var')
            assert list_var == ['item1', 'item2', 'item3']
            
            # Test single item as list
            single_item = config.get_list('single_item')
            assert single_item == ['single']
            
            # Test empty list handling
            empty_list = config.get_list('empty_list', [])
            assert empty_list == []
            
        finally:
            # Cleanup
            for key in ['TEST_PREFIX_LIST_VAR', 'TEST_PREFIX_SINGLE_ITEM', 'TEST_PREFIX_EMPTY_LIST']:
                if key in os.environ:
                    del os.environ[key]


# Performance and stress tests
@pytest.mark.performance
class TestConfigManagerPerformance:
    """Performance tests for ConfigManager (marked as slow)."""
    
    @pytest.mark.slow
    def test_large_config_performance(self):
        """Test performance with large configuration data."""
        # Create large test data
        large_data = {
            f"section_{i}": {
                f"key_{j}": f"value_{i}_{j}"
                for j in range(100)
            }
            for i in range(100)
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(large_data, f, indent=2)
            temp_path = f.name
        
        try:
            config = create_json_config_manager(temp_path)
            
            # Test that we can access values efficiently
            import time
            start_time = time.time()
            
            # Access multiple values
            for i in range(0, 100, 10):
                for j in range(0, 100, 10):
                    value = config.get(f'section_{i}.key_{j}')
                    assert value == f'value_{i}_{j}'
            
            end_time = time.time()
            access_time = end_time - start_time
            
            # Should be reasonably fast (adjust threshold as needed)
            assert access_time < 1.0, f"Config access took too long: {access_time:.2f}s"
            
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v'])

"""
Pytest configuration and shared fixtures for ConfigManager tests.

This file contains common fixtures, test utilities, and pytest configuration
that can be used across all test modules.
"""

import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from unittest.mock import MagicMock

from config_manager import ConfigManager
from config_manager.sources.json_source import JsonSource
from config_manager.sources.environment import EnvironmentSource

# Test Data Fixtures
def sample_config_data() -> Dict[str, Any]:
    """Sample configuration data for testing."""
    return {
        "app_name": "TestApp",
        "version": "1.0.0",
        "debug": True,
        "port": 8080,
        "features": ["auth", "api", "logging"],
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "testdb",
            "ssl_enabled": True,
            "credentials": {
                "username": "testuser",
                "password": "testpass"
            }
        },
        "cache": {
            "enabled": True,
            "ttl": 300,
            "max_size": 1000
        },
        "numeric_values": {
            "int_value": 42,
            "float_value": 3.14,
            "negative_int": -10,
            "zero_value": 0
        },
        "string_list": "item1,item2,item3",
        "empty_string": "",
        "null_value": None
    }


def nested_config_data() -> Dict[str, Any]:
    """Deeply nested configuration data for testing."""
    return {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "deep_value": "found_me",
                        "deep_list": [1, 2, 3, 4, 5],
                        "deep_dict": {
                            "a": "alpha",
                            "b": "beta",
                            "c": "gamma"
                        }
                    }
                }
            }
        }
    }


# File Fixtures
def create_temp_json_file(config_data: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
    """Create a temporary JSON configuration file."""
    if config_data is None:
        config_data = sample_config_data()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


def create_temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


# Environment Variable Helpers
def setup_test_environment_vars() -> Dict[str, str]:
    """Set up test environment variables."""
    test_vars = {
        "TEST_PREFIX_APP_NAME": "TestApp",
        "TEST_PREFIX_DEBUG": "true",
        "TEST_PREFIX_PORT": "8080",
        "TEST_PREFIX_DATABASE_HOST": "localhost",
        "TEST_PREFIX_DATABASE_PORT": "5432",
        "TEST_PREFIX_FEATURES": "auth,api,logging",
        "TEST_PREFIX_INT_VALUE": "42",
        "TEST_PREFIX_FLOAT_VALUE": "3.14",
        "TEST_PREFIX_BOOL_TRUE": "yes",
        "TEST_PREFIX_BOOL_FALSE": "no",
        "TEST_PREFIX_EMPTY": "",
    }
    
    for key, value in test_vars.items():
        os.environ[key] = value
    
    return test_vars


def cleanup_test_environment_vars():
    """Clean up test environment variables."""
    test_vars = [key for key in os.environ.keys() if key.startswith('TEST_')]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


# ConfigManager Factory Functions
def create_config_manager() -> ConfigManager:
    """Create a fresh ConfigManager instance."""
    return ConfigManager()


def create_json_config_manager(temp_json_file: str) -> ConfigManager:
    """ConfigManager with JSON source loaded."""
    config = ConfigManager()
    config.add_source(JsonSource(temp_json_file))
    return config


def create_env_config_manager() -> ConfigManager:
    """ConfigManager with environment source loaded."""
    config = ConfigManager()
    config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))
    return config


def create_multi_source_config_manager(temp_json_file: str) -> ConfigManager:
    """ConfigManager with multiple sources for priority testing."""
    config = ConfigManager()
    # Add sources in priority order (last added = highest priority)
    config.add_source(JsonSource(temp_json_file))  # Lowest priority
    config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))  # Highest priority
    return config


# Mock Helpers
def create_mock_cache() -> MagicMock:
    """Create a mock cache for testing."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = None
    mock.delete.return_value = None
    mock.clear.return_value = None
    mock.stats.return_value = {"hits": 0, "misses": 0, "size": 0}
    return mock


# Performance Testing Data
def create_performance_config_data() -> Dict[str, Any]:
    """Large configuration data for performance testing."""
    base_data = {
        f"key_{i}": {
            "nested_value": f"value_{i}",
            "list_data": list(range(10)),
            "metadata": {
                "created": f"2024-01-{i:02d}",
                "updated": f"2024-02-{i:02d}",
                "version": f"1.{i}.0"
            }
        }
        for i in range(1000)
    }
    
    return {
        "app_config": base_data,
        "global_settings": {
            "timeout": 30,
            "retries": 3,
            "batch_size": 100
        }
    }


# Test Base Classes for easy inheritance
class BaseConfigManagerTest:
    """Base test class with common setup and teardown."""
    
    def setup_method(self):
        """Set up test method."""
        self.config = ConfigManager()
        self.original_env = os.environ.copy()
        cleanup_test_environment_vars()
    
    def teardown_method(self):
        """Clean up after test method."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clear any global cache
        try:
            from config_manager.cache import clear_global_cache
            clear_global_cache()
        except ImportError:
            pass


class BaseIntegrationTest(BaseConfigManagerTest):
    """Base test class for integration tests."""
    
    def setup_method(self):
        """Set up integration test."""
        super().setup_method()
        self.temp_files = []
    
    def teardown_method(self):
        """Clean up integration test."""
        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass
        
        super().teardown_method()
    
    def create_temp_json(self, data: Optional[Dict[str, Any]] = None) -> str:
        """Create a temporary JSON file for testing."""
        if data is None:
            data = sample_config_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f, indent=2)
            temp_path = f.name
        
        self.temp_files.append(temp_path)
        return temp_path

import unittest
import os
import json
import sys
from pathlib import Path

# Add the parent directory to sys.path to make config_manager importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import ConfigManager
from config_manager.sources.environment import EnvironmentSource
from config_manager.sources.json_source import JsonSource

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        # Create a dummy json file for testing
        self.test_json_path = "test_config.json"
        with open(self.test_json_path, 'w') as f:
            json.dump({
                "JSON_KEY": "json_value",
                "INT_VALUE": 42,
                "FLOAT_VALUE": 3.14,
                "BOOL_VALUE": True,
                "STRING_LIST": "item1,item2,item3",
                "NESTED": {
                    "INNER_KEY": "inner_value",
                    "DEEPER": {
                        "DEEPEST_KEY": "deepest_value"
                    }
                }
            }, f)

        # Set up environment variables for testing
        os.environ["TEST_PREFIX_ENV_KEY"] = "env_value"
        os.environ["TEST_PREFIX_INT_ENV"] = "123"
        os.environ["TEST_PREFIX_BOOL_ENV"] = "yes"

    def tearDown(self):
        # Clean up the dummy json file and environment variables
        os.remove(self.test_json_path)
        del os.environ["TEST_PREFIX_ENV_KEY"]
        del os.environ["TEST_PREFIX_INT_ENV"]
        del os.environ["TEST_PREFIX_BOOL_ENV"]

    def test_json_source(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        self.assertEqual(config.get("JSON_KEY"), "json_value")

    def test_environment_source(self):
        config = ConfigManager()
        config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))
        self.assertEqual(config.get("ENV_KEY"), "env_value")

    def test_override_with_environment_source(self):
        # Create a json file with a key that will be overridden
        override_json_path = "override_config.json"
        with open(override_json_path, 'w') as f:
            json.dump({"KEY_TO_OVERRIDE": "json_original"}, f)
        
        os.environ["TEST_OVERRIDE_KEY_TO_OVERRIDE"] = "env_override"

        config = ConfigManager()
        config.add_source(JsonSource(override_json_path))
        config.add_source(EnvironmentSource(prefix="TEST_OVERRIDE_"))

        self.assertEqual(config.get("KEY_TO_OVERRIDE"), "env_override")

        # Clean up
        os.remove(override_json_path)
        del os.environ["TEST_OVERRIDE_KEY_TO_OVERRIDE"]

    def test_get_with_default(self):
        config = ConfigManager()
        self.assertEqual(config.get("NON_EXISTENT_KEY", "default_value"), "default_value")

    def test_getitem(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        self.assertEqual(config["JSON_KEY"], "json_value")
        with self.assertRaises(KeyError):
            _ = config["NON_EXISTENT_KEY"]
    
    def test_nested_keys(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        
        # Test nested key access
        self.assertEqual(config.get("NESTED.INNER_KEY"), "inner_value")
        self.assertEqual(config.get("NESTED.DEEPER.DEEPEST_KEY"), "deepest_value")
        
        # Test non-existent nested keys
        self.assertIsNone(config.get("NESTED.NONEXISTENT"))
        self.assertEqual(config.get("NESTED.NONEXISTENT", "default"), "default")
        
        # Test non-existent parent keys
        self.assertIsNone(config.get("NONEXISTENT.CHILD"))
        
        # Test invalid nested paths (trying to navigate through non-dict values)
        self.assertIsNone(config.get("JSON_KEY.INVALID"))
    
    def test_type_conversions(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        
        # Test integer conversion
        self.assertEqual(config.get_int("INT_VALUE"), 42)
        self.assertEqual(config.get_int("JSON_KEY", 99), 99)  # Can't convert string to int, return default
        self.assertEqual(config.get_int("NONEXISTENT", 100), 100)  # Return default for missing keys
        
        # Test float conversion
        self.assertEqual(config.get_float("FLOAT_VALUE"), 3.14)
        self.assertEqual(config.get_float("INT_VALUE"), 42.0)  # Int converts to float
        self.assertEqual(config.get_float("NONEXISTENT", 2.71), 2.71)
        
        # Test boolean conversion
        self.assertTrue(config.get_bool("BOOL_VALUE"))
        self.assertTrue(config.get_bool("NONEXISTENT", True))
        
        # Test from environment variable
        config.add_source(EnvironmentSource(prefix="TEST_PREFIX_"))
        self.assertEqual(config.get_int("INT_ENV"), 123)
        self.assertTrue(config.get_bool("BOOL_ENV"))
    
    def test_list_conversion(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        
        # Test list from comma-separated string
        self.assertEqual(config.get_list("STRING_LIST"), ["item1", "item2", "item3"])
        
        # Test default
        self.assertEqual(config.get_list("NONEXISTENT", ["default"]), ["default"])
        
        # Test scalar value converted to single-item list
        self.assertEqual(config.get_list("INT_VALUE"), [42])
    
    def test_contains(self):
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path))
        
        self.assertTrue("JSON_KEY" in config)
        self.assertTrue("NESTED.INNER_KEY" in config)
        self.assertFalse("NONEXISTENT" in config)
        self.assertFalse("NESTED.NONEXISTENT" in config)
    
    def test_method_chaining(self):
        # Test that add_source returns self for method chaining
        config = ConfigManager()
        result = config.add_source(JsonSource(self.test_json_path))
        self.assertIs(result, config)
        
        # Test actual chaining
        config = ConfigManager()
        config.add_source(JsonSource(self.test_json_path)).add_source(EnvironmentSource(prefix="TEST_PREFIX_"))
        self.assertEqual(config.get("ENV_KEY"), "env_value")
        self.assertEqual(config.get("JSON_KEY"), "json_value")
    
    def test_reload(self):
        # Create an initial JSON config file
        reload_json_path = "reload_config.json"
        with open(reload_json_path, 'w') as f:
            json.dump({"RELOAD_KEY": "initial_value"}, f)
        
        # Load the config
        config = ConfigManager()
        config.add_source(JsonSource(reload_json_path))
        self.assertEqual(config.get("RELOAD_KEY"), "initial_value")
        
        # Update the JSON file
        with open(reload_json_path, 'w') as f:
            json.dump({"RELOAD_KEY": "updated_value"}, f)
        
        # Without reload, the value should be unchanged
        self.assertEqual(config.get("RELOAD_KEY"), "initial_value")
        
        # After reload, the value should be updated
        config.reload()
        self.assertEqual(config.get("RELOAD_KEY"), "updated_value")
        
        # Clean up
        os.remove(reload_json_path)

if __name__ == '__main__':
    unittest.main()

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
            json.dump({"JSON_KEY": "json_value"}, f)

        # Set up environment variables for testing
        os.environ["TEST_PREFIX_ENV_KEY"] = "env_value"

    def tearDown(self):
        # Clean up the dummy json file and environment variables
        os.remove(self.test_json_path)
        del os.environ["TEST_PREFIX_ENV_KEY"]

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

if __name__ == '__main__':
    unittest.main()

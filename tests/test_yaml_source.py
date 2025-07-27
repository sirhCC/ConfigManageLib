import unittest
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to make config_manager importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import YAML with fallback
try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    from simple_yaml import SimpleYaml as yaml
    HAS_PYYAML = False

from config_manager import ConfigManager
from config_manager.sources.yaml_source import YamlSource

class TestYamlSource(unittest.TestCase):

    def setUp(self):
        # Create a test YAML file
        self.test_yaml_path = "test_config.yaml"
        test_config = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "admin",
                    "password": "secret"
                }
            },
            "features": {
                "feature1": True,
                "feature2": False
            },
            "numbers": {
                "int_value": 42,
                "float_value": 3.14
            },
            "simple_list": "item1,item2,item3"  # Use comma-separated string instead of YAML list
        }
        
        with open(self.test_yaml_path, 'w') as f:
            if HAS_PYYAML:
                yaml.dump(test_config, f, default_flow_style=False)
            else:
                f.write(yaml.dump(test_config))

    def tearDown(self):
        # Clean up the test YAML file
        if os.path.exists(self.test_yaml_path):
            os.remove(self.test_yaml_path)

    def test_yaml_source_load(self):
        """Test that YAML source loads configuration correctly."""
        config = ConfigManager()
        config.add_source(YamlSource(self.test_yaml_path))
        
        # Test basic values
        self.assertEqual(config.get("app.name"), "TestApp")
        self.assertEqual(config.get("app.version"), "1.0.0")
        self.assertTrue(config.get_bool("app.debug"))
        
        # Test nested values
        self.assertEqual(config.get("database.host"), "localhost")
        self.assertEqual(config.get_int("database.port"), 5432)
        self.assertEqual(config.get("database.credentials.username"), "admin")
        
        # Test different data types
        self.assertEqual(config.get_int("numbers.int_value"), 42)
        self.assertEqual(config.get_float("numbers.float_value"), 3.14)
        self.assertEqual(config.get_list("simple_list"), ["item1", "item2", "item3"])

    def test_yaml_source_missing_file(self):
        """Test that YAML source handles missing files gracefully."""
        config = ConfigManager()
        config.add_source(YamlSource("nonexistent.yaml"))
        
        # Should not raise an exception and should return default values
        self.assertIsNone(config.get("any.key"))
        self.assertEqual(config.get("any.key", "default"), "default")

    def test_yaml_source_empty_file(self):
        """Test that YAML source handles empty files gracefully."""
        empty_yaml_path = "empty_config.yaml"
        with open(empty_yaml_path, 'w') as f:
            f.write("")  # Empty file
        
        try:
            config = ConfigManager()
            config.add_source(YamlSource(empty_yaml_path))
            
            # Should not raise an exception
            self.assertIsNone(config.get("any.key"))
        finally:
            os.remove(empty_yaml_path)

    def test_yaml_source_with_json_source(self):
        """Test YAML source working together with JSON source."""
        # Create a JSON file with some overlapping keys
        json_path = "test_config.json"
        import json
        json_config = {
            "app": {
                "name": "JsonApp",
                "environment": "production"
            },
            "database": {
                "timeout": 30
            }
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_config, f)
        
        try:
            from config_manager.sources.json_source import JsonSource
            
            config = ConfigManager()
            config.add_source(JsonSource(json_path))      # Lower priority
            config.add_source(YamlSource(self.test_yaml_path))  # Higher priority
            
            # YAML should override JSON for overlapping keys
            self.assertEqual(config.get("app.name"), "TestApp")  # From YAML
            
            # Non-overlapping keys should be preserved
            self.assertEqual(config.get("app.environment"), "production")  # From JSON
            self.assertEqual(config.get("database.timeout"), 30)  # From JSON
            self.assertEqual(config.get("database.host"), "localhost")  # From YAML
            
        finally:
            os.remove(json_path)

    def test_yaml_source_complex_structures(self):
        """Test YAML source with complex nested structures."""
        complex_yaml_path = "complex_config.yaml"
        complex_config = {
            "services": {
                "web": {
                    "image": "nginx:latest",
                    "ports": "80:80,443:443",  # Use comma-separated string
                    "environment": {
                        "NGINX_HOST": "localhost",
                        "NGINX_PORT": "80"
                    }
                },
                "db": {
                    "image": "postgres:13",
                    "environment": {
                        "POSTGRES_DB": "myapp",
                        "POSTGRES_USER": "user",
                        "POSTGRES_PASSWORD": "pass"
                    }
                }
            }
        }
        
        with open(complex_yaml_path, 'w') as f:
            if HAS_PYYAML:
                yaml.dump(complex_config, f, default_flow_style=False)
            else:
                f.write(yaml.dump(complex_config))
        
        try:
            config = ConfigManager()
            config.add_source(YamlSource(complex_yaml_path))
            
            # Test deeply nested access
            self.assertEqual(config.get("services.web.image"), "nginx:latest")
            self.assertEqual(config.get_list("services.web.ports"), ["80:80", "443:443"])
            self.assertEqual(config.get("services.web.environment.NGINX_HOST"), "localhost")
            self.assertEqual(config.get("services.db.environment.POSTGRES_DB"), "myapp")
            
        finally:
            os.remove(complex_yaml_path)

if __name__ == '__main__':
    unittest.main()

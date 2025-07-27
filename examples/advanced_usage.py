# Advanced usage example showing multiple configuration sources and reloading

import os
import json
import tempfile
import time
from config_manager import ConfigManager
from config_manager.sources import JsonSource, EnvironmentSource

# Create temporary config files
default_config_path = tempfile.mktemp(suffix='.json')
with open(default_config_path, 'w') as f:
    json.dump({
        "app": {
            "name": "AdvancedApp",
            "log_level": "info"
        },
        "features": {
            "feature1": True,
            "feature2": False
        }
    }, f, indent=2)

env_config_path = tempfile.mktemp(suffix='.json')
with open(env_config_path, 'w') as f:
    json.dump({
        "app": {
            "log_level": "debug"
        },
        "features": {
            "feature2": True
        }
    }, f, indent=2)

# Set environment variables
os.environ["APP_FEATURES_FEATURE3"] = "true"  # Will be accessible as both features.feature3 and FEATURES_FEATURE3

# Create config manager with multiple sources
config = ConfigManager()
config.add_source(JsonSource(default_config_path))  # Lowest priority
config.add_source(JsonSource(env_config_path))      # Medium priority
config.add_source(EnvironmentSource(prefix="APP_")) # Highest priority

# The environment source now provides both direct and nested access
# Print which keys are actually in the config
print("Available keys in config:", list(config._config.keys()))
print("App structure:", config._config.get('app'))
print("Features structure:", config._config.get('features'))

# Display initial configuration
print("=== Initial Configuration ===")
app_dict = config.get('app')
print(f"App name: {app_dict.get('name') if isinstance(app_dict, dict) else None}")
print(f"Log level: {config.get('app.log_level')}")  # Should be "debug" from env_config
print(f"Feature 1: {config.get_bool('features.feature1')}")  # Should be True from default_config
print(f"Feature 2: {config.get_bool('features.feature2')}")  # Should be True from env_config
print(f"Feature 3: {config.get_bool('FEATURES_FEATURE3')}")  # Should be True from environment variable

# Now modify the environment config file
with open(env_config_path, 'w') as f:
    json.dump({
        "app": {
            "log_level": "trace"
        },
        "features": {
            "feature1": False,
            "feature2": False
        }
    }, f, indent=2)

print("\n=== Before Reload (config should be unchanged) ===")
print(f"Log level: {config.get('app.log_level')}")  # Should still be "debug"

# Reload configuration
config.reload()

print("\n=== After Reload ===")
print(f"Log level: {config.get('app.log_level')}")  # Should now be "trace"
print(f"Feature 1: {config.get_bool('features.feature1')}")  # Should now be False
print(f"Feature 2: {config.get_bool('features.feature2')}")  # Should be False from env_config
print(f"Feature 3: {config.get_bool('features.feature3')}")  # Should still be True from env var

# Clean up
os.remove(default_config_path)
os.remove(env_config_path)
del os.environ["APP_FEATURES_FEATURE3"]

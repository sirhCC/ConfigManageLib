# Basic example of using ConfigManageLib

import os
import json
from config_manager import ConfigManager
from config_manager.sources import JsonSource, EnvironmentSource

# Create a sample configuration file
with open("example_config.json", "w") as f:
    json.dump({
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "debug": False
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {
                "username": "admin",
                "password": "password"
            }
        }
    }, f, indent=2)

# Set some environment variables
os.environ["APP_DATABASE_HOST"] = "db.example.com"
os.environ["APP_APP_DEBUG"] = "true"

# Create a configuration manager
config = ConfigManager()

# Add sources in order of precedence
config.add_source(JsonSource("example_config.json"))
config.add_source(EnvironmentSource(prefix="APP_"))

# Access configuration values
print(f"App Name: {config.get('app.name')}")
print(f"Version: {config.get('app.version')}")
print(f"Debug Mode: {config.get_bool('app.debug')}")  # Will be True from env var
print(f"Database Host: {config.get('database.host')}")  # Will be db.example.com from env var
print(f"Database Port: {config.get_int('database.port')}")
print(f"Database Username: {config.get('database.credentials.username')}")

# Clean up the example file
import os
os.remove("example_config.json")

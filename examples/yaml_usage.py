# Example demonstrating YAML configuration support

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to make config_manager importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import ConfigManager
from config_manager.sources import YamlSource, JsonSource, EnvironmentSource

# Create a sample YAML configuration file
yaml_config_content = """
app:
  name: "YamlDemoApp"
  version: "2.0.0"
  debug: false

database:
  host: "localhost"
  port: 5432
  name: "myapp_db"
  credentials:
    username: "dbuser"
    password: "dbpass"

api:
  base_url: "https://api.example.com"
  timeout: 30.0
  retry_attempts: 3
  endpoints:
    - "/users"
    - "/products" 
    - "/orders"

features:
  user_registration: true
  email_notifications: true
  advanced_search: false
  
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    - console
    - file

cache:
  type: "redis"
  ttl: 3600
  settings:
    host: "localhost"
    port: 6379
    db: 0
"""

# Write the YAML configuration to a file
with open("app_config.yaml", "w") as f:
    f.write(yaml_config_content)

# Set some environment variables to override specific values
os.environ["APP_DATABASE_HOST"] = "prod-db.example.com"
os.environ["APP_API_TIMEOUT"] = "60.0"
os.environ["APP_FEATURES_ADVANCED_SEARCH"] = "true"

print("=== YAML Configuration Management Demo ===\n")

# Create configuration manager with multiple sources
config = ConfigManager()
config.add_source(YamlSource("app_config.yaml"))        # Base configuration
config.add_source(EnvironmentSource(prefix="APP_"))     # Environment overrides

print("📄 Loaded configuration from YAML file and environment variables\n")

# Demonstrate accessing various configuration values
print("🏷️  Basic App Information:")
print(f"   App Name: {config.get('app.name')}")
print(f"   Version: {config.get('app.version')}")
print(f"   Debug Mode: {config.get_bool('app.debug')}")

print("\n🗄️  Database Configuration:")
print(f"   Host: {config.get('database.host')}")  # Will be overridden by env var
print(f"   Port: {config.get_int('database.port')}")
print(f"   Database: {config.get('database.name')}")
print(f"   Username: {config.get('database.credentials.username')}")

print("\n🌐 API Configuration:")
print(f"   Base URL: {config.get('api.base_url')}")
print(f"   Timeout: {config.get_float('api.timeout')} seconds")  # Will be overridden by env var
print(f"   Retry Attempts: {config.get_int('api.retry_attempts')}")
print(f"   Endpoints: {config.get_list('api.endpoints')}")

print("\n🎛️  Feature Flags:")
print(f"   User Registration: {config.get_bool('features.user_registration')}")
print(f"   Email Notifications: {config.get_bool('features.email_notifications')}")
print(f"   Advanced Search: {config.get_bool('features.advanced_search')}")  # Will be overridden by env var

print("\n📝 Logging Configuration:")
print(f"   Level: {config.get('logging.level')}")
print(f"   Format: {config.get('logging.format')}")
print(f"   Handlers: {config.get_list('logging.handlers')}")

print("\n💾 Cache Configuration:")
print(f"   Type: {config.get('cache.type')}")
print(f"   TTL: {config.get_int('cache.ttl')} seconds")
print(f"   Redis Host: {config.get('cache.settings.host')}")
print(f"   Redis Port: {config.get_int('cache.settings.port')}")

print("\n🔄 Environment Variable Overrides Applied:")
print(f"   Database host overridden to: {config.get('database.host')}")
print(f"   API timeout overridden to: {config.get_float('api.timeout')}")
print(f"   Advanced search feature enabled via env var: {config.get_bool('features.advanced_search')}")

# Demonstrate checking if keys exist
print(f"\n🔍 Configuration Key Checks:")
print(f"   'app.name' exists: {'app.name' in config}")
print(f"   'nonexistent.key' exists: {'nonexistent.key' in config}")

# Clean up
os.remove("app_config.yaml")
del os.environ["APP_DATABASE_HOST"]
del os.environ["APP_API_TIMEOUT"] 
del os.environ["APP_FEATURES_ADVANCED_SEARCH"]

print("\n✅ YAML configuration demo completed successfully!")

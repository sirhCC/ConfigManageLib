"""
Example demonstrating TOML configuration support with ConfigManager.

This example shows how to use TOML files as configuration sources,
including integration with schema validation and other sources.
"""

import tempfile
import os
from config_manager import ConfigManager
from config_manager.sources.toml_source import TomlSource
from config_manager.sources.json_source import JsonSource
from config_manager.schema import Schema, String, Integer, Boolean, ListField
from config_manager.validation import RangeValidator, ChoicesValidator


def basic_toml_example():
    """Demonstrate basic TOML configuration loading."""
    print("=== Basic TOML Configuration ===")
    
    # Create a temporary TOML file
    temp_dir = tempfile.mkdtemp()
    toml_file = os.path.join(temp_dir, "app.toml")
    
    toml_content = '''
# Application Configuration
app_name = "MyTOMLApp"
version = "2.1.0"
debug = true
port = 8080

# Features to enable
features = ["authentication", "api", "logging", "metrics"]

# Database settings
[database]
host = "localhost"
port = 5432
name = "myapp_db"
ssl_enabled = true

# Logging configuration
[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file = "/var/log/myapp.log"

[logging.handlers]
console = true
file = true
syslog = false
'''
    
    with open(toml_file, 'w') as f:
        f.write(toml_content)
    
    # Load configuration
    config = ConfigManager()
    config.add_source(TomlSource(toml_file))
    
    print(f"✅ Loaded TOML configuration from: {toml_file}")
    print(f"App: {config.get('app_name')} v{config.get('version')}")
    print(f"Debug mode: {config.get_bool('debug')}")
    print(f"Port: {config.get_int('port')}")
    print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
    print(f"SSL: {config.get_bool('database.ssl_enabled')}")
    print(f"Features: {config.get_list('features')}")
    print(f"Log level: {config.get('logging.level')}")
    print(f"Log format: {config.get('logging.format')}")
    print(f"Console logging: {config.get_bool('logging.handlers.console')}")
    print()
    
    # Cleanup
    os.remove(toml_file)
    os.rmdir(temp_dir)


def toml_with_schema_example():
    """Demonstrate TOML configuration with schema validation."""
    print("=== TOML Configuration with Schema Validation ===")
    
    # Define schema for web application
    schema = Schema({
        "app": Schema({
            "name": String(required=True),
            "version": String(default="1.0.0"),
            "environment": String(
                default="development",
                validators=[ChoicesValidator(["development", "staging", "production"])]
            ),
            "debug": Boolean(default=False)
        }),
        "server": Schema({
            "host": String(default="127.0.0.1"),
            "port": Integer(
                default=8000,
                validators=[RangeValidator(min_value=1024, max_value=65535)]
            ),
            "workers": Integer(default=4, validators=[RangeValidator(min_value=1, max_value=32)])
        }),
        "database": Schema({
            "url": String(required=True),
            "pool_size": Integer(default=10, validators=[RangeValidator(min_value=1, max_value=100)]),
            "timeout": Integer(default=30, validators=[RangeValidator(min_value=1, max_value=300)])
        }),
        "features": ListField(default=["basic"]),
        "log_level": String(
            default="INFO",
            validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]
        )
    })
    
    # Create TOML configuration
    temp_dir = tempfile.mkdtemp()
    toml_file = os.path.join(temp_dir, "webapp.toml")
    
    toml_content = '''
# Web Application Configuration

# Application settings
[app]
name = "MyWebApp"
version = "3.2.1"
environment = "production"
debug = false

# Server configuration
[server]
host = "0.0.0.0"
port = 8443
workers = 8

# Database configuration
[database]
url = "postgresql://user:pass@localhost/webapp_db"
pool_size = 20
timeout = 60

# Enabled features
features = ["auth", "api", "admin", "analytics", "caching"]

# Logging level
log_level = "WARNING"
'''
    
    with open(toml_file, 'w') as f:
        f.write(toml_content)
    
    # Load and validate configuration
    config = ConfigManager(schema=schema)
    config.add_source(TomlSource(toml_file))
    
    try:
        validated_config = config.validate()
        print("✅ TOML configuration validated successfully!")
        print(f"App: {validated_config['app']['name']} v{validated_config['app']['version']}")
        print(f"Environment: {validated_config['app']['environment']}")
        print(f"Server: {validated_config['server']['host']}:{validated_config['server']['port']}")
        print(f"Workers: {validated_config['server']['workers']}")
        print(f"Database: {validated_config['database']['url']}")
        print(f"Pool size: {validated_config['database']['pool_size']}")
        print(f"Features: {validated_config['features']}")
        print(f"Log level: {validated_config['log_level']}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    print()
    
    # Cleanup
    os.remove(toml_file)
    os.rmdir(temp_dir)


def multi_source_with_toml_example():
    """Demonstrate TOML integration with multiple configuration sources."""
    print("=== Multi-Source Configuration with TOML ===")
    
    temp_dir = tempfile.mkdtemp()
    
    # Create base TOML configuration
    toml_file = os.path.join(temp_dir, "base.toml")
    toml_content = '''
# Base configuration
app_name = "MultiSourceApp"
version = "1.0.0"

[server]
host = "localhost"
port = 8000
ssl = false

[database]
host = "localhost"
port = 5432
name = "app_db"

features = ["basic", "logging"]
'''
    
    with open(toml_file, 'w') as f:
        f.write(toml_content)
    
    # Create environment-specific JSON override
    json_file = os.path.join(temp_dir, "production.json")
    json_content = {
        "server": {
            "host": "0.0.0.0",
            "port": 443,
            "ssl": True
        },
        "database": {
            "host": "prod-db.example.com",
            "name": "production_db"
        },
        "features": ["basic", "logging", "metrics", "auth"]
    }
    
    import json
    with open(json_file, 'w') as f:
        json.dump(json_content, f, indent=2)
    
    # Load configuration with precedence: TOML (base) < JSON (environment)
    config = ConfigManager()
    config.add_source(TomlSource(toml_file))  # Base configuration
    config.add_source(JsonSource(json_file))  # Environment overrides
    
    print("📄 Base TOML + Production JSON Override")
    print(f"App: {config.get('app_name')} v{config.get('version')}")
    print(f"Server: {config.get('server.host')}:{config.get_int('server.port')} (SSL: {config.get_bool('server.ssl')})")
    print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
    print(f"Features: {config.get_list('features')}")
    print()
    
    # Cleanup
    os.remove(toml_file)
    os.remove(json_file)
    os.rmdir(temp_dir)


def pyproject_toml_example():
    """Demonstrate loading from a pyproject.toml-style file."""
    print("=== PyProject.toml Style Configuration ===")
    
    temp_dir = tempfile.mkdtemp()
    pyproject_file = os.path.join(temp_dir, "pyproject.toml")
    
    # Simulate a pyproject.toml with custom tool configuration
    pyproject_content = '''
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-awesome-project"
version = "0.1.0"
description = "An awesome Python project"
authors = [{name = "Developer", email = "dev@example.com"}]

# Custom tool configuration section
[tool.myapp]
debug = true
log_level = "DEBUG"
max_workers = 4

[tool.myapp.database]
url = "sqlite:///app.db"
echo = true

[tool.myapp.features]
enabled = ["auth", "api", "web_ui"]
experimental = ["ai_features", "advanced_analytics"]
'''
    
    with open(pyproject_file, 'w') as f:
        f.write(pyproject_content)
    
    # Load and extract tool-specific configuration
    config = ConfigManager()
    config.add_source(TomlSource(pyproject_file))
    
    print(f"📦 Project: {config.get('project.name')} v{config.get('project.version')}")
    print(f"Description: {config.get('project.description')}")
    print(f"Build system: {config.get_list('build-system.requires')}")
    print()
    print("🔧 Tool Configuration:")
    print(f"Debug: {config.get_bool('tool.myapp.debug')}")
    print(f"Log level: {config.get('tool.myapp.log_level')}")
    print(f"Max workers: {config.get_int('tool.myapp.max_workers')}")
    print(f"Database: {config.get('tool.myapp.database.url')}")
    print(f"DB Echo: {config.get_bool('tool.myapp.database.echo')}")
    print(f"Features: {config.get_list('tool.myapp.features.enabled')}")
    print(f"Experimental: {config.get_list('tool.myapp.features.experimental')}")
    print()
    
    # Cleanup
    os.remove(pyproject_file)
    os.rmdir(temp_dir)


def toml_fallback_parser_example():
    """Demonstrate the fallback TOML parser."""
    print("=== TOML Fallback Parser Demo ===")
    
    temp_dir = tempfile.mkdtemp()
    toml_file = os.path.join(temp_dir, "simple.toml")
    
    toml_content = '''
# Simple TOML file to test fallback parser
app_name = "FallbackDemo"
version = "1.0.0"
debug = true
port = 8080
timeout = 30.5

# Array of strings
tags = ["demo", "fallback", "simple"]

# Section
[database]
host = "localhost"
port = 5432
ssl = false

# Nested section
[logging.handlers]
console = true
file = false
'''
    
    with open(toml_file, 'w') as f:
        f.write(toml_content)
    
    # Force use of fallback parser
    source = TomlSource(toml_file)
    print(f"🔧 Parser type: {source._toml_parser[0]}")
    
    # Override to force simple parser for demonstration
    source._toml_parser = ("simple", None)
    print(f"🔧 Forced parser type: {source._toml_parser[0]}")
    
    config_data = source.load()
    
    print("✅ Fallback parser successfully loaded configuration:")
    print(f"App: {config_data['app_name']} v{config_data['version']}")
    print(f"Debug: {config_data['debug']}")
    print(f"Port: {config_data['port']}")
    print(f"Timeout: {config_data['timeout']}")
    print(f"Tags: {config_data['tags']}")
    print(f"Database: {config_data['database']['host']}:{config_data['database']['port']}")
    print(f"SSL: {config_data['database']['ssl']}")
    print(f"Console logging: {config_data['logging']['handlers']['console']}")
    print()
    
    # Cleanup
    os.remove(toml_file)
    os.rmdir(temp_dir)


if __name__ == "__main__":
    print("🚀 ConfigManager TOML Support Examples")
    print("=" * 50)
    print()
    
    basic_toml_example()
    toml_with_schema_example()
    multi_source_with_toml_example()
    pyproject_toml_example()
    toml_fallback_parser_example()
    
    print("🎉 TOML configuration examples completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Basic TOML file loading")
    print("✓ Nested sections and arrays")
    print("✓ Schema validation with TOML")
    print("✓ Multi-source configuration (TOML + JSON)")
    print("✓ PyProject.toml style configuration")
    print("✓ Fallback parser for environments without TOML libraries")
    print("✓ Type conversion and validation")
    print("✓ Comments and inline comments support")

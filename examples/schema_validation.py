"""
Example demonstrating schema validation with ConfigManager.

This example shows how to use the schema validation system to:
1. Define configuration schemas with types, defaults, and validation rules
2. Validate configuration data from multiple sources
3. Handle validation errors gracefully
4. Use nested schemas for complex configurations
"""

import tempfile
import os
import json
from config_manager import ConfigManager
from config_manager.schema import Schema, String, Integer, Float, Boolean, ListField
from config_manager.validation import ValidationError, RangeValidator, ChoicesValidator, RegexValidator
from config_manager.sources.json_source import JsonSource
from config_manager.sources.environment import EnvironmentSource


def basic_schema_example():
    """Demonstrate basic schema validation."""
    print("=== Basic Schema Validation ===")
    
    # Define a schema for a web application configuration
    schema = Schema({
        "app_name": String(required=True, description="Application name"),
        "port": Integer(
            default=8080, 
            validators=[RangeValidator(min_value=1024, max_value=65535)],
            description="Server port number"
        ),
        "host": String(default="localhost", description="Server host"),
        "debug": Boolean(default=False, description="Enable debug mode"),
        "allowed_origins": ListField(default=[], description="CORS allowed origins"),
        "log_level": String(
            default="INFO",
            validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])],
            description="Logging level"
        )
    })
    
    # Create configuration data
    config_data = {
        "app_name": "MyWebApp",
        "port": "3000",  # String that will be converted to int
        "debug": "true",  # String that will be converted to bool
        "allowed_origins": "localhost,127.0.0.1,*.example.com",  # String that will be converted to list
        "log_level": "DEBUG"
    }
    
    # Create ConfigManager with schema
    config = ConfigManager(schema=schema)
    
    # Simulate environment source
    class MockEnvironmentSource:
        def __init__(self, data):
            self._data = data
        def load(self):
            return self._data
    
    config.add_source(MockEnvironmentSource(config_data))
    
    # Validate and get configuration
    try:
        validated_config = config.validate()
        print("✅ Configuration is valid!")
        print(f"App Name: {validated_config['app_name']}")
        print(f"Port: {validated_config['port']} (type: {type(validated_config['port'])})")
        print(f"Host: {validated_config['host']} (default applied)")
        print(f"Debug: {validated_config['debug']} (type: {type(validated_config['debug'])})")
        print(f"Allowed Origins: {validated_config['allowed_origins']}")
        print(f"Log Level: {validated_config['log_level']}")
        print()
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        print()


def validation_error_example():
    """Demonstrate validation error handling."""
    print("=== Validation Error Handling ===")
    
    # Schema with strict validation
    schema = Schema({
        "username": String(
            required=True,
            validators=[RegexValidator(r"^[a-zA-Z0-9_]{3,20}$")],
            description="Username (3-20 alphanumeric characters and underscores)"
        ),
        "age": Integer(
            required=True,
            validators=[RangeValidator(min_value=18, max_value=120)],
            description="User age (18-120)"
        ),
        "email": String(
            required=True,
            validators=[RegexValidator(r"^[^@]+@[^@]+\.[^@]+$")],
            description="Valid email address"
        )
    })
    
    # Invalid configuration data
    invalid_config_data = {
        "username": "u",  # Too short
        "age": 15,  # Too young
        "email": "invalid-email"  # Invalid format
    }
    
    config = ConfigManager(schema=schema)
    
    class MockEnvironmentSource:
        def __init__(self, data):
            self._data = data
        def load(self):
            return self._data
    
    config.add_source(MockEnvironmentSource(invalid_config_data))
    
    # Check if configuration is valid
    if config.is_valid():
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration has validation errors:")
        errors = config.get_validation_errors()
        for error in errors:
            print(f"  - {error}")
    
    # Try to validate with error handling
    try:
        validated_config = config.validate()
        print("This shouldn't be reached")
    except ValidationError as e:
        print(f"\n💥 Validation failed: {e}")
    
    # Get configuration without raising errors
    fallback_config = config.validate(raise_on_error=False)
    print(f"\n🔄 Fallback configuration (validation ignored):")
    print(f"Username: {fallback_config['username']}")
    print(f"Age: {fallback_config['age']}")
    print(f"Email: {fallback_config['email']}")
    print()


def nested_schema_example():
    """Demonstrate nested schema validation."""
    print("=== Nested Schema Validation ===")
    
    # Define nested schemas
    database_schema = Schema({
        "host": String(default="localhost"),
        "port": Integer(default=5432, validators=[RangeValidator(min_value=1, max_value=65535)]),
        "name": String(required=True),
        "username": String(required=True),
        "password": String(required=True),
        "pool_size": Integer(default=10, validators=[RangeValidator(min_value=1, max_value=100)])
    })
    
    redis_schema = Schema({
        "host": String(default="localhost"),
        "port": Integer(default=6379),
        "db": Integer(default=0, validators=[RangeValidator(min_value=0, max_value=15)])
    })
    
    app_schema = Schema({
        "app_name": String(required=True),
        "version": String(default="1.0.0"),
        "database": database_schema,
        "redis": redis_schema,
        "features": ListField(default=["basic"]),
        "environment": String(
            default="development",
            validators=[ChoicesValidator(["development", "staging", "production"])]
        )
    })
    
    # Configuration data with nested structures
    config_data = {
        "app_name": "MyComplexApp",
        "version": "2.1.0",
        "database": {
            "name": "myapp_db",
            "username": "dbuser",
            "password": "secret123",
            "port": 3306  # Override default
        },
        "redis": {
            "db": 1
        },
        "features": "auth,api,admin",
        "environment": "production"
    }
    
    config = ConfigManager(schema=app_schema)
    
    class MockEnvironmentSource:
        def __init__(self, data):
            self._data = data
        def load(self):
            return self._data
    
    config.add_source(MockEnvironmentSource(config_data))
    
    try:
        validated_config = config.validate()
        print("✅ Nested configuration is valid!")
        print(f"App: {validated_config['app_name']} v{validated_config['version']}")
        print(f"Environment: {validated_config['environment']}")
        print(f"Database: {validated_config['database']['name']} on {validated_config['database']['host']}:{validated_config['database']['port']}")
        print(f"Redis: {validated_config['redis']['host']}:{validated_config['redis']['port']} (db: {validated_config['redis']['db']})")
        print(f"Features: {validated_config['features']}")
        print(f"Database pool size: {validated_config['database']['pool_size']} (default applied)")
        print()
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        print()


def file_based_example():
    """Demonstrate schema validation with file-based configuration."""
    print("=== File-Based Configuration with Schema ===")
    
    # Create temporary config file
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, "app_config.json")
    
    # Define schema
    schema = Schema({
        "server": Schema({
            "host": String(default="0.0.0.0"),
            "port": Integer(required=True, validators=[RangeValidator(min_value=1024, max_value=65535)]),
            "ssl": Boolean(default=False)
        }),
        "database": Schema({
            "url": String(required=True),
            "timeout": Float(default=30.0, validators=[RangeValidator(min_value=1.0, max_value=300.0)])
        }),
        "logging": Schema({
            "level": String(default="INFO", validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]),
            "file": String(default=None)
        })
    })
    
    # Create config file
    config_data = {
        "server": {
            "port": 8443,
            "ssl": True
        },
        "database": {
            "url": "postgresql://user:pass@localhost/mydb",
            "timeout": 60.5
        },
        "logging": {
            "level": "DEBUG",
            "file": "/var/log/myapp.log"
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"📄 Created config file: {config_file}")
    
    # Load configuration with schema validation
    config = ConfigManager(schema=schema)
    config.add_source(JsonSource(config_file))
    
    try:
        validated_config = config.validate()
        print("✅ File-based configuration is valid!")
        print(f"Server: {validated_config['server']['host']}:{validated_config['server']['port']} (SSL: {validated_config['server']['ssl']})")
        print(f"Database: {validated_config['database']['url']} (timeout: {validated_config['database']['timeout']}s)")
        print(f"Logging: {validated_config['logging']['level']} -> {validated_config['logging']['file']}")
        print()
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        print()
    finally:
        # Clean up
        os.remove(config_file)
        os.rmdir(temp_dir)


if __name__ == "__main__":
    print("🔧 ConfigManager Schema Validation Examples")
    print("=" * 50)
    print()
    
    basic_schema_example()
    validation_error_example()
    nested_schema_example()
    file_based_example()
    
    print("🎉 Schema validation examples completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Type conversion (string -> int, bool, list)")
    print("✓ Default value application")
    print("✓ Validation rules (range, choices, regex)")
    print("✓ Required field checking")
    print("✓ Nested schema validation")
    print("✓ Error handling and fallback behavior")
    print("✓ File-based configuration validation")

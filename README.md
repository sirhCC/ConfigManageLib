# ConfigManageLib

A modern, flexible, and type-safe configuration management library for Python.

## Features

- 📦 Load configuration from multiple sources (JSON, YAML, environment variables, and more)
- 🔄 Override configuration values with a defined order of precedence
- 🌳 Support for nested configuration values using dot notation
- 🧩 Type conversion helpers for common data types (int, float, bool, list)
- ✅ Schema validation with type checking, defaults, and validation rules
- 🔄 Easy reloading of configuration when sources change
- 📝 Comprehensive documentation and test coverage

## Installation

```bash
pip install configmanagelib
```

## Quick Start

```python
from config_manager import ConfigManager
from config_manager.sources import JsonSource, YamlSource, EnvironmentSource

# Create a new configuration manager
config = ConfigManager()

# Add sources in order of precedence (lowest to highest)
config.add_source(YamlSource('config/defaults.yaml'))
config.add_source(JsonSource('config/environment.json'))
config.add_source(EnvironmentSource(prefix='APP_'))

# Access configuration values
db_host = config.get('database.host', 'localhost')
db_port = config.get_int('database.port', 5432)
debug_mode = config.get_bool('debug', False)
allowed_origins = config.get_list('security.allowed_origins', [])

# Dictionary-style access
api_key = config['api.key']
```

## Configuration Sources

### YAML Source

Load configuration from a YAML file:

```python
from config_manager.sources import YamlSource

config.add_source(YamlSource('config.yaml'))
```

Example YAML file:
```yaml
app:
  name: "MyApp"
  debug: false

database:
  host: "localhost"
  port: 5432
  credentials:
    username: "admin"
    password: "secret"

features:
  - user_registration
  - email_notifications
```

### JSON Source

Load configuration from a JSON file:

```python
from config_manager.sources import JsonSource

config.add_source(JsonSource('config.json'))
```

### Environment Variables

Load configuration from environment variables:

```python
from config_manager.sources import EnvironmentSource

# Load all environment variables with the APP_ prefix
# For example, APP_DATABASE_HOST will be available as DATABASE_HOST
config.add_source(EnvironmentSource(prefix='APP_'))
```

## Advanced Usage

### Schema Validation

Define schemas to validate configuration structure, types, and values:

```python
from config_manager import ConfigManager
from config_manager.schema import Schema, String, Integer, Boolean
from config_manager.validation import RangeValidator, ChoicesValidator

# Define a schema
schema = Schema({
    "app_name": String(required=True),
    "port": Integer(default=8080, validators=[RangeValidator(min_value=1024, max_value=65535)]),
    "debug": Boolean(default=False),
    "log_level": String(default="INFO", validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])])
})

# Create ConfigManager with schema
config = ConfigManager(schema=schema)
config.add_source(JsonSource('config.json'))

# Validate configuration
try:
    validated_config = config.validate()
    print(f"App: {validated_config['app_name']}")
    print(f"Port: {validated_config['port']}")  # Automatically converted to int
except ValidationError as e:
    print(f"Configuration error: {e}")

# Check if configuration is valid
if config.is_valid():
    print("✅ Configuration is valid!")
else:
    errors = config.get_validation_errors()
    for error in errors:
        print(f"❌ {error}")
```

For detailed schema validation documentation, see [SCHEMA_VALIDATION.md](SCHEMA_VALIDATION.md).

### Nested Configuration

Access nested configuration values using dot notation:

```python
# Given a JSON structure like:
# {
#   "database": {
#     "host": "localhost",
#     "port": 5432,
#     "credentials": {
#       "username": "admin"
#     }
#   }
# }

host = config.get('database.host')  # 'localhost'
username = config.get('database.credentials.username')  # 'admin'
```

### Type Conversion

Convert configuration values to specific types:

```python
port = config.get_int('database.port', 5432)  # Returns an int
timeout = config.get_float('api.timeout', 30.0)  # Returns a float
debug = config.get_bool('app.debug', False)  # Returns a boolean
allowed_hosts = config.get_list('security.allowed_hosts', ['localhost'])  # Returns a list
```

### Reloading Configuration

Reload configuration from all sources:

```python
# When configuration sources change (e.g., updated JSON files)
config.reload()
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

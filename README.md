# ConfigManageLib

A modern, flexible, and type-safe configuration management library for Python.

## Features

- 📦 Load configuration from multiple sources (JSON, YAML, TOML, INI/CFG, remote HTTP/HTTPS, environment variables, and more)
- 🌐 Remote configuration support with authentication (Bearer tokens, API keys, Basic auth)
- 🔄 **Configuration File Watching & Auto-Reload** - Automatically reload configuration when files change (zero-downtime updates)
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

**Optional Dependencies:**
- For TOML support: `pip install tomli` (Python 3.11+) or `pip install toml`
- For YAML support: `pip install PyYAML`

*Note: TOML and YAML sources include fallback parsers and will work without external libraries for basic use cases.*

## Quick Start

```python
from config_manager import ConfigManager
from config_manager.sources import (
    JsonSource, YamlSource, TomlSource, IniSource, 
    EnvironmentSource, RemoteSource
)

# Create a new configuration manager with auto-reload
config = ConfigManager(auto_reload=True)

# Add sources in order of precedence (lowest to highest)
config.add_source(YamlSource('config/defaults.yaml'))
config.add_source(TomlSource('config/app.toml'))
config.add_source(IniSource('config/app.ini'))
config.add_source(JsonSource('config/environment.json'))
config.add_source(RemoteSource('https://config.example.com/api/config'))
config.add_source(EnvironmentSource(prefix='APP_'))

# Configuration will automatically reload when files change!

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

### TOML Source

Load configuration from a TOML file:

```python
from config_manager.sources import TomlSource

config.add_source(TomlSource('config.toml'))
```

Example TOML file:
```toml
# Application Configuration
app_name = "MyApp"
debug = false
features = ["user_registration", "email_notifications"]

[database]
host = "localhost"
port = 5432

[database.credentials]
username = "admin"
password = "secret"
```

**TOML Library Support**: The TOML source automatically detects and uses available TOML libraries (`tomli` or `toml`). If no library is available, it falls back to a built-in simple parser that handles basic TOML syntax.

**PyProject.toml Support**: Perfect for loading configuration from `pyproject.toml` files:

```python
# Load tool configuration from pyproject.toml
config.add_source(TomlSource('pyproject.toml'))

# Access tool-specific settings
debug = config.get_bool('tool.myapp.debug', False)
workers = config.get_int('tool.myapp.workers', 4)
```

### INI/CFG Source

Load configuration from INI or CFG files:

```python
from config_manager.sources import IniSource

# Load all sections as nested dictionary
config.add_source(IniSource('config.ini'))

# Load only a specific section as flat dictionary
config.add_source(IniSource('setup.cfg', section='metadata'))
```

Example INI file:
```ini
# Application Configuration
[app]
name = MyApp
debug = false
port = 8080

[database]
host = localhost
port = 5432
ssl = true

[features]
authentication = true
api = false
logging = true
```

**Perfect for Python Projects**: INI sources work excellently with common Python configuration files:

```python
# Load setup.cfg metadata
config.add_source(IniSource('setup.cfg', section='metadata'))
project_name = config.get('name')

# Load pytest configuration
config.add_source(IniSource('pytest.ini', section='tool:pytest'))
test_paths = config.get('testpaths')

# Load full configuration with all sections
config.add_source(IniSource('app.ini'))
db_host = config.get('database.host')
```

**Built-in Type Conversion**: Automatically converts string values to appropriate Python types (bool, int, float).

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

### Remote Configuration Source

Load configuration from remote HTTP/HTTPS endpoints for centralized configuration management:

```python
from config_manager.sources import RemoteSource, remote_source

# Basic usage
config.add_source(RemoteSource('https://config.example.com/api/config'))

# Using the fluent builder API with authentication
source = remote_source('https://config.example.com/api/config') \
    .with_bearer_token('your-token-here') \
    .with_header('X-Client-Version', '1.0.0') \
    .with_timeout(30.0) \
    .build()

config.add_source(source)
```

**Authentication Support**: Multiple authentication methods are supported:

```python
# Bearer Token Authentication
source = remote_source(url).with_bearer_token('token123').build()

# API Key Authentication
source = remote_source(url).with_api_key('key123', 'X-API-Key').build()

# Basic Authentication
source = remote_source(url).with_basic_auth('user', 'pass').build()

# Custom Headers
source = remote_source(url) \
    .with_header('Authorization', 'Custom auth-scheme') \
    .with_header('X-Service', 'ConfigManager') \
    .build()
```

**Configuration Options**:

```python
source = remote_source('https://config.example.com/config.json') \
    .with_timeout(30.0) \           # Request timeout in seconds
    .with_ssl_verify(True) \        # SSL certificate verification
    .with_user_agent('MyApp/1.0') \ # Custom User-Agent header
    .build()
```

**Perfect for Cloud-Native Applications**: Ideal for microservices, containerized applications, and cloud deployments where configuration needs to be centralized and dynamically updated.

```python
# Environment-specific configuration
env = os.getenv('ENVIRONMENT', 'production')
config_url = f'https://config-service.example.com/api/config/{env}'

config = ConfigManager()
config.add_source(remote_source(config_url)
    .with_bearer_token(os.getenv('CONFIG_TOKEN'))
    .with_timeout(10.0)
    .build())
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

### Multi-Source Configuration with TOML

Combine multiple configuration sources with TOML as the base configuration:

```python
from config_manager import ConfigManager
from config_manager.sources import TomlSource, JsonSource, EnvironmentSource

# Create configuration manager
config = ConfigManager()

# Base configuration from TOML
config.add_source(TomlSource('app.toml'))

# Environment-specific overrides from JSON
config.add_source(JsonSource('config/production.json'))

# Runtime overrides from environment variables
config.add_source(EnvironmentSource(prefix='APP_'))

# TOML configuration takes precedence order into account
# Environment variables > JSON > TOML
app_name = config.get('app.name')
database_url = config.get('database.url')
```

Example `app.toml`:
```toml
[app]
name = "MyApp"
version = "1.0.0"
debug = false

[database]
url = "sqlite:///app.db"
pool_size = 5

[features]
authentication = true
api = true
web_ui = false
```

### Multi-Source Configuration with INI

Use INI files as base configuration with other source overrides:

```python
from config_manager import ConfigManager
from config_manager.sources import IniSource, JsonSource, EnvironmentSource

# Create configuration manager
config = ConfigManager()

# Base configuration from INI/CFG
config.add_source(IniSource('app.ini'))

# Environment-specific overrides from JSON
config.add_source(JsonSource('config/production.json'))

# Runtime overrides from environment variables
config.add_source(EnvironmentSource(prefix='APP_'))

# INI configuration with precedence order
# Environment variables > JSON > INI
server_port = config.get_int('server.port')
db_host = config.get('database.host')
```

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

### Configuration File Watching & Auto-Reload

Automatically reload configuration when files change, enabling zero-downtime configuration updates:

```python
# Enable auto-reload for file-based sources
config = ConfigManager(auto_reload=True)
config.add_source(JsonSource('app.json'))
config.add_source(YamlSource('config.yaml'))

# Configuration will automatically reload when files change
# No manual intervention required!
```

**Callback Support**: Register functions to be called when configuration reloads:

```python
def on_config_change():
    print("Configuration updated! Refreshing application state...")
    # Update application state based on new configuration
    update_database_pool_size(config.get_int('database.pool_size'))
    update_log_level(config.get('logging.level'))

# Register callback
config = ConfigManager(auto_reload=True, reload_interval=1.0)
config.add_source(JsonSource('app.json'))
config.on_reload(on_config_change)
```

**Configuration Options**:

```python
# Customize auto-reload behavior
config = ConfigManager(
    auto_reload=True,           # Enable auto-reload
    reload_interval=0.5         # Check for changes every 0.5 seconds
)

# Multiple callbacks are supported
config.on_reload(update_cache_settings)
config.on_reload(refresh_feature_flags)
config.on_reload(log_config_change)

# Remove callbacks when no longer needed
config.remove_reload_callback(update_cache_settings)
```

**File Watching Technology**: Auto-reload uses the `watchdog` library for efficient file monitoring when available, with automatic fallback to polling for maximum compatibility.

**Production Benefits**:
- **Zero-downtime updates**: Change configuration without restarting applications
- **Feature flag updates**: Enable/disable features in real-time
- **Scaling adjustments**: Modify connection pools, timeouts, and limits dynamically
- **Environment transitions**: Switch between configurations seamlessly

**Installation for Optimal Performance**:
```bash
pip install watchdog  # Optional: For better file watching performance
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

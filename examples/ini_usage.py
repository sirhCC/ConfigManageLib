"""
Example demonstrating INI/CFG configuration support with ConfigManager.

This example shows how to use INI/CFG files as configuration sources,
including integration with schema validation and other sources.
"""

import tempfile
import os
from config_manager import ConfigManager
from config_manager.sources.ini_source import IniSource
from config_manager.sources.json_source import JsonSource
from config_manager.schema import Schema, String, Integer, Boolean, ListField
from config_manager.validation import RangeValidator, ChoicesValidator


def basic_ini_example():
    """Demonstrate basic INI configuration loading."""
    print("=== Basic INI Configuration ===")
    
    # Create temporary INI file
    temp_dir = tempfile.mkdtemp()
    ini_file = os.path.join(temp_dir, "app.ini")
    
    ini_content = '''
# Application Configuration
[app]
name = MyINIApp
version = 2.5.0
debug = true
port = 8080

# Database settings
[database]
host = localhost
port = 5432
name = myapp_db
ssl_enabled = true
timeout = 45.5

# Feature flags
[features]
authentication = true
api = true
logging = false
metrics = true
'''
    
    with open(ini_file, 'w') as f:
        f.write(ini_content)
    
    # Load configuration
    config = ConfigManager()
    config.add_source(IniSource(ini_file))
    
    print(f"✅ Loaded INI configuration from: {ini_file}")
    print(f"App: {config.get('app.name')} v{config.get('app.version')}")
    print(f"Debug mode: {config.get_bool('app.debug')}")
    print(f"Port: {config.get_int('app.port')}")
    print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
    print(f"SSL: {config.get_bool('database.ssl_enabled')}")
    print(f"DB Timeout: {config.get_float('database.timeout')} seconds")
    print(f"Features:")
    print(f"  - Authentication: {config.get_bool('features.authentication')}")
    print(f"  - API: {config.get_bool('features.api')}")
    print(f"  - Logging: {config.get_bool('features.logging')}")
    print(f"  - Metrics: {config.get_bool('features.metrics')}")
    print()
    
    # Cleanup
    os.remove(ini_file)
    os.rmdir(temp_dir)


def ini_specific_section_example():
    """Demonstrate loading a specific INI section."""
    print("=== INI Specific Section Loading ===")
    
    temp_dir = tempfile.mkdtemp()
    ini_file = os.path.join(temp_dir, "multi_section.ini")
    
    ini_content = '''
[app]
name = SectionApp
debug = false
port = 3000

[database]
host = db.example.com
port = 5432
ssl = true

[cache]
type = redis
host = cache.example.com
port = 6379
ttl = 3600
'''
    
    with open(ini_file, 'w') as f:
        f.write(ini_content)
    
    # Load only the database section
    config = ConfigManager()
    config.add_source(IniSource(ini_file, section='database'))
    
    print("📄 Loaded only 'database' section from INI file")
    print(f"Database Host: {config.get('host')}")
    print(f"Database Port: {config.get_int('port')}")
    print(f"SSL Enabled: {config.get_bool('ssl')}")
    
    # Note: Other sections are not available
    print(f"App name (should be None): {config.get('name', 'Not Available')}")
    print()
    
    # Cleanup
    os.remove(ini_file)
    os.rmdir(temp_dir)


def ini_with_schema_example():
    """Demonstrate INI configuration with schema validation."""
    print("=== INI Configuration with Schema Validation ===")
    
    # Define schema for application
    schema = Schema({
        "server": Schema({
            "name": String(required=True),
            "host": String(default="localhost"),
            "port": Integer(
                default=8000,
                validators=[RangeValidator(min_value=1024, max_value=65535)]
            ),
            "debug": Boolean(default=False)
        }),
        "database": Schema({
            "host": String(required=True),
            "port": Integer(default=5432),
            "name": String(required=True),
            "ssl": Boolean(default=False)
        }),
        "logging": Schema({
            "level": String(
                default="INFO",
                validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]
            ),
            "file": String(default="/var/log/app.log")
        })
    })
    
    # Create INI configuration
    temp_dir = tempfile.mkdtemp()
    ini_file = os.path.join(temp_dir, "server.ini")
    
    ini_content = '''
# Server Configuration with Schema Validation

[server]
name = WebServer
host = 0.0.0.0
port = 8443
debug = true

[database]
host = prod-db.example.com
port = 5432
name = production_db
ssl = true

[logging]
level = DEBUG
file = /var/log/webserver.log
'''
    
    with open(ini_file, 'w') as f:
        f.write(ini_content)
    
    # Load and validate configuration
    config = ConfigManager(schema=schema)
    config.add_source(IniSource(ini_file))
    
    try:
        validated_config = config.validate()
        print("✅ INI configuration validated successfully!")
        print(f"Server: {validated_config['server']['name']} on {validated_config['server']['host']}:{validated_config['server']['port']}")
        print(f"Debug: {validated_config['server']['debug']}")
        print(f"Database: {validated_config['database']['name']} at {validated_config['database']['host']}")
        print(f"SSL: {validated_config['database']['ssl']}")
        print(f"Log Level: {validated_config['logging']['level']}")
        print(f"Log File: {validated_config['logging']['file']}")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
    
    print()
    
    # Cleanup
    os.remove(ini_file)
    os.rmdir(temp_dir)


def multi_source_with_ini_example():
    """Demonstrate INI integration with multiple configuration sources."""
    print("=== Multi-Source Configuration with INI ===")
    
    temp_dir = tempfile.mkdtemp()
    
    # Create base INI configuration
    ini_file = os.path.join(temp_dir, "base.ini")
    ini_content = '''
# Base Configuration
[app]
name = MultiSourceApp
version = 1.0.0
debug = false

[server]
host = localhost
port = 8000
ssl = false

[database]
host = localhost
port = 5432
name = app_db

[features]
auth = true
api = true
logging = false
'''
    
    with open(ini_file, 'w') as f:
        f.write(ini_content)
    
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
        "features": {
            "logging": True,
            "metrics": True,
            "monitoring": True
        }
    }
    
    import json
    with open(json_file, 'w') as f:
        json.dump(json_content, f, indent=2)
    
    # Load configuration with precedence: INI (base) < JSON (environment)
    config = ConfigManager()
    config.add_source(IniSource(ini_file))  # Base configuration
    config.add_source(JsonSource(json_file))  # Environment overrides
    
    print("📄 Base INI + Production JSON Override")
    print(f"App: {config.get('app.name')} v{config.get('app.version')}")
    print(f"Server: {config.get('server.host')}:{config.get_int('server.port')} (SSL: {config.get_bool('server.ssl')})")
    print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
    print(f"Features:")
    print(f"  - Auth: {config.get_bool('features.auth')}")
    print(f"  - API: {config.get_bool('features.api')}")
    print(f"  - Logging: {config.get_bool('features.logging')}")  # Overridden to True
    print(f"  - Metrics: {config.get_bool('features.metrics', False)}")  # Added by JSON
    print(f"  - Monitoring: {config.get_bool('features.monitoring', False)}")  # Added by JSON
    print()
    
    # Cleanup
    os.remove(ini_file)
    os.remove(json_file)
    os.rmdir(temp_dir)


def setup_cfg_example():
    """Demonstrate loading from a setup.cfg-style file."""
    print("=== Setup.cfg Style Configuration ===")
    
    temp_dir = tempfile.mkdtemp()
    setup_cfg = os.path.join(temp_dir, "setup.cfg")
    
    setup_cfg_content = '''
[metadata]
name = my-awesome-package
version = 2.1.0
author = John Doe
author_email = john@example.com
description = An awesome Python package
long_description_content_type = text/markdown
url = https://github.com/johndoe/my-awesome-package
project_urls =
    Bug Tracker = https://github.com/johndoe/my-awesome-package/issues

[options]
packages = find:
python_requires = >=3.7
include_package_data = true
zip_safe = false
install_requires =
    requests>=2.25.0
    click>=7.0

[options.extras_require]
dev =
    pytest>=6.0
    flake8>=3.8
    black>=20.8
test =
    pytest>=6.0
    coverage>=5.0

[tool:pytest]
testpaths = tests
addopts = -v --tb=short
python_files = test_*.py
python_classes = Test*
python_functions = test_*

[flake8]
max-line-length = 88
exclude = .git,__pycache__,build,dist
ignore = E203,W503
'''
    
    with open(setup_cfg, 'w') as f:
        f.write(setup_cfg_content)
    
    # Load configuration
    config = ConfigManager()
    config.add_source(IniSource(setup_cfg))
    
    print(f"📦 Loaded setup.cfg from: {setup_cfg}")
    print(f"Package: {config.get('metadata.name')} v{config.get('metadata.version')}")
    print(f"Author: {config.get('metadata.author')} ({config.get('metadata.author_email')})")
    print(f"Description: {config.get('metadata.description')}")
    print(f"Python Requirements: {config.get('options.python_requires')}")
    print(f"Include Package Data: {config.get_bool('options.include_package_data')}")
    print(f"Zip Safe: {config.get_bool('options.zip_safe')}")
    print(f"Pytest Test Paths: {config.get('tool:pytest.testpaths')}")
    print(f"Flake8 Max Line Length: {config.get_int('flake8.max-line-length')}")
    print()
    
    # Cleanup
    os.remove(setup_cfg)
    os.rmdir(temp_dir)


if __name__ == "__main__":
    print("🚀 ConfigManager INI/CFG Support Examples")
    print("=" * 50)
    print()
    
    basic_ini_example()
    ini_specific_section_example()
    ini_with_schema_example()
    multi_source_with_ini_example()
    setup_cfg_example()
    
    print("🎉 INI configuration examples completed!")
    print("Key Features Demonstrated:")
    print("✓ Basic INI file loading")
    print("✓ Specific section loading")
    print("✓ Type conversion (bool, int, float)")
    print("✓ Schema validation with INI")
    print("✓ Multi-source configuration (INI + JSON)")
    print("✓ Setup.cfg style configuration")
    print("✓ Comments and nested sections support")
    print("✓ Integration with existing ConfigManager ecosystem")

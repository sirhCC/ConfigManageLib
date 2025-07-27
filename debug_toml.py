#!/usr/bin/env python3

import tempfile
import os
from config_manager.sources.toml_source import TomlSource

# Create the same TOML content as in the example
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
console = true
'''

# Create temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
    f.write(toml_content)
    temp_file = f.name

try:
    # Load with TOML source
    source = TomlSource(temp_file)
    print(f"Parser type: {source._toml_parser[0]}")
    
    # Load the data
    data = source.load()
    
    print("Loaded data keys:", list(data.keys()))
    print("Features value:", repr(data.get('features')))
    print("Features type:", type(data.get('features')))
    
    if 'features' in data:
        print("Features found in root data")
    else:
        print("Features NOT found in root data")
        
    # Print all data for debugging
    print("\nFull data structure:")
    import pprint
    pprint.pprint(data)
    
finally:
    # Clean up
    os.unlink(temp_file)

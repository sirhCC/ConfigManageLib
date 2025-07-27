#!/usr/bin/env python3
"""Debug script to understand TOML parsing issue."""

import tempfile
import os
from pathlib import Path

# Add the project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config_manager.sources.toml_source import TomlSource

def debug_toml_parsing():
    """Debug the TOML parsing issue step by step."""
    
    # Create a simple test TOML file
    toml_content = """
[app]
name = "test-app"
version = "1.0.0"
debug = true

[database]
host = "localhost"
port = 5432
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        temp_file = f.name
    
    try:
        print("🔍 Creating TomlSource...")
        source = TomlSource(temp_file)
        
        print(f"🔍 Parser info: {source._parser_info}")
        print(f"🔍 File mode will be: {source._parser_info['method']}")
        
        # Test reading the file manually
        file_mode = source._parser_info["method"]
        encoding = None if file_mode == "rb" else "utf-8"
        
        print(f"🔍 Reading file with mode '{file_mode}', encoding: {encoding}")
        
        with open(temp_file, file_mode, encoding=encoding) as f:
            content = f.read()
        
        print(f"🔍 Content type: {type(content)}")
        print(f"🔍 Content length: {len(content)}")
        print(f"🔍 Content preview: {repr(content[:100])}")
        
        # Test the parser directly
        print("🔍 Testing parser directly...")
        parser_module = source._parser_info["module"]
        parser_name = source._parser_info["name"]
        
        if parser_name in ("tomllib", "tomli"):
            print(f"🔍 Parser {parser_name} expects string for .loads(), content is {type(content)}")
            if isinstance(content, bytes):
                print("🔍 Converting bytes to string...")
                content_str = content.decode('utf-8')
                print(f"🔍 String content type: {type(content_str)}")
                print(f"🔍 String content preview: {repr(content_str[:100])}")
                
                print("🔍 Calling parser.loads() with string...")
                result = parser_module.loads(content_str)
                print(f"🔍 Parse result: {result}")
            else:
                print("🔍 Calling parser.loads() with existing string content...")
                result = parser_module.loads(content)
                print(f"🔍 Parse result: {result}")
        
        print("🔍 Now testing through TomlSource._parse_toml_content...")
        try:
            result = source._parse_toml_content(content)
            print(f"✅ Success! Result: {result}")
        except Exception as e:
            print(f"❌ Error in _parse_toml_content: {e}")
            print(f"❌ Error type: {type(e)}")
            
        print("🔍 Now testing full load...")
        try:
            result = source.load()
            print(f"✅ Full load success! Result: {result}")
        except Exception as e:
            print(f"❌ Error in full load: {e}")
            print(f"❌ Error type: {type(e)}")
            
    finally:
        # Clean up
        os.unlink(temp_file)

if __name__ == "__main__":
    debug_toml_parsing()

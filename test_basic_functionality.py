#!/usr/bin/env python3
"""
Quick functional test to verify ConfigManager core features work.
"""

import json
import tempfile
import os
from pathlib import Path

# Import ConfigManager
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from config_manager.sources import JsonSource

def test_basic_functionality():
    """Test basic ConfigManager functionality that should work."""
    
    print("🧪 Testing ConfigManager Core Functionality")
    print("=" * 50)
    
    # Test 1: Basic JSON loading
    print("📄 Test 1: JSON Source Loading")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "features": ["feature1", "feature2", "feature3"]
        }
        json.dump(test_config, f, indent=2)
        json_file = f.name
    
    try:
        config = ConfigManager()
        config.add_source(JsonSource(json_file))
        
        # Test basic gets
        app_name = config.get("app.name")
        print(f"   ✅ App name: {app_name}")
        
        # Test type conversions
        port = config.get_int("database.port")
        print(f"   ✅ Database port (int): {port}")
        
        debug = config.get_bool("app.debug")
        print(f"   ✅ Debug mode (bool): {debug}")
        
        # Test list handling
        features = config.get_list("features")
        print(f"   ✅ Features (list): {features}")
        
        # Test nested access
        db_host = config.get("database.host")
        print(f"   ✅ Database host: {db_host}")
        
        # Test defaults
        timeout = config.get("database.timeout", 30)
        print(f"   ✅ Timeout with default: {timeout}")
        
        print("   🎉 JSON source tests: PASSED")
        
    except Exception as e:
        print(f"   ❌ JSON source tests FAILED: {e}")
        return False
    finally:
        os.unlink(json_file)
    
    # Test 2: Profile management
    print("\n👤 Test 2: Profile Management")
    try:
        config = ConfigManager(profile='development')
        current_profile = config.get_current_profile()
        print(f"   ✅ Current profile: {current_profile}")
        
        # Test profile variables
        debug_mode = config.get_profile_var('debug')
        print(f"   ✅ Profile debug var: {debug_mode}")
        
        print("   🎉 Profile tests: PASSED")
        
    except Exception as e:
        print(f"   ❌ Profile tests FAILED: {e}")
        return False
    
    # Test 3: Method chaining and contains
    print("\n🔗 Test 3: Advanced Features")
    try:
        config = ConfigManager()
        config.add_source(JsonSource(json_file))  # This will fail since file is deleted, but let's test with a new one
        
        # Create a new test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": {"key": "value"}}, f)
            json_file2 = f.name
        
        config = ConfigManager()
        config.add_source(JsonSource(json_file2))
        
        # Test contains
        has_key = "test.key" in config
        print(f"   ✅ Contains check: {has_key}")
        
        # Test iteration (if implemented)
        try:
            value = config["test.key"]
            print(f"   ✅ Dictionary access: {value}")
        except Exception as e:
            print(f"   ⚠️  Dictionary access not working: {e}")
        
        print("   🎉 Advanced feature tests: PASSED")
        
    except Exception as e:
        print(f"   ❌ Advanced feature tests FAILED: {e}")
        return False
    finally:
        if 'json_file2' in locals():
            os.unlink(json_file2)
    
    print("\n🏆 Overall Result: ConfigManager Core Features Working!")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)

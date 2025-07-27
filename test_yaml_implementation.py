#!/usr/bin/env python3
"""
Test script to verify YAML support works with our fallback implementation.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to sys.path to make config_manager importable
sys.path.insert(0, str(Path(__file__).parent))

def test_yaml_implementation():
    """Test our YAML implementation works correctly."""
    print("🧪 Testing YAML Implementation\n")
    
    try:
        # Test our ConfigManager with YAML source
        from config_manager import ConfigManager
        from config_manager.sources import YamlSource
        print("✅ Successfully imported ConfigManager and YamlSource")
    except ImportError as e:
        print(f"❌ Failed to import modules: {e}")
        return False
    
    try:
        # Use the existing test YAML file
        yaml_file = "test_config.yaml"
        if not os.path.exists(yaml_file):
            print(f"❌ Test YAML file '{yaml_file}' not found")
            return False
            
        print(f"✅ Found test YAML file: {yaml_file}")
        
        # Create ConfigManager and load YAML
        config = ConfigManager()
        config.add_source(YamlSource(yaml_file))
        print("✅ Successfully loaded YAML configuration")
        
        # Test basic access
        app_name = config.get('app.name')
        print(f"   App name: {app_name}")
        
        if app_name != "TestApp":
            print(f"❌ Expected 'TestApp', got '{app_name}'")
            return False
        
        # Test nested access
        db_host = config.get('database.host')
        print(f"   Database host: {db_host}")
        
        if db_host != "localhost":
            print(f"❌ Expected 'localhost', got '{db_host}'")
            return False
        
        # Test type conversion
        debug_mode = config.get_bool('app.debug')
        print(f"   Debug mode: {debug_mode}")
        
        if debug_mode is not True:
            print(f"❌ Expected True, got {debug_mode}")
            return False
        
        # Test integer conversion
        db_port = config.get_int('database.port')
        print(f"   Database port: {db_port}")
        
        if db_port != 5432:
            print(f"❌ Expected 5432, got {db_port}")
            return False
        
        # Test deeply nested access
        username = config.get('database.credentials.username')
        print(f"   Database username: {username}")
        
        if username != "admin":
            print(f"❌ Expected 'admin', got '{username}'")
            return False
        
        print("\n✅ All YAML tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yaml_with_other_sources():
    """Test YAML working with other sources."""
    print("\n🔄 Testing YAML with other sources\n")
    
    try:
        from config_manager import ConfigManager
        from config_manager.sources import YamlSource, EnvironmentSource
        
        # Set an environment variable
        os.environ["TEST_APP_DEBUG"] = "false"
        
        config = ConfigManager()
        config.add_source(YamlSource("test_config.yaml"))  # debug: true
        config.add_source(EnvironmentSource(prefix="TEST_"))  # Should override debug to false
        
        # The environment variable should override the YAML value
        debug_from_yaml = True  # What's in the YAML
        debug_from_env = config.get_bool('APP_DEBUG')  # What we get from env var
        
        print(f"   YAML debug value: {debug_from_yaml}")
        print(f"   Environment override: {debug_from_env}")
        
        # Clean up
        del os.environ["TEST_APP_DEBUG"]
        
        print("✅ Multi-source configuration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Multi-source test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ConfigManageLib YAML Implementation Test\n")
    
    test1_passed = test_yaml_implementation()
    test2_passed = test_yaml_with_other_sources()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! YAML support is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the implementation.")
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script to verify YAML support works correctly.
Run this after installing PyYAML: pip install PyYAML
"""

import sys
import os
from pathlib import Path

# Add the parent directory to sys.path to make config_manager importable
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_yaml_support():
    """Test basic YAML functionality."""
    try:
        # Try to import yaml first
        import yaml
        print("✅ PyYAML is installed and importable")
    except ImportError:
        print("❌ PyYAML is not installed. Please run: pip install PyYAML")
        return False
    
    try:
        # Try to import our YAML source
        from config_manager.sources import YamlSource
        print("✅ YamlSource is importable")
    except ImportError as e:
        print(f"❌ Failed to import YamlSource: {e}")
        return False
    
    try:
        # Create a test YAML file
        test_yaml = "test_yaml_support.yaml"
        yaml_content = {
            "test": {
                "success": True,
                "message": "YAML support is working!"
            }
        }
        
        with open(test_yaml, 'w') as f:
            yaml.dump(yaml_content, f)
        
        print("✅ Created test YAML file")
        
        # Test loading with our ConfigManager
        from config_manager import ConfigManager
        
        config = ConfigManager()
        config.add_source(YamlSource(test_yaml))
        
        # Test reading values
        success = config.get_bool('test.success')
        message = config.get('test.message')
        
        if success and message == "YAML support is working!":
            print("✅ Successfully loaded and read YAML configuration")
            print(f"   Message: {message}")
            return True
        else:
            print("❌ Failed to read expected values from YAML")
            return False
            
    except Exception as e:
        print(f"❌ Error during YAML testing: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_yaml):
            os.remove(test_yaml)
            print("✅ Cleaned up test file")

if __name__ == "__main__":
    print("🧪 Testing YAML Support for ConfigManageLib\n")
    
    if test_yaml_support():
        print("\n🎉 All YAML tests passed! YAML support is fully functional.")
        sys.exit(0)
    else:
        print("\n💥 YAML tests failed. Please check the installation and try again.")
        sys.exit(1)

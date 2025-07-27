#!/usr/bin/env python3
"""
Test ConfigManager integration with enterprise cache.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_integration():
    """Test ConfigManager with enterprise cache integration."""
    try:
        from config_manager import ConfigManager
        print("✅ ConfigManager import successful")
        
        # Create ConfigManager instance
        cm = ConfigManager()
        print("✅ ConfigManager initialization successful")
        
        # Test ConfigManager's caching methods
        print("Testing ConfigManager caching interface...")
        
        # Test cache stats (this should work if caching is integrated)
        stats = cm.get_cache_stats()
        print(f"Cache stats type: {type(stats)}")
        print(f"Cache enabled: {cm.is_caching_enabled()}")
        
        # Test cache enable/disable
        cm.enable_caching()
        print("✅ Cache enable successful")
        
        cm.disable_caching()
        print("✅ Cache disable successful")
        
        cm.enable_caching()
        print("✅ Cache re-enable successful")
        
        # Test cache clear
        cm.clear_cache()
        print("✅ Cache clear successful")
        
        print("✅ ConfigManager enterprise cache integration working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integration()
    print(f"\nIntegration test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Simple test of the caching functionality.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager.cache import MemoryCache, ConfigCache, create_cache_key

def test_cache_key():
    """Test cache key generation."""
    key = create_cache_key("test", "data")
    print(f"Cache key: {key}")
    assert "test:data:" in key
    print("✓ Cache key test passed")

def test_memory_cache():
    """Test memory cache basic operations."""
    cache = MemoryCache(max_size=3, default_ttl=60.0)
    
    # Test set and get
    cache.set("key1", "value1")
    value = cache.get("key1")
    assert value == "value1"
    print("✓ Memory cache set/get test passed")
    
    # Test has_key
    assert cache.has_key("key1")
    assert not cache.has_key("nonexistent")
    print("✓ Memory cache has_key test passed")
    
    # Test delete
    cache.delete("key1")
    assert not cache.has_key("key1")
    print("✓ Memory cache delete test passed")

def test_config_cache():
    """Test config cache operations."""
    cache = ConfigCache(MemoryCache(max_size=10))
    
    # Test cache config
    config_data = {"test": "data", "nested": {"value": 42}}
    cache.cache_config("source1", config_data)
    
    # Test get config
    retrieved = cache.get_config("source1")
    assert retrieved == config_data
    print("✓ Config cache operations test passed")
    
    # Test invalidation
    cache.invalidate("source1")
    assert cache.get_config("source1") is None
    print("✓ Config cache invalidation test passed")

def main():
    """Run all tests."""
    print("Testing ConfigManager caching functionality...")
    
    try:
        test_cache_key()
        test_memory_cache()
        test_config_cache()
        
        print("\n🎉 All cache tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

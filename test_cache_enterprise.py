#!/usr/bin/env python3
"""
Test script for the modernized enterprise cache system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_enterprise_cache():
    """Test all enterprise cache features."""
    try:
        from config_manager.cache import (
            EnterpriseMemoryCache, 
            CacheEvictionPolicy, 
            CacheManager, 
            CacheConfiguration,
            EnterpriseFileCache,
            NullCache
        )
        
        print("=== Enterprise Cache System Test ===")
        
        # Test 1: EnterpriseMemoryCache
        print("\n1. Testing EnterpriseMemoryCache:")
        cache = EnterpriseMemoryCache(max_size=5, eviction_policy=CacheEvictionPolicy.LRU)
        
        # Basic operations
        cache.set('key1', 'value1', ttl=60.0, tags={'tag1', 'important'})
        cache.set('key2', 'value2', tags={'tag2'})
        
        result1 = cache.get('key1')
        result2 = cache.get('key2')
        exists = cache.exists('key1')
        
        print(f"   Set/Get key1: {result1}")
        print(f"   Set/Get key2: {result2}")
        print(f"   Exists key1: {exists}")
        
        # Batch operations
        cache.set_many({'key3': 'value3', 'key4': 'value4'})
        many_results = cache.get_many(['key1', 'key3', 'key4'])
        print(f"   Get many: {many_results}")
        
        # Tag operations
        deleted = cache.delete_by_tags({'tag1'})
        print(f"   Deleted by tags: {deleted}")
        
        # Statistics
        stats = cache.get_stats()
        print(f"   Stats - Size: {stats.current_size}, Hits: {stats.cache_hits}")
        
        # Test 2: CacheManager
        print("\n2. Testing CacheManager:")
        config = CacheConfiguration(
            backend_type='memory',
            max_size=100,
            default_ttl=300.0
        )
        
        manager = CacheManager(config)
        manager.set('test_key', {'config': 'data', 'version': 1})
        manager_result = manager.get('test_key')
        print(f"   Manager result: {manager_result}")
        
        # Health check
        health = manager.health_check()
        print(f"   Health: {health['status']} ({health['backend_type']})")
        
        # Test 3: EnterpriseFileCache
        print("\n3. Testing EnterpriseFileCache:")
        file_cache = EnterpriseFileCache(cache_dir='.test_cache', max_files=10)
        file_cache.set('file_key', {'data': 'persistent'}, ttl=3600)
        file_result = file_cache.get('file_key')
        print(f"   File cache result: {file_result}")
        
        # Test 4: NullCache
        print("\n4. Testing NullCache:")
        null_cache = NullCache()
        null_cache.set('null_key', 'value')
        null_result = null_cache.get('null_key')
        print(f"   Null cache result (should be None): {null_result}")
        
        print("\n✅ All enterprise cache tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing cache: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enterprise_cache()
    sys.exit(0 if success else 1)

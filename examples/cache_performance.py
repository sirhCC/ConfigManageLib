"""
Configuration Caching Performance Example

This example demonstrates the performance benefits of caching
in the ConfigManager library.
"""

import time
import tempfile
import json
import os
from typing import Dict, Any

from config_manager import ConfigManager
from config_manager.cache import ConfigCache, MemoryCache, FileCache
from config_manager.sources import JsonSource


def create_test_config_file(path: str, size: int = 1000) -> None:
    """Create a test configuration file with specified size."""
    config_data = {
        f"key_{i}": f"value_{i}" for i in range(size)
    }
    config_data.update({
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "credentials": {
                "username": "user",
                "password": "secret"
            }
        },
        "api": {
            "base_url": "https://api.example.com",
            "timeout": 30,
            "retries": 3
        },
        "features": {
            "caching": True,
            "logging": True,
            "monitoring": False
        }
    })
    
    with open(path, 'w') as f:
        json.dump(config_data, f, indent=2)


class SlowConfigSource:
    """A configuration source that simulates slow loading (e.g., remote API)."""
    
    def __init__(self, config_data: Dict[str, Any], delay: float = 0.1):
        """
        Initialize slow config source.
        
        Args:
            config_data: Configuration data to return.
            delay: Artificial delay in seconds.
        """
        self.config_data = config_data
        self.delay = delay
        self.load_count = 0
    
    def load(self) -> Dict[str, Any]:
        """Load configuration with artificial delay."""
        self.load_count += 1
        print(f"Loading configuration (attempt #{self.load_count})...")
        time.sleep(self.delay)
        return self.config_data.copy()


def demonstrate_memory_cache():
    """Demonstrate memory cache performance."""
    print("=" * 60)
    print("MEMORY CACHE DEMONSTRATION")
    print("=" * 60)
    
    # Create test configuration
    config_data = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }
    
    # Create slow source
    slow_source = SlowConfigSource(config_data, delay=0.2)
    
    # Test without caching
    print("\n1. Without caching:")
    cm_no_cache = ConfigManager(enable_caching=False)
    cm_no_cache.add_source(slow_source)
    
    start_time = time.time()
    config1 = cm_no_cache.get_config()
    time1 = time.time() - start_time
    
    start_time = time.time()
    config2 = cm_no_cache.get_config()
    time2 = time.time() - start_time
    
    print(f"   First load:  {time1:.3f} seconds")
    print(f"   Second load: {time2:.3f} seconds")
    print(f"   Source called: {slow_source.load_count} times")
    
    # Reset for cache test
    slow_source.load_count = 0
    slow_source_cached = SlowConfigSource(config_data, delay=0.2)
    
    # Test with caching
    print("\n2. With memory caching:")
    cache = ConfigCache(MemoryCache(default_ttl=60.0))
    cm_with_cache = ConfigManager(cache=cache)
    cm_with_cache.add_source(slow_source_cached)
    
    start_time = time.time()
    config1 = cm_with_cache.get_config()
    time1 = time.time() - start_time
    
    start_time = time.time()
    config2 = cm_with_cache.get_config()
    time2 = time.time() - start_time
    
    print(f"   First load:  {time1:.3f} seconds")
    print(f"   Second load: {time2:.3f} seconds (from cache)")
    print(f"   Source called: {slow_source_cached.load_count} times")
    print(f"   Speed improvement: {time1/time2:.1f}x faster")
    
    # Show cache statistics
    stats = cm_with_cache.get_cache_stats()
    print(f"\n   Cache Statistics:")
    print(f"   - Hits: {stats['hits']}")
    print(f"   - Misses: {stats['misses']}")
    print(f"   - Hit Ratio: {stats['hit_ratio']:.1%}")


def demonstrate_file_cache():
    """Demonstrate file cache persistence."""
    print("\n" + "=" * 60)
    print("FILE CACHE DEMONSTRATION")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "config.json")
        cache_dir = os.path.join(temp_dir, "cache")
        
        # Create test config file
        create_test_config_file(config_file, size=500)
        
        print(f"\n1. Creating file cache in: {cache_dir}")
        
        # Test file cache persistence
        cache = ConfigCache(FileCache(cache_dir=cache_dir, default_ttl=300.0))
        cm1 = ConfigManager(cache=cache)
        cm1.add_source(JsonSource(config_file))
        
        print("   Loading configuration (first time)...")
        start_time = time.time()
        config1 = cm1.get_config()
        time1 = time.time() - start_time
        print(f"   Load time: {time1:.3f} seconds")
        
        # Create new ConfigManager instance (simulating app restart)
        print("\n2. Simulating application restart...")
        cache2 = ConfigCache(FileCache(cache_dir=cache_dir, default_ttl=300.0))
        cm2 = ConfigManager(cache=cache2)
        cm2.add_source(JsonSource(config_file))
        
        print("   Loading configuration (from persistent cache)...")
        start_time = time.time()
        config2 = cm2.get_config()
        time2 = time.time() - start_time
        print(f"   Load time: {time2:.3f} seconds")
        
        print(f"   Cache persistence works: {config1 == config2}")
        print(f"   Speed improvement: {time1/time2:.1f}x faster")
        
        # Show cache statistics
        stats = cm2.get_cache_stats()
        print(f"\n   Cache Statistics:")
        print(f"   - Cache enabled: {stats['enabled']}")
        print(f"   - Backend type: {stats.get('backend_stats', {}).get('type', 'unknown')}")


def demonstrate_cache_invalidation():
    """Demonstrate cache invalidation when files change."""
    print("\n" + "=" * 60)
    print("CACHE INVALIDATION DEMONSTRATION")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "config.json")
        
        # Create initial config
        initial_config = {"version": "1.0", "feature_x": False}
        with open(config_file, 'w') as f:
            json.dump(initial_config, f)
        
        # Setup ConfigManager with caching
        cache = ConfigCache(MemoryCache(default_ttl=300.0))
        cm = ConfigManager(cache=cache)
        cm.add_source(JsonSource(config_file))
        
        print("1. Loading initial configuration...")
        config1 = cm.get_config()
        print(f"   Version: {config1['version']}")
        print(f"   Feature X: {config1['feature_x']}")
        
        # Wait a moment to ensure different mtime
        time.sleep(0.01)
        
        # Modify the config file
        print("\n2. Modifying configuration file...")
        updated_config = {"version": "2.0", "feature_x": True}
        with open(config_file, 'w') as f:
            json.dump(updated_config, f)
        
        # Reload - should detect file change
        print("3. Reloading configuration...")
        cm.reload()
        config2 = cm.get_config()
        print(f"   Version: {config2['version']}")
        print(f"   Feature X: {config2['feature_x']}")
        
        print(f"\n   Cache invalidation works: {config1 != config2}")
        
        # Show cache statistics
        stats = cm.get_cache_stats()
        print(f"\n   Cache Statistics:")
        print(f"   - Total hits: {stats['hits']}")
        print(f"   - Total misses: {stats['misses']}")


def demonstrate_cache_backends():
    """Compare different cache backends."""
    print("\n" + "=" * 60)
    print("CACHE BACKEND COMPARISON")
    print("=" * 60)
    
    # Test data
    config_data = {"test": "data", "numbers": list(range(100))}
    
    backends = [
        ("Memory Cache", MemoryCache(max_size=10, default_ttl=60.0)),
        ("File Cache", FileCache(default_ttl=60.0)),
    ]
    
    for name, backend in backends:
        print(f"\n{name}:")
        cache = ConfigCache(backend=backend)
        
        # Test basic operations
        start_time = time.time()
        cache.set("test_key", config_data)
        set_time = time.time() - start_time
        
        start_time = time.time()
        retrieved_data = cache.get("test_key")
        get_time = time.time() - start_time
        
        print(f"   Set time: {set_time:.6f} seconds")
        print(f"   Get time: {get_time:.6f} seconds")
        print(f"   Data integrity: {config_data == retrieved_data}")
        
        # Show backend-specific stats
        stats = cache.get_stats()
        if 'backend_stats' in stats:
            backend_stats = stats['backend_stats']
            print(f"   Backend stats: {backend_stats}")


def main():
    """Run all cache demonstrations."""
    print("ConfigManager Caching Performance Demonstration")
    print("This example shows how caching improves configuration loading performance.")
    
    try:
        demonstrate_memory_cache()
        demonstrate_file_cache()
        demonstrate_cache_invalidation()
        demonstrate_cache_backends()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("✓ Memory caching provides significant speed improvements")
        print("✓ File caching enables persistence across application restarts")
        print("✓ Cache invalidation ensures data consistency when files change")
        print("✓ Multiple cache backends support different use cases")
        print("\nCaching is now enabled by default in ConfigManager!")
        
    except Exception as e:
        print(f"Error running cache demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

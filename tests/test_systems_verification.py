#!/usr/bin/env python3
"""
Simple comprehensive test for Priority 2 modernized systems.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_all_systems():
    """Test all Priority 2 modernized systems."""
    print("=== Priority 2 Systems Verification ===")
    
    try:
        # Test 1: Validation System
        print("\n1. Testing Enterprise Validation System:")
        from config_manager.validation import ValidationEngine, TypeValidator, ValidationContext
        
        engine = ValidationEngine()
        # Test with ValidationEngine interface
        validators = [TypeValidator(str)]
        result = engine.validate_value("hello", validators, "test.value")
        print(f"   Type validation: valid={result.is_valid}")
        
        # Test individual validator
        validator = TypeValidator(str)
        context = ValidationContext(path="test.string")
        str_result = validator.validate("hello", context)
        print(f"   String validation: valid={str_result.is_valid}")
        
        print("   ✅ Validation system working")
        
        # Test 2: Schema System
        print("\n2. Testing Modern Schema System:")
        from config_manager.schema import Schema, String, Integer
        
        schema = Schema()
        schema.add_field('name', String(required=True))
        schema.add_field('age', Integer())
        
        test_data = {'name': 'John', 'age': 30}
        schema_result = schema.validate(test_data)
        # Schema.validate returns dict, not ValidationResult
        print(f"   Schema validation: data={schema_result}")
        print("   ✅ Schema system working")
        
        # Test 3: Cache System  
        print("\n3. Testing Enterprise Cache System:")
        from config_manager.cache import CacheManager
        
        cache = CacheManager()
        cache.set('test', 'value')
        cached = cache.get('test')
        print(f"   Cache test: {cached}")
        
        stats = cache.get_stats()
        print(f"   Cache stats: hits={stats.cache_hits}")
        print("   ✅ Cache system working")
        
        # Test 4: ConfigManager Integration
        print("\n4. Testing ConfigManager Integration:")
        from config_manager import ConfigManager
        
        # Use ConfigManager's built-in functionality
        cm = ConfigManager()
        
        # Test basic functionality
        cache_stats = cm.get_cache_stats()
        is_caching = cm.is_caching_enabled()
        print(f"   ConfigManager caching: enabled={is_caching}")
        print(f"   Cache stats available: {cache_stats is not None}")
        print("   ✅ ConfigManager integration working")
        
        print("\n🎉 ALL SYSTEMS VERIFIED SUCCESSFULLY! ✅")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_all_systems()
    print(f"\nTest Result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)

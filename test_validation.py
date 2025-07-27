#!/usr/bin/env python3
"""Test script for modernized validation system."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config_manager.validation import (
    ValidationLevel, ValidationContext, ValidationResult, ValidationError,
    Validator, TypeValidator, RequiredValidator, RangeValidator, 
    ChoicesValidator, RegexValidator, LengthValidator, EmailValidator,
    URLValidator, CustomValidator, CompositeValidator, ValidationEngine
)

def test_type_validator():
    """Test the modernized TypeValidator."""
    print("🔍 Testing TypeValidator...")
    
    # Test basic type validation
    validator = TypeValidator(int, convert=True)
    context = ValidationContext(path="test.value")
    
    # Test string to int conversion
    result = validator.validate("123", context)
    print(f"  String '123' -> int: {result.value} (valid: {result.is_valid})")
    
    # Test boolean conversion
    bool_validator = TypeValidator(bool, convert=True)
    result = bool_validator.validate("true", context)
    print(f"  String 'true' -> bool: {result.value} (valid: {result.is_valid})")
    
    # Test failed conversion
    result = validator.validate("abc", context)
    print(f"  String 'abc' -> int: valid={result.is_valid}, errors={result.errors}")

def test_composite_validator():
    """Test the CompositeValidator."""
    print("🔍 Testing CompositeValidator...")
    
    validators = [
        RequiredValidator(),
        TypeValidator(int, convert=True),
        RangeValidator(min_value=1, max_value=100)
    ]
    
    composite = CompositeValidator(validators)
    context = ValidationContext(path="test.composite")
    
    # Test valid value
    result = composite.validate("50", context)
    print(f"  Value '50': {result.value} (valid: {result.is_valid})")
    
    # Test invalid value
    result = composite.validate("150", context)
    print(f"  Value '150': valid={result.is_valid}, errors={result.errors}")

def test_validation_engine():
    """Test the ValidationEngine."""
    print("🔍 Testing ValidationEngine...")
    
    engine = ValidationEngine(level=ValidationLevel.LENIENT)
    
    validators = [
        TypeValidator(str),
        LengthValidator(min_length=3, max_length=20)
    ]
    
    result = engine.validate_value("hello", validators, "test.string")
    print(f"  String 'hello': valid={result.is_valid}")
    
    result = engine.validate_value("a", validators, "test.string")
    print(f"  String 'a': valid={result.is_valid}, errors={result.errors}")

def test_email_validator():
    """Test the EmailValidator."""
    print("🔍 Testing EmailValidator...")
    
    validator = EmailValidator()
    context = ValidationContext(path="test.email")
    
    result = validator.validate("user@example.com", context)
    print(f"  'user@example.com': valid={result.is_valid}")
    
    result = validator.validate("invalid-email", context)
    print(f"  'invalid-email': valid={result.is_valid}, errors={result.errors}")

def main():
    """Run all validation tests."""
    print("🚀 Testing Modernized Validation System")
    print("=" * 50)
    
    try:
        test_type_validator()
        print()
        test_composite_validator()
        print()
        test_validation_engine()
        print()
        test_email_validator()
        print()
        
        print("✅ All validation tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

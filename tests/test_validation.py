"""Tests for the validation system."""

import unittest
import re
from config_manager.validation import (
    ValidationError,
    TypeValidator,
    RequiredValidator,
    RangeValidator,
    ChoicesValidator,
    RegexValidator,
    LengthValidator,
    CustomValidator
)


class TestValidationError(unittest.TestCase):
    """Test the ValidationError exception."""
    
    def test_simple_error(self):
        """Test creating a simple validation error."""
        error = ValidationError("Test error", "field1")
        self.assertEqual(str(error), "Validation error at 'field1': Test error")
        self.assertEqual(error.path, "field1")
        self.assertEqual(error.message, "Test error")
    
    def test_error_without_field(self):
        """Test creating an error without a field name."""
        error = ValidationError("General error")
        self.assertEqual(str(error), "Validation error: General error")
        self.assertEqual(error.path, "")
        self.assertEqual(error.message, "General error")


class TestTypeValidator(unittest.TestCase):
    """Test the TypeValidator."""
    
    def test_string_validation(self):
        """Test string type validation."""
        validator = TypeValidator(str)
        
        # Valid strings
        self.assertEqual(validator.validate("hello"), "hello")
        self.assertEqual(validator.validate(""), "")
        
        # Type conversion
        self.assertEqual(validator.validate(123), "123")
        self.assertEqual(validator.validate(45.67), "45.67")
        self.assertEqual(validator.validate(True), "True")
    
    def test_int_validation(self):
        """Test integer type validation."""
        validator = TypeValidator(int)
        
        # Valid integers
        self.assertEqual(validator.validate(123), 123)
        self.assertEqual(validator.validate(0), 0)
        self.assertEqual(validator.validate(-456), -456)
        
        # Type conversion
        self.assertEqual(validator.validate("789"), 789)
        self.assertEqual(validator.validate(12.0), 12)
        self.assertEqual(validator.validate(True), 1)
        
        # Invalid conversion
        with self.assertRaises(ValidationError):
            validator.validate("not a number")
    
    def test_float_validation(self):
        """Test float type validation."""
        validator = TypeValidator(float)
        
        # Valid floats
        self.assertEqual(validator.validate(123.45), 123.45)
        self.assertEqual(validator.validate(0.0), 0.0)
        self.assertEqual(validator.validate(-456.78), -456.78)
        
        # Type conversion
        self.assertEqual(validator.validate("789.12"), 789.12)
        self.assertEqual(validator.validate(12), 12.0)
        
        # Invalid conversion
        with self.assertRaises(ValidationError):
            validator.validate("not a number")
    
    def test_bool_validation(self):
        """Test boolean type validation."""
        validator = TypeValidator(bool)
        
        # Valid booleans
        self.assertTrue(validator.validate(True))
        self.assertFalse(validator.validate(False))
        
        # String conversion
        self.assertTrue(validator.validate("true"))
        self.assertTrue(validator.validate("True"))
        self.assertTrue(validator.validate("TRUE"))
        self.assertTrue(validator.validate("yes"))
        self.assertTrue(validator.validate("1"))
        
        self.assertFalse(validator.validate("false"))
        self.assertFalse(validator.validate("False"))
        self.assertFalse(validator.validate("FALSE"))
        self.assertFalse(validator.validate("no"))
        self.assertFalse(validator.validate("0"))
        
        # Invalid conversion
        with self.assertRaises(ValidationError):
            validator.validate("maybe")
    
    def test_list_validation(self):
        """Test list type validation."""
        validator = TypeValidator(list)
        
        # Valid lists
        self.assertEqual(validator.validate([1, 2, 3]), [1, 2, 3])
        self.assertEqual(validator.validate([]), [])
        
        # String conversion (comma-separated)
        self.assertEqual(validator.validate("a,b,c"), ["a", "b", "c"])
        self.assertEqual(validator.validate("1,2,3"), ["1", "2", "3"])
        self.assertEqual(validator.validate(""), [])
        
        # Invalid types
        with self.assertRaises(ValidationError):
            validator.validate(123)


class TestRequiredValidator(unittest.TestCase):
    """Test the RequiredValidator."""
    
    def test_required_validation(self):
        """Test required field validation."""
        validator = RequiredValidator()
        
        # Valid values
        self.assertEqual(validator.validate("hello"), "hello")
        self.assertEqual(validator.validate(0), 0)
        self.assertEqual(validator.validate(False), False)
        self.assertEqual(validator.validate([]), [])
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate(None)
        
        with self.assertRaises(ValidationError):
            validator.validate("")


class TestRangeValidator(unittest.TestCase):
    """Test the RangeValidator."""
    
    def test_min_only(self):
        """Test validation with minimum only."""
        validator = RangeValidator(min_value=5)
        
        # Valid values
        self.assertEqual(validator.validate(5), 5)
        self.assertEqual(validator.validate(10), 10)
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate(4)
    
    def test_max_only(self):
        """Test validation with maximum only."""
        validator = RangeValidator(max_value=10)
        
        # Valid values
        self.assertEqual(validator.validate(5), 5)
        self.assertEqual(validator.validate(10), 10)
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate(11)
    
    def test_min_and_max(self):
        """Test validation with both minimum and maximum."""
        validator = RangeValidator(min_value=5, max_value=10)
        
        # Valid values
        self.assertEqual(validator.validate(5), 5)
        self.assertEqual(validator.validate(7), 7)
        self.assertEqual(validator.validate(10), 10)
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate(4)
        
        with self.assertRaises(ValidationError):
            validator.validate(11)
    
    def test_no_range(self):
        """Test validation with no range constraints."""
        validator = RangeValidator()
        
        # All values should be valid
        self.assertEqual(validator.validate(-100), -100)
        self.assertEqual(validator.validate(0), 0)
        self.assertEqual(validator.validate(100), 100)


class TestChoicesValidator(unittest.TestCase):
    """Test the ChoicesValidator."""
    
    def test_valid_choices(self):
        """Test validation with valid choices."""
        validator = ChoicesValidator(["red", "green", "blue"])
        
        # Valid choices
        self.assertEqual(validator.validate("red"), "red")
        self.assertEqual(validator.validate("green"), "green")
        self.assertEqual(validator.validate("blue"), "blue")
        
        # Invalid choices
        with self.assertRaises(ValidationError):
            validator.validate("yellow")
    
    def test_mixed_type_choices(self):
        """Test validation with mixed type choices."""
        validator = ChoicesValidator([1, "two", 3.0])
        
        # Valid choices
        self.assertEqual(validator.validate(1), 1)
        self.assertEqual(validator.validate("two"), "two")
        self.assertEqual(validator.validate(3.0), 3.0)
        
        # Invalid choices
        with self.assertRaises(ValidationError):
            validator.validate(2)


class TestRegexValidator(unittest.TestCase):
    """Test the RegexValidator."""
    
    def test_string_pattern(self):
        """Test validation with string pattern."""
        validator = RegexValidator(r"^\d{3}-\d{3}-\d{4}$")
        
        # Valid patterns
        self.assertEqual(validator.validate("123-456-7890"), "123-456-7890")
        
        # Invalid patterns
        with self.assertRaises(ValidationError):
            validator.validate("123-45-7890")
        
        with self.assertRaises(ValidationError):
            validator.validate("not-a-phone")
    
    def test_compiled_pattern(self):
        """Test validation with compiled regex pattern."""
        validator = RegexValidator(r"^[a-z]+$")
        
        # Valid patterns
        self.assertEqual(validator.validate("hello"), "hello")
        
        # Invalid patterns
        with self.assertRaises(ValidationError):
            validator.validate("Hello")
        
        with self.assertRaises(ValidationError):
            validator.validate("hello123")


class TestLengthValidator(unittest.TestCase):
    """Test the LengthValidator."""
    
    def test_min_length_only(self):
        """Test validation with minimum length only."""
        validator = LengthValidator(min_length=3)
        
        # Valid lengths
        self.assertEqual(validator.validate("abc"), "abc")
        self.assertEqual(validator.validate("abcd"), "abcd")
        self.assertEqual(validator.validate([1, 2, 3]), [1, 2, 3])
        
        # Invalid lengths
        with self.assertRaises(ValidationError):
            validator.validate("ab")
        
        with self.assertRaises(ValidationError):
            validator.validate([1, 2])
    
    def test_max_length_only(self):
        """Test validation with maximum length only."""
        validator = LengthValidator(max_length=5)
        
        # Valid lengths
        self.assertEqual(validator.validate("abc"), "abc")
        self.assertEqual(validator.validate("abcde"), "abcde")
        self.assertEqual(validator.validate([1, 2, 3]), [1, 2, 3])
        
        # Invalid lengths
        with self.assertRaises(ValidationError):
            validator.validate("abcdef")
        
        with self.assertRaises(ValidationError):
            validator.validate([1, 2, 3, 4, 5, 6])
    
    def test_min_and_max_length(self):
        """Test validation with both minimum and maximum length."""
        validator = LengthValidator(min_length=3, max_length=5)
        
        # Valid lengths
        self.assertEqual(validator.validate("abc"), "abc")
        self.assertEqual(validator.validate("abcd"), "abcd")
        self.assertEqual(validator.validate("abcde"), "abcde")
        
        # Invalid lengths
        with self.assertRaises(ValidationError):
            validator.validate("ab")
        
        with self.assertRaises(ValidationError):
            validator.validate("abcdef")


class TestCustomValidator(unittest.TestCase):
    """Test the CustomValidator."""
    
    def test_simple_function(self):
        """Test validation with a simple function."""
        def is_even(value):
            if value % 2 != 0:
                raise ValidationError(f"Value {value} is not even")
            return value
        
        validator = CustomValidator(is_even)
        
        # Valid values
        self.assertEqual(validator.validate(2), 2)
        self.assertEqual(validator.validate(4), 4)
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate(3)
    
    def test_function_with_transformation(self):
        """Test validation with a function that transforms the value."""
        def upper_and_validate(value):
            if not isinstance(value, str):
                raise ValidationError("Value must be a string")
            result = value.upper()
            if len(result) < 3:
                raise ValidationError("Uppercased value must be at least 3 characters")
            return result
        
        validator = CustomValidator(upper_and_validate)
        
        # Valid values
        self.assertEqual(validator.validate("hello"), "HELLO")
        self.assertEqual(validator.validate("abc"), "ABC")
        
        # Invalid values
        with self.assertRaises(ValidationError):
            validator.validate("ab")
        
        with self.assertRaises(ValidationError):
            validator.validate(123)


if __name__ == '__main__':
    unittest.main()

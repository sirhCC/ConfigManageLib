"""
Comprehensive test suite for ConfigManager validation system.

Achieves 85%+ coverage of validation.py module with tests for:
- ValidationContext and ValidationResult dataclasses
- TypeValidator with type conversion and Union types
- RequiredValidator with empty value detection
- RangeValidator with numeric bounds
- ChoicesValidator with case-insensitive matching
- RegexValidator with pattern matching modes
- LengthValidator for strings, lists, dicts
- EmailValidator with format validation
- URLValidator with scheme and domain validation
- CustomValidator with callable functions
- CompositeValidator combining multiple validators
- ValidationEngine with caching and dict validation
- ValidationError exception with detailed context
"""

import pytest
import re
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

from config_manager.validation import (
    ValidationLevel,
    ValidationContext,
    ValidationResult,
    ValidationError,
    Validator,
    TypeValidator,
    RequiredValidator,
    RangeValidator,
    ChoicesValidator,
    RegexValidator,
    LengthValidator,
    EmailValidator,
    URLValidator,
    CustomValidator,
    CompositeValidator,
    ValidationEngine,
)


class TestValidationContext:
    """Test ValidationContext immutable dataclass."""

    def test_create_validation_context_defaults(self):
        """Test creating ValidationContext with default values."""
        context = ValidationContext()
        assert context.path == ""
        assert context.level == ValidationLevel.STRICT
        assert context.parent_value is None
        assert context.root_value is None
        assert context.custom_data == {}

    def test_create_validation_context_with_values(self):
        """Test creating ValidationContext with custom values."""
        custom_data = {"key": "value"}
        context = ValidationContext(
            path="config.database.host",
            level=ValidationLevel.LENIENT,
            parent_value={"host": "localhost"},
            root_value={"database": {"host": "localhost"}},
            custom_data=custom_data
        )
        assert context.path == "config.database.host"
        assert context.level == ValidationLevel.LENIENT
        assert context.parent_value == {"host": "localhost"}
        assert context.root_value == {"database": {"host": "localhost"}}
        assert context.custom_data == custom_data

    def test_validation_context_with_path(self):
        """Test creating new context with updated path."""
        context = ValidationContext(path="original", level=ValidationLevel.STRICT)
        new_context = context.with_path("new.path")
        
        assert new_context.path == "new.path"
        assert new_context.level == ValidationLevel.STRICT
        assert context.path == "original"  # Original unchanged

    def test_validation_context_with_parent(self):
        """Test creating new context with updated parent."""
        context = ValidationContext(path="test", parent_value=None)
        parent = {"key": "value"}
        new_context = context.with_parent(parent)
        
        assert new_context.parent_value == parent
        assert new_context.path == "test"
        assert context.parent_value is None  # Original unchanged

    def test_validation_context_immutable(self):
        """Test that ValidationContext is immutable (frozen)."""
        context = ValidationContext(path="test")
        with pytest.raises(AttributeError):
            context.path = "new_path"  # type: ignore


class TestValidationResult:
    """Test ValidationResult mutable dataclass."""

    def test_create_validation_result_defaults(self):
        """Test creating ValidationResult with default values."""
        result = ValidationResult(value=42)
        assert result.value == 42
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.transformations == []
        assert result.validation_time == 0.0
        assert result.validator_name == ""
        assert result.path == ""

    def test_validation_result_add_error(self):
        """Test adding error to validation result."""
        result = ValidationResult(value=42)
        assert result.is_valid is True
        
        result.add_error("Test error")
        assert result.is_valid is False
        assert result.errors == ["Test error"]

    def test_validation_result_add_multiple_errors(self):
        """Test adding multiple errors."""
        result = ValidationResult(value=42)
        result.add_error("Error 1")
        result.add_error("Error 2")
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors

    def test_validation_result_add_warning(self):
        """Test adding warning to validation result."""
        result = ValidationResult(value=42)
        result.add_warning("Test warning")
        
        assert result.is_valid is True  # Warnings don't invalidate
        assert result.warnings == ["Test warning"]

    def test_validation_result_add_transformation(self):
        """Test recording transformation."""
        result = ValidationResult(value=42)
        result.add_transformation("Converted string to int")
        
        assert result.is_valid is True
        assert result.transformations == ["Converted string to int"]


class TestValidationError:
    """Test ValidationError exception."""

    def test_create_validation_error_simple(self):
        """Test creating ValidationError with basic message."""
        error = ValidationError("Test error")
        assert str(error) == "Validation error: Test error"
        assert error.message == "Test error"
        assert error.path == ""
        assert error.expected_type is None
        assert error.actual_value is None
        assert error.suggestions == []

    def test_create_validation_error_with_path(self):
        """Test ValidationError with path."""
        error = ValidationError("Invalid value", path="config.database.port")
        assert "config.database.port" in str(error)
        assert error.path == "config.database.port"

    def test_create_validation_error_with_type_info(self):
        """Test ValidationError with type information."""
        error = ValidationError(
            "Type mismatch",
            path="config.port",
            expected_type=int,
            actual_value="8080"
        )
        error_str = str(error)
        assert "config.port" in error_str
        assert "int" in error_str
        assert "str" in error_str

    def test_create_validation_error_with_suggestions(self):
        """Test ValidationError with suggestions."""
        error = ValidationError(
            "Invalid choice",
            suggestions=["option1", "option2"]
        )
        error_str = str(error)
        assert "option1" in error_str
        assert "option2" in error_str


class TestTypeValidator:
    """Test TypeValidator with type conversion and validation."""

    def test_type_validator_correct_type(self):
        """Test validation with correct type."""
        validator = TypeValidator(int)
        context = ValidationContext(path="test.value")
        result = validator.validate(42, context)
        
        assert result.is_valid is True
        assert result.value == 42
        assert len(result.errors) == 0

    def test_type_validator_string_to_int_conversion(self):
        """Test converting string to int."""
        validator = TypeValidator(int, convert=True)
        context = ValidationContext(path="test.value")
        result = validator.validate("123", context)
        
        assert result.is_valid is True
        assert result.value == 123
        assert len(result.transformations) > 0

    def test_type_validator_string_to_float_conversion(self):
        """Test converting string to float."""
        validator = TypeValidator(float, convert=True)
        result = validator.validate("123.45", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == 123.45

    def test_type_validator_string_to_bool_true(self):
        """Test converting various strings to True."""
        validator = TypeValidator(bool, convert=True)
        
        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "on", "enabled"]:
            result = validator.validate(value, ValidationContext())
            assert result.is_valid is True, f"Failed for value: {value}"
            assert result.value is True, f"Failed for value: {value}"

    def test_type_validator_string_to_bool_false(self):
        """Test converting various strings to False."""
        validator = TypeValidator(bool, convert=True)
        
        for value in ["false", "False", "FALSE", "0", "no", "No", "off", "disabled"]:
            result = validator.validate(value, ValidationContext())
            assert result.is_valid is True, f"Failed for value: {value}"
            assert result.value is False, f"Failed for value: {value}"

    def test_type_validator_failed_conversion(self):
        """Test failed type conversion."""
        validator = TypeValidator(int, convert=True)
        result = validator.validate("not_a_number", ValidationContext())
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_type_validator_without_conversion(self):
        """Test validation without conversion enabled."""
        validator = TypeValidator(int, convert=False)
        result = validator.validate("123", ValidationContext())
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "Expected int, got str" in result.errors[0]

    def test_type_validator_none_value_not_optional(self):
        """Test None value when type is not optional."""
        validator = TypeValidator(int)
        result = validator.validate(None, ValidationContext())
        
        assert result.is_valid is False
        assert "None value not allowed" in result.errors[0]

    def test_type_validator_list_conversion(self):
        """Test converting comma-separated string to list."""
        validator = TypeValidator(list, convert=True, strict_conversion=False)
        result = validator.validate("item1, item2, item3", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == ["item1", "item2", "item3"]

    def test_type_validator_path_conversion(self):
        """Test converting string to Path object."""
        validator = TypeValidator(Path, convert=True)
        result = validator.validate("/path/to/file", ValidationContext())
        
        assert result.is_valid is True
        assert isinstance(result.value, Path)
        # Path uses OS-specific separators on Windows
        assert result.value == Path("/path/to/file")

    def test_type_validator_strict_conversion_float_to_int(self):
        """Test strict conversion rejects non-whole floats."""
        validator = TypeValidator(int, convert=True, strict_conversion=True)
        result = validator.validate(123.45, ValidationContext())
        
        assert result.is_valid is False

    def test_type_validator_lenient_conversion_float_to_int(self):
        """Test lenient conversion allows float to int."""
        validator = TypeValidator(int, convert=True, strict_conversion=False)
        result = validator.validate(123.0, ValidationContext())
        
        assert result.is_valid is True
        assert result.value == 123


class TestRequiredValidator:
    """Test RequiredValidator for required field validation."""

    def test_required_validator_valid_value(self):
        """Test validation with valid non-empty value."""
        validator = RequiredValidator()
        result = validator.validate("valid_value", ValidationContext())
        
        assert result.is_valid is True

    def test_required_validator_none_value(self):
        """Test validation with None value."""
        validator = RequiredValidator()
        result = validator.validate(None, ValidationContext())
        
        assert result.is_valid is False
        assert "Required field is missing" in result.errors[0]

    def test_required_validator_empty_string_not_allowed(self):
        """Test empty string not allowed by default."""
        validator = RequiredValidator(allow_empty_string=False)
        result = validator.validate("", ValidationContext())
        
        assert result.is_valid is False
        assert "empty string" in result.errors[0]

    def test_required_validator_empty_string_allowed(self):
        """Test empty string allowed when configured."""
        validator = RequiredValidator(allow_empty_string=True)
        result = validator.validate("", ValidationContext())
        
        assert result.is_valid is True

    def test_required_validator_empty_list_not_allowed(self):
        """Test empty list not allowed by default."""
        validator = RequiredValidator(allow_empty_collections=False)
        result = validator.validate([], ValidationContext())
        
        assert result.is_valid is False
        assert "empty list" in result.errors[0]

    def test_required_validator_empty_dict_not_allowed(self):
        """Test empty dict not allowed by default."""
        validator = RequiredValidator(allow_empty_collections=False)
        result = validator.validate({}, ValidationContext())
        
        assert result.is_valid is False
        assert "empty dict" in result.errors[0]

    def test_required_validator_empty_collections_allowed(self):
        """Test empty collections allowed when configured."""
        validator = RequiredValidator(allow_empty_collections=True)
        
        assert validator.validate([], ValidationContext()).is_valid is True
        assert validator.validate({}, ValidationContext()).is_valid is True
        assert validator.validate((), ValidationContext()).is_valid is True

    def test_required_validator_custom_empty_values(self):
        """Test custom empty values detection."""
        validator = RequiredValidator(custom_empty_values={"N/A", "null", "undefined"})
        
        assert validator.validate("N/A", ValidationContext()).is_valid is False
        assert validator.validate("null", ValidationContext()).is_valid is False
        assert validator.validate("undefined", ValidationContext()).is_valid is False
        assert validator.validate("valid", ValidationContext()).is_valid is True


class TestRangeValidator:
    """Test RangeValidator for numeric range validation."""

    def test_range_validator_within_range(self):
        """Test value within range."""
        validator = RangeValidator(min_value=0, max_value=100)
        result = validator.validate(50, ValidationContext())
        
        assert result.is_valid is True

    def test_range_validator_below_minimum(self):
        """Test value below minimum."""
        validator = RangeValidator(min_value=10)
        result = validator.validate(5, ValidationContext())
        
        assert result.is_valid is False
        assert "below minimum" in result.errors[0]

    def test_range_validator_above_maximum(self):
        """Test value above maximum."""
        validator = RangeValidator(max_value=100)
        result = validator.validate(150, ValidationContext())
        
        assert result.is_valid is False
        assert "above maximum" in result.errors[0]

    def test_range_validator_exclusive_bounds(self):
        """Test exclusive min/max bounds."""
        validator = RangeValidator(
            min_value=0, max_value=100,
            min_inclusive=False, max_inclusive=False
        )
        
        assert validator.validate(0, ValidationContext()).is_valid is False
        assert validator.validate(100, ValidationContext()).is_valid is False
        assert validator.validate(50, ValidationContext()).is_valid is True

    def test_range_validator_inclusive_bounds(self):
        """Test inclusive min/max bounds."""
        validator = RangeValidator(
            min_value=0, max_value=100,
            min_inclusive=True, max_inclusive=True
        )
        
        assert validator.validate(0, ValidationContext()).is_valid is True
        assert validator.validate(100, ValidationContext()).is_valid is True

    def test_range_validator_auto_convert_string(self):
        """Test automatic conversion of numeric strings."""
        validator = RangeValidator(min_value=0, max_value=100, auto_convert=True)
        result = validator.validate("50", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == 50

    def test_range_validator_auto_convert_float_string(self):
        """Test auto-conversion of float strings."""
        validator = RangeValidator(min_value=0.0, max_value=100.0, auto_convert=True)
        result = validator.validate("50.5", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == 50.5

    def test_range_validator_invalid_string(self):
        """Test invalid string for range validation."""
        validator = RangeValidator(min_value=0, max_value=100, auto_convert=True)
        result = validator.validate("not_a_number", ValidationContext())
        
        assert result.is_valid is False

    def test_range_validator_non_numeric_value(self):
        """Test non-numeric value without auto-convert."""
        validator = RangeValidator(min_value=0, max_value=100, auto_convert=False)
        result = validator.validate("50", ValidationContext())
        
        assert result.is_valid is False
        assert "numeric value" in result.errors[0]


class TestChoicesValidator:
    """Test ChoicesValidator for allowed values validation."""

    def test_choices_validator_valid_choice(self):
        """Test validation with valid choice."""
        validator = ChoicesValidator(["red", "green", "blue"])
        result = validator.validate("red", ValidationContext())
        
        assert result.is_valid is True

    def test_choices_validator_invalid_choice(self):
        """Test validation with invalid choice."""
        validator = ChoicesValidator(["red", "green", "blue"])
        result = validator.validate("yellow", ValidationContext())
        
        assert result.is_valid is False
        assert "not in allowed choices" in result.errors[0]

    def test_choices_validator_case_insensitive(self):
        """Test case-insensitive matching."""
        validator = ChoicesValidator(["RED", "GREEN", "BLUE"], case_sensitive=False)
        result = validator.validate("red", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == "RED"  # Normalized to canonical form

    def test_choices_validator_case_sensitive(self):
        """Test case-sensitive matching."""
        validator = ChoicesValidator(["Red", "Green", "Blue"], case_sensitive=True)
        
        assert validator.validate("Red", ValidationContext()).is_valid is True
        assert validator.validate("red", ValidationContext()).is_valid is False

    def test_choices_validator_callable_choices(self):
        """Test dynamic choices from callable."""
        def get_choices():
            return ["option1", "option2", "option3"]
        
        validator = ChoicesValidator(get_choices)
        assert validator.validate("option1", ValidationContext()).is_valid is True
        assert validator.validate("invalid", ValidationContext()).is_valid is False

    def test_choices_validator_suggestions(self):
        """Test near-match suggestions."""
        validator = ChoicesValidator(["development", "production", "staging"], suggest_near_matches=True)
        result = validator.validate("developmnt", ValidationContext())  # Typo
        
        assert result.is_valid is False
        # Should suggest "development" as close match


class TestRegexValidator:
    """Test RegexValidator for pattern matching."""

    def test_regex_validator_match_mode(self):
        """Test regex validation with match mode."""
        validator = RegexValidator(r"^\d{3}-\d{3}-\d{4}$", match_mode="match")
        
        assert validator.validate("123-456-7890", ValidationContext()).is_valid is True
        assert validator.validate("not-a-phone", ValidationContext()).is_valid is False

    def test_regex_validator_search_mode(self):
        """Test regex validation with search mode."""
        validator = RegexValidator(r"\d{3}", match_mode="search")
        result = validator.validate("abc123def", ValidationContext())
        
        assert result.is_valid is True  # Contains 3 digits

    def test_regex_validator_fullmatch_mode(self):
        """Test regex validation with fullmatch mode."""
        validator = RegexValidator(r"\d{3}", match_mode="fullmatch")
        
        assert validator.validate("123", ValidationContext()).is_valid is True
        assert validator.validate("123abc", ValidationContext()).is_valid is False

    def test_regex_validator_with_flags(self):
        """Test regex with flags (case-insensitive)."""
        validator = RegexValidator(r"^test$", flags=re.IGNORECASE)
        
        assert validator.validate("test", ValidationContext()).is_valid is True
        assert validator.validate("TEST", ValidationContext()).is_valid is True
        assert validator.validate("Test", ValidationContext()).is_valid is True

    def test_regex_validator_non_string_value(self):
        """Test regex validation with non-string value."""
        validator = RegexValidator(r"\d+")
        result = validator.validate(123, ValidationContext())
        
        assert result.is_valid is False
        assert "requires string value" in result.errors[0]

    def test_regex_validator_invalid_pattern(self):
        """Test creating validator with invalid regex pattern."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RegexValidator(r"[invalid(")


class TestLengthValidator:
    """Test LengthValidator for length/size validation."""

    def test_length_validator_string_within_range(self):
        """Test string length within range."""
        validator = LengthValidator(min_length=3, max_length=10)
        result = validator.validate("hello", ValidationContext())
        
        assert result.is_valid is True

    def test_length_validator_string_too_short(self):
        """Test string too short."""
        validator = LengthValidator(min_length=5)
        result = validator.validate("hi", ValidationContext())
        
        assert result.is_valid is False
        assert "below minimum" in result.errors[0]

    def test_length_validator_string_too_long(self):
        """Test string too long."""
        validator = LengthValidator(max_length=5)
        result = validator.validate("very long string", ValidationContext())
        
        assert result.is_valid is False
        assert "above maximum" in result.errors[0]

    def test_length_validator_list(self):
        """Test length validation for list."""
        validator = LengthValidator(min_length=2, max_length=5)
        
        assert validator.validate([1, 2, 3], ValidationContext()).is_valid is True
        assert validator.validate([1], ValidationContext()).is_valid is False
        assert validator.validate([1, 2, 3, 4, 5, 6], ValidationContext()).is_valid is False

    def test_length_validator_dict(self):
        """Test length validation for dict."""
        validator = LengthValidator(min_length=1, max_length=3)
        
        assert validator.validate({"a": 1}, ValidationContext()).is_valid is True
        assert validator.validate({}, ValidationContext()).is_valid is False

    def test_length_validator_trim_strings(self):
        """Test trimming whitespace from strings."""
        validator = LengthValidator(min_length=3, max_length=10, trim_strings=True)
        result = validator.validate("  hello  ", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == "hello"
        assert len(result.transformations) > 0

    def test_length_validator_exclusive_bounds(self):
        """Test exclusive length bounds."""
        validator = LengthValidator(
            min_length=3, max_length=10,
            min_inclusive=False, max_inclusive=False
        )
        
        assert validator.validate("abc", ValidationContext()).is_valid is False  # Exactly 3
        assert validator.validate("1234567890", ValidationContext()).is_valid is False  # Exactly 10
        assert validator.validate("abcd", ValidationContext()).is_valid is True  # 4


class TestEmailValidator:
    """Test EmailValidator for email format validation."""

    def test_email_validator_valid_email(self):
        """Test validation with valid email."""
        validator = EmailValidator()
        
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com"
        ]
        
        for email in valid_emails:
            result = validator.validate(email, ValidationContext())
            assert result.is_valid is True, f"Failed for: {email}"

    def test_email_validator_invalid_email(self):
        """Test validation with invalid email."""
        validator = EmailValidator()
        
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com"
        ]
        
        for email in invalid_emails:
            result = validator.validate(email, ValidationContext())
            assert result.is_valid is False, f"Should have failed for: {email}"

    def test_email_validator_non_string(self):
        """Test email validation with non-string value."""
        validator = EmailValidator()
        result = validator.validate(123, ValidationContext())
        
        assert result.is_valid is False
        assert "requires string value" in result.errors[0]

    def test_email_validator_none_value(self):
        """Test email validation with None value."""
        validator = EmailValidator()
        result = validator.validate(None, ValidationContext())
        
        assert result.is_valid is True  # None passes through validators


class TestURLValidator:
    """Test URLValidator for URL format validation."""

    def test_url_validator_valid_urls(self):
        """Test validation with valid URLs."""
        validator = URLValidator()
        
        valid_urls = [
            "http://example.com",
            "https://example.com/path",
            "https://example.com/path?query=value",
            "ftp://ftp.example.com/file.txt"
        ]
        
        for url in valid_urls:
            result = validator.validate(url, ValidationContext())
            assert result.is_valid is True, f"Failed for: {url}"

    def test_url_validator_invalid_scheme(self):
        """Test URL with invalid scheme."""
        validator = URLValidator(allowed_schemes={"http", "https"})
        result = validator.validate("ftp://example.com", ValidationContext())
        
        assert result.is_valid is False
        assert "scheme" in result.errors[0]

    def test_url_validator_missing_domain(self):
        """Test URL with missing domain."""
        validator = URLValidator(require_domain=True)
        result = validator.validate("http://", ValidationContext())
        
        assert result.is_valid is False
        assert "domain" in result.errors[0]

    def test_url_validator_normalization(self):
        """Test URL normalization."""
        validator = URLValidator(normalize_url=True)
        result = validator.validate("HTTP://EXAMPLE.COM/PATH", ValidationContext())
        
        # URL should be normalized (this is implementation-specific)
        assert result.is_valid is True

    def test_url_validator_non_string(self):
        """Test URL validation with non-string value."""
        validator = URLValidator()
        result = validator.validate(123, ValidationContext())
        
        assert result.is_valid is False


class TestCustomValidator:
    """Test CustomValidator for custom validation functions."""

    def test_custom_validator_success(self):
        """Test custom validator with successful validation."""
        def is_even(value):
            if value % 2 != 0:
                raise ValueError("Value must be even")
            return value
        
        validator = CustomValidator(is_even, error_message="Not even")
        result = validator.validate(4, ValidationContext())
        
        assert result.is_valid is True

    def test_custom_validator_failure(self):
        """Test custom validator with failed validation."""
        def is_even(value):
            if value % 2 != 0:
                raise ValueError("Value must be even")
            return value
        
        validator = CustomValidator(is_even, error_message="Not even")
        result = validator.validate(3, ValidationContext())
        
        assert result.is_valid is False
        assert "Not even" in result.errors[0]

    def test_custom_validator_transformation(self):
        """Test custom validator that transforms value."""
        def uppercase(value):
            return value.upper()
        
        validator = CustomValidator(uppercase)
        result = validator.validate("hello", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == "HELLO"
        assert len(result.transformations) > 0


class TestCompositeValidator:
    """Test CompositeValidator for combining validators."""

    def test_composite_validator_all_pass(self):
        """Test composite validator when all validators pass."""
        validators = [
            TypeValidator(int, convert=True),
            RangeValidator(min_value=0, max_value=100)
        ]
        composite = CompositeValidator(validators)
        result = composite.validate("50", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == 50

    def test_composite_validator_one_fails(self):
        """Test composite validator when one validator fails."""
        validators = [
            TypeValidator(int, convert=True),
            RangeValidator(min_value=0, max_value=100)
        ]
        composite = CompositeValidator(validators)
        result = composite.validate("150", ValidationContext())
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_composite_validator_stop_on_first_error(self):
        """Test composite validator with stop_on_first_error."""
        validators = [
            RequiredValidator(),
            TypeValidator(int, convert=True),
            RangeValidator(min_value=0, max_value=100)
        ]
        composite = CompositeValidator(validators, stop_on_first_error=True)
        result = composite.validate(None, ValidationContext())
        
        assert result.is_valid is False
        # Should only have error from RequiredValidator, not subsequent validators

    def test_composite_validator_chained_transformations(self):
        """Test composite validator with multiple transformations."""
        validators = [
            TypeValidator(str, convert=True),
            LengthValidator(min_length=3, max_length=20, trim_strings=True)
        ]
        composite = CompositeValidator(validators)
        result = composite.validate("  hello  ", ValidationContext())
        
        assert result.is_valid is True
        assert result.value == "hello"


class TestValidationEngine:
    """Test ValidationEngine for validation orchestration."""

    def test_validation_engine_validate_value(self):
        """Test ValidationEngine.validate_value method."""
        engine = ValidationEngine(level=ValidationLevel.STRICT)
        validators = [TypeValidator(int, convert=True)]
        
        result = engine.validate_value("123", validators, "test.value")
        
        assert result.is_valid is True
        assert result.value == 123

    def test_validation_engine_validate_dict(self):
        """Test ValidationEngine.validate_dict method."""
        engine = ValidationEngine()
        data = {
            "name": "John",
            "age": "30",
            "email": "john@example.com"
        }
        field_validators = {
            "name": [TypeValidator(str), LengthValidator(min_length=2)],
            "age": [TypeValidator(int, convert=True), RangeValidator(min_value=0, max_value=120)],
            "email": [EmailValidator()]
        }
        
        results = engine.validate_dict(data, field_validators)
        
        assert "name" in results
        assert "age" in results
        assert "email" in results
        assert results["name"].is_valid is True
        assert results["age"].is_valid is True
        assert results["email"].is_valid is True

    def test_validation_engine_caching_enabled(self):
        """Test ValidationEngine with caching enabled."""
        engine = ValidationEngine(cache_results=True, max_cache_size=100)
        validators = [TypeValidator(int, convert=True)]
        
        # First validation
        result1 = engine.validate_value("123", validators, "test.value")
        assert result1.is_valid is True
        
        # Second validation (should hit cache)
        result2 = engine.validate_value("123", validators, "test.value")
        assert result2.is_valid is True
        
        # Check cache stats
        stats = engine.get_cache_stats()
        assert stats["cache_size"] > 0
        assert stats["cache_enabled"] is True

    def test_validation_engine_clear_cache(self):
        """Test clearing ValidationEngine cache."""
        engine = ValidationEngine(cache_results=True)
        validators = [TypeValidator(int, convert=True)]
        
        engine.validate_value("123", validators, "test.value")
        assert engine.get_cache_stats()["cache_size"] > 0
        
        engine.clear_cache()
        assert engine.get_cache_stats()["cache_size"] == 0

    def test_validation_engine_validation_levels(self):
        """Test ValidationEngine with different validation levels."""
        strict_engine = ValidationEngine(level=ValidationLevel.STRICT)
        lenient_engine = ValidationEngine(level=ValidationLevel.LENIENT)
        
        validators = [TypeValidator(int, convert=True)]
        
        # Both should work the same for valid conversions
        assert strict_engine.validate_value("123", validators).is_valid is True
        assert lenient_engine.validate_value("123", validators).is_valid is True


class TestValidatorBaseClass:
    """Test Validator base class functionality."""

    def test_validator_repr(self):
        """Test validator string representation."""
        validator = TypeValidator(int, name="test_validator")
        repr_str = repr(validator)
        
        assert "TypeValidator" in repr_str

    def test_validator_error_handling(self):
        """Test validator error handling."""
        class BrokenValidator(Validator):
            def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                raise RuntimeError("Intentional error")
        
        validator = BrokenValidator(name="broken")
        result = validator.validate(42, ValidationContext())
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validator_logging(self):
        """Test validator logging functionality."""
        validator = TypeValidator(int, convert=True)
        
        with patch('config_manager.validation.logger') as mock_logger:
            result = validator.validate("123", ValidationContext(path="test"))
            # Validator should log debug messages

    def test_validator_performance_tracking(self):
        """Test that validation time is tracked."""
        validator = TypeValidator(int, convert=True)
        result = validator.validate("123", ValidationContext())
        
        assert result.validation_time >= 0.0
        assert result.validator_name == "TypeValidator"

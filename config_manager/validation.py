"""
Configuration validation and schema system for ConfigManager.
"""

from typing import Any, Dict, List, Optional, Union, Callable, Type
from abc import ABC, abstractmethod
import re


class ValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, message: str, path: str = ""):
        self.message = message
        self.path = path
        super().__init__(f"Validation error at '{path}': {message}" if path else f"Validation error: {message}")


class Validator(ABC):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, value: Any, path: str = "") -> Any:
        """
        Validate a value and return the validated/converted value.
        
        Args:
            value: The value to validate
            path: The path to this value in the configuration (for error reporting)
            
        Returns:
            The validated/converted value
            
        Raises:
            ValidationError: If validation fails
        """
        pass


class TypeValidator(Validator):
    """Validates that a value is of a specific type."""
    
    def __init__(self, expected_type: Type, convert: bool = True):
        """
        Initialize the type validator.
        
        Args:
            expected_type: The expected Python type
            convert: Whether to attempt type conversion
        """
        self.expected_type = expected_type
        self.convert = convert
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        if isinstance(value, self.expected_type):
            return value
            
        if self.convert:
            try:
                if self.expected_type == bool:
                    # Special handling for boolean conversion
                    if isinstance(value, str):
                        lower_val = value.lower()
                        if lower_val in ('true', 'yes', 'y', 'on', '1'):
                            return True
                        elif lower_val in ('false', 'no', 'n', 'off', '0'):
                            return False
                        else:
                            raise ValueError(f"Cannot convert '{value}' to boolean")
                    return bool(value)
                elif self.expected_type == list:
                    # Special handling for list conversion
                    if isinstance(value, str):
                        if not value.strip():  # Empty string
                            return []
                        return [item.strip() for item in value.split(',')]
                    return list(value)
                else:
                    return self.expected_type(value)
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Cannot convert '{value}' to {self.expected_type.__name__}: {e}", path)
        else:
            raise ValidationError(f"Expected {self.expected_type.__name__}, got {type(value).__name__}", path)


class RequiredValidator(Validator):
    """Validates that a value is present (not None)."""
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValidationError("Required field is missing", path)
        return value


class RangeValidator(Validator):
    """Validates that a numeric value is within a specified range."""
    
    def __init__(self, min_value: Optional[Union[int, float]] = None, max_value: Optional[Union[int, float]] = None):
        """
        Initialize the range validator.
        
        Args:
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
        """
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Range validation requires numeric value, got {type(value).__name__}", path)
        
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"Value {value} is below minimum {self.min_value}", path)
            
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"Value {value} is above maximum {self.max_value}", path)
            
        return value


class ChoicesValidator(Validator):
    """Validates that a value is one of the allowed choices."""
    
    def __init__(self, choices: List[Any]):
        """
        Initialize the choices validator.
        
        Args:
            choices: List of allowed values
        """
        self.choices = choices
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        if value not in self.choices:
            raise ValidationError(f"Value '{value}' not in allowed choices: {self.choices}", path)
            
        return value


class RegexValidator(Validator):
    """Validates that a string value matches a regular expression."""
    
    def __init__(self, pattern: str, flags: int = 0):
        """
        Initialize the regex validator.
        
        Args:
            pattern: Regular expression pattern
            flags: Regex flags (e.g., re.IGNORECASE)
        """
        self.pattern = pattern
        self.regex = re.compile(pattern, flags)
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        if not isinstance(value, str):
            raise ValidationError(f"Regex validation requires string value, got {type(value).__name__}", path)
        
        if not self.regex.match(value):
            raise ValidationError(f"Value '{value}' does not match pattern '{self.pattern}'", path)
            
        return value


class LengthValidator(Validator):
    """Validates the length of a string or list."""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        """
        Initialize the length validator.
        
        Args:
            min_length: Minimum allowed length
            max_length: Maximum allowed length
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        if not hasattr(value, '__len__'):
            raise ValidationError(f"Length validation requires string or list, got {type(value).__name__}", path)
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            raise ValidationError(f"Length {length} is below minimum {self.min_length}", path)
            
        if self.max_length is not None and length > self.max_length:
            raise ValidationError(f"Length {length} is above maximum {self.max_length}", path)
            
        return value


class CustomValidator(Validator):
    """Validates using a custom function."""
    
    def __init__(self, validator_func: Callable[[Any], Any], error_message: str = "Custom validation failed"):
        """
        Initialize the custom validator.
        
        Args:
            validator_func: Function that takes a value and returns validated value or raises exception
            error_message: Error message to use if validation fails
        """
        self.validator_func = validator_func
        self.error_message = error_message
    
    def validate(self, value: Any, path: str = "") -> Any:
        if value is None:
            return None
            
        try:
            return self.validator_func(value)
        except Exception as e:
            raise ValidationError(f"{self.error_message}: {e}", path)

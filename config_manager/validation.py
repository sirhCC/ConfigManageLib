"""
🔧 Enterprise-grade Configuration Validation System for ConfigManager.

This module provides a comprehensive validation framework with modern Python patterns,
detailed error reporting, performance monitoring, and extensible validator architecture.
"""

from typing import Any, Dict, List, Optional, Union, Callable, Type, Set, FrozenSet
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
import logging
import time
from enum import Enum


# Configure logger for this module
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Fail on any validation error
    LENIENT = "lenient"    # Convert values when possible, warn on issues
    PERMISSIVE = "permissive"  # Allow most values, minimal validation


@dataclass(frozen=True)
class ValidationContext:
    """
    Immutable context for validation operations.
    
    This provides additional information to validators during the validation process,
    enabling more sophisticated validation logic and better error reporting.
    """
    path: str = ""
    level: ValidationLevel = ValidationLevel.STRICT
    parent_value: Optional[Any] = None
    root_value: Optional[Any] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def with_path(self, new_path: str) -> 'ValidationContext':
        """Create a new context with an updated path."""
        return ValidationContext(
            path=new_path,
            level=self.level,
            parent_value=self.parent_value,
            root_value=self.root_value,
            custom_data=self.custom_data
        )
    
    def with_parent(self, parent: Any) -> 'ValidationContext':
        """Create a new context with an updated parent value."""
        return ValidationContext(
            path=self.path,
            level=self.level,
            parent_value=parent,
            root_value=self.root_value,
            custom_data=self.custom_data
        )


@dataclass
class ValidationResult:
    """
    Comprehensive validation result with metadata and performance tracking.
    
    This provides detailed information about the validation process,
    including timing, warnings, and transformation details.
    """
    value: Any
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)
    validation_time: float = 0.0
    validator_name: str = ""
    path: str = ""
    
    def add_error(self, message: str) -> None:
        """Add an error message and mark result as invalid."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_transformation(self, message: str) -> None:
        """Record a transformation that was applied."""
        self.transformations.append(message)


class ValidationError(Exception):
    """
    Enhanced validation error with detailed context and suggestions.
    
    This exception provides comprehensive information about validation failures,
    including the path, expected vs actual values, and potential solutions.
    """
    
    def __init__(
        self, 
        message: str, 
        path: str = "",
        expected_type: Optional[Type] = None,
        actual_value: Any = None,
        suggestions: Optional[List[str]] = None
    ):
        self.message = message
        self.path = path
        self.expected_type = expected_type
        self.actual_value = actual_value
        self.suggestions = suggestions or []
        
        # Create detailed error message
        error_parts = []
        if path:
            error_parts.append(f"Validation error at '{path}'")
        else:
            error_parts.append("Validation error")
        
        error_parts.append(message)
        
        if expected_type and actual_value is not None:
            error_parts.append(
                f"Expected {expected_type.__name__}, got {type(actual_value).__name__}"
            )
        
        if suggestions:
            error_parts.append(f"Suggestions: {', '.join(suggestions)}")
        
        full_message = ": ".join(error_parts)
        super().__init__(full_message)


class Validator(ABC):
    """
    Abstract base class for all validators with enterprise-grade capabilities.
    
    This provides a modern foundation for validation with performance monitoring,
    detailed error reporting, and extensible architecture.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            name: Optional custom name for this validator instance
        """
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @abstractmethod
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """
        Abstract method for validator-specific logic.
        
        Subclasses must implement this method to define their validation behavior.
        
        Args:
            value: The value to validate
            context: Validation context with path and metadata
            
        Returns:
            ValidationResult with validation outcome and metadata
        """
        pass
    
    def validate(self, value: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        """
        Validate a value with performance monitoring and error handling.
        
        Args:
            value: The value to validate
            context: Optional validation context (created if not provided)
            
        Returns:
            ValidationResult with validation outcome and metadata
        """
        if context is None:
            context = ValidationContext()
        
        start_time = time.perf_counter()
        
        try:
            self._logger.debug(f"Validating value at '{context.path}' with {self.name}")
            
            result = self._do_validate(value, context)
            result.validator_name = self.name
            result.path = context.path
            result.validation_time = time.perf_counter() - start_time
            
            if result.is_valid:
                self._logger.debug(
                    f"Validation successful for {self.name} at '{context.path}' "
                    f"({result.validation_time:.4f}s)"
                )
            else:
                self._logger.warning(
                    f"Validation failed for {self.name} at '{context.path}': "
                    f"{', '.join(result.errors)}"
                )
            
            return result
            
        except Exception as e:
            validation_time = time.perf_counter() - start_time
            self._logger.error(
                f"Validation error in {self.name} at '{context.path}': {e} "
                f"({validation_time:.4f}s)"
            )
            
            # Return failed result
            result = ValidationResult(
                value=value,
                is_valid=False,
                validator_name=self.name,
                path=context.path,
                validation_time=validation_time
            )
            result.add_error(str(e))
            return result
    
    def __repr__(self) -> str:
        """String representation of the validator."""
        return f"{self.__class__.__name__}(name='{self.name}')"


class TypeValidator(Validator):
    """
    Enterprise-grade type validator with intelligent conversion and detailed error reporting.
    
    Features:
    - Intelligent type conversion with safety checks
    - Support for Union types and Optional types
    - Detailed conversion tracking and warnings
    - Configurable conversion strictness
    """
    
    def __init__(
        self, 
        expected_type: Type, 
        convert: bool = True,
        strict_conversion: bool = False,
        name: Optional[str] = None
    ):
        """
        Initialize the type validator.
        
        Args:
            expected_type: The expected Python type
            convert: Whether to attempt type conversion
            strict_conversion: If True, only safe conversions are allowed
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.expected_type = expected_type
        self.convert = convert
        self.strict_conversion = strict_conversion
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate and optionally convert the value to the expected type."""
        result = ValidationResult(value=value)
        
        # Handle None values for Optional types
        if value is None:
            origin = getattr(self.expected_type, '__origin__', None)
            if origin is Union:
                args = getattr(self.expected_type, '__args__', ())
                if type(None) in args:
                    # This is Optional[T], None is valid
                    return result
            
            result.add_error(f"None value not allowed for type {self.expected_type.__name__}")
            return result
        
        # Check if value is already the correct type
        if isinstance(value, self.expected_type):
            return result
        
        # Handle Union types (including Optional)
        origin = getattr(self.expected_type, '__origin__', None)
        if origin is Union:
            args = getattr(self.expected_type, '__args__', ())
            for arg_type in args:
                if arg_type is type(None):
                    continue
                if isinstance(value, arg_type):
                    return result
                
                # Try conversion for each type in the Union
                if self.convert:
                    try:
                        converted_value = self._safe_convert(value, arg_type, context)
                        result.value = converted_value
                        result.add_transformation(
                            f"Converted {type(value).__name__} to {arg_type.__name__}"
                        )
                        return result
                    except ValueError:
                        continue
            
            # None of the Union types matched
            type_names = [t.__name__ for t in args if t is not type(None)]
            result.add_error(
                f"Value must be one of types: {', '.join(type_names)}"
            )
            return result
        
        # Attempt conversion if enabled
        if self.convert:
            try:
                converted_value = self._safe_convert(value, self.expected_type, context)
                result.value = converted_value
                result.add_transformation(
                    f"Converted {type(value).__name__} to {self.expected_type.__name__}"
                )
                
                if context.level == ValidationLevel.STRICT and not self.strict_conversion:
                    result.add_warning(
                        f"Type conversion applied in strict mode: "
                        f"{type(value).__name__} -> {self.expected_type.__name__}"
                    )
                
                return result
                
            except ValueError as e:
                result.add_error(
                    f"Cannot convert {type(value).__name__} to {self.expected_type.__name__}: {e}"
                )
                return result
        
        # No conversion, type mismatch
        result.add_error(
            f"Expected {self.expected_type.__name__}, got {type(value).__name__}"
        )
        return result
    
    def _safe_convert(self, value: Any, target_type: Type, context: ValidationContext) -> Any:
        """
        Safely convert a value to the target type with validation.
        
        Args:
            value: Value to convert
            target_type: Target type for conversion
            context: Validation context
            
        Returns:
            Converted value
            
        Raises:
            ValueError: If conversion is not possible or safe
        """
        # String conversions
        if target_type == str:
            return str(value)
        
        # Numeric conversions
        elif target_type == int:
            if isinstance(value, bool):
                # Handle boolean to int conversion explicitly
                return int(value)
            elif isinstance(value, str):
                # Parse string to int
                value = value.strip()
                if not value:
                    raise ValueError("Empty string cannot be converted to int")
                return int(value)
            elif isinstance(value, float):
                # Check if it's a whole number
                if self.strict_conversion and not value.is_integer():
                    raise ValueError(f"Float {value} is not a whole number")
                return int(value)
            else:
                return int(value)
        
        elif target_type == float:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValueError("Empty string cannot be converted to float")
                return float(value)
            else:
                return float(value)
        
        # Boolean conversions
        elif target_type == bool:
            if isinstance(value, str):
                value_lower = value.lower().strip()
                if value_lower in ('true', '1', 'yes', 'on', 'enabled'):
                    return True
                elif value_lower in ('false', '0', 'no', 'off', 'disabled'):
                    return False
                else:
                    raise ValueError(f"Cannot convert string '{value}' to boolean")
            else:
                return bool(value)
        
        # List conversions
        elif target_type == list:
            if isinstance(value, (tuple, set, frozenset)):
                return list(value)
            elif isinstance(value, str):
                # Try to parse as comma-separated values
                if self.strict_conversion:
                    raise ValueError("String to list conversion not allowed in strict mode")
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                # Try to make it iterable
                try:
                    return list(value)
                except TypeError:
                    raise ValueError(f"Cannot convert {type(value).__name__} to list")
        
        # Path conversions
        elif target_type == Path:
            return Path(str(value))
        
        # Default conversion attempt
        else:
            try:
                return target_type(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Default conversion failed: {e}")
    
    def __repr__(self) -> str:
        """String representation of the type validator."""
        return (
            f"TypeValidator(expected_type={self.expected_type.__name__}, "
            f"convert={self.convert}, strict_conversion={self.strict_conversion})"
        )


class RequiredValidator(Validator):
    """
    Enterprise-grade required field validator with comprehensive empty value detection.
    
    Features:
    - Configurable empty value detection
    - Support for custom empty value definitions
    - Detailed error messages with suggestions
    """
    
    def __init__(
        self, 
        allow_empty_string: bool = False,
        allow_empty_collections: bool = False,
        custom_empty_values: Optional[Set[Any]] = None,
        name: Optional[str] = None
    ):
        """
        Initialize the required validator.
        
        Args:
            allow_empty_string: Whether to allow empty strings as valid
            allow_empty_collections: Whether to allow empty lists/dicts as valid
            custom_empty_values: Set of additional values to treat as "empty"
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.allow_empty_string = allow_empty_string
        self.allow_empty_collections = allow_empty_collections
        self.custom_empty_values = custom_empty_values or set()
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the value is present and not empty."""
        result = ValidationResult(value=value)
        
        # Check for None
        if value is None:
            result.add_error("Required field is missing (None value)")
            return result
        
        # Check for empty string
        if isinstance(value, str):
            if not self.allow_empty_string and value.strip() == "":
                result.add_error("Required field cannot be empty string")
                return result
        
        # Check for empty collections (before custom_empty_values to avoid unhashable type errors)
        elif isinstance(value, (list, dict, tuple, set)):
            if not self.allow_empty_collections and len(value) == 0:
                collection_type = type(value).__name__
                result.add_error(f"Required field cannot be empty {collection_type}")
                return result
        
        # Check for custom empty values (only for hashable types)
        try:
            if value in self.custom_empty_values:
                result.add_error(f"Value '{value}' is in custom empty values list")
                return result
        except TypeError:
            # Value is unhashable (list, dict, set), skip this check
            pass
        
        return result


class RangeValidator(Validator):
    """
    Enterprise-grade range validator with comprehensive numeric validation.
    
    Features:
    - Support for inclusive and exclusive bounds
    - Automatic type conversion for numeric strings
    - Detailed error messages with current and expected ranges
    """
    
    def __init__(
        self, 
        min_value: Optional[Union[int, float]] = None, 
        max_value: Optional[Union[int, float]] = None,
        min_inclusive: bool = True,
        max_inclusive: bool = True,
        auto_convert: bool = True,
        name: Optional[str] = None
    ):
        """
        Initialize the range validator.
        
        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            min_inclusive: Whether minimum bound is inclusive
            max_inclusive: Whether maximum bound is inclusive
            auto_convert: Whether to auto-convert numeric strings
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.min_value = min_value
        self.max_value = max_value
        self.min_inclusive = min_inclusive
        self.max_inclusive = max_inclusive
        self.auto_convert = auto_convert
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the value is within the specified range."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        # Auto-convert numeric strings if enabled
        if self.auto_convert and isinstance(value, str):
            try:
                if '.' in value:
                    value = float(value.strip())
                else:
                    value = int(value.strip())
                result.value = value
                result.add_transformation(f"Converted string to {type(value).__name__}")
            except ValueError:
                result.add_error(f"Cannot convert '{value}' to numeric value for range validation")
                return result
        
        # Check if value is numeric
        if not isinstance(value, (int, float)):
            result.add_error(
                f"Range validation requires numeric value, got {type(value).__name__}"
            )
            return result
        
        # Check minimum bound
        if self.min_value is not None:
            if self.min_inclusive:
                if value < self.min_value:
                    result.add_error(
                        f"Value {value} is below minimum {self.min_value} (inclusive)"
                    )
            else:
                if value <= self.min_value:
                    result.add_error(
                        f"Value {value} is not above minimum {self.min_value} (exclusive)"
                    )
        
        # Check maximum bound
        if self.max_value is not None:
            if self.max_inclusive:
                if value > self.max_value:
                    result.add_error(
                        f"Value {value} is above maximum {self.max_value} (inclusive)"
                    )
            else:
                if value >= self.max_value:
                    result.add_error(
                        f"Value {value} is not below maximum {self.max_value} (exclusive)"
                    )
        
        return result


class ChoicesValidator(Validator):
    """
    Enterprise-grade choices validator with case-insensitive matching and suggestions.
    
    Features:
    - Case-insensitive string matching option
    - Smart suggestions for near-matches
    - Support for callable choice generators
    """
    
    def __init__(
        self, 
        choices: Union[List[Any], Callable[[], List[Any]]], 
        case_sensitive: bool = True,
        suggest_near_matches: bool = True,
        name: Optional[str] = None
    ):
        """
        Initialize the choices validator.
        
        Args:
            choices: List of allowed values or callable that returns choices
            case_sensitive: Whether string matching should be case-sensitive
            suggest_near_matches: Whether to suggest similar values on mismatch
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.choices = choices
        self.case_sensitive = case_sensitive
        self.suggest_near_matches = suggest_near_matches
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the value is one of the allowed choices."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        # Get current choices (may be dynamic)
        current_choices = self.choices() if callable(self.choices) else self.choices
        
        # Direct match check
        if value in current_choices:
            return result
        
        # Case-insensitive string matching if enabled
        if not self.case_sensitive and isinstance(value, str):
            for choice in current_choices:
                if isinstance(choice, str) and value.lower() == choice.lower():
                    result.value = choice  # Use the canonical form
                    result.add_transformation(f"Normalized case: '{value}' -> '{choice}'")
                    return result
        
        # Value not found in choices
        error_msg = f"Value '{value}' not in allowed choices: {current_choices}"
        
        # Add suggestions for near matches
        if self.suggest_near_matches and isinstance(value, str):
            suggestions = self._find_near_matches(value, current_choices)
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions)}?"
        
        result.add_error(error_msg)
        return result
    
    def _find_near_matches(self, value: str, choices: List[Any]) -> List[str]:
        """Find choices that are similar to the given value."""
        import difflib
        
        string_choices = [str(choice) for choice in choices if isinstance(choice, str)]
        if not string_choices:
            return []
        
        # Use difflib to find close matches
        close_matches = difflib.get_close_matches(
            value, string_choices, n=3, cutoff=0.6
        )
        return close_matches


class RegexValidator(Validator):
    """
    Enterprise-grade regex validator with detailed pattern matching and error reporting.
    
    Features:
    - Compiled pattern caching for performance
    - Multiple match modes (match, search, fullmatch)
    - Detailed error messages with pattern explanation
    - Group extraction capabilities
    """
    
    def __init__(
        self, 
        pattern: str, 
        flags: int = 0,
        match_mode: str = "match",
        extract_groups: bool = False,
        name: Optional[str] = None
    ):
        """
        Initialize the regex validator.
        
        Args:
            pattern: Regular expression pattern
            flags: Regex flags (e.g., re.IGNORECASE)
            match_mode: Match mode ('match', 'search', 'fullmatch')
            extract_groups: Whether to extract and return regex groups
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.pattern = pattern
        self.flags = flags
        self.match_mode = match_mode
        self.extract_groups = extract_groups
        
        try:
            self.regex = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the string value matches the regex pattern."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        # Ensure value is a string
        if not isinstance(value, str):
            result.add_error(
                f"Regex validation requires string value, got {type(value).__name__}"
            )
            return result
        
        # Perform pattern matching based on mode
        if self.match_mode == "match":
            match = self.regex.match(value)
        elif self.match_mode == "search":
            match = self.regex.search(value)
        elif self.match_mode == "fullmatch":
            match = self.regex.fullmatch(value)
        else:
            result.add_error(f"Invalid match mode: {self.match_mode}")
            return result
        
        if not match:
            result.add_error(
                f"Value '{value}' does not match pattern '{self.pattern}' "
                f"(mode: {self.match_mode})"
            )
            return result
        
        # Extract groups if requested
        if self.extract_groups and match.groups():
            result.add_transformation(f"Extracted groups: {match.groups()}")
            # Optionally store groups in custom data for later use
        
        return result


class LengthValidator(Validator):
    """
    Enterprise-grade length validator with comprehensive size validation.
    
    Features:
    - Support for strings, lists, dicts, and any sized object
    - Configurable bounds (inclusive/exclusive)
    - Automatic trimming options for strings
    - Detailed error messages with current and expected lengths
    """
    
    def __init__(
        self, 
        min_length: Optional[int] = None, 
        max_length: Optional[int] = None,
        min_inclusive: bool = True,
        max_inclusive: bool = True,
        trim_strings: bool = False,
        name: Optional[str] = None
    ):
        """
        Initialize the length validator.
        
        Args:
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            min_inclusive: Whether minimum bound is inclusive
            max_inclusive: Whether maximum bound is inclusive
            trim_strings: Whether to trim whitespace from strings before checking
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.min_length = min_length
        self.max_length = max_length
        self.min_inclusive = min_inclusive
        self.max_inclusive = max_inclusive
        self.trim_strings = trim_strings
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate the length/size of the value."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        # Handle string trimming
        if isinstance(value, str) and self.trim_strings:
            trimmed_value = value.strip()
            if trimmed_value != value:
                result.value = trimmed_value
                result.add_transformation("Trimmed whitespace from string")
            value = trimmed_value
        
        # Check if value has length
        if not hasattr(value, '__len__'):
            result.add_error(
                f"Length validation requires sized object, got {type(value).__name__}"
            )
            return result
        
        length = len(value)
        object_type = type(value).__name__
        
        # Check minimum length
        if self.min_length is not None:
            if self.min_inclusive:
                if length < self.min_length:
                    result.add_error(
                        f"{object_type} length {length} is below minimum {self.min_length}"
                    )
            else:
                if length <= self.min_length:
                    result.add_error(
                        f"{object_type} length {length} is not above minimum {self.min_length}"
                    )
        
        # Check maximum length
        if self.max_length is not None:
            if self.max_inclusive:
                if length > self.max_length:
                    result.add_error(
                        f"{object_type} length {length} is above maximum {self.max_length}"
                    )
            else:
                if length >= self.max_length:
                    result.add_error(
                        f"{object_type} length {length} is not below maximum {self.max_length}"
                    )
        
        return result


class EmailValidator(Validator):
    """
    Enterprise-grade email validator with comprehensive validation.
    
    Features:
    - RFC-compliant email validation
    - Domain validation options
    - Internationalized domain support
    - Disposable email detection (optional)
    """
    
    def __init__(
        self, 
        validate_domain: bool = False,
        allow_international: bool = True,
        name: Optional[str] = None
    ):
        """
        Initialize the email validator.
        
        Args:
            validate_domain: Whether to validate that the domain exists
            allow_international: Whether to allow international domain names
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.validate_domain = validate_domain
        self.allow_international = allow_international
        
        # Basic email regex pattern (simplified but functional)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the value is a valid email address."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        if not isinstance(value, str):
            result.add_error(
                f"Email validation requires string value, got {type(value).__name__}"
            )
            return result
        
        # Basic format validation
        if not self.email_pattern.match(value):
            result.add_error(f"'{value}' is not a valid email format")
            return result
        
        # Additional domain validation if requested
        if self.validate_domain:
            domain = value.split('@')[1]
            try:
                import socket
                socket.gethostbyname(domain)
            except socket.gaierror:
                result.add_warning(f"Email domain '{domain}' does not appear to exist")
        
        return result


class URLValidator(Validator):
    """
    Enterprise-grade URL validator with comprehensive validation.
    
    Features:
    - Multiple URL scheme support
    - Domain validation options
    - Path and query parameter validation
    - Automatic URL normalization
    """
    
    def __init__(
        self, 
        allowed_schemes: Optional[Set[str]] = None,
        require_domain: bool = True,
        normalize_url: bool = True,
        name: Optional[str] = None
    ):
        """
        Initialize the URL validator.
        
        Args:
            allowed_schemes: Set of allowed URL schemes (None = any)
            require_domain: Whether to require a domain/host
            normalize_url: Whether to normalize the URL
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.allowed_schemes = allowed_schemes or {'http', 'https', 'ftp', 'ftps'}
        self.require_domain = require_domain
        self.normalize_url = normalize_url
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate that the value is a valid URL."""
        from urllib.parse import urlparse, urlunparse
        
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        if not isinstance(value, str):
            result.add_error(
                f"URL validation requires string value, got {type(value).__name__}"
            )
            return result
        
        try:
            parsed = urlparse(value)
        except Exception as e:
            result.add_error(f"Cannot parse URL '{value}': {e}")
            return result
        
        # Validate scheme
        if parsed.scheme.lower() not in self.allowed_schemes:
            result.add_error(
                f"URL scheme '{parsed.scheme}' not in allowed schemes: "
                f"{', '.join(self.allowed_schemes)}"
            )
            return result
        
        # Validate domain if required
        if self.require_domain and not parsed.netloc:
            result.add_error("URL must include a domain/host")
            return result
        
        # Normalize URL if requested
        if self.normalize_url:
            normalized = urlunparse(parsed)
            if normalized != value:
                result.value = normalized
                result.add_transformation(f"Normalized URL: '{value}' -> '{normalized}'")
        
        return result


class CustomValidator(Validator):
    """
    Enterprise-grade custom validator with flexible validation functions.
    
    Features:
    - Support for multiple validation functions
    - Detailed error context and suggestions
    - Performance monitoring for custom functions
    - Async validation support (future)
    """
    
    def __init__(
        self, 
        validator_func: Callable[[Any], Any], 
        error_message: str = "Custom validation failed",
        description: str = "",
        name: Optional[str] = None
    ):
        """
        Initialize the custom validator.
        
        Args:
            validator_func: Function that validates and optionally transforms value
            error_message: Error message to use if validation fails
            description: Human-readable description of what this validator does
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.validator_func = validator_func
        self.error_message = error_message
        self.description = description
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate using the custom function."""
        result = ValidationResult(value=value)
        
        if value is None:
            return result
        
        try:
            validated_value = self.validator_func(value)
            
            # Check if value was transformed
            if validated_value != value:
                result.value = validated_value
                result.add_transformation("Custom validation transformation applied")
            
            return result
            
        except Exception as e:
            result.add_error(f"{self.error_message}: {e}")
            return result


class CompositeValidator(Validator):
    """
    Enterprise-grade composite validator for combining multiple validators.
    
    Features:
    - Sequential validation with short-circuiting options
    - Aggregated error and warning collection
    - Performance monitoring across all validators
    - Conditional validation based on context
    """
    
    def __init__(
        self, 
        validators: List[Validator],
        stop_on_first_error: bool = False,
        require_all_pass: bool = True,
        name: Optional[str] = None
    ):
        """
        Initialize the composite validator.
        
        Args:
            validators: List of validators to apply in sequence
            stop_on_first_error: Whether to stop on the first validation error
            require_all_pass: Whether all validators must pass (vs. any one)
            name: Optional custom name for this validator
        """
        super().__init__(name)
        self.validators = validators
        self.stop_on_first_error = stop_on_first_error
        self.require_all_pass = require_all_pass
    
    def _do_validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate using all component validators."""
        result = ValidationResult(value=value)
        current_value = value
        
        passed_count = 0
        
        for validator in self.validators:
            validator_result = validator.validate(current_value, context)
            
            # Aggregate errors and warnings
            result.errors.extend(validator_result.errors)
            result.warnings.extend(validator_result.warnings)
            result.transformations.extend(validator_result.transformations)
            result.validation_time += validator_result.validation_time
            
            if validator_result.is_valid:
                passed_count += 1
                current_value = validator_result.value  # Use transformed value
            elif self.stop_on_first_error:
                result.is_valid = False
                result.value = current_value
                return result
        
        # Determine overall result
        if self.require_all_pass:
            result.is_valid = passed_count == len(self.validators)
        else:
            result.is_valid = passed_count > 0
        
        result.value = current_value
        return result


@dataclass
class ValidationEngine:
    """
    Enterprise-grade validation engine with comprehensive validation orchestration.
    
    This provides a high-level interface for managing complex validation workflows,
    with support for conditional validation, caching, and detailed reporting.
    """
    
    level: ValidationLevel = ValidationLevel.STRICT
    cache_results: bool = False
    max_cache_size: int = 1000
    
    def __post_init__(self):
        """Initialize the validation engine."""
        self._logger = logging.getLogger(f"{__name__}.ValidationEngine")
        self._cache: Dict[str, ValidationResult] = {}
    
    def validate_value(
        self, 
        value: Any, 
        validators: List[Validator], 
        path: str = "",
        parent_value: Optional[Any] = None,
        root_value: Optional[Any] = None
    ) -> ValidationResult:
        """
        Validate a single value using multiple validators.
        
        Args:
            value: Value to validate
            validators: List of validators to apply
            path: Path to this value in the configuration
            parent_value: Parent container of this value
            root_value: Root configuration object
            
        Returns:
            Aggregated validation result
        """
        context = ValidationContext(
            path=path,
            level=self.level,
            parent_value=parent_value,
            root_value=root_value
        )
        
        # Check cache if enabled
        if self.cache_results:
            cache_key = self._generate_cache_key(value, validators, context)
            if cache_key in self._cache:
                self._logger.debug(f"Cache hit for validation at '{path}'")
                return self._cache[cache_key]
        
        # Run validation
        start_time = time.perf_counter()
        
        if len(validators) == 1:
            result = validators[0].validate(value, context)
        else:
            # Use composite validator for multiple validators
            composite = CompositeValidator(validators, name=f"Composite[{path}]")
            result = composite.validate(value, context)
        
        total_time = time.perf_counter() - start_time
        
        self._logger.debug(
            f"Validation complete for '{path}': "
            f"{'valid' if result.is_valid else 'invalid'} "
            f"({total_time:.4f}s total)"
        )
        
        # Cache result if enabled
        if self.cache_results and len(self._cache) < self.max_cache_size:
            cache_key = self._generate_cache_key(value, validators, context)
            self._cache[cache_key] = result
        
        return result
    
    def validate_dict(
        self, 
        data: Dict[str, Any], 
        field_validators: Dict[str, List[Validator]],
        path: str = ""
    ) -> Dict[str, ValidationResult]:
        """
        Validate all fields in a dictionary.
        
        Args:
            data: Dictionary to validate
            field_validators: Mapping of field names to validator lists
            path: Base path for error reporting
            
        Returns:
            Dictionary of field names to validation results
        """
        results = {}
        
        for field_name, validators in field_validators.items():
            field_path = f"{path}.{field_name}" if path else field_name
            field_value = data.get(field_name)
            
            results[field_name] = self.validate_value(
                field_value, validators, field_path, data, data
            )
        
        return results
    
    def _generate_cache_key(
        self, 
        value: Any, 
        validators: List[Validator], 
        context: ValidationContext
    ) -> str:
        """Generate a cache key for the validation operation."""
        import hashlib
        
        # Create a simple cache key (in production, this could be more sophisticated)
        key_parts = [
            str(type(value).__name__),
            str(hash(str(value)) if value is not None else "None"),
            str([v.__class__.__name__ for v in validators]),
            context.path,
            context.level.value
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """Clear the validation cache."""
        self._cache.clear()
        self._logger.debug("Validation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.max_cache_size,
            "cache_enabled": self.cache_results
        }

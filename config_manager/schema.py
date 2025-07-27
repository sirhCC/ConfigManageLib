"""
🔧 Enterprise-grade Schema Definition and Validation System for ConfigManager.

This module provides a comprehensive schema system with modern Python patterns,
dataclass-based field definitions, advanced validation orchestration, and
enterprise-grade error reporting and performance monitoring.
"""

from typing import Any, Dict, List, Optional, Union, Type, Set, Callable, ForwardRef
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging
import time
from pathlib import Path

from .validation import (
    Validator, ValidationError, ValidationResult, ValidationContext, 
    ValidationLevel, ValidationEngine, TypeValidator, RequiredValidator
)

# Configure logger for this module
logger = logging.getLogger(__name__)


class FieldValidationMode(Enum):
    """Field validation modes for schema processing."""
    STRICT = "strict"        # All validators must pass
    LENIENT = "lenient"      # Try to convert/fix values
    PERMISSIVE = "permissive"  # Minimal validation, accept most values


@dataclass
class FieldMetadata:
    """
    Metadata for schema fields with comprehensive configuration options.
    
    This provides detailed information about field behavior, validation,
    and documentation for enterprise schema management.
    """
    description: str = ""
    examples: List[Any] = field(default_factory=list)
    deprecated: bool = False
    deprecation_message: str = ""
    version_added: Optional[str] = None
    version_deprecated: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    sensitive: bool = False  # For fields containing secrets/passwords
    internal: bool = False   # For internal-only fields
    
    def is_deprecated(self) -> bool:
        """Check if this field is deprecated."""
        return self.deprecated
    
    def get_deprecation_warning(self, field_name: str) -> str:
        """Get a formatted deprecation warning message."""
        message = f"Field '{field_name}' is deprecated"
        if self.deprecation_message:
            message += f": {self.deprecation_message}"
        if self.version_deprecated:
            message += f" (deprecated in version {self.version_deprecated})"
        return message


@dataclass
class SchemaField:
    """
    Enterprise-grade schema field definition with comprehensive validation and metadata.
    
    Features:
    - Modern dataclass-based configuration
    - Comprehensive validation orchestration
    - Rich metadata and documentation support
    - Performance monitoring and caching
    - Advanced default value handling
    """
    
    field_type: Optional[Type] = None
    required: bool = False
    default: Any = None
    default_factory: Optional[Callable[[], Any]] = None
    validators: List[Validator] = field(default_factory=list)
    validation_mode: FieldValidationMode = FieldValidationMode.STRICT
    metadata: FieldMetadata = field(default_factory=FieldMetadata)
    
    # Advanced configuration
    allow_none: bool = False
    transform_func: Optional[Callable[[Any], Any]] = None
    condition_func: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    def __post_init__(self):
        """Initialize field with automatic validator setup."""
        self._logger = logging.getLogger(f"{__name__}.SchemaField")
        
        # Auto-add type validator if type is specified
        if self.field_type is not None and not any(
            isinstance(v, TypeValidator) for v in self.validators
        ):
            type_validator = TypeValidator(
                self.field_type, 
                convert=self.validation_mode != FieldValidationMode.STRICT
            )
            self.validators.insert(0, type_validator)
        
        # Auto-add required validator if field is required
        if self.required and not any(
            isinstance(v, RequiredValidator) for v in self.validators
        ):
            required_validator = RequiredValidator(
                allow_empty_string=self.validation_mode == FieldValidationMode.PERMISSIVE
            )
            self.validators.insert(0, required_validator)
    
    def get_default_value(self, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get the default value for this field.
        
        Args:
            context: Optional context for dynamic defaults
            
        Returns:
            Default value for this field
        """
        if self.default_factory is not None:
            return self.default_factory()
        return self.default
    
    def should_validate(self, config_data: Dict[str, Any]) -> bool:
        """
        Check if this field should be validated based on conditions.
        
        Args:
            config_data: Complete configuration data for context
            
        Returns:
            True if field should be validated
        """
        if self.condition_func is None:
            return True
        
        try:
            return self.condition_func(config_data)
        except Exception as e:
            self._logger.warning(f"Condition function failed: {e}")
            return True  # Default to validating if condition fails
    
    def validate(
        self, 
        value: Any, 
        context: ValidationContext,
        validation_engine: Optional[ValidationEngine] = None
    ) -> ValidationResult:
        """
        Validate a value against this field's schema with enterprise features.
        
        Args:
            value: Value to validate
            context: Validation context with path and metadata
            validation_engine: Optional validation engine for advanced features
            
        Returns:
            Comprehensive validation result
        """
        start_time = time.perf_counter()
        
        # Handle None values and defaults
        if value is None:
            if self.allow_none:
                return ValidationResult(value=None, validation_time=time.perf_counter() - start_time)
            
            # Try to use default value
            default_value = self.get_default_value()
            if default_value is not None:
                value = default_value
                result = ValidationResult(value=value)
                result.add_transformation("Applied default value")
                result.validation_time = time.perf_counter() - start_time
                return result
        
        # Apply transformation if specified
        if self.transform_func is not None:
            try:
                transformed_value = self.transform_func(value)
                if transformed_value != value:
                    value = transformed_value
                    result = ValidationResult(value=value)
                    result.add_transformation("Applied field transformation")
                else:
                    result = ValidationResult(value=value)
            except Exception as e:
                result = ValidationResult(value=value, is_valid=False)
                result.add_error(f"Transformation failed: {e}")
                result.validation_time = time.perf_counter() - start_time
                return result
        else:
            result = ValidationResult(value=value)
        
        # Apply validators using validation engine if available
        if validation_engine:
            validator_result = validation_engine.validate_value(
                value, self.validators, context.path
            )
        else:
            # Fallback to direct validation
            from .validation import CompositeValidator
            composite = CompositeValidator(self.validators)
            validator_result = composite.validate(value, context)
        
        # Merge results
        result.value = validator_result.value
        result.is_valid = validator_result.is_valid
        result.errors.extend(validator_result.errors)
        result.warnings.extend(validator_result.warnings)
        result.transformations.extend(validator_result.transformations)
        result.validation_time = time.perf_counter() - start_time
        
        # Add deprecation warning if field is deprecated
        if self.metadata.is_deprecated():
            field_name = context.path.split('.')[-1] if context.path else "unknown"
            warning = self.metadata.get_deprecation_warning(field_name)
            result.add_warning(warning)
        
        return result
    
    def __repr__(self) -> str:
        """String representation of the schema field."""
        return (
            f"SchemaField(type={self.field_type.__name__ if self.field_type else None}, "
            f"required={self.required}, validators={len(self.validators)})"
        )


@dataclass
class SchemaMetadata:
    """
    Comprehensive metadata for schema definitions.
    
    This provides documentation, versioning, and behavioral configuration
    for entire schema definitions.
    """
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    authors: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    strict_mode: bool = False
    allow_extra_fields: bool = True
    auto_convert_types: bool = True
    validation_level: ValidationLevel = ValidationLevel.STRICT


class Schema:
    """
    Enterprise-grade configuration schema with advanced validation and metadata support.
    
    Features:
    - Modern dataclass-based field definitions
    - Nested schema support with inheritance
    - Comprehensive validation orchestration
    - Performance monitoring and caching
    - Rich metadata and documentation
    - Conditional field validation
    - Schema composition and inheritance
    """
    
    def __init__(
        self, 
        fields: Optional[Dict[str, Union[SchemaField, 'Schema']]] = None,
        metadata: Optional[SchemaMetadata] = None,
        validation_engine: Optional[ValidationEngine] = None
    ):
        """
        Initialize an enterprise schema.
        
        Args:
            fields: Dictionary mapping field names to SchemaField or nested Schema objects
            metadata: Schema metadata configuration
            validation_engine: Optional validation engine for advanced features
        """
        self.fields = fields or {}
        self.metadata = metadata or SchemaMetadata()
        self.validation_engine = validation_engine or ValidationEngine(
            level=self.metadata.validation_level
        )
        self._logger = logging.getLogger(f"{__name__}.Schema")
    
    def add_field(self, name: str, field_def: Union[SchemaField, 'Schema']) -> 'Schema':
        """
        Add a field to this schema with method chaining.
        
        Args:
            name: The field name
            field_def: SchemaField or nested Schema definition
            
        Returns:
            This schema instance for method chaining
        """
        self.fields[name] = field_def
        return self
    
    def remove_field(self, name: str) -> 'Schema':
        """
        Remove a field from this schema.
        
        Args:
            name: The field name to remove
            
        Returns:
            This schema instance for method chaining
        """
        if name in self.fields:
            del self.fields[name]
        return self
    
    def extend_schema(self, other_schema: 'Schema', override: bool = False) -> 'Schema':
        """
        Extend this schema with fields from another schema.
        
        Args:
            other_schema: Schema to extend from
            override: Whether to override existing fields
            
        Returns:
            This schema instance for method chaining
        """
        for field_name, field_def in other_schema.fields.items():
            if field_name not in self.fields or override:
                self.fields[field_name] = field_def
        return self
    
    def validate(
        self, 
        config: Dict[str, Any], 
        path: str = "",
        context: Optional[ValidationContext] = None
    ) -> Dict[str, Any]:
        """
        Validate a configuration dictionary against this schema with enterprise features.
        
        Args:
            config: The configuration dictionary to validate
            path: The current path in the configuration (for error reporting)
            context: Optional validation context
            
        Returns:
            The validated configuration with type conversions and defaults applied
            
        Raises:
            ValidationError: If validation fails and strict mode is enabled
        """
        if context is None:
            context = ValidationContext(
                path=path,
                level=self.metadata.validation_level,
                root_value=config
            )
        
        start_time = time.perf_counter()
        
        if not isinstance(config, dict):
            raise ValidationError(
                f"Expected dictionary for schema validation, got {type(config).__name__}",
                path
            )
        
        validated = {}
        all_errors = []
        all_warnings = []
        
        # Validate each field defined in the schema
        for field_name, field_definition in self.fields.items():
            field_path = f"{path}.{field_name}" if path else field_name
            field_value = config.get(field_name)
            field_context = context.with_path(field_path).with_parent(config)
            
            try:
                if isinstance(field_definition, Schema):
                    # Nested schema validation
                    if field_value is None:
                        field_value = {}
                    validated[field_name] = field_definition.validate(
                        field_value, field_path, field_context
                    )
                    
                elif isinstance(field_definition, SchemaField):
                    # Check if field should be validated based on conditions
                    if not field_definition.should_validate(config):
                        self._logger.debug(f"Skipping conditional field: {field_path}")
                        continue
                    
                    # Regular field validation
                    result = field_definition.validate(
                        field_value, field_context, self.validation_engine
                    )
                    
                    if result.is_valid:
                        validated[field_name] = result.value
                        all_warnings.extend(result.warnings)
                    else:
                        all_errors.extend([f"{field_path}: {error}" for error in result.errors])
                        
                        # In permissive mode, use default or original value
                        if self.metadata.validation_level == ValidationLevel.PERMISSIVE:
                            default_value = field_definition.get_default_value(config)
                            validated[field_name] = default_value if default_value is not None else field_value
                        
                else:
                    raise ValidationError(
                        f"Invalid field definition type for '{field_name}': {type(field_definition)}",
                        field_path
                    )
                    
            except ValidationError as e:
                all_errors.append(str(e))
                
                # In permissive mode, continue with default values
                if self.metadata.validation_level == ValidationLevel.PERMISSIVE:
                    if isinstance(field_definition, SchemaField):
                        default_value = field_definition.get_default_value(config)
                        if default_value is not None:
                            validated[field_name] = default_value
        
        # Handle extra fields based on schema configuration
        if self.metadata.allow_extra_fields:
            extra_fields = set(config.keys()) - set(self.fields.keys())
            for extra_field in extra_fields:
                if not self.metadata.strict_mode:
                    validated[extra_field] = config[extra_field]
                    all_warnings.append(f"Extra field '{extra_field}' included without validation")
        elif self.metadata.strict_mode:
            unexpected_keys = set(config.keys()) - set(self.fields.keys())
            if unexpected_keys:
                all_errors.append(f"Unexpected keys in strict schema: {unexpected_keys}")
        
        # Log validation results
        validation_time = time.perf_counter() - start_time
        self._logger.debug(
            f"Schema validation for '{path}' completed: "
            f"{len(all_errors)} errors, {len(all_warnings)} warnings "
            f"({validation_time:.4f}s)"
        )
        
        # Report warnings
        for warning in all_warnings:
            self._logger.warning(warning)
        
        # Handle errors based on validation level
        if all_errors:
            error_message = f"Schema validation failed with {len(all_errors)} errors: " + "; ".join(all_errors)
            
            if self.metadata.validation_level == ValidationLevel.STRICT:
                raise ValidationError(error_message, path)
            elif self.metadata.validation_level == ValidationLevel.LENIENT:
                self._logger.warning(f"Validation errors in lenient mode: {error_message}")
            # PERMISSIVE mode already handled above
        
        return validated
    
    def get_field_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive information about all fields in this schema.
        
        Returns:
            Dictionary with field information for documentation/introspection
        """
        field_info = {}
        
        for field_name, field_def in self.fields.items():
            if isinstance(field_def, SchemaField):
                field_info[field_name] = {
                    "type": field_def.field_type.__name__ if field_def.field_type else "Any",
                    "required": field_def.required,
                    "description": field_def.metadata.description,
                    "deprecated": field_def.metadata.is_deprecated(),
                    "examples": field_def.metadata.examples,
                    "validators": [v.__class__.__name__ for v in field_def.validators]
                }
            elif isinstance(field_def, Schema):
                field_info[field_name] = {
                    "type": "Schema",
                    "nested_fields": field_def.get_field_info()
                }
        
        return field_info
    
    def __repr__(self) -> str:
        """String representation of the schema."""
        return f"Schema(fields={len(self.fields)}, strict={self.metadata.strict_mode})"


# Modern field factory functions with enterprise features
def String(
    required: bool = False, 
    default: Optional[str] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise string field with comprehensive validation."""
    return SchemaField(
        field_type=str,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def Integer(
    required: bool = False, 
    default: Optional[int] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise integer field with comprehensive validation."""
    return SchemaField(
        field_type=int,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def Float(
    required: bool = False, 
    default: Optional[float] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise float field with comprehensive validation."""
    return SchemaField(
        field_type=float,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def Boolean(
    required: bool = False, 
    default: Optional[bool] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise boolean field with comprehensive validation."""
    return SchemaField(
        field_type=bool,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def ListField(
    required: bool = False, 
    default: Optional[List[Any]] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise list field with comprehensive validation."""
    return SchemaField(
        field_type=list,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def DictField(
    required: bool = False, 
    default: Optional[Dict[str, Any]] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise dictionary field with comprehensive validation."""
    return SchemaField(
        field_type=dict,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def AnyField(
    required: bool = False, 
    default: Any = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise field that accepts any type."""
    return SchemaField(
        field_type=None,  # No type constraint
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )


def PathField(
    required: bool = False, 
    default: Optional[Union[str, Path]] = None,
    validators: Optional[List[Validator]] = None,
    description: str = "",
    **kwargs
) -> SchemaField:
    """Create an enterprise path field with automatic Path conversion."""
    return SchemaField(
        field_type=Path,
        required=required,
        default=default,
        validators=validators or [],
        metadata=FieldMetadata(description=description),
        **kwargs
    )

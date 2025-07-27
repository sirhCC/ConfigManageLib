"""
Schema definition and validation system for ConfigManager.
"""

from typing import Any as AnyType, Dict, List, Optional, Union, Type
from .validation import Validator, ValidationError, TypeValidator, RequiredValidator


class SchemaField:
    """Defines a single field in a configuration schema."""
    
    def __init__(
        self,
        field_type: Optional[Type] = None,
        required: bool = False,
        default: AnyType = None,
        validators: Optional[List[Validator]] = None,
        description: str = ""
    ):
        """
        Initialize a schema field.
        
        Args:
            field_type: Expected Python type for this field
            required: Whether this field is required
            default: Default value if field is missing
            validators: List of validators to apply to this field
            description: Human-readable description of this field
        """
        self.field_type = field_type
        self.required = required
        self.default = default
        self.validators = validators or []
        self.description = description
        
        # Add type validator if type is specified
        if field_type is not None:
            self.validators.insert(0, TypeValidator(field_type, convert=True))
        
        # Add required validator if field is required
        if required:
            self.validators.insert(0, RequiredValidator())
    
    def validate(self, value: AnyType, path: str = "") -> AnyType:
        """
        Validate a value against this field's schema.
        
        Args:
            value: The value to validate
            path: The path to this field in the configuration
            
        Returns:
            The validated/converted value
            
        Raises:
            ValidationError: If validation fails
        """
        # Use default value if value is None and default is provided
        if value is None and self.default is not None:
            value = self.default
        
        # Apply all validators in order
        for validator in self.validators:
            value = validator.validate(value, path)
        
        return value


class Schema:
    """Defines a configuration schema with fields and nested schemas."""
    
    def __init__(self, fields: Optional[Dict[str, Union[SchemaField, 'Schema']]] = None, strict: bool = False):
        """
        Initialize a schema.
        
        Args:
            fields: Dictionary mapping field names to SchemaField or nested Schema objects
            strict: If True, reject any keys not defined in the schema
        """
        self.fields = fields or {}
        self.strict = strict
    
    def add_field(self, name: str, field: Union[SchemaField, 'Schema']) -> 'Schema':
        """
        Add a field to this schema.
        
        Args:
            name: The field name
            field: SchemaField or nested Schema
            
        Returns:
            This schema instance for method chaining
        """
        self.fields[name] = field
        return self
    
    def validate(self, config: Dict[str, AnyType], path: str = "") -> Dict[str, AnyType]:
        """
        Validate a configuration dictionary against this schema.
        
        Args:
            config: The configuration dictionary to validate
            path: The current path in the configuration (for error reporting)
            
        Returns:
            The validated configuration with type conversions and defaults applied
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(config, dict):
            raise ValidationError(f"Expected dictionary, got {type(config).__name__}", path)
        
        validated = {}
        
        # Validate each field defined in the schema
        for field_name, field_definition in self.fields.items():
            field_path = f"{path}.{field_name}" if path else field_name
            field_value = config.get(field_name)
            
            if isinstance(field_definition, Schema):
                # Nested schema
                if field_value is None:
                    field_value = {}
                validated[field_name] = field_definition.validate(field_value, field_path)
            elif isinstance(field_definition, SchemaField):
                # Regular field
                validated[field_name] = field_definition.validate(field_value, field_path)
            else:
                raise ValidationError(f"Invalid field definition for '{field_name}'", field_path)
        
        # In strict mode, check for unexpected keys
        if self.strict:
            unexpected_keys = set(config.keys()) - set(self.fields.keys())
            if unexpected_keys:
                raise ValidationError(f"Unexpected keys in configuration: {unexpected_keys}", path)
        
        # By default, only return validated fields (extra fields are ignored)
        return validated


# Convenience functions for creating common field types
def String(required: bool = False, default: Optional[str] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a string field."""
    return SchemaField(str, required, default, validators, description)


def Integer(required: bool = False, default: Optional[int] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create an integer field."""
    return SchemaField(int, required, default, validators, description)


def Float(required: bool = False, default: Optional[float] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a float field."""
    return SchemaField(float, required, default, validators, description)


def Boolean(required: bool = False, default: Optional[bool] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a boolean field."""
    return SchemaField(bool, required, default, validators, description)


def ListField(required: bool = False, default: Optional[List[AnyType]] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a list field."""
    return SchemaField(list, required, default, validators, description)


def DictField(required: bool = False, default: Optional[Dict[str, AnyType]] = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a dictionary field."""
    return SchemaField(dict, required, default, validators, description)


def AnyField(required: bool = False, default: AnyType = None, validators: Optional[List[Validator]] = None, description: str = "") -> SchemaField:
    """Create a field that accepts any type."""
    return SchemaField(None, required, default, validators, description)

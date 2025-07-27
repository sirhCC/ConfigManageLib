# Schema Validation System

The ConfigManager library includes a comprehensive schema validation system that allows you to define the structure, types, and validation rules for your configuration data. This ensures that your application receives properly formatted and validated configuration values.

## Overview

The schema validation system consists of three main components:

1. **Schema**: Defines the overall structure of your configuration
2. **SchemaField**: Defines individual configuration fields with types and validation rules
3. **Validators**: Provide specific validation logic (type checking, ranges, patterns, etc.)

## Basic Usage

### Defining a Schema

```python
from config_manager import ConfigManager
from config_manager.schema import Schema, String, Integer, Boolean
from config_manager.validation import RangeValidator

# Define a schema
schema = Schema({
    "app_name": String(required=True),
    "port": Integer(default=8080, validators=[RangeValidator(min_value=1024, max_value=65535)]),
    "debug": Boolean(default=False)
})

# Create ConfigManager with schema
config = ConfigManager(schema=schema)
```

### Using Schema Validation

```python
# Add configuration sources
config.add_source(JsonSource("config.json"))
config.add_source(EnvironmentSource("MYAPP_"))

# Validate configuration
try:
    validated_config = config.validate()
    print(f"App running on port {validated_config['port']}")
except ValidationError as e:
    print(f"Configuration error: {e}")

# Check if configuration is valid
if config.is_valid():
    print("Configuration is valid!")
else:
    errors = config.get_validation_errors()
    for error in errors:
        print(f"Error: {error}")
```

## Field Types

### Basic Types

```python
from config_manager.schema import String, Integer, Float, Boolean, ListField

schema = Schema({
    "name": String(required=True),
    "age": Integer(default=25),
    "height": Float(),
    "active": Boolean(default=True),
    "tags": ListField(default=[])
})
```

### Type Conversion

The schema system automatically converts string values to the appropriate types:

- **String to Integer**: `"123"` → `123`
- **String to Float**: `"45.67"` → `45.67`
- **String to Boolean**: `"true"`, `"yes"`, `"1"` → `True`; `"false"`, `"no"`, `"0"` → `False`
- **String to List**: `"a,b,c"` → `["a", "b", "c"]`

## Validators

### Built-in Validators

#### TypeValidator
Validates and converts types:
```python
from config_manager.validation import TypeValidator

field = SchemaField(int, validators=[TypeValidator(int)])
```

#### RequiredValidator
Ensures a field is present and not empty:
```python
from config_manager.validation import RequiredValidator

field = String(validators=[RequiredValidator()])
# Or simply:
field = String(required=True)
```

#### RangeValidator
Validates numeric ranges:
```python
from config_manager.validation import RangeValidator

# Age between 18 and 120
age_field = Integer(validators=[RangeValidator(min_value=18, max_value=120)])

# Port above 1024
port_field = Integer(validators=[RangeValidator(min_value=1024)])
```

#### ChoicesValidator
Validates against a list of allowed values:
```python
from config_manager.validation import ChoicesValidator

level_field = String(validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])])
```

#### RegexValidator
Validates using regular expressions:
```python
from config_manager.validation import RegexValidator

# Email validation
email_field = String(validators=[RegexValidator(r"^[^@]+@[^@]+\\.[^@]+$")])

# Username validation (alphanumeric and underscores, 3-20 chars)
username_field = String(validators=[RegexValidator(r"^[a-zA-Z0-9_]{3,20}$")])
```

#### LengthValidator
Validates string or list length:
```python
from config_manager.validation import LengthValidator

# Password must be 8-32 characters
password_field = String(validators=[LengthValidator(min_length=8, max_length=32)])

# List must have 1-10 items
tags_field = ListField(validators=[LengthValidator(min_length=1, max_length=10)])
```

#### CustomValidator
Use custom validation functions:
```python
from config_manager.validation import CustomValidator

def validate_even_number(value):
    if value % 2 != 0:
        raise ValidationError(f"Value {value} is not even")
    return value

even_field = Integer(validators=[CustomValidator(validate_even_number)])
```

## Nested Schemas

You can create complex nested configurations:

```python
# Define nested schemas
database_schema = Schema({
    "host": String(default="localhost"),
    "port": Integer(default=5432),
    "name": String(required=True),
    "username": String(required=True),
    "password": String(required=True)
})

app_schema = Schema({
    "app_name": String(required=True),
    "database": database_schema,
    "debug": Boolean(default=False)
})

# Usage
config = ConfigManager(schema=app_schema)
validated = config.validate()

# Access nested values
db_host = validated["database"]["host"]
db_port = validated["database"]["port"]
```

## Default Values

Schemas support default values that are applied when fields are missing:

```python
schema = Schema({
    "host": String(default="localhost"),
    "port": Integer(default=8080),
    "timeout": Float(default=30.0),
    "features": ListField(default=["basic"])
})

# If configuration only contains {"host": "example.com"}
# The validated result will be:
# {
#     "host": "example.com",
#     "port": 8080,
#     "timeout": 30.0,
#     "features": ["basic"]
# }
```

## Error Handling

### Validation Methods

The ConfigManager provides several methods for handling validation:

```python
# Validate and raise exception on error
try:
    validated_config = config.validate()
except ValidationError as e:
    print(f"Validation failed: {e}")

# Validate without raising exceptions
validated_config = config.validate(raise_on_error=False)

# Check if configuration is valid
if config.is_valid():
    print("Configuration is valid")

# Get list of validation errors
errors = config.get_validation_errors()
for error in errors:
    print(f"Error: {error}")
```

### Validation Caching

Validation results are cached for performance. The cache is automatically invalidated when:

- A new configuration source is added
- The configuration is reloaded
- The schema is changed

```python
# First validation - performs full validation
result1 = config.validate()

# Second validation - returns cached result
result2 = config.validate()

# Add new source - cache is invalidated
config.add_source(new_source)

# Next validation - performs full validation again
result3 = config.validate()
```

## Advanced Usage

### Multiple Validators

You can combine multiple validators for a single field:

```python
from config_manager.validation import RangeValidator, RegexValidator

# Port must be in range AND match pattern
port_field = String(validators=[
    RegexValidator(r"^\\d+$"),  # Must be numeric string
    RangeValidator(min_value=1024, max_value=65535)  # Will be converted to int first
])
```

### Schema Composition

Build complex schemas by composing smaller ones:

```python
# Common address schema
address_schema = Schema({
    "street": String(required=True),
    "city": String(required=True),
    "state": String(required=True),
    "zip": String(validators=[RegexValidator(r"^\\d{5}(-\\d{4})?$")])
})

# User schema with address
user_schema = Schema({
    "name": String(required=True),
    "email": String(required=True, validators=[RegexValidator(r"^[^@]+@[^@]+\\.[^@]+$")]),
    "address": address_schema
})
```

### Custom Field Types

Create reusable field definitions:

```python
def EmailField(**kwargs):
    return String(
        validators=[RegexValidator(r"^[^@]+@[^@]+\\.[^@]+$")],
        **kwargs
    )

def PortField(**kwargs):
    return Integer(
        validators=[RangeValidator(min_value=1, max_value=65535)],
        **kwargs
    )

schema = Schema({
    "admin_email": EmailField(required=True),
    "web_port": PortField(default=8080),
    "db_port": PortField(default=5432)
})
```

## Best Practices

### 1. Use Descriptive Field Names and Descriptions

```python
schema = Schema({
    "database_connection_timeout": Float(
        default=30.0,
        validators=[RangeValidator(min_value=1.0, max_value=300.0)],
        description="Database connection timeout in seconds"
    )
})
```

### 2. Provide Sensible Defaults

```python
schema = Schema({
    "log_level": String(
        default="INFO",
        validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]
    ),
    "max_connections": Integer(default=100)
})
```

### 3. Validate Early and Fail Fast

```python
# Validate configuration at application startup
config = ConfigManager(schema=app_schema)
config.add_source(JsonSource("config.json"))

try:
    validated_config = config.validate()
except ValidationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Use validated configuration throughout the application
app.run(host=validated_config["host"], port=validated_config["port"])
```

### 4. Group Related Configuration

```python
# Group related settings into nested schemas
app_schema = Schema({
    "server": Schema({
        "host": String(default="localhost"),
        "port": Integer(default=8080),
        "ssl": Boolean(default=False)
    }),
    "database": Schema({
        "url": String(required=True),
        "pool_size": Integer(default=10)
    }),
    "logging": Schema({
        "level": String(default="INFO"),
        "file": String(default=None)
    })
})
```

This schema validation system provides a robust foundation for ensuring your application receives properly formatted and validated configuration data, reducing runtime errors and improving application reliability.

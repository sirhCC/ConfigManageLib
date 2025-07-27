"""Tests for the schema system."""

import unittest
from config_manager.schema import Schema, SchemaField, String, Integer, Float, Boolean, ListField
from config_manager.validation import ValidationError, RequiredValidator, RangeValidator


class TestSchemaField(unittest.TestCase):
    """Test the SchemaField class."""
    
    def test_basic_field(self):
        """Test creating a basic schema field."""
        field = SchemaField(str)
        
        # Valid string
        self.assertEqual(field.validate("hello"), "hello")
        
        # Type conversion
        self.assertEqual(field.validate(123), "123")
    
    def test_field_with_default(self):
        """Test field with default value."""
        field = SchemaField(str, default="default_value")
        
        # With value
        self.assertEqual(field.validate("hello"), "hello")
        
        # Default handling is done at schema level, not field level
        self.assertEqual(field.validate(123), "123")
    
    def test_field_with_validators(self):
        """Test field with validators."""
        field = SchemaField(
            int,
            validators=[RequiredValidator(), RangeValidator(min_value=1, max_value=10)]
        )
        
        # Valid value
        self.assertEqual(field.validate(5), 5)
        
        # Invalid range
        with self.assertRaises(ValidationError):
            field.validate(15)
        
        # Invalid type
        with self.assertRaises(ValidationError):
            field.validate("not a number")


class TestSchema(unittest.TestCase):
    """Test the Schema class."""
    
    def test_simple_schema(self):
        """Test a simple schema with basic fields."""
        schema = Schema({
            "name": String(),
            "age": Integer(),
            "height": Float(),
            "active": Boolean()
        })
        
        config = {
            "name": "John",
            "age": 30,
            "height": 5.9,
            "active": True
        }
        
        result = schema.validate(config)
        self.assertEqual(result["name"], "John")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["height"], 5.9)
        self.assertEqual(result["active"], True)
    
    def test_schema_with_defaults(self):
        """Test schema with default values."""
        schema = Schema({
            "name": String(required=True),
            "age": Integer(default=25),
            "active": Boolean(default=True)
        })
        
        # Minimal config
        config = {"name": "John"}
        result = schema.validate(config)
        
        self.assertEqual(result["name"], "John")
        self.assertEqual(result["age"], 25)
        self.assertEqual(result["active"], True)
    
    def test_schema_missing_required(self):
        """Test schema validation with missing required field."""
        schema = Schema({
            "name": String(required=True),
            "age": Integer()
        })
        
        config = {"age": 30}  # Missing required "name"
        
        with self.assertRaises(ValidationError):
            schema.validate(config)
    
    def test_schema_type_conversion(self):
        """Test schema with type conversion."""
        schema = Schema({
            "port": Integer(),
            "timeout": Float(),
            "debug": Boolean(),
            "tags": ListField()
        })
        
        config = {
            "port": "8080",  # String to int
            "timeout": "30.5",  # String to float
            "debug": "true",  # String to bool
            "tags": "web,api,service"  # String to list
        }
        
        result = schema.validate(config)
        self.assertEqual(result["port"], 8080)
        self.assertEqual(result["timeout"], 30.5)
        self.assertEqual(result["debug"], True)
        self.assertEqual(result["tags"], ["web", "api", "service"])
    
    def test_nested_schema(self):
        """Test nested schema validation."""
        database_schema = Schema({
            "host": String(default="localhost"),
            "port": Integer(default=5432),
            "name": String(required=True)
        })
        
        main_schema = Schema({
            "app_name": String(required=True),
            "database": database_schema
        })
        
        config = {
            "app_name": "MyApp",
            "database": {
                "name": "mydb",
                "port": 3306
            }
        }
        
        result = main_schema.validate(config)
        self.assertEqual(result["app_name"], "MyApp")
        self.assertEqual(result["database"]["host"], "localhost")  # Default applied
        self.assertEqual(result["database"]["port"], 3306)
        self.assertEqual(result["database"]["name"], "mydb")
    
    def test_invalid_nested_schema(self):
        """Test nested schema with validation error."""
        database_schema = Schema({
            "host": String(required=True),
            "port": Integer(required=True)
        })
        
        main_schema = Schema({
            "app_name": String(required=True),
            "database": database_schema
        })
        
        config = {
            "app_name": "MyApp",
            "database": {
                "host": "localhost"
                # Missing required "port"
            }
        }
        
        with self.assertRaises(ValidationError):
            main_schema.validate(config)
    
    def test_extra_fields(self):
        """Test schema behavior with extra fields."""
        schema = Schema({
            "name": String(),
            "age": Integer()
        })
        
        config = {
            "name": "John",
            "age": 30,
            "extra_field": "should be ignored"
        }
        
        result = schema.validate(config)
        # Extra fields should be ignored
        self.assertNotIn("extra_field", result)
        self.assertEqual(result["name"], "John")
        self.assertEqual(result["age"], 30)


class TestConvenienceFunctions(unittest.TestCase):
    """Test the convenience functions for creating schema fields."""
    
    def test_string_field(self):
        """Test String convenience function."""
        field = String(required=True, default="test")
        
        # Check that it creates a SchemaField with string type
        self.assertEqual(field.field_type, str)
        self.assertEqual(field.default, "test")
        self.assertTrue(any(isinstance(v, RequiredValidator) for v in field.validators))
    
    def test_integer_field(self):
        """Test Integer convenience function."""
        field = Integer(default=50, validators=[RangeValidator(min_value=1, max_value=100)])
        
        # Check that it creates a SchemaField with int type
        self.assertEqual(field.field_type, int)
        self.assertEqual(field.default, 50)
        self.assertTrue(any(isinstance(v, RangeValidator) for v in field.validators))
    
    def test_float_field(self):
        """Test Float convenience function."""
        field = Float(validators=[RangeValidator(min_value=0.0, max_value=1.0)])
        
        # Check that it creates a SchemaField with float type
        self.assertEqual(field.field_type, float)
        self.assertTrue(any(isinstance(v, RangeValidator) for v in field.validators))
    
    def test_boolean_field(self):
        """Test Boolean convenience function."""
        field = Boolean(default=True)
        
        # Check that it creates a SchemaField with bool type
        self.assertEqual(field.field_type, bool)
        self.assertEqual(field.default, True)
    
    def test_list_field(self):
        """Test ListField convenience function."""
        field = ListField(default=[])
        
        # Check that it creates a SchemaField with list type
        self.assertEqual(field.field_type, list)
        self.assertEqual(field.default, [])


if __name__ == '__main__':
    unittest.main()

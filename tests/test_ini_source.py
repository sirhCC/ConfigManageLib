"""
Tests for the IniSource class.
"""

import unittest
import tempfile
import os
from config_manager.sources.ini_source import IniSource
from config_manager import ConfigManager


class TestIniSource(unittest.TestCase):
    """Test the IniSource class."""

    def test_ini_source_load(self):
        """Test that INI source loads configuration correctly."""
        # Create a temporary INI file
        ini_content = """
[app]
name = MyApp
version = 1.0.0
debug = true
port = 8080

[database]
host = localhost
port = 5432
ssl_enabled = false
timeout = 30.5

[features]
auth = true
api = false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            source = IniSource(ini_file)
            config = source.load()
            
            # Test nested structure
            self.assertIn('app', config)
            self.assertIn('database', config)
            self.assertIn('features', config)
            
            # Test app section
            self.assertEqual(config['app']['name'], 'MyApp')
            self.assertEqual(config['app']['version'], '1.0.0')
            self.assertTrue(config['app']['debug'])  # Should be converted to bool
            self.assertEqual(config['app']['port'], 8080)  # Should be converted to int
            
            # Test database section
            self.assertEqual(config['database']['host'], 'localhost')
            self.assertEqual(config['database']['port'], 5432)
            self.assertFalse(config['database']['ssl_enabled'])  # Should be converted to bool
            self.assertEqual(config['database']['timeout'], 30.5)  # Should be converted to float
            
            # Test features section
            self.assertTrue(config['features']['auth'])
            self.assertFalse(config['features']['api'])
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_specific_section(self):
        """Test loading a specific section only."""
        ini_content = """
[app]
name = MyApp
debug = true
port = 8080

[database]
host = localhost
port = 5432
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            # Load only the app section
            source = IniSource(ini_file, section='app')
            config = source.load()
            
            # Should be a flat dictionary with only app section content
            self.assertEqual(config['name'], 'MyApp')
            self.assertTrue(config['debug'])
            self.assertEqual(config['port'], 8080)
            
            # Should not contain other sections
            self.assertNotIn('database', config)
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_nonexistent_section(self):
        """Test loading a section that doesn't exist."""
        ini_content = """
[app]
name = MyApp
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            source = IniSource(ini_file, section='nonexistent')
            config = source.load()
            
            # Should return empty dict for nonexistent section
            self.assertEqual(config, {})
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_with_defaults(self):
        """Test that INI source handles DEFAULT section correctly."""
        ini_content = """
[DEFAULT]
timeout = 30
debug = false

[app]
name = MyApp
port = 8080

[database]
host = localhost
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            source = IniSource(ini_file)
            config = source.load()
            
            # Should include DEFAULT section
            self.assertIn('DEFAULT', config)
            self.assertEqual(config['DEFAULT']['timeout'], 30)
            self.assertFalse(config['DEFAULT']['debug'])
            
            # Other sections should still exist
            self.assertIn('app', config)
            self.assertIn('database', config)
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_type_conversion(self):
        """Test that INI source handles type conversion correctly."""
        ini_content = """
[types]
# Boolean values
bool_true_1 = true
bool_true_2 = True
bool_true_3 = yes
bool_true_4 = YES
bool_true_5 = on
bool_true_6 = 1

bool_false_1 = false
bool_false_2 = False
bool_false_3 = no
bool_false_4 = NO
bool_false_5 = off
bool_false_6 = 0

# Numeric values
int_value = 42
negative_int = -123
float_value = 3.14159
negative_float = -2.71
scientific = 1.5e-10

# String values
string_value = hello world
quoted_string = "quoted value"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            source = IniSource(ini_file, section='types')
            config = source.load()
            
            # Test boolean true values
            self.assertTrue(config['bool_true_1'])
            self.assertTrue(config['bool_true_2'])
            self.assertTrue(config['bool_true_3'])
            self.assertTrue(config['bool_true_4'])
            self.assertTrue(config['bool_true_5'])
            self.assertTrue(config['bool_true_6'])
            
            # Test boolean false values
            self.assertFalse(config['bool_false_1'])
            self.assertFalse(config['bool_false_2'])
            self.assertFalse(config['bool_false_3'])
            self.assertFalse(config['bool_false_4'])
            self.assertFalse(config['bool_false_5'])
            self.assertFalse(config['bool_false_6'])
            
            # Test numeric values
            self.assertEqual(config['int_value'], 42)
            self.assertEqual(config['negative_int'], -123)
            self.assertEqual(config['float_value'], 3.14159)
            self.assertEqual(config['negative_float'], -2.71)
            self.assertEqual(config['scientific'], 1.5e-10)
            
            # Test string values
            self.assertEqual(config['string_value'], 'hello world')
            self.assertEqual(config['quoted_string'], '"quoted value"')
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_empty_file(self):
        """Test that INI source handles empty files gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("")  # Empty file
            ini_file = f.name
        
        try:
            source = IniSource(ini_file)
            config = source.load()
            
            # Should return empty dict for empty file
            self.assertEqual(config, {})
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_missing_file(self):
        """Test that INI source handles missing files gracefully."""
        source = IniSource('/nonexistent/path/config.ini')
        
        with self.assertRaises(FileNotFoundError):
            source.load()

    def test_ini_source_invalid_syntax(self):
        """Test that INI source handles invalid syntax gracefully."""
        # Create file with invalid INI syntax
        ini_content = """
[app
name = MyApp
this is not valid ini syntax
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            source = IniSource(ini_file)
            
            with self.assertRaises(ValueError):
                source.load()
                
        finally:
            os.unlink(ini_file)

    def test_ini_source_string_representation(self):
        """Test the string representation of IniSource."""
        source1 = IniSource('/path/to/config.ini')
        self.assertEqual(str(source1), "IniSource('/path/to/config.ini')")
        
        source2 = IniSource('/path/to/config.ini', section='app')
        self.assertEqual(str(source2), "IniSource('/path/to/config.ini', section='app')")

    def test_ini_source_with_config_manager(self):
        """Test INI source integration with ConfigManager."""
        # Create a temporary INI file
        ini_content = """
[app]
name = IniTestApp
debug = true
port = 9000

[database]
host = ini-db.example.com
port = 5432
ssl = true

[features]
auth = true
api = false
logging = true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(ini_content)
            ini_file = f.name
        
        try:
            config = ConfigManager()
            config.add_source(IniSource(ini_file))
            
            # Test accessing nested values
            self.assertEqual(config.get('app.name'), 'IniTestApp')
            self.assertTrue(config.get_bool('app.debug'))
            self.assertEqual(config.get_int('app.port'), 9000)
            
            self.assertEqual(config.get('database.host'), 'ini-db.example.com')
            self.assertEqual(config.get_int('database.port'), 5432)
            self.assertTrue(config.get_bool('database.ssl'))
            
            self.assertTrue(config.get_bool('features.auth'))
            self.assertFalse(config.get_bool('features.api'))
            self.assertTrue(config.get_bool('features.logging'))
            
        finally:
            os.unlink(ini_file)

    def test_ini_source_setup_cfg_style(self):
        """Test INI source with setup.cfg style configuration."""
        setup_cfg_content = """
[metadata]
name = myproject
version = 1.2.3
author = John Doe
author_email = john@example.com
description = A sample Python project
long_description_content_type = text/markdown

[options]
packages = find:
python_requires = >=3.7
include_package_data = true
zip_safe = false

[options.extras_require]
dev = pytest>=6.0
    flake8>=3.8
    black>=20.8
test = pytest>=6.0
    coverage>=5.0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write(setup_cfg_content)
            cfg_file = f.name
        
        try:
            source = IniSource(cfg_file)
            config = source.load()
            
            # Test metadata section
            self.assertEqual(config['metadata']['name'], 'myproject')
            self.assertEqual(config['metadata']['version'], '1.2.3')
            self.assertEqual(config['metadata']['author'], 'John Doe')
            
            # Test options section
            self.assertEqual(config['options']['packages'], 'find:')
            self.assertEqual(config['options']['python_requires'], '>=3.7')
            self.assertTrue(config['options']['include_package_data'])
            self.assertFalse(config['options']['zip_safe'])
            
            # Test subsection
            self.assertIn('options.extras_require', config)
            
        finally:
            os.unlink(cfg_file)


if __name__ == '__main__':
    unittest.main()

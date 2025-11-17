"""
Comprehensive tests for TomlSource to achieve 80%+ coverage.
"""
import unittest
import tempfile
import os
import sys
from pathlib import Path

from config_manager.sources.toml_source import TomlSource


class TestTomlSourceComprehensive(unittest.TestCase):
    """Comprehensive test suite for TomlSource."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.valid_toml_path = os.path.join(self.temp_dir, "valid.toml")
        self.pyproject_path = os.path.join(self.temp_dir, "pyproject.toml")
        self.invalid_toml_path = os.path.join(self.temp_dir, "invalid.toml")
        self.empty_toml_path = os.path.join(self.temp_dir, "empty.toml")
        self.nested_toml_path = os.path.join(self.temp_dir, "nested.toml")
        
        # Create valid TOML file
        with open(self.valid_toml_path, 'w') as f:
            f.write("""
[app]
name = "TestApp"
version = "1.0.0"
debug = true

[database]
host = "localhost"
port = 5432

[database.credentials]
username = "admin"
password = "secret"

[features]
enabled = ["auth", "api", "cache"]
""")
        
        # Create pyproject.toml style file
        with open(self.pyproject_path, 'w') as f:
            f.write("""
[tool.poetry]
name = "test-project"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.7"
""")
        
        # Create invalid TOML file
        with open(self.invalid_toml_path, 'w') as f:
            f.write("""
[section]
key = "value"
invalid syntax here
""")
        
        # Create empty TOML file
        with open(self.empty_toml_path, 'w') as f:
            f.write("")
        
        # Create nested TOML
        with open(self.nested_toml_path, 'w') as f:
            f.write("""
[level1.level2.level3]
value = "deep"
""")
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_basic_loading(self):
        """Test basic TOML loading."""
        source = TomlSource(self.valid_toml_path)
        config = source.load()
        
        self.assertIsInstance(config, dict)
        self.assertEqual(config["app"]["name"], "TestApp")
        self.assertEqual(config["database"]["port"], 5432)
        self.assertTrue(config["app"]["debug"])
        self.assertEqual(config["features"]["enabled"], ["auth", "api", "cache"])
    
    def test_load_with_path_object(self):
        """Test loading with Path object."""
        source = TomlSource(Path(self.valid_toml_path))
        config = source.load()
        
        self.assertIsInstance(config, dict)
        self.assertIn("app", config)
    
    def test_nested_sections(self):
        """Test loading nested TOML sections."""
        source = TomlSource(self.nested_toml_path)
        config = source.load()
        
        self.assertEqual(config["level1"]["level2"]["level3"]["value"], "deep")
    
    def test_empty_toml_file(self):
        """Test loading empty TOML file."""
        source = TomlSource(self.empty_toml_path)
        config = source.load()
        
        # Empty TOML returns empty dict
        self.assertEqual(config, {})
    
    def test_file_not_found(self):
        """Test error handling when file doesn't exist."""
        source = TomlSource("nonexistent.toml")
        
        # BaseSource.load() returns empty dict on error
        config = source.load()
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_invalid_toml_syntax(self):
        """Test error handling for malformed TOML."""
        source = TomlSource(self.invalid_toml_path)
        
        # BaseSource.load() returns empty dict on error
        config = source.load()
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_custom_encoding(self):
        """Test loading with custom encoding."""
        utf8_bom_path = os.path.join(self.temp_dir, "utf8_bom.toml")
        with open(utf8_bom_path, 'w', encoding='utf-8-sig') as f:
            f.write('[test]\nencoding = "utf-8-sig"\n')
        
        source = TomlSource(utf8_bom_path, encoding='utf-8-sig')
        config = source.load()
        
        self.assertEqual(config["test"]["encoding"], "utf-8-sig")
    
    def test_unicode_content(self):
        """Test loading TOML with unicode characters."""
        unicode_path = os.path.join(self.temp_dir, "unicode.toml")
        with open(unicode_path, 'w', encoding='utf-8') as f:
            f.write('[test]\nmessage = "Hello 世界 🌍"\nemoji = "✨"\n')
        
        source = TomlSource(unicode_path)
        config = source.load()
        
        self.assertEqual(config["test"]["message"], "Hello 世界 🌍")
        self.assertEqual(config["test"]["emoji"], "✨")
    
    def test_pyproject_toml_style(self):
        """Test loading pyproject.toml style file."""
        source = TomlSource(self.pyproject_path)
        config = source.load()
        
        self.assertIn("tool", config)
        self.assertIn("poetry", config["tool"])
        self.assertEqual(config["tool"]["poetry"]["name"], "test-project")
    
    def test_is_available_existing_file(self):
        """Test is_available for existing file."""
        source = TomlSource(self.valid_toml_path)
        self.assertTrue(source.is_available())
    
    def test_is_available_missing_file(self):
        """Test is_available for missing file."""
        source = TomlSource("nonexistent.toml")
        self.assertFalse(source.is_available())
    
    def test_reload_method(self):
        """Test the reload method."""
        source = TomlSource(self.valid_toml_path)
        config1 = source.load()
        
        # Modify the file
        with open(self.valid_toml_path, 'w') as f:
            f.write('[test]\nmodified = true\n')
        
        # Reload
        config2 = source.reload()
        
        self.assertNotEqual(config1, config2)
        self.assertTrue(config2["test"]["modified"])
    
    def test_get_file_path(self):
        """Test get_file_path method."""
        source = TomlSource(self.valid_toml_path)
        path = source.get_file_path()
        
        self.assertIsInstance(path, Path)
        self.assertEqual(str(path), self.valid_toml_path)
    
    def test_get_parser_info(self):
        """Test get_parser_info method."""
        source = TomlSource(self.valid_toml_path)
        info = source.get_parser_info()
        
        self.assertIn("name", info)
        self.assertIn("version", info)
        self.assertIn("module", info)
        self.assertIn("method", info)
        
        # Should be using tomllib on Python 3.11+ or tomli/toml on older versions
        self.assertIn(info["name"], ["tomllib", "tomli", "toml", "simple"])
    
    def test_validate_syntax_valid(self):
        """Test validate_syntax with valid TOML."""
        source = TomlSource(self.valid_toml_path)
        self.assertTrue(source.validate_syntax())
    
    def test_validate_syntax_invalid(self):
        """Test validate_syntax with invalid TOML."""
        source = TomlSource(self.invalid_toml_path)
        self.assertFalse(source.validate_syntax())
    
    def test_validate_syntax_missing_file(self):
        """Test validate_syntax with missing file."""
        source = TomlSource("nonexistent.toml")
        self.assertFalse(source.validate_syntax())
    
    def test_metadata_tracking(self):
        """Test that source metadata is tracked."""
        source = TomlSource(self.valid_toml_path)
        config = source.load()
        
        metadata = source.get_metadata()
        self.assertEqual(metadata.source_type, "toml")
        self.assertIsNotNone(metadata.source_path)
        self.assertIn("valid.toml", str(metadata.source_path))
        self.assertIsNotNone(metadata.last_loaded)
        self.assertGreater(metadata.load_count, 0)
    
    def test_metadata_error_tracking(self):
        """Test that errors are tracked in metadata."""
        source = TomlSource(self.invalid_toml_path)
        
        # Attempt to load (will fail)
        config = source.load()
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
        self.assertIsNotNone(metadata.last_error)
    
    def test_multiple_loads(self):
        """Test loading the same source multiple times."""
        source = TomlSource(self.valid_toml_path)
        
        config1 = source.load()
        config2 = source.load()
        config3 = source.load()
        
        self.assertEqual(config1, config2)
        self.assertEqual(config2, config3)
        
        metadata = source.get_metadata()
        self.assertEqual(metadata.load_count, 3)
    
    def test_toml_with_special_types(self):
        """Test TOML with various data types."""
        types_path = os.path.join(self.temp_dir, "types.toml")
        with open(types_path, 'w') as f:
            f.write("""
integer = 42
float = 3.14
negative = -100
string = "quoted string"
bool_true = true
bool_false = false
array = ["item1", "item2"]
date = 1979-05-27T07:32:00Z

[table]
nested = "value"
""")
        
        source = TomlSource(types_path)
        config = source.load()
        
        self.assertEqual(config["integer"], 42)
        self.assertEqual(config["float"], 3.14)
        self.assertEqual(config["negative"], -100)
        self.assertTrue(config["bool_true"])
        self.assertFalse(config["bool_false"])
        self.assertEqual(config["array"], ["item1", "item2"])
        self.assertEqual(config["table"]["nested"], "value")
    
    def test_toml_with_comments(self):
        """Test TOML with comments."""
        comments_path = os.path.join(self.temp_dir, "comments.toml")
        with open(comments_path, 'w') as f:
            f.write("""
# This is a comment
key1 = "value1"  # inline comment
# Another comment
key2 = "value2"
""")
        
        source = TomlSource(comments_path)
        config = source.load()
        
        self.assertEqual(config["key1"], "value1")
        self.assertEqual(config["key2"], "value2")
    
    def test_toml_multiline_strings(self):
        """Test TOML with multiline strings."""
        multiline_path = os.path.join(self.temp_dir, "multiline.toml")
        with open(multiline_path, 'w') as f:
            f.write('''
basic = """
Line 1
Line 2
Line 3
"""
literal = \'\'\'
C:\\Users\\nodejs\\templates
\'\'\'
''')
        
        source = TomlSource(multiline_path)
        config = source.load()
        
        self.assertIn("Line 1", config["basic"])
        self.assertIn("Line 2", config["basic"])
        self.assertIn("templates", config["literal"])
    
    def test_toml_array_of_tables(self):
        """Test TOML array of tables syntax."""
        array_path = os.path.join(self.temp_dir, "array.toml")
        with open(array_path, 'w') as f:
            f.write("""
[[products]]
name = "Hammer"
sku = 738594937

[[products]]
name = "Nail"
sku = 284758393
""")
        
        source = TomlSource(array_path)
        config = source.load()
        
        self.assertEqual(len(config["products"]), 2)
        self.assertEqual(config["products"][0]["name"], "Hammer")
        self.assertEqual(config["products"][1]["name"], "Nail")
    
    def test_toml_inline_tables(self):
        """Test TOML inline tables."""
        inline_path = os.path.join(self.temp_dir, "inline.toml")
        with open(inline_path, 'w') as f:
            f.write("""
name = { first = "Tom", last = "Preston-Werner" }
point = { x = 1, y = 2 }
""")
        
        source = TomlSource(inline_path)
        config = source.load()
        
        self.assertEqual(config["name"]["first"], "Tom")
        self.assertEqual(config["point"]["x"], 1)
    
    def test_parser_availability(self):
        """Test parser availability detection."""
        source = TomlSource(self.valid_toml_path)
        info = source.get_parser_info()
        
        # Should have detected a parser
        self.assertIsNotNone(info["name"])
        self.assertIsNotNone(info["version"])
    
    def test_parser_method_correct(self):
        """Test parser uses correct file opening method."""
        source = TomlSource(self.valid_toml_path)
        info = source.get_parser_info()
        
        # Method should be either 'r' or 'rb'
        self.assertIn(info["method"], ["r", "rb"])


if __name__ == '__main__':
    unittest.main()

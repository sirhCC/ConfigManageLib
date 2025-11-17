"""
Comprehensive tests for YamlSource to achieve 90%+ coverage.
"""
import unittest
import tempfile
import os
from pathlib import Path

try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False

from config_manager.sources.yaml_source import YamlSource


class TestYamlSourceComprehensive(unittest.TestCase):
    """Comprehensive test suite for YamlSource."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.valid_yaml_path = os.path.join(self.temp_dir, "valid.yaml")
        self.valid_yml_path = os.path.join(self.temp_dir, "config.yml")
        self.invalid_yaml_path = os.path.join(self.temp_dir, "invalid.yaml")
        self.non_dict_yaml_path = os.path.join(self.temp_dir, "non_dict.yaml")
        self.empty_yaml_path = os.path.join(self.temp_dir, "empty.yaml")
        self.nested_yaml_path = os.path.join(self.temp_dir, "nested.yaml")
        self.multi_doc_path = os.path.join(self.temp_dir, "multi.yaml")
        self.no_extension_path = os.path.join(self.temp_dir, "config")
        
        # Create valid YAML file
        with open(self.valid_yaml_path, 'w') as f:
            f.write("""
app:
  name: TestApp
  version: 1.0.0
database:
  host: localhost
  port: 5432
debug: true
features:
  - auth
  - api
""")
        
        # Create valid .yml file
        with open(self.valid_yml_path, 'w') as f:
            f.write("test: yml_extension\n")
        
        # Create invalid YAML file (malformed)
        with open(self.invalid_yaml_path, 'w') as f:
            f.write("key: value\n  bad: indentation\nthis is: [not, valid")
        
        # Create YAML with non-dict root
        with open(self.non_dict_yaml_path, 'w') as f:
            f.write("- item1\n- item2\n- item3\n")
        
        # Create empty YAML file
        with open(self.empty_yaml_path, 'w') as f:
            f.write("")
        
        # Create nested YAML
        with open(self.nested_yaml_path, 'w') as f:
            f.write("""
level1:
  level2:
    level3:
      value: deep
""")
        
        # Create multi-document YAML
        with open(self.multi_doc_path, 'w') as f:
            f.write("""
key1: value1
---
key2: value2
---
key3: value3
""")
        
        # Create file without YAML extension
        with open(self.no_extension_path, 'w') as f:
            f.write("test: no_extension\n")
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_basic_loading(self):
        """Test basic YAML loading."""
        source = YamlSource(self.valid_yaml_path)
        config = source.load()
        
        self.assertIsInstance(config, dict)
        self.assertEqual(config["app"]["name"], "TestApp")
        self.assertEqual(config["database"]["port"], 5432)
        self.assertTrue(config["debug"])
        self.assertEqual(config["features"], ["auth", "api"])
    
    def test_load_with_path_object(self):
        """Test loading with Path object."""
        source = YamlSource(Path(self.valid_yaml_path))
        config = source.load()
        
        self.assertIsInstance(config, dict)
        self.assertIn("app", config)
    
    def test_yml_extension(self):
        """Test loading file with .yml extension."""
        source = YamlSource(self.valid_yml_path)
        config = source.load()
        
        self.assertEqual(config["test"], "yml_extension")
    
    def test_nested_structure(self):
        """Test loading deeply nested YAML."""
        source = YamlSource(self.nested_yaml_path)
        config = source.load()
        
        self.assertEqual(config["level1"]["level2"]["level3"]["value"], "deep")
    
    def test_empty_yaml_file(self):
        """Test loading empty YAML file."""
        source = YamlSource(self.empty_yaml_path)
        config = source.load()
        
        # Empty YAML returns empty dict
        self.assertEqual(config, {})
    
    def test_file_not_found(self):
        """Test error handling when file doesn't exist."""
        source = YamlSource("nonexistent.yaml")
        
        # BaseSource.load() returns empty dict on error
        config = source.load()
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_invalid_yaml_syntax(self):
        """Test error handling for malformed YAML."""
        source = YamlSource(self.invalid_yaml_path)
        
        # BaseSource.load() returns empty dict on error
        config = source.load()
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_non_dict_root(self):
        """Test error handling when YAML root is not a dictionary."""
        source = YamlSource(self.non_dict_yaml_path)
        
        # BaseSource.load() returns empty dict on error
        config = source.load()
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_custom_encoding(self):
        """Test loading with custom encoding."""
        utf8_bom_path = os.path.join(self.temp_dir, "utf8_bom.yaml")
        with open(utf8_bom_path, 'w', encoding='utf-8-sig') as f:
            f.write("encoding: utf-8-sig\n")
        
        source = YamlSource(utf8_bom_path, encoding='utf-8-sig')
        config = source.load()
        
        self.assertEqual(config["encoding"], "utf-8-sig")
    
    def test_unicode_content(self):
        """Test loading YAML with unicode characters."""
        unicode_path = os.path.join(self.temp_dir, "unicode.yaml")
        with open(unicode_path, 'w', encoding='utf-8') as f:
            f.write("message: Hello 世界 🌍\nemoji: ✨\n")
        
        source = YamlSource(unicode_path)
        config = source.load()
        
        self.assertEqual(config["message"], "Hello 世界 🌍")
        self.assertEqual(config["emoji"], "✨")
    
    def test_multi_document_merge(self):
        """Test loading and merging multiple YAML documents."""
        source = YamlSource(self.multi_doc_path, load_all=True, merge_documents=True)
        config = source.load()
        
        # All documents should be merged into one dict
        self.assertEqual(config["key1"], "value1")
        self.assertEqual(config["key2"], "value2")
        self.assertEqual(config["key3"], "value3")
    
    def test_multi_document_no_merge(self):
        """Test loading multiple YAML documents without merging."""
        source = YamlSource(self.multi_doc_path, load_all=True, merge_documents=False)
        config = source.load()
        
        # Documents should be in a list
        self.assertIn("documents", config)
        self.assertIsInstance(config["documents"], list)
        self.assertEqual(len(config["documents"]), 3)
    
    def test_single_document_mode(self):
        """Test loading only first document from multi-document file."""
        source = YamlSource(self.multi_doc_path, load_all=False)
        config = source.load()
        
        # Multi-document YAML without load_all=True causes an error
        # BaseSource returns empty dict on error
        self.assertEqual(config, {})
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
    
    def test_is_available_existing_file(self):
        """Test is_available for existing file."""
        source = YamlSource(self.valid_yaml_path)
        self.assertTrue(source.is_available())
    
    def test_is_available_missing_file(self):
        """Test is_available for missing file."""
        source = YamlSource("nonexistent.yaml")
        self.assertFalse(source.is_available())
    
    def test_is_available_no_extension(self):
        """Test is_available for file without YAML extension."""
        source = YamlSource(self.no_extension_path)
        # Should still return True but log a warning
        self.assertTrue(source.is_available())
    
    def test_reload_method(self):
        """Test the reload method."""
        source = YamlSource(self.valid_yaml_path)
        config1 = source.load()
        
        # Modify the file
        with open(self.valid_yaml_path, 'w') as f:
            f.write("modified: true\n")
        
        # Reload
        config2 = source.reload()
        
        self.assertNotEqual(config1, config2)
        self.assertTrue(config2["modified"])
    
    def test_get_file_path(self):
        """Test get_file_path method."""
        source = YamlSource(self.valid_yaml_path)
        path = source.get_file_path()
        
        self.assertIsInstance(path, Path)
        self.assertEqual(str(path), self.valid_yaml_path)
    
    def test_has_pyyaml(self):
        """Test has_pyyaml method."""
        source = YamlSource(self.valid_yaml_path)
        result = source.has_pyyaml()
        
        self.assertIsInstance(result, bool)
        # Should match the global HAS_PYYAML
        self.assertEqual(result, HAS_PYYAML)
    
    def test_get_parser_info(self):
        """Test get_parser_info method."""
        source = YamlSource(self.valid_yaml_path)
        info = source.get_parser_info()
        
        self.assertIn("parser", info)
        self.assertIn("version", info)
        self.assertIn("features", info)
        self.assertTrue(info["features"]["safe_loading"])
    
    def test_validate_syntax_valid(self):
        """Test validate_syntax with valid YAML."""
        source = YamlSource(self.valid_yaml_path)
        self.assertTrue(source.validate_syntax())
    
    def test_validate_syntax_invalid(self):
        """Test validate_syntax with invalid YAML."""
        source = YamlSource(self.invalid_yaml_path)
        self.assertFalse(source.validate_syntax())
    
    def test_validate_syntax_missing_file(self):
        """Test validate_syntax with missing file."""
        source = YamlSource("nonexistent.yaml")
        self.assertFalse(source.validate_syntax())
    
    def test_validate_syntax_multi_document(self):
        """Test validate_syntax with multi-document YAML."""
        source = YamlSource(self.multi_doc_path, load_all=True)
        self.assertTrue(source.validate_syntax())
    
    def test_metadata_tracking(self):
        """Test that source metadata is tracked."""
        source = YamlSource(self.valid_yaml_path)
        config = source.load()
        
        metadata = source.get_metadata()
        self.assertEqual(metadata.source_type, "yaml")
        self.assertIsNotNone(metadata.source_path)
        self.assertIn("valid.yaml", str(metadata.source_path))
        self.assertIsNotNone(metadata.last_loaded)
        self.assertGreater(metadata.load_count, 0)
    
    def test_metadata_error_tracking(self):
        """Test that errors are tracked in metadata."""
        source = YamlSource(self.invalid_yaml_path)
        
        # Attempt to load (will fail)
        config = source.load()
        
        metadata = source.get_metadata()
        self.assertGreater(metadata.error_count, 0)
        self.assertIsNotNone(metadata.last_error)
    
    def test_multiple_loads(self):
        """Test loading the same source multiple times."""
        source = YamlSource(self.valid_yaml_path)
        
        config1 = source.load()
        config2 = source.load()
        config3 = source.load()
        
        self.assertEqual(config1, config2)
        self.assertEqual(config2, config3)
        
        metadata = source.get_metadata()
        self.assertEqual(metadata.load_count, 3)
    
    def test_yaml_with_special_types(self):
        """Test YAML with various data types."""
        types_path = os.path.join(self.temp_dir, "types.yaml")
        with open(types_path, 'w') as f:
            f.write("""
integer: 42
float: 3.14
negative: -100
null_value: null
true_bool: true
false_bool: false
string: "quoted string"
unquoted: unquoted string
list:
  - item1
  - item2
dict:
  nested: value
""")
        
        source = YamlSource(types_path)
        config = source.load()
        
        self.assertEqual(config["integer"], 42)
        self.assertEqual(config["float"], 3.14)
        self.assertEqual(config["negative"], -100)
        self.assertIsNone(config["null_value"])
        self.assertTrue(config["true_bool"])
        self.assertFalse(config["false_bool"])
        self.assertEqual(config["list"], ["item1", "item2"])
        self.assertEqual(config["dict"]["nested"], "value")
    
    def test_yaml_with_comments(self):
        """Test YAML with comments."""
        comments_path = os.path.join(self.temp_dir, "comments.yaml")
        with open(comments_path, 'w') as f:
            f.write("""
# This is a comment
key1: value1  # inline comment
# Another comment
key2: value2
""")
        
        source = YamlSource(comments_path)
        config = source.load()
        
        self.assertEqual(config["key1"], "value1")
        self.assertEqual(config["key2"], "value2")
    
    def test_yaml_multiline_strings(self):
        """Test YAML with multiline strings."""
        multiline_path = os.path.join(self.temp_dir, "multiline.yaml")
        with open(multiline_path, 'w') as f:
            f.write("""
literal: |
  Line 1
  Line 2
  Line 3
folded: >
  This is a long
  line that will
  be folded
""")
        
        source = YamlSource(multiline_path)
        config = source.load()
        
        self.assertIn("Line 1", config["literal"])
        self.assertIn("Line 2", config["literal"])
        self.assertIsInstance(config["folded"], str)


if __name__ == '__main__':
    unittest.main()

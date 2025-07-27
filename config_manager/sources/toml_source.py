"""
TOML configuration source for ConfigManager.

This module provides support for loading configuration from TOML files,
with fallback to a simple TOML parser if the 'tomli' package is not available.
"""

import os
from typing import Dict, Any
from .base import BaseSource


class TomlSource(BaseSource):
    """
    Loads configuration from a TOML file.
    
    TOML (Tom's Obvious, Minimal Language) is a configuration file format
    that's easy to read due to obvious semantics. It's becoming increasingly
    popular in the Python ecosystem, especially for pyproject.toml files.
    
    This source attempts to use the 'tomli' library for parsing, but falls
    back to a simple parser if it's not available.
    """

    def __init__(self, file_path: str):
        """
        Initialize the TOML source.
        
        Args:
            file_path: Path to the TOML file
        """
        self.file_path = file_path
        self._toml_parser = self._get_toml_parser()
    
    def _get_toml_parser(self):
        """Get the best available TOML parser."""
        try:
            # Try to use tomli (recommended for Python 3.11+)
            import tomli  # type: ignore
            return ("tomli", tomli)
        except ImportError:
            try:
                # Try toml (older but widely available)
                import toml  # type: ignore
                return ("toml", toml)
            except ImportError:
                # Fall back to simple parser
                return ("simple", None)
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the TOML file.
        
        Returns:
            Dictionary containing the configuration data.
            
        Raises:
            FileNotFoundError: If the TOML file doesn't exist.
            ValueError: If the TOML file contains invalid syntax.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"TOML file not found: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                parser_name, parser = self._toml_parser
                
                if parser_name == "tomli":
                    # tomli expects bytes
                    return parser.loads(content)  # type: ignore
                elif parser_name == "toml":
                    # toml works with strings
                    return parser.loads(content)  # type: ignore
                else:
                    # Use simple fallback parser
                    return self._simple_toml_parse(content)
                    
        except Exception as e:
            if "tomli" in str(e) or "toml" in str(e):
                # TOML parsing error
                raise ValueError(f"Invalid TOML syntax in {self.file_path}: {e}")
            else:
                # Other error (file read, etc.)
                raise
    
    def _simple_toml_parse(self, content: str) -> Dict[str, Any]:
        """
        Simple TOML parser fallback for basic TOML files.
        
        This is a minimal implementation that handles:
        - Key-value pairs
        - Basic sections [section]
        - Comments (lines starting with #)
        - String, number, and boolean values
        - Arrays (simple lists)
        
        Note: This does not support all TOML features like:
        - Nested tables
        - Inline tables
        - Multi-line strings
        - Complex date/time formats
        
        Args:
            content: The TOML file content as a string
            
        Returns:
            Dictionary representation of the TOML data
        """
        result = {}
        current_section = result
        section_path = []
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Handle sections [section.name]
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip()
                
                # Handle nested sections
                if '.' in section_name:
                    section_parts = section_name.split('.')
                    current_section = result
                    section_path = []
                    
                    for part in section_parts:
                        section_path.append(part)
                        if part not in current_section:
                            current_section[part] = {}
                        current_section = current_section[part]
                else:
                    # Simple section
                    section_path = [section_name]
                    if section_name not in result:
                        result[section_name] = {}
                    current_section = result[section_name]
                continue
            
            # Handle key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove inline comments (but not from quoted strings)
                if '#' in value and not self._is_in_quotes(value, value.find('#')):
                    comment_pos = value.find('#')
                    value = value[:comment_pos].strip()
                
                # Parse the value
                parsed_value = self._parse_toml_value(value, line_num)
                current_section[key] = parsed_value
            else:
                # Invalid line
                raise ValueError(f"Invalid TOML syntax at line {line_num}: {line}")
        
        return result
    
    def _is_in_quotes(self, text: str, pos: int) -> bool:
        """
        Check if a position in text is inside quotes.
        
        Args:
            text: The text to check
            pos: The position to check
            
        Returns:
            True if the position is inside quotes
        """
        in_single_quotes = False
        in_double_quotes = False
        
        for i, char in enumerate(text[:pos]):
            if char == '"' and not in_single_quotes:
                in_double_quotes = not in_double_quotes
            elif char == "'" and not in_double_quotes:
                in_single_quotes = not in_single_quotes
        
        return in_single_quotes or in_double_quotes
    
    def _parse_toml_value(self, value: str, line_num: int) -> Any:
        """
        Parse a TOML value from a string.
        
        Args:
            value: The value string to parse
            line_num: Line number for error reporting
            
        Returns:
            The parsed Python value
        """
        value = value.strip()
        
        # Handle strings (quoted)
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]  # Remove quotes
        
        # Handle arrays [item1, item2, item3]
        if value.startswith('[') and value.endswith(']'):
            array_content = value[1:-1].strip()
            if not array_content:
                return []
            
            items = []
            for item in array_content.split(','):
                item = item.strip()
                if item:
                    items.append(self._parse_toml_value(item, line_num))
            return items
        
        # Handle booleans
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        # Handle numbers
        try:
            # Try integer first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except ValueError:
            pass
        
        # If we can't parse it, treat as unquoted string
        return value
    
    def __str__(self) -> str:
        """String representation of the TOML source."""
        parser_name, _ = self._toml_parser
        return f"TomlSource(file_path='{self.file_path}', parser='{parser_name}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the TOML source."""
        return self.__str__()

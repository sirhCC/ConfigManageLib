"""
🔧 Enterprise-grade TOML configuration source for ConfigManager.

This module provides robust TOML file loading with comprehensive error handling,
multiple parser support, and enterprise-grade monitoring capabilities.
"""

import os
from typing import Dict, Any, Union, Optional, Tuple
from pathlib import Path
import logging

from .base import BaseSource

# Configure logger for this module
logger = logging.getLogger(__name__)


class TomlSource(BaseSource):
    """
    Enterprise-grade TOML configuration source with advanced parsing capabilities.
    
    TOML (Tom's Obvious, Minimal Language) is a configuration file format
    that's easy to read due to obvious semantics. It's increasingly popular
    in the Python ecosystem, especially for pyproject.toml files.
    
    Features:
    - Multiple parser support (tomli, tomllib, toml, simple fallback)
    - Intelligent parser selection based on Python version
    - Comprehensive error handling with detailed error messages
    - Performance monitoring and metadata tracking
    - Support for both .toml and custom extensions
    - Graceful fallback parsing for maximum compatibility
    
    Example:
        ```python
        # Basic usage
        source = TomlSource('pyproject.toml')
        config = source.load()
        
        # With custom encoding
        source = TomlSource('config.toml', encoding='utf-8-sig')
        
        # Check parser info
        parser_info = source.get_parser_info()
        print(f"Using parser: {parser_info['name']}")
        ```
    """

    def __init__(
        self, 
        file_path: Union[str, Path], 
        encoding: str = "utf-8"
    ):
        """
        Initialize the TOML configuration source.
        
        Args:
            file_path: Path to the TOML configuration file
            encoding: Text encoding for the file (default: utf-8)
        """
        super().__init__(
            source_type="toml", 
            source_path=file_path,
            encoding=encoding
        )
        self._file_path = Path(file_path)
        self._parser_info = self._get_best_toml_parser()
        
        # Log the parser being used
        self._logger.debug(
            f"Initialized TOML source with {self._parser_info['name']} parser "
            f"(version: {self._parser_info['version']})"
        )

    def _get_best_toml_parser(self) -> Dict[str, Any]:
        """
        Get the best available TOML parser for this Python version.
        
        Returns:
            Dictionary with parser information including name, module, and version
        """
        import sys
        
        # Python 3.11+ has built-in tomllib
        if sys.version_info >= (3, 11):
            try:
                import tomllib
                return {
                    "name": "tomllib",
                    "module": tomllib,
                    "version": "built-in",
                    "method": "r"  # tomllib.loads() expects string, not bytes
                }
            except ImportError:
                pass
        
        # Try tomli (recommended for older Python versions)
        try:
            import tomli
            return {
                "name": "tomli",
                "module": tomli,
                "version": getattr(tomli, "__version__", "unknown"),
                "method": "rb"  # tomli also requires binary mode
            }
        except ImportError:
            pass
        
        # Try legacy toml library
        try:
            import toml
            return {
                "name": "toml",
                "module": toml,
                "version": getattr(toml, "__version__", "unknown"),
                "method": "r"  # toml uses text mode
            }
        except ImportError:
            pass
        
        # Fallback to simple parser
        return {
            "name": "simple",
            "module": None,
            "version": "fallback",
            "method": "r"
        }

    def _do_load(self) -> Dict[str, Any]:
        """
        Load and parse the TOML configuration file.
        
        Returns:
            Dictionary containing the parsed TOML data
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the TOML syntax is invalid
            PermissionError: If the file cannot be read
        """
        self._logger.debug(f"Loading TOML configuration from: {self._file_path}")
        
        try:
            # Read file with appropriate mode based on parser
            file_mode = self._parser_info["method"]
            encoding = None if file_mode == "rb" else (self._metadata.encoding or "utf-8")
            
            with open(self._file_path, file_mode, encoding=encoding) as f:
                content = f.read()
            
            # Parse TOML with selected parser
            config_data = self._parse_toml_content(content)
            
            # Validate that we got a dictionary
            if not isinstance(config_data, dict):
                raise ValueError(
                    f"TOML root must be a table/dictionary, got {type(config_data).__name__}"
                )
            
            self._logger.info(
                f"Successfully loaded {len(config_data)} configuration keys from TOML file "
                f"using {self._parser_info['name']} parser"
            )
            
            return config_data
            
        except FileNotFoundError:
            self._logger.error(f"TOML configuration file not found: {self._file_path}")
            raise
            
        except ValueError as e:
            # TOML parsing errors
            self._logger.error(f"Invalid TOML syntax in {self._file_path}: {e}")
            raise
            
        except PermissionError:
            self._logger.error(f"Permission denied reading configuration file: {self._file_path}")
            raise

    def _parse_toml_content(self, content: Union[str, bytes]) -> Dict[str, Any]:
        """Parse TOML content using the selected parser."""
        parser_name = self._parser_info["name"]
        parser_module = self._parser_info["module"]
        encoding = self._metadata.encoding or "utf-8"
        
        try:
            if parser_name == "tomllib":
                # tomllib.loads() expects string
                if isinstance(content, bytes):
                    content_str = content.decode(encoding)
                elif isinstance(content, str):
                    content_str = content
                else:
                    content_str = str(content)
                return parser_module.loads(content_str)
                
            elif parser_name == "tomli":
                # tomli.loads() expects bytes  
                if isinstance(content, str):
                    content_bytes = content.encode(encoding)
                elif isinstance(content, bytes):
                    content_bytes = content
                else:
                    content_bytes = str(content).encode(encoding)
                return parser_module.loads(content_bytes)
                
            elif parser_name == "toml":
                # Legacy toml parser expects string and uses .loads()
                if isinstance(content, bytes):
                    content_str = content.decode(encoding)
                elif isinstance(content, str):
                    content_str = content
                else:
                    content_str = str(content)
                return parser_module.loads(content_str)
                
            else:
                # Simple fallback parser expects string
                if isinstance(content, bytes):
                    content_str = content.decode(encoding)
                elif isinstance(content, str):
                    content_str = content
                else:
                    content_str = str(content)
                return self._simple_toml_parse(content_str)
                
        except Exception as e:
            # Re-raise with more context
            raise ValueError(f"TOML parsing failed with {parser_name}: {e}")

    def _simple_toml_parse(self, content: str) -> Dict[str, Any]:
        """
        Simple TOML parser fallback for basic TOML files.
        
        This is a minimal implementation that handles:
        - Key-value pairs
        - Basic sections [section]
        - Comments (lines starting with #)
        - String, number, and boolean values
        - Simple arrays
        
        Args:
            content: The TOML file content as a string
            
        Returns:
            Dictionary representation of the TOML data
        """
        result = {}
        current_section = result
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Handle section headers [section]
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip()
                if '.' in section_name:
                    # Handle nested sections like [tool.myapp]
                    parts = section_name.split('.')
                    current_section = result
                    for part in parts:
                        if part not in current_section:
                            current_section[part] = {}
                        current_section = current_section[part]
                else:
                    # Simple section
                    if section_name not in result:
                        result[section_name] = {}
                    current_section = result[section_name]
                continue
            
            # Handle key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Parse the value
                parsed_value = self._parse_simple_value(value)
                current_section[key] = parsed_value
        
        return result

    def _parse_simple_value(self, value: str) -> Any:
        """Parse a simple TOML value."""
        value = value.strip()
        
        # String values (quoted)
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Boolean values
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        # Array values (simple)
        if value.startswith('[') and value.endswith(']'):
            array_content = value[1:-1].strip()
            if not array_content:
                return []
            items = [item.strip() for item in array_content.split(',')]
            return [self._parse_simple_value(item) for item in items if item]
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string if nothing else matches
        return value

    def is_available(self) -> bool:
        """
        Check if the TOML configuration file is available and readable.
        
        Returns:
            True if the file exists and appears to be valid TOML
        """
        if not super().is_available():
            return False
        
        # Check file extension (warning only, not blocking)
        if self._file_path.suffix.lower() != '.toml':
            self._logger.warning(
                f"File {self._file_path} doesn't have .toml extension, "
                f"but will attempt to parse as TOML"
            )
        
        return True

    def reload(self) -> Dict[str, Any]:
        """Convenience method to reload the configuration file."""
        self._logger.info(f"Reloading TOML configuration from: {self._file_path}")
        return self.load()

    def get_file_path(self) -> Path:
        """Get the path to the TOML configuration file."""
        return self._file_path

    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about the TOML parser being used."""
        return self._parser_info.copy()

    def validate_syntax(self) -> bool:
        """
        Validate TOML syntax without loading the full configuration.
        
        Returns:
            True if the TOML syntax is valid, False otherwise
        """
        try:
            with open(self._file_path, 'r', encoding=self._metadata.encoding or "utf-8") as f:
                content = f.read()
            
            # Try to parse with current parser
            self._parse_toml_content(content)
            return True
        except (ValueError, FileNotFoundError, PermissionError):
            return False

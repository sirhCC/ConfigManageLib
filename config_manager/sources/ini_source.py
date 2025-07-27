"""
🔧 Enterprise-grade INI/CFG configuration source for ConfigManager.

This module provides robust INI/CFG file loading with comprehensive error handling,
section management, and enterprise-grade monitoring capabilities.
"""

import configparser
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

from .base import BaseSource

# Configure logger for this module
logger = logging.getLogger(__name__)


class IniSource(BaseSource):
    """
    Enterprise-grade INI/CFG configuration source with advanced parsing capabilities.
    
    This source supports standard INI file format with sections and key-value pairs.
    It can load all sections as nested dictionaries or focus on a specific section.
    
    Features:
    - Comprehensive section management (load all or specific sections)
    - Automatic type conversion (bool, int, float, strings)
    - Support for common INI file variations
    - Robust error handling with detailed error messages
    - Performance monitoring and metadata tracking
    - Support for various encoding formats
    
    Common use cases:
    - setup.cfg files
    - pytest.ini configuration
    - uwsgi.ini settings
    - application.ini files
    
    Example:
        ```python
        # Load all sections
        source = IniSource('config.ini')
        config = source.load()  # {'section1': {...}, 'section2': {...}}
        
        # Load specific section only
        source = IniSource('setup.cfg', section='tool:pytest')
        config = source.load()  # Flat dict with pytest config
        
        # Custom encoding
        source = IniSource('config.ini', encoding='utf-8-sig')
        ```
    """

    def __init__(
        self, 
        file_path: Union[str, Path], 
        section: Optional[str] = None, 
        encoding: str = 'utf-8'
    ):
        """
        Initialize the INI configuration source.
        
        Args:
            file_path: Path to the INI/CFG file
            section: If specified, only load this section (returns flat dict).
                    If None, load all sections as nested dict.
            encoding: File encoding (default: utf-8)
        """
        super().__init__(
            source_type="ini",
            source_path=file_path,
            encoding=encoding
        )
        self._file_path = Path(file_path)
        self._section = section
        
        self._logger.debug(
            f"Initialized INI source: {file_path}, "
            f"section: {section or 'all'}, encoding: {encoding}"
        )

    def _do_load(self) -> Dict[str, Any]:
        """
        Load and parse the INI configuration file.
        
        Returns:
            Dictionary containing the parsed INI data
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the INI syntax is invalid
            PermissionError: If the file cannot be read
        """
        self._logger.debug(f"Loading INI configuration from: {self._file_path}")
        
        try:
            # Create parser with enhanced configuration
            parser = configparser.ConfigParser(
                interpolation=configparser.ExtendedInterpolation(),
                allow_no_value=True
            )
            
            # Read the INI file
            parser.read(self._file_path, encoding=self._metadata.encoding)
            
            if self._section:
                # Return only the specified section as a flat dictionary
                return self._load_specific_section(parser)
            else:
                # Return all sections as nested dictionary
                return self._load_all_sections(parser)
                
        except FileNotFoundError:
            self._logger.error(f"INI configuration file not found: {self._file_path}")
            raise
            
        except configparser.Error as e:
            self._logger.error(f"Invalid INI syntax in {self._file_path}: {e}")
            raise ValueError(f"Invalid INI syntax in {self._file_path}: {e}")
            
        except PermissionError:
            self._logger.error(f"Permission denied reading configuration file: {self._file_path}")
            raise

    def _load_specific_section(self, parser: configparser.ConfigParser) -> Dict[str, Any]:
        """Load a specific section from the INI file."""
        if self._section not in parser:
            self._logger.warning(f"Section '{self._section}' not found in INI file")
            return {}
        
        section_dict = {}
        for key, value in parser[self._section].items():
            section_dict[key] = self._convert_ini_value(value)
        
        self._logger.info(f"Loaded section '{self._section}' with {len(section_dict)} keys")
        return section_dict

    def _load_all_sections(self, parser: configparser.ConfigParser) -> Dict[str, Any]:
        """Load all sections from the INI file."""
        result = {}
        total_keys = 0
        
        # Load regular sections
        for section_name in parser.sections():
            section_dict = {}
            for key, value in parser[section_name].items():
                section_dict[key] = self._convert_ini_value(value)
            result[section_name] = section_dict
            total_keys += len(section_dict)
        
        # Include DEFAULT section values if they exist
        if parser.defaults():
            default_dict = {}
            for key, value in parser.defaults().items():
                default_dict[key] = self._convert_ini_value(value)
            result['DEFAULT'] = default_dict
            total_keys += len(default_dict)
        
        self._logger.info(f"Loaded {len(result)} sections with {total_keys} total keys")
        return result

    def _convert_ini_value(self, value: str) -> Any:
        """
        Convert INI string values to appropriate Python types.
        
        Supports:
        - Booleans: true/false, yes/no, on/off, 1/0
        - Integers: numeric strings
        - Floats: decimal numbers
        - Lists: comma-separated values
        
        Args:
            value: The string value from INI file
            
        Returns:
            The converted value in appropriate Python type
        """
        if not isinstance(value, str):
            return value
        
        value = value.strip()
        
        # Handle empty values
        if not value:
            return ""
        
        # Boolean values (INI standard)
        lower_value = value.lower()
        if lower_value in ('true', 'yes', 'on', '1'):
            return True
        elif lower_value in ('false', 'no', 'off', '0'):
            return False
        
        # List values (comma-separated)
        if ',' in value:
            items = [item.strip() for item in value.split(',')]
            return [self._convert_ini_value(item) for item in items if item.strip()]
        
        # Numeric values
        try:
            # Try integer first
            if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                return int(value)
            
            # Try float
            float_val = float(value)
            return float_val
        except ValueError:
            pass
        
        # Return as string
        return value

    def is_available(self) -> bool:
        """
        Check if the INI configuration file is available and readable.
        
        Returns:
            True if the file exists and appears to be valid INI
        """
        if not super().is_available():
            return False
        
        # Check file extension (warning only, not blocking)
        valid_extensions = ['.ini', '.cfg', '.conf']
        if self._file_path.suffix.lower() not in valid_extensions:
            self._logger.warning(
                f"File {self._file_path} doesn't have common INI extension "
                f"({', '.join(valid_extensions)}), but will attempt to parse as INI"
            )
        
        return True

    def reload(self) -> Dict[str, Any]:
        """Convenience method to reload the configuration file."""
        self._logger.info(f"Reloading INI configuration from: {self._file_path}")
        return self.load()

    def get_file_path(self) -> Path:
        """Get the path to the INI configuration file."""
        return self._file_path

    def get_section_info(self) -> Dict[str, Any]:
        """
        Get information about the INI file sections.
        
        Returns:
            Dictionary with section information
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(self._file_path, encoding=self._metadata.encoding)
            
            return {
                "target_section": self._section,
                "available_sections": list(parser.sections()),
                "has_defaults": bool(parser.defaults()),
                "total_sections": len(parser.sections())
            }
        except (FileNotFoundError, PermissionError, configparser.Error):
            return {
                "target_section": self._section,
                "available_sections": [],
                "has_defaults": False,
                "total_sections": 0,
                "error": "Cannot read INI file"
            }

    def validate_syntax(self) -> bool:
        """
        Validate INI syntax without loading the full configuration.
        
        Returns:
            True if the INI syntax is valid, False otherwise
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(self._file_path, encoding=self._metadata.encoding)
            return True
        except (configparser.Error, FileNotFoundError, PermissionError):
            return False

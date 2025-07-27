"""
INI/CFG configuration source for ConfigManager.

This module provides support for loading configuration from INI/CFG files,
commonly used in Python projects (setup.cfg, pytest.ini, tox.ini, etc.).
"""

import configparser
import os
from typing import Dict, Any, Optional, Union
from .base import BaseSource


class IniSource(BaseSource):
    """
    Loads configuration from INI/CFG files.
    
    This source supports standard INI file format with sections and key-value pairs.
    It can load all sections as nested dictionaries or focus on a specific section.
    
    Common use cases:
    - setup.cfg files
    - pytest.ini configuration
    - uwsgi.ini settings
    - application.ini files
    """

    def __init__(self, file_path: str, section: Optional[str] = None, encoding: str = 'utf-8'):
        """
        Initialize the INI source.
        
        Args:
            file_path: Path to the INI/CFG file
            section: If specified, only load this section (returns flat dict).
                    If None, load all sections as nested dict.
            encoding: File encoding (default: utf-8)
        """
        self.file_path = file_path
        self.section = section
        self.encoding = encoding
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the INI file.
        
        Returns:
            Dictionary containing the configuration data.
            If section is specified, returns flat dict of that section.
            If section is None, returns nested dict with sections as top-level keys.
            
        Raises:
            FileNotFoundError: If the INI file doesn't exist.
            ValueError: If the INI file contains invalid syntax.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"INI file not found: {self.file_path}")
        
        try:
            parser = configparser.ConfigParser()
            parser.read(self.file_path, encoding=self.encoding)
            
            if self.section:
                # Return only the specified section as a flat dictionary
                if self.section not in parser:
                    return {}  # Section doesn't exist, return empty dict
                
                section_dict = {}
                for key, value in parser[self.section].items():
                    section_dict[key] = self._convert_value(value)
                return section_dict
            else:
                # Return all sections as nested dictionary
                result = {}
                for section_name in parser.sections():
                    section_dict = {}
                    for key, value in parser[section_name].items():
                        section_dict[key] = self._convert_value(value)
                    result[section_name] = section_dict
                
                # Also include DEFAULT section values if they exist
                if parser.defaults():
                    default_dict = {}
                    for key, value in parser.defaults().items():
                        default_dict[key] = self._convert_value(value)
                    result['DEFAULT'] = default_dict
                
                return result
                
        except configparser.Error as e:
            raise ValueError(f"Invalid INI syntax in {self.file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading INI file {self.file_path}: {e}")
    
    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """
        Convert string values to appropriate Python types.
        
        Args:
            value: String value from INI file
            
        Returns:
            Converted value (str, int, float, or bool)
        """
        # Handle boolean values (common in INI files)
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Try to convert to number
        try:
            # Try integer first
            if '.' not in value and 'e' not in value.lower():
                return int(value)
            else:
                # Try float
                return float(value)
        except ValueError:
            pass
        
        # Return as string if no conversion possible
        return value
    
    def __str__(self) -> str:
        """String representation of the INI source."""
        if self.section:
            return f"IniSource('{self.file_path}', section='{self.section}')"
        else:
            return f"IniSource('{self.file_path}')"

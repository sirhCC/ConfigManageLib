"""
🔧 Enterprise-grade environment variable configuration source for ConfigManager.

This module provides robust environment variable loading with comprehensive parsing,
nested structure support, and enterprise-grade monitoring capabilities.
"""

import os
import re
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path
import logging

from .base import BaseSource

# Configure logger for this module
logger = logging.getLogger(__name__)


class EnvironmentSource(BaseSource):
    """
    Enterprise-grade environment variable source with advanced parsing capabilities.
    
    Features:
    - Flexible prefix matching with multiple prefixes support
    - Automatic type conversion (bool, int, float, lists)
    - Nested configuration structure via underscore notation
    - Environment variable validation and sanitization
    - Support for common environment patterns (DATABASE_URL, etc.)
    - Performance monitoring and metadata tracking
    - Case-insensitive and case-sensitive modes
    
    Example:
        ```python
        # Basic usage with prefix
        source = EnvironmentSource(prefix='APP_')
        config = source.load()  # Loads APP_DATABASE_HOST, APP_DEBUG, etc.
        
        # Multiple prefixes
        source = EnvironmentSource(prefixes=['APP_', 'API_', 'DB_'])
        
        # Nested configuration
        # APP_DATABASE_HOST=localhost -> {'database': {'host': 'localhost'}}
        source = EnvironmentSource(prefix='APP_', nested=True)
        
        # Case insensitive matching
        source = EnvironmentSource(prefix='app_', case_sensitive=False)
        ```
    """

    def __init__(
        self,
        prefix: str = "",
        prefixes: Optional[List[str]] = None,
        nested: bool = True,
        case_sensitive: bool = True,
        strip_prefix: bool = True,
        parse_values: bool = True,
        list_separator: str = ","
    ):
        """
        Initialize the environment variable configuration source.
        
        Args:
            prefix: Single prefix to match (e.g., "APP_")
            prefixes: List of prefixes to match (overrides prefix if provided)
            nested: Whether to create nested structures from underscore notation
            case_sensitive: Whether prefix matching is case-sensitive
            strip_prefix: Whether to remove prefix from resulting keys
            parse_values: Whether to parse values to appropriate types
            list_separator: Separator for parsing list values
        """
        super().__init__(
            source_type="environment",
            source_path=None,  # Environment variables don't have a file path
            encoding="utf-8"  # Default encoding for environment processing
        )
        
        # Handle prefix configuration
        if prefixes is not None:
            self._prefixes = prefixes
        elif prefix:
            self._prefixes = [prefix]
        else:
            self._prefixes = []
        
        self._nested = nested
        self._case_sensitive = case_sensitive
        self._strip_prefix = strip_prefix
        self._parse_values = parse_values
        self._list_separator = list_separator
        
        # Prepare prefix patterns for matching
        self._prefix_patterns = self._prepare_prefix_patterns()
        
        self._logger.debug(
            f"Initialized environment source with prefixes: {self._prefixes}, "
            f"nested: {nested}, case_sensitive: {case_sensitive}"
        )

    def _prepare_prefix_patterns(self) -> List[str]:
        """Prepare prefix patterns for efficient matching."""
        if not self._case_sensitive:
            return [prefix.lower() for prefix in self._prefixes]
        return self._prefixes.copy()

    def _do_load(self) -> Dict[str, Any]:
        """
        Load and parse environment variables.
        
        Returns:
            Dictionary containing the environment variable configuration
        """
        self._logger.debug("Loading configuration from environment variables")
        
        config = {}
        matched_vars = 0
        
        # Get all environment variables
        env_vars = dict(os.environ)
        
        # Process each environment variable
        for env_key, env_value in env_vars.items():
            processed_key = self._process_env_var(env_key, env_value, config)
            if processed_key:
                matched_vars += 1
        
        self._logger.info(
            f"Successfully loaded {matched_vars} environment variables "
            f"(from {len(env_vars)} total environment variables)"
        )
        
        return config

    def _process_env_var(self, env_key: str, env_value: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Process a single environment variable.
        
        Returns:
            The processed key if the variable was matched and processed, None otherwise
        """
        # Check if this environment variable matches any of our prefixes
        matched_prefix = self._find_matching_prefix(env_key)
        if matched_prefix is None:
            return None
        
        # Get the key without the prefix
        if self._strip_prefix:
            config_key = env_key[len(matched_prefix):]
        else:
            config_key = env_key
        
        # Skip empty keys
        if not config_key:
            return None
        
        # Parse the value
        parsed_value = self._parse_env_value(env_value) if self._parse_values else env_value
        
        # Normalize key to lowercase for consistent access
        normalized_key = config_key.lower()
        
        # Handle nested structure
        if self._nested and '_' in normalized_key:
            self._set_nested_value(config, normalized_key, parsed_value)
        else:
            config[normalized_key] = parsed_value
        
        self._logger.debug(f"Processed {env_key} -> {normalized_key} = {parsed_value}")
        return normalized_key

    def _find_matching_prefix(self, env_key: str) -> Optional[str]:
        """Find the first matching prefix for an environment variable."""
        if not self._prefixes:
            return ""  # No prefix means match all variables
        
        check_key = env_key if self._case_sensitive else env_key.lower()
        
        for i, prefix in enumerate(self._prefixes):
            check_prefix = self._prefix_patterns[i]
            if check_key.startswith(check_prefix):
                return self._prefixes[i]  # Return original prefix, not lowercased
        
        return None

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse an environment variable value to an appropriate Python type.
        
        Supports:
        - Booleans: true/false, yes/no, on/off, 1/0
        - Integers: numeric strings
        - Floats: decimal numbers
        - Lists: comma-separated values (or custom separator)
        - URLs: special handling for database URLs, etc.
        
        Args:
            value: The string value to parse
            
        Returns:
            The parsed value in appropriate Python type
        """
        if not isinstance(value, str):
            return value
        
        value = value.strip()
        
        # Handle empty values
        if not value:
            return ""
        
        # Boolean values
        bool_result = self._parse_boolean(value)
        if bool_result is not None:
            return bool_result
        
        # List values (check for separator)
        if self._list_separator in value:
            items = [item.strip() for item in value.split(self._list_separator)]
            # Recursively parse each item
            return [self._parse_env_value(item) for item in items if item.strip()]
        
        # Numeric values
        numeric_result = self._parse_numeric(value)
        if numeric_result is not None:
            return numeric_result
        
        # Special URL patterns (database URLs, Redis URLs, etc.)
        if self._looks_like_url(value):
            return value  # Keep URLs as strings
        
        # Return as string
        return value

    def _parse_boolean(self, value: str) -> Optional[bool]:
        """Parse boolean values from strings."""
        lower_value = value.lower()
        
        # True values
        if lower_value in ('true', 'yes', 'y', 'on', '1', 'enable', 'enabled'):
            return True
        
        # False values
        if lower_value in ('false', 'no', 'n', 'off', '0', 'disable', 'disabled'):
            return False
        
        return None

    def _parse_numeric(self, value: str) -> Union[int, float, None]:
        """Parse numeric values from strings."""
        try:
            # Try integer first
            if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                return int(value)
            
            # Try float
            return float(value)
        except ValueError:
            return None

    def _looks_like_url(self, value: str) -> bool:
        """Check if a value looks like a URL."""
        url_patterns = [
            r'^https?://',
            r'^ftp://',
            r'^postgresql://',
            r'^mysql://',
            r'^redis://',
            r'^mongodb://',
        ]
        
        for pattern in url_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return True
        
        return False

    def _set_nested_value(self, config_dict: Dict[str, Any], key: str, value: Any) -> None:
        """
        Set a value in a nested dictionary using underscore notation.
        
        Converts keys like 'database_host' to nested structure {'database': {'host': value}}
        Note: Key should already be normalized to lowercase before calling this method.
        
        Args:
            config_dict: The dictionary to update
            key: The lowercase key with underscores
            value: The value to set
        """
        # Split key by underscores (assumes key is already lowercase)
        parts = key.split('_')
        
        if len(parts) == 1:
            config_dict[key] = value
            return
        
        current = config_dict
        
        # Navigate to the correct nested dictionary
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # If the path exists but is not a dict, preserve the value
                current[part] = {"_value": current[part]}
            current = current[part]
        
        current[parts[-1]] = value

    def is_available(self) -> bool:
        """
        Environment variables are always available.
        
        Returns:
            True (environment variables are always accessible)
        """
        return True

    def get_matched_variables(self) -> Dict[str, str]:
        """
        Get all environment variables that match the configured prefixes.
        
        Returns:
            Dictionary of matched environment variables
        """
        matched = {}
        
        for env_key, env_value in os.environ.items():
            if self._find_matching_prefix(env_key):
                matched[env_key] = env_value
        
        return matched

    def get_prefix_info(self) -> Dict[str, Any]:
        """
        Get information about the configured prefixes.
        
        Returns:
            Dictionary with prefix configuration details
        """
        return {
            "prefixes": self._prefixes,
            "case_sensitive": self._case_sensitive,
            "nested": self._nested,
            "strip_prefix": self._strip_prefix,
            "parse_values": self._parse_values,
            "list_separator": self._list_separator
        }

    def validate_environment(self) -> Dict[str, Any]:
        """
        Validate the current environment configuration.
        
        Returns:
            Dictionary with validation results
        """
        matched_vars = self.get_matched_variables()
        
        return {
            "total_env_vars": len(os.environ),
            "matched_vars": len(matched_vars),
            "prefixes_configured": len(self._prefixes),
            "matched_variables": list(matched_vars.keys()),
            "configuration_valid": len(matched_vars) > 0 or len(self._prefixes) == 0
        }

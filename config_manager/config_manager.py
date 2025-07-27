from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, overload
import re

T = TypeVar('T')

class ConfigManager:
    """
    Manages application configuration from multiple sources.
    
    The ConfigManager allows loading configuration from different sources like 
    environment variables, JSON files, etc. Sources are processed in the order 
    they are added, with later sources overriding earlier ones for the same keys.
    
    Basic usage:
    ```python
    from config_manager import ConfigManager
    from config_manager.sources import JsonSource, EnvironmentSource

    # Create a new configuration manager
    config = ConfigManager()
    
    # Add sources in order of precedence (lowest to highest)
    config.add_source(JsonSource('config.json'))
    config.add_source(EnvironmentSource(prefix='APP_'))
    
    # Get configuration values
    db_host = config.get('database.host', 'localhost')
    db_port = config.get_int('database.port', 5432)
    debug_mode = config.get_bool('debug', False)
    ```
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._sources: List[Any] = []

    def add_source(self, source: Any) -> 'ConfigManager':
        """
        Adds a configuration source. Sources are processed in the order they are added,
        with later sources overriding earlier ones.
        
        Args:
            source: A configuration source with a load() method that returns a dictionary.
            
        Returns:
            The ConfigManager instance for method chaining.
        """
        self._sources.append(source)
        self._deep_update(self._config, source.load())
        return self
        
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively updates a target dictionary with values from a source dictionary.
        Unlike dict.update(), this handles nested dictionaries by merging them rather
        than replacing them.
        
        Args:
            target: The dictionary to update
            source: The dictionary to get values from
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # If both are dictionaries, recursively merge them
                self._deep_update(target[key], value)
            else:
                # Otherwise just update the value
                target[key] = value

    def reload(self) -> None:
        """
        Reloads all configuration sources.
        This is useful when you know that the underlying configuration has changed.
        """
        self._config = {}
        for source in self._sources:
            self._deep_update(self._config, source.load())

    def _get_nested(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Internal method to get a possibly nested configuration value.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation (e.g., 'database.host').
            default: The value to return if the key is not found.
            
        Returns:
            The value for the key, or the default if not found.
        """
        # Handle non-nested keys directly
        if '.' not in key:
            return self._config.get(key, default)
        
        # Handle nested keys
        parts = key.split('.')
        current = self._config
        
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                return default
            current = current[part]
            
        return current.get(parts[-1], default)

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieves a configuration value by key.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation (e.g., 'database.host').
            default: The value to return if the key is not found.
            
        Returns:
            The value for the key, or the default if not found.
        """
        return self._get_nested(key, default)

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Retrieves a configuration value as an integer.
        
        Args:
            key: The key to look up.
            default: The integer value to return if the key is not found.
            
        Returns:
            The value for the key converted to an integer, or the default if not found.
            If the value cannot be converted to an integer, the default is returned.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """
        Retrieves a configuration value as a float.
        
        Args:
            key: The key to look up.
            default: The float value to return if the key is not found.
            
        Returns:
            The value for the key converted to a float, or the default if not found.
            If the value cannot be converted to a float, the default is returned.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        Retrieves a configuration value as a boolean.
        
        Args:
            key: The key to look up.
            default: The boolean value to return if the key is not found.
            
        Returns:
            The value for the key converted to a boolean, or the default if not found.
            If the value cannot be converted to a boolean, the default is returned.
            
        Note:
            String values 'true', 'yes', 'y', 'on', and '1' (case insensitive) are converted to True.
            String values 'false', 'no', 'n', 'off', and '0' (case insensitive) are converted to False.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        # Handle string values
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', 'yes', 'y', 'on', '1'):
                return True
            if value in ('false', 'no', 'n', 'off', '0'):
                return False
        
        # If we got here, we can't convert the value, so return the default
        return default

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> Optional[List[Any]]:
        """
        Retrieves a configuration value as a list.
        If the value is a string, it will be split by commas.
        
        Args:
            key: The key to look up.
            default: The list value to return if the key is not found.
            
        Returns:
            The value as a list, or the default if not found.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            return [item.strip() for item in value.split(',')]
        
        return [value]

    def __getitem__(self, key: str) -> Any:
        """
        Allows dictionary-style access to configuration values.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation.
            
        Returns:
            The value for the key.
            
        Raises:
            KeyError: If the key is not found.
        """
        value = self._get_nested(key)
        if value is None:
            raise KeyError(key)
        return value
            
    def __contains__(self, key: str) -> bool:
        """
        Checks if a key exists in the configuration.
        
        Args:
            key: The key to check. Can be a nested key using dot notation.
            
        Returns:
            True if the key exists, False otherwise.
        """
        try:
            self[key]
            return True
        except KeyError:
            return False

import os
from typing import Dict, Any
from .base import BaseSource

class EnvironmentSource(BaseSource):
    """
    Loads configuration from environment variables.
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    def load(self) -> Dict[str, Any]:
        """
        Loads environment variables that match the given prefix.
        
        Environment variables can be accessed directly or can be converted to nested structures
        based on the constructor parameters.
        """
        config = {}
        for key, value in os.environ.items():
            if key.startswith(self._prefix):
                # Get the key without the prefix
                config_key = key[len(self._prefix):]
                
                # Store both the original key and a nested version
                config[config_key] = value
                
                # Also create a nested version if there are underscores
                if '_' in config_key:
                    nested_key = config_key.replace('_', '.')
                    
                    # Handle the value - try to parse common data types
                    parsed_value = self._parse_value(value)
                    
                    # Add the nested version as well
                    self._set_nested_value(config, nested_key, parsed_value)
        
        return config
        
    def _parse_value(self, value: str) -> Any:
        """
        Parses a string value into an appropriate data type if possible.
        """
        # Check for boolean values
        if value.lower() in ('true', 'yes', 'y', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'n', 'off', '0'):
            return False
            
        # Check for integer values
        try:
            if value.isdigit():
                return int(value)
        except (ValueError, AttributeError):
            pass
            
        # Check for float values
        try:
            if value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                return float(value)
        except (ValueError, AttributeError):
            pass
            
        # Return as string if no other type matches
        return value
        
    def _set_nested_value(self, config_dict: Dict[str, Any], key: str, value: Any) -> None:
        """
        Sets a value in a nested dictionary using a key with dot notation.
        
        Args:
            config_dict: The dictionary to update
            key: The key using dot notation (e.g., 'database.host')
            value: The value to set
        """
        if '.' not in key:
            config_dict[key] = value
            return
            
        parts = key.split('.')
        current = config_dict
        
        # Navigate to the correct nested dictionary
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # If the path exists but is not a dict, convert it to one
                current[part] = {"value": current[part]}
            current = current[part]
            
        current[parts[-1]] = value

"""
Simple YAML-like parser for testing our implementation.
This is NOT a full YAML parser, just enough to test our ConfigManager.
"""

import re
from typing import Dict, Any, Union


class SimpleYaml:
    """A very basic YAML-like parser for testing purposes."""
    
    @staticmethod
    def safe_load(content: str) -> Dict[str, Any]:
        """
        Parse a simple YAML-like format.
        Only supports basic key-value pairs and simple nesting.
        """
        if not content.strip():
            return {}
            
        lines = content.strip().split('\n')
        result = {}
        current_dict = result
        indent_stack = [(0, result)]
        current_list_key = None
        
        for line in lines:
            line = line.rstrip()
            if not line or line.strip().startswith('#'):
                continue
                
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            
            # Check if this is a list item
            if line.strip().startswith('- '):
                # Pop from stack until we find the right parent
                while len(indent_stack) > 1 and indent <= indent_stack[-1][0]:
                    indent_stack.pop()
                
                current_dict = indent_stack[-1][1]
                
                if current_list_key and current_list_key in current_dict:
                    if not isinstance(current_dict[current_list_key], list):
                        current_dict[current_list_key] = []
                    item_value = line.strip()[2:]  # Remove '- '
                    current_dict[current_list_key].append(SimpleYaml._parse_value(item_value))
                continue
            
            # Pop from stack until we find the right parent
            while len(indent_stack) > 1 and indent <= indent_stack[-1][0]:
                indent_stack.pop()
            
            current_dict = indent_stack[-1][1]
            
            # Parse the line
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value == '':
                    # This is a parent key - could be a dict or list
                    new_dict = {}
                    current_dict[key] = new_dict
                    indent_stack.append((indent, new_dict))
                    current_list_key = key
                else:
                    # This is a key-value pair
                    current_dict[key] = SimpleYaml._parse_value(value)
                    current_list_key = None
        
        return result
    
    @staticmethod
    def _parse_value(value: str) -> Union[str, int, float, bool]:
        """Parse a value into the appropriate Python type."""
        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Boolean values
        if value.lower() in ('true', 'yes'):
            return True
        if value.lower() in ('false', 'no'):
            return False
            
        # Integer values
        if value.isdigit():
            return int(value)
            
        # Float values
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
            
        # Default to string
        return value
    
    @staticmethod
    def dump(data: Dict[str, Any], stream=None, **kwargs) -> str:
        """Convert a dictionary back to YAML-like format."""
        lines = []
        
        def _dump_dict(d: Dict[str, Any], indent: int = 0):
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append('  ' * indent + f"{key}:")
                    _dump_dict(value, indent + 1)
                elif isinstance(value, list):
                    lines.append('  ' * indent + f"{key}:")
                    for item in value:
                        lines.append('  ' * (indent + 1) + f"- {item}")
                else:
                    lines.append('  ' * indent + f"{key}: {value}")
        
        _dump_dict(data)
        result = '\n'.join(lines)
        
        if stream:
            stream.write(result)
        
        return result

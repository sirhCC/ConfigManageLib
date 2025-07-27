try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    # Fallback to simple YAML implementation for testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from simple_yaml import SimpleYaml as yaml
    HAS_PYYAML = False

from typing import Dict, Any
from .base import BaseSource

class YamlSource(BaseSource):
    """
    Loads configuration from a YAML file.
    
    Supports both .yaml and .yml file extensions.
    """

    def __init__(self, file_path: str):
        """
        Initialize the YAML source.
        
        Args:
            file_path: Path to the YAML file to load.
        """
        self._file_path = file_path

    def load(self) -> Dict[str, Any]:
        """
        Loads the YAML file and returns the configuration dictionary.
        
        Returns:
            A dictionary containing the configuration data from the YAML file.
            Returns an empty dictionary if the file is not found or cannot be parsed.
        """
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                if HAS_PYYAML:
                    content = yaml.safe_load(f)
                else:
                    # Our simple implementation expects string content
                    content = yaml.safe_load(f.read())
                # yaml.safe_load can return None for empty files
                return content if content is not None else {}
        except FileNotFoundError:
            return {}
        except Exception:
            # Handle any parsing errors gracefully
            return {}

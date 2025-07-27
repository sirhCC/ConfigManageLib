import json
from typing import Dict, Any
from .base import BaseSource

class JsonSource(BaseSource):
    """
    Loads configuration from a JSON file.
    """

    def __init__(self, file_path: str):
        self._file_path = file_path

    def load(self) -> Dict[str, Any]:
        """
        Loads the JSON file.
        """
        try:
            with open(self._file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

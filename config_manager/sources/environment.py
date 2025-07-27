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
        """
        config = {}
        for key, value in os.environ.items():
            if key.startswith(self._prefix):
                config_key = key[len(self._prefix):]
                config[config_key] = value
        return config

from typing import Any, Dict, List, Optional

class ConfigManager:
    """
    Manages application configuration from multiple sources.
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._sources: List[Any] = []

    def add_source(self, source: Any):
        """
        Adds a configuration source. Sources are processed in the order they are added,
        with later sources overriding earlier ones.
        """
        self._sources.append(source)
        self._config.update(source.load())

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieves a configuration value by key.
        """
        return self._config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """
        Allows dictionary-style access to configuration values.
        """
        return self._config[key]

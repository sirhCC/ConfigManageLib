from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseSource(ABC):
    """
    Abstract base class for configuration sources.
    """

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        Loads the configuration data from the source.
        """
        raise NotImplementedError

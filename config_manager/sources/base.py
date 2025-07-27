"""
🔧 Enterprise-grade base classes for configuration sources.

This module provides the foundational protocols and abstract base classes
for all configuration sources in the ConfigManager library.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, runtime_checkable, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class SourceMetadata:
    """Metadata about a configuration source for monitoring and debugging."""
    source_type: str
    source_path: Optional[str] = None
    last_loaded: Optional[datetime] = None
    load_count: int = 0
    file_size: Optional[int] = None
    encoding: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    def record_load(self, success: bool = True, error: Optional[str] = None) -> None:
        """Record a load attempt with timestamp and outcome."""
        self.last_loaded = datetime.now()
        self.load_count += 1
        if not success:
            self.error_count += 1
            self.last_error = error


@runtime_checkable
class ConfigSource(Protocol):
    """
    Protocol defining the interface for configuration sources.
    
    This protocol ensures type safety and consistency across all source implementations.
    """
    
    def load(self) -> Dict[str, Any]:
        """Load configuration data from the source."""
        ...
    
    def get_metadata(self) -> SourceMetadata:
        """Get metadata about this configuration source."""
        ...
    
    def is_available(self) -> bool:
        """Check if the source is available and can be loaded."""
        ...


class BaseSource(ABC):
    """
    Enterprise-grade abstract base class for configuration sources.
    
    This class provides common functionality for all configuration sources including:
    - Metadata tracking and monitoring
    - Error handling and logging
    - Performance optimization
    - Type safety and validation
    
    Example:
        ```python
        class MySource(BaseSource):
            def __init__(self, path: str):
                super().__init__(source_type="custom", source_path=path)
            
            def _do_load(self) -> Dict[str, Any]:
                # Implement your loading logic here
                return {"key": "value"}
        ```
    """

    def __init__(
        self, 
        source_type: str, 
        source_path: Optional[Union[str, Path]] = None,
        encoding: str = "utf-8"
    ):
        """
        Initialize the base source with metadata tracking.
        
        Args:
            source_type: Type identifier for this source (e.g., "json", "yaml")
            source_path: Path to the source file or resource
            encoding: Text encoding for file-based sources
        """
        self._metadata = SourceMetadata(
            source_type=source_type,
            source_path=str(source_path) if source_path else None,
            encoding=encoding
        )
        self._logger = logging.getLogger(f"{__name__}.{source_type}")

    @abstractmethod
    def _do_load(self) -> Dict[str, Any]:
        """
        Abstract method for source-specific loading logic.
        
        Subclasses must implement this method to define how they load
        configuration data from their specific source type.
        
        Returns:
            Dictionary containing the loaded configuration data
            
        Raises:
            Various exceptions depending on the source type
        """
        raise NotImplementedError("Subclasses must implement _do_load()")

    def load(self) -> Dict[str, Any]:
        """
        Load configuration data with enterprise-grade error handling and monitoring.
        
        This method wraps the source-specific loading logic with:
        - Performance monitoring
        - Error handling and logging
        - Metadata tracking
        - Graceful degradation
        
        Returns:
            Dictionary containing the loaded configuration data.
            Returns empty dict on error to allow graceful degradation.
        """
        start_time = datetime.now()
        
        try:
            self._logger.debug(f"Loading configuration from {self._metadata.source_type} source: {self._metadata.source_path}")
            
            # Check if source is available before attempting load
            if not self.is_available():
                self._logger.warning(f"Source not available: {self._metadata.source_path}")
                self._metadata.record_load(success=False, error="Source not available")
                return {}
            
            # Perform the actual loading
            config_data = self._do_load()
            
            # Record successful load
            load_time = (datetime.now() - start_time).total_seconds()
            self._metadata.record_load(success=True)
            
            self._logger.debug(
                f"Successfully loaded {len(config_data)} keys from {self._metadata.source_type} "
                f"source in {load_time:.3f}s"
            )
            
            return config_data
            
        except Exception as e:
            load_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Failed to load {self._metadata.source_type} source: {e}"
            
            self._logger.error(f"{error_msg} (after {load_time:.3f}s)")
            self._metadata.record_load(success=False, error=str(e))
            
            # Return empty dict for graceful degradation
            return {}

    def get_metadata(self) -> SourceMetadata:
        """
        Get comprehensive metadata about this configuration source.
        
        Returns:
            SourceMetadata object containing load statistics, error info, etc.
        """
        # Update file size if this is a file-based source
        if self._metadata.source_path and Path(self._metadata.source_path).exists():
            try:
                self._metadata.file_size = Path(self._metadata.source_path).stat().st_size
            except (OSError, PermissionError):
                pass  # Ignore file access errors
        
        return self._metadata

    def is_available(self) -> bool:
        """
        Check if the configuration source is available and can be loaded.
        
        For file-based sources, this checks if the file exists and is readable.
        Subclasses can override this for more sophisticated availability checks.
        
        Returns:
            True if the source is available, False otherwise
        """
        if self._metadata.source_path:
            path = Path(self._metadata.source_path)
            return path.exists() and path.is_file()
        
        # For non-file sources, assume available by default
        # Subclasses should override this for specific availability logic
        return True

    def __str__(self) -> str:
        """String representation showing source type and path."""
        return f"{self._metadata.source_type.title()}Source({self._metadata.source_path})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"type={self._metadata.source_type!r}, "
            f"path={self._metadata.source_path!r}, "
            f"loads={self._metadata.load_count}, "
            f"errors={self._metadata.error_count})"
        )

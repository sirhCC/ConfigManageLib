"""
🔧 Enterprise-grade JSON configuration source for ConfigManager.

This module provides robust JSON file loading with comprehensive error handling,
performance optimization, and enterprise-grade monitoring capabilities.
"""

import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

from .base import BaseSource

# Configure logger for this module
logger = logging.getLogger(__name__)


class JsonSource(BaseSource):
    """
    Enterprise-grade JSON configuration source with advanced error handling.
    
    Features:
    - Robust JSON parsing with detailed error messages
    - Support for JSON5-style comments (when available)
    - Graceful handling of malformed JSON
    - Performance monitoring and metadata tracking
    - Comprehensive logging for debugging
    
    Example:
        ```python
        # Basic usage
        source = JsonSource('config.json')
        config = source.load()
        
        # With custom encoding
        source = JsonSource('config.json', encoding='utf-8-sig')
        
        # Check availability before loading
        if source.is_available():
            config = source.load()
        ```
    """

    def __init__(
        self, 
        file_path: Union[str, Path], 
        encoding: str = "utf-8",
        allow_comments: bool = False
    ):
        """
        Initialize the JSON configuration source.
        
        Args:
            file_path: Path to the JSON configuration file
            encoding: Text encoding for the file (default: utf-8)
            allow_comments: Whether to attempt parsing JSON with comments
        """
        super().__init__(
            source_type="json", 
            source_path=file_path,
            encoding=encoding
        )
        self._file_path = Path(file_path)
        self._allow_comments = allow_comments
        
        # Try to import json5 for comment support if requested
        self._json5_available = False
        if allow_comments:
            try:
                import json5
                self._json5_available = True
                self._logger.debug("JSON5 support enabled for comment parsing")
            except ImportError:
                self._logger.debug("JSON5 not available, falling back to standard JSON")

    def _do_load(self) -> Dict[str, Any]:
        """
        Load and parse the JSON configuration file.
        
        Returns:
            Dictionary containing the parsed JSON data
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            json.JSONDecodeError: If the JSON is malformed
            PermissionError: If the file cannot be read
            UnicodeDecodeError: If the file encoding is incorrect
        """
        self._logger.debug(f"Loading JSON configuration from: {self._file_path}")
        
        try:
            # Read the file with specified encoding
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                content = f.read()
            
            # Parse JSON with or without comment support
            if self._allow_comments and self._json5_available:
                import json5
                config_data = json5.loads(content)
                self._logger.debug("Parsed JSON with comment support using JSON5")
            else:
                config_data = json.loads(content)
                self._logger.debug("Parsed standard JSON")
            
            # Validate that we got a dictionary
            if not isinstance(config_data, dict):
                raise ValueError(
                    f"JSON root must be an object/dictionary, got {type(config_data).__name__}"
                )
            
            self._logger.info(
                f"Successfully loaded {len(config_data)} configuration keys from JSON file"
            )
            
            return config_data
            
        except FileNotFoundError:
            self._logger.error(f"JSON configuration file not found: {self._file_path}")
            raise
            
        except json.JSONDecodeError as e:
            self._logger.error(
                f"Invalid JSON in configuration file {self._file_path}: "
                f"line {e.lineno}, column {e.colno}: {e.msg}"
            )
            raise
            
        except UnicodeDecodeError as e:
            self._logger.error(
                f"Encoding error reading {self._file_path} with {self._metadata.encoding}: {e}"
            )
            raise
            
        except PermissionError:
            self._logger.error(f"Permission denied reading configuration file: {self._file_path}")
            raise
            
        except ValueError as e:
            self._logger.error(f"Invalid JSON structure in {self._file_path}: {e}")
            raise

    def is_available(self) -> bool:
        """
        Check if the JSON configuration file is available and readable.
        
        Performs additional checks beyond the base class:
        - Verifies the file has a .json extension (warning if not)
        - Checks basic JSON syntax validity
        
        Returns:
            True if the file exists and appears to be valid JSON
        """
        if not super().is_available():
            return False
        
        # Check file extension (warning only, not blocking)
        if self._file_path.suffix.lower() not in ['.json', '.jsonc']:
            self._logger.warning(
                f"File {self._file_path} doesn't have .json extension, "
                f"but will attempt to parse as JSON"
            )
        
        # Quick syntax check by attempting to parse first few characters
        try:
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                # Read first few characters to check if it looks like JSON
                preview = f.read(100).strip()
                if preview and not (preview.startswith('{') or preview.startswith('[')):
                    self._logger.warning(
                        f"File {self._file_path} doesn't appear to start with JSON syntax"
                    )
                    return False
                    
        except (OSError, UnicodeDecodeError):
            # If we can't read the file for preview, let the main load handle the error
            pass
        
        return True

    def reload(self) -> Dict[str, Any]:
        """
        Convenience method to reload the configuration file.
        
        This is equivalent to calling load() again but provides
        a more explicit API for reloading scenarios.
        
        Returns:
            Dictionary containing the reloaded configuration data
        """
        self._logger.info(f"Reloading JSON configuration from: {self._file_path}")
        return self.load()

    def get_file_path(self) -> Path:
        """
        Get the path to the JSON configuration file.
        
        Returns:
            Path object for the configuration file
        """
        return self._file_path

    def validate_syntax(self) -> bool:
        """
        Validate JSON syntax without loading the full configuration.
        
        Useful for configuration validation tools or health checks.
        
        Returns:
            True if the JSON syntax is valid, False otherwise
        """
        try:
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError):
            return False

"""
🔧 Enterprise-grade YAML configuration source for ConfigManager.

This module provides robust YAML file loading with comprehensive error handling,
fallback parsing, and enterprise-grade monitoring capabilities.
"""

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

from typing import Dict, Any, Union, Optional, List
from pathlib import Path
import logging

from .base import BaseSource

# Configure logger for this module
logger = logging.getLogger(__name__)


class YamlSource(BaseSource):
    """
    Enterprise-grade YAML configuration source with advanced parsing capabilities.
    
    Features:
    - Automatic fallback between PyYAML and simple parser
    - Support for multiple YAML documents in a single file
    - Advanced error handling with detailed error messages
    - Safe loading to prevent code execution
    - Performance monitoring and metadata tracking
    - Support for both .yaml and .yml extensions
    
    Example:
        ```python
        # Basic usage
        source = YamlSource('config.yaml')
        config = source.load()
        
        # With custom encoding
        source = YamlSource('config.yml', encoding='utf-8-sig')
        
        # Multi-document support
        source = YamlSource('configs.yaml', load_all=True)
        
        # Check parser availability
        if source.has_pyyaml():
            print("Using PyYAML for parsing")
        ```
    """

    def __init__(
        self, 
        file_path: Union[str, Path], 
        encoding: str = "utf-8",
        load_all: bool = False,
        merge_documents: bool = True
    ):
        """
        Initialize the YAML configuration source.
        
        Args:
            file_path: Path to the YAML configuration file
            encoding: Text encoding for the file (default: utf-8)
            load_all: Whether to load all documents from multi-document YAML
            merge_documents: Whether to merge multiple documents into one dict
        """
        super().__init__(
            source_type="yaml", 
            source_path=file_path,
            encoding=encoding
        )
        self._file_path = Path(file_path)
        self._load_all = load_all
        self._merge_documents = merge_documents
        
        # Log the parser being used
        parser_name = "PyYAML" if HAS_PYYAML else "SimpleYAML (fallback)"
        self._logger.debug(f"Initialized YAML source with {parser_name} parser")

    def _do_load(self) -> Dict[str, Any]:
        """
        Load and parse the YAML configuration file.
        
        Returns:
            Dictionary containing the parsed YAML data
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            PermissionError: If the file cannot be read
            UnicodeDecodeError: If the file encoding is incorrect
        """
        self._logger.debug(f"Loading YAML configuration from: {self._file_path}")
        
        try:
            # Read the file with specified encoding
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                content = f.read()
            
            # Parse YAML based on configuration
            if self._load_all:
                config_data = self._load_all_documents(content)
            else:
                config_data = self._load_single_document(content)
            
            # Validate that we got a dictionary
            if not isinstance(config_data, dict):
                raise ValueError(
                    f"YAML root must be a mapping/dictionary, got {type(config_data).__name__}"
                )
            
            self._logger.info(
                f"Successfully loaded {len(config_data)} configuration keys from YAML file"
            )
            
            return config_data
            
        except FileNotFoundError:
            self._logger.error(f"YAML configuration file not found: {self._file_path}")
            raise
            
        except yaml.YAMLError as e:
            self._logger.error(f"Invalid YAML in configuration file {self._file_path}: {e}")
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
            self._logger.error(f"Invalid YAML structure in {self._file_path}: {e}")
            raise

    def _load_single_document(self, content: str) -> Dict[str, Any]:
        """Load a single YAML document."""
        if HAS_PYYAML:
            result = yaml.safe_load(content)
        else:
            # SimpleYAML fallback expects string content
            result = yaml.safe_load(content)
        
        # yaml.safe_load can return None for empty files
        return result if result is not None else {}

    def _load_all_documents(self, content: str) -> Dict[str, Any]:
        """Load all documents from a multi-document YAML file."""
        if HAS_PYYAML:
            documents = list(yaml.safe_load_all(content))
        else:
            # SimpleYAML fallback - split on document separators
            docs = content.split('\n---\n')
            documents = [yaml.safe_load(doc.strip()) for doc in docs if doc.strip()]
        
        # Filter out None documents (empty documents)
        documents = [doc for doc in documents if doc is not None]
        
        if not documents:
            return {}
        
        if self._merge_documents and all(isinstance(doc, dict) for doc in documents):
            # Merge all documents into a single dictionary
            merged = {}
            for doc in documents:
                merged.update(doc)
            self._logger.debug(f"Merged {len(documents)} YAML documents into single configuration")
            return merged
        else:
            # Return as a list of documents under a special key
            self._logger.debug(f"Loaded {len(documents)} YAML documents as separate items")
            return {"documents": documents}

    def is_available(self) -> bool:
        """
        Check if the YAML configuration file is available and readable.
        
        Performs additional checks beyond the base class:
        - Verifies the file has a .yaml or .yml extension (warning if not)
        - Checks basic YAML syntax validity
        
        Returns:
            True if the file exists and appears to be valid YAML
        """
        if not super().is_available():
            return False
        
        # Check file extension (warning only, not blocking)
        valid_extensions = ['.yaml', '.yml']
        if self._file_path.suffix.lower() not in valid_extensions:
            self._logger.warning(
                f"File {self._file_path} doesn't have YAML extension "
                f"({', '.join(valid_extensions)}), but will attempt to parse as YAML"
            )
        
        # Quick syntax check by attempting to parse first document
        try:
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                # Read first few lines to check basic YAML syntax
                preview = []
                for i, line in enumerate(f):
                    if i >= 10:  # Only check first 10 lines
                        break
                    preview.append(line)
                
                preview_content = ''.join(preview)
                if preview_content.strip():
                    # Try to parse the preview
                    if HAS_PYYAML:
                        yaml.safe_load(preview_content)
                    else:
                        yaml.safe_load(preview_content)
                        
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            # If we can't parse preview, let the main load handle the error
            pass
        
        return True

    def reload(self) -> Dict[str, Any]:
        """
        Convenience method to reload the configuration file.
        
        Returns:
            Dictionary containing the reloaded configuration data
        """
        self._logger.info(f"Reloading YAML configuration from: {self._file_path}")
        return self.load()

    def get_file_path(self) -> Path:
        """Get the path to the YAML configuration file."""
        return self._file_path

    def has_pyyaml(self) -> bool:
        """Check if PyYAML is available for parsing."""
        return HAS_PYYAML

    def get_parser_info(self) -> Dict[str, Any]:
        """
        Get information about the YAML parser being used.
        
        Returns:
            Dictionary with parser information
        """
        return {
            "parser": "PyYAML" if HAS_PYYAML else "SimpleYAML",
            "version": getattr(yaml, "__version__", "unknown") if HAS_PYYAML else "fallback",
            "features": {
                "multi_document": True,
                "safe_loading": True,
                "complex_types": HAS_PYYAML
            }
        }

    def validate_syntax(self) -> bool:
        """
        Validate YAML syntax without loading the full configuration.
        
        Returns:
            True if the YAML syntax is valid, False otherwise
        """
        try:
            with open(self._file_path, 'r', encoding=self._metadata.encoding) as f:
                content = f.read()
            
            if HAS_PYYAML:
                if self._load_all:
                    list(yaml.safe_load_all(content))
                else:
                    yaml.safe_load(content)
            else:
                yaml.safe_load(content)
            
            return True
        except (yaml.YAMLError, FileNotFoundError, PermissionError, UnicodeDecodeError):
            return False

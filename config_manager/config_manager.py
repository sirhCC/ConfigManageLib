from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, overload, Callable
import re
import threading
import time
import os
from pathlib import Path
from .schema import Schema
from .validation import ValidationError

# Try to import watchdog for file watching, fall back to polling if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

T = TypeVar('T')

class ConfigManager:
    """
    Manages application configuration from multiple sources.
    
    The ConfigManager allows loading configuration from different sources like 
    environment variables, JSON files, YAML files, etc. Sources are processed in 
    the order they are added, with later sources overriding earlier ones for the same keys.
    
    Basic usage:
    ```python
    from config_manager import ConfigManager
    from config_manager.sources import JsonSource, YamlSource, EnvironmentSource

    # Create a new configuration manager
    config = ConfigManager()
    
    # Add sources in order of precedence (lowest to highest)
    config.add_source(YamlSource('config.yaml'))
    config.add_source(JsonSource('config.json'))
    config.add_source(EnvironmentSource(prefix='APP_'))
    
    # Get configuration values
    db_host = config.get('database.host', 'localhost')
    db_port = config.get_int('database.port', 5432)
    debug_mode = config.get_bool('debug', False)
    ```
    
    Auto-reload usage:
    ```python
    # Enable auto-reload for file-based sources
    config = ConfigManager(auto_reload=True)
    config.add_source(JsonSource('config.json'))
    
    # Register callback for configuration changes
    config.on_reload(lambda: print("Configuration reloaded!"))
    ```
    """

    def __init__(self, schema: Optional[Schema] = None, auto_reload: bool = False, reload_interval: float = 1.0):
        self._config: Dict[str, Any] = {}
        self._sources: List[Any] = []
        self._schema: Optional[Schema] = schema
        self._validated_config: Optional[Dict[str, Any]] = None
        
        # Auto-reload functionality
        self._auto_reload: bool = auto_reload
        self._reload_interval: float = reload_interval
        self._reload_callbacks: List[Callable[[], None]] = []
        self._config_lock = threading.RLock()  # Reentrant lock for thread safety
        self._watched_files: Dict[str, float] = {}  # file_path -> last_modified_time
        self._observer: Optional[Any] = None
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_watching = threading.Event()
        
        if self._auto_reload:
            self._start_watching()

    def add_source(self, source: Any) -> 'ConfigManager':
        """
        Adds a configuration source. Sources are processed in the order they are added,
        with later sources overriding earlier ones.
        
        Args:
            source: A configuration source with a load() method that returns a dictionary.
            
        Returns:
            The ConfigManager instance for method chaining.
        """
        self._sources.append(source)
        
        # Register file-based sources for auto-reload watching
        if self._auto_reload and hasattr(source, '_file_path'):
            self._add_watched_file(source._file_path)
        
        with self._config_lock:
            self._deep_update(self._config, source.load())
            # Invalidate validated config cache
            self._validated_config = None
        
        return self
        
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively updates a target dictionary with values from a source dictionary.
        Unlike dict.update(), this handles nested dictionaries by merging them rather
        than replacing them.
        
        Args:
            target: The dictionary to update
            source: The dictionary to get values from
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # If both are dictionaries, recursively merge them
                self._deep_update(target[key], value)
            else:
                # Otherwise just update the value
                target[key] = value

    def reload(self) -> None:
        """
        Reloads all configuration sources.
        This is useful when you know that the underlying configuration has changed.
        """
        with self._config_lock:
            self._config = {}
            for source in self._sources:
                self._deep_update(self._config, source.load())
            # Invalidate validated config cache
            self._validated_config = None

    def _get_nested(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Internal method to get a possibly nested configuration value.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation (e.g., 'database.host').
            default: The value to return if the key is not found.
            
        Returns:
            The value for the key, or the default if not found.
        """
        with self._config_lock:
            # Handle non-nested keys directly
            if '.' not in key:
                return self._config.get(key, default)
            
            # Handle nested keys
            parts = key.split('.')
            current = self._config
            
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    return default
                current = current[part]
                
            return current.get(parts[-1], default)

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieves a configuration value by key.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation (e.g., 'database.host').
            default: The value to return if the key is not found.
            
        Returns:
            The value for the key, or the default if not found.
        """
        return self._get_nested(key, default)

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Retrieves a configuration value as an integer.
        
        Args:
            key: The key to look up.
            default: The integer value to return if the key is not found.
            
        Returns:
            The value for the key converted to an integer, or the default if not found.
            If the value cannot be converted to an integer, the default is returned.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """
        Retrieves a configuration value as a float.
        
        Args:
            key: The key to look up.
            default: The float value to return if the key is not found.
            
        Returns:
            The value for the key converted to a float, or the default if not found.
            If the value cannot be converted to a float, the default is returned.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        Retrieves a configuration value as a boolean.
        
        Args:
            key: The key to look up.
            default: The boolean value to return if the key is not found.
            
        Returns:
            The value for the key converted to a boolean, or the default if not found.
            If the value cannot be converted to a boolean, the default is returned.
            
        Note:
            String values 'true', 'yes', 'y', 'on', and '1' (case insensitive) are converted to True.
            String values 'false', 'no', 'n', 'off', and '0' (case insensitive) are converted to False.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        # Handle string values
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', 'yes', 'y', 'on', '1'):
                return True
            if value in ('false', 'no', 'n', 'off', '0'):
                return False
        
        # If we got here, we can't convert the value, so return the default
        return default

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> Optional[List[Any]]:
        """
        Retrieves a configuration value as a list.
        If the value is a string, it will be split by commas.
        
        Args:
            key: The key to look up.
            default: The list value to return if the key is not found.
            
        Returns:
            The value as a list, or the default if not found.
        """
        value = self._get_nested(key, default)
        if value is None or value == default:
            return default
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            return [item.strip() for item in value.split(',')]
        
        return [value]

    def __getitem__(self, key: str) -> Any:
        """
        Allows dictionary-style access to configuration values.
        
        Args:
            key: The key to look up. Can be a nested key using dot notation.
            
        Returns:
            The value for the key.
            
        Raises:
            KeyError: If the key is not found.
        """
        value = self._get_nested(key)
        if value is None:
            raise KeyError(key)
        return value
            
    def __contains__(self, key: str) -> bool:
        """
        Checks if a key exists in the configuration.
        
        Args:
            key: The key to check. Can be a nested key using dot notation.
            
        Returns:
            True if the key exists, False otherwise.
        """
        try:
            self[key]
            return True
        except KeyError:
            return False

    def set_schema(self, schema: Schema) -> 'ConfigManager':
        """
        Set the validation schema for this configuration manager.
        
        Args:
            schema: The schema to use for validation
            
        Returns:
            The ConfigManager instance for method chaining.
        """
        self._schema = schema
        # Invalidate validated config cache
        self._validated_config = None
        return self

    def validate(self, raise_on_error: bool = True) -> Dict[str, Any]:
        """
        Validate the current configuration against the schema.
        
        Args:
            raise_on_error: If True, raise ValidationError on validation failure.
                          If False, return the configuration as-is even if validation fails.
            
        Returns:
            The validated configuration with type conversions and defaults applied.
            
        Raises:
            ValidationError: If validation fails and raise_on_error is True.
            ValueError: If no schema has been set.
        """
        if self._schema is None:
            if raise_on_error:
                raise ValueError("No schema has been set for validation")
            return self._config
        
        # Use cached validated config if available
        if self._validated_config is not None:
            return self._validated_config
        
        try:
            validated = self._schema.validate(self._config)
            self._validated_config = validated
            return validated
        except ValidationError:
            if raise_on_error:
                raise
            return self._config

    def is_valid(self) -> bool:
        """
        Check if the current configuration is valid according to the schema.
        
        Returns:
            True if the configuration is valid or no schema is set, False otherwise.
        """
        if self._schema is None:
            return True
        
        try:
            self.validate(raise_on_error=True)
            return True
        except (ValidationError, ValueError):
            return False

    def get_validation_errors(self) -> List[str]:
        """
        Get a list of validation error messages for the current configuration.
        
        Returns:
            List of error messages. Empty list if configuration is valid or no schema is set.
        """
        if self._schema is None:
            return []
        
        try:
            self.validate(raise_on_error=True)
            return []
        except ValidationError as e:
            return [str(e)]
        except ValueError as e:
            return [str(e)]

    def on_reload(self, callback: Callable[[], None]) -> 'ConfigManager':
        """
        Register a callback function to be called when configuration is reloaded.
        
        Args:
            callback: Function to call when configuration changes. Takes no arguments.
            
        Returns:
            Self for method chaining.
        """
        self._reload_callbacks.append(callback)
        return self

    def remove_reload_callback(self, callback: Callable[[], None]) -> 'ConfigManager':
        """
        Remove a previously registered reload callback.
        
        Args:
            callback: The callback function to remove.
            
        Returns:
            Self for method chaining.
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)
        return self

    def _start_watching(self) -> None:
        """Start watching for file changes using the best available method."""
        if WATCHDOG_AVAILABLE:
            self._start_watchdog()
        else:
            self._start_polling()

    def _start_watchdog(self) -> None:
        """Start file watching using the watchdog library."""
        if not WATCHDOG_AVAILABLE:
            return
            
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, config_manager):
                self.config_manager = config_manager
                
            def on_modified(self, event):
                if not event.is_directory:
                    # Check if this is one of our watched files
                    file_path = os.path.abspath(event.src_path)
                    if file_path in self.config_manager._watched_files:
                        self.config_manager._debounced_reload()

        self._observer = Observer()
        self._file_handler = ConfigFileHandler(self)
        
        # Watch all directories containing our config files
        watched_dirs = set()
        for file_path in self._watched_files.keys():
            dir_path = os.path.dirname(file_path)
            if dir_path not in watched_dirs:
                self._observer.schedule(self._file_handler, dir_path, recursive=False)
                watched_dirs.add(dir_path)
        
        self._observer.start()

    def _start_polling(self) -> None:
        """Start file watching using polling as a fallback."""
        def poll_files():
            while not self._stop_watching.is_set():
                try:
                    changed = False
                    with self._config_lock:
                        for file_path, last_mtime in list(self._watched_files.items()):
                            if os.path.exists(file_path):
                                current_mtime = os.path.getmtime(file_path)
                                if current_mtime > last_mtime:
                                    self._watched_files[file_path] = current_mtime
                                    changed = True
                    
                    if changed:
                        self._debounced_reload()
                        
                except Exception:
                    # Ignore errors during polling to prevent crash
                    pass
                    
                self._stop_watching.wait(self._reload_interval)
        
        self._polling_thread = threading.Thread(target=poll_files, daemon=True)
        self._polling_thread.start()

    def _debounced_reload(self) -> None:
        """Reload configuration with debouncing to prevent rapid successive reloads."""
        # Simple debouncing: wait a short time to batch multiple file changes
        time.sleep(0.1)
        
        try:
            with self._config_lock:
                self.reload()
                
            # Call all registered callbacks
            for callback in self._reload_callbacks:
                try:
                    callback()
                except Exception:
                    # Don't let callback errors break the reload process
                    pass
                    
        except Exception:
            # Don't let reload errors break the watching process
            pass

    def _add_watched_file(self, file_path: str) -> None:
        """Add a file to the watch list."""
        if not self._auto_reload:
            return
            
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            self._watched_files[abs_path] = os.path.getmtime(abs_path)
            
            # If using watchdog and observer is running, add new directory watch
            if WATCHDOG_AVAILABLE and self._observer and self._observer.is_alive():
                dir_path = os.path.dirname(abs_path)
                # Check if we're already watching this directory
                watching_dir = False
                for watch in self._observer.emitters:
                    if hasattr(watch, 'watch') and watch.watch.path == dir_path:
                        watching_dir = True
                        break
                
                if not watching_dir:
                    self._observer.schedule(self._file_handler, dir_path, recursive=False)

    def stop_watching(self) -> None:
        """Stop watching for file changes and clean up resources."""
        self._stop_watching.set()
        
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=1.0)
            self._observer = None
            
        if self._polling_thread:
            self._polling_thread.join(timeout=1.0)
            self._polling_thread = None

    def __del__(self):
        """Cleanup when the ConfigManager is destroyed."""
        try:
            self.stop_watching()
        except Exception:
            pass

from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, overload, Callable
import re
import threading
import time
import os
from pathlib import Path
from .schema import Schema
from .validation import ValidationError
from .profiles import ProfileManager, ConfigProfile, create_profile_source_path, profile_source_exists
from .cache import ConfigCache, get_global_cache, create_cache_key, hash_config_data
from .secrets import SecretsManager, get_global_secrets_manager, SecretValue, mask_sensitive_config

# Try to import watchdog for file watching, fall back to polling if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = None  # type: ignore

T = TypeVar('T')


class _ConfigFileHandler:
    """
    File system event handler for configuration file watching.
    
    This is extracted as a module-level class to improve testability
    and reduce complexity in ConfigManager._start_watchdog().
    """
    
    def __init__(self, config_manager: 'ConfigManager'):
        """
        Initialize file handler.
        
        Args:
            config_manager: ConfigManager instance to notify on changes.
        """
        self.config_manager = config_manager
    
    def on_modified(self, event):
        """
        Handle file modification events.
        
        Args:
            event: File system event from watchdog.
        """
        if not event.is_directory:
            # Check if this is one of our watched files
            file_path = os.path.abspath(event.src_path)
            if file_path in self.config_manager._watched_files:
                self.config_manager._debounced_reload()


# Make it compatible with FileSystemEventHandler if watchdog is available
if WATCHDOG_AVAILABLE and FileSystemEventHandler is not None:
    _ConfigFileHandler = type('_ConfigFileHandler', 
                              (FileSystemEventHandler,), 
                              dict(_ConfigFileHandler.__dict__))

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

    def __init__(
        self, 
        schema: Optional[Schema] = None, 
        auto_reload: bool = False, 
        reload_interval: float = 1.0,
        profile: Optional[str] = None,
        auto_detect_profile: bool = True,
        cache: Optional[ConfigCache] = None,
        enable_caching: bool = True,
        secrets_manager: Optional[SecretsManager] = None,
        mask_secrets_in_display: bool = True
    ):
        self._config: Dict[str, Any] = {}
        self._sources: List[Any] = []
        self._schema: Optional[Schema] = schema
        self._validated_config: Optional[Dict[str, Any]] = None
        
        # Profile management
        self._profile_manager = ProfileManager()
        self._current_profile: Optional[str] = None
        self._auto_detect_profile = auto_detect_profile
        
        # Set up the profile
        if profile:
            self._profile_manager.set_active_profile(profile)
            self._current_profile = profile
        elif auto_detect_profile:
            detected_profile = self._profile_manager.detect_environment()
            self._current_profile = detected_profile
        
        # Caching setup
        self._cache = cache if cache is not None else get_global_cache()
        self._enable_caching = enable_caching
        if not enable_caching:
            self._cache.disable()
        
        # Secrets management
        self._secrets_manager = secrets_manager or get_global_secrets_manager()
        self._mask_secrets_in_display = mask_secrets_in_display
        
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
            source_data = self._load_source_with_cache(source)
            self._deep_update(self._config, source_data)
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
                source_data = self._load_source_with_cache(source)
                self._deep_update(self._config, source_data)
            # Invalidate validated config cache
            self._validated_config = None
            
            # Clear cache if configuration changed significantly
            if self._enable_caching:
                self._cache.delete("validated_config")
    
    def _load_source_with_cache(self, source: Any) -> Dict[str, Any]:
        """
        Load configuration from a source with caching support.
        
        Args:
            source: Configuration source to load.
            
        Returns:
            Configuration data dictionary.
        """
        if not self._enable_caching:
            return source.load()
        
        cache_key = self._generate_cache_key(source)
        if cache_key is None:
            # Dynamic sources without stable keys - load and cache by content hash
            return self._load_and_cache_by_content(source)
        
        # Check cache first for file-based sources
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Load from source and cache
        return self._load_and_cache(source, cache_key)
    
    def _generate_cache_key(self, source: Any) -> Optional[str]:
        """
        Generate a cache key for a source. Returns None for dynamic sources.
        
        Args:
            source: Configuration source.
            
        Returns:
            Cache key string or None for dynamic sources.
        """
        source_id = self._get_source_cache_id(source)
        
        # File-based sources use modification time
        if hasattr(source, '_file_path'):
            file_path = getattr(source, '_file_path')
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                return create_cache_key("source", source_id, str(mtime))
        
        # Dynamic sources (remote, generated) return None
        return None
    
    def _load_and_cache_by_content(self, source: Any) -> Dict[str, Any]:
        """
        Load source and cache by content hash (for dynamic sources).
        
        Args:
            source: Configuration source.
            
        Returns:
            Configuration data dictionary.
        """
        try:
            data = source.load()
            source_id = self._get_source_cache_id(source)
            data_hash = hash_config_data(data)
            cache_key = create_cache_key("source", source_id, data_hash)
            self._cache.set(cache_key, data)
            return data
        except Exception:
            # If loading fails, don't cache
            return source.load()
    
    def _load_and_cache(self, source: Any, cache_key: str) -> Dict[str, Any]:
        """
        Load source data and store in cache.
        
        Args:
            source: Configuration source.
            cache_key: Cache key to use.
            
        Returns:
            Configuration data dictionary.
        """
        try:
            data = source.load()
            self._cache.set(cache_key, data)
            return data
        except Exception:
            # If loading fails, return empty dict
            return {}
    
    def _get_source_cache_id(self, source: Any) -> str:
        """Get a unique identifier for a configuration source."""
        source_type = type(source).__name__
        
        # Use file path if available
        if hasattr(source, '_file_path'):
            return f"{source_type}:{getattr(source, '_file_path')}"
        
        # Use URL for remote sources
        if hasattr(source, '_url'):
            return f"{source_type}:{getattr(source, '_url')}"
        
        # Use prefix for environment sources
        if hasattr(source, '_prefix'):
            return f"{source_type}:{getattr(source, '_prefix')}"
        
        # Fallback to type and object id
        return f"{source_type}:{id(source)}"

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
    
    def _convert_value(self, value: Any, converter: Callable[[Any], T], 
                      default: Optional[T] = None) -> Optional[T]:
        """
        Generic value conversion with error handling.
        
        Args:
            value: Value to convert.
            converter: Conversion function.
            default: Default value to return on conversion failure.
            
        Returns:
            Converted value or default.
        """
        if value is None or value == default:
            return default
        
        try:
            return converter(value)
        except (ValueError, TypeError):
            return default

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
        return self._convert_value(value, int, default)

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
        return self._convert_value(value, float, default)

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
        return self._convert_value(value, self._to_bool, default)
    
    def _to_bool(self, value: Any) -> bool:
        """
        Convert value to boolean with smart string handling.
        
        Args:
            value: Value to convert.
            
        Returns:
            Boolean value.
            
        Raises:
            ValueError: If value cannot be converted.
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', 'yes', 'y', 'on', '1'):
                return True
            if value_lower in ('false', 'no', 'n', 'off', '0'):
                return False
        
        raise ValueError(f"Cannot convert {value!r} to boolean")

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
        return self._convert_value(value, self._to_list, default)
    
    def _to_list(self, value: Any) -> List[Any]:
        """
        Convert value to list with smart string parsing.
        
        Args:
            value: Value to convert.
            
        Returns:
            List value.
            
        Raises:
            ValueError: If value cannot be converted.
        """
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            return [item.strip() for item in value.split(',')]
        
        # For other types, wrap in list
        if value is not None:
            return [value]
        
        raise ValueError(f"Cannot convert {value!r} to list")
        
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

        self._observer = Observer()
        self._file_handler = _ConfigFileHandler(self)
        
        # Watch all directories containing our config files
        self._schedule_directory_watches()
        
        self._observer.start()
    
    def _schedule_directory_watches(self) -> None:
        """Schedule watches for all directories containing config files."""
        watched_dirs = set()
        for file_path in self._watched_files.keys():
            dir_path = os.path.dirname(file_path)
            if dir_path not in watched_dirs:
                self._observer.schedule(self._file_handler, dir_path, recursive=False)
                watched_dirs.add(dir_path)

    def _start_polling(self) -> None:
        """Start file watching using polling as a fallback."""
        self._polling_thread = threading.Thread(
            target=self._poll_files_loop, 
            daemon=True
        )
        self._polling_thread.start()
    
    def _poll_files_loop(self) -> None:
        """Continuously poll files for changes."""
        while not self._stop_watching.is_set():
            try:
                if self._check_files_changed():
                    self._debounced_reload()
            except Exception:
                # Ignore errors during polling to prevent crash
                pass
            
            self._stop_watching.wait(self._reload_interval)
    
    def _check_files_changed(self) -> bool:
        """Check if any watched files have changed.
        
        Returns:
            True if any files changed, False otherwise.
        """
        changed = False
        with self._config_lock:
            for file_path, last_mtime in list(self._watched_files.items()):
                if os.path.exists(file_path):
                    current_mtime = os.path.getmtime(file_path)
                    if current_mtime > last_mtime:
                        self._watched_files[file_path] = current_mtime
                        changed = True
        return changed

    def _debounced_reload(self) -> None:
        """Reload configuration with debouncing to prevent rapid successive reloads."""
        # Simple debouncing: wait a short time to batch multiple file changes
        time.sleep(0.1)
        
        try:
            with self._config_lock:
                self.reload()
            
            # Call all registered callbacks
            self._execute_reload_callbacks()
                    
        except Exception:
            # Don't let reload errors break the watching process
            pass
    
    def _execute_reload_callbacks(self) -> None:
        """Execute all registered reload callbacks."""
        for callback in self._reload_callbacks:
            try:
                callback()
            except Exception:
                # Don't let callback errors break the reload process
                pass

    def _add_watched_file(self, file_path: str) -> None:
        """Add a file to the watch list.
        
        Args:
            file_path: Path to file to watch.
        """
        if not self._auto_reload:
            return
            
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            self._watched_files[abs_path] = os.path.getmtime(abs_path)
            
            # If using watchdog and observer is running, add new directory watch
            if WATCHDOG_AVAILABLE and self._observer and self._observer.is_alive():
                self._add_directory_watch(abs_path)
    
    def _add_directory_watch(self, abs_path: str) -> None:
        """Add directory watch if not already watching.
        
        Args:
            abs_path: Absolute path to file whose directory should be watched.
        """
        dir_path = os.path.dirname(abs_path)
        
        # Check if we're already watching this directory
        if self._is_watching_directory(dir_path):
            return
        
        self._observer.schedule(self._file_handler, dir_path, recursive=False)
    
    def _is_watching_directory(self, dir_path: str) -> bool:
        """Check if a directory is already being watched.
        
        Args:
            dir_path: Directory path to check.
            
        Returns:
            True if directory is being watched.
        """
        for watch in self._observer.emitters:
            if hasattr(watch, 'watch') and watch.watch.path == dir_path:
                return True
        return False

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

    # Profile Management Methods
    
    def get_current_profile(self) -> Optional[str]:
        """
        Get the name of the currently active profile.
        
        Returns:
            Current profile name or None if no profile is active.
        """
        return self._current_profile
    
    def set_profile(self, profile: str) -> 'ConfigManager':
        """
        Set the active configuration profile and reload sources.
        
        Args:
            profile: Profile name to activate.
            
        Returns:
            Self for method chaining.
            
        Raises:
            ValueError: If profile doesn't exist.
        """
        if not self._profile_manager.get_profile(profile):
            raise ValueError(f"Profile '{profile}' not found")
        
        self._current_profile = profile
        self._profile_manager.set_active_profile(profile)
        
        # Reload configuration with new profile
        self.reload()
        
        return self
    
    def create_profile(self, name: str, base_profile: Optional[str] = None) -> ConfigProfile:
        """
        Create a new configuration profile.
        
        Args:
            name: Profile name.
            base_profile: Name of base profile to inherit from.
            
        Returns:
            Created ConfigProfile instance.
        """
        return self._profile_manager.create_profile(name, base_profile)
    
    def get_profile(self, name: Optional[str] = None) -> Optional[ConfigProfile]:
        """
        Get a configuration profile.
        
        Args:
            name: Profile name (uses current profile if None).
            
        Returns:
            ConfigProfile instance or None if not found.
        """
        return self._profile_manager.get_profile(name or self._current_profile)
    
    def list_profiles(self) -> List[str]:
        """
        Get a list of all available profile names.
        
        Returns:
            List of profile names.
        """
        return self._profile_manager.list_profiles()
    
    def get_profile_var(self, key: str, default: Any = None) -> Any:
        """
        Get a profile-specific variable from the current profile.
        
        Args:
            key: Variable name.
            default: Default value if not found.
            
        Returns:
            Variable value or default.
        """
        return self._profile_manager.get_profile_var(key, self._current_profile, default)
    
    def add_profile_source(
        self, 
        base_path: Union[str, Path], 
        source_type: Optional[str] = None,
        profile: Optional[str] = None,
        fallback_to_base: bool = True
    ) -> 'ConfigManager':
        """
        Add a profile-specific configuration source.
        
        Args:
            base_path: Base configuration directory or file path.
            source_type: Source type ('json', 'yaml', 'toml', 'ini'). Auto-detected if None.
            profile: Profile name (uses current profile if None).
            fallback_to_base: If True and profile file doesn't exist, try base file.
            
        Returns:
            Self for method chaining.
            
        Example:
            # Loads config/development.json for development profile
            config.add_profile_source('config')
            
            # Loads app.production.yaml for production profile  
            config.add_profile_source('app.yaml', profile='production')
        """
        profile_name = profile or self._current_profile or 'development'
        base_path = Path(base_path)
        
        # Detect file extension
        extension = self._detect_source_extension(base_path, source_type)
        
        # Resolve profile-specific file path
        profile_path = self._resolve_profile_path(base_path, profile_name, extension, fallback_to_base)
        
        # Create and add source
        self._add_source_by_extension(profile_path, extension, fallback_to_base)
        
        return self
    
    def _detect_source_extension(self, base_path: Path, source_type: Optional[str]) -> str:
        """
        Detect source file extension from path or explicit type.
        
        Args:
            base_path: Base file or directory path.
            source_type: Explicit source type or None for auto-detection.
            
        Returns:
            File extension string (without dot).
        """
        if source_type is not None:
            return source_type.lower()
        
        if base_path.suffix:
            return base_path.suffix[1:].lower()  # Remove the dot
        
        return 'json'  # Default to JSON
    
    def _resolve_profile_path(self, base_path: Path, profile_name: str, 
                             extension: str, fallback_to_base: bool) -> str:
        """
        Resolve profile-specific file path with fallback logic.
        
        Args:
            base_path: Base file or directory path.
            profile_name: Profile name.
            extension: File extension.
            fallback_to_base: Whether to fall back to base file if profile file missing.
            
        Returns:
            Resolved file path string.
        """
        profile_path = create_profile_source_path(base_path, profile_name, extension)
        
        # Check if profile file exists
        if Path(profile_path).exists():
            return profile_path
        
        if not fallback_to_base:
            return profile_path
        
        # Fall back to base file
        if base_path.is_file() or base_path.suffix:
            return str(base_path)
        
        # Try base file with same extension
        base_file = base_path / f"base.{extension}"
        if base_file.exists():
            return str(base_file)
        
        return profile_path  # Return profile path even if doesn't exist
    
    def _add_source_by_extension(self, file_path: str, extension: str, 
                                allow_missing: bool = False) -> None:
        """
        Create and add source by file extension.
        
        Args:
            file_path: Configuration file path.
            extension: File extension.
            allow_missing: Whether to allow missing files.
            
        Raises:
            ValueError: If extension is not supported.
            FileNotFoundError: If file not found and allow_missing=False.
        """
        from .sources import JsonSource, YamlSource, TomlSource, IniSource
        
        source_classes = {
            'json': JsonSource,
            'yaml': YamlSource,
            'yml': YamlSource,
            'toml': TomlSource,
            'ini': IniSource,
            'cfg': IniSource
        }
        
        source_class = source_classes.get(extension)
        if not source_class:
            raise ValueError(f"Unsupported source type: {extension}")
        
        try:
            source = source_class(file_path)
            self.add_source(source)
        except FileNotFoundError:
            if not allow_missing:
                raise
    
    def detect_environment(self) -> str:
        """
        Detect the current environment from environment variables.
        
        Returns:
            Detected environment name.
        """
        return self._profile_manager.detect_environment()
    
    # Cache management methods
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and performance metrics.
        
        Returns:
            Dictionary containing cache statistics.
        """
        stats = self._cache.get_stats()
        
        # Convert CacheStats dataclass to dictionary for backward compatibility
        if hasattr(stats, '__dict__'):
            stats_dict = {}
            for key, value in stats.__dict__.items():
                if not key.startswith('_'):
                    stats_dict[key] = value
            
            # Add common aliases for backward compatibility
            stats_dict['hits'] = stats_dict.get('cache_hits', 0)
            stats_dict['misses'] = stats_dict.get('cache_misses', 0)
            
            return stats_dict
        
        # Fallback if stats is already a dictionary
        return stats if isinstance(stats, dict) else {}
    
    def clear_cache(self) -> None:
        """Clear all cached configuration data."""
        self._cache.clear()
    
    def enable_caching(self) -> None:
        """Enable configuration caching."""
        self._enable_caching = True
        self._cache.enable()
    
    def disable_caching(self) -> None:
        """Disable configuration caching."""
        self._enable_caching = False
        self._cache.disable()
    
    def is_caching_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enable_caching and self._cache.enabled
    
    def set_cache(self, cache: ConfigCache) -> None:
        """
        Set a custom cache instance.
        
        Args:
            cache: ConfigCache instance to use.
        """
        self._cache = cache
    
    def get_cache_key_for_source(self, source: Any) -> str:
        """
        Get the cache key that would be used for a source.
        
        Args:
            source: Configuration source.
            
        Returns:
            Cache key string.
        """
        source_id = self._get_source_cache_id(source)
        
        if hasattr(source, '_file_path'):
            file_path = getattr(source, '_file_path')
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                return create_cache_key("source", source_id, str(mtime))
        
        return create_cache_key("source", source_id, "dynamic")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.
        
        Returns:
            Dictionary containing all configuration values.
        """
        with self._config_lock:
            if self._mask_secrets_in_display:
                return mask_sensitive_config(self._config)
            return self._config.copy()
    
    def get_raw_config(self) -> Dict[str, Any]:
        """
        Get the raw configuration dictionary without masking secrets.
        
        Returns:
            Dictionary containing all configuration values including unmasked secrets.
        """
        with self._config_lock:
            return self._config.copy()
    
    # Secrets Management Methods
    
    def get_secrets_manager(self) -> SecretsManager:
        """Get the secrets manager instance."""
        return self._secrets_manager
    
    def set_secret(self, key: str, value: Any, 
                   provider_name: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a secret value.
        
        Args:
            key: Secret key
            value: Secret value to store
            provider_name: Specific secrets provider to use
            metadata: Optional metadata for the secret
        """
        self._secrets_manager.set_secret(key, value, provider_name, metadata)
    
    def get_secret(self, key: str, provider_name: Optional[str] = None) -> Optional[Any]:
        """
        Get a secret value.
        
        Args:
            key: Secret key
            provider_name: Specific secrets provider to use
            
        Returns:
            Secret value or None if not found
        """
        secret = self._secrets_manager.get_secret(key, provider_name)
        return secret.get_value() if secret else None
    
    def get_secret_info(self, key: str, provider_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about a secret.
        
        Args:
            key: Secret key
            provider_name: Specific secrets provider to use
            
        Returns:
            Secret information dictionary or None if not found
        """
        secret = self._secrets_manager.get_secret(key, provider_name)
        if secret:
            return {
                'key': key,
                'provider': provider_name,
                'metadata': secret.metadata,
                'accessed_count': secret.accessed_count,
                'created_at': secret.created_at.isoformat(),
                'last_accessed': secret.last_accessed.isoformat() if secret.last_accessed else None,
                'is_expired': secret.is_expired(3600)  # 1 hour default TTL check
            }
        return None
    
    def delete_secret(self, key: str, provider_name: Optional[str] = None) -> bool:
        """
        Delete a secret.
        
        Args:
            key: Secret key
            provider_name: Specific secrets provider to use
            
        Returns:
            True if secret was deleted, False if not found
        """
        return self._secrets_manager.delete_secret(key, provider_name)
    
    def list_secrets(self, provider_name: Optional[str] = None) -> List[str]:
        """
        List available secret keys.
        
        Args:
            provider_name: Specific secrets provider to use
            
        Returns:
            List of secret keys
        """
        return self._secrets_manager.list_secrets(provider_name)
    
    def rotate_secret(self, key: str, new_value: Any, 
                     provider_name: Optional[str] = None) -> bool:
        """
        Rotate a secret to a new value.
        
        Args:
            key: Secret key
            new_value: New secret value
            provider_name: Specific secrets provider to use
            
        Returns:
            True if rotation was successful
        """
        return self._secrets_manager.rotate_secret(key, new_value, provider_name)
    
    def add_secrets_provider(self, name: str, provider: Any) -> None:
        """
        Add a secrets provider.
        
        Args:
            name: Provider name
            provider: Provider instance implementing SecretProvider protocol
        """
        self._secrets_manager.add_provider(name, provider)
    
    def get_secrets_stats(self) -> Dict[str, Any]:
        """
        Get secrets management statistics.
        
        Returns:
            Dictionary with secrets statistics
        """
        return self._secrets_manager.get_stats()
    
    def enable_secrets_masking(self, enabled: bool = True) -> None:
        """
        Enable or disable secrets masking in configuration display.
        
        Args:
            enabled: Whether to mask secrets in display
        """
        self._mask_secrets_in_display = enabled
    
    def schedule_secret_rotation(self, key: str, interval_hours: int,
                               generator_func: Callable[[], Any],
                               provider_name: Optional[str] = None) -> None:
        """
        Schedule automatic secret rotation.
        
        Args:
            key: Secret key to rotate
            interval_hours: Rotation interval in hours
            generator_func: Function to generate new secret value
            provider_name: Specific secrets provider to use
        """
        self._secrets_manager.schedule_rotation(key, interval_hours, generator_func, provider_name)
    
    def check_secret_rotations(self) -> None:
        """Check and execute any scheduled secret rotations."""
        self._secrets_manager.check_rotations()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get the full configuration as a dictionary.
        
        Returns:
            Complete configuration dictionary.
        """
        with self._config_lock:
            return self._config.copy()

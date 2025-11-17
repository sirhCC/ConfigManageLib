# ConfigManager Development Guidelines

Enterprise-grade Python configuration management library with zero-dependency core and comprehensive validation/caching/secrets systems.

## Overview

This library implements a source-priority configuration system where later sources override earlier ones via deep merge (not replacement). All operations are thread-safe using RLock patterns.

**Key Architecture**:
- `ConfigManager`: Main orchestrator with thread-safe operations
- `BaseSource` + `ConfigSource` Protocol: All sources inherit from `config_manager/sources/base.py`
- `ValidationEngine`: Dataclass-first validation with immutable contexts
- `ConfigCache`: Backend-agnostic caching (Memory/File/Null) with TTL/LRU eviction
- `SecretsManager`: Provider pattern for encrypted secrets (Local/Vault/Azure)
- `ProfileManager`: Environment-specific configs with inheritance

## Coding Standards

### Method and Class Naming
- **Private methods**: Prefix with `_` (e.g., `_do_load()`, `_deep_update()`)
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Classes**: `PascalCase` (e.g., `ConfigManager`, `BaseSource`)
- **Methods/Functions**: `snake_case` (e.g., `get_int()`, `add_source()`)

### Method Length and Complexity
- **Target**: Methods under 25 lines
- **Extract helpers** when methods exceed 50 lines
- **Single Responsibility**: One method, one purpose
- **Example**: If a method does "load, cache, and parse", extract 3 methods

### Documentation Requirements
- **All public methods** require Google-style docstrings:
  ```python
  def get_int(self, key: str, default: Optional[int] = None) -> int:
      """Get configuration value as integer with type conversion.
      
      Args:
          key: Dot-notation path (e.g., 'database.port')
          default: Value returned if key not found
          
      Returns:
          Integer value or default
          
      Raises:
          ValueError: If value cannot be converted to int
          
      Example:
          >>> port = config.get_int('server.port', 8080)
      """
  ```
- **Type hints**: Required for all public methods and recommended for private methods
- **Inline comments**: For complex logic only, prefer self-documenting code

### Code Organization
1. **Module structure**: Standard Python ordering
   - Imports (stdlib, third-party, local)
   - Constants
   - Module-level functions
   - Classes (public first, private last)
2. **Class structure**:
   - `__init__` first
   - Public methods (alphabetically)
   - Private methods (alphabetically)
   - Magic methods (`__str__`, `__repr__`) last

## Core Development Patterns

### Source Priority System
Sources are processed in order - **last source wins** for conflicts:
```python
config = ConfigManager()
config.add_source(YamlSource('base.yaml'))      # Lowest priority
config.add_source(JsonSource('config.json'))    
config.add_source(EnvironmentSource('APP_'))    # Highest priority
```

### Deep Configuration Access
Use dot notation for nested access. Type conversion methods auto-handle edge cases:
```python
config.get('database.credentials.password')     # Nested dict traversal
config.get_int('server.port', 8080)             # Type-safe with default
config.get_bool('debug')                        # Handles "true"/"false" strings
config.get_list('features')                     # Comma-separated string parsing
```

### Thread Safety Pattern
All config operations use `self._config_lock` (RLock). When modifying `_config`, invalidate `_validated_config = None`:
```python
def your_method(self) -> None:
    with self._config_lock:
        # Read or write _config here
        self._config['key'] = value
        self._validated_config = None  # Invalidate cache
```

### Cache Key Strategy
File-based sources use modification time for cache keys. Remote sources cache by URL+hash:
```python
# In _load_source_with_cache():
source_id = self._get_source_cache_id(source)  # Type:path or Type:URL
if hasattr(source, '_file_path') and os.path.exists(file_path):
    mtime = os.path.getmtime(file_path)
    cache_key = create_cache_key("source", source_id, str(mtime))
else:
    data = source.load()
    data_hash = hash_config_data(data)
    cache_key = create_cache_key("source", source_id, data_hash)
```

## Adding New Configuration Sources

### Step-by-Step Guide

1. **Create source file** in `config_manager/sources/`:
   ```python
   # config_manager/sources/my_source.py
   from typing import Dict, Any
   from .base import BaseSource
   
   class MySource(BaseSource):
       """Load configuration from [your source type].
       
       Args:
           path: Path to source (file, URL, etc.)
           **kwargs: Additional source-specific options
       """
       def __init__(self, path: str, **kwargs):
           super().__init__(source_type="my_source", source_path=path)
           self._kwargs = kwargs
   ```

2. **Implement `_do_load()`**:
   ```python
       def _do_load(self) -> Dict[str, Any]:
           """Load and parse configuration data.
           
           Returns:
               Parsed configuration dict (empty dict on error)
           """
           # Your loading logic here
           # BaseSource handles errors, logging, and metrics
           return {"key": "value"}
   ```

3. **Implement `is_available()`**:
   ```python
       def is_available(self) -> bool:
           """Check if source is accessible.
           
           Returns:
               True if source can be loaded
           """
           # Check file exists, URL is reachable, etc.
           from pathlib import Path
           return Path(self._metadata.source_path).exists()
   ```

4. **Add to `sources/__init__.py`**:
   ```python
   from .my_source import MySource
   
   __all__ = [
       # ... existing sources
       'MySource',
   ]
   ```

5. **Write comprehensive tests** (see Testing Requirements below)

### BaseSource Features

The `load()` method in `BaseSource` automatically provides:
- Performance timing and logging (`self._logger.debug`)
- Metadata tracking via `SourceMetadata.record_load(success, error)`
- Graceful degradation (returns `{}` on error, never raises)
- Availability check via `is_available()` before loading

### Environment Source Pattern
`EnvironmentSource` converts underscore notation to nested dicts:
```python
# Environment: APP_DATABASE_HOST=localhost, APP_DEBUG=true
source = EnvironmentSource(prefix='APP_', nested=True, parse_values=True)
# Result: {'database': {'host': 'localhost'}, 'debug': True}

# APP_DATABASE_CREDENTIALS_PASSWORD → database.credentials.password
```

## Testing Requirements

### Coverage Standards
- **Minimum for production-ready**: 85% coverage
- **Target for all modules**: 95% coverage
- **Run coverage report**: `pytest --cov=config_manager --cov-report=term-missing`

### Test Structure
Use pytest fixtures from `tests/conftest.py`:
```python
import pytest

class TestMySource:
    """Tests for MySource configuration source."""
    
    def test_load_success(self, tmp_path):
        """Test successful loading of valid config."""
        # Arrange
        config_file = tmp_path / "config.ext"
        config_file.write_text("key: value")
        source = MySource(str(config_file))
        
        # Act
        result = source.load()
        
        # Assert
        assert result == {"key": "value"}
    
    def test_load_file_not_found(self):
        """Test graceful handling of missing file."""
        source = MySource("nonexistent.ext")
        result = source.load()
        assert result == {}  # BaseSource returns empty dict on error
    
    def test_is_available(self, tmp_path):
        """Test availability check."""
        config_file = tmp_path / "config.ext"
        source = MySource(str(config_file))
        
        assert not source.is_available()  # File doesn't exist
        
        config_file.write_text("data")
        assert source.is_available()  # File exists now
```

### Test Categories (pytest markers)
- `@pytest.mark.unit`: Fast, isolated tests
- `@pytest.mark.integration`: Cross-component tests
- `@pytest.mark.slow`: Performance/load tests

### What to Test
1. **Success cases**: Valid inputs, expected outputs
2. **Error cases**: Invalid inputs, missing files, network errors
3. **Edge cases**: Empty files, special characters, large files
4. **Thread safety**: Concurrent access (for ConfigManager)
5. **Type conversion**: All getter methods with various types
6. **Windows specifics**: File locking, path handling

### Windows File Handling Pattern
Always use try/finally for file cleanup in tests:
```python
def test_with_file(tmp_path):
    config_file = tmp_path / "test.json"
    try:
        config_file.write_text('{"key": "value"}')
        # Test operations
    finally:
        if config_file.exists():
            config_file.unlink()  # Explicit cleanup
```

## Development Workflows

### Running Tests
```powershell
# All tests with coverage
pytest --cov=config_manager --cov-report=term-missing

# Specific test file
pytest tests/test_config_manager.py -v

# Specific test markers
pytest -m unit
pytest -m integration
```

### Manual Testing
Examples in `examples/` serve as integration tests - they must run successfully:
```powershell
python examples/basic_usage.py
python examples/advanced_usage.py
python examples/cache_performance.py
```

## Common Pitfalls

- **Don't** use `dict.update()` for config merging - use `_deep_update()` to preserve nested structures
- **Don't** access `_config` without acquiring `_config_lock` in threaded contexts
- **Don't** forget to call `profile_manager.set_active_profile()` before loading profile-specific sources
- **Don't** return `None` from source `_do_load()` - always return `Dict[str, Any]` (empty `{}` is OK)
- **Always** validate cache keys include source-specific identifiers (file path, URL, timestamp)
- **Always** test new sources with `is_available()` before calling `load()`
- **Always** use `with self._config_lock:` when reading/writing `_config` or `_sources`

## Project-Specific Conventions

1. **Dataclass-First Design**: Use `@dataclass(frozen=True)` for immutable data (ValidationContext, SourceMetadata)
2. **Protocol Over ABC**: Define interfaces with `@runtime_checkable Protocol` (see `ConfigSource` in base.py)
3. **Zero External Dependencies**: Core library has no `install_requires` - optional features use extras_require
4. **Enterprise Logging**: Every module has `logger = logging.getLogger(__name__)` with structured messages
5. **Google-Style Docstrings**: All public methods include Args/Returns/Raises sections with examples
6. **Metadata Tracking**: Sources track `last_loaded`, `load_count`, `error_count` via `SourceMetadata.record_load()`

## Performance Considerations

### Cache Backend Selection
- **MemoryCache**: Fast (O(1) access), volatile, use for short-lived apps or dev
- **FileCache**: Persistent across restarts, slower (disk I/O), use for production
- **NullCache**: Disables caching, use for testing or dynamic configs

```python
# High-performance memory cache with LRU eviction
cache = ConfigCache(
    backend=EnterpriseMemoryCache(max_size=100, default_ttl=300.0)
)

# Persistent file cache with compression
cache = ConfigCache(
    backend=EnterpriseFileCache(
        cache_dir=".cache", 
        default_ttl=3600.0,
        max_files=1000,
        compression=True  # Reduces disk usage
    )
)
```

### Cache Invalidation
- File sources: Auto-invalidate on mtime change
- Remote sources: Manual `cache.delete(key)` or TTL expiry
- Schema changes: Invalidate `_validated_config = None` in ConfigManager

### Validation Performance
- Use `ValidationLevel.LENIENT` for runtime configs (auto-convert types)
- Use `ValidationLevel.STRICT` for startup validation (fail fast)
- Cache validated config: `_validated_config` stores schema validation result

## Common Pitfalls

- **Don't** use `dict.update()` for config merging - use `_deep_update()` to preserve nested structures
- **Don't** access `_config` without acquiring `_config_lock` in threaded contexts
- **Don't** forget to call `profile_manager.set_active_profile()` before loading profile-specific sources
- **Don't** return `None` from source `_do_load()` - always return `Dict[str, Any]` (empty `{}` is OK)
- **Always** validate cache keys include source-specific identifiers (file path, URL, timestamp)
- **Always** test new sources with `is_available()` before calling `load()`
- **Always** use `with self._config_lock:` when reading/writing `_config` or `_sources`

## Source Types & Usage

### Built-in Sources
- **JsonSource** (`json_source.py`): JSON files with UTF-8 encoding
- **YamlSource** (`yaml_source.py`): YAML files, requires `pyyaml` extra
- **TomlSource** (`toml_source.py`): TOML files, requires `tomli` (Python <3.11) or stdlib
- **IniSource** (`ini_source.py`): INI/ConfigParser files with section support
- **EnvironmentSource** (`environment.py`): Env vars with prefix filtering, nested structures
- **RemoteSource** (`remote_source.py`): HTTP/HTTPS JSON endpoints with auth support
- **SecretsConfigSource** (`secrets_source.py`): Encrypted secrets integration

### Source Priority Example
```python
# Typical layered configuration setup
config = ConfigManager()
config.add_source(JsonSource('defaults.json'))          # Base defaults
config.add_source(YamlSource('config.yaml'))            # App config
config.add_source(IniSource('legacy.ini'))              # Legacy settings
config.add_source(EnvironmentSource(prefix='APP_'))     # Runtime overrides
config.add_source(RemoteSource('https://cfg.example.com/app'))  # Central config

# Result: Remote > Env > INI > YAML > JSON (for conflicting keys)
```

## Remote Source Patterns

### With Authentication
```python
source = RemoteSource(
    url='https://api.example.com/config',
    auth_token='your-token',           # Auto-adds "Bearer " prefix
    auth_header='Authorization',       # Default header
    timeout=30.0,
    verify_ssl=True
)
```

### Custom Headers
```python
source = RemoteSource(
    url='https://api.example.com/config',
    headers={
        'X-API-Key': 'secret-key',
        'Accept': 'application/json'
    }
)
```

## Key Files Reference

- `config_manager/config_manager.py`: Main API, auto-reload logic (lines 1-200 for core API)
- `config_manager/sources/base.py`: Source protocol and BaseSource implementation (lines 61-200)
- `config_manager/sources/environment.py`: Env var parsing with nested support (lines 1-100)
- `config_manager/validation.py`: ValidationEngine, validators (TypeValidator, RangeValidator, etc.)
- `config_manager/cache.py`: ConfigCache with backend implementations (lines 100-300 for CacheEntry/Metrics)
- `config_manager/secrets.py`: SecretsManager and provider implementations (lines 200-300 for providers)
- `config_manager/profiles.py`: ProfileManager for env-specific configs (lines 1-100)
- `pyproject.toml`: Tool configurations (black, isort, mypy, pytest settings)
- `tests/conftest.py`: Shared test fixtures and utilities

## Windows-Specific Notes

Default shell is PowerShell v5.1:
- Use `;` for command chaining (not `&&`)
- Path separators are `\` but Python Path handles cross-platform
- Virtual env activation: `.venv\Scripts\activate`

### Source Priority Example
```python
# Typical layered configuration setup
config = ConfigManager()
config.add_source(JsonSource('defaults.json'))          # Base defaults
config.add_source(YamlSource('config.yaml'))            # App config
config.add_source(IniSource('legacy.ini'))              # Legacy settings
config.add_source(EnvironmentSource(prefix='APP_'))     # Runtime overrides
config.add_source(RemoteSource('https://cfg.example.com/app'))  # Central config

# Result: Remote > Env > INI > YAML > JSON (for conflicting keys)
```

## Remote Source Patterns

### With Authentication
```python
source = RemoteSource(
    url='https://api.example.com/config',
    auth_token='your-token',           # Auto-adds "Bearer " prefix
    auth_header='Authorization',       # Default header
    timeout=30.0,
    verify_ssl=True
)
```

### Custom Headers
```python
source = RemoteSource(
    url='https://api.example.com/config',
    headers={
        'X-API-Key': 'secret-key',
        'Accept': 'application/json'
    }
)
```

## Key Files Reference

- `config_manager/config_manager.py`: Main API, auto-reload logic (lines 1-200 for core API)
- `config_manager/sources/base.py`: Source protocol and BaseSource implementation (lines 61-200)
- `config_manager/sources/environment.py`: Env var parsing with nested support (lines 1-100)
- `config_manager/validation.py`: ValidationEngine, validators (TypeValidator, RangeValidator, etc.)
- `config_manager/cache.py`: ConfigCache with backend implementations (lines 100-300 for CacheEntry/Metrics)
- `config_manager/secrets.py`: SecretsManager and provider implementations (lines 200-300 for providers)
- `config_manager/profiles.py`: ProfileManager for env-specific configs (lines 1-100)
- `pyproject.toml`: Tool configurations (black, isort, mypy, pytest settings)
- `tests/conftest.py`: Shared test fixtures and utilities

## Windows-Specific Notes

Default shell is PowerShell v5.1:
- Use `;` for command chaining (not `&&`)
- Path separators are `\` but Python Path handles cross-platform
- Virtual env activation: `.venv\Scripts\activate`

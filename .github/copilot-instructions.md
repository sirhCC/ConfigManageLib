# ConfigManager AI Coding Guidelines

Enterprise-grade Python configuration management library with zero-dependency core and comprehensive validation/caching/secrets systems.

## ⚠️ Project Status (Updated: November 16, 2025)

**Current Maturity Level:** Alpha/Beta - Active Development

### What's Working (Production-Ready):
- ✅ **Core ConfigManager**: Thread-safe operations, source priority system
- ✅ **JSON Source**: 83.91% coverage, 30 comprehensive tests, production-ready
- ✅ **Environment Source**: 93.99% coverage, 20 comprehensive tests, **FIXED** empty prefix bug
- ✅ **YAML Source**: 83.80% coverage, 30 comprehensive tests, production-ready
- ✅ **Deep merge system**: Properly merges nested dictionaries
- ✅ **Type-safe getters**: get_int(), get_bool(), get_float(), get_list()
- ✅ **BaseSource protocol**: Clean abstraction for all sources

### What Needs Work (Do Not Use in Production):
- ⚠️ **Validation Engine**: 12% coverage - implemented but undertested
- ⚠️ **Cache System**: 21-31% coverage - basic functionality works, edge cases untested  
- ⚠️ **Secrets Management**: 15% coverage - architecture solid, needs comprehensive tests
- ⚠️ **Schema System**: 22% coverage - dataclass design good, validation integration incomplete
- ❌ **Secrets Sources**: 0% coverage - not production-ready
- ❌ **Remote Source**: 19% coverage - minimal testing
- ⚠️ **TOML Source**: 35.05% coverage (improved from 8%) - 27 comprehensive tests added
- ❌ **INI Source**: 13% coverage - basic implementation only

### Recent Fixes (Nov 16, 2025 - Session 2):
1. **Fixed EnvironmentSource bugs:**
   - Empty prefix (`prefixes=[]`) now correctly loads all environment variables
   - Fixed `if not matched_prefix:` to `if matched_prefix is None:` to handle empty string prefix
2. **Fixed 3 failing tests** in test_config_manager.py by adding `nested=False` to EnvironmentSource
3. **Added comprehensive EnvironmentSource tests** - 20 tests achieving 93.99% coverage
4. **Added comprehensive JsonSource tests** - 30 tests achieving 83.91% coverage
5. **Added comprehensive YamlSource tests** - 30 tests achieving 83.80% coverage
6. **Added comprehensive ConfigManager tests** - 33 tests improving coverage from 12.94% to 44.15%
7. **Added comprehensive TomlSource tests** - 27 tests improving coverage from 8% to 35.05%
8. **Fixed syntax error** in test_secrets_management.py (f-string backslash issue - line 493)
9. **Overall comprehensive tests status**: 140/140 tests passing ✅ (Environment + JSON + YAML + ConfigManager + TOML)

### Quality Metrics:
- **Overall Coverage**: ~28% (Target: 95%)
- **Core Module Coverage**:
  - EnvironmentSource: 93.99% ✅
  - JsonSource: 83.91% ✅
  - YamlSource: 83.80% ✅
  - BaseSource: 89.47% ✅
  - TomlSource: 35.05% ⚠️ (improved from 8%)
  - ConfigManager: 44.15% ⚠️ (improved from 12.94%)
  - Cache: 21.51%
  - Validation: 12.12%
- **Comprehensive Test Suite**: 140/140 tests passing ✅ (Environment, JSON, YAML, TOML sources + ConfigManager)
- **Overall Test Suite**: 250+ passing, 57 failing (other modules), 6 skipped
- **Known Bugs**: None in tested modules

## Architecture Overview

**Core Pattern**: Source Priority System - later sources override earlier ones via `_deep_update()` (recursive dict merging, not replacement).

**Key Components**:
- `ConfigManager`: Main orchestrator with thread-safe operations (`_config_lock` RLock)
- `BaseSource` + `ConfigSource` Protocol: All sources inherit from `config_manager/sources/base.py` with `load() -> Dict[str, Any]`, `is_available()`, and `SourceMetadata` tracking
- `ValidationEngine`: Dataclass-first validation with `ValidationContext` (frozen immutable) and `ValidationResult` (performance tracking)
- `ConfigCache`: Backend-agnostic (`EnterpriseMemoryCache`/`EnterpriseFileCache`/`NullCache`) with TTL, LRU eviction, and metrics
- `SecretsManager`: Provider pattern for `LocalEncryptedSecrets`, `HashiCorpVaultSecrets`, `AzureKeyVaultSecrets`
- `ProfileManager`: Environment-specific configs via `ConfigProfile` with inheritance chains

## Critical Patterns

### Adding Configuration Sources
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

### Validation with Context
Always use `ValidationContext` for path tracking and `ValidationResult` for detailed feedback:
```python
context = ValidationContext(path="database.port", level=ValidationLevel.STRICT)
result = validator.validate(value, context)
if not result.is_valid:
    # result.errors, result.warnings, result.transformations available
```

### Thread Safety
All config operations use `self._config_lock` (RLock). When modifying `_config`, invalidate `_validated_config = None`.

### Caching Strategy
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

### Source Implementation Pattern
All sources follow this structure (see `BaseSource` in `sources/base.py`):
```python
class YourSource(BaseSource):
    def __init__(self, path: str):
        super().__init__(source_type="your_type", source_path=path)
        # Your initialization
    
    def _do_load(self) -> Dict[str, Any]:
        # Implement your loading logic - BaseSource handles error/metrics
        return {"key": "value"}
    
    def is_available(self) -> bool:
        # Check if source is accessible (file exists, URL reachable, etc.)
        return Path(self._metadata.source_path).exists()
```

The `load()` method in `BaseSource` wraps `_do_load()` with:
- Performance timing and logging (`self._logger.debug`)
- Metadata tracking via `SourceMetadata.record_load(success, error)`
- Graceful degradation (returns `{}` on error, never raises)
- Availability check via `is_available()` before loading

### Environment Variables Pattern
`EnvironmentSource` supports nested structures and type parsing:
```python
# Environment: APP_DATABASE_HOST=localhost, APP_DEBUG=true
source = EnvironmentSource(prefix='APP_', nested=True, parse_values=True)
# Result: {'database': {'host': 'localhost'}, 'debug': True}

# Multiple prefixes
source = EnvironmentSource(prefixes=['APP_', 'API_'], case_sensitive=False)
```

Converts underscore notation to nested dicts: `APP_DATABASE_CREDENTIALS_PASSWORD` → `database.credentials.password`

### Secrets Integration
Secrets are accessed via `ConfigManager` but stored separately from config:
```python
# Secrets don't merge into _config, they're queried on-demand
password = config.get_secret('db_password')  # Returns SecretValue object
# SecretValue has: .value, .metadata, .created_at, .last_accessed

# Auto-masking in logs/display
config.mask_secrets_in_display = True  # Replaces secret values with '***'
masked = mask_sensitive_config(config._config)  # Heuristic detection
```

## Development Workflows

### Running Tests
```powershell
# All tests with coverage (95%+ required)
pytest

# Specific test markers
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Single test file
pytest tests/test_config_manager.py -v
```

### Type Checking
Zero type errors enforced via `mypy.ini` with strict flags:
```powershell
mypy config_manager
```

### Code Formatting
Black (88 char) + isort with profile="black":
```powershell
black config_manager tests examples
isort config_manager tests examples
```

### Manual Testing
Examples in `examples/` serve as integration tests - they must run successfully:
```powershell
python examples/basic_usage.py
python examples/advanced_usage.py
python examples/cache_performance.py
```

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

## Testing Patterns

Fixtures in `tests/conftest.py` provide:
- `sample_config_data()`: Standard nested config dict for tests
- Temp file utilities for file-based source testing

Test structure follows pytest markers:
- `@pytest.mark.unit`: Fast, isolated tests
- `@pytest.mark.integration`: Cross-component tests
- `@pytest.mark.slow`: Performance/load tests

Mock file watching with `unittest.mock.MagicMock` for auto-reload tests (avoid real file I/O).

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

# ConfigManager AI Coding Guidelines

## Code Quality Excellence

**Strive for absolute best code.** This project maintains enterprise-grade standards with zero compromises:
- **Zero lint errors** across all components
- **Complete type safety** with comprehensive annotations
- **Performance-optimized** operations with monitoring
- **Thread-safe** by design with minimal locking
- **Backward compatibility** maintained while modernizing
- **Production-ready** patterns throughout

Every contribution should exemplify Python best practices and enterprise software engineering principles.

## Architecture Overview

ConfigManager is an enterprise-grade Python configuration management library with a modular, dataclass-based architecture. The system follows a layered design:

### Core Components
- **ConfigManager** (`config_manager/config_manager.py`) - Main orchestrator with source management, caching, and profile support
- **Sources** (`config_manager/sources/`) - Pluggable configuration sources (JSON, YAML, TOML, INI, Environment, Remote)
- **Validation Engine** (`config_manager/validation.py`) - Enterprise validation system with ValidationContext/ValidationResult dataclasses
- **Schema System** (`config_manager/schema.py`) - Type-safe field definitions with factory functions (String, Integer, Boolean)
- **Cache System** (`config_manager/cache.py`) - Multi-backend caching with EnterpriseMemoryCache and CacheManager
- **Secrets Management** (`config_manager/secrets.py`) - SecretValue wrapper with encryption providers and automatic masking

### Key Design Patterns

**Dataclass-First Architecture**: All core components use dataclasses (ValidationContext, ValidationResult, CacheStats, FieldMetadata) for type safety and performance.

**Source Priority System**: Sources are processed in order of addition, with later sources overriding earlier ones:
```python
config.add_source(YamlSource('base.yaml'))        # Base config
config.add_source(JsonSource('env.json'))         # Environment override  
config.add_source(EnvironmentSource(prefix='APP_')) # Runtime override
```

**Enterprise Validation**: Use ValidationEngine with composite validators. Always create ValidationContext for comprehensive error reporting:
```python
from config_manager.validation import ValidationEngine, TypeValidator, RequiredValidator
engine = ValidationEngine([TypeValidator(str), RequiredValidator()])
```

**Schema Field Factories**: Use factory functions instead of direct class instantiation:
```python
# Correct
schema = Schema({
    "port": Integer(validators=[RangeValidator(1024, 65535)]),
    "name": String(required=True)
})
```

## Development Workflows

### Testing
- **Unit Tests**: Run `python -m unittest discover tests/` (unittest-based, no pytest)
- **Comprehensive Test**: Run `python comprehensive_test.py` for full system verification
- **Integration Tests**: Files prefixed with `test_` in `tests/` directory
- **Example Verification**: All examples in `examples/` are executable test cases

### Key Commands
```bash
# Run all tests
python -m unittest discover tests/

# Test specific component
python tests/test_config_manager.py

# Comprehensive system verification
python comprehensive_test.py

# Example testing (any file in examples/)
python examples/advanced_usage.py
```

### File Organization Conventions

**Source Modules**: Each source type has its own module in `config_manager/sources/` with fallback parsing support
**Tests**: Mirror the source structure - `test_config_manager.py` tests `config_manager.py`
**Examples**: Production-ready examples in `examples/` demonstrating real-world patterns
**Documentation**: Technical docs in `docs/` with implementation details

## Critical Integration Points

### Cache Integration
All ConfigManager instances use a global cache by default. Cache operations are thread-safe:
```python
# Cache stats are returned as dictionaries, not objects
stats = config.get_cache_stats()
print(f"Hits: {stats['cache_hits']}, Misses: {stats['cache_misses']}")
```

### Profile Management
Profiles enable environment-specific configurations with auto-detection:
```python
# Auto-detects from ENVIRONMENT, APP_ENV, etc.
config = ConfigManager(profile='production', auto_detect_profile=True)
```

### Secrets Handling
SecretValue wrapper provides automatic masking and access tracking:
```python
from config_manager.secrets import mask_sensitive_config
safe_config = mask_sensitive_config(config.get_config())  # Masks passwords/keys
```

## Error Handling Patterns

**ValidationError**: Thrown by validation engine, contains path and detailed context
**Source Loading**: Sources fail gracefully - missing files don't crash the system
**Schema Validation**: Use lenient mode for backward compatibility, strict for new code

## Performance Considerations

- **Lazy Loading**: Sources are only loaded when configuration is accessed
- **Caching**: Enabled by default with configurable backends and TTL
- **Thread Safety**: All operations are thread-safe with minimal locking
- **Auto-reload**: File watching with configurable intervals (requires watchdog package)

## Project-Specific Conventions

**Import Patterns**: Examples use try/except for package imports with development fallback:
```python
try:
    from config_manager import ConfigManager
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config_manager import ConfigManager
```

**Type Safety**: Use typing annotations and dataclasses throughout. Avoid bare dicts for structured data.

**Enterprise Features**: All components support monitoring, statistics, and health checks - leverage these for production deployments.

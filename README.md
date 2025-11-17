# ConfigManageLib

[![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-28%25-yellow.svg)](htmlcov/index.html)

**Zero-dependency Python configuration management with enterprise features**

---

## Installation

```bash
# Core package (zero dependencies)
pip install configmanagelib

# With optional features
pip install configmanagelib[yaml]  # YAML support
pip install configmanagelib[toml]  # TOML support (Python < 3.11)
pip install configmanagelib[all]   # All features
```

---

## Quick Start

```python
from config_manager import ConfigManager
from config_manager.sources import JsonSource, EnvironmentSource

config = ConfigManager()
config.add_source(JsonSource('config.json'))
config.add_source(EnvironmentSource(prefix='APP_'))

# Type-safe access
db_host = config.get('database.host', 'localhost')
port = config.get_int('server.port', 8080)
debug = config.get_bool('debug', False)
```

---

## Features

- **Multiple Sources**: JSON, YAML, TOML, INI, Environment variables
- **Type Safety**: `get_int()`, `get_bool()`, `get_float()`, `get_list()` with automatic conversion
- **Deep Access**: Nested configuration with dot notation (`database.credentials.password`)
- **Source Priority**: Later sources override earlier ones (environment overrides files)
- **Caching**: Memory and file-based caching with LRU/LFU/FIFO eviction
- **Validation**: Comprehensive validation engine with custom validators
- **Zero Dependencies**: Core library has no external dependencies

---

## Development Status

**Version:** 0.1.0 (Alpha/Beta)  
**Overall Coverage:** 28% (Target: 95%)

### Production-Ready (85%+ coverage)
- ✅ INI Source (97.01%)
- ✅ Environment Source (93.99%)
- ✅ BaseSource (89.47%)
- ✅ Validation Engine (85.06%)
- ✅ JSON Source (83.91%)
- ✅ YAML Source (83.80%)
- ✅ Cache System (80.29%)

### In Development (50-85% coverage)
- ⚠️ ConfigManager Core (57.62%)

### Not Production-Ready (<50% coverage)
- ❌ TOML Source (35.05%)
- ❌ Schema System (22%)
- ❌ Remote Source (19%)
- ❌ Secrets Management (15%)
- ❌ Secrets Sources (0%)

---

## Examples

### Multi-Source Configuration

```python
from config_manager import ConfigManager
from config_manager.sources import YamlSource, JsonSource, EnvironmentSource

config = ConfigManager()
config.add_source(YamlSource('defaults.yaml'))     # Base defaults
config.add_source(JsonSource('config.json'))       # App config
config.add_source(EnvironmentSource(prefix='APP_'))  # Runtime overrides

# Environment variables override JSON, JSON overrides YAML
db_url = config.get('database.url')
```

### Type Conversion

```python
# Automatic type conversion with defaults
port = config.get_int('server.port', 8080)
debug = config.get_bool('debug', False)
timeout = config.get_float('timeout', 30.0)
features = config.get_list('features', [])
```

### Environment Variables with Nesting

```python
from config_manager.sources import EnvironmentSource

# Environment: APP_DATABASE_HOST=localhost, APP_DEBUG=true
source = EnvironmentSource(prefix='APP_', nested=True, parse_values=True)
config = ConfigManager()
config.add_source(source)

# Result: {'database': {'host': 'localhost'}, 'debug': True}
```

### Caching

```python
from config_manager.cache import ConfigCache, EnterpriseMemoryCache

cache = ConfigCache(
    backend=EnterpriseMemoryCache(
        max_size=100,
        default_ttl=300.0,
        eviction_policy='lru'
    )
)

config = ConfigManager(cache=cache)
```

---

## Documentation

### Implementation Guides
- [YAML Implementation](docs/YAML_IMPLEMENTATION.md)
- [INI Implementation](docs/INI_IMPLEMENTATION.md)
- [Caching System](docs/CACHING.md)
- [Schema Validation](docs/SCHEMA_VALIDATION.md)
- [Secrets Management](docs/SECRETS_MANAGEMENT.md)

### Development
- [Contributing Guide](docs/dev/CONTRIBUTING.md)
- [Priority Improvements](docs/dev/PRIORITY_IMPROVEMENTS.md)
- [Changelog](docs/dev/CHANGELOG.md)

### Examples
See `examples/` directory for complete working examples:
- `basic_usage.py` - Getting started
- `advanced_usage.py` - Complex configurations
- `yaml_usage.py`, `ini_usage.py`, `toml_usage.py` - Source-specific examples
- `cache_performance.py` - Caching demonstrations
- `validation.py` - Validation examples

---

## Development

```bash
# Clone and setup
git clone https://github.com/sirhCC/ConfigManageLib.git
cd ConfigManageLib
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=config_manager --cov-report=html

# Type checking
mypy config_manager

# Code formatting
black config_manager tests
isort config_manager tests
```

**Quality Standards:**
- ✅ Full mypy compliance (zero type errors)
- ✅ 332+ passing tests
- ✅ Black (88 char) + isort formatting
- ✅ pytest with markers, fixtures, parametrization
- 🚧 Working toward 95% test coverage

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](docs/dev/CONTRIBUTING.md) for guidelines.

**Priority Areas:**
- Increase test coverage (target: 95%)
- TOML Source improvements
- Schema system integration tests
- Secrets management tests
- Documentation and examples

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Links

- **Repository**: https://github.com/sirhCC/ConfigManageLib
- **Issues**: https://github.com/sirhCC/ConfigManageLib/issues
- **PyPI**: `pip install configmanagelib`

---

**Made with ❤️ for Python developers who need reliable configuration management**

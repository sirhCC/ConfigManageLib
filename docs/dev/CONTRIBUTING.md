# Contributing to ConfigManager

We welcome contributions to ConfigManager! This document provides guidelines for contributing to this enterprise-grade configuration management library.

## 🎯 Code Quality Standards

ConfigManager maintains the highest code quality standards with **zero compromises**:

- **Zero lint errors** across all components
- **Complete type safety** with comprehensive annotations
- **95%+ test coverage** for all new code
- **Performance-optimized** operations
- **Thread-safe** by design
- **Enterprise-ready** patterns throughout

## 🚀 Getting Started

### Prerequisites

- Python 3.7+ 
- Git
- Virtual environment tool (venv, conda, etc.)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/sirhCC/ConfigManageLib.git
cd ConfigManageLib

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
python -m unittest discover tests/

# Run comprehensive system test
python comprehensive_test.py

# Test specific component
python tests/test_config_manager.py

# Run all examples (they serve as integration tests)
python examples/advanced_usage.py
```

## 📝 Contribution Process

### 1. Create an Issue

Before starting work, please create an issue describing:
- The problem you're solving
- Your proposed approach
- Any breaking changes

### 2. Fork and Branch

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ConfigManageLib.git

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 3. Development Guidelines

#### Code Style
- Follow PEP 8 with line length of 88 characters
- Use type hints for all functions and methods
- Write comprehensive docstrings in Google style
- Use dataclasses for structured data

#### Architecture Patterns
- **Dataclass-first**: Use dataclasses for all structured data
- **Protocol-based**: Define clear interfaces with typing.Protocol
- **Enterprise validation**: Use ValidationEngine with ValidationContext
- **Source priority**: Later sources override earlier ones
- **Thread safety**: All operations must be thread-safe

#### Example Code Style

```python
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config_manager.validation import ValidationEngine, ValidationContext

@dataclass
class ConfigurationModel:
    """Type-safe configuration model with validation."""
    
    host: str
    port: int
    ssl_enabled: bool = False
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        engine = ValidationEngine([TypeValidator(str)])
        context = ValidationContext(path="host")
        result = engine.validate(self.host, context)
        
        if not result.is_valid:
            raise ValidationError(f"Invalid host: {result.errors}")
```

### 4. Testing Requirements

#### Unit Tests
- Write tests for all new functionality
- Use unittest framework (project standard)
- Test both success and failure cases
- Include edge cases and error conditions

#### Integration Tests
- Test interaction between components
- Verify thread safety with concurrent access
- Test performance characteristics
- Validate backward compatibility

#### Example Test Structure

```python
import unittest
import threading
from pathlib import Path
from config_manager import ConfigManager
from config_manager.sources import JsonSource

class TestConfigManagerIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {"app": {"name": "test", "port": 8080}}
        
    def test_thread_safe_access(self):
        """Test concurrent configuration access."""
        config = ConfigManager()
        # Add test implementation
        
    def test_backward_compatibility(self):
        """Ensure changes don't break existing APIs."""
        # Add test implementation
```

### 5. Documentation

#### Code Documentation
- Write comprehensive docstrings for all public APIs
- Include usage examples in docstrings
- Document complex algorithms and design decisions
- Update type hints and annotations

#### User Documentation
- Update README.md for new features
- Add examples to `examples/` directory
- Update API documentation
- Create migration guides for breaking changes

## 🔍 Code Review Process

### Review Criteria
- **Functionality**: Does the code work as intended?
- **Architecture**: Does it follow ConfigManager patterns?
- **Performance**: Are there any performance regressions?
- **Security**: Are there any security implications?
- **Testing**: Is test coverage adequate?
- **Documentation**: Is the code well-documented?

### Review Checklist
- [ ] All tests pass
- [ ] No lint errors
- [ ] Type checking passes
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Examples work correctly
- [ ] Thread safety verified
- [ ] Backward compatibility maintained

## 🏗️ Architecture Guidelines

### Core Components
- **ConfigManager**: Main orchestrator with caching and profiles
- **Sources**: Pluggable configuration sources
- **Validation**: Enterprise validation with dataclass architecture
- **Schema**: Type-safe field definitions with factory functions
- **Cache**: Multi-backend caching with thread safety
- **Secrets**: SecretValue wrapper with encryption providers

### Design Principles
- **Modularity**: Clear separation of concerns
- **Extensibility**: Plugin architecture for sources and validators
- **Performance**: Lazy loading and intelligent caching
- **Reliability**: Graceful error handling and fallbacks
- **Security**: Secrets management and access control

## 🎯 Areas for Contribution

### High Priority
- 🔌 **New Configuration Sources**: Add support for new formats
- 🛡️ **Security Enhancements**: Improve encryption and secrets management
- 🚀 **Performance Optimizations**: Cache improvements and async support
- 📚 **Documentation**: API docs, guides, and examples
- 🧪 **Testing**: Additional test cases and scenarios

### Feature Requests
- Configuration templates and includes
- Plugin architecture for extensibility
- CLI tools for configuration management
- IDE integration and schema support
- Monitoring and observability features

## 📋 Pull Request Template

When creating a pull request, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Performance tests pass
- [ ] All examples work

## Documentation
- [ ] Code comments updated
- [ ] README updated
- [ ] API documentation updated
- [ ] Examples added/updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code contributions and reviews

## 📞 Getting Help

- 📖 **Documentation**: Check the `docs/` directory
- 💬 **Issues**: Search existing issues or create a new one
- 📧 **Maintainers**: Reach out to the core team for guidance

## 🏆 Recognition

Contributors will be recognized in:
- CHANGELOG.md for their contributions
- README.md contributors section
- Release notes for significant features

---

Thank you for contributing to ConfigManager! Together we're building the definitive enterprise-grade Python configuration management library.

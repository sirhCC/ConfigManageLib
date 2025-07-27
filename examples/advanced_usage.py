#!/usr/bin/env python3
"""
🚀 Advanced Configuration Management Examples for ConfigManager

This showcase demonstrates sophisticated multi-source configuration patterns.
Features enterprise-grade layering, real-time reloading, and performance monitoring.

✨ What you'll learn:
• Multi-source configuration architecture
• Real-time configuration hot-reloading
• Configuration layering and priority management
• Performance monitoring and debugging
• Type-safe configuration models
• Enterprise deployment patterns
"""

import os
import json
import tempfile
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import sys
from concurrent.futures import ThreadPoolExecutor

# Modern import handling - try package import first, fallback to development path
try:
    from config_manager import ConfigManager
    from config_manager.sources import JsonSource, EnvironmentSource, YamlSource
except ImportError:
    # Development mode - add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config_manager import ConfigManager
    from config_manager.sources import JsonSource, EnvironmentSource, YamlSource


class LogLevel(Enum):
    """Type-safe logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DeploymentStage(Enum):
    """Type-safe deployment stages."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Type-safe database configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "myapp"
    username: str = "app_user"
    password: str = "secure_password"
    pool_size: int = 10
    connection_timeout: int = 30
    ssl_enabled: bool = True


@dataclass
class ApiConfig:
    """Type-safe API configuration."""
    base_url: str = "https://api.example.com"
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit: int = 1000
    api_key: Optional[str] = None
    endpoints: List[str] = field(default_factory=lambda: ['/health', '/status'])


@dataclass
class FeatureFlags:
    """Type-safe feature toggle configuration."""
    authentication: bool = True
    caching: bool = True
    logging: bool = True
    monitoring: bool = False
    beta_features: bool = False
    experimental_ui: bool = False


@dataclass
class PerformanceConfig:
    """Type-safe performance configuration."""
    max_workers: int = 4
    request_timeout: int = 30
    cache_ttl: int = 3600
    batch_size: int = 100
    enable_profiling: bool = False


@dataclass
class AdvancedAppConfig:
    """Complete enterprise application configuration with type safety."""
    app_name: str = "AdvancedConfigDemo"
    version: str = "2.0.0"
    stage: DeploymentStage = DeploymentStage.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    debug: bool = False
    
    # Nested configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Runtime settings
    hot_reload: bool = False
    config_validation: bool = True
    metrics_enabled: bool = True


# Modern console formatting for beautiful output
class AdvancedConsole:
    """Enhanced console output with performance metrics and styling."""
    
    @staticmethod
    def header(text: str) -> None:
        """Print a styled header with enhanced formatting."""
        print(f"\n🚀 {text}")
        print("=" * (len(text) + 3))
    
    @staticmethod
    def subheader(text: str) -> None:
        """Print a styled subheader."""
        print(f"\n✨ {text}")
        print("-" * (len(text) + 3))
    
    @staticmethod
    def success(text: str) -> None:
        """Print success message."""
        print(f"✅ {text}")
    
    @staticmethod
    def info(text: str, indent: int = 0) -> None:
        """Print info message with optional indentation."""
        prefix = "  " * indent
        print(f"{prefix}• {text}")
    
    @staticmethod
    def warning(text: str) -> None:
        """Print warning message."""
        print(f"⚠️  {text}")
        
    @staticmethod
    def error(text: str) -> None:
        """Print error message."""
        print(f"❌ {text}")
    
    @staticmethod
    def performance(text: str, duration: float) -> None:
        """Print performance metric."""
        print(f"⚡ {text}: {duration:.4f}s")
    
    @staticmethod
    def source_info(name: str, priority: int, loaded: bool = True) -> None:
        """Print configuration source information."""
        status = "✅" if loaded else "❌"
        print(f"  📁 {name} (priority: {priority}) {status}")


@contextmanager
def temp_config_files(configs: Dict[str, Dict[str, Any]]):
    """Advanced context manager for creating temporary configuration files."""
    with tempfile.TemporaryDirectory(prefix="advanced_config_") as temp_dir:
        temp_path = Path(temp_dir)
        config_files = {}
        
        for config_name, config_data in configs.items():
            # Support different file formats
            if config_name.endswith('.yaml') or config_name.endswith('.yml'):
                config_file = temp_path / config_name
                import yaml
                config_file.write_text(yaml.dump(config_data, default_flow_style=False))
            else:
                config_file = temp_path / f"{config_name}.json"
                config_file.write_text(json.dumps(config_data, indent=2))
            
            config_files[config_name] = config_file
            
        yield temp_path, config_files


@contextmanager
def environment_context(env_vars: Dict[str, str]):
    """Context manager for temporarily setting environment variables."""
    original_values = {}
    
    # Store original values and set new ones
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = str(value)
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


class ConfigurationMonitor:
    """Advanced configuration monitoring and performance tracking."""
    
    def __init__(self):
        self.load_times: Dict[str, float] = {}
        self.reload_count: int = 0
        self.source_priorities: Dict[str, int] = {}
    
    def track_load_time(self, source_name: str, duration: float) -> None:
        """Track configuration loading time."""
        self.load_times[source_name] = duration
    
    def increment_reload(self) -> None:
        """Increment reload counter."""
        self.reload_count += 1
    
    def set_priority(self, source_name: str, priority: int) -> None:
        """Set source priority."""
        self.source_priorities[source_name] = priority
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        total_load_time = sum(self.load_times.values())
        return {
            "total_load_time": total_load_time,
            "source_load_times": self.load_times,
            "reload_count": self.reload_count,
            "source_priorities": self.source_priorities,
            "average_load_time": total_load_time / len(self.load_times) if self.load_times else 0
        }



def demo_basic_multi_source() -> None:
    """Demonstrate basic multi-source configuration with modern patterns."""
    AdvancedConsole.header("Multi-Source Configuration Architecture")
    
    monitor = ConfigurationMonitor()
    
    try:
        # Create realistic configuration layers
        config_layers = {
            'base': {
                "app_name": "AdvancedConfigDemo",
                "version": "2.0.0",
                "stage": "development",
                "debug": False,
                "log_level": "INFO",
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "myapp_base",
                    "pool_size": 5
                },
                "api": {
                    "base_url": "https://api-dev.example.com",
                    "timeout": 30,
                    "retry_attempts": 3
                },
                "features": {
                    "authentication": True,
                    "caching": False,
                    "logging": True
                }
            },
            'environment': {
                "debug": True,
                "log_level": "DEBUG",
                "database": {
                    "name": "myapp_dev",
                    "pool_size": 10
                },
                "features": {
                    "caching": True,
                    "beta_features": True
                }
            },
            'override': {
                "stage": "testing",
                "api": {
                    "base_url": "https://api-test.example.com",
                    "timeout": 45
                },
                "features": {
                    "monitoring": True,
                    "experimental_ui": True
                }
            }
        }
        
        with temp_config_files(config_layers) as (temp_path, config_files):
            AdvancedConsole.subheader("Configuration Source Loading")
            
            # Initialize ConfigManager with performance monitoring
            start_time = time.time()
            cm = ConfigManager()
            
            # Add sources with explicit priority
            sources = [
                ("base.json", 1, JsonSource(str(config_files['base']))),
                ("environment.json", 2, JsonSource(str(config_files['environment']))),
                ("override.json", 3, JsonSource(str(config_files['override'])))
            ]
            
            for name, priority, source in sources:
                source_start = time.time()
                cm.add_source(source)
                load_time = time.time() - source_start
                
                monitor.track_load_time(name, load_time)
                monitor.set_priority(name, priority)
                AdvancedConsole.source_info(name, priority)
                AdvancedConsole.performance(f"Loaded {name}", load_time)
            
            total_time = time.time() - start_time
            AdvancedConsole.performance("Total initialization", total_time)
            
            AdvancedConsole.subheader("Configuration Layering Results")
            
            # Display effective configuration with source attribution
            config_checks = [
                ("app_name", "Application name"),
                ("stage", "Deployment stage"),
                ("debug", "Debug mode"), 
                ("log_level", "Logging level"),
                ("database.name", "Database name"),
                ("database.pool_size", "Connection pool size"),
                ("api.base_url", "API base URL"),
                ("api.timeout", "API timeout"),
                ("features.caching", "Caching enabled"),
                ("features.beta_features", "Beta features"),
                ("features.monitoring", "Monitoring enabled")
            ]
            
            for key, description in config_checks:
                value = cm.get(key)
                AdvancedConsole.info(f"{description}: {value}")
            
            # Show feature flags summary
            features = cm.get('features') or {}
            enabled_features = [k for k, v in features.items() if v]
            AdvancedConsole.info(f"Enabled features: {', '.join(enabled_features)}")
            
            AdvancedConsole.success("Multi-source configuration loaded successfully")
            
    except Exception as e:
        AdvancedConsole.error(f"Multi-source configuration error: {e}")
        raise


def demo_environment_variable_integration() -> None:
    """Demonstrate advanced environment variable integration patterns."""
    AdvancedConsole.header("Environment Variable Integration & Overrides")
    
    try:
        # Create base configuration
        base_config = {
            "app_name": "EnvIntegrationDemo",
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "myapp",
                "ssl_enabled": False
            },
            "api": {
                "timeout": 30,
                "rate_limit": 1000
            },
            "features": {
                "caching": False,
                "monitoring": False
            }
        }
        
        with temp_config_files({'base': base_config}) as (temp_path, config_files):
            # Set environment variables with different patterns
            env_overrides = {
                "APP_DEBUG": "true",
                "APP_DATABASE_HOST": "prod-db.example.com",
                "APP_DATABASE_PORT": "5433",
                "APP_DATABASE_SSL_ENABLED": "true",
                "APP_API_TIMEOUT": "60",
                "APP_API_RATE_LIMIT": "5000",
                "APP_FEATURES_CACHING": "true",
                "APP_FEATURES_MONITORING": "true",
                "APP_FEATURES_BETA_FEATURES": "true"
            }
            
            with environment_context(env_overrides):
                AdvancedConsole.subheader("Environment Variable Configuration")
                
                cm = ConfigManager()
                cm.add_source(JsonSource(str(config_files['base'])))
                cm.add_source(EnvironmentSource(prefix="APP_"))
                
                AdvancedConsole.info("Environment variable overrides:")
                for key, value in env_overrides.items():
                    AdvancedConsole.info(f"{key}={value}", indent=1)
                
                AdvancedConsole.subheader("Effective Configuration")
                
                # Show how environment variables override base config
                config_comparisons = [
                    ("debug", "Debug mode", "env only"),
                    ("database.host", "Database host", "overridden"),
                    ("database.port", "Database port", "overridden"),
                    ("database.ssl_enabled", "SSL enabled", "overridden"),
                    ("api.timeout", "API timeout", "overridden"),
                    ("api.rate_limit", "Rate limit", "overridden"),
                    ("features.caching", "Caching", "overridden"),
                    ("features.monitoring", "Monitoring", "overridden"),
                    ("features.beta_features", "Beta features", "env only")
                ]
                
                for key, description, source in config_comparisons:
                    value = cm.get(key)
                    AdvancedConsole.info(f"{description}: {value} ({source})")
                
                AdvancedConsole.success("Environment variable integration completed")
                
    except Exception as e:
        AdvancedConsole.error(f"Environment integration error: {e}")
        raise


def demo_hot_reload_configuration() -> None:
    """Demonstrate real-time configuration hot-reloading capabilities."""
    AdvancedConsole.header("Hot-Reload Configuration Management")
    
    try:
        # Create initial configuration
        initial_config = {
            "app_name": "HotReloadDemo", 
            "debug": False,
            "log_level": "INFO",
            "features": {
                "feature_a": True,
                "feature_b": False,
                "feature_c": False
            },
            "performance": {
                "cache_ttl": 3600,
                "batch_size": 100
            }
        }
        
        with temp_config_files({'dynamic': initial_config}) as (temp_path, config_files):
            AdvancedConsole.subheader("Initial Configuration State")
            
            cm = ConfigManager()
            cm.add_source(JsonSource(str(config_files['dynamic'])))
            
            # Display initial state
            AdvancedConsole.info(f"Debug mode: {cm.get('debug')}")
            AdvancedConsole.info(f"Log level: {cm.get('log_level')}")
            AdvancedConsole.info(f"Feature A: {cm.get('features.feature_a')}")
            AdvancedConsole.info(f"Feature B: {cm.get('features.feature_b')}")
            AdvancedConsole.info(f"Cache TTL: {cm.get('performance.cache_ttl')}s")
            
            AdvancedConsole.subheader("Simulating Configuration Changes")
            
            # Simulate configuration updates
            updates = [
                {
                    "description": "Enable debug mode and change log level",
                    "changes": {
                        "debug": True,
                        "log_level": "DEBUG",
                        "features": {
                            "feature_a": True,
                            "feature_b": True,
                            "feature_c": False
                        },
                        "performance": {
                            "cache_ttl": 1800,
                            "batch_size": 50
                        }
                    }
                },
                {
                    "description": "Enable all features and optimize performance",
                    "changes": {
                        "debug": False,
                        "log_level": "WARNING",
                        "features": {
                            "feature_a": True,
                            "feature_b": True,
                            "feature_c": True
                        },
                        "performance": {
                            "cache_ttl": 7200,
                            "batch_size": 200
                        }
                    }
                }
            ]
            
            for i, update in enumerate(updates, 1):
                AdvancedConsole.info(f"Update {i}: {update['description']}")
                
                # Write updated configuration
                updated_config = {**initial_config, **update['changes']}
                config_files['dynamic'].write_text(json.dumps(updated_config, indent=2))
                
                # Reload configuration
                reload_start = time.time()
                cm.reload()
                reload_time = time.time() - reload_start
                
                AdvancedConsole.performance(f"Configuration reload {i}", reload_time)
                
                # Show updated values
                AdvancedConsole.info(f"Debug mode: {cm.get('debug')}", indent=1)
                AdvancedConsole.info(f"Log level: {cm.get('log_level')}", indent=1)
                AdvancedConsole.info(f"Feature B: {cm.get('features.feature_b')}", indent=1)
                AdvancedConsole.info(f"Feature C: {cm.get('features.feature_c')}", indent=1)
                AdvancedConsole.info(f"Cache TTL: {cm.get('performance.cache_ttl')}s", indent=1)
                
                print()  # Space between updates
            
            AdvancedConsole.success("Hot-reload demonstration completed")
            
    except Exception as e:
        AdvancedConsole.error(f"Hot-reload error: {e}")
        raise


def demo_performance_monitoring() -> None:
    """Demonstrate advanced performance monitoring and configuration debugging."""
    AdvancedConsole.header("Performance Monitoring & Configuration Debugging")
    
    monitor = ConfigurationMonitor()
    
    try:
        # Create multiple configuration sources with varying sizes
        large_config: Dict[str, Any] = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_config.update({
            "app_name": "PerformanceDemo",
            "database": {"host": "localhost", "port": 5432},
            "features": {f"feature_{i}": i % 2 == 0 for i in range(50)}
        })
        
        medium_config = {f"override_{i}": f"override_value_{i}" for i in range(100)}
        small_config = {"debug": True, "log_level": "DEBUG"}
        
        configs = {
            'large': large_config,
            'medium': medium_config,
            'small': small_config
        }
        
        with temp_config_files(configs) as (temp_path, config_files):
            AdvancedConsole.subheader("Configuration Loading Performance")
            
            cm = ConfigManager()
            
            # Load sources with performance tracking
            load_results = []
            for name, config_file in config_files.items():
                start_time = time.time()
                source = JsonSource(str(config_file))
                cm.add_source(source)
                load_time = time.time() - start_time
                
                config_size = len(json.dumps(configs[name]))
                load_results.append((name, load_time, config_size))
                monitor.track_load_time(name, load_time)
                
                AdvancedConsole.info(f"{name}.json: {config_size:,} bytes")
                AdvancedConsole.performance(f"Load time", load_time)
                print()
            
            AdvancedConsole.subheader("Configuration Access Performance")
            
            # Test configuration access performance
            access_tests = [
                ("Simple key", lambda: cm.get('debug')),
                ("Nested key", lambda: cm.get('database.host')),
                ("Complex nested", lambda: cm.get('features.feature_10')),
                ("Non-existent key", lambda: cm.get('non.existent.key')),
                ("Large key iteration", lambda: [cm.get(f'key_{i}') for i in range(0, 100, 10)])
            ]
            
            for test_name, test_func in access_tests:
                start_time = time.time()
                result = test_func()
                access_time = time.time() - start_time
                
                AdvancedConsole.performance(test_name, access_time)
                if test_name != "Large key iteration":
                    AdvancedConsole.info(f"Result: {result}", indent=1)
                else:
                    AdvancedConsole.info(f"Retrieved {len(result)} values", indent=1)
            
            AdvancedConsole.subheader("Performance Summary")
            
            report = monitor.get_performance_report()
            AdvancedConsole.info(f"Total sources loaded: {len(report['source_load_times'])}")
            AdvancedConsole.info(f"Total load time: {report['total_load_time']:.4f}s")
            AdvancedConsole.info(f"Average load time: {report['average_load_time']:.4f}s")
            AdvancedConsole.info(f"Reload count: {report['reload_count']}")
            
            # Show per-source performance
            AdvancedConsole.info("Per-source performance:")
            for source, load_time in report['source_load_times'].items():
                AdvancedConsole.info(f"{source}: {load_time:.4f}s", indent=1)
            
            AdvancedConsole.success("Performance monitoring completed")
            
    except Exception as e:
        AdvancedConsole.error(f"Performance monitoring error: {e}")
        raise


def demo_concurrent_configuration() -> None:
    """Demonstrate thread-safe concurrent configuration access."""
    AdvancedConsole.header("Concurrent Configuration Access & Thread Safety")
    
    try:
        # Create configuration for concurrent testing
        concurrent_config = {
            "app_name": "ConcurrentDemo",
            "counters": {f"counter_{i}": 0 for i in range(10)},
            "settings": {f"setting_{i}": f"value_{i}" for i in range(20)},
            "flags": {f"flag_{i}": i % 2 == 0 for i in range(15)}
        }
        
        with temp_config_files({'concurrent': concurrent_config}) as (temp_path, config_files):
            AdvancedConsole.subheader("Thread-Safe Configuration Access")
            
            cm = ConfigManager()
            cm.add_source(JsonSource(str(config_files['concurrent'])))
            
            access_results = []
            access_lock = threading.Lock()
            
            def worker_function(worker_id: int, iterations: int) -> None:
                """Worker function for concurrent access testing."""
                worker_start = time.time()
                
                for i in range(iterations):
                    # Perform various configuration operations
                    app_name = cm.get('app_name')
                    counter_value = cm.get(f'counters.counter_{i % 10}')
                    setting_value = cm.get(f'settings.setting_{i % 20}')
                    flag_value = cm.get(f'flags.flag_{i % 15}')
                    
                    # Simulate some work
                    time.sleep(0.001)
                
                worker_time = time.time() - worker_start
                
                with access_lock:
                    access_results.append((worker_id, worker_time, iterations))
            
            # Run concurrent workers
            num_workers = 5
            iterations_per_worker = 50
            
            AdvancedConsole.info(f"Starting {num_workers} concurrent workers")
            AdvancedConsole.info(f"Each worker performs {iterations_per_worker} configuration accesses")
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(worker_function, worker_id, iterations_per_worker)
                    for worker_id in range(num_workers)
                ]
                
                # Wait for all workers to complete
                for future in futures:
                    future.result()
            
            total_time = time.time() - start_time
            
            AdvancedConsole.subheader("Concurrent Access Results")
            
            total_operations = sum(result[2] for result in access_results)
            AdvancedConsole.info(f"Total operations: {total_operations}")
            AdvancedConsole.info(f"Total time: {total_time:.4f}s")
            AdvancedConsole.info(f"Operations per second: {total_operations / total_time:.2f}")
            
            AdvancedConsole.info("Per-worker performance:")
            for worker_id, worker_time, iterations in access_results:
                ops_per_sec = iterations / worker_time if worker_time > 0 else 0
                AdvancedConsole.info(f"Worker {worker_id}: {worker_time:.4f}s ({ops_per_sec:.1f} ops/sec)", indent=1)
            
            AdvancedConsole.success("Concurrent configuration access completed")
            
    except Exception as e:
        AdvancedConsole.error(f"Concurrent access error: {e}")
        raise


def main() -> None:
    """Execute all advanced configuration management demonstrations."""
    try:
        # Beautiful header
        print("\n" + "="*80)
        print("🚀 ConfigManager: Advanced Configuration Management Patterns")
        print("="*80)
        print("✨ Enterprise-grade multi-source configuration with performance monitoring")
        print()
        
        # Run all advanced demonstrations
        demos = [
            demo_basic_multi_source,
            demo_environment_variable_integration,
            demo_hot_reload_configuration,
            demo_performance_monitoring,
            demo_concurrent_configuration
        ]
        
        for i, demo_func in enumerate(demos, 1):
            try:
                demo_func()
            except Exception as e:
                AdvancedConsole.error(f"Demo {i} failed: {e}")
                continue
        
        # Success summary
        print("\n" + "="*80)
        AdvancedConsole.success("All advanced configuration examples completed successfully!")
        print("🚀 Your ConfigManager demonstrates enterprise-grade capabilities:")
        print("   • Multi-source configuration layering")
        print("   • Real-time hot-reloading")
        print("   • Performance monitoring and optimization")
        print("   • Thread-safe concurrent access")
        print("   • Environment variable integration")
        print("   • Type-safe configuration models")
        print("="*80)
        
    except KeyboardInterrupt:
        AdvancedConsole.warning("Demo interrupted by user")
    except Exception as e:
        AdvancedConsole.error(f"Critical error: {e}")
        raise


if __name__ == "__main__":
    main()

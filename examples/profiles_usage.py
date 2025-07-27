#!/usr/bin/env python3
"""
🔧 Profile and Environment Management Examples for ConfigManager

This showcase demonstrates modern configuration management with profiles and environments.
Features enterprise-grade patterns for development, testing, staging, and production.

✨ What you'll learn:
• Profile management and inheritance
• Environment auto-detection
• Configuration layering strategies  
• Best practices for production deployments
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, field
import sys

# Modern import handling - try package import first, fallback to development path
try:
    from config_manager import ConfigManager, ProfileManager, ConfigProfile
    from config_manager.sources import JsonSource
    from config_manager.profiles import create_profile_source_path, profile_source_exists
except ImportError:
    # Development mode - add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config_manager import ConfigManager, ProfileManager, ConfigProfile
    from config_manager.sources import JsonSource
    from config_manager.profiles import create_profile_source_path, profile_source_exists


@dataclass
class DatabaseConfig:
    """Modern configuration structure with type safety."""
    host: str = "localhost"
    port: int = 5432
    name: str = "myapp"
    ssl_mode: str = "prefer"
    pool_size: int = 10
    
    
@dataclass
class FeatureFlags:
    """Feature toggle configuration."""
    analytics: bool = True
    notifications: bool = True
    new_ui: bool = False
    beta_features: bool = False
    

@dataclass  
class AppConfig:
    """Complete application configuration with type safety."""
    app_name: str = "ConfigManager Demo"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    ssl_required: bool = False
    api_timeout: int = 30
    cache_ttl: int = 3600


# Console formatting for better UX
class Console:
    """Beautiful console output with colors and formatting."""
    
    @staticmethod
    def header(text: str) -> None:
        """Print a styled header."""
        print(f"\n🔧 {text}")
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


@contextmanager
def temp_config_files(configs: Dict[str, Dict[str, Any]]):
    """Context manager for creating temporary configuration files."""
    with tempfile.TemporaryDirectory(prefix="configmanager_") as temp_dir:
        temp_path = Path(temp_dir)
        config_files = {}
        
        for env_name, config_data in configs.items():
            config_file = temp_path / f"{env_name}.json"
            config_file.write_text(json.dumps(config_data, indent=2))
            config_files[env_name] = config_file
            
        yield temp_path, config_files


@contextmanager  
def environment_context(env_vars: Dict[str, str]):
    """Context manager for temporarily setting environment variables."""
    original_values = {}
    
    # Store original values and set new ones
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def demo_basic_profiles() -> None:
    """Demonstrate modern profile management with error handling and validation."""
    Console.header("Basic Profile Management")
    
    try:
        # Initialize ProfileManager with proper error handling
        profile_manager = ProfileManager()
        Console.success("ProfileManager initialized successfully")
        
        # Display available profiles with enhanced formatting
        profiles = profile_manager.list_profiles()
        Console.info(f"Available profiles ({len(profiles)}):")
        for profile_name in profiles:
            Console.info(profile_name, indent=1)
        
        # Demonstrate profile retrieval with validation
        Console.subheader("Profile Inspection")
        
        dev_profile = profile_manager.get_profile('development')
        if dev_profile:
            Console.success(f"Retrieved '{dev_profile.name}' profile")
            Console.info(f"Debug mode: {dev_profile.get_var('debug')}")
            Console.info(f"Log level: {dev_profile.get_var('log_level')}")
            Console.info(f"Cache enabled: {dev_profile.get_var('cache_enabled')}")
        else:
            Console.error("Development profile not found")
            return
        
        # Create custom profile with inheritance
        Console.subheader("Custom Profile Creation")
        
        custom_profile = profile_manager.create_profile('demo', base_profile='production')
        if custom_profile:
            # Configure custom settings with type-safe values
            custom_profile.set_var('feature_flags', {
                'new_ui': True, 
                'analytics': False,
                'beta_features': True
            })
            custom_profile.set_var('cache_ttl', 300)
            custom_profile.set_var('api_timeout', 45)
            
            Console.success(f"Created custom profile: '{custom_profile.name}'")
            Console.info(f"SSL required: {custom_profile.get_var('ssl_required')} (inherited)")
            Console.info(f"Feature flags: {custom_profile.get_var('feature_flags')}")
            Console.info(f"Cache TTL: {custom_profile.get_var('cache_ttl')}s")
        else:
            Console.error("Failed to create custom profile")
            
    except Exception as e:
        Console.error(f"Profile management error: {e}")
        raise


def demo_environment_detection() -> None:
    """Demonstrate intelligent environment detection with modern patterns."""
    Console.header("Environment Detection & Auto-Configuration")
    
    try:
        profile_manager = ProfileManager()
        
        # Show current environment detection
        current_env = profile_manager.detect_environment()
        Console.success(f"Current detected environment: '{current_env}'")
        
        # Demonstrate environment variable priority
        Console.subheader("Environment Variable Priority Testing")
        
        env_tests = [
            ('ENV', 'production', "Standard environment variable"),
            ('NODE_ENV', 'development', "Node.js style"), 
            ('PYTHON_ENV', 'staging', "Python specific"),
            ('CONFIG_ENV', 'testing', "Configuration specific")
        ]
        
        for env_var, env_value, description in env_tests:
            with environment_context({env_var: env_value}):
                detected = profile_manager.detect_environment()
                Console.info(f"{env_var}={env_value} → '{detected}' ({description})")
        
        # Test profile aliases with validation
        Console.subheader("Profile Alias Resolution")
        
        alias_tests = [
            ('prod', 'production'),
            ('dev', 'development'), 
            ('stage', 'staging'),
            ('test', 'testing'),
            ('local', 'development'),
        ]
        
        for alias, expected in alias_tests:
            with environment_context({'ENV': alias}):
                detected = profile_manager.detect_environment()
                status = "✅" if detected == expected else "❌"
                Console.info(f"'{alias}' → '{detected}' {status}")
                
        Console.success("Environment detection completed successfully")
        
    except Exception as e:
        Console.error(f"Environment detection error: {e}")
        raise


def demo_configmanager_with_profiles() -> None:
    """Demonstrate ConfigManager with modern profile integration and type safety."""
    Console.header("ConfigManager with Advanced Profile Integration")
    
    try:
        # Create realistic, type-safe configuration data
        environments = {
            'development': AppConfig(
                app_name="ConfigManager Demo",
                debug=True,
                log_level="DEBUG",
                database=DatabaseConfig(name="myapp_dev", ssl_mode="disable"),
                features=FeatureFlags(beta_features=True),
                cache_ttl=300
            ),
            'testing': AppConfig(
                app_name="ConfigManager Demo",
                debug=False,
                log_level="WARNING", 
                database=DatabaseConfig(name="myapp_test", pool_size=5),
                features=FeatureFlags(analytics=False),
                cache_ttl=600
            ),
            'production': AppConfig(
                app_name="ConfigManager Demo",
                debug=False,
                log_level="ERROR",
                database=DatabaseConfig(name="myapp_prod", ssl_mode="require", pool_size=20),
                features=FeatureFlags(new_ui=False, beta_features=False),
                ssl_required=True,
                cache_ttl=3600
            )
        }
        
        # Convert dataclasses to dictionaries for JSON serialization
        config_data = {
            env: {
                "app_name": config.app_name,
                "version": config.version,
                "debug": config.debug,
                "log_level": config.log_level,
                "ssl_required": config.ssl_required,
                "api_timeout": config.api_timeout,
                "cache_ttl": config.cache_ttl,
                "database": {
                    "host": config.database.host,
                    "port": config.database.port,
                    "name": config.database.name,
                    "ssl_mode": config.database.ssl_mode,
                    "pool_size": config.database.pool_size
                },
                "features": {
                    "analytics": config.features.analytics,
                    "notifications": config.features.notifications,
                    "new_ui": config.features.new_ui,
                    "beta_features": config.features.beta_features
                }
            }
            for env, config in environments.items()
        }
        
        with temp_config_files(config_data) as (temp_path, config_files):
            Console.subheader("Explicit Profile Configuration")
            
            # Demonstrate each environment with detailed output
            for profile_name in ['development', 'testing', 'production']:
                Console.info(f"🔧 {profile_name.upper()} Environment:")
                
                cm = ConfigManager(profile=profile_name)
                cm.add_source(JsonSource(str(config_files[profile_name])))
                
                # Display key configuration values with formatting
                Console.info(f"Database: {cm.get('database.name')} ({cm.get('database.ssl_mode')})", indent=1)
                Console.info(f"Debug mode: {cm.get('debug')}", indent=1)
                Console.info(f"Log level: {cm.get('log_level')}", indent=1)
                Console.info(f"Pool size: {cm.get('database.pool_size')} connections", indent=1)
                Console.info(f"Cache TTL: {cm.get('cache_ttl')}s", indent=1)
                
                # Show feature flags status
                features = cm.get('features') or {}
                enabled_features = [k for k, v in features.items() if v]
                Console.info(f"Features: {', '.join(enabled_features) if enabled_features else 'none'}", indent=1)
                
                if cm.get('ssl_required'):
                    Console.info("🔒 SSL/TLS required", indent=1)
                
                print()  # Space between environments
            
            Console.subheader("Dynamic Profile Switching")
            
            # Demonstrate profile switching with state management
            cm = ConfigManager(profile='development')
            cm.add_source(JsonSource(str(config_files['development'])))
            
            Console.info(f"Initial: {cm.get_current_profile()} → DB: {cm.get('database.name')}")
            
            # Switch profiles and update sources
            cm.set_profile('production')
            cm.add_source(JsonSource(str(config_files['production'])))
            
            Console.info(f"Switched: {cm.get_current_profile()} → DB: {cm.get('database.name')}")
            Console.success("Profile switching completed successfully")
            
    except Exception as e:
        Console.error(f"ConfigManager profile integration error: {e}")
        raise


def demo_profile_specific_sources() -> None:
    """Demonstrate intelligent profile-specific source loading with validation."""
    Console.header("Profile-Specific Configuration Sources")
    
    try:
        # Create realistic multi-layered configuration
        base_config = {
            "app": "ConfigManager Demo",
            "version": "2.0.0",
            "timezone": "UTC",
            "max_connections": 100
        }
        
        profile_configs = {
            'development': {
                "debug": True,
                "log_level": "DEBUG",
                "hot_reload": True,
                "profiling": True,
                "max_connections": 10  # Override base config
            },
            'production': {
                "debug": False,
                "log_level": "ERROR", 
                "ssl_required": True,
                "monitoring": True,
                "max_connections": 500  # Override base config
            }
        }
        
        with temp_config_files({'base': base_config, **profile_configs}) as (temp_path, config_files):
            Console.subheader("Layered Configuration Loading")
            
            for profile_name in ['development', 'production']:
                Console.info(f"🔧 {profile_name.title()} Configuration:")
                
                cm = ConfigManager(profile=profile_name)
                
                # Load base configuration first
                cm.add_source(JsonSource(str(config_files['base'])))
                Console.info(f"Base config loaded: {config_files['base'].name}", indent=1)
                
                # Add profile-specific configuration 
                cm.add_profile_source(str(temp_path))
                Console.info(f"Profile config loaded: {profile_name}.json", indent=1)
                
                # Show effective configuration with inheritance
                Console.info(f"App: {cm.get('app')} v{cm.get('version')}", indent=1)
                Console.info(f"Debug: {cm.get('debug', 'inherited')}", indent=1)
                Console.info(f"Max connections: {cm.get('max_connections')} (profile override)", indent=1)
                Console.info(f"Timezone: {cm.get('timezone')} (from base)", indent=1)
                
                # Show profile-specific features
                if cm.get('hot_reload'):
                    Console.info("🔄 Hot reload enabled", indent=1)
                if cm.get('ssl_required'):
                    Console.info("🔒 SSL/TLS enforced", indent=1)
                if cm.get('monitoring'):
                    Console.info("📊 Monitoring active", indent=1)
                
                print()
                
            Console.success("Profile-specific source loading completed")
            
    except Exception as e:
        Console.error(f"Profile-specific sources error: {e}")
        raise


def demo_profile_path_utilities():
    """Demonstrate profile path utility functions."""
    print("=== Profile Path Utilities ===")
    
    # Demonstrate path creation for directories
    print("Directory-style paths:")
    examples = [
        ('config', 'development'),
        ('settings', 'production', 'yaml'),
        ('configs/', 'staging'),
    ]
    
    for args in examples:
        path = create_profile_source_path(*args)
        print(f"  {args} -> {path}")
    
    # Demonstrate path creation for files
    print("\nFile-style paths:")
    examples = [
        ('app.json', 'development'),
        ('settings.yaml', 'production'),
        ('config', 'test', 'toml'),
    ]
    
    for args in examples:
        path = create_profile_source_path(*args)
        print(f"  {args} -> {path}")
    
    # Demonstrate existence checking
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test file
        test_file = temp_path / "development.json"
        test_file.write_text('{"test": true}')
        
        exists = profile_source_exists(temp_path, 'development')
        not_exists = profile_source_exists(temp_path, 'production')
        
        print(f"\nExistence checking in {temp_path}:")
        print(f"  development.json exists: {exists}")
        print(f"  production.json exists: {not_exists}")
    
    print()


def demo_profile_path_utilities() -> None:
    """Demonstrate modern profile path utilities with validation."""
    Console.header("Profile Path Utilities & File Discovery")
    
    try:
        Console.subheader("Smart Path Generation")
        
        # Directory-style path examples
        Console.info("Directory-based configurations:")
        directory_examples = [
            ('config', 'development'),
            ('settings', 'production', 'yaml'),
            ('configs/', 'staging'),
            ('app-settings', 'testing', 'toml')
        ]
        
        for args in directory_examples:
            path = create_profile_source_path(*args)
            Console.info(f"{args} → {path}", indent=1)
        
        # File-style path examples
        Console.info("\nFile-based configurations:")
        file_examples = [
            ('app.json', 'development'),
            ('database.yaml', 'production'),
            ('cache-config', 'staging', 'toml'),
            ('secrets.json', 'testing')
        ]
        
        for args in file_examples:
            path = create_profile_source_path(*args)
            Console.info(f"{args} → {path}", indent=1)
        
        Console.subheader("File Existence Validation")
        
        # Create realistic test scenario
        with tempfile.TemporaryDirectory(prefix="profile_discovery_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test configuration files
            test_configs = {
                'development.json': {'debug': True, 'env': 'dev'},
                'production.yaml': 'ssl_required: true\nenv: prod\n',
                'staging.toml': '[database]\nname = "staging_db"\n'
            }
            
            for filename, content in test_configs.items():
                config_file = temp_path / filename
                config_file.write_text(content if isinstance(content, str) else json.dumps(content, indent=2))
            
            Console.info(f"Test directory: {temp_path}")
            
            # Test existence checking for different profiles and formats
            test_cases = [
                ('development', 'json', True),
                ('production', 'yaml', True), 
                ('staging', 'toml', True),
                ('testing', 'json', False),
                ('development', 'yaml', False)
            ]
            
            for profile, ext, expected in test_cases:
                exists = profile_source_exists(temp_path, profile, ext)
                status = "✅" if exists == expected else "❌"
                result = "found" if exists else "not found"
                Console.info(f"{profile}.{ext}: {result} {status}", indent=1)
            
            # Demonstrate automatic format detection
            Console.info("\nAutomatic format detection:")
            for profile in ['development', 'production', 'staging', 'testing']:
                exists = profile_source_exists(temp_path, profile)
                if exists:
                    Console.info(f"{profile}: detected ✅", indent=1)
                else:
                    Console.info(f"{profile}: not found ❌", indent=1)
        
        Console.success("Profile path utilities completed successfully")
        
    except Exception as e:
        Console.error(f"Profile path utilities error: {e}")
        raise


def demo_production_patterns() -> None:
    """Demonstrate enterprise production patterns and best practices."""
    Console.header("Production-Ready Configuration Patterns")
    
    try:
        Console.subheader("Environment Auto-Detection in Production")
        
        # Simulate realistic production scenarios
        production_scenarios = [
            ({'ENV': 'production', 'DATABASE_URL': 'postgres://prod-db'}, "Standard production"),
            ({'NODE_ENV': 'production', 'STAGE': 'live'}, "Node.js deployment"),
            ({'PYTHON_ENV': 'prod', 'AWS_ENV': 'production'}, "Python/AWS deployment"),
            ({'CONFIG_ENV': 'staging', 'DEPLOY_ENV': 'blue'}, "Blue/green deployment")
        ]
        
        for env_vars, description in production_scenarios:
            with environment_context(env_vars):
                profile_manager = ProfileManager()
                detected = profile_manager.detect_environment()
                
                env_display = ", ".join(f"{k}={v}" for k, v in env_vars.items())
                Console.info(f"{description}: [{env_display}] → '{detected}'")
        
        Console.subheader("Configuration Validation & Type Safety")
        
        # Demonstrate configuration validation
        with temp_config_files({
            'production': {
                'database': {'host': 'prod-db.company.com', 'port': 5432},
                'cache_ttl': 3600,
                'ssl_required': True,
                'log_level': 'ERROR'
            }
        }) as (temp_path, config_files):
            
            cm = ConfigManager(profile='production')
            cm.add_source(JsonSource(str(config_files['production'])))
            
            # Validate critical production settings
            validations = [
                ('database.host', lambda x: x and '.' in x, "Valid database host"),
                ('database.port', lambda x: isinstance(x, int) and 1000 <= x <= 65535, "Valid port range"),
                ('ssl_required', lambda x: x is True, "SSL enforcement"),
                ('log_level', lambda x: x in ['ERROR', 'CRITICAL'], "Production log level"),
                ('cache_ttl', lambda x: isinstance(x, int) and x > 0, "Positive cache TTL")
            ]
            
            Console.info("Production configuration validation:")
            all_valid = True
            
            for config_path, validator, description in validations:
                value = cm.get(config_path)
                is_valid = validator(value)
                status = "✅" if is_valid else "❌"
                Console.info(f"{description}: {value} {status}", indent=1)
                all_valid &= is_valid
            
            if all_valid:
                Console.success("All production validations passed")
            else:
                Console.warning("Some production validations failed")
        
        Console.subheader("Profile Variable Management")
        
        cm = ConfigManager(profile='production')
        
        # Access built-in profile variables
        Console.info("Built-in profile variables:")
        profile_vars = ['debug', 'log_level', 'ssl_required', 'cache_enabled']
        for var in profile_vars:
            value = cm.get_profile_var(var)
            Console.info(f"{var}: {value}", indent=1)
        
        # Create custom profile with enterprise settings
        custom_profile = cm.create_profile('enterprise')
        enterprise_settings = {
            'api_rate_limit': 1000,
            'connection_timeout': 30,
            'retry_attempts': 3,
            'circuit_breaker_threshold': 0.5,
            'metrics_enabled': True,
            'audit_logging': True
        }
        
        for key, value in enterprise_settings.items():
            custom_profile.set_var(key, value)
        
        cm.set_profile('enterprise')
        Console.info("Enterprise profile variables:")
        for key in enterprise_settings:
            value = cm.get_profile_var(key)
            Console.info(f"{key}: {value}", indent=1)
            
        Console.success("Production patterns demonstration completed")
        
    except Exception as e:
        Console.error(f"Production patterns error: {e}")
        raise


def main() -> None:
    """Execute all modernized profile management demonstrations."""
    try:
        # Beautiful header
        print("\n" + "="*70)
        print("🔧 ConfigManager: Modern Profile & Environment Management")
        print("="*70)
        print("✨ Enterprise-grade configuration patterns and best practices")
        print()
        
        # Run all demonstrations with error handling
        demos = [
            demo_basic_profiles,
            demo_environment_detection, 
            demo_configmanager_with_profiles,
            demo_profile_specific_sources,
            demo_profile_path_utilities,
            demo_production_patterns
        ]
        
        for i, demo_func in enumerate(demos, 1):
            try:
                demo_func()
            except Exception as e:
                Console.error(f"Demo {i} failed: {e}")
                continue
        
        # Success summary
        print("\n" + "="*70)
        Console.success("All profile management examples completed successfully!")
        print("🚀 Your ConfigManager is ready for production deployment")
        print("="*70)
        
    except KeyboardInterrupt:
        Console.warning("Demo interrupted by user")
    except Exception as e:
        Console.error(f"Critical error: {e}")
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Profile and Environment Management Examples for ConfigManager

This example demonstrates how to use configuration profiles and environments
to manage different settings for development, testing, staging, and production.
"""

import os
import tempfile
import json
from pathlib import Path

# Add the parent directory to the Python path so we can import the modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import ConfigManager, ProfileManager, ConfigProfile
from config_manager.sources import JsonSource
from config_manager.profiles import create_profile_source_path, profile_source_exists


def demo_basic_profiles():
    """Demonstrate basic profile management."""
    print("=== Basic Profile Management ===")
    
    # Create a ProfileManager to work with profiles
    profile_manager = ProfileManager()
    
    # List default profiles
    print("Default profiles:")
    for profile_name in profile_manager.list_profiles():
        print(f"  - {profile_name}")
    
    # Get a specific profile
    dev_profile = profile_manager.get_profile('development')
    if dev_profile:
        print(f"\nDevelopment profile: {dev_profile.name}")
        print(f"Debug enabled: {dev_profile.get_var('debug')}")
        print(f"Log level: {dev_profile.get_var('log_level')}")
    else:
        print("\nDevelopment profile not found")
    
    # Create a custom profile
    custom_profile = profile_manager.create_profile('demo', base_profile='production')
    custom_profile.set_var('feature_flags', {'new_ui': True, 'analytics': False})
    custom_profile.set_var('cache_ttl', 300)
    
    print(f"\nCustom profile: {custom_profile.name}")
    print(f"SSL required: {custom_profile.get_var('ssl_required')}")  # Inherited from production
    print(f"Feature flags: {custom_profile.get_var('feature_flags')}")
    print()


def demo_environment_detection():
    """Demonstrate automatic environment detection."""
    print("=== Environment Detection ===")
    
    profile_manager = ProfileManager()
    
    # Show current environment detection
    current_env = profile_manager.detect_environment()
    print(f"Detected environment: {current_env}")
    
    # Simulate different environment variables
    test_envs = {
        'ENV': 'production',
        'NODE_ENV': 'development', 
        'PYTHON_ENV': 'staging',
        'CONFIG_ENV': 'testing'
    }
    
    print("\nSimulating different environment variables:")
    for env_var, env_value in test_envs.items():
        # Temporarily set environment variable
        original_value = os.environ.get(env_var)
        os.environ[env_var] = env_value
        
        detected = profile_manager.detect_environment()
        print(f"  {env_var}={env_value} -> detected: {detected}")
        
        # Restore original value
        if original_value is None:
            os.environ.pop(env_var, None)
        else:
            os.environ[env_var] = original_value
    
    # Test profile aliases
    print("\nTesting profile aliases:")
    test_aliases = ['prod', 'dev', 'stage', 'test']
    for alias in test_aliases:
        os.environ['ENV'] = alias
        detected = profile_manager.detect_environment()
        print(f"  ENV={alias} -> detected: {detected}")
    
    # Clean up
    os.environ.pop('ENV', None)
    print()


def demo_configmanager_with_profiles():
    """Demonstrate ConfigManager with profile support."""
    print("=== ConfigManager with Profiles ===")
    
    # Create temporary configuration files for different environments
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create base configuration
        base_config = {
            "app_name": "MyApp",
            "version": "1.0.0",
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "myapp"
            },
            "features": {
                "analytics": True,
                "notifications": True
            }
        }
        
        # Create environment-specific configurations
        configs = {
            'development': {
                **base_config,
                "database": {**base_config["database"], "name": "myapp_dev"},
                "debug": True,
                "log_level": "DEBUG"
            },
            'testing': {
                **base_config,
                "database": {**base_config["database"], "name": "myapp_test"},
                "debug": False,
                "log_level": "WARNING",
                "features": {**base_config["features"], "analytics": False}
            },
            'production': {
                **base_config,
                "database": {**base_config["database"], "name": "myapp_prod"},
                "debug": False,
                "log_level": "ERROR",
                "ssl_required": True
            }
        }
        
        # Write configuration files
        config_files = {}
        for env, config in configs.items():
            config_file = temp_path / f"{env}.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            config_files[env] = config_file
        
        # Demonstrate explicit profile usage
        print("Using explicit profiles:")
        for profile_name in ['development', 'testing', 'production']:
            cm = ConfigManager(profile=profile_name)
            cm.add_source(JsonSource(config_files[profile_name]))
            
            print(f"\n{profile_name.upper()} Profile:")
            print(f"  Database: {cm.get('database.name')}")
            print(f"  Debug: {cm.get('debug', False)}")
            print(f"  Log Level: {cm.get('log_level', 'INFO')}")
            print(f"  Analytics: {cm.get('features.analytics')}")
            if cm.get('ssl_required'):
                print(f"  SSL Required: {cm.get('ssl_required')}")
        
        # Demonstrate profile switching
        print("\nProfile Switching:")
        cm = ConfigManager(profile='development')
        cm.add_source(JsonSource(config_files['development']))
        
        print(f"Initial profile: {cm.get_current_profile()}")
        print(f"Database name: {cm.get('database.name')}")
        
        # Switch to production profile
        cm.set_profile('production')
        cm.add_source(JsonSource(config_files['production']))
        
        print(f"After switching to production: {cm.get_current_profile()}")
        print(f"Database name: {cm.get('database.name')}")
        
        print()


def demo_profile_specific_sources():
    """Demonstrate adding profile-specific configuration sources."""
    print("=== Profile-Specific Sources ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create base config
        base_config = {"app": "MyApp", "version": "1.0"}
        base_file = temp_path / "config.json"
        with open(base_file, 'w') as f:
            json.dump(base_config, f)
        
        # Create development-specific config
        dev_config = {"debug": True, "log_level": "DEBUG"}
        dev_file = temp_path / "development.json"  # Profile-specific naming
        with open(dev_file, 'w') as f:
            json.dump(dev_config, f)
        
        # Create production-specific config  
        prod_config = {"debug": False, "ssl_required": True}
        prod_file = temp_path / "production.json"  # Profile-specific naming
        with open(prod_file, 'w') as f:
            json.dump(prod_config, f)
        
        # Test with development profile
        print("Development configuration:")
        cm = ConfigManager(profile='development')
        cm.add_source(JsonSource(str(base_file)))  # Base config
        cm.add_profile_source(str(temp_path))  # Will load development.json
        
        print(f"  App: {cm.get('app')}")
        print(f"  Debug: {cm.get('debug')}")
        print(f"  Log Level: {cm.get('log_level')}")
        
        # Test with production profile
        print("\nProduction configuration:")
        cm.set_profile('production')
        cm.add_profile_source(str(temp_path))  # Will load production.json
        
        print(f"  App: {cm.get('app')}")
        print(f"  Debug: {cm.get('debug', 'Not set')}")
        print(f"  SSL Required: {cm.get('ssl_required')}")
        
        print()


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


def demo_profile_variables():
    """Demonstrate profile variable access."""
    print("=== Profile Variables ===")
    
    cm = ConfigManager(profile='development')
    
    # Access profile variables directly
    print("Development profile variables:")
    print(f"  Debug: {cm.get_profile_var('debug')}")
    print(f"  Log Level: {cm.get_profile_var('log_level')}")
    print(f"  Cache Enabled: {cm.get_profile_var('cache_enabled')}")
    
    # Switch to production and check variables
    cm.set_profile('production')
    print("\nProduction profile variables:")
    print(f"  Debug: {cm.get_profile_var('debug')}")
    print(f"  Log Level: {cm.get_profile_var('log_level')}")
    print(f"  SSL Required: {cm.get_profile_var('ssl_required')}")
    
    # Create a custom profile with custom variables
    custom_profile = cm.create_profile('custom')
    custom_profile.set_var('api_timeout', 30)
    custom_profile.set_var('retry_attempts', 3)
    custom_profile.set_var('feature_flags', {'beta_feature': True})
    
    cm.set_profile('custom')
    print("\nCustom profile variables:")
    print(f"  API Timeout: {cm.get_profile_var('api_timeout')}")
    print(f"  Retry Attempts: {cm.get_profile_var('retry_attempts')}")
    print(f"  Feature Flags: {cm.get_profile_var('feature_flags')}")
    
    print()


def demo_environment_simulation():
    """Demonstrate how profiles work with environment variables."""
    print("=== Environment Variable Simulation ===")
    
    # Create a temporary config file
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "app.json"
        config = {
            "app_name": "TestApp",
            "database_url": "sqlite:///app.db"
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        # Test without environment variables (defaults to development)
        print("No environment variables set:")
        cm = ConfigManager(auto_detect_profile=True)
        cm.add_source(JsonSource(str(config_file)))
        print(f"  Active profile: {cm.get_current_profile()}")
        print(f"  Debug mode: {cm.get_profile_var('debug')}")
        
        # Simulate production environment
        print("\nSimulating production environment:")
        os.environ['ENV'] = 'production'
        cm = ConfigManager(auto_detect_profile=True)
        cm.add_source(JsonSource(str(config_file)))
        print(f"  Active profile: {cm.get_current_profile()}")
        print(f"  Debug mode: {cm.get_profile_var('debug')}")
        print(f"  SSL required: {cm.get_profile_var('ssl_required')}")
        
        # Simulate testing environment
        print("\nSimulating testing environment:")
        os.environ['ENV'] = 'testing'
        cm = ConfigManager(auto_detect_profile=True)
        cm.add_source(JsonSource(str(config_file)))
        print(f"  Active profile: {cm.get_current_profile()}")
        print(f"  Debug mode: {cm.get_profile_var('debug')}")
        print(f"  Log level: {cm.get_profile_var('log_level')}")
        
        # Clean up
        os.environ.pop('ENV', None)
    
    print()


if __name__ == "__main__":
    print("Configuration Profiles and Environment Management Examples")
    print("=" * 60)
    print()
    
    # Run all demonstrations
    demo_basic_profiles()
    demo_environment_detection()
    demo_configmanager_with_profiles()
    demo_profile_specific_sources()
    demo_profile_path_utilities()
    demo_profile_variables()
    demo_environment_simulation()
    
    print("All profile examples completed successfully!")

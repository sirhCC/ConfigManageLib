"""
Example demonstrating Configuration File Watching & Auto-Reload functionality.

This example shows how to enable automatic reloading of configuration
when files change, enabling zero-downtime configuration updates.
"""

import json
import time
import tempfile
import os
from config_manager import ConfigManager
from config_manager.sources import JsonSource, YamlSource, TomlSource, IniSource
from config_manager.schema import Schema, String, Integer, Boolean
from config_manager.validation import RangeValidator, ChoicesValidator


def basic_auto_reload_example():
    """Demonstrate basic auto-reload functionality."""
    print("=== Basic Auto-Reload Example ===")
    
    # Create a temporary config file
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'app_config.json')
    
    # Initial configuration
    initial_config = {
        "app": {
            "name": "AutoReloadApp",
            "version": "1.0.0",
            "debug": False,
            "max_connections": 100
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "timeout": 30
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(initial_config, f, indent=2)
    
    try:
        # Create ConfigManager with auto-reload enabled
        config = ConfigManager(auto_reload=True, reload_interval=0.5)
        config.add_source(JsonSource(config_file))
        
        print(f"📁 Watching config file: {config_file}")
        print(f"🔄 Auto-reload enabled with {config._reload_interval}s interval")
        print()
        
        # Display initial configuration
        print("📊 Initial Configuration:")
        print(f"  App: {config.get('app.name')} v{config.get('app.version')}")
        print(f"  Debug: {config.get_bool('app.debug')}")
        print(f"  Max Connections: {config.get_int('app.max_connections')}")
        print(f"  Database: {config.get('database.host')}:{config.get_int('database.port')}")
        print()
        
        # Simulate configuration change
        print("🔧 Modifying configuration file...")
        modified_config = initial_config.copy()
        modified_config['app']['debug'] = True
        modified_config['app']['max_connections'] = 200
        modified_config['database']['timeout'] = 60
        
        with open(config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        print("⏳ Waiting for auto-reload to detect changes...")
        time.sleep(1.0)  # Wait for auto-reload
        
        # Display updated configuration
        print("📊 Updated Configuration (after auto-reload):")
        print(f"  App: {config.get('app.name')} v{config.get('app.version')}")
        print(f"  Debug: {config.get_bool('app.debug')}")  # Should be True now
        print(f"  Max Connections: {config.get_int('app.max_connections')}")  # Should be 200 now
        print(f"  Database timeout: {config.get_int('database.timeout')}s")  # Should be 60 now
        print()
        
        # Clean up
        config.stop_watching()
        
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def auto_reload_with_callbacks_example():
    """Demonstrate auto-reload with callback functions."""
    print("=== Auto-Reload with Callbacks Example ===")
    
    # Create temporary config files
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'service_config.json')
    
    # Initial configuration
    service_config = {
        "service": {
            "name": "WebService",
            "port": 8080,
            "workers": 4,
            "timeout": 30
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(message)s"
        },
        "features": {
            "rate_limiting": True,
            "caching": False,
            "monitoring": True
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(service_config, f, indent=2)
    
    try:
        # Track reload events
        reload_count = [0]
        config_changes = []
        
        def on_config_reload():
            """Callback function called when configuration reloads."""
            reload_count[0] += 1
            timestamp = time.strftime("%H:%M:%S")
            config_changes.append(f"[{timestamp}] Configuration reloaded (#{reload_count[0]})")
            print(f"🔄 [{timestamp}] Configuration automatically reloaded!")
        
        # Create ConfigManager with callback
        config = ConfigManager(auto_reload=True, reload_interval=0.3)
        config.add_source(JsonSource(config_file))
        
        # Register callback
        config.on_reload(on_config_reload)
        
        print(f"📁 Watching: {config_file}")
        print("📞 Registered reload callback function")
        print()
        
        # Display initial state
        print("📊 Initial Service Configuration:")
        print(f"  Service: {config.get('service.name')} on port {config.get_int('service.port')}")
        print(f"  Workers: {config.get_int('service.workers')}")
        print(f"  Logging: {config.get('logging.level')}")
        print(f"  Features:")
        print(f"    - Rate Limiting: {config.get_bool('features.rate_limiting')}")
        print(f"    - Caching: {config.get_bool('features.caching')}")
        print(f"    - Monitoring: {config.get_bool('features.monitoring')}")
        print()
        
        # Simulate multiple configuration changes
        changes = [
            {
                "description": "Scale up workers and enable caching",
                "changes": {
                    "service.workers": 8,
                    "features.caching": True
                }
            },
            {
                "description": "Change log level to DEBUG",
                "changes": {
                    "logging.level": "DEBUG"
                }
            },
            {
                "description": "Disable rate limiting and increase timeout",
                "changes": {
                    "features.rate_limiting": False,
                    "service.timeout": 60
                }
            }
        ]
        
        for i, change in enumerate(changes, 1):
            print(f"🔧 Change #{i}: {change['description']}")
            
            # Apply changes to config
            updated_config = service_config.copy()
            for key, value in change['changes'].items():
                keys = key.split('.')
                current = updated_config
                for k in keys[:-1]:
                    current = current[k]
                current[keys[-1]] = value
            
            # Write updated config
            with open(config_file, 'w') as f:
                json.dump(updated_config, f, indent=2)
            
            # Wait for auto-reload
            print("⏳ Waiting for auto-reload...")
            time.sleep(0.7)
            
            # Show updated values
            print("📊 Updated values:")
            for key in change['changes'].keys():
                if key.endswith('.caching') or key.endswith('.rate_limiting') or key.endswith('.monitoring'):
                    value = config.get_bool(key)
                elif key.endswith('.workers') or key.endswith('.port') or key.endswith('.timeout'):
                    value = config.get_int(key)
                else:
                    value = config.get(key)
                print(f"    {key}: {value}")
            print()
        
        # Display callback history
        print("📞 Callback History:")
        for change in config_changes:
            print(f"  {change}")
        print(f"Total reloads detected: {reload_count[0]}")
        print()
        
        # Clean up
        config.stop_watching()
        
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def multi_source_auto_reload_example():
    """Demonstrate auto-reload with multiple configuration sources."""
    print("=== Multi-Source Auto-Reload Example ===")
    
    # Create temporary config files
    temp_dir = tempfile.mkdtemp()
    base_config_file = os.path.join(temp_dir, 'base.json')
    env_config_file = os.path.join(temp_dir, 'environment.json')
    
    # Base configuration
    base_config = {
        "app": {
            "name": "MultiSourceApp",
            "version": "1.0.0"
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "pool_size": 10
        },
        "cache": {
            "enabled": True,
            "ttl": 3600
        }
    }
    
    # Environment-specific overrides
    env_config = {
        "app": {
            "debug": True  # Add debug flag for development
        },
        "database": {
            "host": "dev-db.internal",  # Override for development
            "pool_size": 5  # Smaller pool for dev
        }
    }
    
    with open(base_config_file, 'w') as f:
        json.dump(base_config, f, indent=2)
    
    with open(env_config_file, 'w') as f:
        json.dump(env_config, f, indent=2)
    
    try:
        # Track which files triggered reloads
        reload_events = []
        
        def track_reload():
            timestamp = time.strftime("%H:%M:%S")
            reload_events.append(f"[{timestamp}] Multi-source configuration reloaded")
            print(f"🔄 [{timestamp}] Multi-source auto-reload triggered!")
        
        # Create ConfigManager with multiple sources
        config = ConfigManager(auto_reload=True, reload_interval=0.4)
        config.add_source(JsonSource(base_config_file))      # Base configuration
        config.add_source(JsonSource(env_config_file))       # Environment overrides
        
        config.on_reload(track_reload)
        
        print(f"📁 Watching multiple files:")
        print(f"  Base: {base_config_file}")
        print(f"  Environment: {env_config_file}")
        print()
        
        # Display initial merged configuration
        print("📊 Initial Merged Configuration:")
        print(f"  App: {config.get('app.name')} v{config.get('app.version')}")
        print(f"  Debug: {config.get_bool('app.debug', False)}")
        print(f"  Database: {config.get('database.host')}:{config.get_int('database.port')}")
        print(f"  Pool Size: {config.get_int('database.pool_size')}")
        print(f"  Cache: {'Enabled' if config.get_bool('cache.enabled') else 'Disabled'} (TTL: {config.get_int('cache.ttl')}s)")
        print()
        
        # Modify base configuration
        print("🔧 Modifying base configuration...")
        modified_base = base_config.copy()
        modified_base['app']['version'] = '2.0.0'
        modified_base['cache']['ttl'] = 7200  # 2 hours
        
        with open(base_config_file, 'w') as f:
            json.dump(modified_base, f, indent=2)
        
        time.sleep(0.8)  # Wait for auto-reload
        
        print("📊 After base config change:")
        print(f"  Version: {config.get('app.version')}")  # Should be 2.0.0
        print(f"  Cache TTL: {config.get_int('cache.ttl')}s")  # Should be 7200
        print(f"  Host: {config.get('database.host')}")  # Should still be overridden
        print()
        
        # Modify environment configuration
        print("🔧 Modifying environment configuration...")
        modified_env = env_config.copy()
        modified_env['app']['debug'] = False  # Disable debug
        modified_env['database']['pool_size'] = 15  # Increase pool
        modified_env['new_feature'] = {'enabled': True}  # Add new feature
        
        with open(env_config_file, 'w') as f:
            json.dump(modified_env, f, indent=2)
        
        time.sleep(0.8)  # Wait for auto-reload
        
        print("📊 After environment config change:")
        print(f"  Debug: {config.get_bool('app.debug')}")  # Should be False now
        print(f"  Pool Size: {config.get_int('database.pool_size')}")  # Should be 15
        print(f"  New Feature: {config.get_bool('new_feature.enabled', False)}")  # Should be True
        print()
        
        # Display reload events
        print("📞 Reload Events:")
        for event in reload_events:
            print(f"  {event}")
        print(f"Total multi-source reloads: {len(reload_events)}")
        print()
        
        # Clean up
        config.stop_watching()
        
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def auto_reload_with_schema_validation_example():
    """Demonstrate auto-reload with schema validation."""
    print("=== Auto-Reload with Schema Validation Example ===")
    
    # Create temporary config file
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'validated_config.json')
    
    # Define schema for validation
    schema = Schema({
        "server": Schema({
            "port": Integer(
                default=8080,
                validators=[RangeValidator(min_value=1024, max_value=65535)]
            ),
            "host": String(default="localhost"),
            "workers": Integer(
                default=1,
                validators=[RangeValidator(min_value=1, max_value=32)]
            )
        }),
        "database": Schema({
            "host": String(required=True),
            "port": Integer(default=5432),
            "name": String(required=True)
        }),
        "logging": Schema({
            "level": String(
                default="INFO",
                validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]
            )
        })
    })
    
    # Valid initial configuration
    valid_config = {
        "server": {
            "port": 9000,
            "host": "0.0.0.0",
            "workers": 4
        },
        "database": {
            "host": "db.example.com",
            "port": 5432,
            "name": "production_db"
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(valid_config, f, indent=2)
    
    try:
        # Track validation results
        validation_results = []
        
        def on_reload_with_validation():
            """Callback that validates configuration after reload."""
            timestamp = time.strftime("%H:%M:%S")
            if config.is_valid():
                validation_results.append(f"[{timestamp}] ✅ Configuration reloaded and validated successfully")
                print(f"✅ [{timestamp}] Configuration reloaded and is valid!")
            else:
                errors = config.get_validation_errors()
                validation_results.append(f"[{timestamp}] ❌ Configuration reloaded but validation failed: {errors}")
                print(f"❌ [{timestamp}] Configuration reloaded but validation failed!")
                for error in errors:
                    print(f"    Error: {error}")
        
        # Create ConfigManager with schema validation
        config = ConfigManager(schema=schema, auto_reload=True, reload_interval=0.4)
        config.add_source(JsonSource(config_file))
        
        config.on_reload(on_reload_with_validation)
        
        print(f"📁 Watching: {config_file}")
        print("✅ Schema validation enabled")
        print()
        
        # Display initial valid configuration
        print("📊 Initial Valid Configuration:")
        if config.is_valid():
            validated = config.validate()
            print(f"  Server: {validated['server']['host']}:{validated['server']['port']} ({validated['server']['workers']} workers)")
            print(f"  Database: {validated['database']['name']} on {validated['database']['host']}")
            print(f"  Logging: {validated['logging']['level']}")
        print()
        
        # Test 1: Valid configuration change
        print("🔧 Test 1: Making valid configuration change...")
        valid_update = valid_config.copy()
        valid_update['server']['port'] = 8443
        valid_update['server']['workers'] = 8
        valid_update['logging']['level'] = 'DEBUG'
        
        with open(config_file, 'w') as f:
            json.dump(valid_update, f, indent=2)
        
        time.sleep(0.8)
        print()
        
        # Test 2: Invalid configuration change
        print("🔧 Test 2: Making invalid configuration change...")
        invalid_update = valid_config.copy()
        invalid_update['server']['port'] = 80  # Invalid: too low
        invalid_update['server']['workers'] = 50  # Invalid: too high
        invalid_update['logging']['level'] = 'INVALID'  # Invalid: not in choices
        
        with open(config_file, 'w') as f:
            json.dump(invalid_update, f, indent=2)
        
        time.sleep(0.8)
        print()
        
        # Test 3: Fix the configuration
        print("🔧 Test 3: Fixing the configuration...")
        fixed_config = {
            "server": {
                "port": 8080,
                "host": "localhost",
                "workers": 2
            },
            "database": {
                "host": "fixed-db.example.com",
                "port": 5432,
                "name": "fixed_db"
            },
            "logging": {
                "level": "WARNING"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(fixed_config, f, indent=2)
        
        time.sleep(0.8)
        print()
        
        # Display validation history
        print("📊 Validation History:")
        for result in validation_results:
            print(f"  {result}")
        print()
        
        # Clean up
        config.stop_watching()
        
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def production_like_auto_reload_example():
    """Demonstrate production-like auto-reload scenario."""
    print("=== Production-Like Auto-Reload Scenario ===")
    
    # Create temporary config directory structure
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, 'config')
    os.makedirs(config_dir)
    
    app_config_file = os.path.join(config_dir, 'app.json')
    feature_flags_file = os.path.join(config_dir, 'features.json')
    
    # Application configuration
    app_config = {
        "service": {
            "name": "ProductionService",
            "version": "3.2.1",
            "port": 8080,
            "health_check_interval": 30
        },
        "database": {
            "primary": {
                "host": "primary-db.prod.internal",
                "port": 5432,
                "pool_size": 20
            },
            "replica": {
                "host": "replica-db.prod.internal",
                "port": 5432,
                "pool_size": 10
            }
        },
        "security": {
            "jwt_secret_rotation_interval": 86400,
            "rate_limit_per_minute": 1000
        }
    }
    
    # Feature flags (frequently updated)
    feature_flags = {
        "features": {
            "new_payment_processor": False,
            "advanced_analytics": True,
            "maintenance_mode": False,
            "beta_ui": False,
            "circuit_breaker": True
        },
        "rollout": {
            "new_payment_processor": 0,    # 0% rollout
            "advanced_analytics": 100,     # 100% rollout
            "beta_ui": 5                   # 5% rollout
        }
    }
    
    with open(app_config_file, 'w') as f:
        json.dump(app_config, f, indent=2)
    
    with open(feature_flags_file, 'w') as f:
        json.dump(feature_flags, f, indent=2)
    
    try:
        # Production-like reload monitoring
        reload_log = []
        
        def production_reload_handler():
            """Production-style reload handler with logging."""
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            reload_log.append({
                "timestamp": timestamp,
                "service_port": config.get_int('service.port'),
                "maintenance_mode": config.get_bool('features.maintenance_mode'),
                "primary_db_pool": config.get_int('database.primary.pool_size'),
                "new_payment_rollout": config.get_int('rollout.new_payment_processor', 0)
            })
            
            # Log important configuration state
            print(f"🔄 [{timestamp}] Production config reloaded:")
            print(f"  Service Port: {config.get_int('service.port')}")
            print(f"  Maintenance Mode: {config.get_bool('features.maintenance_mode')}")
            print(f"  Circuit Breaker: {config.get_bool('features.circuit_breaker')}")
            print(f"  Payment Processor Rollout: {config.get_int('rollout.new_payment_processor', 0)}%")
            
            # Simulate alerting for critical changes
            if config.get_bool('features.maintenance_mode'):
                print("  🚨 ALERT: Maintenance mode enabled!")
            
            rollout_percentage = config.get_int('rollout.new_payment_processor', 0) or 0
            if rollout_percentage > 0:
                print(f"  💳 NOTICE: New payment processor rollout at {rollout_percentage}%")
        
        # Create production-style ConfigManager
        config = ConfigManager(auto_reload=True, reload_interval=0.5)
        config.add_source(JsonSource(app_config_file))        # Core application config
        config.add_source(JsonSource(feature_flags_file))     # Feature flags (higher precedence)
        
        config.on_reload(production_reload_handler)
        
        print(f"📁 Production Config Watching:")
        print(f"  App Config: {app_config_file}")
        print(f"  Feature Flags: {feature_flags_file}")
        print("🔄 Auto-reload enabled for zero-downtime updates")
        print()
        
        # Display initial production state
        print("📊 Initial Production Configuration:")
        print(f"  Service: {config.get('service.name')} v{config.get('service.version')} on port {config.get_int('service.port')}")
        print(f"  Primary DB Pool: {config.get_int('database.primary.pool_size')}")
        print(f"  Replica DB Pool: {config.get_int('database.replica.pool_size')}")
        print(f"  Feature Flags:")
        print(f"    - New Payment Processor: {config.get_bool('features.new_payment_processor')} ({config.get_int('rollout.new_payment_processor', 0)}%)")
        print(f"    - Advanced Analytics: {config.get_bool('features.advanced_analytics')}")
        print(f"    - Maintenance Mode: {config.get_bool('features.maintenance_mode')}")
        print(f"    - Beta UI: {config.get_bool('features.beta_ui')} ({config.get_int('rollout.beta_ui', 0)}%)")
        print()
        
        # Simulate production configuration changes
        production_changes = [
            {
                "description": "Scale up database connections for peak traffic",
                "file": app_config_file,
                "config": app_config.copy(),
                "changes": {"database.primary.pool_size": 40, "database.replica.pool_size": 20}
            },
            {
                "description": "Begin gradual rollout of new payment processor",
                "file": feature_flags_file,
                "config": feature_flags.copy(),
                "changes": {"features.new_payment_processor": True, "rollout.new_payment_processor": 10}
            },
            {
                "description": "Increase payment processor rollout",
                "file": feature_flags_file,
                "config": feature_flags.copy(),
                "changes": {"rollout.new_payment_processor": 25}
            },
            {
                "description": "Enable maintenance mode for critical update",
                "file": feature_flags_file,
                "config": feature_flags.copy(),
                "changes": {"features.maintenance_mode": True}
            },
            {
                "description": "Complete maintenance and disable maintenance mode",
                "file": feature_flags_file,
                "config": feature_flags.copy(),
                "changes": {"features.maintenance_mode": False}
            }
        ]
        
        for i, change in enumerate(production_changes, 1):
            print(f"🔧 Production Change #{i}: {change['description']}")
            
            # Apply changes
            updated_config = change['config']
            for key, value in change['changes'].items():
                keys = key.split('.')
                current = updated_config
                for k in keys[:-1]:
                    current = current[k]
                current[keys[-1]] = value
            
            # Write updated config
            with open(change['file'], 'w') as f:
                json.dump(updated_config, f, indent=2)
            
            # Wait for auto-reload
            time.sleep(1.0)
            print()
        
        # Display production reload history
        print("📊 Production Reload History:")
        for i, log_entry in enumerate(reload_log, 1):
            print(f"  #{i} [{log_entry['timestamp']}]:")
            print(f"      Port: {log_entry['service_port']}")
            print(f"      Maintenance: {log_entry['maintenance_mode']}")
            print(f"      Primary DB Pool: {log_entry['primary_db_pool']}")
            print(f"      Payment Rollout: {log_entry['new_payment_rollout']}%")
        print()
        
        # Clean up
        config.stop_watching()
        
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("🚀 ConfigManager Auto-Reload Examples")
    print("=" * 60)
    print()
    
    basic_auto_reload_example()
    auto_reload_with_callbacks_example()
    multi_source_auto_reload_example()
    auto_reload_with_schema_validation_example()
    production_like_auto_reload_example()
    
    print("🎉 Auto-reload examples completed!")
    print()
    print("Key Features Demonstrated:")
    print("✓ File watching and automatic reloading")
    print("✓ Polling fallback when watchdog is unavailable")
    print("✓ Reload callback functions")
    print("✓ Thread-safe configuration access")
    print("✓ Multi-source auto-reload")
    print("✓ Schema validation with auto-reload")
    print("✓ Production-like zero-downtime updates")
    print("✓ Feature flag and configuration hot-swapping")
    print("✓ Graceful cleanup and resource management")
    print()
    print("💡 Usage Tips:")
    print("• Set reload_interval based on your needs (default: 1.0s)")
    print("• Use callbacks for application state updates")
    print("• Install 'watchdog' package for better file watching performance")
    print("• Always call stop_watching() or use context managers for cleanup")
    print("• Consider schema validation for production safety")

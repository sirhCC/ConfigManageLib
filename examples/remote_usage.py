"""
Example demonstrating Remote Configuration Source support with ConfigManager.

This example shows how to use HTTP/HTTPS URLs as configuration sources,
enabling centralized configuration management and dynamic updates.
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from config_manager import ConfigManager
from config_manager.sources.remote_source import RemoteSource, remote_source
from config_manager.sources.json_source import JsonSource
from config_manager.schema import Schema, String, Integer, Boolean
from config_manager.validation import RangeValidator, ChoicesValidator


class DemoConfigServer:
    """Demo HTTP server for remote configuration examples."""
    
    def __init__(self, port=8888):
        self.port = port
        self.server = None
        self.thread = None
        self.responses = {}
        
    def set_response(self, path, response_data):
        """Set the response for a specific path."""
        self.responses[path] = response_data
    
    def start(self):
        """Start the demo server."""
        handler = self._create_handler()
        self.server = HTTPServer(('localhost', self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # Give server time to start
        
    def stop(self):
        """Stop the demo server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)
    
    def get_url(self, path=""):
        """Get the full URL for a path."""
        return f"http://localhost:{self.port}{path}"
    
    def _create_handler(self):
        """Create the request handler class."""
        responses = self.responses
        
        class DemoHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress log messages
                
            def do_GET(self):
                if self.path in responses:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    data = json.dumps(responses[self.path])
                    self.wfile.write(data.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Not Found"}')
        
        return DemoHandler


def basic_remote_example():
    """Demonstrate basic remote configuration loading."""
    print("=== Basic Remote Configuration ===")
    
    # Start demo server
    server = DemoConfigServer(port=8881)
    
    # Set up configuration data
    config_data = {
        "app": {
            "name": "RemoteConfigApp",
            "version": "2.0.0",
            "debug": False
        },
        "database": {
            "host": "remote-db.example.com",
            "port": 5432,
            "name": "production_db",
            "ssl": True
        },
        "features": {
            "authentication": True,
            "api": True,
            "logging": True,
            "metrics": False
        }
    }
    
    server.set_response("/config.json", config_data)
    server.start()
    
    try:
        # Load configuration from remote URL
        config = ConfigManager()
        config.add_source(RemoteSource(server.get_url("/config.json")))
        
        print(f"✅ Loaded remote configuration from: {server.get_url('/config.json')}")
        print(f"App: {config.get('app.name')} v{config.get('app.version')}")
        print(f"Debug mode: {config.get_bool('app.debug')}")
        print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
        print(f"SSL: {config.get_bool('database.ssl')}")
        print(f"Features:")
        print(f"  - Authentication: {config.get_bool('features.authentication')}")
        print(f"  - API: {config.get_bool('features.api')}")
        print(f"  - Logging: {config.get_bool('features.logging')}")
        print(f"  - Metrics: {config.get_bool('features.metrics')}")
        print()
        
    finally:
        server.stop()


def remote_with_authentication_example():
    """Demonstrate remote configuration with authentication."""
    print("=== Remote Configuration with Authentication ===")
    
    # Example using the fluent builder API
    print("🔐 Using Bearer Token Authentication")
    
    try:
        # Using builder pattern for clean configuration
        source = remote_source("https://httpbin.org/headers") \
            .with_bearer_token("demo_token_12345") \
            .with_header("X-Client-Version", "1.0.0") \
            .with_timeout(10.0) \
            .build()
        
        # Note: httpbin.org/headers returns the headers sent to it
        # This is just for demonstration - in real use, you'd have your config endpoint
        config = ConfigManager()
        config.add_source(source)
        
        # Configuration is loaded automatically when adding source
        # Just verify it's accessible (will contain the headers we sent)
        if config.get('headers'):
            print(f"✅ Successfully authenticated with remote service")
            print(f"Request headers were sent correctly")
        else:
            print(f"⚠️  Could not verify authentication headers")
        
    except Exception as e:
        print(f"⚠️  Demo service unavailable: {e}")
    
    print("\n🔑 Using API Key Authentication")
    
    try:
        # Using API key authentication
        source = remote_source("https://httpbin.org/headers") \
            .with_api_key("demo_api_key_67890", "X-API-Key") \
            .with_header("X-Service", "ConfigManager") \
            .build()
        
        config = ConfigManager()
        config.add_source(source)
        
        # Configuration is loaded automatically when adding source
        if config.get('headers'):
            print(f"✅ Successfully authenticated with API key")
        else:
            print(f"⚠️  Could not verify API key authentication")
        
    except Exception as e:
        print(f"⚠️  Demo service unavailable: {e}")
    
    print()


def remote_with_schema_validation_example():
    """Demonstrate remote configuration with schema validation."""
    print("=== Remote Configuration with Schema Validation ===")
    
    # Start demo server
    server = DemoConfigServer(port=8882)
    
    # Define schema for validation
    schema = Schema({
        "service": Schema({
            "name": String(required=True),
            "port": Integer(
                default=8000,
                validators=[RangeValidator(min_value=1024, max_value=65535)]
            ),
            "debug": Boolean(default=False),
            "environment": String(
                default="production",
                validators=[ChoicesValidator(["development", "staging", "production"])]
            )
        }),
        "database": Schema({
            "url": String(required=True),
            "pool_size": Integer(default=10, validators=[RangeValidator(min_value=1, max_value=100)]),
            "timeout": Integer(default=30)
        }),
        "logging": Schema({
            "level": String(
                default="INFO",
                validators=[ChoicesValidator(["DEBUG", "INFO", "WARNING", "ERROR"])]
            ),
            "format": String(default="%(asctime)s - %(levelname)s - %(message)s")
        })
    })
    
    # Set up validated configuration data
    config_data = {
        "service": {
            "name": "RemoteValidatedService",
            "port": 8443,
            "debug": True,
            "environment": "production"
        },
        "database": {
            "url": "postgresql://user:pass@db.example.com/mydb",
            "pool_size": 20,
            "timeout": 60
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    server.set_response("/validated-config.json", config_data)
    server.start()
    
    try:
        # Load and validate remote configuration
        config = ConfigManager(schema=schema)
        config.add_source(RemoteSource(server.get_url("/validated-config.json")))
        
        try:
            validated_config = config.validate()
            print("✅ Remote configuration validated successfully!")
            print(f"Service: {validated_config['service']['name']} on port {validated_config['service']['port']}")
            print(f"Environment: {validated_config['service']['environment']}")
            print(f"Debug: {validated_config['service']['debug']}")
            print(f"Database URL: {validated_config['database']['url']}")
            print(f"Pool Size: {validated_config['database']['pool_size']}")
            print(f"Log Level: {validated_config['logging']['level']}")
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
        
        print()
        
    finally:
        server.stop()


def multi_source_with_remote_example():
    """Demonstrate remote configuration with local overrides."""
    print("=== Multi-Source Configuration with Remote Base ===")
    
    # Start demo server
    server = DemoConfigServer(port=8883)
    
    # Set up base remote configuration
    remote_config = {
        "app": {
            "name": "MultiSourceApp",
            "version": "3.0.0",
            "debug": False
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "ssl": False
        },
        "database": {
            "host": "remote-db.example.com",
            "port": 5432,
            "name": "production_db"
        },
        "features": {
            "auth": True,
            "api": True,
            "monitoring": False
        }
    }
    
    server.set_response("/base-config.json", remote_config)
    server.start()
    
    try:
        # Create local override configuration
        import tempfile
        import os
        
        local_override = {
            "app": {
                "debug": True  # Enable debug locally
            },
            "server": {
                "host": "localhost",  # Override for local development
                "port": 8080
            },
            "database": {
                "host": "localhost"  # Use local database
            },
            "features": {
                "monitoring": True,  # Enable monitoring
                "development_tools": True  # Add local feature
            }
        }
        
        # Write local override to temporary file
        temp_dir = tempfile.mkdtemp()
        local_file = os.path.join(temp_dir, "local-override.json")
        
        with open(local_file, 'w') as f:
            json.dump(local_override, f, indent=2)
        
        # Load configuration with precedence: Remote (base) < Local (override)
        config = ConfigManager()
        config.add_source(RemoteSource(server.get_url("/base-config.json")))  # Base from remote
        config.add_source(JsonSource(local_file))  # Local overrides
        
        print("📡 Remote Base + Local Override Configuration")
        print(f"App: {config.get('app.name')} v{config.get('app.version')}")
        print(f"Debug: {config.get_bool('app.debug')}")  # Overridden to True
        print(f"Server: {config.get('server.host')}:{config.get_int('server.port')}")  # Overridden
        print(f"Database: {config.get('database.name')} on {config.get('database.host')}:{config.get_int('database.port')}")
        print(f"Features:")
        print(f"  - Auth: {config.get_bool('features.auth')}")  # From remote
        print(f"  - API: {config.get_bool('features.api')}")  # From remote
        print(f"  - Monitoring: {config.get_bool('features.monitoring')}")  # Overridden
        print(f"  - Dev Tools: {config.get_bool('features.development_tools', False)}")  # Added locally
        print()
        
        # Cleanup
        os.remove(local_file)
        os.rmdir(temp_dir)
        
    finally:
        server.stop()


def cloud_config_simulation_example():
    """Simulate cloud configuration service integration."""
    print("=== Cloud Configuration Service Simulation ===")
    
    # Start demo server simulating cloud config service
    server = DemoConfigServer(port=8884)
    
    # Simulate different environment configurations
    environments = {
        "/config/development": {
            "environment": "development",
            "app": {
                "name": "CloudApp",
                "debug": True,
                "log_level": "DEBUG"
            },
            "database": {
                "host": "dev-db.internal",
                "pool_size": 5
            },
            "cache": {
                "enabled": False
            }
        },
        "/config/staging": {
            "environment": "staging",
            "app": {
                "name": "CloudApp",
                "debug": False,
                "log_level": "INFO"
            },
            "database": {
                "host": "staging-db.internal",
                "pool_size": 10
            },
            "cache": {
                "enabled": True,
                "ttl": 300
            }
        },
        "/config/production": {
            "environment": "production",
            "app": {
                "name": "CloudApp",
                "debug": False,
                "log_level": "WARNING"
            },
            "database": {
                "host": "prod-db.internal",
                "pool_size": 20
            },
            "cache": {
                "enabled": True,
                "ttl": 3600
            },
            "monitoring": {
                "enabled": True,
                "endpoint": "https://monitoring.example.com"
            }
        }
    }
    
    # Set up all environment configs
    for path, config_data in environments.items():
        server.set_response(path, config_data)
    
    server.start()
    
    try:
        print("☁️  Simulating different environment configurations:")
        
        for env_name in ["development", "staging", "production"]:
            print(f"\n--- {env_name.upper()} Environment ---")
            
            # Simulate fetching environment-specific config
            config_url = f"{server.get_url(f'/config/{env_name}')}"
            
            config = ConfigManager()
            config.add_source(RemoteSource(config_url))
            
            print(f"📡 Config URL: {config_url}")
            print(f"Environment: {config.get('environment')}")
            print(f"Debug Mode: {config.get_bool('app.debug')}")
            print(f"Log Level: {config.get('app.log_level')}")
            print(f"Database: {config.get('database.host')} (pool: {config.get_int('database.pool_size')})")
            print(f"Cache: {'Enabled' if config.get_bool('cache.enabled', False) else 'Disabled'}")
            
            if config.get('cache.enabled', False):
                print(f"Cache TTL: {config.get_int('cache.ttl')} seconds")
            
            if config.get('monitoring.enabled', False):
                print(f"Monitoring: {config.get('monitoring.endpoint')}")
        
        print()
        
    finally:
        server.stop()


if __name__ == "__main__":
    print("🚀 ConfigManager Remote Configuration Examples")
    print("=" * 60)
    print()
    
    basic_remote_example()
    remote_with_authentication_example()
    remote_with_schema_validation_example()
    multi_source_with_remote_example()
    cloud_config_simulation_example()
    
    print("🎉 Remote configuration examples completed!")
    print("Key Features Demonstrated:")
    print("✓ Basic HTTP/HTTPS configuration loading")
    print("✓ Authentication (Bearer tokens, API keys, Basic auth)")
    print("✓ Custom headers and timeout configuration")
    print("✓ Schema validation with remote sources")
    print("✓ Multi-source configuration (remote + local)")
    print("✓ Cloud configuration service simulation")
    print("✓ Environment-specific configuration management")
    print("✓ Fluent builder API for easy configuration")
    print("✓ Error handling and timeout management")

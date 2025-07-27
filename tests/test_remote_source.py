"""
Tests for the RemoteSource class.
"""

import unittest
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config_manager.sources.remote_source import RemoteSource, RemoteSourceBuilder, remote_source
from config_manager import ConfigManager


class MockConfigServer:
    """Mock HTTP server for testing remote configuration."""
    
    def __init__(self, port=0):
        self.port = port
        self.server = None
        self.thread = None
        self.responses = {}
        self.requests = []
        
    def set_response(self, path, response_data, status_code=200, headers=None):
        """Set the response for a specific path."""
        self.responses[path] = {
            'data': response_data,
            'status': status_code,
            'headers': headers or {}
        }
    
    def start(self):
        """Start the mock server."""
        handler = self._create_handler()
        self.server = HTTPServer(('localhost', self.port), handler)
        self.port = self.server.server_port  # Get actual port if 0 was specified
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # Give server time to start
        
    def stop(self):
        """Stop the mock server."""
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
        requests = self.requests
        
        class MockHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress log messages
                
            def do_GET(self):
                # Record the request
                requests.append({
                    'method': 'GET',
                    'path': self.path,
                    'headers': dict(self.headers)
                })
                
                # Find response
                if self.path in responses:
                    response = responses[self.path]
                    self.send_response(response['status'])
                    
                    # Add custom headers
                    for header_name, header_value in response['headers'].items():
                        self.send_header(header_name, header_value)
                    
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    
                    if isinstance(response['data'], dict):
                        data = json.dumps(response['data'])
                    else:
                        data = response['data']
                    
                    self.wfile.write(data.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Not Found')
        
        return MockHandler


class TestRemoteSource(unittest.TestCase):
    """Test the RemoteSource class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = MockConfigServer()
        self.server.start()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.server.stop()

    def test_remote_source_basic_load(self):
        """Test basic remote configuration loading."""
        # Set up server response
        config_data = {
            "app": {
                "name": "RemoteApp",
                "version": "1.0.0"
            },
            "database": {
                "host": "remote-db.example.com",
                "port": 5432
            }
        }
        self.server.set_response("/config.json", config_data)
        
        # Load configuration
        source = RemoteSource(self.server.get_url("/config.json"))
        data = source.load()
        
        self.assertEqual(data["app"]["name"], "RemoteApp")
        self.assertEqual(data["app"]["version"], "1.0.0")
        self.assertEqual(data["database"]["host"], "remote-db.example.com")
        self.assertEqual(data["database"]["port"], 5432)

    def test_remote_source_with_headers(self):
        """Test remote source with custom headers."""
        config_data = {"test": "value"}
        self.server.set_response("/config.json", config_data)
        
        headers = {
            "X-Custom-Header": "custom-value",
            "X-Client-ID": "test-client"
        }
        
        source = RemoteSource(
            self.server.get_url("/config.json"),
            headers=headers
        )
        data = source.load()
        
        # Check that headers were sent (case-insensitive check)
        requests = self.server.requests
        self.assertEqual(len(requests), 1)
        
        headers = {k.lower(): v for k, v in requests[0]["headers"].items()}
        self.assertEqual(headers["x-custom-header"], "custom-value")
        self.assertEqual(headers["x-client-id"], "test-client")
        self.assertIn("user-agent", headers)

    def test_remote_source_with_bearer_token(self):
        """Test remote source with Bearer token authentication."""
        config_data = {"authenticated": True}
        self.server.set_response("/secure.json", config_data)
        
        source = RemoteSource(
            self.server.get_url("/secure.json"),
            auth_token="abc123token"
        )
        data = source.load()
        
        # Check that Authorization header was sent (case-insensitive)
        requests = self.server.requests
        self.assertEqual(len(requests), 1)
        headers = {k.lower(): v for k, v in requests[0]["headers"].items()}
        self.assertEqual(headers["authorization"], "Bearer abc123token")
        self.assertEqual(data["authenticated"], True)

    def test_remote_source_with_api_key(self):
        """Test remote source with API key authentication."""
        config_data = {"api_access": True}
        self.server.set_response("/api/config.json", config_data)
        
        source = RemoteSource(
            self.server.get_url("/api/config.json"),
            auth_token="myapikey123",
            auth_header="X-API-Key"
        )
        data = source.load()
        
        # Check that API key header was sent (case-insensitive)
        requests = self.server.requests
        self.assertEqual(len(requests), 1)
        headers = {k.lower(): v for k, v in requests[0]["headers"].items()}
        self.assertEqual(headers["x-api-key"], "myapikey123")
        self.assertEqual(data["api_access"], True)

    def test_remote_source_timeout(self):
        """Test remote source timeout handling."""
        # Use a non-responsive URL that will timeout
        source = RemoteSource(
            "http://10.255.255.1:80/timeout",  # Non-routable address
            timeout=0.1  # Very short timeout
        )
        
        with self.assertRaises(TimeoutError):
            source.load()

    def test_remote_source_http_error(self):
        """Test remote source HTTP error handling."""
        # Set up 404 response
        self.server.set_response("/notfound.json", "Not Found", status_code=404)
        
        source = RemoteSource(self.server.get_url("/notfound.json"))
        
        with self.assertRaises(ConnectionError) as cm:
            source.load()
        
        self.assertIn("HTTP error 404", str(cm.exception))

    def test_remote_source_auth_error(self):
        """Test remote source authentication error handling."""
        # Set up 401 response
        self.server.set_response("/protected.json", "Unauthorized", status_code=401)
        
        source = RemoteSource(self.server.get_url("/protected.json"))
        
        with self.assertRaises(PermissionError) as cm:
            source.load()
        
        self.assertIn("Authentication failed", str(cm.exception))

    def test_remote_source_invalid_json(self):
        """Test remote source with invalid JSON response."""
        # Set up invalid JSON response
        self.server.set_response("/invalid.json", "invalid json content")
        
        source = RemoteSource(self.server.get_url("/invalid.json"))
        
        with self.assertRaises(ValueError) as cm:
            source.load()
        
        self.assertIn("Invalid JSON response", str(cm.exception))

    def test_remote_source_builder_basic(self):
        """Test RemoteSourceBuilder basic functionality."""
        config_data = {"builder": "test"}
        self.server.set_response("/builder.json", config_data)
        
        source = RemoteSourceBuilder(self.server.get_url("/builder.json")).build()
        data = source.load()
        
        self.assertEqual(data["builder"], "test")

    def test_remote_source_builder_fluent_api(self):
        """Test RemoteSourceBuilder fluent API."""
        config_data = {"fluent": "api"}
        self.server.set_response("/fluent.json", config_data)
        
        source = RemoteSourceBuilder(self.server.get_url("/fluent.json")) \
            .with_timeout(60.0) \
            .with_header("X-Test", "value") \
            .with_bearer_token("testtoken") \
            .build()
        
        data = source.load()
        
        # Verify configuration
        self.assertEqual(source.timeout, 60.0)
        self.assertEqual(source.headers["X-Test"], "value")
        self.assertEqual(source.headers["Authorization"], "Bearer testtoken")
        self.assertEqual(data["fluent"], "api")

    def test_remote_source_builder_basic_auth(self):
        """Test RemoteSourceBuilder with Basic authentication."""
        config_data = {"basic_auth": True}
        self.server.set_response("/basic.json", config_data)
        
        source = RemoteSourceBuilder(self.server.get_url("/basic.json")) \
            .with_basic_auth("user", "pass") \
            .build()
        
        data = source.load()
        
        # Check that Basic auth header was sent (case-insensitive)
        requests = self.server.requests
        self.assertEqual(len(requests), 1)
        headers = {k.lower(): v for k, v in requests[0]["headers"].items()}
        auth_header = headers["authorization"]
        self.assertTrue(auth_header.startswith("Basic "))
        
        # Decode and verify credentials
        import base64
        encoded = auth_header[6:]  # Remove "Basic " prefix
        decoded = base64.b64decode(encoded).decode()
        self.assertEqual(decoded, "user:pass")

    def test_remote_source_helper_function(self):
        """Test the remote_source helper function."""
        config_data = {"helper": "function"}
        self.server.set_response("/helper.json", config_data)
        
        source = remote_source(self.server.get_url("/helper.json")) \
            .with_api_key("apikey123", "X-API-Key") \
            .with_timeout(30.0) \
            .build()
        
        data = source.load()
        
        self.assertEqual(data["helper"], "function")
        self.assertEqual(source.auth_header, "X-API-Key")
        self.assertEqual(source.headers["X-API-Key"], "apikey123")

    def test_remote_source_string_representation(self):
        """Test the string representation of RemoteSource."""
        url = "https://config.example.com/app.json"
        source = RemoteSource(url)
        self.assertEqual(str(source), f"RemoteSource('{url}')")

    def test_remote_source_cache_key(self):
        """Test the cache key generation."""
        url = "https://config.example.com/app.json"
        source = RemoteSource(url)
        self.assertEqual(source.get_cache_key(), f"remote:{url}")

    def test_remote_source_is_remote(self):
        """Test the is_remote method."""
        source = RemoteSource("https://config.example.com/app.json")
        self.assertTrue(source.is_remote())

    def test_remote_source_with_config_manager(self):
        """Test RemoteSource integration with ConfigManager."""
        # Set up server response
        config_data = {
            "app": {
                "name": "RemoteConfigApp",
                "debug": True
            },
            "database": {
                "host": "remote-db.test.com",
                "port": 5432,
                "ssl": True
            }
        }
        self.server.set_response("/app-config.json", config_data)
        
        # Load configuration through ConfigManager
        config = ConfigManager()
        config.add_source(RemoteSource(self.server.get_url("/app-config.json")))
        
        # Test accessing values
        self.assertEqual(config.get("app.name"), "RemoteConfigApp")
        self.assertTrue(config.get_bool("app.debug"))
        self.assertEqual(config.get("database.host"), "remote-db.test.com")
        self.assertEqual(config.get_int("database.port"), 5432)
        self.assertTrue(config.get_bool("database.ssl"))

    def test_remote_source_unsupported_format(self):
        """Test RemoteSource with unsupported format."""
        with self.assertRaises(ValueError) as cm:
            RemoteSource("https://example.com/config.xml", format="xml")
        
        self.assertIn("Unsupported format: xml", str(cm.exception))

    def test_remote_source_multi_source_integration(self):
        """Test RemoteSource in multi-source configuration."""
        # Set up remote config
        remote_config = {
            "app": {
                "name": "RemoteApp",
                "version": "1.0.0"
            },
            "database": {
                "host": "remote-db.example.com"
            }
        }
        self.server.set_response("/remote.json", remote_config)
        
        # Create local override config
        local_config = {
            "database": {
                "host": "localhost",  # Override remote value
                "port": 5432
            },
            "debug": True
        }
        
        # Set up another server response for local override
        self.server.set_response("/local.json", local_config)
        
        config = ConfigManager()
        config.add_source(RemoteSource(self.server.get_url("/remote.json")))  # Base
        config.add_source(RemoteSource(self.server.get_url("/local.json")))   # Override
        
        # Test that local overrides remote
        self.assertEqual(config.get("app.name"), "RemoteApp")  # From remote
        self.assertEqual(config.get("app.version"), "1.0.0")  # From remote
        self.assertEqual(config.get("database.host"), "localhost")  # Overridden
        self.assertEqual(config.get_int("database.port"), 5432)  # From local
        self.assertTrue(config.get_bool("debug"))  # From local


if __name__ == '__main__':
    unittest.main()

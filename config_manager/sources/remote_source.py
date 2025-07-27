"""
Remote configuration source for ConfigManager.

This module provides support for loading configuration from remote HTTP/HTTPS URLs,
enabling centralized configuration management and dynamic configuration updates.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, Union
from .base import BaseSource


class RemoteSource(BaseSource):
    """
    Loads configuration from remote HTTP/HTTPS URLs.
    
    This source supports loading configuration from remote endpoints that serve
    JSON configuration data. It includes support for authentication, custom headers,
    timeout configuration, and error handling.
    
    Common use cases:
    - Centralized configuration servers
    - Cloud configuration services (AWS Parameter Store, Azure Key Vault, etc.)
    - Microservices configuration endpoints
    - Dynamic configuration updates
    """

    def __init__(
        self,
        url: str,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        auth_header: str = "Authorization",
        verify_ssl: bool = True,
        format: str = "json"
    ):
        """
        Initialize the remote source.
        
        Args:
            url: The HTTP/HTTPS URL to fetch configuration from
            timeout: Request timeout in seconds (default: 30.0)
            headers: Additional HTTP headers to send with the request
            auth_token: Authentication token (will be added to auth_header)
            auth_header: Header name for authentication (default: "Authorization")
            verify_ssl: Whether to verify SSL certificates (default: True)
            format: Response format, currently only "json" is supported
        """
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.auth_token = auth_token
        self.auth_header = auth_header
        self.verify_ssl = verify_ssl
        self.format = format.lower()
        
        if self.format not in ["json"]:
            raise ValueError(f"Unsupported format: {format}. Only 'json' is currently supported.")
        
        # Add authentication header if token is provided
        if self.auth_token:
            if self.auth_header.lower() == "authorization" and not self.auth_token.startswith(("Bearer ", "Basic ")):
                # Assume Bearer token if no prefix is provided
                self.headers[self.auth_header] = f"Bearer {self.auth_token}"
            else:
                self.headers[self.auth_header] = self.auth_token
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the remote URL.
        
        Returns:
            Dictionary containing the configuration data.
            
        Raises:
            ValueError: If the URL is invalid or response cannot be parsed.
            ConnectionError: If the remote server cannot be reached.
            TimeoutError: If the request times out.
            PermissionError: If authentication fails (HTTP 401/403).
        """
        try:
            # Create the request
            req = urllib.request.Request(self.url)
            
            # Add headers
            for header_name, header_value in self.headers.items():
                req.add_header(header_name, header_value)
            
            # Set User-Agent if not provided
            if "User-Agent" not in self.headers:
                req.add_header("User-Agent", "ConfigManager/1.0")
            
            # Create SSL context if needed
            if not self.verify_ssl and self.url.startswith("https://"):
                import ssl
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
                urllib.request.install_opener(opener)
            
            # Make the request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                
                if self.format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON response from {self.url}: {e}")
                else:
                    # Future formats can be added here
                    raise ValueError(f"Unsupported format: {self.format}")
                    
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PermissionError(f"Authentication failed for {self.url}: HTTP {e.code}")
            else:
                raise ConnectionError(f"HTTP error {e.code} when fetching {self.url}: {e.reason}")
        except urllib.error.URLError as e:
            if "timeout" in str(e.reason).lower() or "timed out" in str(e).lower():
                raise TimeoutError(f"Request to {self.url} timed out after {self.timeout} seconds")
            else:
                raise ConnectionError(f"Failed to connect to {self.url}: {e.reason}")
        except (TimeoutError, ConnectionError, PermissionError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise TimeoutError(f"Request to {self.url} timed out after {self.timeout} seconds")
            else:
                raise ValueError(f"Error loading configuration from {self.url}: {e}")
    
    def is_remote(self) -> bool:
        """Check if this is a remote source (always True for RemoteSource)."""
        return True
    
    def get_cache_key(self) -> str:
        """Generate a cache key for this remote source."""
        return f"remote:{self.url}"
    
    def __str__(self) -> str:
        """String representation of the remote source."""
        return f"RemoteSource('{self.url}')"


class RemoteSourceBuilder:
    """
    Builder class for creating RemoteSource instances with fluent API.
    
    This provides a convenient way to configure remote sources with
    method chaining.
    """
    
    def __init__(self, url: str):
        """Initialize the builder with a URL."""
        self.url = url
        self.timeout = 30.0
        self.headers = {}
        self.auth_token = None
        self.auth_header = "Authorization"
        self.verify_ssl = True
        self.format = "json"
    
    def with_timeout(self, timeout: float) -> 'RemoteSourceBuilder':
        """Set the request timeout."""
        self.timeout = timeout
        return self
    
    def with_header(self, name: str, value: str) -> 'RemoteSourceBuilder':
        """Add a custom header."""
        self.headers[name] = value
        return self
    
    def with_headers(self, headers: Dict[str, str]) -> 'RemoteSourceBuilder':
        """Add multiple custom headers."""
        self.headers.update(headers)
        return self
    
    def with_bearer_token(self, token: str) -> 'RemoteSourceBuilder':
        """Add Bearer token authentication."""
        self.auth_token = token
        self.auth_header = "Authorization"
        return self
    
    def with_api_key(self, key: str, header_name: str = "X-API-Key") -> 'RemoteSourceBuilder':
        """Add API key authentication."""
        self.auth_token = key
        self.auth_header = header_name
        return self
    
    def with_basic_auth(self, username: str, password: str) -> 'RemoteSourceBuilder':
        """Add Basic authentication."""
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.auth_token = f"Basic {credentials}"
        self.auth_header = "Authorization"
        return self
    
    def skip_ssl_verification(self) -> 'RemoteSourceBuilder':
        """Skip SSL certificate verification (use with caution)."""
        self.verify_ssl = False
        return self
    
    def with_format(self, format: str) -> 'RemoteSourceBuilder':
        """Set the response format."""
        self.format = format
        return self
    
    def build(self) -> RemoteSource:
        """Build the RemoteSource instance."""
        return RemoteSource(
            url=self.url,
            timeout=self.timeout,
            headers=self.headers,
            auth_token=self.auth_token,
            auth_header=self.auth_header,
            verify_ssl=self.verify_ssl,
            format=self.format
        )


def remote_source(url: str) -> RemoteSourceBuilder:
    """
    Create a RemoteSourceBuilder for fluent configuration.
    
    Args:
        url: The remote URL to fetch configuration from
        
    Returns:
        RemoteSourceBuilder instance for method chaining
        
    Example:
        source = remote_source("https://config.example.com/app.json") \
            .with_bearer_token("abc123") \
            .with_timeout(60.0) \
            .build()
    """
    return RemoteSourceBuilder(url)

"""
Secrets-aware configuration source for ConfigManager.

This module provides configuration sources that can securely handle sensitive
configuration data using the secrets management system.
"""

from typing import Dict, Any, Optional, Union, Set
from pathlib import Path
import threading
import json

from .base import ConfigSource
from ..secrets import SecretsManager, get_global_secrets_manager, SecretValue, mask_sensitive_config


class SecretsConfigSource(ConfigSource):
    """Configuration source that integrates with secrets management."""
    
    def __init__(self, 
                 secrets_manager: Optional[SecretsManager] = None,
                 secrets_mapping: Optional[Dict[str, str]] = None,
                 mask_secrets: bool = True,
                 auto_refresh: bool = True):
        """
        Initialize secrets configuration source.
        
        Args:
            secrets_manager: SecretsManager instance (uses global if None)
            secrets_mapping: Mapping of config keys to secret keys
            mask_secrets: Whether to mask secret values in logs/display
            auto_refresh: Whether to automatically refresh secrets
        """
        super().__init__()
        self.secrets_manager = secrets_manager or get_global_secrets_manager()
        self.secrets_mapping = secrets_mapping or {}
        self.mask_secrets = mask_secrets
        self.auto_refresh = auto_refresh
        self._config_data: Dict[str, Any] = {}
        self._secret_keys: Set[str] = set()
        self._lock = threading.RLock()
        
        # Register for secret refresh callbacks
        if auto_refresh:
            self.secrets_manager.add_refresh_callback(self._on_secret_refresh)
    
    def add_secret_mapping(self, config_key: str, secret_key: str, 
                          provider_name: Optional[str] = None) -> None:
        """
        Add a mapping from configuration key to secret key.
        
        Args:
            config_key: Key in configuration (supports dot notation)
            secret_key: Key in secrets manager
            provider_name: Specific provider to use for this secret
        """
        mapping_key = f"{provider_name}:{secret_key}" if provider_name else secret_key
        self.secrets_mapping[config_key] = mapping_key
        self._secret_keys.add(secret_key)
    
    def _on_secret_refresh(self, secret_key: str, secret_value: SecretValue) -> None:
        """Handle secret refresh events."""
        # Find config keys that use this secret
        for config_key, mapped_secret in self.secrets_mapping.items():
            if mapped_secret.endswith(f":{secret_key}") or mapped_secret == secret_key:
                # Refresh the config value
                self._load_secret_value(config_key, secret_key)
                if self.on_change:
                    self.on_change(self, config_key)
    
    def _load_secret_value(self, config_key: str, secret_key: str, 
                          provider_name: Optional[str] = None) -> Any:
        """Load a secret value and store it in config."""
        secret = self.secrets_manager.get_secret(secret_key, provider_name)
        if secret:
            value = secret.get_value()
            self._set_nested_value(self._config_data, config_key, value)
            return value
        return None
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set a nested dictionary value using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def load(self) -> Dict[str, Any]:
        """Load configuration with secrets resolved."""
        with self._lock:
            self._config_data = {}
            
            # Load all mapped secrets
            for config_key, secret_mapping in self.secrets_mapping.items():
                if ':' in secret_mapping:
                    provider_name, secret_key = secret_mapping.split(':', 1)
                else:
                    provider_name, secret_key = None, secret_mapping
                
                self._load_secret_value(config_key, secret_key, provider_name)
            
            return self._config_data.copy()
    
    def reload(self) -> None:
        """Reload configuration from secrets."""
        self.load()
        if self.on_change:
            self.on_change(self, None)  # Signal full reload
    
    def get_display_data(self) -> Dict[str, Any]:
        """Get configuration data suitable for display (masked secrets)."""
        if self.mask_secrets:
            return mask_sensitive_config(self._config_data)
        return self._config_data.copy()
    
    def add_secret(self, config_key: str, secret_value: Any,
                   secret_key: Optional[str] = None,
                   provider_name: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new secret and map it to a configuration key.
        
        Args:
            config_key: Key in configuration
            secret_value: The secret value to store
            secret_key: Key in secrets manager (uses config_key if None)
            provider_name: Specific provider to use
            metadata: Optional secret metadata
        """
        secret_key = secret_key or config_key.replace('.', '_')
        
        # Store the secret
        self.secrets_manager.set_secret(secret_key, secret_value, provider_name, metadata)
        
        # Add the mapping
        self.add_secret_mapping(config_key, secret_key, provider_name)
        
        # Load the value into config
        self._load_secret_value(config_key, secret_key, provider_name)
    
    def rotate_secret(self, config_key: str, new_value: Any) -> bool:
        """
        Rotate a secret value for a configuration key.
        
        Args:
            config_key: Configuration key
            new_value: New secret value
            
        Returns:
            True if rotation was successful
        """
        if config_key not in self.secrets_mapping:
            return False
        
        secret_mapping = self.secrets_mapping[config_key]
        if ':' in secret_mapping:
            provider_name, secret_key = secret_mapping.split(':', 1)
        else:
            provider_name, secret_key = None, secret_mapping
        
        success = self.secrets_manager.rotate_secret(secret_key, new_value, provider_name)
        if success:
            self._load_secret_value(config_key, secret_key, provider_name)
        
        return success
    
    def get_secret_info(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Get information about a secret mapped to a configuration key."""
        if config_key not in self.secrets_mapping:
            return None
        
        secret_mapping = self.secrets_mapping[config_key]
        if ':' in secret_mapping:
            provider_name, secret_key = secret_mapping.split(':', 1)
        else:
            provider_name, secret_key = None, secret_mapping
        
        secret = self.secrets_manager.get_secret(secret_key, provider_name)
        if secret:
            return {
                'secret_key': secret_key,
                'provider_name': provider_name,
                'metadata': secret.metadata,
                'accessed_count': secret.accessed_count,
                'created_at': secret.created_at.isoformat(),
                'last_accessed': secret.last_accessed.isoformat() if secret.last_accessed else None
            }
        return None


class EncryptedFileSource(ConfigSource):
    """Configuration source that loads from encrypted files."""
    
    def __init__(self, 
                 file_path: Union[str, Path],
                 secrets_manager: Optional[SecretsManager] = None,
                 decryption_key_name: str = "file_encryption_key",
                 format: str = "json"):
        """
        Initialize encrypted file source.
        
        Args:
            file_path: Path to encrypted configuration file
            secrets_manager: SecretsManager instance for decryption key
            decryption_key_name: Name of secret containing decryption key
            format: File format (json, yaml, etc.)
        """
        super().__init__()
        self.file_path = Path(file_path)
        self.secrets_manager = secrets_manager or get_global_secrets_manager()
        self.decryption_key_name = decryption_key_name
        self.format = format.lower()
        self._config_data: Dict[str, Any] = {}
        
        # Validate dependencies
        try:
            from cryptography.fernet import Fernet
            self._Fernet = Fernet
        except ImportError:
            raise ImportError("cryptography package required for encrypted files. Install with: pip install cryptography")
    
    def _get_fernet(self) -> 'Fernet':
        """Get Fernet instance for encryption/decryption."""
        key_secret = self.secrets_manager.get_secret(self.decryption_key_name)
        if not key_secret:
            raise ValueError(f"Decryption key '{self.decryption_key_name}' not found in secrets manager")
        
        encryption_key = key_secret.get_value()
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        return self._Fernet(encryption_key)
    
    def load(self) -> Dict[str, Any]:
        """Load and decrypt configuration file."""
        if not self.file_path.exists():
            return {}
        
        try:
            # Read encrypted data
            encrypted_data = self.file_path.read_bytes()
            
            # Decrypt
            fernet = self._get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Parse based on format
            if self.format == "json":
                self._config_data = json.loads(decrypted_data.decode())
            elif self.format == "yaml":
                import yaml
                self._config_data = yaml.safe_load(decrypted_data.decode())
            else:
                raise ValueError(f"Unsupported format: {self.format}")
            
            return self._config_data.copy()
            
        except Exception as e:
            print(f"Error loading encrypted file {self.file_path}: {e}")
            return {}
    
    def save_encrypted(self, config_data: Dict[str, Any]) -> None:
        """Save configuration data encrypted to file."""
        try:
            # Serialize data
            if self.format == "json":
                data = json.dumps(config_data, indent=2).encode()
            elif self.format == "yaml":
                import yaml
                data = yaml.dump(config_data, default_flow_style=False).encode()
            else:
                raise ValueError(f"Unsupported format: {self.format}")
            
            # Encrypt
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(data)
            
            # Save atomically
            temp_file = self.file_path.with_suffix('.tmp')
            temp_file.write_bytes(encrypted_data)
            temp_file.replace(self.file_path)
            
        except Exception as e:
            print(f"Error saving encrypted file {self.file_path}: {e}")
            raise


class EnvironmentSecretsSource(ConfigSource):
    """Configuration source that loads secrets from environment variables."""
    
    def __init__(self, 
                 env_prefix: str = "",
                 secrets_manager: Optional[SecretsManager] = None,
                 store_in_secrets: bool = True,
                 mask_values: bool = True):
        """
        Initialize environment secrets source.
        
        Args:
            env_prefix: Prefix for environment variables to consider
            secrets_manager: SecretsManager to store discovered secrets
            store_in_secrets: Whether to store discovered secrets in manager
            mask_values: Whether to mask secret values
        """
        super().__init__()
        self.env_prefix = env_prefix
        self.secrets_manager = secrets_manager or get_global_secrets_manager()
        self.store_in_secrets = store_in_secrets
        self.mask_values = mask_values
        self._config_data: Dict[str, Any] = {}
        
        # Common secret environment variable patterns
        self.secret_patterns = [
            'password', 'passwd', 'pwd', 'secret', 'key', 'token',
            'api_key', 'apikey', 'auth', 'credential', 'credentials',
            'private_key', 'cert', 'certificate', 'access_token',
            'refresh_token', 'client_secret', 'webhook_secret'
        ]
    
    def _is_secret_var(self, var_name: str) -> bool:
        """Check if environment variable name indicates a secret."""
        var_lower = var_name.lower()
        return any(pattern in var_lower for pattern in self.secret_patterns)
    
    def load(self) -> Dict[str, Any]:
        """Load secrets from environment variables."""
        import os
        
        self._config_data = {}
        
        for env_var, value in os.environ.items():
            # Skip if doesn't match prefix
            if self.env_prefix and not env_var.startswith(self.env_prefix):
                continue
            
            # Check if this looks like a secret
            if self._is_secret_var(env_var):
                # Remove prefix for config key
                config_key = env_var[len(self.env_prefix):] if self.env_prefix else env_var
                config_key = config_key.lower()
                
                # Store in secrets manager if requested
                if self.store_in_secrets:
                    secret_key = f"env_{env_var}"
                    metadata = {
                        'source': 'environment',
                        'env_var': env_var,
                        'discovered_at': str(threading.current_thread().ident)
                    }
                    self.secrets_manager.set_secret(secret_key, value, metadata=metadata)
                
                # Store in config (potentially masked)
                if self.mask_values:
                    self._config_data[config_key] = "[MASKED_ENV_SECRET]"
                else:
                    self._config_data[config_key] = value
        
        return self._config_data.copy()

"""
Configuration Secrets Management & Encryption for ConfigManager.

This module provides secure handling of sensitive configuration data through:
- Local encryption with AES-256
- HashiCorp Vault integration
- Azure Key Vault support
- Environment variable masking
- Secrets rotation and refresh capabilities
"""

import os
import json
import base64
import hashlib
import secrets
import threading
from typing import Any, Dict, Optional, Union, Protocol, List, Callable
from pathlib import Path
from abc import ABC, abstractmethod
import time
from datetime import datetime, timedelta

# Encryption imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

# HTTP client for remote secrets
try:
    import requests
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


class SecretValue:
    """Wrapper for secret values that provides security features."""
    
    def __init__(self, value: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a secret value.
        
        Args:
            value: The secret value (will be stored securely)
            metadata: Optional metadata about the secret
        """
        self._value = value
        self.metadata = metadata or {}
        self.accessed_count = 0
        self.created_at = datetime.now()
        self.last_accessed = None
        self._lock = threading.RLock()
    
    def get_value(self) -> Any:
        """Get the secret value (tracks access)."""
        with self._lock:
            self.accessed_count += 1
            self.last_accessed = datetime.now()
            return self._value
    
    def is_expired(self, ttl_seconds: Optional[int] = None) -> bool:
        """Check if the secret has expired."""
        if ttl_seconds is None:
            return False
        
        age = (datetime.now() - self.created_at).total_seconds()
        return age > ttl_seconds
    
    def __str__(self) -> str:
        """Return masked representation for security."""
        return "[MASKED_SECRET]"
    
    def __repr__(self) -> str:
        """Return masked representation for security."""
        return f"SecretValue(masked=True, accessed={self.accessed_count}x)"


class SecretProvider(Protocol):
    """Protocol for secret providers."""
    
    def get_secret(self, key: str) -> Optional[SecretValue]:
        """Get a secret value by key."""
        ...
    
    def set_secret(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a secret value."""
        ...
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        ...
    
    def list_secrets(self) -> List[str]:
        """List available secret keys."""
        ...
    
    def rotate_secret(self, key: str, new_value: Any) -> bool:
        """Rotate a secret to a new value."""
        ...


class LocalEncryptedSecrets(SecretProvider):
    """Local file-based encrypted secrets storage."""
    
    def __init__(self, 
                 secrets_file: Union[str, Path] = ".secrets.enc",
                 password: Optional[str] = None,
                 key_file: Optional[Union[str, Path]] = None):
        """
        Initialize local encrypted secrets storage.
        
        Args:
            secrets_file: Path to encrypted secrets file
            password: Password for encryption (will prompt if None)
            key_file: Path to key file (alternative to password)
        """
        if not ENCRYPTION_AVAILABLE:
            raise ImportError("cryptography package required for encryption. Install with: pip install cryptography")
        
        self.secrets_file = Path(secrets_file)
        self.key_file = Path(key_file) if key_file else None
        self._fernet = None
        self._secrets: Dict[str, SecretValue] = {}
        self._lock = threading.RLock()
        
        # Initialize encryption
        self._init_encryption(password)
        
        # Load existing secrets
        self._load_secrets()
    
    def _init_encryption(self, password: Optional[str] = None) -> None:
        """Initialize encryption key."""
        if self.key_file and self.key_file.exists():
            # Load key from file
            key = self.key_file.read_bytes()
        elif password:
            # Derive key from password
            key = self._derive_key_from_password(password)
        else:
            # Generate new key
            key = Fernet.generate_key()
            if self.key_file:
                self.key_file.write_bytes(key)
                print(f"Generated new encryption key: {self.key_file}")
        
        self._fernet = Fernet(key)
    
    def _derive_key_from_password(self, password: str) -> bytes:
        """Derive encryption key from password."""
        salt_file = self.secrets_file.with_suffix('.salt')
        
        if salt_file.exists():
            salt = salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _load_secrets(self) -> None:
        """Load secrets from encrypted file."""
        if not self.secrets_file.exists():
            return
        
        try:
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            secrets_dict = json.loads(decrypted_data.decode())
            
            for key, secret_data in secrets_dict.items():
                self._secrets[key] = SecretValue(
                    value=secret_data['value'],
                    metadata=secret_data.get('metadata', {})
                )
        except Exception as e:
            print(f"Warning: Could not load secrets file: {e}")
    
    def _save_secrets(self) -> None:
        """Save secrets to encrypted file."""
        secrets_dict = {}
        for key, secret in self._secrets.items():
            secrets_dict[key] = {
                'value': secret._value,
                'metadata': secret.metadata
            }
        
        data = json.dumps(secrets_dict).encode()
        encrypted_data = self._fernet.encrypt(data)
        
        # Atomic write
        temp_file = self.secrets_file.with_suffix('.tmp')
        temp_file.write_bytes(encrypted_data)
        temp_file.replace(self.secrets_file)
    
    def get_secret(self, key: str) -> Optional[SecretValue]:
        """Get a secret value by key."""
        with self._lock:
            return self._secrets.get(key)
    
    def set_secret(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a secret value."""
        with self._lock:
            self._secrets[key] = SecretValue(value, metadata)
            self._save_secrets()
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        with self._lock:
            if key in self._secrets:
                del self._secrets[key]
                self._save_secrets()
                return True
            return False
    
    def list_secrets(self) -> List[str]:
        """List available secret keys."""
        with self._lock:
            return list(self._secrets.keys())
    
    def rotate_secret(self, key: str, new_value: Any) -> bool:
        """Rotate a secret to a new value."""
        if key in self._secrets:
            old_metadata = self._secrets[key].metadata.copy()
            old_metadata['rotated_at'] = datetime.now().isoformat()
            old_metadata['rotation_count'] = old_metadata.get('rotation_count', 0) + 1
            
            self.set_secret(key, new_value, old_metadata)
            return True
        return False


class HashiCorpVaultSecrets(SecretProvider):
    """HashiCorp Vault secrets provider."""
    
    def __init__(self, 
                 vault_url: str,
                 vault_token: str,
                 mount_point: str = "secret",
                 version: str = "v2",
                 timeout: int = 30):
        """
        Initialize HashiCorp Vault secrets provider.
        
        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token
            mount_point: Vault mount point for KV secrets
            version: KV secrets engine version (v1 or v2)
            timeout: Request timeout in seconds
        """
        if not HTTP_AVAILABLE:
            raise ImportError("requests package required for Vault integration. Install with: pip install requests")
        
        self.vault_url = vault_url.rstrip('/')
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.version = version
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            'X-Vault-Token': vault_token,
            'Content-Type': 'application/json'
        })
        self._cache: Dict[str, SecretValue] = {}
        self._cache_lock = threading.RLock()
    
    def _get_path(self, key: str) -> str:
        """Get the full Vault path for a secret key."""
        if self.version == "v2":
            return f"{self.vault_url}/v1/{self.mount_point}/data/{key}"
        else:
            return f"{self.vault_url}/v1/{self.mount_point}/{key}"
    
    def _get_metadata_path(self, key: str) -> str:
        """Get the metadata path for a secret key (KV v2 only)."""
        return f"{self.vault_url}/v1/{self.mount_point}/metadata/{key}"
    
    def get_secret(self, key: str) -> Optional[SecretValue]:
        """Get a secret value by key."""
        try:
            response = self._session.get(self._get_path(key), timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if self.version == "v2":
                secret_data = data['data']['data']
                metadata = data['data']['metadata']
            else:
                secret_data = data['data']
                metadata = {}
            
            # Cache the secret
            with self._cache_lock:
                secret_value = SecretValue(secret_data, metadata)
                self._cache[key] = secret_value
                return secret_value
                
        except requests.RequestException as e:
            print(f"Vault error getting secret '{key}': {e}")
            return None
    
    def set_secret(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a secret value."""
        try:
            if self.version == "v2":
                payload = {"data": value}
            else:
                payload = value
            
            response = self._session.post(
                self._get_path(key),
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Update cache
            with self._cache_lock:
                self._cache[key] = SecretValue(value, metadata or {})
                
        except requests.RequestException as e:
            print(f"Vault error setting secret '{key}': {e}")
            raise
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        try:
            response = self._session.delete(self._get_path(key), timeout=self.timeout)
            response.raise_for_status()
            
            # Remove from cache
            with self._cache_lock:
                self._cache.pop(key, None)
            
            return True
        except requests.RequestException as e:
            print(f"Vault error deleting secret '{key}': {e}")
            return False
    
    def list_secrets(self) -> List[str]:
        """List available secret keys."""
        try:
            list_path = f"{self.vault_url}/v1/{self.mount_point}/metadata"
            if self.version == "v1":
                list_path = f"{self.vault_url}/v1/{self.mount_point}"
            
            response = self._session.get(f"{list_path}?list=true", timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data['data']['keys']
        except requests.RequestException as e:
            print(f"Vault error listing secrets: {e}")
            return []
    
    def rotate_secret(self, key: str, new_value: Any) -> bool:
        """Rotate a secret to a new value."""
        try:
            # Get current metadata
            current_secret = self.get_secret(key)
            metadata = current_secret.metadata.copy() if current_secret else {}
            metadata['rotated_at'] = datetime.now().isoformat()
            metadata['rotation_count'] = metadata.get('rotation_count', 0) + 1
            
            self.set_secret(key, new_value, metadata)
            return True
        except Exception as e:
            print(f"Vault error rotating secret '{key}': {e}")
            return False


class AzureKeyVaultSecrets(SecretProvider):
    """Azure Key Vault secrets provider."""
    
    def __init__(self, 
                 vault_url: str,
                 credential: Optional[Any] = None,
                 timeout: int = 30):
        """
        Initialize Azure Key Vault secrets provider.
        
        Args:
            vault_url: Azure Key Vault URL
            credential: Azure credential object (DefaultAzureCredential if None)
            timeout: Request timeout in seconds
        """
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
            self._SecretClient = SecretClient
        except ImportError:
            raise ImportError("azure-keyvault-secrets package required. Install with: pip install azure-keyvault-secrets azure-identity")
        
        self.vault_url = vault_url
        self.timeout = timeout
        
        if credential is None:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
        
        self._client = SecretClient(vault_url=vault_url, credential=credential)
        self._cache: Dict[str, SecretValue] = {}
        self._cache_lock = threading.RLock()
    
    def get_secret(self, key: str) -> Optional[SecretValue]:
        """Get a secret value by key."""
        try:
            secret = self._client.get_secret(key)
            metadata = {
                'version': secret.properties.version,
                'created_on': secret.properties.created_on.isoformat() if secret.properties.created_on else None,
                'updated_on': secret.properties.updated_on.isoformat() if secret.properties.updated_on else None,
                'content_type': secret.properties.content_type,
                'tags': secret.properties.tags or {}
            }
            
            with self._cache_lock:
                secret_value = SecretValue(secret.value, metadata)
                self._cache[key] = secret_value
                return secret_value
                
        except Exception as e:
            print(f"Azure Key Vault error getting secret '{key}': {e}")
            return None
    
    def set_secret(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a secret value."""
        try:
            # Convert value to string for Azure Key Vault
            if not isinstance(value, str):
                value = json.dumps(value)
            
            tags = metadata.get('tags') if metadata else None
            content_type = metadata.get('content_type') if metadata else None
            
            self._client.set_secret(key, value, content_type=content_type, tags=tags)
            
            # Update cache
            with self._cache_lock:
                self._cache[key] = SecretValue(value, metadata or {})
                
        except Exception as e:
            print(f"Azure Key Vault error setting secret '{key}': {e}")
            raise
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        try:
            delete_operation = self._client.begin_delete_secret(key)
            delete_operation.wait()  # Wait for completion
            
            # Remove from cache
            with self._cache_lock:
                self._cache.pop(key, None)
            
            return True
        except Exception as e:
            print(f"Azure Key Vault error deleting secret '{key}': {e}")
            return False
    
    def list_secrets(self) -> List[str]:
        """List available secret keys."""
        try:
            return [secret.name for secret in self._client.list_properties_of_secrets()]
        except Exception as e:
            print(f"Azure Key Vault error listing secrets: {e}")
            return []
    
    def rotate_secret(self, key: str, new_value: Any) -> bool:
        """Rotate a secret to a new value."""
        try:
            # Get current secret metadata
            current_secret = self.get_secret(key)
            metadata = current_secret.metadata.copy() if current_secret else {}
            metadata['rotated_at'] = datetime.now().isoformat()
            metadata['rotation_count'] = metadata.get('rotation_count', 0) + 1
            
            self.set_secret(key, new_value, metadata)
            return True
        except Exception as e:
            print(f"Azure Key Vault error rotating secret '{key}': {e}")
            return False


class SecretsManager:
    """Main secrets manager coordinating multiple providers."""
    
    def __init__(self, default_provider: Optional[SecretProvider] = None):
        """
        Initialize secrets manager.
        
        Args:
            default_provider: Default secret provider to use
        """
        self.providers: Dict[str, SecretProvider] = {}
        self.default_provider_name: Optional[str] = None
        self._refresh_callbacks: List[Callable[[str, SecretValue], None]] = []
        self._rotation_schedule: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        if default_provider:
            self.add_provider("default", default_provider)
            self.default_provider_name = "default"
    
    def add_provider(self, name: str, provider: SecretProvider) -> None:
        """Add a secret provider."""
        with self._lock:
            self.providers[name] = provider
            if self.default_provider_name is None:
                self.default_provider_name = name
    
    def get_secret(self, key: str, provider_name: Optional[str] = None) -> Optional[SecretValue]:
        """Get a secret value."""
        provider_name = provider_name or self.default_provider_name
        if not self.providers or provider_name not in self.providers:
            return None
        
        return self.providers[provider_name].get_secret(key)
    
    def set_secret(self, key: str, value: Any, 
                   provider_name: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a secret value."""
        provider_name = provider_name or self.default_provider_name
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        self.providers[provider_name].set_secret(key, value, metadata)
    
    def delete_secret(self, key: str, provider_name: Optional[str] = None) -> bool:
        """Delete a secret."""
        provider_name = provider_name or self.default_provider_name
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return self.providers[provider_name].delete_secret(key)
    
    def list_secrets(self, provider_name: Optional[str] = None) -> List[str]:
        """List available secret keys."""
        provider_name = provider_name or self.default_provider_name
        if not self.providers:
            return []  # No providers, no secrets
        if provider_name not in self.providers:
            if provider_name is None:
                return []  # No default provider set
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return self.providers[provider_name].list_secrets()
    
    def rotate_secret(self, key: str, new_value: Any, 
                     provider_name: Optional[str] = None) -> bool:
        """Rotate a secret to a new value."""
        provider_name = provider_name or self.default_provider_name
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        success = self.providers[provider_name].rotate_secret(key, new_value)
        
        if success:
            # Notify callbacks
            secret = self.get_secret(key, provider_name)
            if secret:
                for callback in self._refresh_callbacks:
                    try:
                        callback(key, secret)
                    except Exception as e:
                        print(f"Error in refresh callback: {e}")
        
        return success
    
    def schedule_rotation(self, key: str, interval_hours: int, 
                         generator_func: Callable[[], Any],
                         provider_name: Optional[str] = None) -> None:
        """Schedule automatic secret rotation."""
        with self._lock:
            self._rotation_schedule[key] = {
                'interval_hours': interval_hours,
                'generator_func': generator_func,
                'provider_name': provider_name or self.default_provider_name,
                'last_rotation': datetime.now(),
                'next_rotation': datetime.now() + timedelta(hours=interval_hours)
            }
    
    def add_refresh_callback(self, callback: Callable[[str, SecretValue], None]) -> None:
        """Add a callback for secret refresh events."""
        self._refresh_callbacks.append(callback)
    
    def check_rotations(self) -> None:
        """Check and execute scheduled rotations."""
        now = datetime.now()
        with self._lock:
            for key, schedule in self._rotation_schedule.items():
                if now >= schedule['next_rotation']:
                    try:
                        new_value = schedule['generator_func']()
                        if self.rotate_secret(key, new_value, schedule['provider_name']):
                            schedule['last_rotation'] = now
                            schedule['next_rotation'] = now + timedelta(hours=schedule['interval_hours'])
                            print(f"Rotated secret '{key}' successfully")
                        else:
                            print(f"Failed to rotate secret '{key}'")
                    except Exception as e:
                        print(f"Error rotating secret '{key}': {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get secrets management statistics."""
        stats = {
            'providers': list(self.providers.keys()),
            'default_provider': self.default_provider_name,
            'scheduled_rotations': len(self._rotation_schedule),
            'refresh_callbacks': len(self._refresh_callbacks)
        }
        
        # Provider-specific stats
        for name, provider in self.providers.items():
            try:
                secret_count = len(provider.list_secrets())
                stats[f'{name}_secrets_count'] = secret_count
            except Exception:
                stats[f'{name}_secrets_count'] = 'unavailable'
        
        return stats


def mask_sensitive_config(config: Dict[str, Any], 
                         sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Mask sensitive configuration values for logging/display.
    
    Args:
        config: Configuration dictionary
        sensitive_keys: List of keys to mask (auto-detected if None)
        
    Returns:
        Configuration with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'passwd', 'pwd', 'secret', 'key', 'token',
            'api_key', 'apikey', 'auth', 'credential', 'credentials',
            'private_key', 'cert', 'certificate'
        ]
    
    def mask_value(key: str, value: Any) -> Any:
        if isinstance(value, dict):
            # For dictionaries, recursively process all key-value pairs
            return {k: mask_value(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            # For lists, process each item with index as key
            return [mask_value(str(i), item) for i, item in enumerate(value)]
        else:
            # For scalar values, check if the key indicates it's sensitive
            if isinstance(key, str):
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in sensitive_keys):
                    return "[MASKED]"
            return value
    
    if isinstance(config, dict):
        return {k: mask_value(k, v) for k, v in config.items()}
    else:
        return mask_value("root", config)


# Global secrets manager instance
_global_secrets_manager: Optional[SecretsManager] = None


def get_global_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _global_secrets_manager
    if _global_secrets_manager is None:
        _global_secrets_manager = SecretsManager()
    return _global_secrets_manager


def set_global_secrets_manager(manager: SecretsManager) -> None:
    """Set the global secrets manager instance."""
    global _global_secrets_manager
    _global_secrets_manager = manager

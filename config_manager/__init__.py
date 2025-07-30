"""
A modern and extensible configuration management library for Python.
"""

__version__ = "0.1.0"

from .config_manager import ConfigManager
from .profiles import ProfileManager, ConfigProfile, create_profile_source_path, profile_source_exists
from .secrets import (
    SecretsManager, SecretValue, SecretProvider,
    LocalEncryptedSecrets, HashiCorpVaultSecrets, AzureKeyVaultSecrets,
    get_global_secrets_manager, set_global_secrets_manager, mask_sensitive_config
)

__all__ = [
    "__version__",
    "ConfigManager", "ProfileManager", "ConfigProfile", 
    "create_profile_source_path", "profile_source_exists",
    "SecretsManager", "SecretValue", "SecretProvider",
    "LocalEncryptedSecrets", "HashiCorpVaultSecrets", "AzureKeyVaultSecrets",
    "get_global_secrets_manager", "set_global_secrets_manager", "mask_sensitive_config"
]

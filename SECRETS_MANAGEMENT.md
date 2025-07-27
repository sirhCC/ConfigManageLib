# Configuration Secrets Management & Encryption

## 🔐 **Enterprise-Grade Secrets Management for ConfigManager**

The ConfigManager library now includes comprehensive secrets management capabilities to securely handle sensitive configuration data in production environments.

## **Features Overview**

### 🛡️ **Multiple Secrets Backends**
- **Local Encrypted Storage**: AES-256 encryption with PBKDF2 key derivation
- **HashiCorp Vault**: Enterprise secrets management integration
- **Azure Key Vault**: Microsoft Azure cloud secrets integration
- **Environment Variables**: Automatic secrets detection and masking

### 🔄 **Advanced Security Features**
- **Secret Rotation**: Automatic and manual secret rotation with callbacks
- **Access Monitoring**: Track secret access patterns and usage statistics
- **TTL Support**: Time-based secret expiration and refresh
- **Metadata Management**: Rich metadata for secret categorization and auditing

### 🎭 **Security & Privacy**
- **Automatic Masking**: Secrets hidden in logs and configuration display
- **Thread-Safe Operations**: Safe concurrent access to secrets
- **Secure Memory Handling**: Minimal secret exposure in memory
- **Audit Trail**: Complete access and rotation history

---

## **Quick Start**

### Basic Local Encrypted Secrets

```python
from config_manager import ConfigManager, LocalEncryptedSecrets, SecretsManager

# Set up encrypted secrets storage
local_secrets = LocalEncryptedSecrets(
    secrets_file="app_secrets.enc",
    key_file="app_key.bin"
)

secrets_manager = SecretsManager(local_secrets)

# Store sensitive configuration
secrets_manager.set_secret("database_password", "super_secret_db_pass")
secrets_manager.set_secret("api_key", "sk-1234567890abcdef")

# Create ConfigManager with secrets integration
config = ConfigManager(secrets_manager=secrets_manager)

# Access secrets securely
db_password = config.get_secret("database_password")
api_key = config.get_secret("api_key")
```

### HashiCorp Vault Integration

```python
from config_manager import HashiCorpVaultSecrets, SecretsManager

# Connect to Vault
vault_secrets = HashiCorpVaultSecrets(
    vault_url="https://vault.company.com",
    vault_token="your-vault-token",
    mount_point="secret",
    version="v2"
)

secrets_manager = SecretsManager(vault_secrets)
config = ConfigManager(secrets_manager=secrets_manager)

# Access Vault secrets
db_creds = config.get_secret("database/production")
api_keys = config.get_secret("external-apis/stripe")
```

### Azure Key Vault Integration

```python
from config_manager import AzureKeyVaultSecrets, SecretsManager
from azure.identity import DefaultAzureCredential

# Connect to Azure Key Vault
azure_secrets = AzureKeyVaultSecrets(
    vault_url="https://mykeyvault.vault.azure.net/",
    credential=DefaultAzureCredential()
)

secrets_manager = SecretsManager(azure_secrets)
config = ConfigManager(secrets_manager=secrets_manager)

# Access Azure secrets
storage_key = config.get_secret("storage-account-key")
sql_connection = config.get_secret("sql-connection-string")
```

---

## **Configuration Sources Integration**

### Secrets-Aware Configuration Sources

```python
from config_manager.sources import SecretsConfigSource

# Create secrets-aware configuration source
secrets_source = SecretsConfigSource(
    secrets_manager=secrets_manager,
    auto_refresh=True  # Automatically refresh when secrets rotate
)

# Map configuration keys to secrets
secrets_source.add_secret_mapping("database.password", "db_password")
secrets_source.add_secret_mapping("api.stripe_key", "stripe_api_key")
secrets_source.add_secret_mapping("security.jwt_secret", "jwt_signing_key")

config = ConfigManager()
config.add_source(secrets_source)

# Configuration automatically includes resolved secrets
db_config = config.get("database")  # Includes password from secrets
```

### Encrypted Configuration Files

```python
from config_manager.sources import EncryptedFileSource

# Load configuration from encrypted files
encrypted_source = EncryptedFileSource(
    file_path="production_config.enc",
    secrets_manager=secrets_manager,
    decryption_key_name="config_encryption_key"
)

config = ConfigManager()
config.add_source(encrypted_source)
```

### Environment Variable Secrets Detection

```python
from config_manager.sources import EnvironmentSecretsSource

# Automatically detect and secure environment secrets
env_secrets = EnvironmentSecretsSource(
    env_prefix="APP_",
    store_in_secrets=True,  # Store discovered secrets in secrets manager
    mask_values=True       # Mask secret values in configuration
)

config = ConfigManager()
config.add_source(env_secrets)

# Environment variables like APP_DATABASE_PASSWORD are automatically
# detected as secrets and stored securely
```

---

## **Secret Rotation & Management**

### Manual Secret Rotation

```python
# Rotate a secret to a new value
old_value = config.get_secret("api_key")
new_api_key = "sk-new-rotated-key-" + generate_random_suffix()

success = config.rotate_secret("api_key", new_api_key)
if success:
    print("API key rotated successfully")
```

### Automatic Secret Rotation

```python
import secrets

# Schedule automatic rotation
def generate_new_jwt_secret():
    return secrets.token_urlsafe(32)

config.schedule_secret_rotation(
    key="jwt_secret",
    interval_hours=24,  # Rotate daily
    generator_func=generate_new_jwt_secret
)

# Check and execute scheduled rotations (call periodically)
config.check_secret_rotations()
```

### Rotation Callbacks

```python
# Monitor secret rotations
def on_secret_rotated(key: str, secret_value):
    print(f"Secret '{key}' was rotated")
    # Notify dependent services
    notify_services_of_rotation(key)

secrets_manager.add_refresh_callback(on_secret_rotated)
```

---

## **Security & Monitoring**

### Access Monitoring

```python
# Get secret access information
secret_info = config.get_secret_info("database_password")
print(f"Secret accessed {secret_info['accessed_count']} times")
print(f"Last accessed: {secret_info['last_accessed']}")
print(f"Metadata: {secret_info['metadata']}")
```

### Security Audit

```python
# Get comprehensive secrets statistics
stats = config.get_secrets_stats()
print(f"Total secrets: {stats['default_secrets_count']}")
print(f"Scheduled rotations: {stats['scheduled_rotations']}")
print(f"Active providers: {stats['providers']}")

# List all secrets (keys only, values remain secure)
all_secrets = config.list_secrets()
print(f"Managed secrets: {all_secrets}")
```

### Secrets Masking

```python
# Enable automatic masking (default: enabled)
config.enable_secrets_masking(True)

# Get configuration with secrets masked
masked_config = config.get_config()
print(masked_config)  # Sensitive values shown as "[MASKED]"

# Get raw configuration (for internal use only)
raw_config = config.get_raw_config()  # Contains actual secret values
```

---

## **Production Deployment**

### Recommended Architecture

```python
# Production configuration setup
from config_manager import ConfigManager, SecretsManager, HashiCorpVaultSecrets
from config_manager.sources import JsonSource, EnvironmentSecretsSource

# 1. Set up secrets management
vault_secrets = HashiCorpVaultSecrets(
    vault_url=os.environ["VAULT_URL"],
    vault_token=os.environ["VAULT_TOKEN"],
    mount_point="production"
)

secrets_manager = SecretsManager(vault_secrets)

# 2. Create ConfigManager with production settings
config = ConfigManager(
    secrets_manager=secrets_manager,
    mask_secrets_in_display=True,  # Always mask in production
    enable_caching=True,           # Cache for performance
    auto_reload=True              # Monitor configuration changes
)

# 3. Add configuration sources (order matters)
config.add_source(JsonSource("base_config.json"))        # Base configuration
config.add_source(JsonSource("production_config.json"))  # Environment-specific
config.add_source(EnvironmentSecretsSource(              # Environment secrets
    env_prefix="PROD_",
    store_in_secrets=True
))

# 4. Schedule automatic secret rotations
config.schedule_secret_rotation("database_password", 168, generate_db_password)  # Weekly
config.schedule_secret_rotation("api_keys", 720, generate_api_keys)             # Monthly

# 5. Set up monitoring
def audit_secret_access(key: str, secret_value):
    logger.info(f"Secret '{key}' accessed", extra={'secret_key': key})

secrets_manager.add_refresh_callback(audit_secret_access)
```

### Security Best Practices

1. **Separate Secrets from Configuration**
   - Store sensitive data in dedicated secrets management systems
   - Keep public configuration in version control, secrets external

2. **Use Appropriate Secret Tiers**
   ```python
   # Critical secrets (rotate weekly)
   secrets_manager.set_secret("master_db_password", value, {
       "tier": "critical", 
       "rotation_schedule": "weekly"
   })
   
   # High-value secrets (rotate monthly)  
   secrets_manager.set_secret("payment_api_key", value, {
       "tier": "high",
       "rotation_schedule": "monthly"
   })
   ```

3. **Monitor and Audit Secret Access**
   ```python
   # Track secret usage patterns
   for secret_key in config.list_secrets():
       info = config.get_secret_info(secret_key)
       if info['accessed_count'] == 0:
           logger.warning(f"Unused secret: {secret_key}")
       elif info['accessed_count'] > 1000:
           logger.info(f"High-usage secret: {secret_key}")
   ```

4. **Implement Secret Rotation**
   - Rotate critical secrets regularly
   - Use automated rotation for supported services
   - Monitor rotation success and failures

5. **Use Environment-Specific Secrets Management**
   ```python
   # Development: Local encrypted storage
   if environment == "development":
       secrets_provider = LocalEncryptedSecrets("dev_secrets.enc")
   
   # Production: HashiCorp Vault or Azure Key Vault
   elif environment == "production":
       secrets_provider = HashiCorpVaultSecrets(vault_url, vault_token)
   ```

---

## **Installation & Dependencies**

### Core Installation

```bash
pip install configmanagelib
```

### Optional Dependencies

```bash
# For local encrypted secrets
pip install cryptography>=3.4.8

# For HashiCorp Vault integration
pip install requests>=2.25.0

# For Azure Key Vault integration  
pip install azure-keyvault-secrets>=4.2.0 azure-identity>=1.5.0

# Complete installation with all secrets features
pip install cryptography requests azure-keyvault-secrets azure-identity
```

---

## **API Reference**

### SecretsManager

```python
class SecretsManager:
    def add_provider(name: str, provider: SecretProvider) -> None
    def get_secret(key: str, provider_name: Optional[str] = None) -> Optional[SecretValue]
    def set_secret(key: str, value: Any, provider_name: Optional[str] = None, metadata: Optional[Dict] = None) -> None
    def delete_secret(key: str, provider_name: Optional[str] = None) -> bool
    def list_secrets(provider_name: Optional[str] = None) -> List[str]
    def rotate_secret(key: str, new_value: Any, provider_name: Optional[str] = None) -> bool
    def schedule_rotation(key: str, interval_hours: int, generator_func: Callable) -> None
    def add_refresh_callback(callback: Callable) -> None
    def get_stats() -> Dict[str, Any]
```

### ConfigManager Secrets Methods

```python
class ConfigManager:
    def get_secret(key: str, provider_name: Optional[str] = None) -> Optional[Any]
    def set_secret(key: str, value: Any, provider_name: Optional[str] = None, metadata: Optional[Dict] = None) -> None
    def get_secret_info(key: str, provider_name: Optional[str] = None) -> Optional[Dict]
    def delete_secret(key: str, provider_name: Optional[str] = None) -> bool
    def list_secrets(provider_name: Optional[str] = None) -> List[str]
    def rotate_secret(key: str, new_value: Any, provider_name: Optional[str] = None) -> bool
    def add_secrets_provider(name: str, provider: SecretProvider) -> None
    def get_secrets_stats() -> Dict[str, Any]
    def enable_secrets_masking(enabled: bool = True) -> None
    def schedule_secret_rotation(key: str, interval_hours: int, generator_func: Callable) -> None
    def check_secret_rotations() -> None
```

---

## **Examples & Tutorials**

See `examples/secrets_usage.py` for comprehensive examples including:
- Local encrypted secrets storage
- Multi-provider secrets management  
- ConfigManager integration
- Environment variable secrets
- Production deployment patterns
- Security best practices

Run the examples:

```bash
cd examples
python secrets_usage.py
```

Test the functionality:

```bash
python test_secrets_management.py
```

---

## **🎯 Enterprise Ready**

The secrets management system is designed for enterprise production environments with:

- **🔒 Security**: AES-256 encryption, secure key management, minimal memory exposure
- **🔄 Automation**: Automatic rotation, callback system, scheduled operations  
- **📊 Monitoring**: Access tracking, audit trails, comprehensive statistics
- **🚀 Performance**: Efficient caching, thread-safe operations, minimal overhead
- **🔌 Integration**: Works seamlessly with existing ConfigManager features
- **☁️ Cloud Ready**: Native support for HashiCorp Vault and Azure Key Vault

Perfect for applications requiring **enterprise-grade security** and **compliance** with modern security standards.

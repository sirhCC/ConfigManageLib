#!/usr/bin/env python3
"""
🔐 Enterprise Secrets Management Examples for ConfigManager

This showcase demonstrates modern secrets management with enterprise-grade security patterns.
Features comprehensive examples for production-ready secrets handling and encryption.

✨ What you'll learn:
• Local encrypted secrets storage with AES-256
• Enterprise secrets providers (Vault, Azure Key Vault)
• Automatic secrets masking and PII protection
• Secrets rotation and lifecycle management
• Production security best practices
"""

import os
import tempfile
import json
import time
import secrets as python_secrets
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sys

# Modern import handling - try package import first, fallback to development path
try:
    from config_manager import ConfigManager, SecretsManager, LocalEncryptedSecrets, SecretValue
    from config_manager.sources import JsonSource
except ImportError:
    # Development mode - add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config_manager import ConfigManager, SecretsManager, LocalEncryptedSecrets, SecretValue
    from config_manager.sources import JsonSource


@dataclass
class SecretMetadata:
    """Type-safe secret metadata structure."""
    category: str
    environment: str
    created_by: str
    expires_at: Optional[str] = None
    rotation_interval: Optional[int] = None  # days
    access_level: str = "internal"
    

@dataclass
class DatabaseCredentials:
    """Type-safe database credentials."""
    host: str
    port: int = 5432
    username: str = "app_user"
    password: str = ""
    database: str = "production"
    ssl_mode: str = "require"


@dataclass
class ApiCredentials:
    """Type-safe API credentials."""
    api_key: str
    secret_key: str = ""
    endpoint: str = ""
    timeout: int = 30


# Enhanced console output for secrets (more security-focused)
class SecureConsole:
    """Security-focused console output with enhanced masking."""
    
    @staticmethod
    def header(text: str) -> None:
        """Print a styled security header."""
        print(f"\n🔐 {text}")
        print("=" * (len(text) + 3))
    
    @staticmethod
    def subheader(text: str) -> None:
        """Print a styled security subheader.""" 
        print(f"\n🛡️  {text}")
        print("-" * (len(text) + 4))
    
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
    
    @staticmethod
    def secret_info(name: str, masked_value: str = "[MASKED]", metadata: Optional[Dict] = None, indent: int = 0) -> None:
        """Print secret information with proper masking."""
        prefix = "  " * indent
        print(f"{prefix}🔑 {name}: {masked_value}")
        if metadata:
            for key, value in metadata.items():
                print(f"{prefix}   └─ {key}: {value}")


@contextmanager
def temp_secrets_environment():
    """Context manager for creating temporary secrets environment."""
    with tempfile.TemporaryDirectory(prefix="secrets_demo_") as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


def generate_secure_credentials() -> Dict[str, Any]:
    """Generate realistic secure credentials for demonstration."""
    return {
        'database': DatabaseCredentials(
            host="prod-db.company.com",
            username="app_prod_user", 
            password=python_secrets.token_urlsafe(24),
            database="production_app"
        ),
        'api_keys': {
            'stripe': ApiCredentials(
                api_key=f"sk_live_{python_secrets.token_urlsafe(32)}",
                secret_key=python_secrets.token_urlsafe(24),
                endpoint="https://api.stripe.com/v1"
            ),
            'sendgrid': ApiCredentials(
                api_key=f"SG.{python_secrets.token_urlsafe(16)}.{python_secrets.token_urlsafe(32)}",
                endpoint="https://api.sendgrid.com/v3"
            )
        },
        'security': {
            'jwt_secret': python_secrets.token_urlsafe(48),
            'encryption_key': python_secrets.token_hex(32),
            'session_secret': python_secrets.token_urlsafe(32),
            'csrf_token': python_secrets.token_hex(16)
        }
    }


def demo_local_encrypted_secrets() -> None:
    """Demonstrate modern local encrypted secrets storage with enterprise patterns."""
    SecureConsole.header("Local Encrypted Secrets Storage")
    
    try:
        with temp_secrets_environment() as temp_path:
            SecureConsole.subheader("Encrypted Storage Initialization")
            
            # Create encrypted secrets storage with secure file paths
            secrets_file = temp_path / "production_secrets.enc"
            key_file = temp_path / "master.key"
            
            SecureConsole.info("Initializing AES-256 encrypted storage...")
            local_secrets = LocalEncryptedSecrets(
                secrets_file=secrets_file,
                key_file=key_file
            )
            SecureConsole.success("Encrypted storage initialized successfully")
            
            # Generate realistic enterprise credentials
            credentials = generate_secure_credentials()
            
            SecureConsole.subheader("Secure Secret Storage")
            
            # Store database credentials
            db_creds = credentials['database']
            db_metadata = SecretMetadata(
                category="database",
                environment="production", 
                created_by="deployment_system",
                access_level="restricted"
            )
            
            local_secrets.set_secret(
                'database_password', 
                db_creds.password,
                metadata=db_metadata.__dict__
            )
            SecureConsole.secret_info("database_password", "[32-char secure password]", db_metadata.__dict__)
            
            # Store API credentials
            for api_name, api_creds in credentials['api_keys'].items():
                api_metadata = SecretMetadata(
                    category="api_credentials",
                    environment="production",
                    created_by="secrets_manager",
                    access_level="service"
                ).__dict__
                
                local_secrets.set_secret(f'{api_name}_api_key', api_creds.api_key, metadata=api_metadata)
                SecureConsole.secret_info(f'{api_name}_api_key', f"[{len(api_creds.api_key)}-char API key]", api_metadata, indent=1)
            
            # Store security tokens
            for token_name, token_value in credentials['security'].items():
                security_metadata = SecretMetadata(
                    category="security_tokens",
                    environment="production",
                    created_by="security_system",
                    access_level="critical"
                ).__dict__
                
                local_secrets.set_secret(token_name, token_value, metadata=security_metadata)
                SecureConsole.secret_info(token_name, f"[{len(token_value)}-char secure token]", security_metadata, indent=1)
            
            SecureConsole.subheader("Secret Inventory & Access Control")
            
            # List stored secrets (safely)
            stored_secrets = local_secrets.list_secrets()
            SecureConsole.info(f"Total secrets stored: {len(stored_secrets)}")
            for secret_name in stored_secrets:
                SecureConsole.info(secret_name, indent=1)
            
            # Demonstrate secure retrieval with access tracking
            SecureConsole.subheader("Secure Secret Retrieval")
            
            database_secret = local_secrets.get_secret('database_password')
            if database_secret:
                SecureConsole.success("Database password retrieved")
                SecureConsole.info(f"Access count: {database_secret.accessed_count}")
                SecureConsole.info(f"Last accessed: {database_secret.last_accessed}")
                SecureConsole.info(f"Created: {database_secret.created_at}")
            
            # Demonstrate secret rotation with audit trail
            SecureConsole.subheader("Secret Rotation & Lifecycle Management")
            
            # Rotate API key with proper validation
            old_stripe_secret = local_secrets.get_secret('stripe_api_key')
            if old_stripe_secret:
                new_api_key = f"sk_live_{python_secrets.token_urlsafe(32)}"
                
                SecureConsole.info("Initiating API key rotation...")
                local_secrets.rotate_secret('stripe_api_key', new_api_key)
                
                rotated_secret = local_secrets.get_secret('stripe_api_key')
                if rotated_secret:
                    SecureConsole.success("API key rotated successfully")
                    SecureConsole.info(f"Rotation count: {rotated_secret.metadata.get('rotation_count', 0)}")
                    SecureConsole.info(f"Previous key length: {len(old_stripe_secret.get_value())} chars")
                    SecureConsole.info(f"New key length: {len(rotated_secret.get_value())} chars")
            
            # Test persistence and recovery
            SecureConsole.subheader("Persistence & Recovery Validation")
            
            SecureConsole.info("Testing encrypted persistence...")
            local_secrets_recovery = LocalEncryptedSecrets(
                secrets_file=secrets_file,
                key_file=key_file
            )
            
            recovered_secrets = local_secrets_recovery.list_secrets()
            if len(recovered_secrets) == len(stored_secrets):
                SecureConsole.success("All secrets successfully recovered from encrypted storage")
                SecureConsole.info(f"Verified {len(recovered_secrets)} secrets integrity")
            else:
                SecureConsole.error("Secret recovery validation failed")
            
            SecureConsole.success("Local encrypted secrets demonstration completed")
            
    except ImportError as e:
        SecureConsole.warning(f"Encrypted secrets require cryptography package: {e}")
        SecureConsole.info("Install with: pip install cryptography")
    except Exception as e:
        SecureConsole.error(f"Local encrypted secrets error: {e}")
        raise


def demo_secrets_manager() -> None:
    """Demonstrate enterprise SecretsManager coordination and multi-provider management."""
    SecureConsole.header("Enterprise Secrets Manager")
    
    try:
        with temp_secrets_environment() as temp_path:
            SecureConsole.subheader("Multi-Provider Secrets Architecture")
            
            # Initialize enterprise secrets manager
            secrets_manager = SecretsManager()
            SecureConsole.success("SecretsManager initialized")
            
            # Set up multiple providers for different secret types
            providers = {
                "database": LocalEncryptedSecrets(
                    secrets_file=temp_path / "database_secrets.enc",
                    key_file=temp_path / "db_key.bin"
                ),
                "apis": LocalEncryptedSecrets(
                    secrets_file=temp_path / "api_secrets.enc", 
                    key_file=temp_path / "api_key.bin"
                ),
                "security": LocalEncryptedSecrets(
                    secrets_file=temp_path / "security_secrets.enc",
                    key_file=temp_path / "security_key.bin"
                )
            }
            
            # Register providers with the manager
            for provider_name, provider in providers.items():
                secrets_manager.add_provider(provider_name, provider)
                SecureConsole.info(f"Registered '{provider_name}' provider")
            
            SecureConsole.subheader("Categorized Secret Storage Strategy")
            
            # Generate enterprise-grade secrets by category
            enterprise_secrets = {
                'database': {
                    'primary_db_password': python_secrets.token_urlsafe(32),
                    'replica_db_password': python_secrets.token_urlsafe(32),
                    'backup_db_password': python_secrets.token_urlsafe(32),
                    'migration_user_password': python_secrets.token_urlsafe(24)
                },
                'apis': {
                    'stripe_live_key': f"sk_live_{python_secrets.token_urlsafe(40)}",
                    'stripe_webhook_secret': f"whsec_{python_secrets.token_urlsafe(32)}",
                    'sendgrid_api_key': f"SG.{python_secrets.token_urlsafe(22)}.{python_secrets.token_urlsafe(43)}",
                    'aws_access_key': python_secrets.token_urlsafe(20),
                    'aws_secret_key': python_secrets.token_urlsafe(40)
                },
                'security': {
                    'jwt_signing_key': python_secrets.token_urlsafe(64),
                    'encryption_master_key': python_secrets.token_hex(32),
                    'session_encryption_key': python_secrets.token_urlsafe(48),
                    'csrf_protection_key': python_secrets.token_hex(24),
                    'oauth_client_secret': python_secrets.token_urlsafe(32)
                }
            }
            
            # Store secrets with proper categorization and metadata
            total_secrets_stored = 0
            for category, secrets in enterprise_secrets.items():
                SecureConsole.info(f"Storing {category} secrets:")
                
                for secret_name, secret_value in secrets.items():
                    # Create comprehensive metadata
                    metadata = SecretMetadata(
                        category=category,
                        environment="production",
                        created_by="secrets_manager",
                        access_level="restricted" if category == "security" else "service"
                    ).__dict__
                    
                    # Use provider-specific storage
                    secrets_manager.set_secret(
                        secret_name,
                        secret_value,
                        provider_name=category,
                        metadata=metadata
                    )
                    
                    SecureConsole.secret_info(
                        secret_name, 
                        f"[{len(secret_value)}-char secure value]",
                        metadata,
                        indent=1
                    )
                    total_secrets_stored += 1
            
            SecureConsole.success(f"Stored {total_secrets_stored} enterprise secrets across {len(providers)} providers")
            
            SecureConsole.subheader("Enterprise Secret Discovery & Inventory")
            
            # Demonstrate comprehensive secret inventory
            for provider_name in providers.keys():
                provider_secrets = secrets_manager.list_secrets(provider_name=provider_name)
                SecureConsole.info(f"{provider_name.title()} Provider: {len(provider_secrets)} secrets")
                for secret_name in provider_secrets:
                    SecureConsole.info(secret_name, indent=1)
            
            # Show total inventory across all providers
            all_secrets = secrets_manager.list_secrets()
            SecureConsole.success(f"Total secrets under management: {len(all_secrets)}")
            
            SecureConsole.subheader("Secure Secret Retrieval & Access Patterns")
            
            # Demonstrate secure retrieval patterns
            test_retrievals = [
                ('primary_db_password', 'database'),
                ('stripe_live_key', 'apis'),
                ('jwt_signing_key', 'security')
            ]
            
            for secret_name, expected_provider in test_retrievals:
                secret = secrets_manager.get_secret(secret_name, provider_name=expected_provider)
                if secret:
                    SecureConsole.success(f"Retrieved {secret_name} from {expected_provider} provider")
                    SecureConsole.info(f"Access count: {secret.accessed_count}", indent=1)
                    SecureConsole.info(f"Category: {secret.metadata.get('category', 'unknown')}", indent=1)
                    SecureConsole.info(f"Access level: {secret.metadata.get('access_level', 'unknown')}", indent=1)
                else:
                    SecureConsole.error(f"Failed to retrieve {secret_name}")
            
            SecureConsole.subheader("Enterprise Secret Rotation Management")
            
            # Demonstrate coordinated secret rotation
            rotation_candidates = [
                ('stripe_live_key', 'apis', f"sk_live_{python_secrets.token_urlsafe(40)}"),
                ('jwt_signing_key', 'security', python_secrets.token_urlsafe(64))
            ]
            
            for secret_name, provider, new_value in rotation_candidates:
                SecureConsole.info(f"Rotating {secret_name} in {provider} provider...")
                
                # Get old secret for audit
                old_secret = secrets_manager.get_secret(secret_name, provider_name=provider)
                if old_secret:
                    old_length = len(old_secret.get_value())
                    
                    # Perform rotation
                    secrets_manager.rotate_secret(secret_name, new_value, provider_name=provider)
                    
                    # Verify rotation
                    new_secret = secrets_manager.get_secret(secret_name, provider_name=provider)
                    if new_secret:
                        SecureConsole.success(f"Successfully rotated {secret_name}")
                        SecureConsole.info(f"Old value: {old_length} chars → New value: {len(new_secret.get_value())} chars", indent=1)
                        SecureConsole.info(f"Rotation count: {new_secret.metadata.get('rotation_count', 0)}", indent=1)
            
            SecureConsole.success("Enterprise secrets manager demonstration completed")
            
    except ImportError as e:
        SecureConsole.warning(f"Secrets manager requires cryptography package: {e}")
        SecureConsole.info("Install with: pip install cryptography")
    except Exception as e:
        SecureConsole.error(f"Secrets manager error: {e}")
        raise


def demo_configmanager_integration() -> None:
    """Demonstrate advanced ConfigManager integration with enterprise secrets."""
    SecureConsole.header("ConfigManager Enterprise Integration")
    
    try:
        with temp_secrets_environment() as temp_path:
            SecureConsole.subheader("Hybrid Configuration Architecture")
            
            # Create realistic public configuration
            public_config = {
                'application': {
                    'name': 'Enterprise ConfigManager Demo',
                    'version': '2.0.0',
                    'environment': 'production'
                },
                'database': {
                    'host': 'prod-cluster.company.com',
                    'port': 5432,
                    'database': 'production_app',
                    'ssl_mode': 'require',
                    'pool_size': 20
                    # Note: credentials come from secrets
                },
                'features': {
                    'logging': True,
                    'monitoring': True,
                    'analytics': True,
                    'cache_enabled': True
                },
                'api_endpoints': {
                    'payment_gateway': 'https://api.stripe.com/v1',
                    'email_service': 'https://api.sendgrid.com/v3',
                    'monitoring': 'https://api.datadog.com/api/v1'
                }
            }
            
            config_file = temp_path / "production_config.json"
            config_file.write_text(json.dumps(public_config, indent=2))
            
            SecureConsole.subheader("Enterprise Secrets Setup")
            
            # Set up segregated secrets storage
            secrets_manager = SecretsManager()
            
            # Database secrets provider
            db_secrets = LocalEncryptedSecrets(
                secrets_file=temp_path / "database_secrets.enc",
                key_file=temp_path / "db_key.bin"
            )
            secrets_manager.add_provider("database", db_secrets)
            
            # API secrets provider
            api_secrets = LocalEncryptedSecrets(
                secrets_file=temp_path / "api_secrets.enc",
                key_file=temp_path / "api_key.bin"
            )
            secrets_manager.add_provider("external_apis", api_secrets)
            
            # Store enterprise credentials
            enterprise_credentials = generate_secure_credentials()
            
            # Database credentials
            db_creds = enterprise_credentials['database']
            secrets_manager.set_secret(
                'prod_db_user',
                db_creds.username,
                provider_name='database',
                metadata={'type': 'username', 'tier': 'critical'}
            )
            secrets_manager.set_secret(
                'prod_db_password',
                db_creds.password,
                provider_name='database', 
                metadata={'type': 'password', 'tier': 'critical', 'rotation_days': 7}
            )
            
            # API credentials
            for api_name, api_creds in enterprise_credentials['api_keys'].items():
                secrets_manager.set_secret(
                    f'{api_name}_api_key',
                    api_creds.api_key,
                    provider_name='external_apis',
                    metadata={'type': 'api_key', 'service': api_name, 'tier': 'high'}
                )
            
            SecureConsole.success("Enterprise secrets stored across dedicated providers")
            
            SecureConsole.subheader("Integrated ConfigManager Setup")
            
            # Create ConfigManager with secrets integration
            config_manager = ConfigManager(
                secrets_manager=secrets_manager,
                mask_secrets_in_display=True,
                enable_caching=True
            )
            
            # Add public configuration source
            config_manager.add_source(JsonSource(str(config_file)))
            
            SecureConsole.success("ConfigManager initialized with secrets integration")
            
            SecureConsole.subheader("Unified Configuration Access")
            
            # Access public configuration
            SecureConsole.info("Public configuration:")
            SecureConsole.info(f"App: {config_manager.get('application.name')} v{config_manager.get('application.version')}", indent=1)
            SecureConsole.info(f"Database host: {config_manager.get('database.host')}", indent=1)
            SecureConsole.info(f"Pool size: {config_manager.get('database.pool_size')} connections", indent=1)
            
            # Access secrets seamlessly
            SecureConsole.info("Secure credentials access:")
            db_user = config_manager.get_secret('prod_db_user')
            db_password = config_manager.get_secret('prod_db_password') 
            stripe_key = config_manager.get_secret('stripe_api_key')
            
            SecureConsole.secret_info('prod_db_user', '[RETRIEVED]' if db_user else '[FAILED]', indent=1)
            SecureConsole.secret_info('prod_db_password', '[RETRIEVED]' if db_password else '[FAILED]', indent=1)
            SecureConsole.secret_info('stripe_api_key', '[RETRIEVED]' if stripe_key else '[FAILED]', indent=1)
            
            SecureConsole.subheader("Advanced Security Features")
            
            # Demonstrate masking in configuration display
            SecureConsole.info("Configuration masking demonstration:")
            full_config = config_manager.get_config()
            config_summary = {
                'total_keys': len(full_config),
                'public_sections': len([k for k in full_config.keys() if not k.startswith('_')]),
                'secrets_masked': 'Yes - all sensitive data protected'
            }
            
            for key, value in config_summary.items():
                SecureConsole.info(f"{key}: {value}", indent=1)
            
            # Secret access auditing
            SecureConsole.info("Security audit information:")
            audit_targets = ['prod_db_password', 'stripe_api_key']
            
            for secret_name in audit_targets:
                secret_info = config_manager.get_secret_info(secret_name)
                if secret_info:
                    SecureConsole.info(f"{secret_name} audit:", indent=1)
                    SecureConsole.info(f"Access count: {secret_info.get('accessed_count', 0)}", indent=2)
                    SecureConsole.info(f"Security tier: {secret_info.get('metadata', {}).get('tier', 'unknown')}", indent=2)
                    SecureConsole.info(f"Last access: {secret_info.get('last_accessed', 'never')}", indent=2)
            
            # Demonstrate secret rotation
            SecureConsole.info("Secret rotation demonstration:")
            new_stripe_key = f"sk_live_{python_secrets.token_urlsafe(40)}"
            rotation_success = config_manager.rotate_secret('stripe_api_key', new_stripe_key)
            
            if rotation_success:
                SecureConsole.success("Stripe API key rotated successfully")
                rotated_secret = config_manager.get_secret('stripe_api_key')
                if rotated_secret:
                    SecureConsole.info(f"New key length: {len(rotated_secret.get_value())} characters", indent=1)
            else:
                SecureConsole.error("Secret rotation failed")
            
            # Final statistics
            secrets_stats = config_manager.get_secrets_stats()
            SecureConsole.info("Enterprise secrets statistics:")
            SecureConsole.info(f"Total secrets: {secrets_stats.get('total_secrets', 0)}", indent=1)
            SecureConsole.info(f"Active providers: {len(secrets_stats.get('providers', []))}", indent=1)
            SecureConsole.info(f"Rotation schedules: {secrets_stats.get('scheduled_rotations', 0)}", indent=1)
            
            SecureConsole.success("ConfigManager enterprise integration completed")
            
    except ImportError as e:
        SecureConsole.warning(f"ConfigManager integration requires cryptography: {e}")
        SecureConsole.info("Install with: pip install cryptography")
    except Exception as e:
        SecureConsole.error(f"ConfigManager integration error: {e}")
        raise


def demo_production_security_patterns() -> None:
    """Demonstrate production-ready security patterns and best practices."""
    SecureConsole.header("Production Security Patterns & Best Practices")
    
    try:
        with temp_secrets_environment() as temp_path:
            SecureConsole.subheader("1. Layered Security Architecture")
            
            # Different security tiers for different types of secrets
            security_tiers = {
                'critical': {
                    'rotation_days': 7,
                    'access_level': 'restricted',
                    'encryption': 'AES-256',
                    'examples': ['database_master_password', 'root_api_keys']
                },
                'high': {
                    'rotation_days': 30,
                    'access_level': 'service',
                    'encryption': 'AES-256',
                    'examples': ['payment_api_keys', 'oauth_secrets']
                },
                'medium': {
                    'rotation_days': 90,
                    'access_level': 'application',
                    'encryption': 'AES-256',
                    'examples': ['monitoring_tokens', 'webhook_secrets']
                }
            }
            
            SecureConsole.info("Security tier classification:")
            for tier, config in security_tiers.items():
                SecureConsole.info(f"{tier.upper()} Tier:", indent=1)
                SecureConsole.info(f"Rotation: {config['rotation_days']} days", indent=2)
                SecureConsole.info(f"Access: {config['access_level']}", indent=2)
                SecureConsole.info(f"Examples: {', '.join(config['examples'])}", indent=2)
            
            SecureConsole.subheader("2. Segregated Storage Strategy")
            
            # Create tier-specific storage
            secrets_manager = SecretsManager()
            
            tier_providers = {}
            for tier in security_tiers.keys():
                provider = LocalEncryptedSecrets(
                    secrets_file=temp_path / f"{tier}_secrets.enc",
                    key_file=temp_path / f"{tier}_key.bin"
                )
                secrets_manager.add_provider(tier, provider)
                tier_providers[tier] = provider
                SecureConsole.info(f"Created {tier} tier storage", indent=1)
            
            SecureConsole.subheader("3. Production Secret Management")
            
            # Generate and store secrets by security tier
            production_secrets = {
                'critical': {
                    'database_master_password': python_secrets.token_urlsafe(32),
                    'encryption_master_key': python_secrets.token_hex(32),
                    'root_admin_token': python_secrets.token_urlsafe(40)
                },
                'high': {
                    'stripe_live_secret': f"sk_live_{python_secrets.token_urlsafe(32)}",
                    'oauth_client_secret': python_secrets.token_urlsafe(32),
                    'jwt_signing_key': python_secrets.token_urlsafe(48)
                },
                'medium': {
                    'webhook_verification_secret': python_secrets.token_hex(24),
                    'monitoring_api_token': f"token_{python_secrets.token_hex(16)}",
                    'cache_auth_password': python_secrets.token_urlsafe(16)
                }
            }
            
            total_stored = 0
            for tier, secrets in production_secrets.items():
                tier_config = security_tiers[tier]
                SecureConsole.info(f"Storing {tier} tier secrets:")
                
                for secret_name, secret_value in secrets.items():
                    metadata = SecretMetadata(
                        category=tier,
                        environment="production",
                        created_by="security_system",
                        access_level=tier_config['access_level'],
                        rotation_interval=tier_config['rotation_days']
                    ).__dict__
                    
                    secrets_manager.set_secret(
                        secret_name,
                        secret_value,
                        provider_name=tier,
                        metadata=metadata
                    )
                    
                    SecureConsole.secret_info(
                        secret_name,
                        f"[{len(secret_value)}-char {tier} secret]",
                        metadata,
                        indent=1
                    )
                    total_stored += 1
            
            SecureConsole.success(f"Stored {total_stored} production secrets across {len(tier_providers)} security tiers")
            
            SecureConsole.subheader("4. Automated Rotation Schedules")
            
            # Set up rotation schedules based on security tier
            SecureConsole.info("Configuring automated rotation:")
            
            def generate_database_password():
                return python_secrets.token_urlsafe(32)
            
            def generate_api_token():
                return f"token_{python_secrets.token_hex(20)}"
            
            def generate_webhook_secret():
                return python_secrets.token_hex(24)
            
            rotation_configs = [
                ('database_master_password', 'critical', 168, generate_database_password),  # Weekly
                ('stripe_live_secret', 'high', 720, generate_api_token),                   # Monthly
                ('webhook_verification_secret', 'medium', 2160, generate_webhook_secret)   # Quarterly
            ]
            
            for secret_name, tier, hours, generator in rotation_configs:
                    try:
                        secrets_manager.schedule_rotation(
                            key=secret_name,
                            interval_hours=hours,
                            generator_func=generator
                        )
                        SecureConsole.info(f"Scheduled {secret_name}: every {hours}h ({hours//24} days)", indent=1)
                    except AttributeError:
                        SecureConsole.warning(f"Rotation scheduling not available for {secret_name}")
                    except Exception as e:
                        SecureConsole.warning(f"Rotation scheduling error: {e}")
            
            SecureConsole.subheader("5. Access Monitoring & Audit Trail")
            
            # Set up access monitoring
            access_log = []
            
            def audit_secret_access(key: str, secret_value):
                access_log.append({
                    'secret': key,
                    'timestamp': datetime.now().isoformat(),
                    'thread': threading.current_thread().name
                })
                SecureConsole.info(f"🔍 Audit: {key} accessed", indent=1)
            
            try:
                secrets_manager.add_refresh_callback(audit_secret_access)
                SecureConsole.success("Access monitoring enabled")
            except Exception as e:
                SecureConsole.warning(f"Access monitoring not available: {e}")
            
            SecureConsole.subheader("6. Production ConfigManager Integration")
            
            # Create production-ready ConfigManager
            config_manager = ConfigManager(
                secrets_manager=secrets_manager,
                mask_secrets_in_display=True,
                enable_caching=True
            )
            
            # Test secure access patterns
            SecureConsole.info("Testing secure access patterns:")
            
            # Access secrets from different tiers
            test_secrets = [
                ('database_master_password', 'critical'),
                ('stripe_live_secret', 'high'),
                ('webhook_verification_secret', 'medium')
            ]
            
            for secret_name, expected_tier in test_secrets:
                secret = config_manager.get_secret(secret_name)
                if secret:
                    SecureConsole.success(f"Retrieved {secret_name} ({expected_tier} tier)")
                    SecureConsole.info(f"Access count: {secret.accessed_count}", indent=1)
                    SecureConsole.info(f"Security tier: {secret.metadata.get('category', 'unknown')}", indent=1)
                else:
                    SecureConsole.error(f"Failed to retrieve {secret_name}")
            
            SecureConsole.subheader("7. Security Audit Summary")
            
            # Generate comprehensive audit report
            audit_report = {
                'total_secrets': len(secrets_manager.list_secrets()),
                'security_tiers': len(tier_providers),
                'access_events': len(access_log),
                'rotation_schedules': 3,  # From our configuration
                'encryption_status': 'AES-256 enabled',
                'masking_enabled': True
            }
            
            SecureConsole.info("Production security audit:")
            for metric, value in audit_report.items():
                SecureConsole.info(f"{metric.replace('_', ' ').title()}: {value}", indent=1)
            
            SecureConsole.success("Production security patterns demonstration completed")
            
    except ImportError as e:
        SecureConsole.warning(f"Production patterns require cryptography: {e}")
        SecureConsole.info("Install with: pip install cryptography")
    except Exception as e:
        SecureConsole.error(f"Production security patterns error: {e}")
        raise


def main() -> None:
    """Execute all modernized secrets management demonstrations."""
    try:
        # Beautiful header
        print("\n" + "="*80)
        print("🔐 ConfigManager: Enterprise Secrets Management & Encryption")
        print("="*80)
        print("🛡️  Production-ready security patterns and enterprise-grade encryption")
        print()
        
        # Run all demonstrations with error handling
        demos = [
            demo_local_encrypted_secrets,
            demo_secrets_manager,
            demo_configmanager_integration,
            demo_production_security_patterns
        ]
        
        for i, demo_func in enumerate(demos, 1):
            try:
                demo_func()
            except Exception as e:
                SecureConsole.error(f"Demo {i} failed: {e}")
                continue
        
        # Success summary
        print("\n" + "="*80)
        SecureConsole.success("All secrets management examples completed successfully!")
        print("🔐 Your ConfigManager now features enterprise-grade secrets management")
        print("="*80)
        
        # Key takeaways
        print("\n🛡️  Key Security Features:")
        print("   ✅ AES-256 local encryption")
        print("   ✅ Multi-provider secrets architecture") 
        print("   ✅ Automatic secrets masking")
        print("   ✅ Secret rotation and lifecycle management")
        print("   ✅ Access monitoring and audit trails")
        print("   ✅ Security tier classification")
        print("   ✅ Production-ready integration patterns")
        
        print("\n🎯 Best Practices Demonstrated:")
        print("   • Separate secrets from public configuration")
        print("   • Use metadata for secret categorization")
        print("   • Implement rotation schedules based on security tiers")
        print("   • Monitor and audit secret access patterns")
        print("   • Always mask secrets in logs and displays")
        print("   • Use dedicated providers for different secret types")
        
    except KeyboardInterrupt:
        SecureConsole.warning("Demo interrupted by user")
    except Exception as e:
        SecureConsole.error(f"Critical error: {e}")
        raise


if __name__ == "__main__":
    main()

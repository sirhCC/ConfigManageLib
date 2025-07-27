#!/usr/bin/env python3
"""
Secrets Management Examples for ConfigManager

This example demonstrates how to use the secrets management features
to securely handle sensitive configuration data including:
- Local encrypted secrets storage
- HashiCorp Vault integration  
- Azure Key Vault integration
- Environment variable secrets
- Secrets rotation and refresh
"""

import os
import tempfile
import json
import time
import secrets as python_secrets
from pathlib import Path

# Add the parent directory to the Python path so we can import the modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import ConfigManager, SecretsManager, LocalEncryptedSecrets
from config_manager.sources import JsonSource


def demo_local_encrypted_secrets():
    """Demonstrate local encrypted secrets storage."""
    print("=== Local Encrypted Secrets ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create encrypted secrets storage
            secrets_file = temp_path / "secrets.enc"
            key_file = temp_path / "key.bin"
            
            print("Creating encrypted secrets storage...")
            local_secrets = LocalEncryptedSecrets(
                secrets_file=secrets_file,
                key_file=key_file
            )
            
            # Store some secrets
            secrets_data = {
                'database_password': 'super_secret_db_pass_123',
                'api_key': 'sk-1234567890abcdef',
                'jwt_secret': 'my-super-secret-jwt-key',
                'encryption_key': python_secrets.token_hex(32)
            }
            
            print("Storing secrets...")
            for key, value in secrets_data.items():
                metadata = {
                    'type': 'credential',
                    'created_by': 'demo_script',
                    'environment': 'development'
                }
                local_secrets.set_secret(key, value, metadata)
            
            # List stored secrets
            print(f"Stored secrets: {local_secrets.list_secrets()}")
            
            # Retrieve secrets
            print("\nRetrieving secrets:")
            for key in secrets_data.keys():
                secret = local_secrets.get_secret(key)
                if secret:
                    print(f"  {key}: [RETRIEVED] (accessed {secret.accessed_count}x)")
                    print(f"    Metadata: {secret.metadata}")
                else:
                    print(f"  {key}: NOT FOUND")
            
            # Test secret rotation
            print("\nTesting secret rotation...")
            old_api_key = local_secrets.get_secret('api_key').get_value()
            new_api_key = 'sk-new-rotated-key-9876543210'
            
            local_secrets.rotate_secret('api_key', new_api_key)
            rotated_secret = local_secrets.get_secret('api_key')
            print(f"  Rotated API key from '{old_api_key[:10]}...' to '{rotated_secret.get_value()[:10]}...'")
            print(f"  Rotation count: {rotated_secret.metadata.get('rotation_count', 0)}")
            
            # Verify persistence (create new instance)
            print("\nTesting persistence...")
            local_secrets2 = LocalEncryptedSecrets(
                secrets_file=secrets_file,
                key_file=key_file
            )
            persisted_secrets = local_secrets2.list_secrets()
            print(f"Persisted secrets: {persisted_secrets}")
            
        except ImportError as e:
            print(f"Skipping encrypted secrets demo: {e}")
            print("Install cryptography package: pip install cryptography")
    
    print()


def demo_secrets_manager():
    """Demonstrate the SecretsManager coordination."""
    print("=== Secrets Manager ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create secrets manager with local provider
            secrets_manager = SecretsManager()
            
            # Add local encrypted provider
            local_provider = LocalEncryptedSecrets(
                secrets_file=temp_path / "app_secrets.enc",
                key_file=temp_path / "app_key.bin"
            )
            secrets_manager.add_provider("local", local_provider)
            
            # Store secrets across different categories
            app_secrets = {
                'database': {
                    'host': 'localhost',
                    'user': 'admin',
                    'password': 'db_secret_pass_456'
                },
                'external_apis': {
                    'stripe_key': 'sk_test_123456789',
                    'sendgrid_key': 'SG.abcdef123456.ghijkl789012'
                },
                'security': {
                    'jwt_secret': python_secrets.token_urlsafe(32),
                    'encryption_key': python_secrets.token_hex(32)
                }
            }
            
            print("Storing application secrets...")
            for category, secrets in app_secrets.items():
                for key, value in secrets.items():
                    secret_key = f"{category}_{key}"
                    metadata = {
                        'category': category,
                        'environment': 'development',
                        'created_by': 'secrets_demo'
                    }
                    secrets_manager.set_secret(secret_key, value, metadata=metadata)
            
            # List all secrets
            all_secrets = secrets_manager.list_secrets()
            print(f"Total secrets stored: {len(all_secrets)}")
            print("Secret keys:", all_secrets)
            
            # Get secret with info
            db_password = secrets_manager.get_secret('database_password')
            db_info = secrets_manager.get_stats()
            print(f"\nDatabase password retrieved: {'[MASKED]' if db_password else 'NOT FOUND'}")
            print(f"Secrets manager stats: {db_info}")
            
            # Test rotation with callback
            print("\nTesting rotation with callbacks...")
            rotation_count = 0
            
            def on_secret_refresh(key: str, secret_value):
                nonlocal rotation_count
                rotation_count += 1
                print(f"  🔄 Secret '{key}' was rotated (callback #{rotation_count})")
            
            secrets_manager.add_refresh_callback(on_secret_refresh)
            
            # Rotate the JWT secret
            new_jwt_secret = python_secrets.token_urlsafe(32)
            success = secrets_manager.rotate_secret('security_jwt_secret', new_jwt_secret)
            print(f"JWT secret rotation: {'SUCCESS' if success else 'FAILED'}")
            
            # Schedule automatic rotation (demo)
            print("\nScheduling automatic rotation...")
            def generate_new_api_key():
                return f"sk_auto_{python_secrets.token_hex(16)}"
            
            secrets_manager.schedule_rotation(
                key='external_apis_stripe_key',
                interval_hours=24,  # Rotate daily
                generator_func=generate_new_api_key
            )
            
            # Check rotations (would normally be called periodically)
            secrets_manager.check_rotations()
            
        except ImportError as e:
            print(f"Skipping secrets manager demo: {e}")
    
    print()


def demo_config_manager_with_secrets():
    """Demonstrate ConfigManager with integrated secrets."""
    print("=== ConfigManager with Secrets Integration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create a configuration file with some public data
            public_config = {
                'app': {
                    'name': 'MySecureApp',
                    'version': '1.0.0',
                    'environment': 'development'
                },
                'database': {
                    'host': 'localhost',
                    'port': 5432,
                    'name': 'myapp_dev'
                    # Note: password will come from secrets
                },
                'features': {
                    'logging': True,
                    'analytics': False
                }
            }
            
            config_file = temp_path / "app_config.json"
            with open(config_file, 'w') as f:
                json.dump(public_config, f, indent=2)
            
            # Set up secrets manager with encrypted storage
            local_secrets = LocalEncryptedSecrets(
                secrets_file=temp_path / "config_secrets.enc",
                key_file=temp_path / "config_key.bin"
            )
            
            secrets_manager = SecretsManager(local_secrets)
            
            # Store sensitive configuration as secrets
            sensitive_config = {
                'database_password': 'prod_db_password_789',
                'api_keys_stripe': 'sk_live_abcdef123456789',
                'api_keys_sendgrid': 'SG.live_key.xyz789',
                'security_jwt_secret': python_secrets.token_urlsafe(32),
                'monitoring_webhook_secret': python_secrets.token_hex(16)
            }
            
            for key, value in sensitive_config.items():
                metadata = {'source': 'config_demo', 'type': 'config_secret'}
                secrets_manager.set_secret(key, value, metadata=metadata)
            
            # Create ConfigManager with secrets integration
            print("Creating ConfigManager with secrets...")
            config_manager = ConfigManager(
                secrets_manager=secrets_manager,
                mask_secrets_in_display=True  # Mask secrets in get_config()
            )
            
            # Add public configuration source
            config_manager.add_source(JsonSource(str(config_file)))
            
            # Access public configuration
            print("\nPublic configuration:")
            print(f"  App name: {config_manager.get('app.name')}")
            print(f"  Database host: {config_manager.get('database.host')}")
            print(f"  Database port: {config_manager.get('database.port')}")
            
            # Access secrets through ConfigManager
            print("\nAccessing secrets:")
            db_password = config_manager.get_secret('database_password')
            stripe_key = config_manager.get_secret('api_keys_stripe')
            jwt_secret = config_manager.get_secret('security_jwt_secret')
            
            print(f"  Database password: {'[RETRIEVED]' if db_password else 'NOT FOUND'}")
            print(f"  Stripe API key: {'[RETRIEVED]' if stripe_key else 'NOT FOUND'}")
            print(f"  JWT secret: {'[RETRIEVED]' if jwt_secret else 'NOT FOUND'}")
            
            # Show masked configuration (secrets hidden)
            print("\nMasked configuration display:")
            masked_config = config_manager.get_config()
            print(f"  Config keys: {list(masked_config.keys())}")
            
            # Show secrets info
            print("\nSecrets information:")
            for secret_key in ['database_password', 'api_keys_stripe']:
                info = config_manager.get_secret_info(secret_key)
                if info:
                    print(f"  {secret_key}:")
                    print(f"    Accessed: {info['accessed_count']} times")
                    print(f"    Created: {info['created_at']}")
                    print(f"    Metadata: {info['metadata']}")
            
            # Demonstrate secret rotation
            print("\nRotating secrets...")
            new_stripe_key = 'sk_live_rotated_' + python_secrets.token_hex(12)
            rotation_success = config_manager.rotate_secret('api_keys_stripe', new_stripe_key)
            print(f"  Stripe key rotation: {'SUCCESS' if rotation_success else 'FAILED'}")
            
            # List all secrets
            all_secrets = config_manager.list_secrets()
            print(f"  Total secrets managed: {len(all_secrets)}")
            
            # Get secrets statistics
            secrets_stats = config_manager.get_secrets_stats()
            print(f"  Secrets stats: {secrets_stats}")
            
        except ImportError as e:
            print(f"Skipping ConfigManager secrets demo: {e}")
    
    print()


def demo_environment_secrets():
    """Demonstrate automatic discovery of secrets in environment variables."""
    print("=== Environment Variable Secrets ===")
    
    # Set up some test environment variables that look like secrets
    test_env_vars = {
        'APP_DATABASE_PASSWORD': 'env_db_secret_123',
        'APP_API_KEY': 'env_api_key_456',
        'APP_JWT_SECRET': 'env_jwt_secret_789',
        'APP_WEBHOOK_SECRET': 'env_webhook_secret_012',
        'APP_ENCRYPTION_KEY': 'env_encryption_key_345',
        'APP_PUBLIC_CONFIG': 'not_a_secret_value'  # This won't be detected as secret
    }
    
    # Temporarily set environment variables
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # ConfigManager will automatically discover and handle env secrets
        config_manager = ConfigManager(mask_secrets_in_display=True)
        
        # Add environment secrets source
        from config_manager.sources.secrets_source import EnvironmentSecretsSource
        
        env_secrets_source = EnvironmentSecretsSource(
            env_prefix='APP_',
            store_in_secrets=True,
            mask_values=True
        )
        
        config_manager.add_source(env_secrets_source)
        
        print("Environment variables processed:")
        config_data = config_manager.get_config()
        for key, value in config_data.items():
            print(f"  {key}: {value}")
        
        # Check what was stored in secrets manager
        secrets_list = config_manager.list_secrets()
        env_secrets = [s for s in secrets_list if s.startswith('env_')]
        print(f"\nSecrets discovered from environment: {len(env_secrets)}")
        for secret_key in env_secrets:
            print(f"  - {secret_key}")
        
        # Access a secret value
        db_password_secret = config_manager.get_secret('env_APP_DATABASE_PASSWORD')
        print(f"\nDatabase password from env: {'[RETRIEVED]' if db_password_secret else 'NOT FOUND'}")
        
    except ImportError as e:
        print(f"Skipping environment secrets demo: {e}")
    finally:
        # Restore original environment variables
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    print()


def demo_secrets_best_practices():
    """Demonstrate secrets management best practices."""
    print("=== Secrets Management Best Practices ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # 1. Separate secrets storage from configuration
            print("1. Separate secrets from configuration:")
            
            # Public configuration file
            public_config = {
                'app': {'name': 'ProductionApp', 'debug': False},
                'database': {'host': 'db.example.com', 'port': 5432}
            }
            
            config_file = temp_path / "production.json"
            with open(config_file, 'w') as f:
                json.dump(public_config, f, indent=2)
            
            # Secrets in encrypted storage
            secrets_manager = SecretsManager()
            local_secrets = LocalEncryptedSecrets(
                secrets_file=temp_path / "production_secrets.enc",
                key_file=temp_path / "production_key.bin"
            )
            secrets_manager.add_provider("production", local_secrets)
            
            # 2. Use metadata for secret categorization
            print("2. Categorize secrets with metadata:")
            
            secrets_with_metadata = [
                ('db_master_password', 'super_secure_master_pass', {'tier': 'critical', 'rotation': 'weekly'}),
                ('api_key_payment', 'pk_live_payment_key', {'tier': 'high', 'rotation': 'monthly'}),
                ('monitoring_token', 'mon_token_123', {'tier': 'medium', 'rotation': 'quarterly'}),
                ('cache_password', 'cache_pass_456', {'tier': 'low', 'rotation': 'yearly'})
            ]
            
            for key, value, metadata in secrets_with_metadata:
                secrets_manager.set_secret(key, value, metadata=metadata)
                print(f"  Stored '{key}' with tier: {metadata['tier']}")
            
            # 3. Implement secret rotation schedule
            print("3. Schedule automatic rotation:")
            
            def generate_secure_password():
                """Generate a cryptographically secure password."""
                return python_secrets.token_urlsafe(16)
            
            def generate_api_token():
                """Generate a new API token."""
                return f"token_{python_secrets.token_hex(16)}"
            
            # Schedule rotations based on security tier
            rotation_schedules = [
                ('db_master_password', 168, generate_secure_password),  # Weekly (168 hours)
                ('api_key_payment', 720, generate_api_token),           # Monthly (720 hours)
                ('monitoring_token', 2160, generate_api_token),         # Quarterly (2160 hours)
            ]
            
            for key, hours, generator in rotation_schedules:
                secrets_manager.schedule_rotation(key, hours, generator)
                print(f"  Scheduled '{key}' for rotation every {hours} hours")
            
            # 4. Monitor secret access
            print("4. Monitor secret access patterns:")
            
            access_count = 0
            def log_secret_access(key: str, secret_value):
                nonlocal access_count
                access_count += 1
                print(f"  🔍 Secret '{key}' accessed (total: {access_count})")
            
            secrets_manager.add_refresh_callback(log_secret_access)
            
            # 5. ConfigManager integration with best practices
            print("5. Production ConfigManager setup:")
            
            config_manager = ConfigManager(
                secrets_manager=secrets_manager,
                mask_secrets_in_display=True,  # Always mask in production
                enable_caching=True           # Cache for performance
            )
            
            config_manager.add_source(JsonSource(str(config_file)))
            
            # Access secrets with monitoring
            db_password = config_manager.get_secret('db_master_password')
            api_key = config_manager.get_secret('api_key_payment')
            
            print(f"  Accessed production secrets: {'[SUCCESS]' if db_password and api_key else '[FAILED]'}")
            
            # 6. Security audit information
            print("6. Security audit information:")
            
            for key in ['db_master_password', 'api_key_payment']:
                info = config_manager.get_secret_info(key)
                if info:
                    print(f"  {key}:")
                    print(f"    Security tier: {info['metadata'].get('tier', 'unknown')}")
                    print(f"    Rotation schedule: {info['metadata'].get('rotation', 'none')}")
                    print(f"    Access count: {info['accessed_count']}")
                    print(f"    Last accessed: {info['last_accessed'] or 'never'}")
            
            # 7. Final statistics
            stats = config_manager.get_secrets_stats()
            print(f"\nProduction secrets summary:")
            print(f"  Total secrets: {stats.get('production_secrets_count', 0)}")
            print(f"  Scheduled rotations: {stats['scheduled_rotations']}")
            print(f"  Providers: {stats['providers']}")
            
        except ImportError as e:
            print(f"Skipping best practices demo: {e}")
    
    print()


if __name__ == "__main__":
    print("Configuration Secrets Management Examples")
    print("=" * 50)
    print()
    
    # Run all demonstrations
    demo_local_encrypted_secrets()
    demo_secrets_manager()
    demo_config_manager_with_secrets()
    demo_environment_secrets()
    demo_secrets_best_practices()
    
    print("✅ All secrets management examples completed!")
    print("\n🔐 Key Takeaways:")
    print("   • Use encrypted storage for local secrets")
    print("   • Implement secret rotation schedules") 
    print("   • Monitor secret access patterns")
    print("   • Separate secrets from public configuration")
    print("   • Use metadata for secret categorization")
    print("   • Always mask secrets in logs/display")

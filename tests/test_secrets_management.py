#!/usr/bin/env python3
"""
Tests for secrets management functionality in ConfigManager.

This test suite validates:
- Local encrypted secrets storage
- Secrets manager coordination
- ConfigManager secrets integration
- Secret rotation and callbacks
- Environment variable secrets
"""

import os
import sys
import tempfile
import json
import secrets as python_secrets
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import ConfigManager, SecretsManager, LocalEncryptedSecrets
from config_manager.sources import JsonSource


class TestSecretsIntegration(unittest.TestCase):
    """Test secrets integration with ConfigManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_secrets_storage(self):
        """Test basic secrets storage and retrieval."""
        try:
            # Create local secrets storage
            secrets_file = self.temp_path / "test_secrets.enc"
            key_file = self.temp_path / "test_key.bin"
            
            local_secrets = LocalEncryptedSecrets(
                secrets_file=secrets_file,
                key_file=key_file
            )
            
            # Store a secret
            test_secret = "my_super_secret_value"
            metadata = {"type": "test", "created_by": "unittest"}
            local_secrets.set_secret("test_key", test_secret, metadata)
            
            # Retrieve the secret
            retrieved_secret = local_secrets.get_secret("test_key")
            self.assertIsNotNone(retrieved_secret)
            self.assertEqual(retrieved_secret.get_value(), test_secret)
            self.assertEqual(retrieved_secret.metadata["type"], "test")
            
            # Test listing secrets
            secrets_list = local_secrets.list_secrets()
            self.assertIn("test_key", secrets_list)
            
            print("✅ Basic secrets storage test passed")
            
        except ImportError as e:
            print(f"⚠️  Skipping secrets storage test: {e}")
            self.skipTest("cryptography not available")
    
    def test_secrets_manager_coordination(self):
        """Test SecretsManager with multiple providers."""
        try:
            # Create secrets manager
            secrets_manager = SecretsManager()
            
            # Add local provider
            local_secrets = LocalEncryptedSecrets(
                secrets_file=self.temp_path / "manager_secrets.enc",
                key_file=self.temp_path / "manager_key.bin"
            )
            secrets_manager.add_provider("local", local_secrets)
            
            # Store secrets via manager
            test_secrets = {
                "database_password": "db_secret_123",
                "api_key": "api_key_456",
                "jwt_secret": "jwt_secret_789"
            }
            
            for key, value in test_secrets.items():
                metadata = {"category": "test", "environment": "unittest"}
                secrets_manager.set_secret(key, value, metadata=metadata)
            
            # Retrieve secrets
            for key, expected_value in test_secrets.items():
                retrieved_value = secrets_manager.get_secret(key)
                self.assertEqual(retrieved_value.get_value(), expected_value)
            
            # Test listing
            all_secrets = secrets_manager.list_secrets()
            for key in test_secrets.keys():
                self.assertIn(key, all_secrets)
            
            # Test stats
            stats = secrets_manager.get_stats()
            self.assertIn("local", stats["providers"])
            self.assertEqual(stats["default_provider"], "local")
            
            print("✅ Secrets manager coordination test passed")
            
        except ImportError as e:
            print(f"⚠️  Skipping secrets manager test: {e}")
            self.skipTest("cryptography not available")
    
    def test_config_manager_secrets_integration(self):
        """Test ConfigManager with secrets integration."""
        try:
            # Create configuration file
            public_config = {
                "app": {"name": "TestApp", "version": "1.0"},
                "database": {"host": "localhost", "port": 5432}
            }
            
            config_file = self.temp_path / "test_config.json"
            with open(config_file, 'w') as f:
                json.dump(public_config, f)
            
            # Set up secrets
            local_secrets = LocalEncryptedSecrets(
                secrets_file=self.temp_path / "config_secrets.enc",
                key_file=self.temp_path / "config_key.bin"
            )
            
            secrets_manager = SecretsManager(local_secrets)
            
            # Store sensitive configuration
            sensitive_data = {
                "database_password": "secure_db_pass",
                "api_key": "secure_api_key",
                "jwt_secret": python_secrets.token_urlsafe(32)
            }
            
            for key, value in sensitive_data.items():
                secrets_manager.set_secret(key, value)
            
            # Create ConfigManager with secrets
            config_manager = ConfigManager(
                secrets_manager=secrets_manager,
                mask_secrets_in_display=True
            )
            
            config_manager.add_source(JsonSource(str(config_file)))
            
            # Test public config access
            self.assertEqual(config_manager.get("app.name"), "TestApp")
            self.assertEqual(config_manager.get("database.host"), "localhost")
            
            # Test secrets access
            db_password = config_manager.get_secret("database_password")
            self.assertEqual(db_password, "secure_db_pass")
            
            api_key = config_manager.get_secret("api_key")
            self.assertEqual(api_key, "secure_api_key")
            
            # Test secret info
            secret_info = config_manager.get_secret_info("database_password")
            self.assertIsNotNone(secret_info)
            self.assertEqual(secret_info["key"], "database_password")
            self.assertGreater(secret_info["accessed_count"], 0)
            
            # Test listing secrets
            secrets_list = config_manager.list_secrets()
            for key in sensitive_data.keys():
                self.assertIn(key, secrets_list)
            
            print("✅ ConfigManager secrets integration test passed")
            
        except ImportError as e:
            print(f"⚠️  Skipping ConfigManager secrets test: {e}")
            self.skipTest("cryptography not available")
    
    def test_secret_rotation(self):
        """Test secret rotation functionality."""
        try:
            # Set up secrets manager
            local_secrets = LocalEncryptedSecrets(
                secrets_file=self.temp_path / "rotation_secrets.enc",
                key_file=self.temp_path / "rotation_key.bin"
            )
            
            secrets_manager = SecretsManager(local_secrets)
            config_manager = ConfigManager(secrets_manager=secrets_manager)
            
            # Store initial secret
            initial_secret = "initial_secret_value"
            secrets_manager.set_secret("rotatable_secret", initial_secret)
            
            # Verify initial value
            retrieved_initial = config_manager.get_secret("rotatable_secret")
            self.assertEqual(retrieved_initial, initial_secret)
            
            # Rotate the secret
            new_secret = "rotated_secret_value"
            rotation_success = config_manager.rotate_secret("rotatable_secret", new_secret)
            self.assertTrue(rotation_success)
            
            # Verify new value
            retrieved_rotated = config_manager.get_secret("rotatable_secret")
            self.assertEqual(retrieved_rotated, new_secret)
            self.assertNotEqual(retrieved_rotated, initial_secret)
            
            # Check rotation metadata
            secret_info = config_manager.get_secret_info("rotatable_secret")
            self.assertIn("rotated_at", secret_info["metadata"])
            self.assertEqual(secret_info["metadata"]["rotation_count"], 1)
            
            print("✅ Secret rotation test passed")
            
        except ImportError as e:
            print(f"⚠️  Skipping secret rotation test: {e}")
            self.skipTest("cryptography not available")
    
    def test_secret_callbacks(self):
        """Test secret refresh callbacks."""
        try:
            # Set up secrets manager
            local_secrets = LocalEncryptedSecrets(
                secrets_file=self.temp_path / "callback_secrets.enc",
                key_file=self.temp_path / "callback_key.bin"
            )
            
            secrets_manager = SecretsManager(local_secrets)
            
            # Track callback invocations
            callback_count = 0
            callback_keys = []
            
            def test_callback(key: str, secret_value):
                nonlocal callback_count, callback_keys
                callback_count += 1
                callback_keys.append(key)
            
            secrets_manager.add_refresh_callback(test_callback)
            
            # Store and rotate a secret
            secrets_manager.set_secret("callback_test", "initial_value")
            secrets_manager.rotate_secret("callback_test", "rotated_value")
            
            # Verify callback was invoked
            self.assertGreater(callback_count, 0)
            self.assertIn("callback_test", callback_keys)
            
            print("✅ Secret callbacks test passed")
            
        except ImportError as e:
            print(f"⚠️  Skipping secret callbacks test: {e}")
            self.skipTest("cryptography not available")
    
    def test_environment_secrets_detection(self):
        """Test automatic detection of secrets in environment variables."""
        try:
            from config_manager.sources.secrets_source import EnvironmentSecretsSource
            
            # Set up test environment variables
            test_env_vars = {
                'TEST_DATABASE_PASSWORD': 'env_db_secret',
                'TEST_API_KEY': 'env_api_key',
                'TEST_PUBLIC_CONFIG': 'not_a_secret'
            }
            
            # Temporarily set environment variables
            original_values = {}
            for key, value in test_env_vars.items():
                original_values[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                # Create environment secrets source
                secrets_manager = SecretsManager()
                local_secrets = LocalEncryptedSecrets(
                    secrets_file=self.temp_path / "env_secrets.enc",
                    key_file=self.temp_path / "env_key.bin"
                )
                secrets_manager.add_provider("local", local_secrets)
                
                env_source = EnvironmentSecretsSource(
                    env_prefix='TEST_',
                    secrets_manager=secrets_manager,
                    store_in_secrets=True
                )
                
                # Load environment secrets
                env_config = env_source.load()
                
                # Verify secret detection
                self.assertIn('database_password', env_config)
                self.assertIn('api_key', env_config)
                
                # Verify non-secrets are handled differently
                self.assertIn('public_config', env_config)
                
                # Check that secrets were stored in secrets manager
                stored_secrets = secrets_manager.list_secrets()
                self.assertTrue(any('TEST_DATABASE_PASSWORD' in s for s in stored_secrets))
                self.assertTrue(any('TEST_API_KEY' in s for s in stored_secrets))
                
                print("✅ Environment secrets detection test passed")
                
            finally:
                # Restore original environment variables
                for key, original_value in original_values.items():
                    if original_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = original_value
        
        except ImportError as e:
            print(f"⚠️  Skipping environment secrets test: {e}")
            self.skipTest("Required dependencies not available")
    
    def test_secrets_masking(self):
        """Test secrets masking in configuration display."""
        try:
            # Create configuration with mixed data
            public_config = {
                "app_name": "TestApp",
                "database_host": "localhost",
                "database_password": "should_be_masked",
                "api_key": "should_also_be_masked",
                "public_setting": "visible_value"
            }
            
            # Test masking function
            from config_manager.secrets import mask_sensitive_config
            
            masked_config = mask_sensitive_config(public_config)
            
            # Verify masking
            self.assertEqual(masked_config["app_name"], "TestApp")
            self.assertEqual(masked_config["database_host"], "localhost")
            self.assertEqual(masked_config["public_setting"], "visible_value")
            self.assertEqual(masked_config["database_password"], "[MASKED]")
            self.assertEqual(masked_config["api_key"], "[MASKED]")
            
            # Test nested configuration masking
            nested_config = {
                "database": {
                    "host": "localhost",
                    "password": "secret_password",
                    "credentials": {
                        "username": "admin",
                        "password": "another_secret"
                    }
                },
                "api": {
                    "endpoint": "https://api.example.com",
                    "key": "secret_api_key"
                }
            }
            
            masked_nested = mask_sensitive_config(nested_config)
            
            # Verify nested masking
            self.assertEqual(masked_nested["database"]["host"], "localhost")
            self.assertEqual(masked_nested["database"]["password"], "[MASKED]")
            self.assertEqual(masked_nested["database"]["credentials"]["username"], "admin")
            self.assertEqual(masked_nested["database"]["credentials"]["password"], "[MASKED]")
            self.assertEqual(masked_nested["api"]["endpoint"], "https://api.example.com")
            self.assertEqual(masked_nested["api"]["key"], "[MASKED]")
            
            print("✅ Secrets masking test passed")
            
        except Exception as e:
            print(f"❌ Secrets masking test failed: {e}")
            raise
    
    def test_config_manager_masking_integration(self):
        """Test ConfigManager's built-in secrets masking."""
        try:
            # Create config with sensitive data
            sensitive_config = {
                "app": {"name": "TestApp"},
                "database": {
                    "host": "localhost",
                    "password": "secret_db_password"
                },
                "api_key": "secret_api_key_123"
            }
            
            config_file = self.temp_path / "sensitive_config.json"
            with open(config_file, 'w') as f:
                json.dump(sensitive_config, f)
            
            # Test with masking enabled
            config_manager_masked = ConfigManager(mask_secrets_in_display=True)
            config_manager_masked.add_source(JsonSource(str(config_file)))
            
            masked_config = config_manager_masked.get_config()
            
            # Verify masking in ConfigManager
            self.assertEqual(masked_config["app"]["name"], "TestApp")
            self.assertEqual(masked_config["database"]["host"], "localhost")
            self.assertEqual(masked_config["database"]["password"], "[MASKED]")
            self.assertEqual(masked_config["api_key"], "[MASKED]")
            
            # Test with masking disabled
            config_manager_unmasked = ConfigManager(mask_secrets_in_display=False)
            config_manager_unmasked.add_source(JsonSource(str(config_file)))
            
            unmasked_config = config_manager_unmasked.get_config()
            
            # Verify no masking
            self.assertEqual(unmasked_config["database"]["password"], "secret_db_password")
            self.assertEqual(unmasked_config["api_key"], "secret_api_key_123")
            
            # Test raw config access (always unmasked)
            raw_config = config_manager_masked.get_raw_config()
            self.assertEqual(raw_config["database"]["password"], "secret_db_password")
            self.assertEqual(raw_config["api_key"], "secret_api_key_123")
            
            print("✅ ConfigManager masking integration test passed")
            
        except Exception as e:
            print(f"❌ ConfigManager masking test failed: {e}")
            raise


def run_basic_import_test():
    """Test basic imports work correctly."""
    try:
        from config_manager import SecretsManager, SecretValue, LocalEncryptedSecrets
        from config_manager.secrets import mask_sensitive_config
        print("✅ Basic secrets imports successful")
        return True
    except ImportError as e:
        print(f"❌ Basic secrets imports failed: {e}")
        return False


def run_secrets_tests():
    """Run all secrets tests."""
    print("Running Secrets Management Tests")
    print("=" * 40)
    
    # Test basic imports first
    if not run_basic_import_test():
        print("❌ Basic imports failed - cannot continue with tests")
        return False
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_basic_secrets_storage',
        'test_secrets_manager_coordination', 
        'test_config_manager_secrets_integration',
        'test_secret_rotation',
        'test_secret_callbacks',
        'test_environment_secrets_detection',
        'test_secrets_masking',
        'test_config_manager_masking_integration'
    ]
    
    for method in test_methods:
        suite.addTest(TestSecretsIntegration(method))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print(f"\n{'='*40}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(getattr(result, 'skipped', []))}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🎯 Overall result: {'SUCCESS' if success else 'FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_secrets_tests()
    sys.exit(0 if success else 1)

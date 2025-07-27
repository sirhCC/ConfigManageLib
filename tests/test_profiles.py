"""
Tests for configuration profiles and environment management.
"""

import unittest
import tempfile
import json
import os
import shutil
from pathlib import Path
from config_manager import ConfigManager
from config_manager.profiles import ProfileManager, ConfigProfile, create_profile_source_path, profile_source_exists
from config_manager.sources import JsonSource, YamlSource


class TestConfigProfile(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_profile_creation(self):
        """Test basic profile creation."""
        profile = ConfigProfile('development')
        self.assertEqual(profile.name, 'development')
        self.assertIsNone(profile.base_profile)
        self.assertEqual(profile.sources, [])
        self.assertEqual(profile.profile_vars, {})
    
    def test_profile_with_base(self):
        """Test profile creation with base profile."""
        base = ConfigProfile('base')
        base.set_var('timeout', 30)
        
        dev = ConfigProfile('development', base_profile=base)
        self.assertEqual(dev.base_profile, base)
        self.assertEqual(dev.get_var('timeout'), 30)  # Inherited from base
    
    def test_profile_variable_inheritance(self):
        """Test variable inheritance from base profiles."""
        base = ConfigProfile('base')
        base.set_var('timeout', 30)
        base.set_var('debug', False)
        
        dev = ConfigProfile('development', base_profile=base)
        dev.set_var('debug', True)  # Override base value
        dev.set_var('log_level', 'DEBUG')  # New value
        
        # Check inherited value
        self.assertEqual(dev.get_var('timeout'), 30)
        
        # Check overridden value
        self.assertEqual(dev.get_var('debug'), True)
        
        # Check new value
        self.assertEqual(dev.get_var('log_level'), 'DEBUG')
        
        # Check default value
        self.assertEqual(dev.get_var('nonexistent', 'default'), 'default')
    
    def test_profile_source_inheritance(self):
        """Test source inheritance from base profiles."""
        base = ConfigProfile('base')
        base.add_source('base_source')
        
        dev = ConfigProfile('development', base_profile=base)
        dev.add_source('dev_source')
        
        all_sources = dev.get_all_sources()
        self.assertEqual(all_sources, ['base_source', 'dev_source'])


class TestProfileManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ProfileManager()
        # Store original environment variables
        self.original_env = {}
        for var in ProfileManager.ENV_VARS:
            self.original_env[var] = os.environ.get(var)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
    
    def test_default_profiles_exist(self):
        """Test that default profiles are created."""
        expected_profiles = ['base', 'development', 'testing', 'staging', 'production']
        
        for profile_name in expected_profiles:
            profile = self.manager.get_profile(profile_name)
            self.assertIsNotNone(profile, f"Profile '{profile_name}' should exist")
            self.assertEqual(profile.name, profile_name)
    
    def test_profile_aliases(self):
        """Test profile name aliases."""
        test_cases = {
            'dev': 'development',
            'develop': 'development',
            'local': 'development',
            'test': 'testing',
            'stage': 'staging',
            'prod': 'production'
        }
        
        for alias, expected in test_cases.items():
            profile = self.manager.get_profile(alias)
            self.assertIsNotNone(profile)
            self.assertEqual(profile.name, expected)
    
    def test_environment_detection(self):
        """Test automatic environment detection."""
        test_cases = [
            ('ENVIRONMENT', 'production', 'production'),
            ('ENV', 'dev', 'development'),  # Alias resolution
            ('NODE_ENV', 'staging', 'staging'),
            ('PYTHON_ENV', 'test', 'testing'),  # Alias resolution
            ('CONFIG_ENV', 'custom', 'custom'),  # Unknown environment
        ]
        
        for env_var, env_value, expected in test_cases:
            # Clear all environment variables
            for var in ProfileManager.ENV_VARS:
                os.environ.pop(var, None)
            
            # Set specific environment variable
            os.environ[env_var] = env_value
            
            detected = self.manager.detect_environment()
            self.assertEqual(detected, expected, 
                f"ENV {env_var}={env_value} should detect '{expected}', got '{detected}'")
    
    def test_environment_detection_default(self):
        """Test environment detection with no environment variables set."""
        # Clear all environment variables
        for var in ProfileManager.ENV_VARS:
            os.environ.pop(var, None)
        
        detected = self.manager.detect_environment()
        self.assertEqual(detected, 'development')
    
    def test_custom_profile_creation(self):
        """Test creating custom profiles."""
        # Create custom profile
        custom = self.manager.create_profile('custom')
        self.assertEqual(custom.name, 'custom')
        self.assertIsNone(custom.base_profile)
        
        # Create profile with base
        custom_with_base = self.manager.create_profile('custom_base', 'development')
        self.assertEqual(custom_with_base.name, 'custom_base')
        self.assertIsNotNone(custom_with_base.base_profile)
        self.assertEqual(custom_with_base.base_profile.name, 'development')
    
    def test_active_profile_management(self):
        """Test setting and getting active profiles."""
        # Initially no active profile
        self.assertIsNone(self.manager.active_profile)
        
        # Set active profile
        self.manager.set_active_profile('production')
        self.assertEqual(self.manager.active_profile, 'production')
        
        # Test case insensitive
        self.manager.set_active_profile('STAGING')
        self.assertEqual(self.manager.active_profile, 'staging')
        
        # Test alias resolution
        self.manager.set_active_profile('prod')
        self.assertEqual(self.manager.active_profile, 'production')
    
    def test_invalid_profile_operations(self):
        """Test error handling for invalid profile operations."""
        # Setting non-existent profile as active
        with self.assertRaises(ValueError):
            self.manager.set_active_profile('nonexistent')
        
        # Creating profile with non-existent base
        with self.assertRaises(ValueError):
            self.manager.create_profile('test', 'nonexistent_base')
    
    def test_profile_variables(self):
        """Test profile variable access through manager."""
        # Test default profile variables
        debug_val = self.manager.get_profile_var('debug', 'development')
        self.assertTrue(debug_val)
        
        debug_val_prod = self.manager.get_profile_var('debug', 'production')
        self.assertFalse(debug_val_prod)
        
        # Test with active profile
        self.manager.set_active_profile('development')
        debug_val_active = self.manager.get_profile_var('debug')
        self.assertTrue(debug_val_active)


class TestProfileUtils(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_profile_source_path_directory(self):
        """Test profile path creation for directories."""
        # Directory path
        result = create_profile_source_path('config', 'development')
        self.assertEqual(result, 'config/development.json')
        
        result = create_profile_source_path('config', 'production', 'yaml')
        self.assertEqual(result, 'config/production.yaml')
    
    def test_create_profile_source_path_file(self):
        """Test profile path creation for files."""
        # File path with extension
        result = create_profile_source_path('app.json', 'development')
        self.assertEqual(result, 'app.development.json')
        
        result = create_profile_source_path('config.yaml', 'staging')
        self.assertEqual(result, 'config.staging.yaml')
        
        # File path without extension
        result = create_profile_source_path('config', 'test', 'toml')
        self.assertEqual(result, 'config.test.toml')
    
    def test_profile_source_exists(self):
        """Test checking if profile sources exist."""
        # Create test files
        config_dir = Path(self.temp_dir) / 'config'
        config_dir.mkdir()
        
        dev_file = config_dir / 'development.json'
        dev_file.write_text('{}')
        
        # Test existing file
        self.assertTrue(profile_source_exists(config_dir, 'development'))
        
        # Test non-existing file
        self.assertFalse(profile_source_exists(config_dir, 'production'))


class TestConfigManagerProfiles(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Store original environment variables
        self.original_env = {}
        for var in ProfileManager.ENV_VARS:
            self.original_env[var] = os.environ.get(var)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
    
    def test_config_manager_auto_profile_detection(self):
        """Test ConfigManager automatically detects environment."""
        # Set environment variable
        os.environ['ENVIRONMENT'] = 'production'
        
        config = ConfigManager()
        self.assertEqual(config.get_current_profile(), 'production')
    
    def test_config_manager_explicit_profile(self):
        """Test ConfigManager with explicitly set profile."""
        config = ConfigManager(profile='staging')
        self.assertEqual(config.get_current_profile(), 'staging')
    
    def test_config_manager_profile_switching(self):
        """Test switching profiles in ConfigManager."""
        config = ConfigManager(profile='development')
        self.assertEqual(config.get_current_profile(), 'development')
        
        # Switch profile
        config.set_profile('production')
        self.assertEqual(config.get_current_profile(), 'production')
    
    def test_config_manager_profile_variables(self):
        """Test accessing profile variables through ConfigManager."""
        config = ConfigManager(profile='development')
        
        # Get profile variable
        debug = config.get_profile_var('debug')
        self.assertTrue(debug)
        
        # Switch profile and check variable
        config.set_profile('production')
        debug_prod = config.get_profile_var('debug')
        self.assertFalse(debug_prod)
    
    def test_config_manager_profile_sources(self):
        """Test adding profile-specific sources."""
        # Create test configuration files
        config_dir = Path(self.temp_dir) / 'config'
        config_dir.mkdir()
        
        # Development config
        dev_config = {'app': {'name': 'DevApp', 'debug': True}}
        (config_dir / 'development.json').write_text(json.dumps(dev_config))
        
        # Production config
        prod_config = {'app': {'name': 'ProdApp', 'debug': False}}
        (config_dir / 'production.json').write_text(json.dumps(prod_config))
        
        # Test development profile
        config = ConfigManager(profile='development')
        config.add_profile_source(config_dir)
        
        self.assertEqual(config.get('app.name'), 'DevApp')
        self.assertTrue(config.get_bool('app.debug'))
        
        # Switch to production profile
        config.set_profile('production')
        config.add_profile_source(config_dir)
        
        self.assertEqual(config.get('app.name'), 'ProdApp')
        self.assertFalse(config.get_bool('app.debug'))
    
    def test_config_manager_profile_sources_with_fallback(self):
        """Test profile sources with fallback to base configuration."""
        # Create test configuration files
        config_dir = Path(self.temp_dir) / 'config'
        config_dir.mkdir()
        
        # Base config (fallback)
        base_config = {'app': {'name': 'BaseApp', 'version': '1.0.0'}}
        (config_dir / 'base.json').write_text(json.dumps(base_config))
        
        # Only development config exists
        dev_config = {'app': {'name': 'DevApp', 'debug': True}}
        (config_dir / 'development.json').write_text(json.dumps(dev_config))
        
        # Test development profile (specific config exists)
        config = ConfigManager(profile='development')
        config.add_profile_source(config_dir, fallback_to_base=True)
        
        self.assertEqual(config.get('app.name'), 'DevApp')
        
        # Test staging profile (should fall back to base)
        config = ConfigManager(profile='staging')
        config.add_profile_source(config_dir, fallback_to_base=True)
        
        self.assertEqual(config.get('app.name'), 'BaseApp')
        self.assertEqual(config.get('app.version'), '1.0.0')
    
    def test_config_manager_profile_list(self):
        """Test listing available profiles."""
        config = ConfigManager()
        profiles = config.list_profiles()
        
        expected_profiles = ['base', 'development', 'testing', 'staging', 'production']
        for profile in expected_profiles:
            self.assertIn(profile, profiles)
    
    def test_config_manager_custom_profile(self):
        """Test creating and using custom profiles."""
        config = ConfigManager(profile='development')
        
        # Create custom profile
        custom = config.create_profile('integration', 'staging')
        custom.set_var('integration_test', True)
        
        # Switch to custom profile
        config.set_profile('integration')
        
        # Should inherit from staging profile
        self.assertFalse(config.get_profile_var('debug'))  # From staging
        self.assertTrue(config.get_profile_var('integration_test'))  # Custom variable
    
    def test_config_manager_disable_auto_detect(self):
        """Test disabling automatic profile detection."""
        # Set environment variable
        os.environ['ENVIRONMENT'] = 'production'
        
        # Create with auto-detection disabled
        config = ConfigManager(auto_detect_profile=False)
        self.assertIsNone(config.get_current_profile())
        
        # Create with explicit profile and auto-detection disabled
        config = ConfigManager(profile='development', auto_detect_profile=False)
        self.assertEqual(config.get_current_profile(), 'development')


if __name__ == '__main__':
    unittest.main()

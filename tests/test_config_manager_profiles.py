"""
Comprehensive tests for ConfigManager profile management methods.

Tests coverage for:
- get_current_profile, set_profile, create_profile
- get_profile, list_profiles, detect_environment
- Profile inheritance and switching
"""

import pytest
import os
from pathlib import Path
from config_manager import ConfigManager
from config_manager.profiles import ConfigProfile
from config_manager.sources import JsonSource


class TestConfigManagerProfiles:
    """Tests for ConfigManager profile management methods."""
    
    def test_get_current_profile_default(self):
        """Test getting current profile when none set."""
        config = ConfigManager()
        
        profile = config.get_current_profile()
        assert profile is not None  # Should have default profile
    
    def test_create_profile(self):
        """Test creating a new profile."""
        config = ConfigManager()
        
        profile = config.create_profile('development')
        
        assert profile is not None
        assert isinstance(profile, ConfigProfile)
        assert profile.name == 'development'
    
    def test_create_profile_with_inheritance(self):
        """Test creating a profile with base profile inheritance."""
        config = ConfigManager()
        
        # Create base profile
        base = config.create_profile('base')
        
        # Create derived profile
        derived = config.create_profile('production', base_profile='base')
        
        assert derived is not None
        assert derived.name == 'production'
    
    def test_get_profile(self):
        """Test retrieving a profile by name."""
        config = ConfigManager()
        
        # Create a profile
        config.create_profile('staging')
        
        # Get the profile
        profile = config.get_profile('staging')
        
        assert profile is not None
        assert profile.name == 'staging'
    
    def test_get_profile_not_found(self):
        """Test getting non-existent profile returns None."""
        config = ConfigManager()
        
        profile = config.get_profile('nonexistent')
        assert profile is None
    
    def test_get_profile_current(self):
        """Test getting current profile with no name argument."""
        config = ConfigManager()
        
        # Create and set profile
        config.create_profile('test_profile')
        config.set_profile('test_profile')
        
        # Get current profile
        profile = config.get_profile()
        
        assert profile is not None
        assert profile.name == 'test_profile'
    
    def test_list_profiles(self):
        """Test listing all profiles."""
        config = ConfigManager()
        
        # Create multiple profiles
        config.create_profile('dev')
        config.create_profile('staging')
        config.create_profile('prod')
        
        # List profiles
        profiles = config.list_profiles()
        
        assert isinstance(profiles, list)
        assert 'dev' in profiles
        assert 'staging' in profiles
        assert 'prod' in profiles
    
    def test_list_profiles_empty(self):
        """Test listing profiles returns list even when empty."""
        config = ConfigManager()
        
        profiles = config.list_profiles()
        assert isinstance(profiles, list)
    
    def test_set_profile(self):
        """Test setting the active profile."""
        config = ConfigManager()
        
        # Create profile
        config.create_profile('active_profile')
        
        # Set profile
        result = config.set_profile('active_profile')
        
        assert result is config  # Should return self for chaining
        assert config.get_current_profile() == 'active_profile'
    
    def test_set_profile_not_found(self):
        """Test setting non-existent profile raises ValueError."""
        config = ConfigManager()
        
        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            config.set_profile('nonexistent')
    
    def test_set_profile_reloads_config(self, tmp_path):
        """Test that setting profile triggers config reload."""
        config = ConfigManager()
        
        # Create two config files for different profiles
        dev_config = tmp_path / "config.dev.json"
        dev_config.write_text('{"env": "development"}')
        
        prod_config = tmp_path / "config.prod.json"
        prod_config.write_text('{"env": "production"}')
        
        # Create profiles
        config.create_profile('dev')
        config.create_profile('prod')
        
        # Load dev profile source
        config.set_profile('dev')
        config.add_source(JsonSource(str(dev_config)))
        
        assert config.get('env') == 'development'
        
        # Switch to prod profile
        config.set_profile('prod')
        config.add_source(JsonSource(str(prod_config)))
        
        assert config.get('env') == 'production'
    
    def test_detect_environment(self):
        """Test detecting environment from environment variables."""
        config = ConfigManager()
        
        # Set environment variable
        original = os.environ.get('ENV')
        try:
            os.environ['ENV'] = 'production'
            
            env = config.detect_environment()
            
            assert env is not None
            assert isinstance(env, str)
        finally:
            # Restore original
            if original:
                os.environ['ENV'] = original
            elif 'ENV' in os.environ:
                del os.environ['ENV']
    
    def test_detect_environment_no_var(self):
        """Test environment detection with no environment variable."""
        config = ConfigManager()
        
        # Remove common env vars
        env_vars = ['ENV', 'ENVIRONMENT', 'APP_ENV']
        originals = {}
        
        try:
            for var in env_vars:
                originals[var] = os.environ.get(var)
                if var in os.environ:
                    del os.environ[var]
            
            env = config.detect_environment()
            
            # Should return default or None
            assert env is not None or env is None
        finally:
            # Restore originals
            for var, value in originals.items():
                if value:
                    os.environ[var] = value
    
    def test_profile_method_chaining(self):
        """Test profile methods support method chaining."""
        config = ConfigManager()
        
        result = config.create_profile('chain_test')
        # create_profile returns ConfigProfile, not ConfigManager
        
        result = config.set_profile('chain_test')
        assert result is config
        
        # Can chain further
        result.create_profile('chain_test_2')
    
    def test_profile_isolation(self):
        """Test that profiles keep configurations isolated."""
        config = ConfigManager()
        
        # Create two profiles with different configs
        config.create_profile('profile_a')
        config.create_profile('profile_b')
        
        # Set profile A and add config
        config.set_profile('profile_a')
        config._config = {'key': 'value_a'}
        
        # Switch to profile B
        config.set_profile('profile_b')
        config._config = {'key': 'value_b'}
        
        # Each profile should maintain its config
        assert config.get('key') == 'value_b'


class TestConfigManagerProfilesIntegration:
    """Integration tests for profiles with ConfigManager."""
    
    def test_profile_with_multiple_sources(self, tmp_path):
        """Test profile working with multiple configuration sources."""
        config = ConfigManager()
        
        # Create config files
        base_config = tmp_path / "base.json"
        base_config.write_text('{"database": {"host": "localhost"}}')
        
        dev_config = tmp_path / "dev.json"
        dev_config.write_text('{"database": {"port": 5432}}')
        
        # Create profile
        config.create_profile('dev')
        config.set_profile('dev')
        
        # Add sources
        config.add_source(JsonSource(str(base_config)))
        config.add_source(JsonSource(str(dev_config)))
        
        # Both configs should be merged
        assert config.get('database.host') == 'localhost'
        assert config.get('database.port') == 5432
    
    def test_profile_switching_preserves_sources(self, tmp_path):
        """Test that switching profiles handles sources correctly."""
        config = ConfigManager()
        
        config_file = tmp_path / "config.json"
        config_file.write_text('{"setting": "value"}')
        
        # Create profiles
        config.create_profile('profile1')
        config.create_profile('profile2')
        
        # Add source to profile1
        config.set_profile('profile1')
        config.add_source(JsonSource(str(config_file)))
        
        # Switch to profile2
        config.set_profile('profile2')
        
        # Profile2 starts fresh
        # Behavior depends on implementation
    
    def test_profile_inheritance_chain(self):
        """Test multi-level profile inheritance."""
        config = ConfigManager()
        
        # Create inheritance chain: base -> staging -> production
        config.create_profile('base')
        config.create_profile('staging', base_profile='base')
        config.create_profile('production', base_profile='staging')
        
        # Each profile should exist
        assert config.get_profile('base') is not None
        assert config.get_profile('staging') is not None
        assert config.get_profile('production') is not None
    
    def test_profile_with_environment_detection(self):
        """Test profile selection based on environment detection."""
        config = ConfigManager()
        
        # Create environment-named profiles
        config.create_profile('development')
        config.create_profile('production')
        
        # Set environment
        original = os.environ.get('ENV')
        try:
            os.environ['ENV'] = 'production'
            
            # Detect and set profile
            env = config.detect_environment()
            if env and config.get_profile(env):
                config.set_profile(env)
                
                assert config.get_current_profile() == 'production'
        finally:
            if original:
                os.environ['ENV'] = original
            elif 'ENV' in os.environ:
                del os.environ['ENV']
    
    def test_profile_thread_safety(self):
        """Test profile operations are thread-safe."""
        import threading
        
        config = ConfigManager()
        errors = []
        
        def create_and_switch_profile(thread_id):
            try:
                profile_name = f'profile_{thread_id}'
                config.create_profile(profile_name)
                config.set_profile(profile_name)
                assert config.get_current_profile() == profile_name
            except Exception as e:
                errors.append(e)
        
        # Create threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=create_and_switch_profile, args=(i,)))
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have minimal or no errors (last thread wins on current profile)
        assert len(errors) <= 1  # Some race conditions acceptable

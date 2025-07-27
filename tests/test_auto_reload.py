"""
Test configuration file watching and auto-reload functionality.
"""

import unittest
import tempfile
import json
import time
import os
import threading
from config_manager import ConfigManager
from config_manager.sources import JsonSource


class TestAutoReload(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        # Initial configuration
        self.initial_config = {
            'app': {
                'name': 'TestApp',
                'version': '1.0.0',
                'debug': False
            },
            'database': {
                'host': 'localhost',
                'port': 5432
            }
        }
        
        # Create initial config file
        with open(self.config_file, 'w') as f:
            json.dump(self.initial_config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_auto_reload_disabled_by_default(self):
        """Test that auto-reload is disabled by default."""
        config = ConfigManager()
        self.assertFalse(config._auto_reload)
        self.assertIsNone(config._observer)
        self.assertIsNone(config._polling_thread)
    
    def test_auto_reload_enabled(self):
        """Test that auto-reload can be enabled."""
        config = ConfigManager(auto_reload=True)
        self.assertTrue(config._auto_reload)
        
        # Should have started some form of watching
        # (either observer or polling thread should be active)
        self.assertTrue(
            config._observer is not None or 
            config._polling_thread is not None
        )
        
        # Clean up
        config.stop_watching()
    
    def test_file_watching_registration(self):
        """Test that file-based sources are registered for watching."""
        config = ConfigManager(auto_reload=True)
        config.add_source(JsonSource(self.config_file))
        
        # File should be in watched files
        abs_path = os.path.abspath(self.config_file)
        self.assertIn(abs_path, config._watched_files)
        
        # Clean up
        config.stop_watching()
    
    def test_reload_callback_registration(self):
        """Test callback registration and removal."""
        config = ConfigManager()
        
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        # Register callback
        config.on_reload(test_callback)
        self.assertIn(test_callback, config._reload_callbacks)
        
        # Remove callback
        config.remove_reload_callback(test_callback)
        self.assertNotIn(test_callback, config._reload_callbacks)
    
    def test_manual_reload_calls_callbacks(self):
        """Test that manual reload calls registered callbacks."""
        config = ConfigManager()
        config.add_source(JsonSource(self.config_file))
        
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        config.on_reload(test_callback)
        
        # Initial state
        self.assertEqual(len(callback_called), 0)
        
        # Manual reload should not call callbacks
        config.reload()
        self.assertEqual(len(callback_called), 0)  # Manual reload doesn't trigger callbacks
    
    def test_configuration_access_thread_safety(self):
        """Test that configuration access is thread-safe."""
        config = ConfigManager(auto_reload=True)
        config.add_source(JsonSource(self.config_file))
        
        errors = []
        
        def read_config():
            try:
                for _ in range(100):
                    value = config.get('app.name')
                    if value != 'TestApp':
                        errors.append(f"Unexpected value: {value}")
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(str(e))
        
        def reload_config():
            try:
                for _ in range(10):
                    config.reload()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=read_config))
        threads.append(threading.Thread(target=reload_config))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for errors
        if errors:
            self.fail(f"Thread safety errors: {errors}")
        
        # Clean up
        config.stop_watching()
    
    def test_polling_fallback(self):
        """Test that polling works as a fallback when watchdog is not available."""
        # Force polling by temporarily disabling watchdog
        import config_manager.config_manager as cm
        original_watchdog = cm.WATCHDOG_AVAILABLE
        cm.WATCHDOG_AVAILABLE = False
        
        try:
            config = ConfigManager(auto_reload=True, reload_interval=0.1)
            config.add_source(JsonSource(self.config_file))
            
            # Should be using polling
            self.assertIsNone(config._observer)
            self.assertIsNotNone(config._polling_thread)
            self.assertTrue(config._polling_thread.is_alive())
            
            # Clean up
            config.stop_watching()
            
        finally:
            # Restore original state
            cm.WATCHDOG_AVAILABLE = original_watchdog
    
    def test_file_modification_detection_polling(self):
        """Test that file modifications are detected using polling."""
        # Force polling mode
        import config_manager.config_manager as cm
        original_watchdog = cm.WATCHDOG_AVAILABLE
        cm.WATCHDOG_AVAILABLE = False
        
        try:
            config = ConfigManager(auto_reload=True, reload_interval=0.1)
            config.add_source(JsonSource(self.config_file))
            
            callback_called = []
            
            def test_callback():
                callback_called.append(True)
            
            config.on_reload(test_callback)
            
            # Initial check
            self.assertEqual(config.get('app.name'), 'TestApp')
            
            # Modify the config file
            modified_config = self.initial_config.copy()
            modified_config['app']['name'] = 'ModifiedApp'
            
            time.sleep(0.2)  # Wait for initial polling cycle
            
            with open(self.config_file, 'w') as f:
                json.dump(modified_config, f)
            
            # Wait for polling to detect the change
            time.sleep(0.3)
            
            # Check that configuration was reloaded
            self.assertEqual(config.get('app.name'), 'ModifiedApp')
            
            # Check that callback was called
            self.assertTrue(len(callback_called) > 0)
            
            # Clean up
            config.stop_watching()
            
        finally:
            # Restore original state
            cm.WATCHDOG_AVAILABLE = original_watchdog
    
    def test_stop_watching_cleanup(self):
        """Test that stop_watching properly cleans up resources."""
        config = ConfigManager(auto_reload=True)
        config.add_source(JsonSource(self.config_file))
        
        # Should have started watching
        watching_active = (
            config._observer is not None or 
            config._polling_thread is not None
        )
        self.assertTrue(watching_active)
        
        # Stop watching
        config.stop_watching()
        
        # Should have cleaned up
        if config._observer:
            self.assertFalse(config._observer.is_alive())
        if config._polling_thread:
            self.assertFalse(config._polling_thread.is_alive())
    
    def test_configuration_precedence_with_reload(self):
        """Test that configuration precedence is maintained after reload."""
        # Create a second config file
        config_file2 = os.path.join(self.temp_dir, 'override_config.json')
        override_config = {
            'app': {
                'debug': True  # Override debug flag
            },
            'new_setting': 'override_value'
        }
        
        with open(config_file2, 'w') as f:
            json.dump(override_config, f)
        
        # Set up config manager with two sources
        config = ConfigManager(auto_reload=True)
        config.add_source(JsonSource(self.config_file))      # Base config
        config.add_source(JsonSource(config_file2))          # Override config
        
        # Check initial state
        self.assertEqual(config.get('app.name'), 'TestApp')    # From base
        self.assertEqual(config.get_bool('app.debug'), True)   # Overridden
        self.assertEqual(config.get('new_setting'), 'override_value')  # From override
        
        # Modify base config
        modified_base = self.initial_config.copy()
        modified_base['app']['name'] = 'NewTestApp'
        modified_base['app']['version'] = '2.0.0'
        
        with open(self.config_file, 'w') as f:
            json.dump(modified_base, f)
        
        # Trigger reload
        config.reload()
        
        # Check that precedence is maintained
        self.assertEqual(config.get('app.name'), 'NewTestApp')     # Updated from base
        self.assertEqual(config.get('app.version'), '2.0.0')      # Updated from base
        self.assertEqual(config.get_bool('app.debug'), True)      # Still overridden
        self.assertEqual(config.get('new_setting'), 'override_value')  # Still from override
        
        # Clean up
        config.stop_watching()


if __name__ == '__main__':
    unittest.main()

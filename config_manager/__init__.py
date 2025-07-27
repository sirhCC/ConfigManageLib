"""
A modern and extensible configuration management library for Python.
"""

from .config_manager import ConfigManager
from .profiles import ProfileManager, ConfigProfile, create_profile_source_path, profile_source_exists

__all__ = ["ConfigManager", "ProfileManager", "ConfigProfile", "create_profile_source_path", "profile_source_exists"]

#!/usr/bin/env python3
"""
Setup script for ConfigManager - Enterprise Configuration Management Library

This setup.py provides backward compatibility for older Python versions
and build systems that don't support pyproject.toml.
"""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read long description from README
def read_long_description():
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Enterprise-grade configuration management library for Python"

# Read requirements
def read_requirements(filename):
    req_path = Path(__file__).parent / filename
    if req_path.exists():
        with open(req_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

setup(
    name="configmanagelib",
    version="0.1.0",
    description="A modern, flexible, and type-safe configuration management library for Python",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author="ConfigManageLib Team",
    author_email="info@example.com",
    url="https://github.com/sirhCC/ConfigManageLib",
    project_urls={
        "Homepage": "https://github.com/sirhCC/ConfigManageLib",
        "Bug Tracker": "https://github.com/sirhCC/ConfigManageLib/issues",
        "Documentation": "https://github.com/sirhCC/ConfigManageLib/tree/main/docs",
        "Source Code": "https://github.com/sirhCC/ConfigManageLib",
    },
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "mypy>=0.900",
            "black>=21.0.0",
            "isort>=5.0.0",
            "flake8>=3.8.0",
            "pre-commit>=2.10.0",
        ],
        "yaml": ["PyYAML>=6.0"],
        "toml": ["tomli>=1.2.0; python_version<'3.11'"],
        "encryption": ["cryptography>=3.4.8"],
        "vault": ["requests>=2.25.0"],
        "azure": [
            "azure-keyvault-secrets>=4.2.0",
            "azure-identity>=1.5.0",
        ],
        "monitoring": ["psutil>=5.8.0"],
        "watch": ["watchdog>=2.1.0"],
        "full": [
            "PyYAML>=6.0",
            "tomli>=1.2.0; python_version<'3.11'",
            "cryptography>=3.4.8",
            "requests>=2.25.0",
            "azure-keyvault-secrets>=4.2.0",
            "azure-identity>=1.5.0",
            "psutil>=5.8.0",
            "watchdog>=2.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
    keywords=[
        "configuration", "config", "settings", "environment",
        "yaml", "json", "toml", "ini", "enterprise",
        "validation", "schema", "secrets", "cache",
        "profiles", "reload", "type-safe"
    ],
    license="MIT",
    zip_safe=False,
    entry_points={
        "console_scripts": [
            # Future CLI entry points
            # "configmanager=config_manager.cli:main",
        ],
    },
)

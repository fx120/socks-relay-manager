"""
Tests for project setup and structure.
"""

import pytest
import sys
from pathlib import Path


def test_python_version():
    """Test that Python version is 3.9 or higher (3.11+ recommended for production)."""
    assert sys.version_info >= (3, 9), "Python 3.9+ is required (3.11+ recommended)"


def test_package_imports():
    """Test that the main package can be imported."""
    import proxy_relay
    assert proxy_relay.__version__ == "0.1.0"


def test_cli_module_exists():
    """Test that CLI module exists and can be imported."""
    from proxy_relay import cli
    assert hasattr(cli, 'main')


def test_project_structure():
    """Test that basic project structure exists."""
    project_root = Path(__file__).parent.parent
    
    # Check essential files
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "config.yaml.example").exists()
    
    # Check source directory
    assert (project_root / "src" / "proxy_relay").exists()
    assert (project_root / "src" / "proxy_relay" / "__init__.py").exists()
    assert (project_root / "src" / "proxy_relay" / "cli.py").exists()
    
    # Check tests directory
    assert (project_root / "tests").exists()
    assert (project_root / "tests" / "__init__.py").exists()
    assert (project_root / "tests" / "conftest.py").exists()


def test_config_example_is_valid_yaml():
    """Test that the example config file is valid YAML."""
    import yaml
    project_root = Path(__file__).parent.parent
    config_file = project_root / "config.yaml.example"
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check essential sections exist
    assert 'system' in config
    assert 'monitoring' in config
    assert 'api_providers' in config
    assert 'proxies' in config


def test_temp_directories_fixture(temp_dir, config_dir, data_dir, log_dir):
    """Test that pytest fixtures create temporary directories."""
    assert temp_dir.exists()
    assert config_dir.exists()
    assert data_dir.exists()
    assert log_dir.exists()
    
    # Verify they are subdirectories of temp_dir
    assert config_dir.parent == temp_dir
    assert data_dir.parent == temp_dir
    assert log_dir.parent == temp_dir

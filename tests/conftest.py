"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_dir(temp_dir):
    """Create a temporary config directory."""
    config_path = temp_dir / "config"
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path


@pytest.fixture
def data_dir(temp_dir):
    """Create a temporary data directory."""
    data_path = temp_dir / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


@pytest.fixture
def log_dir(temp_dir):
    """Create a temporary log directory."""
    log_path = temp_dir / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path

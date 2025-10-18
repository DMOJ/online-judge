"""
Shared pytest fixtures and configuration for DMOJ tests.

This module contains fixtures that are available to all test modules.
"""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Provide a temporary directory that is cleaned up after the test.

    Yields:
        Path: A pathlib.Path object pointing to the temporary directory.

    Example:
        def test_file_creation(temp_dir):
            test_file = temp_dir / "test.txt"
            test_file.write_text("hello")
            assert test_file.read_text() == "hello"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """
    Provide a temporary file that is cleaned up after the test.

    Yields:
        Path: A pathlib.Path object pointing to the temporary file.

    Example:
        def test_file_write(temp_file):
            temp_file.write_text("test content")
            assert temp_file.exists()
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def sample_dict():
    """
    Provide a sample dictionary for testing.

    Returns:
        dict: A sample dictionary with various data types.
    """
    return {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "boolean": True,
        "none": None,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }


@pytest.fixture
def sample_list():
    """
    Provide a sample list for testing.

    Returns:
        list: A sample list with various items.
    """
    return [1, 2, 3, "four", 5.0, {"key": "value"}]


@pytest.fixture
def mock_env(monkeypatch):
    """
    Provide a way to temporarily set environment variables.

    Args:
        monkeypatch: pytest's monkeypatch fixture.

    Returns:
        function: A function to set temporary environment variables.

    Example:
        def test_with_env_var(mock_env):
            mock_env(MY_VAR="test_value")
            assert os.environ["MY_VAR"] == "test_value"
    """
    def _mock_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)

    return _mock_env


@pytest.fixture(autouse=True)
def reset_test_environment():
    """
    Automatically reset the test environment before each test.

    This fixture runs before every test to ensure a clean state.
    """
    # Setup: runs before each test
    yield
    # Teardown: runs after each test
    # Add any cleanup code here if needed

"""
Validation tests to verify testing infrastructure setup.

These tests ensure that the testing framework is properly configured
and all fixtures are working as expected.
"""
import os
import sys
from pathlib import Path

import pytest


class TestInfrastructure:
    """Test suite to validate the testing infrastructure."""

    def test_pytest_is_working(self):
        """Verify that pytest is installed and working."""
        assert True

    def test_python_version(self):
        """Verify Python version is 3.8 or higher."""
        assert sys.version_info >= (3, 8), f"Python version is {sys.version_info}"

    def test_project_root_exists(self):
        """Verify that the project root directory exists."""
        project_root = Path(__file__).parent.parent
        assert project_root.exists()
        assert (project_root / "pyproject.toml").exists()

    def test_test_directories_exist(self):
        """Verify that test directories are properly created."""
        tests_dir = Path(__file__).parent
        assert (tests_dir / "unit").exists()
        assert (tests_dir / "integration").exists()
        assert (tests_dir / "conftest.py").exists()


class TestFixtures:
    """Test suite to validate pytest fixtures."""

    def test_temp_dir_fixture(self, temp_dir):
        """Verify temp_dir fixture creates a temporary directory."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

        # Test writing to the temp directory
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")
        assert test_file.read_text() == "Hello, World!"

    def test_temp_file_fixture(self, temp_file):
        """Verify temp_file fixture creates a temporary file."""
        assert isinstance(temp_file, Path)

        # Test writing to the temp file
        temp_file.write_text("Test content")
        assert temp_file.read_text() == "Test content"

    def test_sample_dict_fixture(self, sample_dict):
        """Verify sample_dict fixture provides expected data."""
        assert isinstance(sample_dict, dict)
        assert "string" in sample_dict
        assert sample_dict["number"] == 42
        assert sample_dict["boolean"] is True

    def test_sample_list_fixture(self, sample_list):
        """Verify sample_list fixture provides expected data."""
        assert isinstance(sample_list, list)
        assert len(sample_list) == 6
        assert 1 in sample_list
        assert "four" in sample_list

    def test_mock_env_fixture(self, mock_env):
        """Verify mock_env fixture can set environment variables."""
        test_var = "TEST_INFRASTRUCTURE_VAR"
        test_value = "test_value_123"

        # Ensure the variable doesn't exist before
        assert test_var not in os.environ

        # Set it using the fixture
        mock_env(**{test_var: test_value})

        # Verify it's set
        assert os.environ[test_var] == test_value


@pytest.mark.unit
class TestMarkers:
    """Test suite to validate pytest markers."""

    def test_unit_marker(self):
        """Verify unit marker is available."""
        assert True

    @pytest.mark.integration
    def test_integration_marker(self):
        """Verify integration marker is available."""
        assert True

    @pytest.mark.slow
    def test_slow_marker(self):
        """Verify slow marker is available."""
        assert True


class TestPytestMock:
    """Test suite to validate pytest-mock is working."""

    def test_mocker_fixture(self, mocker):
        """Verify pytest-mock mocker fixture is available."""
        mock_func = mocker.Mock(return_value=42)
        result = mock_func()
        assert result == 42
        mock_func.assert_called_once()

    def test_mocker_patch(self, mocker):
        """Verify mocker.patch works correctly."""
        mock_value = "mocked_value"
        mocker.patch.dict(os.environ, {"MOCKED_VAR": mock_value})
        assert os.environ["MOCKED_VAR"] == mock_value


class TestImports:
    """Test suite to validate critical imports."""

    def test_import_pytest(self):
        """Verify pytest can be imported."""
        import pytest
        assert pytest is not None

    def test_import_pytest_cov(self):
        """Verify pytest-cov can be imported."""
        import pytest_cov
        assert pytest_cov is not None

    def test_import_pytest_mock(self):
        """Verify pytest-mock can be imported."""
        import pytest_mock
        assert pytest_mock is not None

# DMOJ Testing Infrastructure

This directory contains the testing infrastructure for the DMOJ Online Judge project.

## Quick Start

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_infrastructure.py

# Run tests with coverage report
poetry run pytest --cov

# Run tests without coverage (faster)
poetry run pytest --no-cov

# Run only unit tests
poetry run pytest -m unit

# Run only integration tests
poetry run pytest -m integration

# Run with verbose output
poetry run pytest -v
```

### Alternative Commands

Both commands work identically:
```bash
poetry run test
poetry run tests
```

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared pytest fixtures and configuration
├── test_infrastructure.py   # Infrastructure validation tests
├── unit/                    # Unit tests (test individual components)
│   └── __init__.py
└── integration/             # Integration tests (test multiple components)
    └── __init__.py
```

## Available Fixtures

The following fixtures are available in all tests (defined in `conftest.py`):

### File System Fixtures

- **`temp_dir`**: Provides a temporary directory that's cleaned up after the test
- **`temp_file`**: Provides a temporary file that's cleaned up after the test

### Data Fixtures

- **`sample_dict`**: A sample dictionary with various data types
- **`sample_list`**: A sample list with various items

### Environment Fixtures

- **`mock_env`**: Temporarily set environment variables

### Example Usage

```python
def test_with_temp_dir(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("Hello, World!")
    assert test_file.read_text() == "Hello, World!"

def test_with_env_var(mock_env):
    mock_env(MY_VAR="test_value")
    assert os.environ["MY_VAR"] == "test_value"
```

## Test Markers

Use markers to categorize your tests:

- **`@pytest.mark.unit`**: Unit tests (test individual components in isolation)
- **`@pytest.mark.integration`**: Integration tests (test multiple components together)
- **`@pytest.mark.slow`**: Tests that take a long time to run
- **`@pytest.mark.django`**: Tests that require Django to be installed and configured

### Example

```python
import pytest

@pytest.mark.unit
def test_something():
    assert True

@pytest.mark.integration
@pytest.mark.slow
def test_complex_integration():
    # This is a slow integration test
    pass
```

## Coverage Reports

Coverage reports are generated automatically when running tests:

- **HTML Report**: `htmlcov/index.html` - Open in browser for interactive coverage view
- **XML Report**: `coverage.xml` - For CI/CD integration
- **Terminal Report**: Shows coverage summary with missing lines

### Coverage Threshold

Tests will fail if coverage falls below **80%**.

To run tests without coverage checks:
```bash
poetry run pytest --no-cov
```

## Configuration

All test configuration is in `pyproject.toml`:

- **Test discovery patterns**: Automatically finds `test_*.py` and `*_test.py` files
- **Coverage settings**: Source directories, omit patterns, report formats
- **Custom markers**: Define and use custom test markers
- **Warning filters**: Control which warnings are displayed

## Writing Tests

### Best Practices

1. **Organize by type**: Place unit tests in `tests/unit/` and integration tests in `tests/integration/`
2. **Use descriptive names**: Test functions should clearly describe what they test
3. **One assertion per test**: Keep tests focused and specific
4. **Use fixtures**: Leverage shared fixtures for common setup
5. **Mark appropriately**: Use markers to categorize tests

### Example Test

```python
import pytest

class TestMyFeature:
    """Test suite for MyFeature."""

    @pytest.mark.unit
    def test_basic_functionality(self, sample_dict):
        """Test that basic functionality works."""
        assert "string" in sample_dict
        assert sample_dict["number"] == 42

    @pytest.mark.integration
    def test_complex_scenario(self, temp_dir, mock_env):
        """Test a complex integration scenario."""
        mock_env(CONFIG_DIR=str(temp_dir))
        # Your test code here
        assert True
```

## Installing Dependencies

### First Time Setup

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install all dependencies (including dev/test dependencies)
poetry install
```

### Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update specific package
poetry update pytest
```

## CI/CD Integration

The testing infrastructure is ready for CI/CD integration:

1. **Coverage reports** in XML format for tools like Codecov
2. **Configurable thresholds** to enforce coverage standards
3. **Marker-based filtering** to run specific test subsets
4. **Clear exit codes** for pass/fail status

### Example CI Configuration

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: poetry install

- name: Run tests with coverage
  run: poetry run pytest

- name: Upload coverage reports
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Tests not being discovered

- Ensure test files match the pattern `test_*.py` or `*_test.py`
- Ensure test classes start with `Test`
- Ensure test functions start with `test_`

### Import errors

- Make sure you're running tests with `poetry run pytest`
- Verify all dependencies are installed with `poetry install`

### Coverage reports not generating

- Check that source directories exist in the coverage configuration
- Ensure tests are actually running code from the source directories

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)

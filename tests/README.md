# Testing Framework for Autonomia

This directory contains the comprehensive testing framework for the Autonomia project, built with pytest.

## Overview

The testing framework provides:
- **Unit tests** for individual components
- **Integration tests** for component interactions
- **Database tests** with SQLite in-memory database
- **Mock tests** for external dependencies
- **Coverage reporting** to ensure code quality

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Database model tests
├── test_processing.py       # Message processing tests
├── test_jobs.py            # Job functionality tests
├── test_simple.py          # Basic functionality tests
├── run_tests.py            # Test runner script
└── README.md              # This documentation
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_simple.py

# Run specific test function
poetry run pytest tests/test_simple.py::test_basic
```

### Using the Test Runner Script

```bash
# Run all tests with coverage
python tests/run_tests.py --type all

# Run only unit tests
python tests/run_tests.py --type unit

# Run only integration tests
python tests/run_tests.py --type integration

# Run with coverage report
python tests/run_tests.py --type coverage

# Run linting only
python tests/run_tests.py --type lint

# Skip slow tests
python tests/run_tests.py --fast
```

### Test Categories

#### Unit Tests
- **Model Tests**: Test database model functionality
- **Processing Tests**: Test message enrichment and formatting
- **Utility Tests**: Test helper functions and utilities

#### Integration Tests
- **Job Tests**: Test job execution and error handling
- **Database Integration**: Test model interactions
- **API Integration**: Test external service interactions

## Test Fixtures

### Database Fixtures
- `test_engine`: SQLite in-memory database engine
- `test_session`: Database session for tests
- `test_database_url`: Database connection URL

### Mock Fixtures
- `mock_telegram_client`: Mock Telegram client
- `mock_openai_client`: Mock OpenAI client
- `sample_chat_data`: Sample chat data for testing
- `sample_user_data`: Sample user data for testing
- `sample_message_data`: Sample message data for testing

### Environment Fixtures
- `setup_test_environment`: Sets up test environment variables

## Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --asyncio-mode=auto
markers =
    asyncio: marks tests as async
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### Coverage Configuration
- Minimum coverage: 70%
- HTML coverage report generation
- Terminal coverage report with missing lines

## Writing Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestMyComponent:
    """Test MyComponent functionality."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        component = MyComponent()
        
        # Act
        result = component.do_something()
        
        # Assert
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, test_session):
        """Test async functionality."""
        # Arrange
        data = {"key": "value"}
        
        # Act
        result = await async_function(data)
        
        # Assert
        assert result is not None
```

### Using Fixtures
```python
def test_with_fixtures(sample_chat_data, mock_telegram_client):
    """Test using fixtures."""
    assert sample_chat_data["id"] == 123456789
    assert mock_telegram_client is not None
```

### Mocking External Dependencies
```python
@patch('module.external_service')
def test_with_mock(mock_service):
    """Test with mocked external service."""
    mock_service.return_value = "mocked_result"
    
    result = function_that_uses_service()
    
    assert result == "mocked_result"
    mock_service.assert_called_once()
```

## Database Testing

### SQLite In-Memory Database
Tests use SQLite in-memory database for fast, isolated testing:
- No file I/O required
- Automatic cleanup between tests
- Compatible with SQLAlchemy async operations

### Test Data Management
- Fixtures provide sample data
- Database is reset between tests
- No data persistence between test runs

## Coverage Reporting

### Running Coverage
```bash
# Run tests with coverage
poetry run pytest --cov=. --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

### Coverage Targets
- **Overall**: 70% minimum
- **Critical modules**: 80% minimum
- **New features**: 90% minimum

## Continuous Integration

### GitHub Actions Integration
Tests are automatically run on:
- Pull requests
- Push to main branch
- Scheduled runs

### Test Commands for CI
```yaml
- name: Run tests
  run: |
    poetry install --with dev
    poetry run pytest --cov=. --cov-report=xml
    poetry run coverage report --fail-under=70
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
- Ensure SQLite is available
- Check database URL format
- Verify async/await usage

#### Import Errors
- Check Python path
- Verify package installation
- Ensure virtual environment is activated

#### Test Timeouts
- Use `--fast` flag to skip slow tests
- Increase timeout in pytest configuration
- Check for infinite loops in tests

### Debugging Tests
```bash
# Run with debug output
poetry run pytest -v -s

# Run single test with debug
poetry run pytest tests/test_simple.py::test_basic -v -s

# Run with print statements
poetry run pytest -s
```

## Best Practices

### Test Organization
1. **Arrange**: Set up test data and mocks
2. **Act**: Execute the function being tested
3. **Assert**: Verify the expected outcomes

### Test Isolation
- Each test should be independent
- Use fixtures for shared setup
- Clean up after each test

### Mock Usage
- Mock external dependencies
- Use realistic mock data
- Verify mock interactions

### Async Testing
- Use `@pytest.mark.asyncio` for async tests
- Use `AsyncMock` for async mocks
- Handle async fixtures properly

## Contributing

### Adding New Tests
1. Create test file in `tests/` directory
2. Follow naming conventions
3. Add appropriate markers
4. Update documentation

### Test Review Checklist
- [ ] Tests are isolated and independent
- [ ] Mocks are used appropriately
- [ ] Edge cases are covered
- [ ] Error conditions are tested
- [ ] Documentation is updated

## Performance

### Test Execution Time
- Unit tests: < 1 second each
- Integration tests: < 5 seconds each
- Full test suite: < 2 minutes

### Optimization Tips
- Use `@pytest.mark.slow` for slow tests
- Group related tests in classes
- Reuse fixtures when possible
- Use parametrized tests for similar cases 
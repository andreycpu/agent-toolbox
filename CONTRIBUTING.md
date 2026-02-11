# Contributing to Agent Toolbox

Thank you for your interest in contributing to Agent Toolbox! This document provides guidelines and information for contributors.

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/agent-toolbox.git
   cd agent-toolbox
   ```

2. **Set up development environment**
   ```bash
   make dev-setup
   ```
   Or manually:
   ```bash
   pip install -e .[dev]
   pip install pytest pytest-cov black flake8 mypy
   ```

3. **Set up git hooks (optional but recommended)**
   ```bash
   make init-git-hooks
   ```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run tests in watch mode
make test-watch
```

### Code Quality

```bash
# Format code
make format

# Check formatting
make format-check

# Run linting
make lint

# Type checking
make type-check
```

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, enforced by `black` and `flake8`
- **Line length**: 127 characters maximum
- **Imports**: Use absolute imports, group by standard/third-party/local
- **Docstrings**: Use Google-style docstrings for all public functions/classes

### Example Code Style

```python
"""Module docstring describing the module purpose."""

import os
import sys
from typing import Dict, List, Optional

import requests
import pandas as pd

from agent_toolbox.utils import Logger


class ExampleClass:
    """Example class demonstrating code style.
    
    Args:
        name: The name of the example.
        timeout: Timeout in seconds.
    """
    
    def __init__(self, name: str, timeout: int = 30):
        """Initialize the example."""
        self.name = name
        self.timeout = timeout
        self.logger = Logger("ExampleClass")
        
    def process_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process input data and return DataFrame.
        
        Args:
            data: List of dictionaries containing data to process.
            
        Returns:
            Processed data as pandas DataFrame.
            
        Raises:
            ValueError: If data is empty or invalid.
        """
        if not data:
            raise ValueError("Data cannot be empty")
            
        self.logger.info(f"Processing {len(data)} records")
        df = pd.DataFrame(data)
        
        return df
```

### Testing

- **Coverage**: Aim for >90% test coverage
- **Test files**: Name test files as `test_*.py`
- **Test classes**: Use `TestClassName` pattern
- **Test methods**: Use descriptive names like `test_method_with_valid_input`
- **Fixtures**: Use pytest fixtures for common test setup
- **Mocking**: Mock external services and file operations when appropriate

### Example Test

```python
import pytest
from unittest.mock import Mock, patch

from agent_toolbox.file_operations import FileManager


class TestFileManager:
    """Test cases for FileManager class."""
    
    @pytest.fixture
    def file_manager(self, tmp_path):
        """Create FileManager instance for testing."""
        return FileManager(base_path=tmp_path)
    
    def test_write_and_read_text(self, file_manager):
        """Test text file operations."""
        content = "Hello, World!"
        file_manager.write_text("test.txt", content)
        
        result = file_manager.read_text("test.txt")
        assert result == content
    
    @patch('requests.get')
    def test_with_mock(self, mock_get):
        """Test with mocked external dependency."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"key": "value"}
        
        # Test code that uses requests.get
        pass
```

### Documentation

- **API Reference**: Update `docs/api_reference.md` for new public APIs
- **Examples**: Add usage examples for new features
- **Docstrings**: Document all public functions, classes, and methods
- **README**: Update README.md if adding major features
- **Changelog**: Update CHANGELOG.md with your changes

## Contributing Process

### 1. Issue First

- **Bug reports**: Create an issue describing the bug with reproduction steps
- **Feature requests**: Create an issue describing the desired feature and use case
- **Questions**: Use GitHub Discussions for general questions

### 2. Branch and Develop

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# Write tests
# Update documentation

# Commit with descriptive messages
git commit -m "Add feature X with Y capability"
```

### 3. Pull Request

- **Description**: Provide clear description of changes
- **Tests**: Include tests for new functionality
- **Documentation**: Update relevant documentation
- **Backward compatibility**: Ensure changes don't break existing code
- **Changelog**: Add entry to CHANGELOG.md

### Pull Request Template

```markdown
## Description
Brief description of the changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Coverage maintained or improved

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Types of Contributions

### 🐛 Bug Fixes

- Fix incorrect behavior
- Improve error handling
- Address security vulnerabilities
- Performance improvements

### ✨ New Features

- **Core modules**: New functionality in file operations, web scraping, etc.
- **Integrations**: New service integrations (APIs, databases, etc.)
- **Utilities**: New utility functions and helpers
- **Examples**: New example workflows and patterns

### 📚 Documentation

- API documentation improvements
- Tutorial and guide updates
- Code example improvements
- README and setup instructions

### 🧪 Testing

- New test cases
- Test infrastructure improvements
- Performance benchmarks
- Integration tests

## Coding Standards

### Error Handling

```python
# Good: Specific exceptions with helpful messages
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise ValueError(f"Failed to process data: {e}") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Logging

```python
# Use the built-in logger
from agent_toolbox.utils import Logger

logger = Logger("ModuleName")

# Good logging practices
logger.info("Starting operation", user_id=123, operation="data_sync")
logger.error("Operation failed", exception=e, context={"file": "data.csv"})
```

### Configuration

```python
# Use ConfigManager for configuration
from agent_toolbox.utils import ConfigManager

config = ConfigManager()
timeout = config.get('api.timeout', default=30)
```

### Type Hints

```python
# Use type hints for all public interfaces
from typing import List, Dict, Optional, Union

def process_items(items: List[str], 
                 config: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """Process items and return statistics."""
    pass
```

## Release Process

### Version Numbering

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

### Release Steps

1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Create release PR
5. Tag release after merge
6. Publish to PyPI (automated)

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: For security issues or private concerns

## Recognition

Contributors are recognized in:
- CHANGELOG.md for significant contributions
- GitHub contributors page
- Release notes for major contributions

Thank you for contributing to Agent Toolbox! 🚀
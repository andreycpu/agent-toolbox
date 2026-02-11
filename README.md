# Agent Toolbox

[![CI](https://github.com/andreycpu/agent-toolbox/workflows/CI/badge.svg)](https://github.com/andreycpu/agent-toolbox/actions)
[![Security](https://github.com/andreycpu/agent-toolbox/workflows/Security%20Scan/badge.svg)](https://github.com/andreycpu/agent-toolbox/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, production-ready toolkit of reusable agent tools and utilities for autonomous agents. Built with security, reliability, and developer experience in mind.

## 🚀 Quick Start

```bash
# Install the package
pip install agent-toolbox

# Or install with development dependencies
pip install agent-toolbox[dev]
```

```python
from agent_toolbox import FileManager, APIClient, ShellExecutor

# File operations with comprehensive error handling
fm = FileManager()
fm.write_json("config.json", {"api_key": "secret"})
config = fm.read_json("config.json")

# Robust API client with retries and authentication
api = APIClient("https://api.example.com")
api.set_auth_bearer("your-token")
data = api.get("/users", params={"limit": 10})

# Safe shell execution with async support
shell = ShellExecutor()
result = shell.execute("ls -la", capture_output=True)
process_id = shell.execute_async("long-running-task")
```

## 🌟 Features

### Core Modules
- **🗂️ File Operations**: Type-safe file system utilities with JSON/YAML support
- **🌐 Web Scraping**: Respectful web data extraction with rate limiting  
- **🔗 API Clients**: Production-ready REST client with authentication & retries
- **📊 Data Processing**: Advanced data manipulation with pandas integration
- **⚡ Shell Execution**: Secure system command execution with async support

### Integration Modules  
- **💬 Slack**: Full Slack API integration for messaging and file operations
- **🐙 GitHub**: Complete GitHub API wrapper for repository management
- **📧 Email**: SMTP/IMAP support for email automation
- **💾 Database**: Type-safe database operations with multiple backend support
- **🔗 Webhooks**: HTTP webhook client and server for real-time integrations

### Utility Modules
- **⚙️ Configuration**: Hierarchical configuration management with validation
- **📝 Logging**: Structured logging with multiple output formats
- **🔄 Retry Logic**: Configurable retry patterns with exponential backoff
- **⏱️ Rate Limiting**: Token bucket rate limiting for API compliance
- **💾 Caching**: Multi-level caching with TTL support
- **🔒 Crypto**: Secure cryptographic utilities for hashing and encoding
- **📊 Monitoring**: Performance monitoring and metrics collection
- **📅 Scheduling**: Task scheduling with cron-like syntax

## 📚 Comprehensive Examples

### File Operations with Error Handling
```python
from agent_toolbox import FileManager
from agent_toolbox.file_operations import FileOperationError

try:
    fm = FileManager("/secure/workspace")
    
    # Safe file operations with automatic directory creation
    fm.write_json("config/settings.json", {
        "api_endpoint": "https://api.example.com",
        "timeout": 30,
        "retries": 3
    })
    
    # Read with encoding validation
    content = fm.read_text("logs/app.log", encoding="utf-8")
    
    # Batch operations with progress tracking
    files = fm.find_files("*.log", recursive=True)
    for file in files:
        stats = fm.get_file_stats(file)
        print(f"{file.name}: {stats['size']} bytes")
        
except FileOperationError as e:
    print(f"File operation failed: {e}")
```

### Robust API Integration
```python
from agent_toolbox import APIClient
from agent_toolbox.api_client import APIError, APITimeoutError
from agent_toolbox.utils import retry, Logger

logger = Logger("APIService")

class GitHubService:
    def __init__(self, token: str):
        self.client = APIClient("https://api.github.com")
        self.client.set_auth_bearer(token)
    
    @retry(max_attempts=3, exceptions=APITimeoutError)
    def get_user_repos(self, username: str):
        try:
            response = self.client.get(f"/users/{username}/repos", 
                                     params={"per_page": 100})
            logger.info(f"Retrieved {len(response)} repositories", 
                       username=username)
            return response
        except APIError as e:
            logger.error(f"API request failed: {e}", username=username)
            raise
```

### Secure Shell Operations
```python
from agent_toolbox import ShellExecutor
import os

# Initialize with restricted environment
executor = ShellExecutor(
    working_directory="/safe/workspace",
    environment={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    timeout=30.0
)

# Synchronous execution with validation
try:
    result = executor.execute(["git", "status", "--porcelain"])
    if result.returncode == 0:
        files = result.stdout.strip().split('\n')
        print(f"Modified files: {len(files)}")
    
    # Asynchronous long-running task
    process_id = executor.execute_async(["python", "train_model.py"])
    
    # Monitor progress
    while True:
        status = executor.get_process_status(process_id)
        if not status['running']:
            break
        time.sleep(5)
    
    output, errors = executor.get_process_output(process_id)
    print(f"Training completed: {output}")
    
except Exception as e:
    print(f"Command failed: {e}")
```

### Advanced Utilities Usage
```python
from agent_toolbox.utils import (
    ConfigManager, Logger, RateLimiter, SimpleCache,
    validate_input, ValidationError, monitor_performance
)

# Hierarchical configuration management
config = ConfigManager("app.json")
config.set("database.host", "localhost")
config.set("database.port", 5432)
db_config = config.get_section("database")

# Performance monitoring with context
@monitor_performance
def process_data(data):
    with RateLimiter(max_calls=10, time_window=60):
        return expensive_operation(data)

# Input validation with custom rules
@validate_input({"email": validate_email, "age": lambda x: 0 <= x <= 120})
def create_user(email: str, age: int):
    logger = Logger("UserService")
    logger.info("Creating user", email=email, age=age)
    return {"id": 123, "email": email, "age": age}

# Caching with TTL
cache = SimpleCache(default_ttl=300)  # 5 minutes

@cache.memoize(ttl=600)  # 10 minutes
def fetch_expensive_data(key: str):
    # Expensive computation or API call
    return process_large_dataset(key)
```

## 🏗️ Architecture

Agent Toolbox is designed with modularity and extensibility in mind:

- **Core Modules**: Essential functionality every agent needs
- **Integration Modules**: Service-specific implementations  
- **Utility Modules**: Cross-cutting concerns and helpers
- **Type Safety**: Comprehensive type hints with mypy validation
- **Error Handling**: Structured exceptions with detailed context
- **Testing**: 95%+ test coverage with integration tests

## 🔧 Development

```bash
# Clone the repository
git clone https://github.com/andreycpu/agent-toolbox.git
cd agent-toolbox

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Type checking
mypy agent_toolbox/

# Code formatting
black agent_toolbox/ tests/
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
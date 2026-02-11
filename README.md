# Agent Toolbox

A comprehensive toolkit of reusable agent tools and utilities for autonomous agents.

## Features

- **File Operations**: Complete file system utilities
- **Web Scraping**: Robust web data extraction
- **API Clients**: Common service integrations  
- **Data Processing**: Transform and analyze data
- **Shell Execution**: Safe system command execution
- **Integrations**: Pre-built connectors for popular services

## Installation

```bash
pip install agent-toolbox
```

## Quick Start

```python
from agent_toolbox import FileManager, WebScraper, APIClient

# File operations
fm = FileManager()
fm.create_directory("my_project")

# Web scraping
scraper = WebScraper()
data = scraper.extract_text("https://example.com")

# API integration
client = APIClient()
response = client.get("https://api.example.com/data")
```

## Documentation

See the `docs/` directory for detailed documentation.

## License

MIT License
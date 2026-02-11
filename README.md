# Agent Toolbox

A comprehensive toolkit of reusable agent tools and utilities for autonomous agents.

## Features

### Core Modules
- **File Operations**: Complete file system utilities with text, JSON, YAML support
- **Web Scraping**: Robust web data extraction with rate limiting and respect for robots.txt
- **API Clients**: Generic REST client with authentication, retries, and error handling
- **Data Processing**: Advanced data manipulation with pandas integration
- **Shell Execution**: Safe system command execution with validation and background processes

### Integration Modules  
- **Slack**: Send messages, upload files, manage channels
- **GitHub**: Repository management, issues, pull requests, file operations
- **Email**: SMTP/IMAP support for sending and receiving emails
- **Database**: SQLite support with extensible architecture for other databases
- **Webhooks**: HTTP webhook client and server for real-time integrations

### Utility Modules
- **Configuration**: Flexible config management with file and environment support
- **Logging**: Enhanced logging with JSON formatting and context
- **Validation**: Input validation with built-in and custom validators
- **Caching**: In-memory and file-based caching with TTL support
- **Monitoring**: System monitoring and application performance tracking
- **Formatting**: Human-readable formatting for bytes, duration, numbers, tables
- **Cryptography**: Basic crypto operations for hashing, encoding, and tokens
- **Scheduling**: Simple task scheduler for periodic and delayed execution
- **Rate Limiting**: Token bucket and sliding window rate limiting algorithms
- **Retry Logic**: Exponential backoff retry with jitter and custom exceptions

## Installation

```bash
pip install agent-toolbox
```

## Quick Start

```python
from agent_toolbox import FileManager, WebScraper, APIClient, DataProcessor
from agent_toolbox.utils import Logger, retry, validate_email, format_bytes
from agent_toolbox.integrations import WebhookClient

# File operations with automatic JSON/YAML handling
fm = FileManager()
fm.create_directory("my_project")
fm.write_json("config.json", {"api_key": "secret", "timeout": 30})
config = fm.read_json("config.json")

# Web scraping with rate limiting
scraper = WebScraper(delay=1.0)  # Respectful 1-second delay
text = scraper.extract_text("https://example.com")
metadata = scraper.extract_metadata("https://example.com")

# API integration with retry logic
@retry(max_attempts=3, delay=1.0)
def api_call():
    client = APIClient(base_url="https://api.example.com")
    client.set_auth_bearer("your-token")
    return client.get("/data")

# Data processing with pandas integration  
processor = DataProcessor()
df = processor.load_csv("data.csv")
stats = processor.get_basic_stats(df, "price")
filtered = processor.filter_dataframe(df, {"price": {"gt": 100}})

# Monitoring and logging
logger = Logger("MyAgent", log_file="agent.log")
logger.info("Agent started", user_id=123, action="startup")

# Validation and formatting
if validate_email("user@example.com"):
    logger.info(f"Processing {format_bytes(1024000)} of data")

# Webhook integration
webhook = WebhookClient("https://hooks.slack.com/...")
webhook.send_alert("Task completed successfully!", level="info")
```

## Documentation

See the `docs/` directory for detailed documentation.

## License

MIT License
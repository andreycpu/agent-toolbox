# Agent Toolbox API Reference

## Core Modules

### FileManager

Comprehensive file management utilities for agents.

```python
from agent_toolbox import FileManager

fm = FileManager(base_path="./workspace")
```

#### Methods

- `create_directory(path, parents=True)` - Create directory
- `read_text(path, encoding="utf-8")` - Read text file
- `write_text(path, content, encoding="utf-8")` - Write text file
- `append_text(path, content, encoding="utf-8")` - Append to text file
- `read_json(path)` - Read JSON file
- `write_json(path, data, indent=2)` - Write JSON file
- `read_yaml(path)` - Read YAML file
- `write_yaml(path, data)` - Write YAML file
- `exists(path)` - Check if path exists
- `is_file(path)` - Check if path is file
- `is_directory(path)` - Check if path is directory
- `copy_file(src, dst)` - Copy file
- `move_file(src, dst)` - Move file
- `delete_file(path)` - Delete file
- `delete_directory(path, recursive=False)` - Delete directory
- `list_files(path=".", pattern="*")` - List files with pattern
- `find_files(pattern, path=".", recursive=True)` - Find files recursively
- `get_file_size(path)` - Get file size in bytes
- `get_file_stats(path)` - Get comprehensive file statistics

### WebScraper

Robust web scraping utilities with rate limiting.

```python
from agent_toolbox import WebScraper

scraper = WebScraper(user_agent="MyAgent/1.0", timeout=30, delay=1.0)
```

#### Methods

- `get_page(url, **kwargs)` - Fetch webpage with error handling
- `extract_text(url, clean=True)` - Extract all text content
- `extract_links(url, absolute=True)` - Extract all links
- `extract_images(url, absolute=True)` - Extract all images
- `extract_by_selector(url, selector)` - Extract elements by CSS selector
- `extract_tables(url)` - Extract all tables as nested lists
- `extract_metadata(url)` - Extract page metadata (title, description, etc.)

### APIClient

Generic API client with authentication and retry logic.

```python
from agent_toolbox import APIClient

client = APIClient(base_url="https://api.example.com", timeout=30)
```

#### Methods

- `get(endpoint, params=None)` - Make GET request
- `post(endpoint, data=None, json_data=None)` - Make POST request
- `put(endpoint, data=None, json_data=None)` - Make PUT request
- `delete(endpoint)` - Make DELETE request
- `set_auth_bearer(token)` - Set Bearer token authentication
- `set_auth_basic(username, password)` - Set Basic authentication
- `set_auth_header(header_name, header_value)` - Set custom auth header
- `set_api_key(key, param_name="api_key", in_header=False)` - Set API key auth
- `add_default_params(params)` - Add default parameters to all requests

### DataProcessor

Data processing and analysis utilities.

```python
from agent_toolbox import DataProcessor

processor = DataProcessor()
```

#### Methods

- `load_csv(file_path, **kwargs)` - Load CSV into DataFrame
- `save_csv(data, file_path, **kwargs)` - Save DataFrame to CSV
- `load_json_lines(file_path)` - Load JSONL file
- `save_json_lines(data, file_path)` - Save to JSONL file
- `clean_text(text, remove_extra_whitespace=True, remove_special_chars=False, lowercase=False)` - Clean text
- `filter_dataframe(df, conditions)` - Filter DataFrame with conditions
- `aggregate_data(df, group_by, agg_funcs)` - Aggregate DataFrame
- `transform_column(df, column, func)` - Apply transformation to column
- `normalize_column(df, column, method="minmax")` - Normalize column values
- `get_basic_stats(df, column)` - Get basic statistics
- `detect_outliers(df, column, method="iqr")` - Detect outliers
- `missing_data_report(df)` - Generate missing data report

### ShellExecutor

Safe shell command execution with validation.

```python
from agent_toolbox import ShellExecutor

executor = ShellExecutor(working_directory="./workspace", timeout=300)
```

#### Methods

- `execute(command, capture_output=True, check_return_code=True, env_vars=None)` - Execute command
- `execute_batch(commands, stop_on_error=True)` - Execute multiple commands
- `execute_script(script_content, script_type="bash", cleanup=True)` - Execute script
- `execute_background(command, env_vars=None)` - Execute in background
- `wait_for_process(process, timeout=None)` - Wait for background process
- `is_process_running(process)` - Check if process running
- `kill_process(process)` - Kill background process

## Integration Modules

### SlackClient

Slack API integration for messaging and channel management.

```python
from agent_toolbox.integrations import SlackClient

slack = SlackClient(token="your-slack-token")
```

#### Methods

- `send_message(channel, text, blocks=None, thread_ts=None)` - Send message
- `get_channels()` - Get list of channels
- `get_users()` - Get list of users
- `upload_file(file_path, channels, title=None, comment=None)` - Upload file
- `create_channel(name, is_private=False)` - Create channel
- `get_channel_history(channel, limit=100)` - Get message history
- `react_to_message(channel, timestamp, emoji)` - Add reaction

### GitHubClient

GitHub API integration for repository management.

```python
from agent_toolbox.integrations import GitHubClient

github = GitHubClient(token="your-github-token")
```

#### Methods

- `get_repositories(user=None)` - Get repositories
- `get_repository(owner, repo)` - Get repository info
- `create_repository(name, description="", private=False)` - Create repository
- `get_issues(owner, repo, state="open")` - Get issues
- `create_issue(owner, repo, title, body="", labels=None)` - Create issue
- `get_pull_requests(owner, repo, state="open")` - Get pull requests
- `create_pull_request(owner, repo, title, head, base="main", body="")` - Create PR
- `get_file_content(owner, repo, path, ref="main")` - Get file content
- `update_file(owner, repo, path, content, message, sha=None, branch="main")` - Update file

### EmailClient

Email client with SMTP and IMAP support.

```python
from agent_toolbox.integrations import EmailClient

email = EmailClient(
    smtp_server="smtp.gmail.com", smtp_port=587,
    imap_server="imap.gmail.com", imap_port=993,
    username="user@gmail.com", password="password"
)
```

#### Methods

- `send_email(to_addresses, subject, body, from_address=None, cc_addresses=None, bcc_addresses=None, attachments=None, is_html=False)` - Send email
- `get_emails(folder="INBOX", limit=10, search_criteria="ALL")` - Get emails

### DatabaseClient

Database client with SQLite support (extensible for other DBs).

```python
from agent_toolbox.integrations import DatabaseClient

# SQLite example
db = DatabaseClient(db_type="sqlite", database="mydb.sqlite")

with db:
    results = db.execute_query("SELECT * FROM users")
```

#### Methods

- `connect()` - Establish connection
- `disconnect()` - Close connection
- `execute_query(query, params=None)` - Execute SELECT query
- `execute_update(query, params=None)` - Execute INSERT/UPDATE/DELETE
- `execute_batch(query, param_list)` - Execute batch query
- `create_table(table_name, columns)` - Create table
- `drop_table(table_name)` - Drop table
- `insert_data(table_name, data)` - Insert single row
- `insert_dataframe(table_name, df, if_exists="append")` - Insert DataFrame
- `query_to_dataframe(query, params=None)` - Query to DataFrame
- `get_table_info(table_name)` - Get table structure
- `list_tables()` - List all tables
- `backup_database(backup_path)` - Backup database

## Utility Modules

### ConfigManager

Configuration management with file and environment variable support.

```python
from agent_toolbox.utils import ConfigManager

config = ConfigManager(config_path="config.yaml", load_env_file=True)
```

#### Methods

- `load_config()` - Load configuration from file
- `save_config(file_path=None)` - Save configuration to file
- `get(key, default=None, use_env=True)` - Get configuration value
- `set(key, value)` - Set configuration value
- `get_section(section)` - Get entire section
- `merge_config(other_config)` - Merge configuration
- `has_key(key)` - Check if key exists
- `delete_key(key)` - Delete key
- `to_dict()` - Get as dictionary
- `clear()` - Clear all configuration

### Logger

Enhanced logging with JSON and standard formats.

```python
from agent_toolbox.utils import Logger

logger = Logger(name="my-agent", level="INFO", log_file="app.log", json_format=False)
```

#### Methods

- `debug(message, **kwargs)` - Log debug message
- `info(message, **kwargs)` - Log info message
- `warning(message, **kwargs)` - Log warning message
- `error(message, exception=None, **kwargs)` - Log error message
- `critical(message, **kwargs)` - Log critical message
- `log_function_call(func_name, args, kwargs, result=None, duration=None)` - Log function call
- `log_api_call(method, url, status_code, duration, response_size=None)` - Log API call
- `add_file_handler(log_file)` - Add file handler
- `set_level(level)` - Change logging level

### Retry Decorator

Retry decorator with exponential backoff.

```python
from agent_toolbox.utils import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def flaky_function():
    # Function that might fail
    pass
```

#### Parameters

- `max_attempts` - Maximum retry attempts
- `delay` - Initial delay between retries
- `backoff` - Backoff multiplier
- `jitter` - Add random jitter
- `exceptions` - Exception types to catch
- `on_retry` - Callback on retry

### RateLimiter

Rate limiting with token bucket and sliding window algorithms.

```python
from agent_toolbox.utils import RateLimiter

limiter = RateLimiter(max_calls=100, time_window=60.0)  # 100 calls per minute

with limiter:
    # Rate-limited operation
    pass
```

#### Methods

- `acquire(tokens=1, blocking=True, timeout=None)` - Acquire tokens
- `get_tokens_available()` - Get available tokens

#### Decorators

```python
from agent_toolbox.utils import api_rate_limit, user_rate_limit

@api_rate_limit(calls_per_minute=60)
def api_function():
    pass

@user_rate_limit(calls_per_hour=1000)
def user_function(user_id=None):
    pass
```
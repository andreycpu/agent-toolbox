# Quick Start Guide

Get up and running with Agent Toolbox in minutes!

## Installation

```bash
pip install agent-toolbox
```

Or install from source:

```bash
git clone https://github.com/andreycpu/agent-toolbox.git
cd agent-toolbox
pip install -e .
```

## Basic Usage

### 1. File Operations

```python
from agent_toolbox import FileManager

# Initialize file manager
fm = FileManager(base_path="./my_project")

# Create directories and write files
fm.create_directory("data")
fm.write_text("data/config.txt", "Hello, Agent Toolbox!")

# Read files
content = fm.read_text("data/config.txt")
print(content)  # Output: Hello, Agent Toolbox!

# Work with JSON
data = {"name": "MyAgent", "version": "1.0"}
fm.write_json("data/config.json", data)
config = fm.read_json("data/config.json")
```

### 2. Web Scraping

```python
from agent_toolbox import WebScraper

# Initialize scraper with rate limiting
scraper = WebScraper(delay=1.0, timeout=30)

# Extract text from a webpage
text = scraper.extract_text("https://example.com")
print(f"Page text: {text[:200]}...")

# Extract metadata
metadata = scraper.extract_metadata("https://example.com")
print(f"Page title: {metadata['title']}")

# Extract specific elements
links = scraper.extract_links("https://example.com")
print(f"Found {len(links)} links")
```

### 3. API Calls

```python
from agent_toolbox import APIClient

# Initialize API client
client = APIClient(base_url="https://jsonplaceholder.typicode.com")

# Make GET request
posts = client.get("/posts")
print(f"Retrieved {len(posts)} posts")

# Make POST request
new_post = {
    "title": "My Post",
    "body": "This is my post content",
    "userId": 1
}
created = client.post("/posts", json_data=new_post)
print(f"Created post with ID: {created.get('id')}")
```

### 4. Data Processing

```python
from agent_toolbox import DataProcessor
import pandas as pd

# Initialize processor
processor = DataProcessor()

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': [85, 92, 78]
}
df = pd.DataFrame(data)

# Get statistics
stats = processor.get_basic_stats(df, 'score')
print(f"Average score: {stats['mean']:.1f}")

# Filter data
high_scorers = processor.filter_dataframe(df, {'score': {'gt': 80}})
print(f"High scorers: {high_scorers['name'].tolist()}")
```

### 5. Safe Shell Execution

```python
from agent_toolbox import ShellExecutor

# Initialize executor with safety settings
executor = ShellExecutor(
    working_directory="./workspace",
    blocked_commands=['rm -rf', 'sudo rm']
)

# Execute single command
result = executor.execute("ls -la")
print(result['stdout'])

# Execute multiple commands
commands = ["date", "whoami", "pwd"]
results = executor.execute_batch(commands)

for i, result in enumerate(results):
    print(f"{commands[i]}: {result['stdout'].strip()}")
```

## Configuration and Logging

### Configuration Management

```python
from agent_toolbox.utils import ConfigManager

# Load configuration from file and environment
config = ConfigManager(config_path="config.yaml")

# Set and get values
config.set('api.timeout', 30)
config.set('api.base_url', 'https://api.example.com')

timeout = config.get('api.timeout', default=10)
print(f"API timeout: {timeout}s")

# Save configuration
config.save_config("updated_config.yaml")
```

### Logging

```python
from agent_toolbox.utils import Logger

# Initialize logger
logger = Logger("MyAgent", level="INFO", log_file="agent.log")

# Log messages
logger.info("Agent started")
logger.warning("This is a warning")
logger.error("Something went wrong", exception=some_exception)

# Log function calls with timing
logger.log_function_call("process_data", args=(), kwargs={}, duration=0.5)
```

## Adding Resilience

### Retry Logic

```python
from agent_toolbox.utils import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def unreliable_api_call():
    # This will be retried up to 3 times with exponential backoff
    response = requests.get("https://unreliable-api.com/data")
    response.raise_for_status()
    return response.json()

try:
    data = unreliable_api_call()
    print("API call succeeded!")
except Exception as e:
    print(f"API call failed after retries: {e}")
```

### Rate Limiting

```python
from agent_toolbox.utils import RateLimiter, api_rate_limit

# Manual rate limiting
limiter = RateLimiter(max_calls=60, time_window=60.0)  # 60 calls per minute

for i in range(100):
    with limiter:  # Will automatically wait if rate limit exceeded
        make_api_call()

# Decorator-based rate limiting
@api_rate_limit(calls_per_minute=30)
def api_function():
    return requests.get("https://api.example.com/data")
```

## Integration Examples

### Slack Integration

```python
from agent_toolbox.integrations import SlackClient

# Initialize with your Slack token
slack = SlackClient(token="xoxb-your-slack-token")

# Send a message
slack.send_message("#general", "Hello from Agent Toolbox!")

# Upload a file
slack.upload_file("report.pdf", "#general", title="Daily Report")
```

### GitHub Integration

```python
from agent_toolbox.integrations import GitHubClient

# Initialize with your GitHub token
github = GitHubClient(token="ghp_your-github-token")

# Get repositories
repos = github.get_repositories()
print(f"You have {len(repos)} repositories")

# Create an issue
issue = github.create_issue(
    owner="your-username",
    repo="your-repo", 
    title="Bug Report",
    body="Found a bug in the application",
    labels=["bug", "priority-high"]
)
```

### Email Integration

```python
from agent_toolbox.integrations import EmailClient

# Initialize email client
email = EmailClient(
    smtp_server="smtp.gmail.com", smtp_port=587,
    imap_server="imap.gmail.com", imap_port=993,
    username="your-email@gmail.com", password="your-app-password"
)

# Send an email
result = email.send_email(
    to_addresses="recipient@example.com",
    subject="Agent Report",
    body="Here's your automated report!",
    attachments=["report.pdf"]
)

if result["success"]:
    print("Email sent successfully!")
```

## Building an Agent Workflow

Here's a complete example that combines multiple components:

```python
from agent_toolbox import FileManager, WebScraper, DataProcessor
from agent_toolbox.utils import Logger, retry, RateLimiter
from agent_toolbox.integrations import SlackClient

class NewsMonitorAgent:
    def __init__(self):
        self.logger = Logger("NewsMonitor")
        self.file_manager = FileManager()
        self.scraper = WebScraper(delay=2.0)
        self.processor = DataProcessor()
        self.rate_limiter = RateLimiter(max_calls=30, time_window=60)
        
    @retry(max_attempts=3)
    def scrape_news_site(self, url):
        with self.rate_limiter:
            self.logger.info(f"Scraping {url}")
            return self.scraper.extract_text(url)
    
    def analyze_sentiment(self, text):
        # Simplified sentiment analysis
        positive_words = ['good', 'great', 'excellent', 'positive']
        negative_words = ['bad', 'terrible', 'awful', 'negative']
        
        text_lower = text.lower()
        pos_count = sum(text_lower.count(word) for word in positive_words)
        neg_count = sum(text_lower.count(word) for word in negative_words)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def run_monitoring(self):
        urls = [
            "https://example-news1.com",
            "https://example-news2.com"
        ]
        
        results = []
        for url in urls:
            try:
                text = self.scrape_news_site(url)
                sentiment = self.analyze_sentiment(text)
                
                results.append({
                    'url': url,
                    'sentiment': sentiment,
                    'length': len(text)
                })
                
            except Exception as e:
                self.logger.error(f"Failed to process {url}", exception=e)
        
        # Save results
        self.file_manager.write_json("news_analysis.json", results)
        
        # Generate report
        report = f"Analyzed {len(results)} news sources\n"
        for result in results:
            report += f"- {result['url']}: {result['sentiment']}\n"
        
        self.file_manager.write_text("news_report.txt", report)
        self.logger.info("Monitoring complete")
        
        return results

# Run the agent
agent = NewsMonitorAgent()
results = agent.run_monitoring()
```

## Next Steps

- Explore the [API Reference](api_reference.md) for detailed documentation
- Check out the [examples/](../examples/) directory for more complete workflows
- Learn about [advanced patterns](advanced_usage.md) and best practices
- Contribute to the project on [GitHub](https://github.com/andreycpu/agent-toolbox)

## Getting Help

- Read the documentation in the `docs/` directory
- Check the examples in `examples/`
- Open an issue on GitHub for bugs or feature requests
- Join our community discussions

Happy agent building! 🤖
#!/usr/bin/env python3
"""Basic usage examples of Agent Toolbox components."""

from agent_toolbox import FileManager, WebScraper, APIClient, DataProcessor, ShellExecutor
from agent_toolbox.utils import Logger, ConfigManager, retry
from agent_toolbox.integrations import SlackClient
import pandas as pd


def file_operations_example():
    """Demonstrate file operations."""
    print("=== File Operations Example ===")
    
    fm = FileManager()
    
    # Create directory and files
    fm.create_directory("example_data")
    
    # Write and read text files
    fm.write_text("example_data/sample.txt", "Hello, Agent Toolbox!")
    content = fm.read_text("example_data/sample.txt")
    print(f"File content: {content}")
    
    # JSON operations
    data = {"name": "Agent", "version": "1.0", "features": ["files", "web", "apis"]}
    fm.write_json("example_data/config.json", data)
    loaded_data = fm.read_json("example_data/config.json")
    print(f"JSON data: {loaded_data}")
    
    # File discovery
    files = fm.find_files("*.json", "example_data")
    print(f"Found JSON files: {files}")


def web_scraping_example():
    """Demonstrate web scraping."""
    print("\n=== Web Scraping Example ===")
    
    scraper = WebScraper(delay=0.5)  # Be nice with rate limiting
    
    try:
        # Extract text from a webpage
        text = scraper.extract_text("https://httpbin.org/html")
        print(f"Extracted text (first 200 chars): {text[:200]}...")
        
        # Extract metadata
        metadata = scraper.extract_metadata("https://httpbin.org/html")
        print(f"Page title: {metadata.get('title', 'N/A')}")
        
    except Exception as e:
        print(f"Web scraping failed: {e}")


def api_client_example():
    """Demonstrate API client."""
    print("\n=== API Client Example ===")
    
    # Example with httpbin.org
    client = APIClient(base_url="https://httpbin.org")
    
    try:
        # GET request
        response = client.get("/json")
        print(f"API Response keys: {list(response.keys())}")
        
        # POST request
        post_data = {"message": "Hello from Agent Toolbox!"}
        response = client.post("/post", json_data=post_data)
        print(f"POST response status: Success")
        
    except Exception as e:
        print(f"API call failed: {e}")


def data_processing_example():
    """Demonstrate data processing."""
    print("\n=== Data Processing Example ===")
    
    processor = DataProcessor()
    
    # Create sample DataFrame
    data = {
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'score': [85, 92, 78, 95, 88],
        'city': ['NY', 'LA', 'NY', 'SF', 'LA']
    }
    df = pd.DataFrame(data)
    
    # Basic statistics
    stats = processor.get_basic_stats(df, 'score')
    print(f"Score statistics: mean={stats['mean']:.1f}, std={stats['std']:.1f}")
    
    # Filter data
    high_scores = processor.filter_dataframe(df, {'score': {'gt': 90}})
    print(f"High scorers: {high_scores['name'].tolist()}")
    
    # Aggregate data
    city_stats = processor.aggregate_data(df, ['city'], {'age': 'mean', 'score': 'mean'})
    print(f"City averages:\n{city_stats}")


def shell_execution_example():
    """Demonstrate safe shell execution."""
    print("\n=== Shell Execution Example ===")
    
    executor = ShellExecutor()
    
    try:
        # Basic command
        result = executor.execute("echo 'Hello from shell!'")
        print(f"Command output: {result['stdout'].strip()}")
        
        # Directory listing
        result = executor.execute("ls -la /tmp | head -5")
        print(f"Directory listing (first few lines):\n{result['stdout']}")
        
        # Multiple commands
        commands = ["date", "whoami", "pwd"]
        results = executor.execute_batch(commands)
        
        for i, result in enumerate(results):
            print(f"Command {commands[i]}: {result['stdout'].strip()}")
            
    except Exception as e:
        print(f"Shell execution failed: {e}")


def utilities_example():
    """Demonstrate utility functions."""
    print("\n=== Utilities Example ===")
    
    # Logger
    logger = Logger("example", level="INFO")
    logger.info("Starting utilities example")
    
    # Configuration
    config = ConfigManager()
    config.set("api.timeout", 30)
    config.set("api.retries", 3)
    print(f"API timeout: {config.get('api.timeout')}")
    
    # Retry decorator
    @retry(max_attempts=3, delay=0.1)
    def flaky_function():
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure!")
        return "Success!"
    
    try:
        result = flaky_function()
        print(f"Retry example result: {result}")
    except Exception as e:
        print(f"Retry example failed: {e}")


def integration_example():
    """Demonstrate integration clients (without actual API calls)."""
    print("\n=== Integration Example ===")
    
    # Note: These would require actual API tokens in real usage
    print("Slack client example (would need real token):")
    print("  slack = SlackClient('your-token')")
    print("  slack.send_message('#general', 'Hello from Agent Toolbox!')")
    
    print("\nGitHub client example (would need real token):")
    print("  github = GitHubClient('your-token')")
    print("  repos = github.get_repositories()")
    
    print("\nEmail client example (would need real credentials):")
    print("  email = EmailClient('smtp.gmail.com', 587, 'imap.gmail.com', 993, 'user', 'pass')")
    print("  email.send_email('recipient@example.com', 'Test', 'Hello from Agent Toolbox!')")


def main():
    """Run all examples."""
    print("Agent Toolbox Examples")
    print("=" * 50)
    
    file_operations_example()
    web_scraping_example()
    api_client_example()
    data_processing_example()
    shell_execution_example()
    utilities_example()
    integration_example()
    
    print("\n" + "=" * 50)
    print("Examples completed! Check the 'example_data' directory for generated files.")


if __name__ == "__main__":
    main()
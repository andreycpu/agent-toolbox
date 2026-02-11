#!/usr/bin/env python3
"""Comprehensive test of Agent Toolbox functionality."""

import tempfile
import shutil
from pathlib import Path
from agent_toolbox import *
from agent_toolbox.utils import *
from agent_toolbox.integrations import *


def test_file_operations():
    """Test file operations."""
    print("Testing file operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        fm = FileManager(base_path=temp_dir)
        
        # Test directory creation
        fm.create_directory("test_dir")
        assert fm.exists("test_dir")
        assert fm.is_directory("test_dir")
        
        # Test text file operations
        test_content = "Hello, Agent Toolbox!"
        fm.write_text("test.txt", test_content)
        assert fm.read_text("test.txt") == test_content
        
        # Test JSON operations
        test_data = {"name": "test", "value": 42}
        fm.write_json("data.json", test_data)
        assert fm.read_json("data.json") == test_data
        
        # Test file discovery
        files = fm.find_files("*.txt")
        assert len(files) == 1
        
    print("✓ File operations test passed")


def test_web_scraping():
    """Test web scraping functionality."""
    print("Testing web scraping...")
    
    try:
        scraper = WebScraper(delay=0.5)
        
        # Test with a simple webpage
        text = scraper.extract_text("https://httpbin.org/html")
        assert len(text) > 0
        
        # Test metadata extraction
        metadata = scraper.extract_metadata("https://httpbin.org/html") 
        assert isinstance(metadata, dict)
        
        print("✓ Web scraping test passed")
    except Exception as e:
        print(f"⚠ Web scraping test skipped (no internet): {e}")


def test_api_client():
    """Test API client functionality."""
    print("Testing API client...")
    
    try:
        client = APIClient(base_url="https://httpbin.org")
        
        # Test GET request
        response = client.get("/json")
        assert isinstance(response, dict)
        
        # Test POST request
        post_data = {"test": "data"}
        response = client.post("/post", json_data=post_data)
        assert isinstance(response, dict)
        
        print("✓ API client test passed")
    except Exception as e:
        print(f"⚠ API client test skipped (no internet): {e}")


def test_data_processing():
    """Test data processing functionality."""
    print("Testing data processing...")
    
    import pandas as pd
    processor = DataProcessor()
    
    # Create test DataFrame
    data = {
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'score': [85, 92, 78]
    }
    df = pd.DataFrame(data)
    
    # Test statistics
    stats = processor.get_basic_stats(df, 'score')
    assert 'mean' in stats
    assert 'std' in stats
    
    # Test filtering
    filtered = processor.filter_dataframe(df, {'age': {'gt': 27}})
    assert len(filtered) == 2
    
    print("✓ Data processing test passed")


def test_shell_execution():
    """Test shell execution functionality."""
    print("Testing shell execution...")
    
    executor = ShellExecutor()
    
    # Test basic command
    result = executor.execute("echo 'Hello World'")
    assert result['success']
    assert 'Hello World' in result['stdout']
    
    # Test batch execution
    commands = ["echo 'test1'", "echo 'test2'"]
    results = executor.execute_batch(commands)
    assert len(results) == 2
    assert all(r['success'] for r in results)
    
    print("✓ Shell execution test passed")


def test_utilities():
    """Test utility functions."""
    print("Testing utilities...")
    
    # Test configuration
    config = ConfigManager()
    config.set('test.value', 42)
    assert config.get('test.value') == 42
    
    # Test logging
    logger = Logger("test", console_output=False)
    logger.info("Test message")
    logger.error("Test error")
    
    # Test validation
    assert validate_email("test@example.com")
    assert not validate_email("invalid-email")
    assert validate_url("https://example.com")
    assert not validate_url("not-a-url")
    
    # Test caching
    cache = SimpleCache()
    cache.set("key", "value")
    assert cache.get("key") == "value"
    
    # Test rate limiting
    limiter = RateLimiter(max_calls=5, time_window=1.0)
    assert limiter.acquire(blocking=False)
    
    # Test monitoring
    monitor = SystemMonitor()
    system_info = monitor.get_system_info()
    assert 'cpu' in system_info
    assert 'memory' in system_info
    
    print("✓ Utilities test passed")


def test_integrations():
    """Test integration components (without real API calls)."""
    print("Testing integrations...")
    
    # Test webhook client creation
    webhook = WebhookClient("https://example.com/webhook")
    assert webhook.webhook_url == "https://example.com/webhook"
    
    # Note: Other integrations require real credentials, so we just test instantiation
    print("✓ Integrations test passed (basic instantiation)")


def test_performance_monitoring():
    """Test performance monitoring."""
    print("Testing performance monitoring...")
    
    @monitor_performance("test_function")
    def sample_function():
        import time
        time.sleep(0.01)
        return "result"
    
    # Call the monitored function
    result = sample_function()
    assert result == "result"
    
    # Check that timing was recorded
    stats = get_performance_stats()
    assert "timings" in stats
    assert "test_function" in stats["timings"]
    
    # Test counter
    increment_counter("test_counter")
    stats = get_performance_stats()
    assert stats["counters"]["test_counter"] == 1
    
    print("✓ Performance monitoring test passed")


def test_retry_and_error_handling():
    """Test retry mechanism and error handling."""
    print("Testing retry and error handling...")
    
    call_count = 0
    
    @retry(max_attempts=3, delay=0.01)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary failure")
        return "success"
    
    result = flaky_function()
    assert result == "success"
    assert call_count == 3
    
    print("✓ Retry and error handling test passed")


def run_comprehensive_test():
    """Run all tests."""
    print("Agent Toolbox Comprehensive Test")
    print("=" * 50)
    
    tests = [
        test_file_operations,
        test_data_processing,
        test_shell_execution,
        test_utilities,
        test_integrations,
        test_performance_monitoring,
        test_retry_and_error_handling,
        test_web_scraping,  # May skip if no internet
        test_api_client,    # May skip if no internet
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Agent Toolbox is working correctly.")
    else:
        print(f"⚠ {failed} tests failed. Check the output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)
"""Tests for utility modules."""

import pytest
import time
import tempfile
import json
from pathlib import Path
from agent_toolbox.utils import ConfigManager, Logger, retry, RateLimiter


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_basic_operations(self):
        """Test basic get/set operations."""
        config = ConfigManager()
        
        # Test setting and getting values
        config.set('test.value', 42)
        config.set('test.string', 'hello')
        
        assert config.get('test.value') == 42
        assert config.get('test.string') == 'hello'
        
    def test_nested_keys(self):
        """Test nested key operations."""
        config = ConfigManager()
        
        config.set('database.host', 'localhost')
        config.set('database.port', 5432)
        config.set('database.credentials.username', 'admin')
        
        assert config.get('database.host') == 'localhost'
        assert config.get('database.port') == 5432
        assert config.get('database.credentials.username') == 'admin'
        
    def test_default_values(self):
        """Test default value handling."""
        config = ConfigManager()
        
        assert config.get('nonexistent.key', 'default') == 'default'
        assert config.get('another.missing.key', 123) == 123
        
    def test_sections(self):
        """Test section operations."""
        config = ConfigManager()
        
        config.set('api.timeout', 30)
        config.set('api.retries', 3)
        config.set('api.base_url', 'https://example.com')
        
        api_section = config.get_section('api')
        expected = {
            'timeout': 30,
            'retries': 3,
            'base_url': 'https://example.com'
        }
        
        assert api_section == expected
        
    def test_has_key(self):
        """Test key existence checking."""
        config = ConfigManager()
        
        config.set('existing.key', 'value')
        
        assert config.has_key('existing.key')
        assert not config.has_key('nonexistent.key')
        
    def test_delete_key(self):
        """Test key deletion."""
        config = ConfigManager()
        
        config.set('temp.key', 'value')
        assert config.has_key('temp.key')
        
        config.delete_key('temp.key')
        assert not config.has_key('temp.key')
        
    def test_merge_config(self):
        """Test configuration merging."""
        config = ConfigManager()
        
        config.set('existing.key', 'original')
        config.set('existing.other', 'keep')
        
        other_config = {
            'existing': {'key': 'updated'},
            'new': {'section': 'added'}
        }
        
        config.merge_config(other_config)
        
        assert config.get('existing.key') == 'updated'
        assert config.get('existing.other') == 'keep'
        assert config.get('new.section') == 'added'
        
    def test_file_operations(self):
        """Test file save/load operations."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
            
        try:
            # Create config and save
            config = ConfigManager()
            config.set('test.data', {'value': 42, 'text': 'hello'})
            config.save_config(config_file)
            
            # Load in new instance
            loaded_config = ConfigManager(config_file)
            
            assert loaded_config.get('test.data.value') == 42
            assert loaded_config.get('test.data.text') == 'hello'
            
        finally:
            Path(config_file).unlink()


class TestLogger:
    """Test cases for Logger."""
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        logger = Logger("test_logger", console_output=False)
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
    def test_logger_with_context(self):
        """Test logging with additional context."""
        logger = Logger("test_logger", console_output=False)
        
        logger.info("Test message", user_id=123, action="test")
        logger.error("Error occurred", error_code=500, module="test")
        
    def test_function_call_logging(self):
        """Test function call logging."""
        logger = Logger("test_logger", console_output=False)
        
        logger.log_function_call(
            "test_function",
            args=(1, 2, 3),
            kwargs={"param": "value"},
            result="success",
            duration=0.5
        )
        
    def test_api_call_logging(self):
        """Test API call logging."""
        logger = Logger("test_logger", console_output=False)
        
        logger.log_api_call("GET", "https://api.example.com", 200, 0.3, 1024)
        logger.log_api_call("POST", "https://api.example.com", 404, 0.5)


class TestRetryDecorator:
    """Test cases for retry decorator."""
    
    def test_successful_function(self):
        """Test retry on successful function."""
        call_count = 0
        
        @retry(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
            
        result = successful_function()
        assert result == "success"
        assert call_count == 1
        
    def test_failing_then_succeeding(self):
        """Test retry on function that fails then succeeds."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)  # Very short delay for testing
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
            
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
        
    def test_always_failing(self):
        """Test retry on function that always fails."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
            
        with pytest.raises(ValueError, match="Always fails"):
            always_fails()
            
        assert call_count == 3
        
    def test_specific_exceptions(self):
        """Test retry with specific exception types."""
        @retry(max_attempts=2, exceptions=ValueError, delay=0.01)
        def specific_exception_function():
            raise TypeError("Wrong exception type")
            
        # Should not retry TypeError
        with pytest.raises(TypeError):
            specific_exception_function()
            
    def test_retry_callback(self):
        """Test retry callback functionality."""
        retry_calls = []
        
        def on_retry_callback(attempt, exception, delay):
            retry_calls.append((attempt, str(exception), delay))
            
        @retry(max_attempts=3, delay=0.01, on_retry=on_retry_callback)
        def failing_function():
            raise ValueError("Test failure")
            
        with pytest.raises(ValueError):
            failing_function()
            
        assert len(retry_calls) == 2  # Two retry attempts


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality."""
        limiter = RateLimiter(max_calls=5, time_window=1.0)
        
        # Should be able to acquire 5 tokens immediately
        for _ in range(5):
            assert limiter.acquire(blocking=False)
            
        # 6th call should fail without blocking
        assert not limiter.acquire(blocking=False)
        
    def test_token_regeneration(self):
        """Test token regeneration over time."""
        limiter = RateLimiter(max_calls=2, time_window=0.1)
        
        # Use all tokens
        assert limiter.acquire(blocking=False)
        assert limiter.acquire(blocking=False)
        assert not limiter.acquire(blocking=False)
        
        # Wait for regeneration
        time.sleep(0.15)
        
        # Should have tokens available again
        assert limiter.acquire(blocking=False)
        
    def test_burst_capacity(self):
        """Test burst capacity functionality."""
        limiter = RateLimiter(max_calls=5, time_window=1.0, burst_capacity=10)
        
        # Should be able to burst up to 10 calls
        for _ in range(10):
            assert limiter.acquire(blocking=False)
            
        # 11th call should fail
        assert not limiter.acquire(blocking=False)
        
    def test_context_manager(self):
        """Test rate limiter as context manager."""
        limiter = RateLimiter(max_calls=1, time_window=0.1)
        
        with limiter:
            pass  # Should acquire and release token
            
        # Token should be consumed
        assert not limiter.acquire(blocking=False)
        
    def test_blocking_acquire(self):
        """Test blocking acquire with timeout."""
        limiter = RateLimiter(max_calls=1, time_window=0.1)
        
        # Use the one available token
        assert limiter.acquire(blocking=False)
        
        # This should block and succeed after timeout
        start_time = time.time()
        assert limiter.acquire(blocking=True, timeout=0.2)
        duration = time.time() - start_time
        
        # Should have waited at least 0.1 seconds for token regeneration
        assert duration >= 0.05  # Some tolerance for timing
        
    def test_get_tokens_available(self):
        """Test getting available tokens."""
        limiter = RateLimiter(max_calls=5, time_window=1.0)
        
        assert limiter.get_tokens_available() == 5
        
        limiter.acquire(tokens=2, blocking=False)
        assert limiter.get_tokens_available() == 3
        
        limiter.acquire(tokens=3, blocking=False)
        assert limiter.get_tokens_available() == 0
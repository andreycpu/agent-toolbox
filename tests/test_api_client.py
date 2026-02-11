"""Tests for API client module."""

import pytest
import requests
import responses
from unittest.mock import Mock, patch
from agent_toolbox.api_client import (
    APIClient, APIError, APITimeoutError, 
    APIConnectionError, APIHTTPError
)


class TestAPIClient:
    """Test cases for APIClient."""
    
    def test_init_default(self):
        """Test APIClient initialization with defaults."""
        client = APIClient()
        assert client.base_url == ""
        assert client.timeout == 30
        assert client.retry_count == 3
        assert client.retry_delay == 1.0
        assert isinstance(client.session, requests.Session)
    
    def test_init_with_params(self):
        """Test APIClient initialization with custom parameters."""
        headers = {"Authorization": "Bearer token"}
        client = APIClient(
            base_url="https://api.example.com",
            headers=headers,
            timeout=60,
            retry_count=5,
            retry_delay=2.0
        )
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 60
        assert client.retry_count == 5
        assert client.retry_delay == 2.0
        assert "Authorization" in client.session.headers
    
    @responses.activate
    def test_successful_get_request(self):
        """Test successful GET request."""
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"status": "success"},
            status=200
        )
        
        client = APIClient(base_url="https://api.example.com")
        result = client.get("/test")
        assert result == {"status": "success"}
    
    @responses.activate
    def test_successful_post_request(self):
        """Test successful POST request."""
        responses.add(
            responses.POST,
            "https://api.example.com/test",
            json={"created": True},
            status=201
        )
        
        client = APIClient(base_url="https://api.example.com")
        result = client.post("/test", json_data={"name": "test"})
        assert result == {"created": True}
    
    @responses.activate
    def test_successful_put_request(self):
        """Test successful PUT request."""
        responses.add(
            responses.PUT,
            "https://api.example.com/test/1",
            json={"updated": True},
            status=200
        )
        
        client = APIClient(base_url="https://api.example.com")
        result = client.put("/test/1", json_data={"name": "updated"})
        assert result == {"updated": True}
    
    @responses.activate
    def test_successful_delete_request(self):
        """Test successful DELETE request."""
        responses.add(
            responses.DELETE,
            "https://api.example.com/test/1",
            json={"deleted": True},
            status=200
        )
        
        client = APIClient(base_url="https://api.example.com")
        result = client.delete("/test/1")
        assert result == {"deleted": True}
    
    @responses.activate
    def test_empty_response(self):
        """Test handling of empty responses."""
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            body="",
            status=204
        )
        
        client = APIClient(base_url="https://api.example.com")
        result = client.get("/test")
        assert result == {}
    
    @responses.activate
    def test_http_error_4xx(self):
        """Test handling of 4xx HTTP errors (no retry)."""
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"error": "Not found"},
            status=404
        )
        
        client = APIClient(base_url="https://api.example.com")
        with pytest.raises(APIHTTPError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 404
        assert "404" in str(exc_info.value)
    
    @responses.activate  
    def test_http_error_5xx_retry(self):
        """Test handling of 5xx HTTP errors (with retry)."""
        # First two attempts fail, third succeeds
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"error": "Server error"},
            status=500
        )
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"error": "Server error"},
            status=500
        )
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"success": True},
            status=200
        )
        
        client = APIClient(base_url="https://api.example.com", retry_delay=0.01)
        result = client.get("/test")
        assert result == {"success": True}
        assert len(responses.calls) == 3
    
    @responses.activate
    def test_http_error_5xx_max_retries(self):
        """Test 5xx error after max retries."""
        for _ in range(4):  # retry_count + 1
            responses.add(
                responses.GET,
                "https://api.example.com/test",
                json={"error": "Server error"},
                status=500
            )
        
        client = APIClient(base_url="https://api.example.com", retry_delay=0.01)
        with pytest.raises(APIHTTPError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 500
        assert len(responses.calls) == 4
    
    def test_timeout_error(self):
        """Test timeout error handling."""
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout()
            
            client = APIClient(retry_delay=0.01)
            with pytest.raises(APITimeoutError):
                client.get("/test")
    
    def test_connection_error(self):
        """Test connection error handling."""
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError()
            
            client = APIClient(retry_delay=0.01)
            with pytest.raises(APIConnectionError):
                client.get("/test")
    
    def test_auth_bearer_token(self):
        """Test Bearer token authentication."""
        client = APIClient()
        client.set_auth_bearer("test_token")
        assert client.session.headers["Authorization"] == "Bearer test_token"
    
    def test_auth_basic(self):
        """Test Basic authentication."""
        client = APIClient()
        client.set_auth_basic("user", "pass")
        assert client.session.auth is not None
    
    def test_auth_custom_header(self):
        """Test custom authentication header."""
        client = APIClient()
        client.set_auth_header("X-API-Key", "secret_key")
        assert client.session.headers["X-API-Key"] == "secret_key"
    
    def test_api_key_in_header(self):
        """Test API key in header."""
        client = APIClient()
        client.set_api_key("secret_key", "X-API-Key", in_header=True)
        assert client.session.headers["X-API-Key"] == "secret_key"
    
    def test_api_key_in_params(self):
        """Test API key in query parameters."""
        client = APIClient()
        client.set_api_key("secret_key", "api_key", in_header=False)
        assert hasattr(client, '_api_key_param')
        assert client._api_key_param == {"api_key": "secret_key"}
    
    def test_add_default_params(self):
        """Test adding default parameters."""
        client = APIClient()
        params = {"version": "v1", "format": "json"}
        client.add_default_params(params)
        assert client.session.params == params
    
    @responses.activate
    def test_url_joining(self):
        """Test URL joining for different base URL formats."""
        responses.add(responses.GET, "https://api.example.com/test", json={})
        
        # Test with trailing slash
        client1 = APIClient(base_url="https://api.example.com/")
        client1.get("/test")
        
        # Test without trailing slash
        client2 = APIClient(base_url="https://api.example.com")
        client2.get("/test")
        
        # Test endpoint without leading slash
        client3 = APIClient(base_url="https://api.example.com")
        client3.get("test")
        
        assert len(responses.calls) == 3
    
    def test_exponential_backoff(self):
        """Test exponential backoff in retry logic."""
        with patch('requests.Session.request') as mock_request, \
             patch('time.sleep') as mock_sleep:
            
            mock_request.side_effect = requests.exceptions.ConnectionError()
            
            client = APIClient(retry_count=3, retry_delay=1.0)
            
            with pytest.raises(APIConnectionError):
                client.get("/test")
            
            # Verify exponential backoff: 1.0, 2.0, 4.0
            expected_delays = [1.0, 2.0, 4.0]
            actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays
    
    @responses.activate
    def test_request_with_params(self):
        """Test GET request with query parameters."""
        def request_callback(request):
            assert "param1=value1" in request.url
            assert "param2=value2" in request.url
            return (200, {}, '{"success": true}')
        
        responses.add_callback(
            responses.GET,
            "https://api.example.com/test",
            callback=request_callback
        )
        
        client = APIClient(base_url="https://api.example.com")
        params = {"param1": "value1", "param2": "value2"}
        result = client.get("/test", params=params)
        assert result == {"success": True}
    
    @responses.activate
    def test_request_with_form_data(self):
        """Test POST request with form data."""
        def request_callback(request):
            assert request.headers['Content-Type'] == 'application/x-www-form-urlencoded'
            return (200, {}, '{"success": true}')
        
        responses.add_callback(
            responses.POST,
            "https://api.example.com/test",
            callback=request_callback
        )
        
        client = APIClient(base_url="https://api.example.com")
        data = {"key": "value"}
        result = client.post("/test", data=data)
        assert result == {"success": True}
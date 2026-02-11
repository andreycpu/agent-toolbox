"""API client utilities for common services and RESTful APIs."""

import requests
import json
import logging
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urljoin
import time


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class APITimeoutError(APIError):
    """Raised when API request times out."""
    pass


class APIConnectionError(APIError):
    """Raised when connection to API fails."""
    pass


class APIHTTPError(APIError):
    """Raised when API returns HTTP error status."""
    
    def __init__(self, message: str, status_code: int, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class APIClient:
    """Generic API client with common functionality."""
    
    def __init__(self, 
                 base_url: str = "",
                 headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30,
                 retry_count: int = 3,
                 retry_delay: float = 1.0):
        """Initialize API client."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        self.session = requests.Session()
        if headers:
            self.session.headers.update(headers)
            
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request with retry logic and proper error handling."""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        last_exception = None
        
        for attempt in range(self.retry_count + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                logger.debug(f"Request successful: {response.status_code}")
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = APITimeoutError(f"Request to {url} timed out after {self.timeout}s")
                logger.warning(f"Request timeout on attempt {attempt + 1}: {str(e)}")
                
            except requests.exceptions.ConnectionError as e:
                last_exception = APIConnectionError(f"Connection failed to {url}: {str(e)}")
                logger.warning(f"Connection error on attempt {attempt + 1}: {str(e)}")
                
            except requests.exceptions.HTTPError as e:
                response_text = e.response.text[:500] if e.response else ""
                last_exception = APIHTTPError(
                    f"HTTP {e.response.status_code} error for {url}: {str(e)}",
                    e.response.status_code,
                    response_text
                )
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e.response.status_code}")
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    break
                    
            except requests.RequestException as e:
                last_exception = APIError(f"Request failed to {url}: {str(e)}")
                logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < self.retry_count:
                sleep_time = self.retry_delay * (2 ** attempt)
                logger.debug(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        
        logger.error(f"All {self.retry_count + 1} attempts failed for {method} {url}")
        raise last_exception
                
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        response = self._make_request('GET', endpoint, params=params)
        return response.json() if response.content else {}
        
    def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        response = self._make_request('POST', endpoint, data=data, json=json_data)
        return response.json() if response.content else {}
        
    def put(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        response = self._make_request('PUT', endpoint, data=data, json=json_data)
        return response.json() if response.content else {}
        
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        response = self._make_request('DELETE', endpoint)
        return response.json() if response.content else {}
        
    def set_auth_bearer(self, token: str) -> None:
        """Set Bearer token authentication."""
        self.session.headers.update({'Authorization': f'Bearer {token}'})
        
    def set_auth_basic(self, username: str, password: str) -> None:
        """Set Basic authentication."""
        from requests.auth import HTTPBasicAuth
        self.session.auth = HTTPBasicAuth(username, password)
        
    def set_auth_header(self, header_name: str, header_value: str) -> None:
        """Set custom authentication header."""
        self.session.headers.update({header_name: header_value})
        
    def set_api_key(self, key: str, param_name: str = 'api_key', in_header: bool = False) -> None:
        """Set API key authentication."""
        if in_header:
            self.session.headers.update({param_name: key})
        else:
            # Store for query params - will be added in requests
            self._api_key_param = {param_name: key}
            
    def add_default_params(self, params: Dict[str, str]) -> None:
        """Add default parameters to all requests."""
        self.session.params = params
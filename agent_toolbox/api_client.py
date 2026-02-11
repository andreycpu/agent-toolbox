"""API client utilities for common services and RESTful APIs."""

import requests
import json
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urljoin
import time


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
        """Make an HTTP request with retry logic."""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        for attempt in range(self.retry_count + 1):
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == self.retry_count:
                    raise Exception(f"API request failed after {self.retry_count + 1} attempts: {str(e)}")
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                
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
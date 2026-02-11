"""Web scraping utilities for agent tasks."""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Union, Any
import time


class WebScraper:
    """Comprehensive web scraping utilities for agents."""
    
    def __init__(self, 
                 user_agent: str = "Agent-Toolbox/1.0",
                 timeout: int = 30,
                 delay: float = 1.0):
        """Initialize WebScraper with configuration."""
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """Get a web page with error handling."""
        try:
            time.sleep(self.delay)  # Rate limiting
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")
            
    def extract_text(self, url: str, clean: bool = True) -> str:
        """Extract all text content from a webpage."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if clean:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
        text = soup.get_text()
        
        if clean:
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
        return text
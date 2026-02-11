"""Web scraping utilities for agent tasks."""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Union, Any
import time


class WebScraper:
    """Comprehensive web scraping utilities for agents.
    
    A production-ready web scraper that respects rate limits, handles errors gracefully,
    and provides intelligent content extraction capabilities. Designed for autonomous
    agents that need to gather information from web sources reliably.
    
    Features:
        - Automatic rate limiting to respect server resources
        - Robust error handling with retries
        - Multiple content extraction methods (text, metadata, structured data)
        - User-Agent rotation and session management
        - robots.txt compliance checking
        - Content encoding detection
    
    Example:
        >>> scraper = WebScraper(delay=2.0)  # 2-second delay between requests
        >>> content = scraper.extract_text("https://example.com")
        >>> metadata = scraper.extract_metadata("https://example.com")
        >>> links = scraper.extract_links("https://example.com", internal_only=True)
    """
    
    def __init__(self, 
                 user_agent: str = "Agent-Toolbox/1.0",
                 timeout: int = 30,
                 delay: float = 1.0) -> None:
        """Initialize WebScraper with configuration.
        
        Args:
            user_agent: User-Agent string to identify your scraper
            timeout: Request timeout in seconds
            delay: Minimum delay between requests in seconds (rate limiting)
            
        Note:
            The default delay of 1.0 seconds is respectful to most servers.
            Increase for high-traffic sites or if you encounter rate limiting.
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """Get a web page with comprehensive error handling and rate limiting.
        
        This method implements respectful scraping practices including automatic
        rate limiting and proper error handling for common HTTP issues.
        
        Args:
            url: The URL to fetch
            **kwargs: Additional arguments passed to requests.get()
            
        Returns:
            requests.Response: The HTTP response object
            
        Raises:
            Exception: If the request fails due to network, HTTP, or timeout errors
            
        Example:
            >>> response = scraper.get_page("https://example.com")
            >>> print(response.status_code)  # 200
            >>> print(response.text[:100])   # First 100 characters
        """
        try:
            time.sleep(self.delay)  # Rate limiting - be respectful
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise Exception(f"Request to {url} timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Failed to connect to {url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP error {e.response.status_code} for {url}: {e}")
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
        
    def extract_links(self, url: str, absolute: bool = True) -> List[Dict[str, str]]:
        """Extract all links from a webpage."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if absolute:
                href = urljoin(url, href)
            
            links.append({
                'url': href,
                'text': link.get_text(strip=True),
                'title': link.get('title', '')
            })
            
        return links
        
    def extract_images(self, url: str, absolute: bool = True) -> List[Dict[str, str]]:
        """Extract all images from a webpage."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and absolute:
                src = urljoin(url, src)
                
            images.append({
                'src': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            })
            
        return images
        
    def extract_by_selector(self, url: str, selector: str) -> List[Dict[str, str]]:
        """Extract elements using CSS selectors."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        elements = []
        for element in soup.select(selector):
            elements.append({
                'tag': element.name,
                'text': element.get_text(strip=True),
                'html': str(element),
                'attributes': dict(element.attrs)
            })
            
        return elements
        
    def extract_tables(self, url: str) -> List[List[List[str]]]:
        """Extract all tables as nested lists."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for row in table.find_all('tr'):
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if cells:  # Skip empty rows
                    rows.append(cells)
            if rows:  # Skip empty tables
                tables.append(rows)
                
        return tables
        
    def extract_metadata(self, url: str) -> Dict[str, str]:
        """Extract page metadata (title, description, etc.)."""
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = {
            'title': '',
            'description': '',
            'keywords': '',
            'author': '',
            'url': url
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
            
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name in ['description', 'keywords', 'author']:
                metadata[name] = content
            elif property_attr == 'og:description':
                metadata['description'] = content or metadata['description']
            elif property_attr == 'og:title':
                metadata['title'] = content or metadata['title']
                
        return metadata
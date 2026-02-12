"""Advanced web tools for scraping, crawling, and analysis."""

import re
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set, Any, Union
from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import requests
import logging

from ..core.tool_base import BaseTool, AsyncBaseTool, ToolResult, ToolStatus, ToolValidationError
from ..core.tool_registry import tool_decorator
from ..utils.advanced_rate_limiter import get_global_rate_limiter, RateLimitConfig, RateLimitAlgorithm
from ..utils.advanced_cache import get_global_cache

logger = logging.getLogger(__name__)


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""
    
    max_pages: int = 100
    delay_between_requests: float = 1.0
    max_retries: int = 3
    timeout: float = 30.0
    follow_redirects: bool = True
    user_agent: str = "AgentToolbox/1.0"
    respect_robots_txt: bool = True
    max_depth: int = 3
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)


@tool_decorator(name="advanced_web_scraper", category="web", tags=["scraping", "html", "extraction"])
class AdvancedWebScraper(BaseTool):
    """Advanced web scraping tool with rate limiting and intelligent content extraction."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or ScrapingConfig()
        
        # Setup rate limiter
        rate_limiter = get_global_rate_limiter()
        rate_config = RateLimitConfig(
            max_requests=60,
            time_window=60.0,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET
        )
        rate_limiter.add_limiter("web_scraper", rate_config)
        
        # Setup cache
        self.cache = get_global_cache()
        
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate scraping parameters."""
        url = kwargs.get('url')
        if not url:
            raise ToolValidationError("URL is required", self.tool_id)
            
        # Validate URL format
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ToolValidationError(f"Invalid URL format: {url}", self.tool_id)
            
        # Check domain restrictions
        domain = parsed.netloc.lower()
        
        if self.config.blocked_domains and any(blocked in domain for blocked in self.config.blocked_domains):
            raise ToolValidationError(f"Domain {domain} is blocked", self.tool_id)
            
        if self.config.allowed_domains and not any(allowed in domain for allowed in self.config.allowed_domains):
            raise ToolValidationError(f"Domain {domain} is not in allowed list", self.tool_id)
            
        return {
            'url': url,
            'selectors': kwargs.get('selectors', {}),
            'extract_links': kwargs.get('extract_links', False),
            'follow_pagination': kwargs.get('follow_pagination', False),
            'max_pages': min(kwargs.get('max_pages', 1), self.config.max_pages)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute web scraping."""
        url = kwargs['url']
        selectors = kwargs['selectors']
        extract_links = kwargs['extract_links']
        follow_pagination = kwargs['follow_pagination']
        max_pages = kwargs['max_pages']
        
        # Check cache first
        cache_key = f"scrape:{url}:{hash(str(selectors))}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self._logger.info("Returning cached result")
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=cached_result
            )
            
        try:
            # Rate limit check
            rate_limiter = get_global_rate_limiter()
            if not rate_limiter.check_limits("web_scraper"):
                wait_time = rate_limiter.wait_time("web_scraper")
                time.sleep(wait_time)
                
            results = []
            visited_urls = set()
            urls_to_visit = [url]
            
            for page_num in range(max_pages):
                if not urls_to_visit:
                    break
                    
                current_url = urls_to_visit.pop(0)
                if current_url in visited_urls:
                    continue
                    
                visited_urls.add(current_url)
                
                # Scrape page
                page_data = self._scrape_page(current_url, selectors, extract_links)
                if page_data:
                    results.append(page_data)
                    
                    # Find pagination links if requested
                    if follow_pagination and page_num < max_pages - 1:
                        next_links = self._find_pagination_links(page_data.get('soup'), current_url)
                        for next_link in next_links:
                            if next_link not in visited_urls:
                                urls_to_visit.append(next_link)
                                
                # Respect rate limiting
                if page_num < max_pages - 1:
                    time.sleep(self.config.delay_between_requests)
                    
            result_data = {
                'url': url,
                'pages_scraped': len(results),
                'results': results
            }
            
            # Cache result
            self.cache.set(cache_key, result_data, ttl=3600)  # Cache for 1 hour
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _scrape_page(self, url: str, selectors: Dict[str, str], extract_links: bool) -> Optional[Dict[str, Any]]:
        """Scrape a single page."""
        try:
            # Make request
            headers = {'User-Agent': self.config.user_agent}
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.timeout,
                allow_redirects=self.config.follow_redirects
            )
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract data based on selectors
            extracted_data = {}
            for field, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        extracted_data[field] = elements[0].get_text(strip=True)
                    else:
                        extracted_data[field] = [elem.get_text(strip=True) for elem in elements]
                        
            # Extract all links if requested
            if extract_links:
                links = []
                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    links.append({
                        'url': absolute_url,
                        'text': link.get_text(strip=True),
                        'title': link.get('title', '')
                    })
                extracted_data['links'] = links
                
            # Extract metadata
            metadata = self._extract_page_metadata(soup)
            
            return {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'data': extracted_data,
                'metadata': metadata,
                'soup': soup  # For pagination analysis
            }
            
        except Exception as e:
            self._logger.error(f"Error scraping {url}: {str(e)}")
            return None
            
    def _extract_page_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract page metadata."""
        metadata = {}
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
                
        # Structured data (JSON-LD)
        json_scripts = soup.find_all('script', type='application/ld+json')
        structured_data = []
        for script in json_scripts:
            try:
                import json
                data = json.loads(script.string)
                structured_data.append(data)
            except:
                pass
        
        if structured_data:
            metadata['structured_data'] = structured_data
            
        return metadata
        
    def _find_pagination_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find pagination links."""
        pagination_selectors = [
            'a[rel="next"]',
            'a.next',
            'a.pagination-next',
            '.pagination a:contains("Next")',
            '.pagination a:contains(">")',
            'a[aria-label="Next"]'
        ]
        
        links = []
        for selector in pagination_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        absolute_url = urljoin(base_url, href)
                        links.append(absolute_url)
            except:
                continue
                
        return list(set(links))  # Remove duplicates


@tool_decorator(name="url_extractor", category="web", tags=["urls", "extraction", "links"])
class URLExtractor(BaseTool):
    """Extract and analyze URLs from text content."""
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate input parameters."""
        text = kwargs.get('text')
        if not text:
            raise ToolValidationError("Text content is required", self.tool_id)
            
        return {
            'text': text,
            'include_emails': kwargs.get('include_emails', False),
            'validate_urls': kwargs.get('validate_urls', True),
            'categorize': kwargs.get('categorize', True)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Extract URLs from text."""
        text = kwargs['text']
        include_emails = kwargs['include_emails']
        validate_urls = kwargs['validate_urls']
        categorize = kwargs['categorize']
        
        try:
            # URL pattern
            url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
            urls = re.findall(url_pattern, text, re.IGNORECASE)
            
            # Email pattern
            emails = []
            if include_emails:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, text)
                
            # Validate URLs
            valid_urls = []
            invalid_urls = []
            
            if validate_urls:
                for url in urls:
                    try:
                        parsed = urlparse(url)
                        if parsed.scheme and parsed.netloc:
                            valid_urls.append(url)
                        else:
                            invalid_urls.append(url)
                    except:
                        invalid_urls.append(url)
            else:
                valid_urls = urls
                
            # Categorize URLs
            categorized_urls = {}
            if categorize:
                for url in valid_urls:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    
                    # Determine category
                    if 'github.com' in domain:
                        category = 'code_repository'
                    elif any(social in domain for social in ['twitter.com', 'facebook.com', 'linkedin.com', 'instagram.com']):
                        category = 'social_media'
                    elif any(news in domain for news in ['news', 'cnn', 'bbc', 'reuters']):
                        category = 'news'
                    elif any(doc in domain for doc in ['docs.', 'documentation', 'wiki']):
                        category = 'documentation'
                    elif parsed.path.endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx')):
                        category = 'document'
                    elif parsed.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                        category = 'image'
                    elif parsed.path.endswith(('.mp4', '.avi', '.mov', '.webm')):
                        category = 'video'
                    else:
                        category = 'web_page'
                        
                    if category not in categorized_urls:
                        categorized_urls[category] = []
                    categorized_urls[category].append(url)
                    
            result_data = {
                'total_urls': len(urls),
                'valid_urls': valid_urls,
                'invalid_urls': invalid_urls,
                'emails': emails,
                'categorized_urls': categorized_urls,
                'statistics': {
                    'total_found': len(urls),
                    'valid_count': len(valid_urls),
                    'invalid_count': len(invalid_urls),
                    'email_count': len(emails),
                    'unique_domains': len(set(urlparse(url).netloc for url in valid_urls))
                }
            }
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )


@tool_decorator(name="sitemap_crawler", category="web", tags=["sitemap", "crawling", "discovery"])
class SitemapCrawler(BaseTool):
    """Crawl and analyze website sitemaps."""
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate input parameters."""
        domain = kwargs.get('domain')
        if not domain:
            raise ToolValidationError("Domain is required", self.tool_id)
            
        return {
            'domain': domain,
            'include_images': kwargs.get('include_images', False),
            'include_news': kwargs.get('include_news', False),
            'max_urls': kwargs.get('max_urls', 1000)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Crawl sitemap."""
        domain = kwargs['domain']
        include_images = kwargs['include_images']
        include_news = kwargs['include_news']
        max_urls = kwargs['max_urls']
        
        try:
            # Normalize domain
            if not domain.startswith(('http://', 'https://')):
                domain = f"https://{domain}"
                
            # Common sitemap locations
            sitemap_urls = [
                f"{domain}/sitemap.xml",
                f"{domain}/sitemap_index.xml",
                f"{domain}/sitemaps.xml",
                f"{domain}/sitemap/sitemap.xml",
                f"{domain}/robots.txt"  # Check for sitemap reference
            ]
            
            found_sitemaps = []
            all_urls = []
            
            for sitemap_url in sitemap_urls:
                try:
                    response = requests.get(sitemap_url, timeout=30)
                    response.raise_for_status()
                    
                    if 'robots.txt' in sitemap_url:
                        # Parse robots.txt for sitemap references
                        for line in response.text.split('\n'):
                            if line.lower().startswith('sitemap:'):
                                sitemap_ref = line.split(':', 1)[1].strip()
                                found_sitemaps.append(sitemap_ref)
                    else:
                        # Parse XML sitemap
                        urls = self._parse_sitemap(response.text, include_images, include_news)
                        if urls:
                            found_sitemaps.append(sitemap_url)
                            all_urls.extend(urls)
                            
                except requests.RequestException:
                    continue
                    
            # Remove duplicates and limit
            unique_urls = list(dict.fromkeys(all_urls))[:max_urls]
            
            # Analyze URLs
            analysis = self._analyze_urls(unique_urls)
            
            result_data = {
                'domain': domain,
                'sitemaps_found': found_sitemaps,
                'total_urls': len(unique_urls),
                'urls': unique_urls,
                'analysis': analysis
            }
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _parse_sitemap(self, xml_content: str, include_images: bool, include_news: bool) -> List[str]:
        """Parse sitemap XML content."""
        try:
            from xml.etree import ElementTree as ET
            
            root = ET.fromstring(xml_content)
            urls = []
            
            # Handle different sitemap namespaces
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Check if this is a sitemap index
            sitemapindex = root.findall('.//sitemap:sitemap', namespaces)
            if sitemapindex:
                # This is a sitemap index, crawl child sitemaps
                for sitemap in sitemapindex:
                    loc = sitemap.find('sitemap:loc', namespaces)
                    if loc is not None and loc.text:
                        try:
                            response = requests.get(loc.text, timeout=30)
                            response.raise_for_status()
                            child_urls = self._parse_sitemap(response.text, include_images, include_news)
                            urls.extend(child_urls)
                        except:
                            continue
            else:
                # This is a regular sitemap
                urlset = root.findall('.//sitemap:url', namespaces)
                for url_elem in urlset:
                    loc = url_elem.find('sitemap:loc', namespaces)
                    if loc is not None and loc.text:
                        urls.append(loc.text)
                        
                # Handle image sitemaps
                if include_images:
                    images = root.findall('.//image:image', namespaces)
                    for image in images:
                        loc = image.find('image:loc', namespaces)
                        if loc is not None and loc.text:
                            urls.append(loc.text)
                            
                # Handle news sitemaps  
                if include_news:
                    news_items = root.findall('.//news:news', namespaces)
                    for news in news_items:
                        # News items are associated with URLs, already captured above
                        pass
                        
            return urls
            
        except Exception as e:
            self._logger.error(f"Error parsing sitemap: {str(e)}")
            return []
            
    def _analyze_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Analyze discovered URLs."""
        analysis = {
            'total_urls': len(urls),
            'file_types': {},
            'url_patterns': {},
            'depth_distribution': {},
            'parameters': 0
        }
        
        for url in urls:
            parsed = urlparse(url)
            
            # File type analysis
            path = parsed.path.lower()
            if '.' in path:
                extension = path.split('.')[-1]
                analysis['file_types'][extension] = analysis['file_types'].get(extension, 0) + 1
            else:
                analysis['file_types']['no_extension'] = analysis['file_types'].get('no_extension', 0) + 1
                
            # URL depth
            depth = len([p for p in parsed.path.split('/') if p])
            analysis['depth_distribution'][str(depth)] = analysis['depth_distribution'].get(str(depth), 0) + 1
            
            # Parameters
            if parsed.query:
                analysis['parameters'] += 1
                
        return analysis


@tool_decorator(name="webpage_analyzer", category="web", tags=["analysis", "seo", "performance"])
class WebPageAnalyzer(BaseTool):
    """Analyze web pages for SEO, performance, and accessibility."""
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate input parameters."""
        url = kwargs.get('url')
        if not url:
            raise ToolValidationError("URL is required", self.tool_id)
            
        return {
            'url': url,
            'include_seo': kwargs.get('include_seo', True),
            'include_performance': kwargs.get('include_performance', True),
            'include_accessibility': kwargs.get('include_accessibility', True),
            'check_links': kwargs.get('check_links', False)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Analyze web page."""
        url = kwargs['url']
        include_seo = kwargs['include_seo']
        include_performance = kwargs['include_performance']
        include_accessibility = kwargs['include_accessibility']
        check_links = kwargs['check_links']
        
        try:
            # Fetch page
            start_time = time.time()
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            load_time = time.time() - start_time
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            analysis = {
                'url': url,
                'status_code': response.status_code,
                'load_time': load_time,
                'page_size': len(response.content)
            }
            
            if include_seo:
                analysis['seo'] = self._analyze_seo(soup, response)
                
            if include_performance:
                analysis['performance'] = self._analyze_performance(soup, response, load_time)
                
            if include_accessibility:
                analysis['accessibility'] = self._analyze_accessibility(soup)
                
            if check_links:
                analysis['links'] = self._check_links(soup, url)
                
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS,
                data=analysis
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _analyze_seo(self, soup: BeautifulSoup, response: requests.Response) -> Dict[str, Any]:
        """Analyze SEO factors."""
        seo = {}
        
        # Title
        title = soup.find('title')
        seo['title'] = {
            'text': title.string if title else '',
            'length': len(title.string) if title else 0,
            'optimal': 30 <= len(title.string) <= 60 if title else False
        }
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc_content = meta_desc.get('content') if meta_desc else ''
        seo['meta_description'] = {
            'content': desc_content,
            'length': len(desc_content),
            'optimal': 120 <= len(desc_content) <= 160
        }
        
        # Headings
        headings = {}
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            headings[f'h{i}'] = [h.get_text(strip=True) for h in h_tags]
            
        seo['headings'] = headings
        
        # Images without alt text
        images = soup.find_all('img')
        images_without_alt = [img.get('src') for img in images if not img.get('alt')]
        seo['images_without_alt'] = len(images_without_alt)
        seo['total_images'] = len(images)
        
        # Internal vs external links
        links = soup.find_all('a', href=True)
        parsed_url = urlparse(response.url)
        internal_links = 0
        external_links = 0
        
        for link in links:
            href = link['href']
            if href.startswith('http'):
                link_domain = urlparse(href).netloc
                if link_domain == parsed_url.netloc:
                    internal_links += 1
                else:
                    external_links += 1
            else:
                internal_links += 1
                
        seo['links'] = {
            'internal': internal_links,
            'external': external_links,
            'total': len(links)
        }
        
        return seo
        
    def _analyze_performance(self, soup: BeautifulSoup, response: requests.Response, load_time: float) -> Dict[str, Any]:
        """Analyze performance factors."""
        performance = {
            'load_time': load_time,
            'page_size_bytes': len(response.content),
            'page_size_kb': len(response.content) / 1024
        }
        
        # Count resources
        css_files = len(soup.find_all('link', rel='stylesheet'))
        js_files = len(soup.find_all('script', src=True))
        images = len(soup.find_all('img', src=True))
        
        performance['resources'] = {
            'css_files': css_files,
            'js_files': js_files,
            'images': images,
            'total': css_files + js_files + images
        }
        
        # Check for compression
        content_encoding = response.headers.get('content-encoding', '')
        performance['compression'] = {
            'enabled': bool(content_encoding),
            'type': content_encoding
        }
        
        # Check caching headers
        cache_control = response.headers.get('cache-control', '')
        expires = response.headers.get('expires', '')
        performance['caching'] = {
            'cache_control': cache_control,
            'expires': expires,
            'has_cache_headers': bool(cache_control or expires)
        }
        
        return performance
        
    def _analyze_accessibility(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze accessibility factors."""
        accessibility = {}
        
        # Images without alt text
        images = soup.find_all('img')
        missing_alt = sum(1 for img in images if not img.get('alt'))
        accessibility['images'] = {
            'total': len(images),
            'missing_alt': missing_alt,
            'alt_coverage': (len(images) - missing_alt) / len(images) if images else 1.0
        }
        
        # Form labels
        inputs = soup.find_all('input', type=lambda x: x not in ['hidden', 'submit'])
        labeled_inputs = 0
        for input_elem in inputs:
            input_id = input_elem.get('id')
            if input_id and soup.find('label', attrs={'for': input_id}):
                labeled_inputs += 1
            elif input_elem.find_parent('label'):
                labeled_inputs += 1
                
        accessibility['forms'] = {
            'total_inputs': len(inputs),
            'labeled_inputs': labeled_inputs,
            'label_coverage': labeled_inputs / len(inputs) if inputs else 1.0
        }
        
        # Semantic elements
        semantic_elements = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        found_semantic = {elem: len(soup.find_all(elem)) for elem in semantic_elements}
        accessibility['semantic_elements'] = found_semantic
        
        # ARIA attributes
        aria_elements = soup.find_all(attrs={'aria-label': True}) + soup.find_all(attrs={'aria-labelledby': True})
        accessibility['aria_labels'] = len(aria_elements)
        
        return accessibility
        
    def _check_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Check link validity."""
        links = soup.find_all('a', href=True)
        
        link_status = {
            'total': len(links),
            'working': 0,
            'broken': 0,
            'redirected': 0,
            'broken_links': []
        }
        
        for link in links[:50]:  # Limit to first 50 links to avoid long execution
            href = link['href']
            if href.startswith('#'):  # Skip anchors
                continue
                
            absolute_url = urljoin(base_url, href)
            
            try:
                response = requests.head(absolute_url, timeout=10, allow_redirects=True)
                if response.status_code < 400:
                    if response.history:
                        link_status['redirected'] += 1
                    else:
                        link_status['working'] += 1
                else:
                    link_status['broken'] += 1
                    link_status['broken_links'].append({
                        'url': absolute_url,
                        'status': response.status_code,
                        'text': link.get_text(strip=True)
                    })
                    
            except Exception as e:
                link_status['broken'] += 1
                link_status['broken_links'].append({
                    'url': absolute_url,
                    'error': str(e),
                    'text': link.get_text(strip=True)
                })
                
        return link_status
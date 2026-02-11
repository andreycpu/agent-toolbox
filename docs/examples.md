# Agent Toolbox Examples

This document provides comprehensive examples of using Agent Toolbox in various scenarios.

## Table of Contents

1. [Basic File Operations](#basic-file-operations)
2. [Web Scraping Workflows](#web-scraping-workflows)
3. [API Integration Patterns](#api-integration-patterns)
4. [Data Processing Pipelines](#data-processing-pipelines)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Error Handling and Resilience](#error-handling-and-resilience)
7. [Integration Examples](#integration-examples)
8. [Complete Agent Workflows](#complete-agent-workflows)

## Basic File Operations

### Managing Configuration Files

```python
from agent_toolbox import FileManager
from agent_toolbox.utils import ConfigManager

# Initialize managers
fm = FileManager(base_path="./config")
config = ConfigManager()

# Create configuration structure
fm.create_directory("environments")

# Write environment-specific configs
dev_config = {
    "database": {"host": "localhost", "port": 5432},
    "api": {"timeout": 30, "retries": 3}
}

prod_config = {
    "database": {"host": "prod.example.com", "port": 5432},
    "api": {"timeout": 60, "retries": 5}
}

fm.write_json("environments/dev.json", dev_config)
fm.write_json("environments/prod.json", prod_config)

# Load and merge configurations
env = "dev"  # or "prod"
env_config = fm.read_json(f"environments/{env}.json")
config.merge_config(env_config)

print(f"Database host: {config.get('database.host')}")
```

### Batch File Processing

```python
from agent_toolbox import FileManager, DataProcessor
import pandas as pd

fm = FileManager()
processor = DataProcessor()

# Find all CSV files
csv_files = fm.find_files("*.csv", "data/")

# Process each file
results = []
for csv_file in csv_files:
    try:
        # Load and analyze
        df = processor.load_csv(csv_file)
        
        # Get basic statistics
        stats = {
            'file': csv_file.name,
            'rows': len(df),
            'columns': len(df.columns),
            'memory_usage': df.memory_usage(deep=True).sum()
        }
        
        results.append(stats)
        
        # Clean and save processed version
        processed_name = f"processed_{csv_file.name}"
        processor.save_csv(df, f"processed/{processed_name}")
        
    except Exception as e:
        print(f"Error processing {csv_file}: {e}")

# Save processing report
fm.write_json("processing_report.json", results)
```

## Web Scraping Workflows

### News Monitoring System

```python
from agent_toolbox import WebScraper, FileManager
from agent_toolbox.utils import Logger, RateLimiter, monitor_performance
from datetime import datetime

class NewsMonitor:
    def __init__(self):
        self.scraper = WebScraper(delay=2.0)
        self.file_manager = FileManager(base_path="news_data")
        self.logger = Logger("NewsMonitor", log_file="news_monitor.log")
        self.rate_limiter = RateLimiter(max_calls=30, time_window=60)
        
        # Create data directories
        self.file_manager.create_directory("articles")
        self.file_manager.create_directory("reports")
    
    @monitor_performance("scrape_article")
    def scrape_article(self, url: str) -> dict:
        """Scrape a single news article."""
        with self.rate_limiter:
            self.logger.info(f"Scraping article: {url}")
            
            # Extract content
            text = self.scraper.extract_text(url)
            metadata = self.scraper.extract_metadata(url)
            
            return {
                "url": url,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "content": text,
                "scraped_at": datetime.now().isoformat(),
                "word_count": len(text.split())
            }
    
    def monitor_sources(self, sources: list):
        """Monitor multiple news sources."""
        articles = []
        
        for source in sources:
            try:
                # Get main page links
                links = self.scraper.extract_links(source["url"])
                
                # Filter for article links
                article_links = [
                    link["url"] for link in links 
                    if any(keyword in link["url"] for keyword in source.get("keywords", []))
                ][:5]  # Limit to 5 articles per source
                
                # Scrape articles
                for article_url in article_links:
                    article = self.scrape_article(article_url)
                    article["source"] = source["name"]
                    articles.append(article)
                    
            except Exception as e:
                self.logger.error(f"Failed to scrape {source['name']}: {e}")
        
        # Save articles
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_manager.write_json(f"articles/articles_{timestamp}.json", articles)
        
        # Generate report
        self.generate_report(articles, timestamp)
        
        return articles
    
    def generate_report(self, articles: list, timestamp: str):
        """Generate monitoring report."""
        report = {
            "timestamp": timestamp,
            "total_articles": len(articles),
            "sources": {},
            "avg_word_count": 0
        }
        
        # Analyze by source
        for article in articles:
            source = article["source"]
            if source not in report["sources"]:
                report["sources"][source] = {"count": 0, "total_words": 0}
            
            report["sources"][source]["count"] += 1
            report["sources"][source]["total_words"] += article["word_count"]
        
        # Calculate averages
        total_words = sum(article["word_count"] for article in articles)
        report["avg_word_count"] = total_words / len(articles) if articles else 0
        
        # Save report
        self.file_manager.write_json(f"reports/report_{timestamp}.json", report)
        self.logger.info(f"Generated report for {len(articles)} articles")

# Usage
sources = [
    {"name": "TechNews", "url": "https://technews.example.com", "keywords": ["article", "story"]},
    {"name": "Business", "url": "https://business.example.com", "keywords": ["news", "report"]}
]

monitor = NewsMonitor()
articles = monitor.monitor_sources(sources)
```

## API Integration Patterns

### Multi-Service API Aggregator

```python
from agent_toolbox import APIClient
from agent_toolbox.utils import retry, Logger, ConfigManager
from concurrent.futures import ThreadPoolExecutor
import time

class ServiceAggregator:
    def __init__(self):
        self.config = ConfigManager()
        self.logger = Logger("ServiceAggregator")
        self.services = {}
        
        # Initialize service clients
        self.setup_services()
    
    def setup_services(self):
        """Setup API clients for different services."""
        # Weather API
        self.services["weather"] = APIClient(
            base_url="https://api.weather.example.com",
            headers={"X-API-Key": self.config.get("weather.api_key", "")}
        )
        
        # News API
        self.services["news"] = APIClient(
            base_url="https://api.news.example.com",
            headers={"Authorization": f"Bearer {self.config.get('news.token', '')}"}
        )
        
        # Stock API
        self.services["stocks"] = APIClient(
            base_url="https://api.stocks.example.com"
        )
    
    @retry(max_attempts=3, delay=1.0)
    def fetch_weather(self, city: str) -> dict:
        """Fetch weather data for a city."""
        try:
            response = self.services["weather"].get(f"/current", params={"q": city})
            return {
                "service": "weather",
                "city": city,
                "temperature": response.get("temperature"),
                "description": response.get("description"),
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Weather API failed for {city}: {e}")
            return {"service": "weather", "city": city, "success": False, "error": str(e)}
    
    @retry(max_attempts=3, delay=1.0)
    def fetch_news(self, category: str) -> dict:
        """Fetch news for a category."""
        try:
            response = self.services["news"].get("/headlines", params={"category": category})
            return {
                "service": "news",
                "category": category,
                "articles": response.get("articles", [])[:5],  # Top 5
                "success": True
            }
        except Exception as e:
            self.logger.error(f"News API failed for {category}: {e}")
            return {"service": "news", "category": category, "success": False, "error": str(e)}
    
    @retry(max_attempts=3, delay=1.0)
    def fetch_stock(self, symbol: str) -> dict:
        """Fetch stock data for a symbol."""
        try:
            response = self.services["stocks"].get(f"/quote/{symbol}")
            return {
                "service": "stocks",
                "symbol": symbol,
                "price": response.get("price"),
                "change": response.get("change"),
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Stock API failed for {symbol}: {e}")
            return {"service": "stocks", "symbol": symbol, "success": False, "error": str(e)}
    
    def fetch_dashboard_data(self, cities: list, categories: list, symbols: list) -> dict:
        """Fetch data for dashboard from all services concurrently."""
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            futures = []
            
            # Weather tasks
            for city in cities:
                futures.append(executor.submit(self.fetch_weather, city))
            
            # News tasks
            for category in categories:
                futures.append(executor.submit(self.fetch_news, category))
            
            # Stock tasks
            for symbol in symbols:
                futures.append(executor.submit(self.fetch_stock, symbol))
            
            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Task failed: {e}")
                    results.append({"success": False, "error": str(e)})
        
        duration = time.time() - start_time
        
        # Organize results by service
        dashboard = {
            "weather": [r for r in results if r.get("service") == "weather"],
            "news": [r for r in results if r.get("service") == "news"],
            "stocks": [r for r in results if r.get("service") == "stocks"],
            "meta": {
                "fetch_duration": duration,
                "total_requests": len(results),
                "successful": len([r for r in results if r.get("success")])
            }
        }
        
        self.logger.info(f"Dashboard data fetched in {duration:.2f}s")
        return dashboard

# Usage
aggregator = ServiceAggregator()
dashboard = aggregator.fetch_dashboard_data(
    cities=["New York", "London"],
    categories=["technology", "business"],
    symbols=["AAPL", "GOOGL", "TSLA"]
)
```

This examples document provides comprehensive, real-world scenarios showing how to use Agent Toolbox effectively. Each example builds on the previous ones and demonstrates best practices for error handling, logging, and performance monitoring.

Would you like me to continue with more examples in the remaining sections?
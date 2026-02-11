#!/usr/bin/env python3
"""Advanced example: Building an agent workflow for web monitoring."""

from agent_toolbox import FileManager, WebScraper, DataProcessor
from agent_toolbox.utils import Logger, ConfigManager, retry, RateLimiter
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any


class WebMonitoringAgent:
    """Agent that monitors websites and analyzes changes."""
    
    def __init__(self, config_path: str = "monitoring_config.json"):
        """Initialize the monitoring agent."""
        self.logger = Logger("WebMonitor", log_file="logs/monitor.log")
        self.config = ConfigManager(config_path)
        self.file_manager = FileManager()
        self.scraper = WebScraper(delay=2.0)  # Be respectful with scraping
        self.processor = DataProcessor()
        self.rate_limiter = RateLimiter(max_calls=30, time_window=60.0)  # 30 calls per minute
        
        # Setup directories
        self.file_manager.create_directory("data/snapshots")
        self.file_manager.create_directory("data/reports")
        self.file_manager.create_directory("logs")
        
        self.logger.info("WebMonitoringAgent initialized")
        
    def load_websites(self) -> List[Dict[str, str]]:
        """Load list of websites to monitor from configuration."""
        websites = self.config.get('websites', [])
        if not websites:
            # Default websites if none configured
            websites = [
                {"name": "httpbin", "url": "https://httpbin.org/html", "selector": "h1"},
                {"name": "example", "url": "https://example.com", "selector": "h1"},
            ]
            self.config.set('websites', websites)
            
        self.logger.info(f"Loaded {len(websites)} websites to monitor")
        return websites
        
    @retry(max_attempts=3, delay=2.0)
    def scrape_website(self, website: Dict[str, str]) -> Dict[str, Any]:
        """Scrape a single website with retry logic."""
        self.logger.info(f"Scraping website: {website['name']}")
        
        # Rate limit requests
        self.rate_limiter.acquire()
        
        try:
            # Extract basic info
            metadata = self.scraper.extract_metadata(website['url'])
            text = self.scraper.extract_text(website['url'])
            
            # Extract specific elements if selector provided
            specific_content = ""
            if website.get('selector'):
                elements = self.scraper.extract_by_selector(website['url'], website['selector'])
                specific_content = " ".join([elem['text'] for elem in elements])
                
            result = {
                'website': website['name'],
                'url': website['url'],
                'timestamp': datetime.now().isoformat(),
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'content_length': len(text),
                'specific_content': specific_content,
                'text_preview': text[:500],  # First 500 chars
                'status': 'success'
            }
            
            self.logger.info(f"Successfully scraped {website['name']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to scrape {website['name']}", exception=e)
            return {
                'website': website['name'],
                'url': website['url'],
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            
    def save_snapshot(self, data: List[Dict[str, Any]]) -> str:
        """Save scraped data as a snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/snapshots/snapshot_{timestamp}.json"
        
        self.file_manager.write_json(filename, {
            'timestamp': timestamp,
            'snapshot_count': len(data),
            'data': data
        })
        
        self.logger.info(f"Saved snapshot to {filename}")
        return filename
        
    def analyze_changes(self, current_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze changes compared to previous snapshots."""
        self.logger.info("Analyzing changes from previous snapshots")
        
        # Find the most recent previous snapshot
        snapshots = self.file_manager.find_files("snapshot_*.json", "data/snapshots")
        if len(snapshots) < 2:
            self.logger.info("Not enough snapshots for comparison")
            return {'status': 'no_comparison', 'changes': []}
            
        # Sort by filename (timestamp) and get the second most recent
        snapshots.sort()
        previous_snapshot_path = snapshots[-2]
        
        try:
            previous_data = self.file_manager.read_json(previous_snapshot_path)
            previous_items = {item['website']: item for item in previous_data['data']}
            
            changes = []
            for current_item in current_data:
                website_name = current_item['website']
                
                if website_name in previous_items:
                    previous_item = previous_items[website_name]
                    
                    # Compare title changes
                    if current_item.get('title') != previous_item.get('title'):
                        changes.append({
                            'website': website_name,
                            'type': 'title_change',
                            'old': previous_item.get('title', ''),
                            'new': current_item.get('title', ''),
                            'timestamp': current_item['timestamp']
                        })
                        
                    # Compare content length changes (significant change = >10%)
                    old_length = previous_item.get('content_length', 0)
                    new_length = current_item.get('content_length', 0)
                    
                    if old_length > 0:
                        change_percent = abs(new_length - old_length) / old_length
                        if change_percent > 0.1:  # 10% change threshold
                            changes.append({
                                'website': website_name,
                                'type': 'content_length_change',
                                'old_length': old_length,
                                'new_length': new_length,
                                'change_percent': round(change_percent * 100, 2),
                                'timestamp': current_item['timestamp']
                            })
                            
                    # Compare specific content if available
                    old_specific = previous_item.get('specific_content', '')
                    new_specific = current_item.get('specific_content', '')
                    
                    if old_specific != new_specific and (old_specific or new_specific):
                        changes.append({
                            'website': website_name,
                            'type': 'specific_content_change',
                            'old': old_specific,
                            'new': new_specific,
                            'timestamp': current_item['timestamp']
                        })
                        
            analysis_result = {
                'status': 'completed',
                'comparison_snapshot': str(previous_snapshot_path),
                'total_changes': len(changes),
                'changes': changes
            }
            
            self.logger.info(f"Found {len(changes)} changes")
            return analysis_result
            
        except Exception as e:
            self.logger.error("Failed to analyze changes", exception=e)
            return {'status': 'error', 'error': str(e)}
            
    def generate_report(self, snapshot_data: List[Dict[str, Any]], 
                       analysis_data: Dict[str, Any]) -> str:
        """Generate a monitoring report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"data/reports/report_{timestamp}.md"
        
        # Build report content
        report = f"""# Website Monitoring Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- Websites monitored: {len(snapshot_data)}
- Total changes detected: {analysis_data.get('total_changes', 0)}

## Website Status
"""
        
        for site in snapshot_data:
            status_emoji = "✅" if site['status'] == 'success' else "❌"
            report += f"- {status_emoji} **{site['website']}**: {site.get('title', 'No title')}\n"
            if site['status'] == 'error':
                report += f"  - Error: {site.get('error', 'Unknown error')}\n"
            else:
                report += f"  - Content length: {site.get('content_length', 0)} characters\n"
            report += f"  - URL: {site['url']}\n\n"
            
        if analysis_data.get('changes'):
            report += "## Changes Detected\n\n"
            
            for change in analysis_data['changes']:
                report += f"### {change['website']}\n"
                report += f"- **Type**: {change['type'].replace('_', ' ').title()}\n"
                
                if change['type'] == 'title_change':
                    report += f"- **Old**: {change['old']}\n"
                    report += f"- **New**: {change['new']}\n"
                elif change['type'] == 'content_length_change':
                    report += f"- **Old length**: {change['old_length']}\n"
                    report += f"- **New length**: {change['new_length']}\n"
                    report += f"- **Change**: {change['change_percent']}%\n"
                elif change['type'] == 'specific_content_change':
                    report += f"- **Old content**: {change['old'][:100]}...\n"
                    report += f"- **New content**: {change['new'][:100]}...\n"
                    
                report += f"- **Timestamp**: {change['timestamp']}\n\n"
        else:
            report += "## No Changes Detected\n\nAll monitored websites remain unchanged.\n"
            
        # Save report
        self.file_manager.write_text(report_filename, report)
        self.logger.info(f"Generated report: {report_filename}")
        
        return report_filename
        
    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run a complete monitoring cycle."""
        self.logger.info("Starting monitoring cycle")
        start_time = time.time()
        
        try:
            # Load websites to monitor
            websites = self.load_websites()
            
            # Scrape all websites
            snapshot_data = []
            for website in websites:
                result = self.scrape_website(website)
                snapshot_data.append(result)
                
            # Save snapshot
            snapshot_file = self.save_snapshot(snapshot_data)
            
            # Analyze changes
            analysis_data = self.analyze_changes(snapshot_data)
            
            # Generate report
            report_file = self.generate_report(snapshot_data, analysis_data)
            
            duration = time.time() - start_time
            
            result = {
                'status': 'success',
                'duration': round(duration, 2),
                'snapshot_file': snapshot_file,
                'report_file': report_file,
                'websites_monitored': len(websites),
                'changes_detected': analysis_data.get('total_changes', 0)
            }
            
            self.logger.info(f"Monitoring cycle completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error("Monitoring cycle failed", exception=e)
            return {'status': 'error', 'error': str(e)}


def main():
    """Main function to run the monitoring agent."""
    print("Web Monitoring Agent")
    print("=" * 50)
    
    agent = WebMonitoringAgent()
    
    # Run monitoring cycle
    result = agent.run_monitoring_cycle()
    
    print(f"\nMonitoring Results:")
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        print(f"Duration: {result['duration']}s")
        print(f"Websites monitored: {result['websites_monitored']}")
        print(f"Changes detected: {result['changes_detected']}")
        print(f"Report saved to: {result['report_file']}")
        
        # Display report content
        fm = FileManager()
        if fm.exists(result['report_file']):
            print(f"\n--- Report Content ---")
            report_content = fm.read_text(result['report_file'])
            print(report_content)
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
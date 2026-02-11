"""Webhook client for sending HTTP webhook notifications."""

import json
import time
from typing import Dict, List, Optional, Any, Union
from ..api_client import APIClient
from ..utils import Logger, retry


class WebhookClient:
    """Client for sending webhook notifications."""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None,
                 timeout: int = 30, user_agent: str = "Agent-Toolbox-Webhook/1.0"):
        """Initialize webhook client."""
        self.webhook_url = webhook_url
        self.secret = secret
        self.timeout = timeout
        self.user_agent = user_agent
        self.logger = Logger("WebhookClient")
        
        # Setup API client
        headers = {"User-Agent": user_agent, "Content-Type": "application/json"}
        self.client = APIClient(base_url="", headers=headers, timeout=timeout)
        
    def _generate_signature(self, payload: str) -> Optional[str]:
        """Generate HMAC signature for payload if secret is provided."""
        if not self.secret:
            return None
            
        import hmac
        import hashlib
        
        signature = hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
        
    @retry(max_attempts=3, delay=1.0)
    def send_webhook(self, payload: Dict[str, Any], 
                    event_type: Optional[str] = None,
                    timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Send webhook with payload."""
        
        # Prepare webhook payload
        webhook_data = {
            "timestamp": timestamp or time.time(),
            "event_type": event_type or "notification",
            "data": payload
        }
        
        payload_str = json.dumps(webhook_data, separators=(',', ':'))
        
        # Prepare headers
        headers = {}
        if self.secret:
            signature = self._generate_signature(payload_str)
            if signature:
                headers["X-Webhook-Signature"] = signature
                
        try:
            self.logger.info(f"Sending webhook to {self.webhook_url}", 
                           event_type=event_type)
            
            response = self.client.session.post(
                self.webhook_url,
                data=payload_str,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = {
                "success": True,
                "status_code": response.status_code,
                "response_text": response.text[:1000],  # Limit response text
                "webhook_url": self.webhook_url
            }
            
            self.logger.info("Webhook sent successfully", 
                           status_code=response.status_code)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Webhook failed: {e}", exception=e)
            return {
                "success": False,
                "error": str(e),
                "webhook_url": self.webhook_url
            }
            
    def send_alert(self, message: str, level: str = "info", 
                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send alert notification via webhook."""
        payload = {
            "alert": {
                "message": message,
                "level": level,
                "context": context or {}
            }
        }
        
        return self.send_webhook(payload, event_type="alert")
        
    def send_metric(self, metric_name: str, value: Union[int, float],
                   tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send metric data via webhook."""
        payload = {
            "metric": {
                "name": metric_name,
                "value": value,
                "tags": tags or {},
                "timestamp": time.time()
            }
        }
        
        return self.send_webhook(payload, event_type="metric")
        
    def send_log_entry(self, message: str, level: str = "info",
                      logger_name: str = "agent", 
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send log entry via webhook."""
        payload = {
            "log": {
                "message": message,
                "level": level,
                "logger": logger_name,
                "context": context or {},
                "timestamp": time.time()
            }
        }
        
        return self.send_webhook(payload, event_type="log")
        
    def test_connection(self) -> Dict[str, Any]:
        """Test webhook connection with a ping."""
        payload = {
            "test": {
                "message": "Webhook connection test",
                "client": "Agent Toolbox WebhookClient"
            }
        }
        
        return self.send_webhook(payload, event_type="test")
"""Simple HTTP server for receiving webhooks and API requests."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Callable, Optional
import threading
from ..utils import Logger


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhooks."""
    
    def __init__(self, *args, webhook_callback=None, **kwargs):
        """Initialize handler with webhook callback."""
        self.webhook_callback = webhook_callback
        self.logger = Logger("WebhookHandler")
        super().__init__(*args, **kwargs)
        
    def do_POST(self):
        """Handle POST requests."""
        try:
            # Parse content
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse JSON if content type indicates it
            content_type = self.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError:
                    data = {"raw": post_data.decode('utf-8')}
            else:
                data = {"raw": post_data.decode('utf-8')}
                
            # Prepare request info
            request_info = {
                "method": "POST",
                "path": self.path,
                "headers": dict(self.headers),
                "data": data,
                "remote_addr": self.client_address[0]
            }
            
            # Call webhook callback
            if self.webhook_callback:
                response_data = self.webhook_callback(request_info)
            else:
                response_data = {"status": "received"}
                
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
            self.logger.info(f"Webhook received from {self.client_address[0]}")
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
            
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        
        request_info = {
            "method": "GET",
            "path": parsed.path,
            "query": query_params,
            "headers": dict(self.headers),
            "remote_addr": self.client_address[0]
        }
        
        # Simple health check
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')


class SimpleHTTPServer:
    """Simple HTTP server for receiving webhooks."""
    
    def __init__(self, port: int = 8080, host: str = 'localhost',
                 webhook_callback: Optional[Callable] = None):
        """Initialize HTTP server."""
        self.port = port
        self.host = host
        self.webhook_callback = webhook_callback
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.logger = Logger("SimpleHTTPServer")
        
    def start(self, blocking: bool = False) -> None:
        """Start the HTTP server."""
        def handler_factory(*args, **kwargs):
            return WebhookHandler(*args, webhook_callback=self.webhook_callback, **kwargs)
            
        self.server = HTTPServer((self.host, self.port), handler_factory)
        
        if blocking:
            self.logger.info(f"Starting HTTP server on {self.host}:{self.port}")
            self.server.serve_forever()
        else:
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            self.server_thread.start()
            self.logger.info(f"HTTP server started on {self.host}:{self.port}")
            
    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.logger.info("HTTP server stopped")
            
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
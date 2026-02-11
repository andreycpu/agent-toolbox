"""Integration modules for popular services and APIs."""

from .slack_client import SlackClient
from .github_client import GitHubClient
from .email_client import EmailClient
from .database_client import DatabaseClient
from .webhook_client import WebhookClient
from .http_server import SimpleHTTPServer

__all__ = [
    "SlackClient",
    "GitHubClient", 
    "EmailClient",
    "DatabaseClient",
    "WebhookClient",
    "SimpleHTTPServer",
]
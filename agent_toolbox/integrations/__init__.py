"""Integration modules for popular services and APIs."""

from .slack_client import SlackClient
from .github_client import GitHubClient
from .email_client import EmailClient
from .database_client import DatabaseClient

__all__ = [
    "SlackClient",
    "GitHubClient", 
    "EmailClient",
    "DatabaseClient",
]
"""Validation utilities for input checking and data validation."""

import re
import ipaddress
from typing import Any, List, Dict, Optional, Union, Callable
from urllib.parse import urlparse
import email.utils


def validate_email(email_addr: str) -> bool:
    """Validate email address format."""
    try:
        # Use email.utils for basic validation
        parsed = email.utils.parseaddr(email_addr)
        if not parsed[1]:
            return False
            
        # Additional regex validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, parsed[1]) is not None
    except:
        return False


def validate_url(url: str, schemes: Optional[List[str]] = None) -> bool:
    """Validate URL format and scheme."""
    if schemes is None:
        schemes = ['http', 'https']
        
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in schemes and
            parsed.netloc and
            len(parsed.netloc) > 0
        )
    except:
        return False


def validate_ip_address(ip: str, version: Optional[int] = None) -> bool:
    """Validate IP address format."""
    try:
        addr = ipaddress.ip_address(ip)
        if version is None:
            return True
        return addr.version == version
    except ValueError:
        return False
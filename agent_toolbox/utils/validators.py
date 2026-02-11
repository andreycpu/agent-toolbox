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


def validate_phone(phone: str, country_code: Optional[str] = None) -> bool:
    """Validate phone number format (basic validation)."""
    # Remove common formatting
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Basic validation patterns
    if country_code == 'US':
        # US phone number: +1XXXXXXXXXX or 1XXXXXXXXXX or XXXXXXXXXX
        pattern = r'^(\+?1)?[0-9]{10}$'
    else:
        # International: must start with + and have 7-15 digits
        pattern = r'^\+[1-9][0-9]{6,14}$'
        
    return re.match(pattern, cleaned) is not None


def validate_json(json_str: str) -> bool:
    """Validate JSON string format."""
    import json
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_regex(pattern: str) -> bool:
    """Validate regex pattern syntax."""
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False
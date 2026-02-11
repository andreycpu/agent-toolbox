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


def validate_range(value: Union[int, float], 
                  min_val: Optional[Union[int, float]] = None,
                  max_val: Optional[Union[int, float]] = None) -> bool:
    """Validate numeric value is within range."""
    try:
        num_value = float(value)
        if min_val is not None and num_value < min_val:
            return False
        if max_val is not None and num_value > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_length(value: Union[str, List, Dict], 
                   min_length: Optional[int] = None,
                   max_length: Optional[int] = None) -> bool:
    """Validate length of string, list, or dictionary."""
    try:
        length = len(value)
        if min_length is not None and length < min_length:
            return False
        if max_length is not None and length > max_length:
            return False
        return True
    except TypeError:
        return False


def validate_type(value: Any, expected_type: type) -> bool:
    """Validate value is of expected type."""
    return isinstance(value, expected_type)


def validate_not_empty(value: Any) -> bool:
    """Validate value is not None or empty."""
    if value is None:
        return False
    if hasattr(value, '__len__'):
        return len(value) > 0
    return True


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_with_schema(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate data against a schema and return list of errors."""
    errors = []
    
    for field, rules in schema.items():
        value = data.get(field)
        field_errors = []
        
        # Check required
        if rules.get('required', False) and not validate_not_empty(value):
            field_errors.append(f"{field} is required")
            continue
            
        # Skip validation if field is not required and empty
        if not validate_not_empty(value) and not rules.get('required', False):
            continue
            
        # Type validation
        if 'type' in rules and not validate_type(value, rules['type']):
            field_errors.append(f"{field} must be of type {rules['type'].__name__}")
            
        # Length validation
        if 'min_length' in rules or 'max_length' in rules:
            if not validate_length(value, rules.get('min_length'), rules.get('max_length')):
                field_errors.append(f"{field} length is invalid")
                
        # Range validation for numbers
        if 'min_value' in rules or 'max_value' in rules:
            if not validate_range(value, rules.get('min_value'), rules.get('max_value')):
                field_errors.append(f"{field} value is out of range")
                
        # Custom validator
        if 'validator' in rules:
            validator_func = rules['validator']
            if callable(validator_func) and not validator_func(value):
                field_errors.append(f"{field} failed custom validation")
                
        errors.extend(field_errors)
        
    return errors
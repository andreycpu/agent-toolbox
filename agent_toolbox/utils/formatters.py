"""Formatting utilities for data presentation."""

from typing import Any, Dict, List, Union, Optional
import json
from datetime import datetime, timedelta


def format_bytes(bytes_value: int, decimal_places: int = 2) -> str:
    """Format bytes as human-readable string."""
    if bytes_value == 0:
        return "0 B"
        
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    
    while bytes_value >= 1024 and i < len(size_names) - 1:
        bytes_value /= 1024.0
        i += 1
        
    return f"{bytes_value:.{decimal_places}f} {size_names[i]}"


def format_duration(seconds: float, precision: int = 2) -> str:
    """Format duration in seconds as human-readable string."""
    if seconds < 0:
        return "0s"
        
    units = [
        ("d", 86400),  # days
        ("h", 3600),   # hours  
        ("m", 60),     # minutes
        ("s", 1),      # seconds
    ]
    
    parts = []
    remaining = abs(seconds)
    
    for unit_name, unit_seconds in units:
        if remaining >= unit_seconds:
            value = int(remaining // unit_seconds)
            remaining = remaining % unit_seconds
            parts.append(f"{value}{unit_name}")
            
        if len(parts) >= precision:
            break
            
    if not parts and seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif not parts:
        return f"{seconds:.2f}s"
        
    return " ".join(parts)


def format_number(number: Union[int, float], precision: int = 2) -> str:
    """Format number with thousand separators."""
    if isinstance(number, int):
        return f"{number:,}"
    else:
        return f"{number:,.{precision}f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format decimal as percentage."""
    return f"{value * 100:.{decimal_places}f}%"


def format_json(data: Any, indent: int = 2, sort_keys: bool = True) -> str:
    """Format data as pretty-printed JSON."""
    return json.dumps(data, indent=indent, sort_keys=sort_keys, default=str)


def format_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
    """Format list of dictionaries as ASCII table."""
    if not data:
        return "No data"
        
    # Get headers
    if headers is None:
        headers = list(data[0].keys())
        
    # Calculate column widths
    col_widths = {}
    for header in headers:
        col_widths[header] = len(str(header))
        
    for row in data:
        for header in headers:
            value = str(row.get(header, ''))
            col_widths[header] = max(col_widths[header], len(value))
            
    # Build table
    lines = []
    
    # Header line
    header_line = "| " + " | ".join(h.ljust(col_widths[h]) for h in headers) + " |"
    lines.append(header_line)
    
    # Separator line
    sep_line = "| " + " | ".join("-" * col_widths[h] for h in headers) + " |"
    lines.append(sep_line)
    
    # Data lines
    for row in data:
        data_line = "| " + " | ".join(str(row.get(h, '')).ljust(col_widths[h]) for h in headers) + " |"
        lines.append(data_line)
        
    return "\n".join(lines)


def format_list(items: List[Any], bullet: str = "•", indent: int = 2) -> str:
    """Format list as bulleted text."""
    if not items:
        return "No items"
        
    lines = []
    for item in items:
        line = " " * indent + bullet + " " + str(item)
        lines.append(line)
        
    return "\n".join(lines)
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
"""Logging utilities for agents."""

import logging
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any
import json
from datetime import datetime


class Logger:
    """Enhanced logging utility with multiple output formats."""
    
    def __init__(self, name: str = "agent-toolbox", 
                 level: str = "INFO",
                 log_file: Optional[Union[str, Path]] = None,
                 console_output: bool = True,
                 json_format: bool = False):
        """Initialize logger with configuration."""
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.json_format = json_format
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup formatters
        if json_format:
            formatter = self._get_json_formatter()
        else:
            formatter = self._get_standard_formatter()
            
        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
        # Add file handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
    def _get_standard_formatter(self) -> logging.Formatter:
        """Get standard text formatter."""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter."""
        return JsonFormatter()
        
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
        
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        if exception:
            kwargs['exception_type'] = type(exception).__name__
            kwargs['exception_message'] = str(exception)
            
        self._log(logging.ERROR, message, **kwargs)
        
        if exception:
            self.logger.exception("Exception details:")
            
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)
        
    def _log(self, level: int, message: str, **kwargs) -> None:
        """Internal logging method with extra context."""
        if self.json_format and kwargs:
            # For JSON format, include extra data
            self.logger.log(level, message, extra={'context': kwargs})
        else:
            # For standard format, append context to message
            if kwargs:
                context_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
                message = f"{message} | {context_str}"
            self.logger.log(level, message)
            
    def log_function_call(self, func_name: str, args: tuple, kwargs: dict, 
                         result: Any = None, duration: Optional[float] = None) -> None:
        """Log function call details."""
        log_data = {
            'function': func_name,
            'args': str(args),
            'kwargs': str(kwargs),
        }
        
        if result is not None:
            log_data['result_type'] = type(result).__name__
            
        if duration is not None:
            log_data['duration_ms'] = round(duration * 1000, 2)
            
        self.info(f"Function call: {func_name}", **log_data)
        
    def log_api_call(self, method: str, url: str, status_code: int,
                    duration: float, response_size: Optional[int] = None) -> None:
        """Log API call details."""
        log_data = {
            'method': method,
            'url': url,
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2)
        }
        
        if response_size is not None:
            log_data['response_size_bytes'] = response_size
            
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self._log(level, f"API call: {method} {url}", **log_data)
        
    def add_file_handler(self, log_file: Union[str, Path]) -> None:
        """Add additional file handler."""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        formatter = self._get_json_formatter() if self.json_format else self._get_standard_formatter()
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    def set_level(self, level: str) -> None:
        """Change logging level."""
        self.logger.setLevel(getattr(logging, level.upper()))


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra context if available
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)
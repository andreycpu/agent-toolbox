"""Agent Toolbox: A comprehensive toolkit of reusable agent tools and utilities."""

__version__ = "0.2.0"
__author__ = "Agent Development Team"
__email__ = "dev@agent-toolbox.io"

# Legacy imports for backward compatibility
from .file_operations import FileManager
from .web_scraping import WebScraper
from .api_client import APIClient
from .data_processing import DataProcessor
from .shell_execution import ShellExecutor

# New core infrastructure
from .core import (
    BaseTool, AsyncBaseTool, ToolResult, ToolStatus, ToolError,
    ToolRegistry, ToolComposer, ToolChain,
    ExecutionContext, SandboxEnvironment,
    get_global_registry, register_tool, tool_decorator
)

# Advanced utilities
from .utils.advanced_rate_limiter import get_global_rate_limiter, rate_limit
from .utils.advanced_cache import get_global_cache, cached
from .utils.error_recovery import with_retry, with_circuit_breaker, resilient
from .utils.analytics import get_global_analytics, track_tool_usage

# Import submodules for convenience
from . import integrations
from . import utils
from . import core
from . import tools

__all__ = [
    # Legacy tools
    "FileManager",
    "WebScraper", 
    "APIClient",
    "DataProcessor",
    "ShellExecutor",
    
    # Core infrastructure
    "BaseTool",
    "AsyncBaseTool", 
    "ToolResult",
    "ToolStatus",
    "ToolError",
    "ToolRegistry",
    "ToolComposer",
    "ToolChain",
    "ExecutionContext",
    "SandboxEnvironment",
    "get_global_registry",
    "register_tool",
    "tool_decorator",
    
    # Utilities
    "get_global_rate_limiter",
    "rate_limit",
    "get_global_cache",
    "cached", 
    "with_retry",
    "with_circuit_breaker",
    "resilient",
    "get_global_analytics",
    "track_tool_usage",
    
    # Modules
    "integrations",
    "utils",
    "core",
    "tools",
]
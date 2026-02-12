"""Base classes for all agent tools."""

import abc
import uuid
import time
from typing import Any, Dict, Optional, Union, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolResult(Generic[T]):
    """Result of tool execution."""
    
    tool_id: str
    status: ToolStatus
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    
    @property
    def success(self) -> bool:
        """Check if tool execution was successful."""
        return self.status == ToolStatus.SUCCESS
        
    @property
    def failed(self) -> bool:
        """Check if tool execution failed."""
        return self.status == ToolStatus.FAILED


class ToolError(Exception):
    """Base exception for tool-related errors."""
    
    def __init__(self, message: str, tool_id: str = "", error_code: str = ""):
        super().__init__(message)
        self.tool_id = tool_id
        self.error_code = error_code


class ToolValidationError(ToolError):
    """Raised when tool input validation fails."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""
    pass


class ToolTimeoutError(ToolError):
    """Raised when tool execution times out."""
    pass


class BaseTool(abc.ABC):
    """Base class for all agent tools."""
    
    def __init__(self, 
                 tool_id: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 version: str = "1.0.0",
                 timeout: Optional[float] = None):
        """Initialize the tool."""
        self.tool_id = tool_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.description = description or self.__doc__ or ""
        self.version = version
        self.timeout = timeout
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
        
    @abc.abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
        
    @abc.abstractmethod
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate input parameters and return cleaned parameters."""
        pass
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata for discovery and registration."""
        return {
            'tool_id': self.tool_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'timeout': self.timeout,
            'class_name': self.__class__.__name__,
            'module': self.__module__
        }
        
    def run(self, **kwargs) -> ToolResult:
        """Run the tool with full lifecycle management."""
        start_time = time.time()
        
        try:
            # Validate input
            validated_params = self.validate_input(**kwargs)
            
            # Create pending result
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.PENDING,
                metadata={'input_params': list(validated_params.keys())}
            )
            
            # Execute tool
            self._logger.info(f"Executing tool {self.name}")
            result.status = ToolStatus.RUNNING
            
            # Call actual implementation
            execution_result = self.execute(**validated_params)
            
            # Update with execution result
            result.data = execution_result.data if execution_result else None
            result.status = ToolStatus.SUCCESS
            result.execution_time = time.time() - start_time
            
            self._logger.info(f"Tool {self.name} completed successfully in {result.execution_time:.2f}s")
            return result
            
        except ToolValidationError as e:
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=f"Validation error: {str(e)}",
                execution_time=time.time() - start_time
            )
            self._logger.error(f"Tool {self.name} validation failed: {str(e)}")
            return result
            
        except ToolTimeoutError as e:
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED, 
                error=f"Timeout error: {str(e)}",
                execution_time=time.time() - start_time
            )
            self._logger.error(f"Tool {self.name} timed out: {str(e)}")
            return result
            
        except Exception as e:
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time
            )
            self._logger.error(f"Tool {self.name} execution failed: {str(e)}", exc_info=True)
            return result
            
    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"
        
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id='{self.tool_id}', name='{self.name}')>"


class AsyncBaseTool(BaseTool):
    """Base class for asynchronous tools."""
    
    @abc.abstractmethod
    async def execute_async(self, **kwargs) -> ToolResult:
        """Execute the tool asynchronously."""
        pass
        
    async def run_async(self, **kwargs) -> ToolResult:
        """Run the tool asynchronously with full lifecycle management."""
        start_time = time.time()
        
        try:
            # Validate input
            validated_params = self.validate_input(**kwargs)
            
            # Create pending result
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.PENDING,
                metadata={'input_params': list(validated_params.keys())}
            )
            
            # Execute tool
            self._logger.info(f"Executing async tool {self.name}")
            result.status = ToolStatus.RUNNING
            
            # Call actual implementation
            execution_result = await self.execute_async(**validated_params)
            
            # Update with execution result
            result.data = execution_result.data if execution_result else None
            result.status = ToolStatus.SUCCESS
            result.execution_time = time.time() - start_time
            
            self._logger.info(f"Async tool {self.name} completed successfully in {result.execution_time:.2f}s")
            return result
            
        except Exception as e:
            result = ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )
            self._logger.error(f"Async tool {self.name} execution failed: {str(e)}", exc_info=True)
            return result
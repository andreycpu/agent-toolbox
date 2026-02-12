"""Tool composition and chaining utilities."""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
import logging

from .tool_base import BaseTool, AsyncBaseTool, ToolResult, ToolStatus, ToolError
from .tool_registry import get_global_registry

logger = logging.getLogger(__name__)


@dataclass
class ChainStep:
    """A single step in a tool chain."""
    
    tool: Union[str, BaseTool]  # Tool name or instance
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[[ToolResult], bool]] = None  # Condition for execution
    error_handler: Optional[Callable[[ToolResult], ToolResult]] = None
    output_mapping: Optional[Dict[str, str]] = None  # Map output to next tool's input
    
    
class ToolChain:
    """Chain multiple tools together in sequence."""
    
    def __init__(self, name: str = "", description: str = ""):
        """Initialize the tool chain."""
        self.name = name
        self.description = description
        self.steps: List[ChainStep] = []
        self.results: List[ToolResult] = []
        self._logger = logging.getLogger(f"{__name__}.{self.name or 'Chain'}")
        
    def add_step(self, 
                 tool: Union[str, BaseTool],
                 params: Optional[Dict[str, Any]] = None,
                 condition: Optional[Callable[[ToolResult], bool]] = None,
                 error_handler: Optional[Callable[[ToolResult], ToolResult]] = None,
                 output_mapping: Optional[Dict[str, str]] = None) -> 'ToolChain':
        """Add a step to the chain."""
        
        step = ChainStep(
            tool=tool,
            params=params or {},
            condition=condition,
            error_handler=error_handler,
            output_mapping=output_mapping
        )
        
        self.steps.append(step)
        return self  # For method chaining
        
    def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> List[ToolResult]:
        """Execute the tool chain."""
        self.results = []
        context = initial_data or {}
        registry = get_global_registry()
        
        self._logger.info(f"Executing chain '{self.name}' with {len(self.steps)} steps")
        
        for i, step in enumerate(self.steps):
            self._logger.debug(f"Executing step {i + 1}: {step.tool}")
            
            # Get tool instance
            if isinstance(step.tool, str):
                tool_instance = registry.create_tool_instance(step.tool)
                if not tool_instance:
                    error_result = ToolResult(
                        tool_id=f"chain_step_{i}",
                        status=ToolStatus.FAILED,
                        error=f"Tool '{step.tool}' not found in registry"
                    )
                    self.results.append(error_result)
                    break
            else:
                tool_instance = step.tool
                
            # Check condition if provided
            if step.condition and self.results:
                last_result = self.results[-1]
                if not step.condition(last_result):
                    self._logger.info(f"Skipping step {i + 1} due to condition")
                    continue
                    
            # Prepare parameters
            params = step.params.copy()
            
            # Apply output mapping from previous step
            if step.output_mapping and self.results:
                last_result = self.results[-1]
                if last_result.success and last_result.data:
                    for output_key, input_key in step.output_mapping.items():
                        if isinstance(last_result.data, dict) and output_key in last_result.data:
                            params[input_key] = last_result.data[output_key]
                            
            # Add context data to params
            params.update(context)
            
            # Execute the tool
            try:
                result = tool_instance.run(**params)
                self.results.append(result)
                
                # Update context with result data
                if result.success and result.data:
                    if isinstance(result.data, dict):
                        context.update(result.data)
                    else:
                        context['last_result'] = result.data
                        
                # Handle failure
                if result.failed:
                    if step.error_handler:
                        result = step.error_handler(result)
                        self.results[-1] = result
                        
                    if result.failed:
                        self._logger.error(f"Chain failed at step {i + 1}: {result.error}")
                        break
                        
            except Exception as e:
                error_result = ToolResult(
                    tool_id=tool_instance.tool_id,
                    status=ToolStatus.FAILED,
                    error=f"Unexpected error: {str(e)}"
                )
                
                if step.error_handler:
                    error_result = step.error_handler(error_result)
                    
                self.results.append(error_result)
                
                if error_result.failed:
                    self._logger.error(f"Chain failed at step {i + 1}: {str(e)}")
                    break
                    
        success_count = sum(1 for r in self.results if r.success)
        self._logger.info(f"Chain completed: {success_count}/{len(self.results)} steps successful")
        
        return self.results
        
    async def execute_async(self, initial_data: Optional[Dict[str, Any]] = None) -> List[ToolResult]:
        """Execute the tool chain asynchronously."""
        self.results = []
        context = initial_data or {}
        registry = get_global_registry()
        
        self._logger.info(f"Executing async chain '{self.name}' with {len(self.steps)} steps")
        
        for i, step in enumerate(self.steps):
            self._logger.debug(f"Executing async step {i + 1}: {step.tool}")
            
            # Get tool instance
            if isinstance(step.tool, str):
                tool_instance = registry.create_tool_instance(step.tool)
                if not tool_instance:
                    error_result = ToolResult(
                        tool_id=f"chain_step_{i}",
                        status=ToolStatus.FAILED,
                        error=f"Tool '{step.tool}' not found in registry"
                    )
                    self.results.append(error_result)
                    break
            else:
                tool_instance = step.tool
                
            # Check condition if provided
            if step.condition and self.results:
                last_result = self.results[-1]
                if not step.condition(last_result):
                    self._logger.info(f"Skipping async step {i + 1} due to condition")
                    continue
                    
            # Prepare parameters
            params = step.params.copy()
            
            # Apply output mapping from previous step
            if step.output_mapping and self.results:
                last_result = self.results[-1]
                if last_result.success and last_result.data:
                    for output_key, input_key in step.output_mapping.items():
                        if isinstance(last_result.data, dict) and output_key in last_result.data:
                            params[input_key] = last_result.data[output_key]
                            
            # Add context data to params
            params.update(context)
            
            # Execute the tool (async if possible)
            try:
                if isinstance(tool_instance, AsyncBaseTool):
                    result = await tool_instance.run_async(**params)
                else:
                    result = tool_instance.run(**params)
                    
                self.results.append(result)
                
                # Update context with result data
                if result.success and result.data:
                    if isinstance(result.data, dict):
                        context.update(result.data)
                    else:
                        context['last_result'] = result.data
                        
                # Handle failure
                if result.failed:
                    if step.error_handler:
                        result = step.error_handler(result)
                        self.results[-1] = result
                        
                    if result.failed:
                        self._logger.error(f"Async chain failed at step {i + 1}: {result.error}")
                        break
                        
            except Exception as e:
                error_result = ToolResult(
                    tool_id=tool_instance.tool_id,
                    status=ToolStatus.FAILED,
                    error=f"Unexpected error: {str(e)}"
                )
                
                if step.error_handler:
                    error_result = step.error_handler(error_result)
                    
                self.results.append(error_result)
                
                if error_result.failed:
                    self._logger.error(f"Async chain failed at step {i + 1}: {str(e)}")
                    break
                    
        success_count = sum(1 for r in self.results if r.success)
        self._logger.info(f"Async chain completed: {success_count}/{len(self.results)} steps successful")
        
        return self.results


class ToolComposer:
    """Compose tools in various patterns (parallel, conditional, etc.)."""
    
    @staticmethod
    def parallel(*tools: Union[str, BaseTool], **kwargs) -> List[ToolResult]:
        """Execute tools in parallel (for sync tools)."""
        import concurrent.futures
        
        registry = get_global_registry()
        results = []
        
        def execute_tool(tool):
            if isinstance(tool, str):
                tool_instance = registry.create_tool_instance(tool)
                if not tool_instance:
                    return ToolResult(
                        tool_id=f"parallel_{tool}",
                        status=ToolStatus.FAILED,
                        error=f"Tool '{tool}' not found in registry"
                    )
            else:
                tool_instance = tool
                
            return tool_instance.run(**kwargs)
            
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(execute_tool, tool) for tool in tools]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        logger.info(f"Parallel execution completed: {len(results)} tools")
        return results
        
    @staticmethod
    async def parallel_async(*tools: Union[str, BaseTool], **kwargs) -> List[ToolResult]:
        """Execute tools in parallel (async)."""
        registry = get_global_registry()
        
        async def execute_tool(tool):
            if isinstance(tool, str):
                tool_instance = registry.create_tool_instance(tool)
                if not tool_instance:
                    return ToolResult(
                        tool_id=f"parallel_{tool}",
                        status=ToolStatus.FAILED,
                        error=f"Tool '{tool}' not found in registry"
                    )
            else:
                tool_instance = tool
                
            if isinstance(tool_instance, AsyncBaseTool):
                return await tool_instance.run_async(**kwargs)
            else:
                return tool_instance.run(**kwargs)
                
        tasks = [execute_tool(tool) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = ToolResult(
                    tool_id=f"parallel_{i}",
                    status=ToolStatus.FAILED,
                    error=str(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
                
        logger.info(f"Parallel async execution completed: {len(processed_results)} tools")
        return processed_results
        
    @staticmethod
    def conditional(condition: Callable[[], bool], 
                   true_tool: Union[str, BaseTool],
                   false_tool: Optional[Union[str, BaseTool]] = None,
                   **kwargs) -> ToolResult:
        """Execute tool based on condition."""
        registry = get_global_registry()
        
        if condition():
            tool_to_execute = true_tool
        elif false_tool:
            tool_to_execute = false_tool
        else:
            return ToolResult(
                tool_id="conditional",
                status=ToolStatus.SUCCESS,
                data={"message": "Condition not met, no tool executed"}
            )
            
        if isinstance(tool_to_execute, str):
            tool_instance = registry.create_tool_instance(tool_to_execute)
            if not tool_instance:
                return ToolResult(
                    tool_id="conditional",
                    status=ToolStatus.FAILED,
                    error=f"Tool '{tool_to_execute}' not found in registry"
                )
        else:
            tool_instance = tool_to_execute
            
        return tool_instance.run(**kwargs)
        
    @staticmethod
    def retry_on_failure(tool: Union[str, BaseTool], 
                        max_retries: int = 3,
                        delay: float = 1.0,
                        **kwargs) -> ToolResult:
        """Execute tool with retry on failure."""
        import time
        
        registry = get_global_registry()
        
        if isinstance(tool, str):
            tool_instance = registry.create_tool_instance(tool)
            if not tool_instance:
                return ToolResult(
                    tool_id="retry",
                    status=ToolStatus.FAILED,
                    error=f"Tool '{tool}' not found in registry"
                )
        else:
            tool_instance = tool
            
        last_result = None
        
        for attempt in range(max_retries + 1):
            result = tool_instance.run(**kwargs)
            
            if result.success:
                logger.info(f"Tool succeeded on attempt {attempt + 1}")
                return result
                
            last_result = result
            
            if attempt < max_retries:
                logger.warning(f"Tool failed on attempt {attempt + 1}, retrying in {delay}s")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                
        logger.error(f"Tool failed after {max_retries + 1} attempts")
        return last_result
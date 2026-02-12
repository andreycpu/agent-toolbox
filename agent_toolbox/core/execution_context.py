"""Execution context for tools with state and resource management."""

import uuid
import time
import threading
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class Resource:
    """Represents a resource that can be acquired and released."""
    
    name: str
    resource_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    acquired_at: Optional[float] = None
    acquired_by: Optional[str] = None
    
    @property
    def is_acquired(self) -> bool:
        """Check if resource is currently acquired."""
        return self.acquired_by is not None


class ExecutionContext:
    """Execution context for tool runs with state and resource management."""
    
    def __init__(self, 
                 context_id: Optional[str] = None,
                 parent_context: Optional['ExecutionContext'] = None,
                 max_resources: int = 100):
        """Initialize execution context."""
        self.context_id = context_id or str(uuid.uuid4())
        self.parent_context = parent_context
        self.max_resources = max_resources
        
        # State management
        self.state: Dict[str, Any] = {}
        self.shared_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        
        # Resource management
        self.resources: Dict[str, Resource] = {}
        self.acquired_resources: Set[str] = set()
        
        # Execution tracking
        self.start_time = time.time()
        self.tool_calls: List[Dict[str, Any]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        self._logger = logging.getLogger(f"{__name__}.{self.context_id[:8]}")
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        with self._lock:
            return self.state.get(key, default)
            
    def set_state(self, key: str, value: Any) -> None:
        """Set a state value."""
        with self._lock:
            self.state[key] = value
            
    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values."""
        with self._lock:
            self.state.update(updates)
            
    def get_shared_state(self, key: str, default: Any = None) -> Any:
        """Get a shared state value (accessible by child contexts)."""
        with self._lock:
            # Check local shared state first
            if key in self.shared_state:
                return self.shared_state[key]
            
            # Check parent context if available
            if self.parent_context:
                return self.parent_context.get_shared_state(key, default)
                
            return default
            
    def set_shared_state(self, key: str, value: Any) -> None:
        """Set a shared state value."""
        with self._lock:
            self.shared_state[key] = value
            
    def register_resource(self, 
                         name: str, 
                         resource_type: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a resource for management."""
        with self._lock:
            if name in self.resources:
                self._logger.warning(f"Resource '{name}' already registered")
                return False
                
            if len(self.resources) >= self.max_resources:
                self._logger.error(f"Maximum resources ({self.max_resources}) reached")
                return False
                
            resource = Resource(
                name=name,
                resource_type=resource_type,
                metadata=metadata or {}
            )
            
            self.resources[name] = resource
            self._logger.debug(f"Registered resource: {name} ({resource_type})")
            return True
            
    def acquire_resource(self, name: str, tool_id: Optional[str] = None) -> bool:
        """Acquire a resource for exclusive use."""
        with self._lock:
            if name not in self.resources:
                self._logger.error(f"Resource '{name}' not registered")
                return False
                
            resource = self.resources[name]
            
            if resource.is_acquired:
                self._logger.warning(f"Resource '{name}' already acquired by {resource.acquired_by}")
                return False
                
            resource.acquired_at = time.time()
            resource.acquired_by = tool_id or "unknown"
            self.acquired_resources.add(name)
            
            self._logger.debug(f"Acquired resource: {name} by {resource.acquired_by}")
            return True
            
    def release_resource(self, name: str) -> bool:
        """Release a resource."""
        with self._lock:
            if name not in self.resources:
                self._logger.error(f"Resource '{name}' not registered")
                return False
                
            resource = self.resources[name]
            
            if not resource.is_acquired:
                self._logger.warning(f"Resource '{name}' not currently acquired")
                return False
                
            resource.acquired_at = None
            resource.acquired_by = None
            self.acquired_resources.discard(name)
            
            self._logger.debug(f"Released resource: {name}")
            return True
            
    def release_all_resources(self) -> int:
        """Release all acquired resources."""
        with self._lock:
            released_count = 0
            for resource_name in list(self.acquired_resources):
                if self.release_resource(resource_name):
                    released_count += 1
                    
            self._logger.info(f"Released {released_count} resources")
            return released_count
            
    @contextmanager
    def acquire_resource_context(self, name: str, tool_id: Optional[str] = None):
        """Context manager for resource acquisition."""
        acquired = self.acquire_resource(name, tool_id)
        
        if not acquired:
            raise RuntimeError(f"Failed to acquire resource: {name}")
            
        try:
            yield
        finally:
            self.release_resource(name)
            
    def record_tool_call(self, 
                        tool_name: str,
                        tool_id: str,
                        params: Dict[str, Any],
                        result: Optional[Dict[str, Any]] = None,
                        execution_time: Optional[float] = None) -> None:
        """Record a tool call for tracking."""
        with self._lock:
            call_record = {
                'tool_name': tool_name,
                'tool_id': tool_id,
                'params': params.copy() if params else {},
                'result': result.copy() if result else None,
                'execution_time': execution_time,
                'timestamp': time.time()
            }
            
            self.tool_calls.append(call_record)
            self._logger.debug(f"Recorded tool call: {tool_name} ({tool_id})")
            
    def get_tool_call_history(self, 
                             tool_name: Optional[str] = None,
                             limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tool call history."""
        with self._lock:
            calls = self.tool_calls
            
            if tool_name:
                calls = [c for c in calls if c['tool_name'] == tool_name]
                
            if limit:
                calls = calls[-limit:]
                
            return calls.copy()
            
    def get_context_stats(self) -> Dict[str, Any]:
        """Get context execution statistics."""
        with self._lock:
            total_execution_time = sum(
                call.get('execution_time', 0) 
                for call in self.tool_calls 
                if call.get('execution_time')
            )
            
            return {
                'context_id': self.context_id,
                'uptime': time.time() - self.start_time,
                'tool_calls_count': len(self.tool_calls),
                'total_execution_time': total_execution_time,
                'resources_registered': len(self.resources),
                'resources_acquired': len(self.acquired_resources),
                'state_keys': len(self.state),
                'shared_state_keys': len(self.shared_state)
            }
            
    def create_child_context(self, 
                           context_id: Optional[str] = None) -> 'ExecutionContext':
        """Create a child context that inherits from this one."""
        child = ExecutionContext(
            context_id=context_id,
            parent_context=self,
            max_resources=self.max_resources
        )
        
        # Copy shared state
        with self._lock:
            child.shared_state.update(self.shared_state)
            
        self._logger.debug(f"Created child context: {child.context_id[:8]}")
        return child
        
    def cleanup(self) -> None:
        """Clean up context resources."""
        with self._lock:
            # Release all resources
            released = self.release_all_resources()
            
            # Clear state
            self.state.clear()
            self.shared_state.clear()
            
            self._logger.info(
                f"Context cleanup completed: released {released} resources, "
                f"cleared {len(self.state)} state entries"
            )
            
    def __enter__(self) -> 'ExecutionContext':
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        
    def __str__(self) -> str:
        return f"ExecutionContext({self.context_id[:8]})"
        
    def __repr__(self) -> str:
        stats = self.get_context_stats()
        return (f"<ExecutionContext(id='{self.context_id}', "
                f"calls={stats['tool_calls_count']}, "
                f"resources={stats['resources_registered']})>")


# Global context registry
_context_registry: Dict[str, ExecutionContext] = {}
_registry_lock = threading.RLock()


def get_context(context_id: str) -> Optional[ExecutionContext]:
    """Get a context by ID."""
    with _registry_lock:
        return _context_registry.get(context_id)


def register_context(context: ExecutionContext) -> None:
    """Register a context globally."""
    with _registry_lock:
        _context_registry[context.context_id] = context
        

def unregister_context(context_id: str) -> bool:
    """Unregister a context."""
    with _registry_lock:
        if context_id in _context_registry:
            del _context_registry[context_id]
            return True
        return False


def list_contexts() -> List[str]:
    """List all registered context IDs."""
    with _registry_lock:
        return list(_context_registry.keys())


@contextmanager
def execution_context(context_id: Optional[str] = None,
                     parent_context: Optional[ExecutionContext] = None,
                     auto_register: bool = True):
    """Context manager for execution context lifecycle."""
    context = ExecutionContext(context_id, parent_context)
    
    if auto_register:
        register_context(context)
        
    try:
        yield context
    finally:
        if auto_register:
            unregister_context(context.context_id)
        context.cleanup()
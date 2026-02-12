"""Tool registry for discovery and management."""

import importlib
import inspect
import json
import os
from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .tool_base import BaseTool, AsyncBaseTool

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Tool metadata for registry."""
    
    name: str
    tool_class: Type[BaseTool]
    module_path: str
    description: str = ""
    version: str = "1.0.0"
    category: str = "general"
    tags: List[str] = None
    dependencies: List[str] = None
    is_async: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['tool_class'] = f"{self.tool_class.__module__}.{self.tool_class.__name__}"
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tool':
        """Create Tool from dictionary."""
        # Import the tool class
        module_path, class_name = data['tool_class'].rsplit('.', 1)
        module = importlib.import_module(module_path)
        tool_class = getattr(module, class_name)
        
        return cls(
            name=data['name'],
            tool_class=tool_class,
            module_path=data['module_path'],
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            dependencies=data.get('dependencies', []),
            is_async=data.get('is_async', False)
        )


class ToolRegistry:
    """Registry for discovering and managing tools."""
    
    def __init__(self, registry_file: Optional[str] = None):
        """Initialize the registry."""
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = {}
        self.registry_file = registry_file or os.path.join(
            Path.home(), '.agent-toolbox', 'tools.json'
        )
        
        # Ensure registry directory exists
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        
        # Load existing registry
        self._load_registry()
        
    def register_tool(self, 
                     tool_class: Type[BaseTool],
                     name: Optional[str] = None,
                     category: str = "general",
                     tags: Optional[List[str]] = None,
                     dependencies: Optional[List[str]] = None) -> None:
        """Register a tool in the registry."""
        
        if not issubclass(tool_class, BaseTool):
            raise ValueError(f"Tool class must inherit from BaseTool: {tool_class}")
            
        # Create tool instance to get metadata
        instance = tool_class()
        
        tool_name = name or instance.name
        
        tool = Tool(
            name=tool_name,
            tool_class=tool_class,
            module_path=tool_class.__module__,
            description=instance.description,
            version=instance.version,
            category=category,
            tags=tags or [],
            dependencies=dependencies or [],
            is_async=issubclass(tool_class, AsyncBaseTool)
        )
        
        self.tools[tool_name] = tool
        
        # Update categories
        if category not in self.categories:
            self.categories[category] = []
        if tool_name not in self.categories[category]:
            self.categories[category].append(tool_name)
            
        logger.info(f"Registered tool: {tool_name} (category: {category})")
        
        # Save registry
        self._save_registry()
        
    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool from the registry."""
        if name not in self.tools:
            return False
            
        tool = self.tools[name]
        del self.tools[name]
        
        # Remove from categories
        if tool.category in self.categories:
            if name in self.categories[tool.category]:
                self.categories[tool.category].remove(name)
                
        logger.info(f"Unregistered tool: {name}")
        self._save_registry()
        return True
        
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
        
    def create_tool_instance(self, name: str, **kwargs) -> Optional[BaseTool]:
        """Create an instance of a registered tool."""
        tool = self.get_tool(name)
        if not tool:
            return None
            
        try:
            return tool.tool_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create instance of tool {name}: {str(e)}")
            return None
            
    def list_tools(self, 
                   category: Optional[str] = None,
                   tags: Optional[List[str]] = None) -> List[Tool]:
        """List registered tools with optional filtering."""
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
            
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]
            
        return tools
        
    def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name or description."""
        query = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query in tool.name.lower() or 
                query in tool.description.lower() or
                any(query in tag.lower() for tag in tool.tags)):
                results.append(tool)
                
        return results
        
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all categories and their tools."""
        return self.categories.copy()
        
    def discover_tools(self, module_path: str, recursive: bool = True) -> int:
        """Discover and register tools from a module path."""
        discovered = 0
        
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find all classes that inherit from BaseTool
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseTool) and 
                    obj is not BaseTool and 
                    obj is not AsyncBaseTool and
                    obj.__module__ == module_path):
                    
                    # Auto-register the tool
                    try:
                        self.register_tool(obj)
                        discovered += 1
                    except Exception as e:
                        logger.warning(f"Failed to register {name}: {str(e)}")
                        
            # Recursively discover in submodules if requested
            if recursive and hasattr(module, '__path__'):
                import pkgutil
                for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
                    submodule_path = f"{module_path}.{modname}"
                    discovered += self.discover_tools(submodule_path, recursive=True)
                    
        except ImportError as e:
            logger.warning(f"Could not import module {module_path}: {str(e)}")
            
        return discovered
        
    def export_registry(self, filename: str) -> None:
        """Export registry to a JSON file."""
        data = {
            'tools': {name: tool.to_dict() for name, tool in self.tools.items()},
            'categories': self.categories
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Exported registry to {filename}")
        
    def import_registry(self, filename: str, merge: bool = True) -> None:
        """Import registry from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
            
        if not merge:
            self.tools.clear()
            self.categories.clear()
            
        # Import tools
        for name, tool_data in data.get('tools', {}).items():
            try:
                tool = Tool.from_dict(tool_data)
                self.tools[name] = tool
            except Exception as e:
                logger.warning(f"Failed to import tool {name}: {str(e)}")
                
        # Import categories
        for category, tool_names in data.get('categories', {}).items():
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].extend(tool_names)
            
        # Save the merged registry
        self._save_registry()
        logger.info(f"Imported registry from {filename}")
        
    def _save_registry(self) -> None:
        """Save registry to file."""
        try:
            self.export_registry(self.registry_file)
        except Exception as e:
            logger.warning(f"Failed to save registry: {str(e)}")
            
    def _load_registry(self) -> None:
        """Load registry from file."""
        if os.path.exists(self.registry_file):
            try:
                self.import_registry(self.registry_file, merge=False)
                logger.info(f"Loaded registry from {self.registry_file}")
            except Exception as e:
                logger.warning(f"Failed to load registry: {str(e)}")


# Global registry instance
_global_registry = None


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool_class: Type[BaseTool], 
                 name: Optional[str] = None,
                 category: str = "general",
                 tags: Optional[List[str]] = None,
                 dependencies: Optional[List[str]] = None) -> None:
    """Register a tool in the global registry."""
    registry = get_global_registry()
    registry.register_tool(tool_class, name, category, tags, dependencies)


def tool_decorator(name: Optional[str] = None,
                  category: str = "general", 
                  tags: Optional[List[str]] = None,
                  dependencies: Optional[List[str]] = None) -> Callable:
    """Decorator to automatically register tools."""
    def decorator(tool_class: Type[BaseTool]) -> Type[BaseTool]:
        register_tool(tool_class, name, category, tags, dependencies)
        return tool_class
    return decorator
"""File operations utilities for agent tasks."""

import os
import shutil
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


class FileManager:
    """Comprehensive file management utilities for agents."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize FileManager with optional base path."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        
    def create_directory(self, path: Union[str, Path], parents: bool = True) -> Path:
        """Create a directory with optional parent creation."""
        full_path = self._resolve_path(path)
        full_path.mkdir(parents=parents, exist_ok=True)
        return full_path
        
    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve path relative to base path."""
        path = Path(path)
        if path.is_absolute():
            return path
        return self.base_path / path
    
    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text content from a file."""
        full_path = self._resolve_path(path)
        return full_path.read_text(encoding=encoding)
        
    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)
        
    def append_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Append text content to a file."""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'a', encoding=encoding) as f:
            f.write(content)
            
    def read_json(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read JSON content from a file."""
        full_path = self._resolve_path(path)
        with open(full_path, 'r') as f:
            return json.load(f)
            
    def write_json(self, path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> None:
        """Write data to a JSON file."""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            json.dump(data, f, indent=indent)
            
    def read_yaml(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read YAML content from a file."""
        full_path = self._resolve_path(path)
        with open(full_path, 'r') as f:
            return yaml.safe_load(f)
            
    def write_yaml(self, path: Union[str, Path], data: Dict[str, Any]) -> None:
        """Write data to a YAML file."""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
            
    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a file or directory exists."""
        full_path = self._resolve_path(path)
        return full_path.exists()
        
    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        full_path = self._resolve_path(path)
        return full_path.is_file()
        
    def is_directory(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        full_path = self._resolve_path(path)
        return full_path.is_dir()
        
    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file to a new location."""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        
    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move a file to a new location."""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        
    def delete_file(self, path: Union[str, Path]) -> None:
        """Delete a file."""
        full_path = self._resolve_path(path)
        if full_path.is_file():
            full_path.unlink()
            
    def delete_directory(self, path: Union[str, Path], recursive: bool = False) -> None:
        """Delete a directory."""
        full_path = self._resolve_path(path)
        if full_path.is_dir():
            if recursive:
                shutil.rmtree(full_path)
            else:
                full_path.rmdir()
"""File operations utilities for agent tasks."""

import os
import shutil
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


logger = logging.getLogger(__name__)


class FileOperationError(Exception):
    """Base exception for file operation errors."""
    pass


class FileNotFoundError(FileOperationError):
    """Raised when a file is not found."""
    pass


class DirectoryNotFoundError(FileOperationError):
    """Raised when a directory is not found."""
    pass


class PermissionError(FileOperationError):
    """Raised when file operation is not permitted."""
    pass


class FileManager:
    """Comprehensive file management utilities for agents."""
    
    def __init__(self, base_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize FileManager with optional base path.
        
        Args:
            base_path: Base directory path for relative operations
            
        Raises:
            DirectoryNotFoundError: If base_path doesn't exist
            PermissionError: If base_path is not accessible
        """
        if base_path is None:
            self.base_path = Path.cwd()
        else:
            self.base_path = Path(base_path).resolve()
            
        if not self.base_path.exists():
            raise DirectoryNotFoundError(f"Base path does not exist: {self.base_path}")
        
        if not self.base_path.is_dir():
            raise DirectoryNotFoundError(f"Base path is not a directory: {self.base_path}")
            
        # Test write permissions
        try:
            test_file = self.base_path / '.test_write_permissions'
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            logger.warning(f"Limited write permissions in base path: {e}")
        
        logger.debug(f"FileManager initialized with base path: {self.base_path}")
        
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
        """Read text content from a file.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not readable
            UnicodeDecodeError: If file cannot be decoded with given encoding
        """
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
            
        if not full_path.is_file():
            raise FileOperationError(f"Path is not a file: {full_path}")
        
        try:
            logger.debug(f"Reading text file: {full_path}")
            return full_path.read_text(encoding=encoding)
        except OSError as e:
            raise PermissionError(f"Cannot read file {full_path}: {e}") from e
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding, e.object, e.start, e.end,
                f"Cannot decode file {full_path} with encoding {encoding}: {e.reason}"
            ) from e
        
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
                
    def list_files(self, path: Union[str, Path] = ".", pattern: str = "*") -> List[Path]:
        """List files in a directory with optional pattern matching."""
        full_path = self._resolve_path(path)
        return list(full_path.glob(pattern))
        
    def find_files(self, pattern: str, path: Union[str, Path] = ".", recursive: bool = True) -> List[Path]:
        """Find files matching a pattern."""
        full_path = self._resolve_path(path)
        if recursive:
            return list(full_path.rglob(pattern))
        else:
            return list(full_path.glob(pattern))
            
    def get_file_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        full_path = self._resolve_path(path)
        return full_path.stat().st_size
        
    def get_file_stats(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Get comprehensive file statistics."""
        full_path = self._resolve_path(path)
        stat = full_path.stat()
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'accessed': stat.st_atime,
            'created': stat.st_ctime,
            'mode': stat.st_mode,
            'is_file': full_path.is_file(),
            'is_dir': full_path.is_dir(),
            'name': full_path.name,
            'suffix': full_path.suffix,
            'parent': str(full_path.parent)
        }
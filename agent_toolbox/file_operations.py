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
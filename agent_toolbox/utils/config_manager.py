"""Configuration management utilities."""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv


class ConfigManager:
    """Manage configuration from files and environment variables."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None, 
                 load_env_file: bool = True):
        """Initialize configuration manager."""
        self.config = {}
        self.config_path = Path(config_path) if config_path else None
        
        if load_env_file:
            load_dotenv()
            
        if self.config_path and self.config_path.exists():
            self.load_config()
            
    def load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path or not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        file_extension = self.config_path.suffix.lower()
        
        if file_extension == '.json':
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        elif file_extension in ['.yml', '.yaml']:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file type: {file_extension}")
            
    def save_config(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save configuration to file."""
        save_path = Path(file_path) if file_path else self.config_path
        
        if not save_path:
            raise ValueError("No file path specified for saving config")
            
        file_extension = save_path.suffix.lower()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_extension == '.json':
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        elif file_extension in ['.yml', '.yaml']:
            with open(save_path, 'w') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported config file type: {file_extension}")
            
    def get(self, key: str, default: Any = None, use_env: bool = True) -> Any:
        """Get configuration value with optional environment variable fallback."""
        # Try to get from loaded config
        value = self._get_nested_value(self.config, key, default)
        
        # If not found and use_env is True, try environment variable
        if value is default and use_env:
            env_key = key.upper().replace('.', '_')
            value = os.getenv(env_key, default)
            
        return value
        
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._set_nested_value(self.config, key, value)
        
    def _get_nested_value(self, data: Dict[str, Any], key: str, default: Any) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = key.split('.')
        current = data
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
            
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        current[keys[-1]] = value
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self._get_nested_value(self.config, section, {})
        
    def merge_config(self, other_config: Dict[str, Any]) -> None:
        """Merge another configuration dictionary."""
        self._deep_merge(self.config, other_config)
        
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge two dictionaries."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
                
    def has_key(self, key: str) -> bool:
        """Check if configuration key exists."""
        return self._get_nested_value(self.config, key, None) is not None
        
    def delete_key(self, key: str) -> None:
        """Delete configuration key."""
        keys = key.split('.')
        current = self.config
        
        try:
            for k in keys[:-1]:
                current = current[k]
            del current[keys[-1]]
        except (KeyError, TypeError):
            pass  # Key doesn't exist
            
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config.copy()
        
    def clear(self) -> None:
        """Clear all configuration."""
        self.config.clear()
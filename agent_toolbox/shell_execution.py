"""Shell execution utilities with safety features for agent tasks."""

import subprocess
import shlex
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import threading


class ShellExecutor:
    """Safe shell command execution utilities for agents."""
    
    def __init__(self, 
                 working_directory: Optional[Union[str, Path]] = None,
                 timeout: int = 300,
                 allowed_commands: Optional[List[str]] = None,
                 blocked_commands: Optional[List[str]] = None):
        """Initialize ShellExecutor with safety settings."""
        self.working_directory = Path(working_directory) if working_directory else Path.cwd()
        self.timeout = timeout
        self.allowed_commands = allowed_commands or []
        self.blocked_commands = blocked_commands or ['rm -rf', 'sudo rm', 'format', 'fdisk']
        
    def _validate_command(self, command: str) -> bool:
        """Validate command against allow/block lists."""
        # Check blocked commands
        for blocked in self.blocked_commands:
            if blocked.lower() in command.lower():
                return False
                
        # Check allowed commands (if specified)
        if self.allowed_commands:
            for allowed in self.allowed_commands:
                if command.lower().startswith(allowed.lower()):
                    return True
            return False
            
        return True
        
    def execute(self, 
                command: str, 
                capture_output: bool = True,
                check_return_code: bool = True,
                env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Union[str, int]]:
        """Execute a shell command safely."""
        
        if not self._validate_command(command):
            raise ValueError(f"Command blocked for security: {command}")
            
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            
        try:
            # Execute command
            result = subprocess.run(
                shlex.split(command),
                cwd=str(self.working_directory),
                capture_output=capture_output,
                text=True,
                timeout=self.timeout,
                env=env
            )
            
            if check_return_code:
                result.check_returncode()
                
            return {
                'stdout': result.stdout if capture_output else '',
                'stderr': result.stderr if capture_output else '',
                'return_code': result.returncode,
                'command': command,
                'success': result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            raise Exception(f"Command timed out after {self.timeout} seconds: {command}")
        except subprocess.CalledProcessError as e:
            if check_return_code:
                raise Exception(f"Command failed with return code {e.returncode}: {command}")
            else:
                return {
                    'stdout': e.stdout if capture_output else '',
                    'stderr': e.stderr if capture_output else '',
                    'return_code': e.returncode,
                    'command': command,
                    'success': False
                }
        except Exception as e:
            raise Exception(f"Failed to execute command: {str(e)}")
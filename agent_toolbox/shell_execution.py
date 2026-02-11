"""Shell execution utilities for agent tasks."""

import subprocess
import shlex
import os
import signal
import threading
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path


class ShellExecutor:
    """Safe shell command execution for agents."""
    
    def __init__(self, 
                 working_directory: Optional[Union[str, Path]] = None,
                 environment: Optional[Dict[str, str]] = None,
                 timeout: Optional[float] = None):
        """Initialize ShellExecutor."""
        self.working_directory = Path(working_directory) if working_directory else Path.cwd()
        self.environment = environment or {}
        self.timeout = timeout
        self._active_processes: Dict[str, subprocess.Popen] = {}
        
    def execute(self, 
                command: Union[str, List[str]], 
                capture_output: bool = True,
                timeout: Optional[float] = None,
                shell: bool = False,
                check: bool = False) -> subprocess.CompletedProcess:
        """Execute a shell command safely."""
        if isinstance(command, str) and not shell:
            command = shlex.split(command)
        
        env = os.environ.copy()
        env.update(self.environment)
        
        try:
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                env=env,
                capture_output=capture_output,
                text=True,
                timeout=timeout or self.timeout,
                shell=shell,
                check=check
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"Command timed out: {command}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed with exit code {e.returncode}: {command}") from e
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Command not found: {command}") from e
    
    def execute_async(self,
                     command: Union[str, List[str]],
                     process_id: Optional[str] = None,
                     shell: bool = False) -> str:
        """Execute a command asynchronously and return process ID."""
        if isinstance(command, str) and not shell:
            command = shlex.split(command)
        
        env = os.environ.copy()
        env.update(self.environment)
        
        process_id = process_id or f"proc_{int(time.time() * 1000)}"
        
        try:
            proc = subprocess.Popen(
                command,
                cwd=self.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=shell
            )
            
            self._active_processes[process_id] = proc
            return process_id
            
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Command not found: {command}") from e
    
    def get_process_status(self, process_id: str) -> Dict[str, Any]:
        """Get status of an async process."""
        if process_id not in self._active_processes:
            raise ValueError(f"Process ID not found: {process_id}")
        
        proc = self._active_processes[process_id]
        poll_result = proc.poll()
        
        return {
            'process_id': process_id,
            'pid': proc.pid,
            'running': poll_result is None,
            'return_code': poll_result,
            'command': ' '.join(proc.args) if isinstance(proc.args, list) else proc.args
        }
    
    def get_process_output(self, process_id: str, timeout: Optional[float] = None) -> Tuple[str, str]:
        """Get output from an async process."""
        if process_id not in self._active_processes:
            raise ValueError(f"Process ID not found: {process_id}")
        
        proc = self._active_processes[process_id]
        
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            del self._active_processes[process_id]
            return stdout, stderr
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Process output retrieval timed out: {process_id}")
    
    def terminate_process(self, process_id: str, force: bool = False) -> bool:
        """Terminate an async process."""
        if process_id not in self._active_processes:
            return False
        
        proc = self._active_processes[process_id]
        
        if force:
            proc.kill()
        else:
            proc.terminate()
        
        try:
            proc.wait(timeout=5)
            del self._active_processes[process_id]
            return True
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            del self._active_processes[process_id]
            return True
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List all active processes."""
        processes = []
        for process_id in list(self._active_processes.keys()):
            try:
                status = self.get_process_status(process_id)
                processes.append(status)
            except ValueError:
                continue
        return processes
    
    def cleanup_finished_processes(self) -> int:
        """Clean up finished processes and return count of cleaned up processes."""
        finished_processes = []
        
        for process_id, proc in self._active_processes.items():
            if proc.poll() is not None:
                finished_processes.append(process_id)
        
        for process_id in finished_processes:
            del self._active_processes[process_id]
        
        return len(finished_processes)
    
    def set_working_directory(self, path: Union[str, Path]) -> None:
        """Set the working directory for future commands."""
        self.working_directory = Path(path)
    
    def set_environment_variable(self, key: str, value: str) -> None:
        """Set an environment variable for future commands."""
        self.environment[key] = value
    
    def unset_environment_variable(self, key: str) -> None:
        """Remove an environment variable."""
        self.environment.pop(key, None)
    
    def get_environment(self) -> Dict[str, str]:
        """Get current environment variables."""
        return self.environment.copy()
    
    def __del__(self):
        """Cleanup any remaining processes."""
        for process_id in list(self._active_processes.keys()):
            self.terminate_process(process_id, force=True)
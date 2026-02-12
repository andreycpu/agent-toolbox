"""Sandbox environment for safe tool execution."""

import os
import tempfile
import shutil
import subprocess
import time
import signal
import psutil
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for sandbox environment."""
    
    # Resource limits
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    max_execution_time: float = 30.0
    max_processes: int = 10
    max_files: int = 1000
    max_file_size_mb: int = 100
    
    # Network restrictions
    allow_network: bool = False
    allowed_hosts: List[str] = None
    blocked_ports: List[int] = None
    
    # File system restrictions  
    read_only: bool = True
    allowed_paths: List[str] = None
    blocked_paths: List[str] = None
    
    # Environment restrictions
    allowed_env_vars: List[str] = None
    blocked_env_vars: List[str] = None
    
    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = []
        if self.blocked_ports is None:
            self.blocked_ports = [22, 23, 25, 53, 80, 443]
        if self.allowed_paths is None:
            self.allowed_paths = []
        if self.blocked_paths is None:
            self.blocked_paths = ['/etc', '/root', '/home']
        if self.allowed_env_vars is None:
            self.allowed_env_vars = ['PATH', 'HOME', 'USER', 'LANG']
        if self.blocked_env_vars is None:
            self.blocked_env_vars = ['PASSWORD', 'SECRET', 'TOKEN', 'KEY']


class SandboxViolation(Exception):
    """Raised when sandbox security is violated."""
    pass


class SandboxTimeoutError(SandboxViolation):
    """Raised when execution exceeds time limit."""
    pass


class SandboxResourceError(SandboxViolation):
    """Raised when resource limits are exceeded."""
    pass


class ProcessMonitor:
    """Monitor process resource usage."""
    
    def __init__(self, pid: int, config: SandboxConfig):
        self.pid = pid
        self.config = config
        self.start_time = time.time()
        self.violations: List[str] = []
        
    def check_limits(self) -> bool:
        """Check if process is within limits."""
        try:
            process = psutil.Process(self.pid)
            
            # Check execution time
            elapsed = time.time() - self.start_time
            if elapsed > self.config.max_execution_time:
                self.violations.append(f"Execution time exceeded: {elapsed:.2f}s > {self.config.max_execution_time}s")
                return False
                
            # Check memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            if memory_mb > self.config.max_memory_mb:
                self.violations.append(f"Memory exceeded: {memory_mb:.2f}MB > {self.config.max_memory_mb}MB")
                return False
                
            # Check CPU usage
            cpu_percent = process.cpu_percent()
            if cpu_percent > self.config.max_cpu_percent:
                self.violations.append(f"CPU exceeded: {cpu_percent:.1f}% > {self.config.max_cpu_percent}%")
                return False
                
            # Check process count
            children = process.children(recursive=True)
            if len(children) > self.config.max_processes:
                self.violations.append(f"Process count exceeded: {len(children)} > {self.config.max_processes}")
                return False
                
            return True
            
        except psutil.NoSuchProcess:
            return True  # Process finished
        except Exception as e:
            logger.warning(f"Error checking process limits: {str(e)}")
            return True  # Assume OK if can't check


class SandboxEnvironment:
    """Secure sandbox environment for tool execution."""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """Initialize sandbox environment."""
        self.config = config or SandboxConfig()
        self.sandbox_dir: Optional[Path] = None
        self.original_cwd: Optional[str] = None
        self.active_processes: Dict[int, ProcessMonitor] = {}
        self._cleanup_needed = False
        
    def __enter__(self) -> 'SandboxEnvironment':
        """Enter sandbox context."""
        self.setup()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context."""
        self.cleanup()
        
    def setup(self) -> None:
        """Set up the sandbox environment."""
        try:
            # Create temporary sandbox directory
            self.sandbox_dir = Path(tempfile.mkdtemp(prefix='agent_sandbox_'))
            logger.info(f"Created sandbox directory: {self.sandbox_dir}")
            
            # Store original working directory
            self.original_cwd = os.getcwd()
            
            # Change to sandbox directory
            os.chdir(self.sandbox_dir)
            
            # Set up restricted environment
            self._setup_environment()
            
            self._cleanup_needed = True
            
        except Exception as e:
            logger.error(f"Failed to setup sandbox: {str(e)}")
            self.cleanup()
            raise SandboxViolation(f"Sandbox setup failed: {str(e)}")
            
    def _setup_environment(self) -> None:
        """Set up restricted environment variables."""
        # Clear environment and set only allowed variables
        if self.config.allowed_env_vars:
            original_env = os.environ.copy()
            os.environ.clear()
            
            for var in self.config.allowed_env_vars:
                if var in original_env:
                    os.environ[var] = original_env[var]
                    
        # Remove blocked environment variables
        for var in self.config.blocked_env_vars:
            os.environ.pop(var, None)
            
        # Set sandbox-specific variables
        os.environ['SANDBOX_MODE'] = '1'
        os.environ['SANDBOX_DIR'] = str(self.sandbox_dir)
        
    def execute_command(self, 
                       command: Union[str, List[str]],
                       timeout: Optional[float] = None,
                       capture_output: bool = True,
                       allow_network: Optional[bool] = None) -> subprocess.CompletedProcess:
        """Execute a command within the sandbox."""
        
        if isinstance(command, str):
            command = ['/bin/bash', '-c', command]
            
        timeout = timeout or self.config.max_execution_time
        allow_network = allow_network if allow_network is not None else self.config.allow_network
        
        # Validate command
        self._validate_command(command)
        
        logger.debug(f"Executing command in sandbox: {' '.join(command)}")
        
        try:
            # Start process with restrictions
            env = os.environ.copy()
            if not allow_network:
                env['NETWORK_DISABLED'] = '1'
                
            process = subprocess.Popen(
                command,
                cwd=self.sandbox_dir,
                env=env,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                preexec_fn=self._set_process_limits
            )
            
            # Monitor process
            monitor = ProcessMonitor(process.pid, self.config)
            self.active_processes[process.pid] = monitor
            
            # Wait for completion with monitoring
            start_time = time.time()
            while process.poll() is None:
                # Check limits
                if not monitor.check_limits():
                    process.terminate()
                    time.sleep(0.1)
                    if process.poll() is None:
                        process.kill()
                    raise SandboxResourceError(f"Resource limits violated: {', '.join(monitor.violations)}")
                    
                # Check timeout
                if time.time() - start_time > timeout:
                    process.terminate() 
                    time.sleep(0.1)
                    if process.poll() is None:
                        process.kill()
                    raise SandboxTimeoutError(f"Command timed out after {timeout}s")
                    
                time.sleep(0.1)
                
            # Get result
            stdout, stderr = process.communicate()
            
            # Clean up monitor
            del self.active_processes[process.pid]
            
            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else '',
                stderr=stderr.decode('utf-8', errors='replace') if stderr else ''
            )
            
        except Exception as e:
            # Clean up on error
            if process.pid in self.active_processes:
                del self.active_processes[process.pid]
            raise
            
    def _validate_command(self, command: List[str]) -> None:
        """Validate command for security."""
        dangerous_commands = [
            'rm', 'rmdir', 'del', 'format', 'fdisk',
            'nc', 'netcat', 'wget', 'curl', 'ssh', 'ftp',
            'sudo', 'su', 'chmod', 'chown', 'mount', 'umount'
        ]
        
        cmd = command[0] if command else ''
        base_cmd = os.path.basename(cmd)
        
        if base_cmd in dangerous_commands and not self._is_command_allowed(command):
            raise SandboxViolation(f"Dangerous command not allowed: {base_cmd}")
            
    def _is_command_allowed(self, command: List[str]) -> bool:
        """Check if a potentially dangerous command is allowed."""
        # This would contain whitelist logic for specific use cases
        # For now, block all dangerous commands
        return False
        
    def _set_process_limits(self) -> None:
        """Set resource limits for spawned processes."""
        try:
            import resource
            
            # Set memory limit
            max_memory = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
            
            # Set CPU time limit
            cpu_time = int(self.config.max_execution_time)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_time, cpu_time))
            
            # Set file descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (self.config.max_files, self.config.max_files))
            
        except ImportError:
            logger.warning("Resource module not available, limits not set")
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {str(e)}")
            
    def create_file(self, 
                   path: Union[str, Path],
                   content: str,
                   mode: int = 0o644) -> Path:
        """Create a file in the sandbox."""
        if not self.sandbox_dir:
            raise SandboxViolation("Sandbox not initialized")
            
        file_path = self.sandbox_dir / path
        
        # Validate path
        if not self._is_path_allowed(file_path):
            raise SandboxViolation(f"Path not allowed: {file_path}")
            
        # Check file size
        content_size = len(content.encode('utf-8'))
        max_size = self.config.max_file_size_mb * 1024 * 1024
        if content_size > max_size:
            raise SandboxResourceError(f"File size {content_size} exceeds limit {max_size}")
            
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_text(content, encoding='utf-8')
        file_path.chmod(mode)
        
        logger.debug(f"Created file in sandbox: {file_path}")
        return file_path
        
    def read_file(self, path: Union[str, Path]) -> str:
        """Read a file from the sandbox."""
        if not self.sandbox_dir:
            raise SandboxViolation("Sandbox not initialized")
            
        file_path = self.sandbox_dir / path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if not self._is_path_allowed(file_path):
            raise SandboxViolation(f"Path not allowed: {file_path}")
            
        return file_path.read_text(encoding='utf-8')
        
    def list_files(self, path: Union[str, Path] = '.') -> List[Path]:
        """List files in sandbox directory."""
        if not self.sandbox_dir:
            raise SandboxViolation("Sandbox not initialized")
            
        dir_path = self.sandbox_dir / path
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
            
        if not self._is_path_allowed(dir_path):
            raise SandboxViolation(f"Path not allowed: {dir_path}")
            
        return list(dir_path.iterdir())
        
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path access is allowed."""
        # Must be within sandbox
        try:
            path.resolve().relative_to(self.sandbox_dir.resolve())
        except ValueError:
            return False
            
        # Check against blocked paths
        for blocked in self.config.blocked_paths:
            if str(path).startswith(blocked):
                return False
                
        # If allowed paths specified, must match one
        if self.config.allowed_paths:
            for allowed in self.config.allowed_paths:
                if str(path).startswith(allowed):
                    return True
            return False
            
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox usage statistics."""
        stats = {
            'sandbox_dir': str(self.sandbox_dir) if self.sandbox_dir else None,
            'active_processes': len(self.active_processes),
            'config': {
                'max_memory_mb': self.config.max_memory_mb,
                'max_execution_time': self.config.max_execution_time,
                'allow_network': self.config.allow_network,
                'read_only': self.config.read_only
            }
        }
        
        if self.sandbox_dir and self.sandbox_dir.exists():
            try:
                # Count files and calculate size
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(self.sandbox_dir):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            total_size += file_path.stat().st_size
                            file_count += 1
                        except OSError:
                            pass
                            
                stats['files'] = {
                    'count': file_count,
                    'total_size_bytes': total_size,
                    'total_size_mb': total_size / 1024 / 1024
                }
            except Exception as e:
                logger.warning(f"Failed to get file stats: {str(e)}")
                
        return stats
        
    def cleanup(self) -> None:
        """Clean up sandbox environment."""
        if not self._cleanup_needed:
            return
            
        try:
            # Terminate active processes
            for pid in list(self.active_processes.keys()):
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    time.sleep(0.1)
                    if process.is_running():
                        process.kill()
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logger.warning(f"Failed to terminate process {pid}: {str(e)}")
                    
            self.active_processes.clear()
            
            # Restore original working directory
            if self.original_cwd:
                try:
                    os.chdir(self.original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore working directory: {str(e)}")
                    
            # Remove sandbox directory
            if self.sandbox_dir and self.sandbox_dir.exists():
                try:
                    shutil.rmtree(self.sandbox_dir)
                    logger.info(f"Cleaned up sandbox directory: {self.sandbox_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove sandbox directory: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error during sandbox cleanup: {str(e)}")
        finally:
            self._cleanup_needed = False
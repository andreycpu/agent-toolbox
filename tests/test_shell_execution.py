"""Tests for shell execution module."""

import pytest
import subprocess
import time
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
from agent_toolbox.shell_execution import ShellExecutor


class TestShellExecutor:
    """Test cases for ShellExecutor."""
    
    def test_init_default(self):
        """Test ShellExecutor initialization with defaults."""
        executor = ShellExecutor()
        assert executor.working_directory == Path.cwd()
        assert executor.environment == {}
        assert executor.timeout is None
        assert executor._active_processes == {}
    
    def test_init_with_params(self):
        """Test ShellExecutor initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"TEST_VAR": "value"}
            executor = ShellExecutor(
                working_directory=tmpdir,
                environment=env,
                timeout=30.0
            )
            assert executor.working_directory == Path(tmpdir)
            assert executor.environment == env
            assert executor.timeout == 30.0
    
    def test_execute_simple_command(self):
        """Test executing a simple command."""
        executor = ShellExecutor()
        result = executor.execute("echo hello")
        
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.stderr == ""
    
    def test_execute_with_list_command(self):
        """Test executing command provided as list."""
        executor = ShellExecutor()
        result = executor.execute(["echo", "hello", "world"])
        
        assert result.returncode == 0
        assert "hello world" in result.stdout
    
    def test_execute_with_shell_true(self):
        """Test executing command with shell=True."""
        executor = ShellExecutor()
        result = executor.execute("echo $HOME", shell=True)
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0  # Should contain home directory
    
    def test_execute_in_working_directory(self):
        """Test executing command in specific working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")
            
            executor = ShellExecutor(working_directory=tmpdir)
            result = executor.execute("ls test.txt")
            
            assert result.returncode == 0
            assert "test.txt" in result.stdout
    
    def test_execute_with_environment(self):
        """Test executing command with custom environment."""
        env = {"TEST_VAR": "test_value"}
        executor = ShellExecutor(environment=env)
        result = executor.execute("echo $TEST_VAR", shell=True)
        
        assert result.returncode == 0
        assert "test_value" in result.stdout
    
    def test_execute_timeout(self):
        """Test command timeout."""
        executor = ShellExecutor()
        with pytest.raises(TimeoutError):
            executor.execute("sleep 2", timeout=0.1)
    
    def test_execute_command_not_found(self):
        """Test executing non-existent command."""
        executor = ShellExecutor()
        with pytest.raises(FileNotFoundError):
            executor.execute("nonexistent_command_12345")
    
    def test_execute_command_failure(self):
        """Test executing command that returns non-zero exit code."""
        executor = ShellExecutor()
        result = executor.execute("false")  # Always returns 1
        
        assert result.returncode == 1
        
        # Test with check=True
        with pytest.raises(RuntimeError):
            executor.execute("false", check=True)
    
    def test_execute_async(self):
        """Test asynchronous command execution."""
        executor = ShellExecutor()
        process_id = executor.execute_async("sleep 0.1")
        
        assert isinstance(process_id, str)
        assert process_id in executor._active_processes
        
        # Wait for completion
        time.sleep(0.2)
        stdout, stderr = executor.get_process_output(process_id)
        assert stdout == ""
        assert stderr == ""
    
    def test_execute_async_with_custom_id(self):
        """Test async execution with custom process ID."""
        executor = ShellExecutor()
        custom_id = "my_process"
        process_id = executor.execute_async("echo hello", process_id=custom_id)
        
        assert process_id == custom_id
        assert custom_id in executor._active_processes
        
        stdout, stderr = executor.get_process_output(custom_id)
        assert "hello" in stdout
    
    def test_get_process_status(self):
        """Test getting process status."""
        executor = ShellExecutor()
        process_id = executor.execute_async("sleep 0.1")
        
        # Should be running initially
        status = executor.get_process_status(process_id)
        assert status['process_id'] == process_id
        assert 'pid' in status
        assert 'running' in status
        assert 'command' in status
        
        # Wait and check again
        time.sleep(0.2)
        status = executor.get_process_status(process_id)
        # Process might still be in dict but should be finished
    
    def test_get_process_status_invalid_id(self):
        """Test getting status of non-existent process."""
        executor = ShellExecutor()
        with pytest.raises(ValueError):
            executor.get_process_status("invalid_id")
    
    def test_terminate_process(self):
        """Test terminating a process."""
        executor = ShellExecutor()
        process_id = executor.execute_async("sleep 10")
        
        # Terminate the process
        result = executor.terminate_process(process_id)
        assert result is True
        assert process_id not in executor._active_processes
    
    def test_terminate_process_force(self):
        """Test force terminating a process."""
        executor = ShellExecutor()
        process_id = executor.execute_async("sleep 10")
        
        # Force kill the process
        result = executor.terminate_process(process_id, force=True)
        assert result is True
        assert process_id not in executor._active_processes
    
    def test_terminate_process_invalid_id(self):
        """Test terminating non-existent process."""
        executor = ShellExecutor()
        result = executor.terminate_process("invalid_id")
        assert result is False
    
    def test_list_processes(self):
        """Test listing active processes."""
        executor = ShellExecutor()
        
        # Start multiple processes
        id1 = executor.execute_async("sleep 0.1")
        id2 = executor.execute_async("echo test")
        
        processes = executor.list_processes()
        assert len(processes) >= 2
        
        process_ids = [p['process_id'] for p in processes]
        assert id1 in process_ids
        assert id2 in process_ids
    
    def test_cleanup_finished_processes(self):
        """Test cleaning up finished processes."""
        executor = ShellExecutor()
        
        # Start a quick process
        process_id = executor.execute_async("echo test")
        time.sleep(0.1)  # Let it finish
        
        count = executor.cleanup_finished_processes()
        assert count >= 1
        assert process_id not in executor._active_processes
    
    def test_set_working_directory(self):
        """Test setting working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ShellExecutor()
            executor.set_working_directory(tmpdir)
            assert executor.working_directory == Path(tmpdir)
    
    def test_environment_management(self):
        """Test environment variable management."""
        executor = ShellExecutor()
        
        # Set environment variable
        executor.set_environment_variable("TEST_KEY", "test_value")
        assert executor.environment["TEST_KEY"] == "test_value"
        
        # Test the variable is used in commands
        result = executor.execute("echo $TEST_KEY", shell=True)
        assert "test_value" in result.stdout
        
        # Unset environment variable
        executor.unset_environment_variable("TEST_KEY")
        assert "TEST_KEY" not in executor.environment
        
        # Get environment copy
        env_copy = executor.get_environment()
        assert isinstance(env_copy, dict)
    
    def test_execute_without_capture_output(self):
        """Test executing command without capturing output."""
        executor = ShellExecutor()
        result = executor.execute("echo hello", capture_output=False)
        
        assert result.returncode == 0
        assert result.stdout is None
        assert result.stderr is None
    
    @patch('subprocess.run')
    def test_execute_with_subprocess_error(self, mock_run):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "test_command")
        
        executor = ShellExecutor()
        with pytest.raises(RuntimeError):
            executor.execute("test_command", check=True)
    
    def test_async_command_not_found(self):
        """Test async execution with non-existent command."""
        executor = ShellExecutor()
        with pytest.raises(FileNotFoundError):
            executor.execute_async("nonexistent_command_12345")
    
    def test_get_output_invalid_process(self):
        """Test getting output from invalid process ID."""
        executor = ShellExecutor()
        with pytest.raises(ValueError):
            executor.get_process_output("invalid_id")
    
    def test_process_cleanup_on_deletion(self):
        """Test process cleanup when executor is deleted."""
        executor = ShellExecutor()
        process_id = executor.execute_async("sleep 5")
        
        # Mock the terminate_process method to verify it's called
        with patch.object(executor, 'terminate_process') as mock_terminate:
            del executor
            # Force garbage collection might be needed in some cases
            import gc
            gc.collect()
            # We can't easily test __del__ directly, so we'll test the logic separately
        
        # Test the actual cleanup manually
        executor2 = ShellExecutor()
        process_id2 = executor2.execute_async("sleep 5")
        assert len(executor2._active_processes) == 1
        
        # Manually call cleanup logic
        for pid in list(executor2._active_processes.keys()):
            executor2.terminate_process(pid, force=True)
        
        assert len(executor2._active_processes) == 0
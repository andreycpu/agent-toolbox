"""Tests for file operations module."""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from agent_toolbox.file_operations import FileManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def file_manager(temp_dir):
    """Create a FileManager instance for testing."""
    return FileManager(base_path=temp_dir)


class TestFileManager:
    """Test cases for FileManager class."""
    
    def test_create_directory(self, file_manager, temp_dir):
        """Test directory creation."""
        test_dir = "test_directory"
        created_path = file_manager.create_directory(test_dir)
        
        assert created_path.exists()
        assert created_path.is_dir()
        assert created_path == temp_dir / test_dir
        
    def test_create_nested_directory(self, file_manager, temp_dir):
        """Test nested directory creation."""
        nested_path = "level1/level2/level3"
        created_path = file_manager.create_directory(nested_path)
        
        assert created_path.exists()
        assert created_path.is_dir()
        assert created_path == temp_dir / nested_path
        
    def test_write_and_read_text(self, file_manager):
        """Test text file operations."""
        test_file = "test.txt"
        test_content = "Hello, World!\nThis is a test file."
        
        # Write file
        file_manager.write_text(test_file, test_content)
        
        # Check file exists
        assert file_manager.exists(test_file)
        assert file_manager.is_file(test_file)
        
        # Read file
        read_content = file_manager.read_text(test_file)
        assert read_content == test_content
        
    def test_append_text(self, file_manager):
        """Test text appending."""
        test_file = "append_test.txt"
        initial_content = "Initial content"
        appended_content = "\nAppended content"
        
        file_manager.write_text(test_file, initial_content)
        file_manager.append_text(test_file, appended_content)
        
        final_content = file_manager.read_text(test_file)
        assert final_content == initial_content + appended_content
        
    def test_write_and_read_json(self, file_manager):
        """Test JSON file operations."""
        test_file = "test.json"
        test_data = {
            "name": "Test",
            "version": "1.0",
            "features": ["file", "json", "test"],
            "settings": {
                "debug": True,
                "timeout": 30
            }
        }
        
        # Write JSON
        file_manager.write_json(test_file, test_data)
        
        # Check file exists
        assert file_manager.exists(test_file)
        
        # Read JSON
        read_data = file_manager.read_json(test_file)
        assert read_data == test_data
        
    def test_write_and_read_yaml(self, file_manager):
        """Test YAML file operations."""
        test_file = "test.yaml"
        test_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "testdb"
            },
            "features": ["yaml", "config", "test"]
        }
        
        # Write YAML
        file_manager.write_yaml(test_file, test_data)
        
        # Check file exists
        assert file_manager.exists(test_file)
        
        # Read YAML
        read_data = file_manager.read_yaml(test_file)
        assert read_data == test_data
        
    def test_file_operations(self, file_manager, temp_dir):
        """Test file manipulation operations."""
        # Create test files
        source_file = "source.txt"
        content = "Source file content"
        file_manager.write_text(source_file, content)
        
        # Test copy
        copied_file = "copied.txt"
        file_manager.copy_file(source_file, copied_file)
        
        assert file_manager.exists(copied_file)
        assert file_manager.read_text(copied_file) == content
        
        # Test move
        moved_file = "moved.txt"
        file_manager.move_file(copied_file, moved_file)
        
        assert not file_manager.exists(copied_file)
        assert file_manager.exists(moved_file)
        assert file_manager.read_text(moved_file) == content
        
        # Test delete
        file_manager.delete_file(moved_file)
        assert not file_manager.exists(moved_file)
        
    def test_directory_operations(self, file_manager):
        """Test directory manipulation."""
        test_dir = "test_dir_ops"
        file_manager.create_directory(test_dir)
        
        # Create file in directory
        file_manager.write_text(f"{test_dir}/file.txt", "content")
        
        # Test directory checks
        assert file_manager.exists(test_dir)
        assert file_manager.is_directory(test_dir)
        assert not file_manager.is_file(test_dir)
        
        # Test recursive delete
        file_manager.delete_directory(test_dir, recursive=True)
        assert not file_manager.exists(test_dir)
        
    def test_file_discovery(self, file_manager):
        """Test file listing and finding."""
        # Create test files
        files_to_create = [
            "test1.txt",
            "test2.txt", 
            "data.json",
            "config.yaml",
            "subdir/nested.txt"
        ]
        
        for file_path in files_to_create:
            file_manager.write_text(file_path, f"Content of {file_path}")
            
        # Test list_files
        all_files = file_manager.list_files(".")
        txt_files = file_manager.list_files(".", "*.txt")
        
        assert len(all_files) >= 4  # At least the files we created
        assert len(txt_files) == 2  # test1.txt and test2.txt
        
        # Test find_files (recursive)
        all_txt_files = file_manager.find_files("*.txt", recursive=True)
        assert len(all_txt_files) == 3  # Including subdir/nested.txt
        
    def test_file_statistics(self, file_manager):
        """Test file statistics and info."""
        test_file = "stats_test.txt"
        content = "This is a test file for statistics."
        
        file_manager.write_text(test_file, content)
        
        # Test file size
        size = file_manager.get_file_size(test_file)
        assert size == len(content.encode('utf-8'))
        
        # Test file stats
        stats = file_manager.get_file_stats(test_file)
        
        assert stats['size'] == size
        assert stats['is_file'] is True
        assert stats['is_dir'] is False
        assert stats['name'] == test_file
        assert stats['suffix'] == '.txt'
        
    def test_path_resolution(self, file_manager, temp_dir):
        """Test path resolution logic."""
        # Relative path
        rel_file = "relative.txt"
        file_manager.write_text(rel_file, "relative")
        assert file_manager.exists(rel_file)
        
        # Absolute path
        abs_file = temp_dir / "absolute.txt"
        file_manager.write_text(str(abs_file), "absolute")
        assert file_manager.exists(str(abs_file))
        
    def test_nonexistent_file_operations(self, file_manager):
        """Test operations on nonexistent files."""
        nonexistent = "does_not_exist.txt"
        
        # Should return False for existence checks
        assert not file_manager.exists(nonexistent)
        assert not file_manager.is_file(nonexistent)
        assert not file_manager.is_directory(nonexistent)
        
        # Should raise exceptions for read operations
        with pytest.raises(FileNotFoundError):
            file_manager.read_text(nonexistent)
            
        with pytest.raises(FileNotFoundError):
            file_manager.read_json(nonexistent)
            
    def test_invalid_json(self, file_manager):
        """Test handling of invalid JSON."""
        test_file = "invalid.json"
        file_manager.write_text(test_file, "{ invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            file_manager.read_json(test_file)
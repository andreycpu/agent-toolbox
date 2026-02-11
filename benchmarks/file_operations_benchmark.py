#!/usr/bin/env python3
"""Benchmark file operations performance."""

import time
import tempfile
import shutil
from pathlib import Path
from agent_toolbox import FileManager
from agent_toolbox.utils import PerformanceMonitor, format_duration


def benchmark_file_operations():
    """Benchmark various file operations."""
    monitor = PerformanceMonitor()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        fm = FileManager(base_path=temp_dir)
        
        # Test data
        small_text = "Hello, World!" * 100
        large_text = "Lorem ipsum dolor sit amet." * 10000
        json_data = {"key": f"value_{i}" for i in range(1000)}
        
        print("Running file operations benchmarks...")
        print("=" * 50)
        
        # Benchmark small file operations
        start_time = time.time()
        for i in range(100):
            fm.write_text(f"small_{i}.txt", small_text)
        small_write_time = time.time() - start_time
        monitor.record_timing("small_file_write", small_write_time)
        
        start_time = time.time()
        for i in range(100):
            content = fm.read_text(f"small_{i}.txt")
        small_read_time = time.time() - start_time
        monitor.record_timing("small_file_read", small_read_time)
        
        # Benchmark large file operations
        start_time = time.time()
        for i in range(10):
            fm.write_text(f"large_{i}.txt", large_text)
        large_write_time = time.time() - start_time
        monitor.record_timing("large_file_write", large_write_time)
        
        start_time = time.time()
        for i in range(10):
            content = fm.read_text(f"large_{i}.txt")
        large_read_time = time.time() - start_time
        monitor.record_timing("large_file_read", large_read_time)
        
        # Benchmark JSON operations
        start_time = time.time()
        for i in range(50):
            fm.write_json(f"data_{i}.json", json_data)
        json_write_time = time.time() - start_time
        monitor.record_timing("json_write", json_write_time)
        
        start_time = time.time()
        for i in range(50):
            data = fm.read_json(f"data_{i}.json")
        json_read_time = time.time() - start_time
        monitor.record_timing("json_read", json_read_time)
        
        # Print results
        print(f"Small files (100x): Write {format_duration(small_write_time)}, Read {format_duration(small_read_time)}")
        print(f"Large files (10x):  Write {format_duration(large_write_time)}, Read {format_duration(large_read_time)}")
        print(f"JSON files (50x):   Write {format_duration(json_write_time)}, Read {format_duration(json_read_time)}")
        
        # Get detailed stats
        stats = monitor.get_all_stats()
        print("\nDetailed Statistics:")
        for metric, data in stats["timings"].items():
            print(f"{metric}: avg={data['mean']:.4f}s, min={data['min']:.4f}s, max={data['max']:.4f}s")


if __name__ == "__main__":
    benchmark_file_operations()
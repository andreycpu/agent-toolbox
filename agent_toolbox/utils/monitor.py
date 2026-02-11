"""System and application monitoring utilities."""

import time
import psutil
import threading
from typing import Dict, Any, Optional, Callable, List
from .logger import Logger


class SystemMonitor:
    """Monitor system resources and performance."""
    
    def __init__(self):
        """Initialize system monitor."""
        self.logger = Logger("SystemMonitor")
        
    def get_cpu_usage(self, interval: float = 1.0) -> float:
        """Get CPU usage percentage."""
        return psutil.cpu_percent(interval=interval)
        
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percentage": memory.percent
        }
        
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Get disk usage information."""
        disk = psutil.disk_usage(path)
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percentage": (disk.used / disk.total) * 100
        }
        
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        stats = psutil.net_io_counters()
        return {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv
        }
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        return {
            "cpu": {
                "usage_percent": self.get_cpu_usage(),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True)
            },
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "network": self.get_network_stats(),
            "uptime": time.time() - psutil.boot_time()
        }


class PerformanceMonitor:
    """Monitor application performance and timing."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self.lock = threading.Lock()
        
    def time_function(self, func_name: str):
        """Decorator to time function execution."""
        import functools
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.record_timing(func_name, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.record_timing(f"{func_name}_error", duration)
                    raise
            return wrapper
        return decorator
        
    def record_timing(self, metric_name: str, duration: float) -> None:
        """Record timing metric."""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            self.metrics[metric_name].append(duration)
            
            # Keep only last 1000 measurements
            if len(self.metrics[metric_name]) > 1000:
                self.metrics[metric_name] = self.metrics[metric_name][-1000:]
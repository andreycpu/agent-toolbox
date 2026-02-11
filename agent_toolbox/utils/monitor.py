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
                
    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter."""
        with self.lock:
            self.counters[counter_name] = self.counters.get(counter_name, 0) + value
            
    def get_timing_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """Get timing statistics for a metric."""
        with self.lock:
            if metric_name not in self.metrics:
                return None
                
            timings = self.metrics[metric_name]
            if not timings:
                return None
                
            import statistics
            return {
                "count": len(timings),
                "min": min(timings),
                "max": max(timings),
                "mean": statistics.mean(timings),
                "median": statistics.median(timings),
                "std_dev": statistics.stdev(timings) if len(timings) > 1 else 0.0
            }
            
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all performance statistics."""
        with self.lock:
            stats = {
                "timings": {},
                "counters": self.counters.copy()
            }
            
            for metric_name in self.metrics.keys():
                timing_stats = self.get_timing_stats(metric_name)
                if timing_stats:
                    stats["timings"][metric_name] = timing_stats
                    
            return stats
            
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()


# Global performance monitor instance
_global_perf_monitor = PerformanceMonitor()

def monitor_performance(func_name: Optional[str] = None):
    """Decorator to monitor function performance using global monitor."""
    import functools
    
    def decorator(func: Callable) -> Callable:
        name = func_name or func.__name__
        return _global_perf_monitor.time_function(name)(func)
    return decorator

def get_performance_stats() -> Dict[str, Any]:
    """Get performance statistics from global monitor."""
    return _global_perf_monitor.get_all_stats()

def record_timing(metric_name: str, duration: float) -> None:
    """Record timing using global monitor."""
    _global_perf_monitor.record_timing(metric_name, duration)

def increment_counter(counter_name: str, value: int = 1) -> None:
    """Increment counter using global monitor.""" 
    _global_perf_monitor.increment_counter(counter_name, value)
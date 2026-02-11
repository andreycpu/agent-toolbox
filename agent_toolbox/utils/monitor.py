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
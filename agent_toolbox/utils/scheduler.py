"""Simple task scheduler for periodic and delayed execution."""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict, List
from .logger import Logger


class ScheduledTask:
    """Represents a scheduled task."""
    
    def __init__(self, func: Callable, interval: float, 
                 args: tuple = (), kwargs: dict = None, 
                 task_id: Optional[str] = None):
        """Initialize scheduled task."""
        self.func = func
        self.interval = interval
        self.args = args
        self.kwargs = kwargs or {}
        self.task_id = task_id or f"task_{id(self)}"
        self.next_run = time.time() + interval
        self.last_run: Optional[float] = None
        self.run_count = 0
        self.is_running = False
        
    def should_run(self) -> bool:
        """Check if task should run now."""
        return time.time() >= self.next_run
        
    def run(self) -> Any:
        """Execute the task."""
        if self.is_running:
            return None
            
        self.is_running = True
        try:
            result = self.func(*self.args, **self.kwargs)
            self.last_run = time.time()
            self.next_run = self.last_run + self.interval
            self.run_count += 1
            return result
        finally:
            self.is_running = False


class SimpleScheduler:
    """Simple task scheduler."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.logger = Logger("SimpleScheduler")
        
    def add_task(self, func: Callable, interval: float,
                 args: tuple = (), kwargs: dict = None,
                 task_id: Optional[str] = None) -> str:
        """Add a task to the scheduler."""
        task = ScheduledTask(func, interval, args, kwargs, task_id)
        self.tasks[task.task_id] = task
        self.logger.info(f"Added task {task.task_id} with {interval}s interval")
        return task.task_id
        
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the scheduler."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.logger.info(f"Removed task {task_id}")
            return True
        return False
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "interval": task.interval,
            "next_run": task.next_run,
            "last_run": task.last_run,
            "run_count": task.run_count,
            "is_running": task.is_running
        }
        
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks and their status."""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
        
    def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Scheduler started")
        
    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler stopped")
        
    def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self.running:
            current_time = time.time()
            
            # Check which tasks need to run
            for task in self.tasks.values():
                if task.should_run():
                    try:
                        task.run()
                    except Exception as e:
                        self.logger.error(f"Task {task.task_id} failed: {e}")
                        
            time.sleep(0.1)  # Small sleep to prevent busy waiting


# Convenience functions for common scheduling patterns
def schedule_every(seconds: float):
    """Decorator to schedule function every N seconds."""
    def decorator(func: Callable) -> Callable:
        scheduler = SimpleScheduler()
        scheduler.add_task(func, seconds)
        scheduler.start()
        return func
    return decorator


def run_once_after(seconds: float):
    """Decorator to run function once after N seconds."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            def delayed_execution():
                time.sleep(seconds)
                return func(*args, **kwargs)
            
            thread = threading.Thread(target=delayed_execution, daemon=True)
            thread.start()
            return thread
        return wrapper
    return decorator
"""Tool analytics and metrics collection system."""

import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import statistics
import json
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SET = "set"


@dataclass
class MetricEvent:
    """A single metric event."""
    
    name: str
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.COUNTER


@dataclass
class ToolUsageEvent:
    """Tool usage event for analytics."""
    
    tool_name: str
    tool_id: str
    operation: str  # execute, success, failure, timeout
    duration: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates metrics."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_events))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.sets: Dict[str, set] = defaultdict(set)
        self._lock = threading.RLock()
        
    def record_metric(self, event: MetricEvent) -> None:
        """Record a metric event."""
        with self._lock:
            self.events[event.name].append(event)
            
            if event.metric_type == MetricType.COUNTER:
                self.counters[event.name] += event.value
            elif event.metric_type == MetricType.GAUGE:
                self.gauges[event.name] = event.value
            elif event.metric_type == MetricType.SET:
                self.sets[event.name].add(event.value)
                
    def increment(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        event = MetricEvent(
            name=name,
            value=value,
            tags=tags or {},
            metric_type=MetricType.COUNTER
        )
        self.record_metric(event)
        
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        event = MetricEvent(
            name=name,
            value=value,
            tags=tags or {},
            metric_type=MetricType.GAUGE
        )
        self.record_metric(event)
        
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        event = MetricEvent(
            name=name,
            value=value,
            tags=tags or {},
            metric_type=MetricType.HISTOGRAM
        )
        self.record_metric(event)
        
    def timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        event = MetricEvent(
            name=name,
            value=duration,
            tags=tags or {},
            metric_type=MetricType.TIMER
        )
        self.record_metric(event)
        
    def set_metric(self, name: str, value: Any, tags: Optional[Dict[str, str]] = None) -> None:
        """Add to a set metric."""
        event = MetricEvent(
            name=name,
            value=value,
            tags=tags or {},
            metric_type=MetricType.SET
        )
        self.record_metric(event)
        
    def get_counter(self, name: str) -> float:
        """Get counter value."""
        with self._lock:
            return self.counters.get(name, 0)
            
    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        with self._lock:
            return self.gauges.get(name, 0)
            
    def get_histogram_stats(self, name: str, window_seconds: Optional[float] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            if name not in self.events:
                return {}
                
            events = self.events[name]
            
            # Filter by time window if specified
            if window_seconds:
                cutoff_time = time.time() - window_seconds
                values = [e.value for e in events if e.timestamp >= cutoff_time]
            else:
                values = [e.value for e in events]
                
            if not values:
                return {}
                
            return {
                'count': len(values),
                'sum': sum(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'p95': self._percentile(values, 0.95),
                'p99': self._percentile(values, 0.99)
            }
            
    def get_set_size(self, name: str) -> int:
        """Get set size."""
        with self._lock:
            return len(self.sets.get(name, set()))
            
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics summary."""
        with self._lock:
            metrics = {}
            
            # Counters
            for name, value in self.counters.items():
                metrics[f"counter.{name}"] = value
                
            # Gauges
            for name, value in self.gauges.items():
                metrics[f"gauge.{name}"] = value
                
            # Sets
            for name, values in self.sets.items():
                metrics[f"set.{name}.size"] = len(values)
                
            # Histograms
            for name in self.events:
                if any(e.metric_type == MetricType.HISTOGRAM for e in self.events[name]):
                    stats = self.get_histogram_stats(name)
                    for stat_name, stat_value in stats.items():
                        metrics[f"histogram.{name}.{stat_name}"] = stat_value
                        
            # Timers
            for name in self.events:
                if any(e.metric_type == MetricType.TIMER for e in self.events[name]):
                    stats = self.get_histogram_stats(name)
                    for stat_name, stat_value in stats.items():
                        metrics[f"timer.{name}.{stat_name}"] = stat_value
                        
            return metrics
            
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self.events.clear()
            self.counters.clear()
            self.gauges.clear()
            self.sets.clear()


class ToolAnalytics:
    """Analytics system specifically for tool usage."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.usage_events: deque = deque(maxlen=max_events)
        self.metrics_collector = MetricsCollector(max_events)
        self._lock = threading.RLock()
        
    def record_tool_usage(self, event: ToolUsageEvent) -> None:
        """Record a tool usage event."""
        with self._lock:
            self.usage_events.append(event)
            
            # Update metrics
            tags = {
                'tool_name': event.tool_name,
                'operation': event.operation
            }
            
            if event.user_id:
                tags['user_id'] = event.user_id
                
            # Record operation counter
            self.metrics_collector.increment(f"tool.{event.operation}", tags=tags)
            
            # Record duration if available
            if event.duration is not None:
                self.metrics_collector.timer(f"tool.duration", event.duration, tags=tags)
                
            # Record input/output sizes
            if event.input_size is not None:
                self.metrics_collector.histogram(f"tool.input_size", event.input_size, tags=tags)
                
            if event.output_size is not None:
                self.metrics_collector.histogram(f"tool.output_size", event.output_size, tags=tags)
                
            # Record unique tools and users
            self.metrics_collector.set_metric("tools.unique", event.tool_name)
            if event.user_id:
                self.metrics_collector.set_metric("users.unique", event.user_id)
                
    def get_tool_stats(self, tool_name: Optional[str] = None, 
                      window_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Get tool usage statistics."""
        with self._lock:
            events = list(self.usage_events)
            
            # Filter by tool name if specified
            if tool_name:
                events = [e for e in events if e.tool_name == tool_name]
                
            # Filter by time window if specified
            if window_seconds:
                cutoff_time = time.time() - window_seconds
                events = [e for e in events if e.timestamp >= cutoff_time]
                
            if not events:
                return {}
                
            stats = {
                'total_calls': len(events),
                'unique_tools': len(set(e.tool_name for e in events)),
                'unique_users': len(set(e.user_id for e in events if e.user_id)),
                'operations': defaultdict(int),
                'tools': defaultdict(int),
                'users': defaultdict(int),
                'errors': defaultdict(int)
            }
            
            durations = []
            input_sizes = []
            output_sizes = []
            
            for event in events:
                stats['operations'][event.operation] += 1
                stats['tools'][event.tool_name] += 1
                
                if event.user_id:
                    stats['users'][event.user_id] += 1
                    
                if event.error_type:
                    stats['errors'][event.error_type] += 1
                    
                if event.duration is not None:
                    durations.append(event.duration)
                    
                if event.input_size is not None:
                    input_sizes.append(event.input_size)
                    
                if event.output_size is not None:
                    output_sizes.append(event.output_size)
                    
            # Calculate duration statistics
            if durations:
                stats['duration'] = {
                    'count': len(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'mean': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'p95': self._percentile(durations, 0.95),
                    'p99': self._percentile(durations, 0.99)
                }
                
            # Calculate size statistics
            if input_sizes:
                stats['input_size'] = {
                    'min': min(input_sizes),
                    'max': max(input_sizes),
                    'mean': statistics.mean(input_sizes),
                    'median': statistics.median(input_sizes)
                }
                
            if output_sizes:
                stats['output_size'] = {
                    'min': min(output_sizes),
                    'max': max(output_sizes),
                    'mean': statistics.mean(output_sizes),
                    'median': statistics.median(output_sizes)
                }
                
            # Convert defaultdicts to regular dicts for JSON serialization
            stats['operations'] = dict(stats['operations'])
            stats['tools'] = dict(stats['tools'])
            stats['users'] = dict(stats['users'])
            stats['errors'] = dict(stats['errors'])
            
            # Calculate success rate
            total_executions = stats['operations'].get('execute', 0)
            successful_executions = stats['operations'].get('success', 0)
            
            if total_executions > 0:
                stats['success_rate'] = successful_executions / total_executions
            else:
                stats['success_rate'] = 0
                
            return stats
            
    def get_performance_trends(self, tool_name: str, 
                             window_seconds: float = 3600,
                             bucket_size: float = 300) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance trends over time."""
        with self._lock:
            events = [e for e in self.usage_events 
                     if e.tool_name == tool_name and 
                     time.time() - e.timestamp <= window_seconds]
                     
            if not events:
                return {}
                
            # Create time buckets
            min_timestamp = min(e.timestamp for e in events)
            max_timestamp = max(e.timestamp for e in events)
            
            buckets = []
            current_time = min_timestamp
            
            while current_time <= max_timestamp:
                bucket_events = [e for e in events 
                               if current_time <= e.timestamp < current_time + bucket_size]
                
                if bucket_events:
                    durations = [e.duration for e in bucket_events if e.duration is not None]
                    successes = sum(1 for e in bucket_events if e.operation == 'success')
                    failures = sum(1 for e in bucket_events if e.operation == 'failure')
                    
                    bucket_data = {
                        'timestamp': current_time,
                        'call_count': len(bucket_events),
                        'success_count': successes,
                        'failure_count': failures,
                        'success_rate': successes / len(bucket_events) if bucket_events else 0
                    }
                    
                    if durations:
                        bucket_data['avg_duration'] = statistics.mean(durations)
                        bucket_data['p95_duration'] = self._percentile(durations, 0.95)
                        
                    buckets.append(bucket_data)
                    
                current_time += bucket_size
                
            return {'buckets': buckets}
            
    def get_top_tools(self, limit: int = 10, 
                     window_seconds: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get top tools by usage."""
        stats = self.get_tool_stats(window_seconds=window_seconds)
        tools = stats.get('tools', {})
        
        # Sort by usage count
        sorted_tools = sorted(tools.items(), key=lambda x: x[1], reverse=True)
        
        return [{'tool_name': name, 'usage_count': count} 
                for name, count in sorted_tools[:limit]]
                
    def get_error_analysis(self, window_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Get error analysis."""
        with self._lock:
            events = list(self.usage_events)
            
            # Filter by time window if specified
            if window_seconds:
                cutoff_time = time.time() - window_seconds
                events = [e for e in events if e.timestamp >= cutoff_time]
                
            error_events = [e for e in events if e.operation == 'failure']
            
            if not error_events:
                return {'total_errors': 0}
                
            error_analysis = {
                'total_errors': len(error_events),
                'error_rate': len(error_events) / len(events) if events else 0,
                'errors_by_type': defaultdict(int),
                'errors_by_tool': defaultdict(int),
                'recent_errors': []
            }
            
            for event in error_events:
                if event.error_type:
                    error_analysis['errors_by_type'][event.error_type] += 1
                error_analysis['errors_by_tool'][event.tool_name] += 1
                
            # Get recent errors (last 10)
            recent_errors = sorted(error_events, key=lambda e: e.timestamp, reverse=True)[:10]
            error_analysis['recent_errors'] = [
                {
                    'tool_name': e.tool_name,
                    'error_type': e.error_type,
                    'timestamp': e.timestamp,
                    'metadata': e.metadata
                }
                for e in recent_errors
            ]
            
            # Convert defaultdicts to regular dicts
            error_analysis['errors_by_type'] = dict(error_analysis['errors_by_type'])
            error_analysis['errors_by_tool'] = dict(error_analysis['errors_by_tool'])
            
            return error_analysis
            
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    def export_data(self, format: str = "json") -> str:
        """Export analytics data."""
        with self._lock:
            data = {
                'tool_stats': self.get_tool_stats(),
                'metrics': self.metrics_collector.get_all_metrics(),
                'top_tools': self.get_top_tools(),
                'error_analysis': self.get_error_analysis(),
                'export_timestamp': time.time()
            }
            
            if format == "json":
                return json.dumps(data, indent=2)
            else:
                return str(data)
                
    def clear_data(self) -> None:
        """Clear all analytics data."""
        with self._lock:
            self.usage_events.clear()
            self.metrics_collector.clear_metrics()


class AnalyticsDecorator:
    """Decorator for automatic tool analytics collection."""
    
    def __init__(self, analytics: ToolAnalytics):
        self.analytics = analytics
        
    def track_tool(self, 
                  tool_name: Optional[str] = None,
                  user_id_param: Optional[str] = None,
                  session_id_param: Optional[str] = None):
        """Decorator to track tool usage."""
        
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Extract parameters
                actual_tool_name = tool_name or func.__name__
                user_id = kwargs.get(user_id_param) if user_id_param else None
                session_id = kwargs.get(session_id_param) if session_id_param else None
                
                # Calculate input size
                input_size = self._calculate_size(args, kwargs)
                
                # Record execution start
                start_time = time.time()
                self.analytics.record_tool_usage(ToolUsageEvent(
                    tool_name=actual_tool_name,
                    tool_id=f"{actual_tool_name}_{int(start_time)}",
                    operation='execute',
                    user_id=user_id,
                    session_id=session_id,
                    input_size=input_size
                ))
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record success
                    duration = time.time() - start_time
                    output_size = self._calculate_size(result)
                    
                    self.analytics.record_tool_usage(ToolUsageEvent(
                        tool_name=actual_tool_name,
                        tool_id=f"{actual_tool_name}_{int(start_time)}",
                        operation='success',
                        duration=duration,
                        user_id=user_id,
                        session_id=session_id,
                        output_size=output_size
                    ))
                    
                    return result
                    
                except Exception as e:
                    # Record failure
                    duration = time.time() - start_time
                    
                    self.analytics.record_tool_usage(ToolUsageEvent(
                        tool_name=actual_tool_name,
                        tool_id=f"{actual_tool_name}_{int(start_time)}",
                        operation='failure',
                        duration=duration,
                        user_id=user_id,
                        session_id=session_id,
                        error_type=type(e).__name__,
                        metadata={'error_message': str(e)}
                    ))
                    
                    raise
                    
            return wrapper
        return decorator
        
    def _calculate_size(self, *objects) -> int:
        """Calculate approximate size of objects."""
        try:
            total_size = 0
            for obj in objects:
                if isinstance(obj, (str, bytes)):
                    total_size += len(obj)
                elif isinstance(obj, (list, tuple, dict, set)):
                    total_size += len(str(obj))
                else:
                    total_size += len(str(obj))
            return total_size
        except:
            return 0


# Global analytics instance
_global_analytics = None


def get_global_analytics() -> ToolAnalytics:
    """Get the global analytics instance."""
    global _global_analytics
    if _global_analytics is None:
        _global_analytics = ToolAnalytics()
    return _global_analytics


def track_tool_usage(tool_name: Optional[str] = None,
                    user_id_param: Optional[str] = None,
                    session_id_param: Optional[str] = None):
    """Decorator for tracking tool usage with global analytics."""
    analytics = get_global_analytics()
    decorator = AnalyticsDecorator(analytics)
    return decorator.track_tool(tool_name, user_id_param, session_id_param)
"""Application metrics and monitoring"""
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict, deque

@dataclass
class RequestMetrics:
    """Metrics for individual requests"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    user_id: Optional[str] = None

@dataclass
class ServiceMetrics:
    """Service-level metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    requests_per_minute: float = 0.0
    error_rate: float = 0.0
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=1000))

class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.service_metrics = ServiceMetrics()
        self.endpoint_metrics: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        self.response_times: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()
    
    async def record_request(self, metrics: RequestMetrics):
        """Record request metrics"""
        async with self._lock:
            # Update service-level metrics
            self.service_metrics.total_requests += 1
            self.service_metrics.recent_requests.append(metrics)
            self.response_times.append(metrics.duration_ms)
            
            if 200 <= metrics.status_code < 400:
                self.service_metrics.successful_requests += 1
            else:
                self.service_metrics.failed_requests += 1
            
            # Update endpoint-specific metrics
            endpoint_key = f"{metrics.method} {metrics.endpoint}"
            endpoint_metrics = self.endpoint_metrics[endpoint_key]
            endpoint_metrics.total_requests += 1
            endpoint_metrics.recent_requests.append(metrics)
            
            if 200 <= metrics.status_code < 400:
                endpoint_metrics.successful_requests += 1
            else:
                endpoint_metrics.failed_requests += 1
            
            # Update calculated metrics
            await self._update_calculated_metrics()
    
    async def _update_calculated_metrics(self):
        """Update calculated metrics like averages and percentiles"""
        if self.response_times:
            sorted_times = sorted(self.response_times)
            self.service_metrics.avg_response_time = sum(sorted_times) / len(sorted_times)
            
            # Calculate percentiles
            if len(sorted_times) >= 20:  # Only calculate if we have enough data
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                self.service_metrics.p95_response_time = sorted_times[p95_idx]
                self.service_metrics.p99_response_time = sorted_times[p99_idx]
        
        # Calculate error rate
        if self.service_metrics.total_requests > 0:
            self.service_metrics.error_rate = (
                self.service_metrics.failed_requests / self.service_metrics.total_requests
            )
        
        # Calculate requests per minute
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = [
            req for req in self.service_metrics.recent_requests
            if req.timestamp > one_minute_ago
        ]
        self.service_metrics.requests_per_minute = len(recent_requests)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        return {
            "service": {
                "total_requests": self.service_metrics.total_requests,
                "successful_requests": self.service_metrics.successful_requests,
                "failed_requests": self.service_metrics.failed_requests,
                "error_rate": round(self.service_metrics.error_rate * 100, 2),
                "avg_response_time_ms": round(self.service_metrics.avg_response_time, 2),
                "p95_response_time_ms": round(self.service_metrics.p95_response_time, 2),
                "p99_response_time_ms": round(self.service_metrics.p99_response_time, 2),
                "requests_per_minute": self.service_metrics.requests_per_minute
            },
            "endpoints": {
                endpoint: {
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "failed_requests": metrics.failed_requests,
                    "error_rate": round(
                        (metrics.failed_requests / metrics.total_requests * 100) 
                        if metrics.total_requests > 0 else 0, 2
                    )
                }
                for endpoint, metrics in self.endpoint_metrics.items()
            }
        }

# Global metrics collector
metrics_collector = MetricsCollector()
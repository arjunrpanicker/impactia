"""Request middleware for logging, metrics, and monitoring"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from ..core.metrics import metrics_collector, RequestMetrics
from ..core.logging import get_logger
from ..config.settings import settings

logger = get_logger(__name__)

class RequestMiddleware(BaseHTTPMiddleware):
    """Middleware for request processing, logging, and metrics"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        if settings.enable_request_logging:
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    'extra_fields': {
                        'request_id': request_id,
                        'method': request.method,
                        'path': request.url.path,
                        'client_ip': request.client.host if request.client else None
                    }
                }
            )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            if settings.enable_metrics:
                await metrics_collector.record_request(RequestMetrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    timestamp=request.state.start_time if hasattr(request.state, 'start_time') else None,
                    request_size=request.headers.get('content-length'),
                    response_size=response.headers.get('content-length')
                ))
            
            # Log request completion
            if settings.enable_request_logging:
                logger.info(
                    f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        'extra_fields': {
                            'request_id': request_id,
                            'status_code': response.status_code,
                            'duration_ms': round(duration_ms, 2)
                        }
                    }
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Record error metrics
            if settings.enable_metrics:
                await metrics_collector.record_request(RequestMetrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=500,
                    duration_ms=duration_ms,
                    timestamp=request.state.start_time if hasattr(request.state, 'start_time') else None
                ))
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    'extra_fields': {
                        'request_id': request_id,
                        'error': str(e),
                        'duration_ms': round(duration_ms, 2)
                    }
                }
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.client_requests = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute ago
        if client_ip in self.client_requests:
            self.client_requests[client_ip] = [
                req_time for req_time in self.client_requests[client_ip]
                if req_time > cutoff_time
            ]
        
        # Check rate limit
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        if len(self.client_requests[client_ip]) >= self.calls_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self.client_requests[client_ip].append(current_time)
        
        return await call_next(request)
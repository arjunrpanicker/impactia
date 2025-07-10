import asyncio
import logging
from typing import Any, Callable, TypeVar, Optional
from functools import wraps

T = TypeVar('T')

class RAGServiceError(Exception):
    """Base exception for RAG service errors"""
    pass

class EmbeddingError(RAGServiceError):
    """Error during embedding generation"""
    pass

class VectorSearchError(RAGServiceError):
    """Error during vector search"""
    pass

class DependencyAnalysisError(RAGServiceError):
    """Error during dependency analysis"""
    pass

class RetryableError(RAGServiceError):
    """Error that can be retried"""
    pass

def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions with exponential backoff"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RetryableError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"All {max_retries + 1} attempts failed")
                except Exception as e:
                    # Non-retryable errors
                    logging.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator

def handle_errors(error_type: type = RAGServiceError):
    """Decorator for consistent error handling"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {e}")
                if isinstance(e, RAGServiceError):
                    raise
                raise error_type(f"Error in {func.__name__}: {str(e)}") from e
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise RetryableError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (asyncio.get_event_loop().time() - self.last_failure_time) >= self.timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
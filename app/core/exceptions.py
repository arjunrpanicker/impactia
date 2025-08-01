"""Custom exceptions for the application"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class BaseAppException(Exception):
    """Base exception for application-specific errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None, 
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BaseAppException):
    """Validation error"""
    pass

class ConfigurationError(BaseAppException):
    """Configuration error"""
    pass

class ExternalServiceError(BaseAppException):
    """External service error"""
    pass

class AzureOpenAIError(ExternalServiceError):
    """Azure OpenAI service error"""
    pass

class SupabaseError(ExternalServiceError):
    """Supabase service error"""
    pass

class AzureDevOpsError(ExternalServiceError):
    """Azure DevOps service error"""
    pass

class RateLimitError(BaseAppException):
    """Rate limit exceeded error"""
    pass

class ProcessingError(BaseAppException):
    """Processing error"""
    pass

class NotFoundError(BaseAppException):
    """Resource not found error"""
    pass

# HTTP Exception mappings
def create_http_exception(
    exception: BaseAppException,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> HTTPException:
    """Create HTTPException from BaseAppException"""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": exception.message,
            "error_code": exception.error_code,
            "details": exception.details
        }
    )

# Exception to HTTP status code mapping
EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_400_BAD_REQUEST,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    AzureOpenAIError: status.HTTP_502_BAD_GATEWAY,
    SupabaseError: status.HTTP_502_BAD_GATEWAY,
    AzureDevOpsError: status.HTTP_502_BAD_GATEWAY,
    ProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}
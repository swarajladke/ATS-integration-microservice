"""
Error handling module.
Provides custom exceptions and error response formatting.
"""
from typing import Any, Dict, Optional
from enum import Enum
import json


class ErrorCode(Enum):
    """Standardized error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ATS_CONNECTION_ERROR = "ATS_CONNECTION_ERROR"
    ATS_AUTHENTICATION_ERROR = "ATS_AUTHENTICATION_ERROR"
    ATS_RATE_LIMIT_ERROR = "ATS_RATE_LIMIT_ERROR"
    ATS_NOT_FOUND = "ATS_NOT_FOUND"
    ATS_SERVICE_ERROR = "ATS_SERVICE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ATSError(Exception):
    """Base exception for ATS-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.ATS_SERVICE_ERROR,
        retryable: bool = False,
        status_code: int = 500,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        self.status_code = status_code
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to API response format."""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "retryable": self.retryable
        }


class ValidationError(ATSError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            retryable=False,
            status_code=400
        )
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.details:
            result["details"] = self.details
        return result


class ATSConnectionError(ATSError):
    """Raised when connection to ATS fails."""
    
    def __init__(self, message: str = "Unable to connect to ATS service"):
        super().__init__(
            message=message,
            error_code=ErrorCode.ATS_CONNECTION_ERROR,
            retryable=True,
            status_code=503
        )


class ATSAuthenticationError(ATSError):
    """Raised when ATS authentication fails."""
    
    def __init__(self, message: str = "ATS authentication failed"):
        super().__init__(
            message=message,
            error_code=ErrorCode.ATS_AUTHENTICATION_ERROR,
            retryable=False,
            status_code=401
        )


class ATSRateLimitError(ATSError):
    """Raised when ATS rate limit is exceeded."""
    
    def __init__(self, message: str = "ATS rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.ATS_RATE_LIMIT_ERROR,
            retryable=True,
            status_code=429
        )
        self.retry_after = retry_after


class ATSNotFoundError(ATSError):
    """Raised when requested resource is not found in ATS."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code=ErrorCode.ATS_NOT_FOUND,
            retryable=False,
            status_code=404
        )


def format_error_response(error: Exception, status_code: int = 500) -> Dict[str, Any]:
    """Format any exception into a standardized API error response."""
    if isinstance(error, ATSError):
        return {
            "statusCode": error.status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error.to_dict())
        }
    
    # Generic error - hide internal details
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "error": ErrorCode.INTERNAL_ERROR.value,
            "message": "An unexpected error occurred",
            "retryable": False
        })
    }


def format_success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Format successful response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data, default=str)
    }

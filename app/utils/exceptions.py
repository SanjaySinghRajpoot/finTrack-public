"""
Custom exception classes for the FinTrack application.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class FinTrackException(Exception):
    """Base exception class for FinTrack application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(FinTrackException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AuthenticationError(FinTrackException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(FinTrackException):
    """Raised when user doesn't have permission."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(FinTrackException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, identifier: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier, **(details or {})},
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(FinTrackException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR", 
            details=details,
            status_code=status.HTTP_409_CONFLICT
        )


class BusinessLogicError(FinTrackException):
    """Raised when business logic rules are violated."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ExternalServiceError(FinTrackException):
    """Raised when external service calls fail."""
    
    def __init__(self, service: str, message: str = None, details: Optional[Dict[str, Any]] = None):
        message = message or f"External service {service} is unavailable"
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class DatabaseError(FinTrackException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class RateLimitError(FinTrackException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class SubscriptionError(FinTrackException):
    """Raised when subscription/credit issues occur."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_ERROR",
            details=details,
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )
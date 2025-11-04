"""
Centralized exception handlers for the FinTrack FastAPI application.
"""
import logging
import traceback
from datetime import datetime
from typing import Dict, Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError

from app.utils.exceptions import (
    FinTrackException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    BusinessLogicError,
    ExternalServiceError,
    DatabaseError,
    RateLimitError,
    SubscriptionError
)

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    details: Dict[str, Any] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    request_id: str = None
) -> JSONResponse:
    """Create a standardized error response."""
    response_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    if details:
        response_data["error"]["details"] = details
    
    if request_id:
        response_data["error"]["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def fintrack_exception_handler(request: Request, exc: FinTrackException) -> JSONResponse:
    """Handle custom FinTrack exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log to structured logger
    logger.error(
        f"FinTrack Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method
        }
    )
    
    # Log to console for immediate visibility
    print(f"🚨 FinTrack Exception [{request_id}]: {exc.error_code} - {exc.message}")
    if exc.details:
        print(f"   Details: {exc.details}")
    print(f"   Path: {request.method} {request.url}")
    
    return create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
        request_id=request_id
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    error_code = "HTTP_ERROR"
    if exc.status_code == 401:
        error_code = "AUTHENTICATION_ERROR"
    elif exc.status_code == 403:
        error_code = "AUTHORIZATION_ERROR"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 422:
        error_code = "VALIDATION_ERROR"
    
    # Log to structured logger
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method
        }
    )
    
    # Log to console for immediate visibility
    print(f"⚠️  HTTP Exception [{request_id}]: {error_code} ({exc.status_code}) - {exc.detail}")
    print(f"   Path: {request.method} {request.url}")
    
    return create_error_response(
        error_code=error_code,
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI request validation errors."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Log to structured logger
    logger.warning(
        f"Validation Error: {len(validation_errors)} validation errors",
        extra={
            "validation_errors": validation_errors,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method
        }
    )
    
    # Log to console for immediate visibility
    print(f"❌ Validation Error [{request_id}]: {len(validation_errors)} validation errors")
    for error in validation_errors:
        print(f"   Field '{error['field']}': {error['message']}")
    print(f"   Path: {request.method} {request.url}")
    
    return create_error_response(
        error_code="VALIDATION_ERROR",
        message="Input validation failed",
        details={"validation_errors": validation_errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    request_id = getattr(request.state, 'request_id', None)
    
    error_code = "DATABASE_ERROR"
    message = "Database operation failed"
    
    # Handle specific SQLAlchemy errors
    if isinstance(exc, IntegrityError):
        error_code = "CONFLICT_ERROR"
        message = "Data integrity constraint violation"
        
        # Extract constraint details if available
        if hasattr(exc, 'orig') and exc.orig:
            orig_error = str(exc.orig)
            if "duplicate key" in orig_error.lower():
                message = "Duplicate entry found"
            elif "foreign key" in orig_error.lower():
                message = "Referenced record not found"
    
    # Log to structured logger
    logger.error(
        f"Database Error: {type(exc).__name__} - {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # Log to console for immediate visibility
    print(f"💾 Database Error [{request_id}]: {error_code} - {message}")
    print(f"   Exception Type: {type(exc).__name__}")
    print(f"   Exception Message: {str(exc)}")
    print(f"   Path: {request.method} {request.url}")
    
    return create_error_response(
        error_code=error_code,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log to structured logger
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # Log to console for immediate visibility
    print(f"💥 Unhandled Exception [{request_id}]: {type(exc).__name__} - {str(exc)}")
    print(f"   Path: {request.method} {request.url}")
    print(f"   Traceback: {traceback.format_exc()}")
    
    # Don't expose internal error details in production
    message = "An unexpected error occurred"
    details = None
    
    # In development, you might want to expose more details
    # Uncomment the following lines for development debugging:
    # message = str(exc)
    # details = {"traceback": traceback.format_exc()}
    
    return create_error_response(
        error_code="INTERNAL_ERROR",
        message=message,
        details=details,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(FinTrackException, fintrack_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
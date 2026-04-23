# Core Exceptions
from fastapi import status


class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict | None = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed", details: dict | None = None):
        super().__init__(
            message=message,
            code="AUTH_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(AppException):
    """User not authorized for this action"""
    def __init__(self, message: str = "Not authorized", details: dict | None = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ValidationError(AppException):
    """Input validation failed"""
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class DuplicateEntryError(AppException):
    """Record already exists"""
    def __init__(self, message: str = "Record already exists", details: dict | None = None):
        super().__init__(
            message=message,
            code="DUPLICATE_ENTRY",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class RateLimitError(AppException):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", details: dict | None = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


class BlockedUserError(AppException):
    """User account is blocked"""
    def __init__(self, message: str = "User account is blocked", details: dict | None = None):
        super().__init__(
            message=message,
            code="USER_BLOCKED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class VerificationPendingError(AppException):
    """User verification not completed"""
    def __init__(self, message: str = "Verification pending", details: dict | None = None):
        super().__init__(
            message=message,
            code="VERIFICATION_PENDING",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ExternalServiceError(AppException):
    """External service (email, SMS, etc.) failed"""
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message=f"{service} service error: {message}",
            code=f"{service.upper()}_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

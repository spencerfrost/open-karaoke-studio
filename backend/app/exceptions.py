# backend/app/exceptions.py
"""
Custom exception classes for the application
"""


from typing import Optional


class KaraokeBaseError(Exception):
    """Base exception for all karaoke application errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ServiceError(KaraokeBaseError):
    """Base exception for service layer errors"""


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found"""


class ValidationError(ServiceError):
    """Raised when input validation fails"""


class DatabaseError(ServiceError):
    """Raised when database operations fail"""


class AudioProcessingError(ServiceError):
    """Raised when audio processing operations fail"""


class YouTubeError(ServiceError):
    """Raised when YouTube operations fail"""


class FileSystemError(ServiceError):
    """Raised when file system operations fail"""


class JobError(ServiceError):
    """Raised when job processing operations fail"""


class ConfigurationError(KaraokeBaseError):
    """Raised when configuration is invalid"""


class NetworkError(ServiceError):
    """Raised when network operations fail"""


# More specific exceptions for better error handling
class RequestValidationError(ValidationError):
    """Raised when API request validation fails"""

    def __init__(
        self, message: str, field: Optional[str] = None, value: Optional[str] = None
    ):
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = str(value)
        super().__init__(message, "REQUEST_VALIDATION_ERROR", details)


class ResourceNotFoundError(NotFoundError):
    """Raised when a specific resource is not found"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID '{resource_id}' not found"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class DuplicateResourceError(ValidationError):
    """Raised when attempting to create a resource that already exists"""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        details = {"resource_type": resource_type, "identifier": identifier}
        super().__init__(message, "DUPLICATE_RESOURCE", details)


class FileOperationError(FileSystemError):
    """Raised when file operations fail"""

    def __init__(self, operation: str, file_path: str, reason: Optional[str] = None):
        message = f"Failed to {operation} file: {file_path}"
        if reason:
            message += f" - {reason}"
        details = {"operation": operation, "file_path": file_path}
        if reason:
            details["reason"] = reason
        super().__init__(message, "FILE_OPERATION_ERROR", details)


class InvalidTrackTypeError(ValidationError):
    """Raised when an invalid track type is requested"""

    def __init__(self, requested_type: str, valid_types: Optional[list[str]] = None):
        valid_types = valid_types or ["vocals", "instrumental", "original"]
        message = f"Invalid track type '{requested_type}'. Valid types: {', '.join(valid_types)}"
        details = {"requested_type": requested_type, "valid_types": valid_types}
        super().__init__(message, "INVALID_TRACK_TYPE", details)

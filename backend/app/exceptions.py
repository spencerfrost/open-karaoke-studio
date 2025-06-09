# backend/app/exceptions.py
"""
Custom exception classes for the application
"""


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found"""
    pass


class ValidationError(ServiceError):
    """Raised when input validation fails"""
    pass


class DatabaseError(ServiceError):
    """Raised when database operations fail"""
    pass

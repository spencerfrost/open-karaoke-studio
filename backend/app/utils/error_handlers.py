# backend/app/utils/error_handlers.py
"""
Standardized error handling utilities for consistent API responses
"""

import logging
from typing import Optional, Dict, Any
from flask import jsonify, Flask
from werkzeug.exceptions import HTTPException

from ..exceptions import (
    KaraokeBaseError,
    ValidationError,
    DatabaseError,
    NotFoundError,
    ServiceError,
    AudioProcessingError,
    YouTubeError,
    FileSystemError,
    JobError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    error: Exception, status_code: int = 500, context: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create standardized error response with consistent format

    Args:
        error: The exception that occurred
        status_code: HTTP status code to return
        context: Additional context for logging

    Returns:
        Tuple of (response, status_code) for Flask
    """
    # Log the error with context
    log_context = context or {}

    if isinstance(error, KaraokeBaseError):
        # Custom application errors - log as warning/error based on severity
        if status_code >= 500:
            logger.error(
                "Application error: %s",
                error.message,
                extra={
                    "error_code": error.error_code,
                    "details": error.details,
                    **log_context,
                },
                exc_info=True,
            )
        else:
            logger.warning(
                "Client error: %s",
                error.message,
                extra={
                    "error_code": error.error_code,
                    "details": error.details,
                    **log_context,
                },
            )

        return (
            jsonify(
                {
                    "error": error.message,
                    "code": error.error_code or "APPLICATION_ERROR",
                    "details": error.details,
                }
            ),
            status_code,
        )

    elif isinstance(error, HTTPException):
        # Werkzeug HTTP exceptions
        logger.warning(
            "HTTP error: %s",
            error.description,
            extra={"status_code": error.code, **log_context},
        )

        return (
            jsonify(
                {
                    "error": error.description,
                    "code": f"HTTP_{error.code}",
                    "details": {},
                }
            ),
            error.code,
        )

    else:
        # Unexpected errors - always log as error with full traceback
        logger.error("Unexpected error: %s", str(error), extra=log_context, exc_info=True)

        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "details": {},
                }
            ),
            500,
        )


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for the Flask application

    Args:
        app: Flask application instance
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return create_error_response(error, 400)

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error: NotFoundError):
        return create_error_response(error, 404)

    @app.errorhandler(DatabaseError)
    def handle_database_error(error: DatabaseError):
        return create_error_response(error, 500)

    @app.errorhandler(AudioProcessingError)
    def handle_audio_processing_error(error: AudioProcessingError):
        return create_error_response(error, 500)

    @app.errorhandler(YouTubeError)
    def handle_youtube_error(error: YouTubeError):
        return create_error_response(error, 422)  # Unprocessable Entity

    @app.errorhandler(FileSystemError)
    def handle_filesystem_error(error: FileSystemError):
        return create_error_response(error, 500)

    @app.errorhandler(JobError)
    def handle_job_error(error: JobError):
        return create_error_response(error, 500)

    @app.errorhandler(ConfigurationError)
    def handle_configuration_error(error: ConfigurationError):
        return create_error_response(error, 500)

    @app.errorhandler(ServiceError)
    def handle_generic_service_error(error: ServiceError):
        return create_error_response(error, 500)

    @app.errorhandler(KaraokeBaseError)
    def handle_karaoke_base_error(error: KaraokeBaseError):
        return create_error_response(error, 500)

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        return create_error_response(
            Exception("An unexpected error occurred"),
            500,
            {"original_error": str(error)},
        )

    logger.info("Error handlers registered successfully")


def handle_api_error(func):
    """
    Decorator to wrap API endpoints with consistent error handling

    Usage:
        @song_bp.route("/api/songs", methods=["GET"])
        @handle_api_error
        def get_songs():
            # Your endpoint code here
            pass
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KaraokeBaseError:
            # Let our custom error handlers deal with these
            raise
        except Exception as e:
            # Convert unexpected exceptions to ServiceError
            logger.error("Unhandled exception in %s: %s", func.__name__, str(e), exc_info=True)
            raise ServiceError(
                f"Unexpected error in {func.__name__}",
                "UNEXPECTED_SERVICE_ERROR",
                {"function": func.__name__, "original_error": str(e)},
            )

    return wrapper

"""Shared exception types for Celery job processing."""


class AudioProcessingError(Exception):
    """Raised when an audio processing pipeline step fails."""

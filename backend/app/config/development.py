"""
Development configuration for Open Karaoke Studio backend.
"""

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False

    @property
    def DEFAULT_CORS_ORIGINS(self) -> list[str]:
        """Default CORS origins for development environment."""
        return [
            "http://localhost:5173",  # Vite dev server default
            "http://127.0.0.1:5173",  # Alternative localhost
            "http://localhost:3000",  # Alternative dev port
            "http://127.0.0.1:3000",  # Alternative localhost
            "http://192.168.50.112:5173",  # Network IP access
        ]

    @classmethod
    def validate_config(cls):
        """Development environment has more relaxed validation."""
        # In development, we don't require SECRET_KEY to be explicitly set

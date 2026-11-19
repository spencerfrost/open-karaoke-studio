"""
Production configuration for Open Karaoke Studio backend.
"""

import os

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    @property
    def DEFAULT_CORS_ORIGINS(self) -> list[str]:
        """Default CORS origins for production environment."""
        # In production, we should be more restrictive
        # These should be overridden via CORS_ORIGINS environment variable
        return []

    @classmethod
    def validate_config(cls):
        """Production environment requires strict validation."""
        super().validate_config()

        required_vars = []

        # Production-specific required environment variables
        if not os.environ.get("SECRET_KEY"):
            required_vars.append("SECRET_KEY")

        if not os.environ.get("CORS_ORIGINS"):
            required_vars.append("CORS_ORIGINS")

        if required_vars:
            raise ValueError(
                f"Production environment missing required variables: {', '.join(required_vars)}"
            )

    # Production-specific optimizations
    SQLALCHEMY_ECHO = False

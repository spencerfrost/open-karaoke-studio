"""
Testing configuration for Open Karaoke Studio backend.
"""

from .base import BaseConfig


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    DEBUG = True
    TESTING = True

    # Use in-memory database for testing
    DATABASE_URL = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    @property
    def DEFAULT_CORS_ORIGINS(self) -> list[str]:
        """Default CORS origins for testing environment."""
        return ["*"]  # Allow all origins in testing

    @classmethod
    def validate_config(cls):
        """Testing environment has minimal validation."""
        # No strict requirements for testing

    def __init__(self):
        """Initialize testing configuration without directory creation."""
        super().__init__()
        # Don't create directories in testing mode
        self.validate_config()

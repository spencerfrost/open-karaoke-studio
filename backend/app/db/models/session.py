"""
Session management models for Open Karaoke Studio.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KaraokeSession(Base):
    """Model for karaoke sessions."""

    __tablename__ = "karaoke_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    host_device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to session devices
    devices: Mapped[List["SessionDevice"]] = relationship(
        "SessionDevice", back_populates="session", cascade="all, delete-orphan"
    )

    @classmethod
    def generate_session_id(cls) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(24)

    @classmethod
    def generate_display_code(cls) -> str:
        """Generate a 4-character display code."""
        # Use uppercase letters and numbers, excluding confusing characters (0, O, 1, I)
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        return "".join(secrets.choice(chars) for _ in range(4))

    @classmethod
    def create_new_session(
        cls, host_device_id: str, duration_hours: int = 24
    ) -> "KaraokeSession":
        """Create a new karaoke session."""
        session = cls(
            session_id=cls.generate_session_id(),
            display_code=cls.generate_display_code(),
            host_device_id=host_device_id,
            expires_at=datetime.utcnow() + timedelta(hours=duration_hours),
        )
        return session

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at

    def get_active_devices(self) -> List["SessionDevice"]:
        """Get all active devices in this session."""
        return [device for device in self.devices if device.is_active]

    def get_device_count(self) -> int:
        """Get the count of active devices in this session."""
        return len(self.get_active_devices())


class SessionDevice(Base):
    """Model for devices connected to a session."""

    __tablename__ = "session_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("karaoke_sessions.session_id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship to session
    session: Mapped["KaraokeSession"] = relationship(
        "KaraokeSession", back_populates="devices"
    )

    DEVICE_TYPES = ["stage", "performer", "controller"]

    def __init__(self, **kwargs):
        """Initialize session device with validation."""
        device_type = kwargs.get("device_type")
        if device_type and device_type not in self.DEVICE_TYPES:
            raise ValueError(f"Invalid device type: {device_type}")
        super().__init__(**kwargs)
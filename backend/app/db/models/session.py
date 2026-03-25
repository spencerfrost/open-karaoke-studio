"""
Session management models for Open Karaoke Studio.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from .base import Base

if TYPE_CHECKING:
    from .queue import KaraokeQueueItem
    from .song import DbSong


class KaraokeSession(Base):
    """Model for karaoke sessions."""

    __tablename__ = "karaoke_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    display_code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    host_device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    host_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to session devices
    devices: Mapped[List["SessionDevice"]] = relationship(
        "SessionDevice", back_populates="session", cascade="all, delete-orphan"
    )

    # Relationship to queue items
    queue_items: Mapped[List["KaraokeQueueItem"]] = relationship(
        "KaraokeQueueItem", back_populates="session", cascade="all, delete-orphan"
    )

    # Relationship to playback state
    playback_state: Mapped[Optional["SessionPlaybackState"]] = relationship(
        "SessionPlaybackState",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @classmethod
    def generate_session_id(cls) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(24)

    @classmethod
    def generate_display_code(cls, db_session) -> str:
        """Generate a unique 4-character display code using only capital letters, checking against active sessions."""
        # Use only uppercase letters for simplicity and readability
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        # Keep trying until we find an unused code
        max_attempts = 100  # Prevent infinite loop, though 26^4 = 456,976 possibilities make this unlikely
        for _ in range(max_attempts):
            code = "".join(secrets.choice(chars) for _ in range(4))

            # Check if this code is already in use by an active session
            existing = (
                db_session.query(cls)
                .filter(
                    cls.display_code == code,
                    cls.is_active == True,
                    cls.expires_at > datetime.utcnow(),
                )
                .first()
            )

            if not existing:
                return code

        # If we somehow exhaust all possibilities (extremely unlikely), raise an error
        raise RuntimeError("Unable to generate unique display code - all codes in use")

    @classmethod
    def create_new_session(
        cls, db_session, host_device_id: str, duration_hours: int = 24
    ) -> "KaraokeSession":
        """Create a new karaoke session with unique display code."""
        display_code = cls.generate_display_code(db_session)
        session = cls(
            session_id=display_code,  # Use display_code as session_id for simplicity
            display_code=display_code,
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
        String(4), ForeignKey("karaoke_sessions.session_id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

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


class SessionPlaybackState(Base):
    """Persisted playback state for a karaoke session."""

    __tablename__ = "session_playback_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("karaoke_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_queue_item_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("karaoke_queue.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_song_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("songs.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_playing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_time: Mapped[float] = mapped_column(nullable=False, default=0.0)
    duration: Mapped[float] = mapped_column(nullable=False, default=0.0)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session: Mapped["KaraokeSession"] = relationship(
        "KaraokeSession", back_populates="playback_state"
    )
    current_queue_item: Mapped[Optional["KaraokeQueueItem"]] = relationship(
        "KaraokeQueueItem",
        foreign_keys=[current_queue_item_id],
    )
    current_song: Mapped[Optional["DbSong"]] = relationship(
        "DbSong",
        foreign_keys=[current_song_id],
    )

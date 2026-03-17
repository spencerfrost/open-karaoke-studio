"""
HostSettings SQLAlchemy model — per-host session configuration.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class HostSettings(Base):
    """Per-host settings that govern all sessions created by that host."""

    __tablename__ = "host_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Queue behaviour
    queue_submission_mode = Column(String, nullable=False, default="instant")  # "instant" | "approval"
    max_songs_per_singer = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    queue_open = Column(Boolean, nullable=False, default=True)
    session_duration_hours = Column(Integer, nullable=False, default=8)

    user = relationship("User", backref="host_settings", uselist=False)

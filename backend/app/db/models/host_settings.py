"""
HostSettings SQLAlchemy model — per-host session configuration.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import backref, relationship

from .base import Base


class HostSettings(Base):
    """Per-host settings that govern all sessions created by that host."""

    __tablename__ = "host_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Defaults applied to every session this host creates
    session_duration_hours = Column(Float, nullable=False, default=8)

    user = relationship(
        "User",
        backref=backref(
            "host_settings",
            uselist=False,
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

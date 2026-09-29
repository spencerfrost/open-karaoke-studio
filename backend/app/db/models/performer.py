"""
SessionPerformer model - a name-bound roster entry for a karaoke session.

A performer entry can exist with zero devices attached, so a walk-up who never
touches a phone is still a real person the queue can point at, not just a
string. See docs/plans/archive/2026-08-29-roster-and-rotation.md.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .session import KaraokeSession


class SessionPerformer(Base):
    """A person in a session's roster, matched by normalized name."""

    __tablename__ = "session_performers"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "normalized_name", name="uq_session_performer_name"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(4), ForeignKey("karaoke_sessions.session_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # This person's place in the circle - rotation order for the whole night.
    # Fixed once they join; inserting someone at the turn renumbers everyone at
    # or after that seat, inactive rows included, so an undo lands back in place.
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    # Part of the night. Only "Remove from rotation" clears it; their songs are
    # hidden rather than deleted while it is off.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Turns already sung out of order (a bump, or a song played from the rail
    # early). The pointer steps over this person once per borrowed turn - see
    # turn_service.advance_pointer, the only place it is spent.
    turns_borrowed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["KaraokeSession"] = relationship(
        "KaraokeSession", back_populates="performers", foreign_keys=[session_id]
    )

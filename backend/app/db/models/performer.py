"""
SessionPerformer model - a name-bound roster entry for a karaoke session.

A performer entry can exist with zero devices attached, so a walk-up who never
touches a phone is still a real person the queue can point at, not just a
string. See docs/plans/2026-08-29-roster-and-rotation.md.
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
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    laps_taken: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # When this person first queued anything - their place in the circle.
    # Null until they queue: being on the roster (joined, picked, added by the
    # host) does not put you in the rotation, singing does. `seat` is join
    # order and drives roster display; it deliberately does not decide play
    # order, or the host would win every lap tie all night.
    first_queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["KaraokeSession"] = relationship(
        "KaraokeSession", back_populates="performers"
    )

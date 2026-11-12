"""
Break checks - answers given by ear on the admin Compare breaks page.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .base import Base


class BreakCheck(Base):
    """One answer about one moment: was the singing map or today's bar right?

    A moment is identified by its key, built from its exact times (see
    singing_map_review.moment_key). Re-measuring with other settings moves
    the times, so a changed moment gets a new key and needs a fresh listen,
    while unchanged moments keep their answers. The moment and the map's
    settings are stored as they were, for reading the answers back later.
    """

    __tablename__ = "break_checks"
    __table_args__ = (
        UniqueConstraint("song_id", "moment_key", name="uq_break_checks_song_moment"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(
        String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    moment_key = Column(String, nullable=False)
    # "break" or "backing_only".
    kind = Column(String, nullable=False)
    # See singing_map_review.ANSWERS.
    answer = Column(String, nullable=False)
    # JSON: the moment as shown, and the map's params and measured_at.
    moment = Column(Text, nullable=False)
    map_params = Column(Text, nullable=True)
    map_measured_at = Column(String, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

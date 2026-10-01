"""
Lyrics reports - someone singing said a song's lyrics are wrong.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class LyricsReport(Base):
    """A report that a song's lyrics have the wrong words or are out of sync.

    One row per song, kind and lyrics text: reporting the same lyrics again
    bumps `report_count`. "words" reports are also the memory of rejected
    lyrics: alignment never picks a candidate whose words key matches one,
    even after an admin resolves the report.
    """

    __tablename__ = "lyrics_reports"
    __table_args__ = (
        UniqueConstraint(
            "song_id", "kind", "words_key", name="uq_lyrics_reports_song_kind_words"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(
        String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "words": the text is wrong. "timing": the words are right but out of sync.
    kind = Column(String, nullable=False)
    # lyrics_words_key() of the lyrics on screen when reported.
    words_key = Column(String, nullable=False)
    report_count = Column(Integer, nullable=False, default=1)

    # Who reported it last: an account, or a guest in a session.
    reporter_name = Column(String, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id = Column(
        String(4),
        ForeignKey("karaoke_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_reported_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # What the automatic fix did: "replaced", "retimed", "transcribed" or "unchanged".
    outcome = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    song = relationship("DbSong")

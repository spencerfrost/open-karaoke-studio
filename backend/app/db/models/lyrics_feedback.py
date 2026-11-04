"""
Lyrics feedback - how the lyrics went, asked on the stage after each song.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base


class LyricsFeedback(Base):
    """One answer to "How were the lyrics?" for one song as it was sung.

    Unlike a report it starts no fix: it's a record of which songs need work,
    and which are right and must stay right. One row per queue item, so
    changing the answer replaces it. The words key and alignment time say
    which lyrics and which word timings the answer was about; once either
    changes, the answer is about lyrics the song no longer shows.
    """

    __tablename__ = "lyrics_feedback"
    __table_args__ = (
        UniqueConstraint("queue_item_id", name="uq_lyrics_feedback_queue_item"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(
        String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The queue item that was sung. No foreign key: the item is deleted once
    # the next song starts, and the answer outlives it.
    queue_item_id = Column(Integer, nullable=False)
    # "spot_on", "a_bit_off" or "way_off".
    rating = Column(String, nullable=False)
    # lyrics_words_key() of the lyrics on screen, and the `aligned_at` of the
    # word timings on screen (None when the song had no word timing).
    words_key = Column(String, nullable=False)
    word_timing_aligned_at = Column(String, nullable=True)

    singer_name = Column(String, nullable=True)
    # Who answered: an account, or a device in the session.
    answered_by = Column(String, nullable=True)
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
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    song = relationship("DbSong")

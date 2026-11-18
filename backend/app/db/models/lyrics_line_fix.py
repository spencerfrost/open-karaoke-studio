"""
Lyrics line fixes - a person corrected one line of a song's lyrics on the stage.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .song import DbSong


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LyricsLineFix(Base):
    """One line of lyrics a person fixed, kept over whatever the lyrics are later.

    A fix is a layer over the stored lyrics: every job that stores lyrics puts
    the fixed text back on the line it belongs to (see
    services/lyrics_line_fixes.py). The line is found again by its words, its
    neighbours and its place among lines with the same words, so a re-time, a
    new fetch or added break lines don't lose it. One that can't be found is
    listed for an admin, never dropped.
    """

    __tablename__ = "lyrics_line_fixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id: Mapped[str] = mapped_column(
        String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The line as it was before any fix, and what the person typed.
    old_text: Mapped[str] = mapped_column(Text, nullable=False)
    new_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Where the line was when fixed: its LRC time in seconds, the sung lines
    # either side of it (None at the start or end of the song), and which of
    # the lines reading the old or new text it was, counting from 0.
    line_start: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prev_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurrence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # The lyrics version on screen when it was fixed: lyrics_words_key() of
    # the lyrics, and the `aligned_at` of the word timings (None without any).
    words_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    word_timing_aligned_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # The line's words are timed again on their own after a fix:
    # "pending", "aligned", "failed", or "no_timing" (the song has no word
    # timing to patch, no vocals, or a language without word timing).
    align_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    aligned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    fixed_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    song: Mapped["DbSong"] = relationship("DbSong")

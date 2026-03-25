# backend/app/db/models/performance.py
"""
Performance history model - records every song that starts playing.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class PerformanceHistory(Base):
    """Records each karaoke performance (song + singer + session + time)."""

    __tablename__ = "performance_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(
        String,
        ForeignKey("songs.id", ondelete="SET NULL"),
        nullable=True,
    )
    singer_name = Column(String, nullable=False)
    session_id = Column(
        String(4),
        ForeignKey("karaoke_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    song = relationship("DbSong")
    session = relationship("KaraokeSession")

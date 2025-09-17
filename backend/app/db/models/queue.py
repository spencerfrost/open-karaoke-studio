"""
Karaoke queue item SQLAlchemy model.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class KaraokeQueueItem(Base):
    """Model representing an item in the karaoke queue."""

    __tablename__ = "karaoke_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    singer_name = Column(String, nullable=False)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False)
    position = Column(Integer, nullable=False)
    session_id = Column(String(4), ForeignKey("karaoke_sessions.session_id"), nullable=False)
    song = relationship("DbSong", back_populates="queue_items")
    session = relationship("KaraokeSession", back_populates="queue_items")

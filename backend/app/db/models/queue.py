"""
Karaoke queue item SQLAlchemy model.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class KaraokeQueueItem(Base):
    __tablename__ = "karaoke_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    singer_name = Column(String, nullable=False)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False)
    position = Column(Integer, nullable=False)
    song = relationship("DbSong", back_populates="queue_items")

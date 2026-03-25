"""
Lyrics database model - stores lyrics separately from songs with versioning support.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .base import Base


class DbLyrics(Base):
    __tablename__ = "lyrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(
        String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String(10), nullable=False)  # 'plain' or 'synced'
    content = Column(Text, nullable=False)
    source = Column(String(50), nullable=True)  # 'lrclib', 'syncedlyrics', 'manual', 'legacy_migration'
    metadata_ = Column("metadata", JSON, nullable=True)  # Extensible metadata
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    song = relationship("DbSong", back_populates="lyrics")

    __table_args__ = (
        Index("idx_lyrics_song_id", "song_id"),
        Index("idx_lyrics_song_type_active", "song_id", "type", "is_active"),
    )

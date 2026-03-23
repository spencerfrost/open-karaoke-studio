from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class DbSongArtist(Base):
    __tablename__ = "song_artists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False)
    role = Column(String(20), nullable=False, default="primary")  # 'primary' | 'featured'
    display_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("song_id", "artist_id"),
        Index("ix_song_artists_song_id", "song_id"),
        Index("ix_song_artists_artist_id", "artist_id"),
    )

    song_rel = relationship("DbSong", back_populates="song_artists")
    artist_rel = relationship("DbArtist", back_populates="song_artist_links")

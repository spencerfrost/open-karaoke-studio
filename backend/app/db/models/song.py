"""
Song database model - Single source of truth.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import UNKNOWN_ARTIST, Base

SongStatus = Literal["processing", "queued", "processed", "error"]


class DbSong(Base):
    __tablename__ = "songs"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default=UNKNOWN_ARTIST)
    duration = Column(Float, nullable=True)  # Duration in seconds
    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    vocals_path = Column(String, nullable=True)
    instrumental_path = Column(String, nullable=True)
    original_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    
    # Core metadata
    album = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String, nullable=True)
    
    # Lyrics
    plain_lyrics = Column(Text, nullable=True)
    synced_lyrics = Column(Text, nullable=True)

    # iTunes metadata
    itunes_track_id = Column(Integer, nullable=True)
    itunes_explicit = Column(Boolean, nullable=True)
    itunes_preview_url = Column(String, nullable=True)  # 30-sec preview for "what's this song?"
    itunes_artwork_urls = Column(Text, nullable=True)  # JSON array as string

    # YouTube thumbnail URLs (fallback for artwork)
    youtube_thumbnail_urls = Column(Text, nullable=True)  # JSON array as string

    # Processing metadata
    engine_type = Column(String, nullable=True)  # Separation engine used (demucs, roformer, hybrid, clean_backing)

    queue_items = relationship(
        "KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Convert to API response format - replaces to_pydantic()"""
        # Extract year from release_date if available
        year_value = None
        if self.year is not None:
            year_value = self.year
        elif self.release_date is not None:
            try:
                year_value = (
                    int(str(self.release_date).split("-")[0])
                    if "-" in str(self.release_date)
                    else int(str(self.release_date))
                )
            except (ValueError, AttributeError):
                year_value = None

        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,  # Duration in seconds
            "status": "processed",
            "dateAdded": (
                self.date_added.isoformat() if self.date_added is not None else None
            ),
            # File paths for API
            "vocalPath": (
                f"/api/songs/{self.id}/vocal" if self.vocals_path is not None else None
            ),
            "instrumentalPath": (
                f"/api/songs/{self.id}/instrumental"
                if self.instrumental_path is not None
                else None
            ),
            "originalPath": (
                f"/api/songs/{self.id}/original"
                if self.original_path is not None
                else None
            ),
            "thumbnail": self.thumbnail_path,
            # Source info
            "videoId": self.video_id,
            "sourceUrl": self.source_url,
            "source": self.source,
            # Metadata
            "album": self.album,
            "releaseDate": self.release_date,
            "year": year_value,
            "genre": self.genre,
            # Lyrics
            "plainLyrics": self.plain_lyrics,
            "syncedLyrics": self.synced_lyrics,
            # iTunes metadata
            "itunesTrackId": self.itunes_track_id,
            "itunesExplicit": self.itunes_explicit,
            "itunesPreviewUrl": self.itunes_preview_url,
            "itunesArtworkUrls": self.itunes_artwork_urls,
            # YouTube thumbnail URLs (for artwork fallback)
            "youtubeThumbnailUrls": self.youtube_thumbnail_urls,
            # Processing metadata
            "engineType": self.engine_type,
        }

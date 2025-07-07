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
    duration_ms = Column(Integer, nullable=True)
    date_added = Column(DateTime, default=datetime.now(timezone.utc))
    vocals_path = Column(String, nullable=True)
    instrumental_path = Column(String, nullable=True)
    original_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    cover_art_path = Column(String, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    uploader_id = Column(String, nullable=True)
    channel = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)  # Song/video description

    # Phase 1A = Column(Text, nullable=True)
    upload_date = Column(DateTime, nullable=True)
    mbid = Column(String, nullable=True)
    album = Column(String, nullable=True)  # Renamed from release_title for better UX
    release_id = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String, nullable=True)
    language = Column(String, nullable=True)
    lyrics = Column(Text, nullable=True)
    synced_lyrics = Column(Text, nullable=True)
    channel_name = Column(String, nullable=True)  # Legacy field

    # Phase 1B = Column(Integer, nullable=True)
    itunes_artist_id = Column(Integer, nullable=True)
    itunes_collection_id = Column(Integer, nullable=True)
    track_time_millis = Column(Integer, nullable=True)
    itunes_explicit = Column(Boolean, nullable=True)
    itunes_preview_url = Column(String, nullable=True)
    itunes_artwork_urls = Column(Text, nullable=True)  # JSON array as string

    # Phase 1B = Column(Integer, nullable=True)
    youtube_thumbnail_urls = Column(Text, nullable=True)  # JSON array as string
    youtube_tags = Column(Text, nullable=True)  # JSON array as string
    youtube_categories = Column(Text, nullable=True)  # JSON array as string
    youtube_channel_id = Column(String, nullable=True)
    youtube_channel_name = Column(String, nullable=True)

    # Phase 1B = Column(Text, nullable=True)  # JSON string
    youtube_raw_metadata = Column(Text, nullable=True)  # JSON string

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
            "durationMs": self.duration_ms,
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
            "coverArt": self.cover_art_path,
            "thumbnail": self.thumbnail_path,
            # YouTube data (convert to camelCase)
            "videoId": self.video_id,
            "sourceUrl": self.source_url,
            "uploader": self.uploader,
            "uploaderId": self.uploader_id,
            "channel": self.channel,
            "channelId": self.channel_id,
            "channelName": self.youtube_channel_name or self.channel_name,
            "description": self.description,
            "uploadDate": (
                self.upload_date.isoformat() if self.upload_date is not None else None
            ),
            # Metadata
            "mbid": self.mbid,
            "metadataId": self.mbid,  # Alias for frontend compatibility
            "album": self.album,
            "releaseTitle": self.album,  # Legacy alias
            "releaseId": self.release_id,
            "releaseDate": self.release_date,
            "year": year_value,
            "genre": self.genre,
            "language": self.language,
            # Lyrics
            "lyrics": self.lyrics,
            "syncedLyrics": self.synced_lyrics,
            # System
            "source": self.source,
        }

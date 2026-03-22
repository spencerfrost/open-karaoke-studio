"""
Song database model - Single source of truth.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
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
    itunes_preview_url = Column(
        String, nullable=True
    )  # 30-sec preview for "what's this song?"
    itunes_artwork_urls = Column(Text, nullable=True)  # JSON array as string

    # YouTube thumbnail URLs (fallback for artwork)
    youtube_thumbnail_urls = Column(Text, nullable=True)  # JSON array as string

    # Relational links (nullable; backfilled by migration, enriched via iTunes metadata)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)

    # Processing metadata
    engine_type = Column(
        String, nullable=True
    )  # Separation engine used (demucs, roformer, hybrid, clean_backing)
    bpm = Column(Float, nullable=True)  # Beats per minute for count-in timing
    chords_data = Column(JSON, nullable=True)  # Chord detection data
    vocal_range_low = Column(String, nullable=True)   # Lowest sung note, e.g. "G2"
    vocal_range_high = Column(String, nullable=True)  # Highest sung note, e.g. "E5"
    loudness_dbfs = Column(Float, nullable=True)  # RMS loudness in dBFS (e.g. -20.0)
    gain_db = Column(Float, nullable=True)        # Gain correction to reach -14 dBFS target

    # AcoustID fingerprinting
    musicbrainz_recording_id = Column(String, nullable=True)
    acoustid_score = Column(Float, nullable=True)
    acoustid_fingerprint_status = Column(String, nullable=False, default="not_checked")
    # acoustid_fingerprint_status: "not_checked" | "matched" | "no_match" | "failed"

    queue_items = relationship(
        "KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan"
    )
    lyrics = relationship(
        "DbLyrics", back_populates="song", cascade="all, delete-orphan"
    )
    artist_rel = relationship("DbArtist", back_populates="songs")
    album_rel = relationship("DbAlbum", back_populates="songs")

    def _get_active_lyrics_content(self, lyrics_type: str) -> Optional[str]:
        """Get active lyrics content by type, falling back to legacy columns."""
        if self.lyrics:
            for lyric in self.lyrics:
                if lyric.type == lyrics_type and lyric.is_active:
                    return lyric.content
        # Fallback to legacy columns during transition
        if lyrics_type == "plain":
            return self.plain_lyrics
        elif lyrics_type == "synced":
            return self.synced_lyrics
        return None

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
            "backingVocalPath": (
                f"/api/songs/{self.id}/download/backing-vocals"
                if self.engine_type == "three_track"
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
            "plainLyrics": self._get_active_lyrics_content("plain"),
            "syncedLyrics": self._get_active_lyrics_content("synced"),
            # iTunes metadata
            "itunesTrackId": self.itunes_track_id,
            "itunesExplicit": self.itunes_explicit,
            "itunesPreviewUrl": self.itunes_preview_url,
            "itunesArtworkUrls": self.itunes_artwork_urls,
            # YouTube thumbnail URLs (for artwork fallback)
            "youtubeThumbnailUrls": self.youtube_thumbnail_urls,
            # Relational IDs and computed cover URL
            "artistId": self.artist_id,
            "albumId": self.album_id,
            "albumCoverUrl": (
                f"/api/albums/{self.album_id}/cover"
                if self.album_id and self.album_rel and self.album_rel.cover_path
                else None
            ),
            # Processing metadata
            "engineType": self.engine_type,
            "bpm": self.bpm,
            "chordsData": self.chords_data,
            "vocalRangeLow": self.vocal_range_low,
            "vocalRangeHigh": self.vocal_range_high,
            "loudnessDbfs": self.loudness_dbfs,
            "gainDb": self.gain_db,
            # AcoustID fingerprinting
            "musicbrainzRecordingId": self.musicbrainz_recording_id,
            "acoustidScore": self.acoustid_score,
            "acoustidFingerprintStatus": self.acoustid_fingerprint_status,
        }

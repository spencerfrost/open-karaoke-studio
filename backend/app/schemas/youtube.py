"""
Pydantic Schemas for YouTube related requests.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class YouTubeProcessRequest(BaseModel):
    """Schema for YouTube processing requests"""

    url: str = Field(..., description="YouTube URL")
    title: Optional[str] = Field(None, max_length=200, description="Custom title")
    artist: Optional[str] = Field(None, max_length=200, description="Custom artist")

    @field_validator("url")
    def validate_youtube_url(cls, v):
        if not v:
            raise ValueError("URL is required")

        # Basic YouTube URL validation
        youtube_domains = ["youtube.com", "youtu.be", "m.youtube.com"]
        if not any(domain in v.lower() for domain in youtube_domains):
            raise ValueError("Must be a valid YouTube URL")

        return v


class YouTubeDownloadRequest(BaseModel):
    """Schema for YouTube download requests"""

    video_id: str = Field(
        ..., min_length=1, max_length=100, description="YouTube video ID"
    )
    song_id: str = Field(
        ..., min_length=1, max_length=100, description="Song ID to associate with"
    )
    title: Optional[str] = Field(
        None, max_length=200, description="Custom title override"
    )
    artist: Optional[str] = Field(
        None, max_length=200, description="Custom artist override"
    )
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    searchThumbnailUrl: Optional[str] = Field(
        None, max_length=500, description="Original search result thumbnail URL"
    )

    @field_validator("video_id", "song_id")
    def validate_required_ids(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("title", "artist", "album")
    def validate_optional_strings(cls, v):
        # Convert empty strings to None for optional fields
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if stripped == "":
                return None
            return stripped
        return v


class SongFromYouTubeRequest(BaseModel):
    """Add a YouTube song to the library and queue its processing, in one go."""

    video_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    # Every credited artist, primary first
    artists: list[str] = Field(..., min_length=1, max_length=10)
    album: Optional[str] = Field(None, max_length=200)
    duration: Optional[float] = Field(None, ge=0, description="Length in seconds")
    source: Literal["youtube_music", "youtube"] = "youtube_music"

    @field_validator("video_id", "title")
    @classmethod
    def strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v

    @field_validator("artists")
    @classmethod
    def strip_artists(cls, v: list[str]) -> list[str]:
        names = [name.strip() for name in v if name and name.strip()]
        if not names:
            raise ValueError("At least one artist is required")
        if any(len(name) > 200 for name in names):
            raise ValueError("Artist names are at most 200 characters")
        return names

    @field_validator("album")
    @classmethod
    def strip_album(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() or None if v else None


class SongFromYouTubeResponse(BaseModel):
    songId: str
    jobId: str
    # True when this restarted the song's failed copy instead of adding one
    restarted: bool

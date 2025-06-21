"""
Request validation schemas for the karaoke application.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator


class CreateSongRequest(BaseModel):
    """Schema for creating a new song"""

    title: str = Field(..., min_length=1, max_length=200, description="Song title")
    artist: str = Field(..., min_length=1, max_length=200, description="Artist name")
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    duration: Optional[float] = Field(
        None, ge=0, description="Song duration in seconds"
    )
    source: Optional[str] = Field(None, max_length=50, description="Source of the song")
    video_id: Optional[str] = Field(
        None, max_length=100, description="YouTube video ID"
    )

    @validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class UpdateSongRequest(BaseModel):
    """Schema for updating an existing song"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    artist: Optional[str] = Field(None, min_length=1, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    duration: Optional[float] = Field(None, ge=0)
    favorite: Optional[bool] = Field(None)

    @validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v


class YouTubeProcessRequest(BaseModel):
    """Schema for YouTube processing requests"""

    url: str = Field(..., description="YouTube URL")
    title: Optional[str] = Field(None, max_length=200, description="Custom title")
    artist: Optional[str] = Field(None, max_length=200, description="Custom artist")

    @validator("url")
    def validate_youtube_url(cls, v):
        if not v:
            raise ValueError("URL is required")

        # Basic YouTube URL validation
        youtube_domains = ["youtube.com", "youtu.be", "m.youtube.com"]
        if not any(domain in v.lower() for domain in youtube_domains):
            raise ValueError("Must be a valid YouTube URL")

        return v


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete operations"""

    song_ids: List[str] = Field(
        ..., min_items=1, description="List of song IDs to delete"
    )

    @validator("song_ids")
    def validate_song_ids(cls, v):
        if not v:
            raise ValueError("At least one song ID is required")

        # Validate each ID is not empty
        for song_id in v:
            if not song_id or song_id.strip() == "":
                raise ValueError("Song IDs cannot be empty")

        return v


class LyricsSearchRequest(BaseModel):
    """Schema for lyrics search requests"""

    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=200)

    @validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class MetadataUpdateRequest(BaseModel):
    """Schema for metadata update requests"""

    title: Optional[str] = Field(None, max_length=200)
    artist: Optional[str] = Field(None, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    year: Optional[int] = Field(None, ge=1800, le=2100)
    genre: Optional[str] = Field(None, max_length=100)

    @validator("title", "artist", "album", "genre")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v


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

    @validator("video_id", "song_id")
    def validate_required_ids(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

    @validator("title", "artist", "album")
    def validate_optional_strings(cls, v):
        # Convert empty strings to None for optional fields
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if stripped == "":
                return None
            return stripped
        return v


class SaveLyricsRequest(BaseModel):
    """Schema for saving song lyrics"""

    lyrics: str = Field(..., min_length=1, max_length=50000, description="Lyrics text")

    @validator("lyrics")
    def validate_lyrics_content(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Lyrics cannot be empty")
        # Remove excessive whitespace but preserve line breaks
        return v.strip()

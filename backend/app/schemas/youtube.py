"""
Pydantic Schemas for YouTube related requests.
"""

from typing import Optional

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

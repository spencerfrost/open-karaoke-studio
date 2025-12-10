"""
Pydantic Schemas for Lyrics related requests.
"""

from pydantic import BaseModel, Field, field_validator


class LyricsSearchRequest(BaseModel):
    """Schema for lyrics search requests"""

    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=200)

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class SaveLyricsRequest(BaseModel):
    """Schema for saving song lyrics"""

    lyrics: str = Field(..., min_length=1, max_length=50000, description="Lyrics text")

    @field_validator("lyrics")
    def validate_lyrics_content(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Lyrics cannot be empty")
        # Remove excessive whitespace but preserve line breaks
        return v.strip()

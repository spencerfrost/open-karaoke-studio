"""
Pydantic Schemas for Metadata related requests.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MetadataUpdateRequest(BaseModel):
    """Schema for metadata update requests"""

    title: Optional[str] = Field(None, max_length=200)
    artist: Optional[str] = Field(None, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    year: Optional[int] = Field(None, ge=1800, le=2100)
    genre: Optional[str] = Field(None, max_length=100)

    @field_validator("title", "artist", "album", "genre")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v

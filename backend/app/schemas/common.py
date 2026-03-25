"""
Pydantic Schemas for common or generic requests.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete operations"""

    song_ids: List[str] = Field(..., description="List of song IDs to delete")

    @field_validator("song_ids")
    def validate_song_ids(cls, v):
        if not v:
            raise ValueError("At least one song ID is required")

        # Validate each ID is not empty
        for song_id in v:
            if not song_id or song_id.strip() == "":
                raise ValueError("Song IDs cannot be empty")

        return v

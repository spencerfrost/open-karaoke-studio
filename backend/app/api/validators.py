"""Shared validation utilities for API endpoints"""
from typing import Literal
from fastapi import HTTPException

# Field mapping constants
CAMEL_TO_SNAKE_CASE = {
    "syncedLyrics": "synced_lyrics",
    "plainLyrics": "plain_lyrics",
    "releaseDate": "release_date",
    "itunesTrackId": "itunes_track_id",
    "itunesArtworkUrls": "itunes_artwork_urls",
    "itunesExplicit": "itunes_explicit",
    "itunesPreviewUrl": "itunes_preview_url",
    "dateAdded": "date_added",
}

VALID_SONG_SORT_FIELDS = {"date_added", "title", "artist", "album", "year"}
VALID_ARTIST_SORT_FIELDS = {"title", "album", "year", "dateAdded", "date_added"}


def validate_sort_field(
    field: str, valid_fields: set[str], default: str = "date_added"
) -> str:
    """Validate and normalize sort field"""
    return field if field in valid_fields else default


def validate_direction(
    direction: str, raise_on_invalid: bool = False
) -> Literal["asc", "desc"]:
    """Validate sort direction"""
    normalized = direction.lower()
    if normalized not in ["asc", "desc"]:
        if raise_on_invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
            )
        return "desc"
    return normalized


LYRICS_FIELDS = {"plainLyrics", "syncedLyrics"}


def extract_lyrics_fields(data: dict) -> dict:
    """Extract lyrics fields from update data, returning them separately.
    Modifies data in place by removing lyrics fields."""
    lyrics = {}
    for key in list(data.keys()):
        if key in LYRICS_FIELDS:
            lyrics[key] = data.pop(key)
    return lyrics


def map_fields_to_db(data: dict) -> dict:
    """Convert camelCase fields to snake_case for database"""
    result = {}
    for key, value in data.items():
        if value is not None:
            db_field = CAMEL_TO_SNAKE_CASE.get(key, key)
            # Serialize lists for TEXT columns
            if db_field == "itunes_artwork_urls" and isinstance(value, list):
                import json

                result[db_field] = json.dumps(value)
            else:
                result[db_field] = value
    return result

import pytest
from fastapi import HTTPException
from app.api.validators import (
    validate_sort_field,
    validate_direction,
    map_fields_to_db,
    VALID_SONG_SORT_FIELDS,
)


def test_validate_sort_field_valid():
    assert validate_sort_field("title", VALID_SONG_SORT_FIELDS) == "title"


def test_validate_sort_field_invalid_returns_default():
    assert validate_sort_field("invalid", VALID_SONG_SORT_FIELDS) == "date_added"


def test_validate_sort_field_custom_default():
    assert (
        validate_sort_field("invalid", VALID_SONG_SORT_FIELDS, default="title")
        == "title"
    )


def test_validate_direction_valid_asc():
    assert validate_direction("asc") == "asc"


def test_validate_direction_valid_desc():
    assert validate_direction("DESC") == "desc"


def test_validate_direction_invalid_returns_default():
    assert validate_direction("invalid") == "desc"


def test_validate_direction_raises_on_invalid():
    with pytest.raises(HTTPException) as exc:
        validate_direction("invalid", raise_on_invalid=True)
    assert exc.value.status_code == 400
    assert "Invalid sort direction" in exc.value.detail


def test_map_fields_to_db():
    data = {
        "syncedLyrics": "lyrics content",
        "plainLyrics": "plain lyrics",
        "title": "Song Title",
        "itunesArtworkUrls": ["url1", "url2"],
    }
    result = map_fields_to_db(data)
    assert result["synced_lyrics"] == "lyrics content"
    assert result["plain_lyrics"] == "plain lyrics"
    assert result["title"] == "Song Title"
    assert '"url1"' in result["itunes_artwork_urls"]  # JSON serialized
    assert '"url2"' in result["itunes_artwork_urls"]


def test_map_fields_to_db_ignores_none_values():
    data = {
        "title": "Song Title",
        "artist": None,
    }
    result = map_fields_to_db(data)
    assert "title" in result
    assert "artist" not in result


def test_map_fields_to_db_preserves_unknown_fields():
    data = {
        "customField": "custom value",
    }
    result = map_fields_to_db(data)
    assert result["customField"] == "custom value"

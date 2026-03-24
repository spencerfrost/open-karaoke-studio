import pytest
from pydantic import ValidationError

from app.schemas.metadata import MetadataUpdateRequest


def test_all_fields_valid():
    req = MetadataUpdateRequest(title="Song Title", artist="Artist", album="Album", year=2020)
    assert req.title == "Song Title"
    assert req.year == 2020


def test_all_fields_none():
    req = MetadataUpdateRequest()
    assert req.title is None
    assert req.artist is None
    assert req.year is None


def test_strings_stripped():
    req = MetadataUpdateRequest(title="  Hello  ", artist=" World ")
    assert req.title == "Hello"
    assert req.artist == "World"


def test_title_too_long_raises():
    with pytest.raises(ValidationError):
        MetadataUpdateRequest(title="x" * 201)


def test_artist_too_long_raises():
    with pytest.raises(ValidationError):
        MetadataUpdateRequest(artist="x" * 201)


def test_album_too_long_raises():
    with pytest.raises(ValidationError):
        MetadataUpdateRequest(album="x" * 201)



def test_year_below_minimum_raises():
    with pytest.raises(ValidationError):
        MetadataUpdateRequest(year=1799)


def test_year_above_maximum_raises():
    with pytest.raises(ValidationError):
        MetadataUpdateRequest(year=2101)


def test_year_at_boundaries():
    assert MetadataUpdateRequest(year=1800).year == 1800
    assert MetadataUpdateRequest(year=2100).year == 2100


def test_empty_string_title_raises():
    with pytest.raises(ValidationError) as exc_info:
        MetadataUpdateRequest(title="")
    assert "Field cannot be empty" in str(exc_info.value)


def test_whitespace_only_title_raises():
    with pytest.raises(ValidationError) as exc_info:
        MetadataUpdateRequest(title="   ")
    assert "Field cannot be empty" in str(exc_info.value)

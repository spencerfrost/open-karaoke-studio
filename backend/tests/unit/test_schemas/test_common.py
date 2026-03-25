import pytest
from pydantic import ValidationError

from app.schemas.common import BulkDeleteRequest


def test_valid_single_id():
    req = BulkDeleteRequest(song_ids=["abc123"])
    assert req.song_ids == ["abc123"]


def test_valid_multiple_ids():
    req = BulkDeleteRequest(song_ids=["id1", "id2", "id3"])
    assert len(req.song_ids) == 3


def test_empty_list_raises():
    with pytest.raises(ValidationError) as exc_info:
        BulkDeleteRequest(song_ids=[])
    assert "At least one song ID is required" in str(exc_info.value)


def test_empty_string_id_raises():
    with pytest.raises(ValidationError) as exc_info:
        BulkDeleteRequest(song_ids=[""])
    assert "Song IDs cannot be empty" in str(exc_info.value)


def test_whitespace_only_id_raises():
    with pytest.raises(ValidationError) as exc_info:
        BulkDeleteRequest(song_ids=["   "])
    assert "Song IDs cannot be empty" in str(exc_info.value)


def test_mixed_valid_and_empty_raises():
    with pytest.raises(ValidationError):
        BulkDeleteRequest(song_ids=["valid-id", ""])

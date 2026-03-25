"""Unit tests for app/schemas/song.py."""
import pytest
from pydantic import ValidationError

from app.schemas.song import SongCreateRequest, SongReprocessRequest, SongReplaceYouTubeRequest, SongUpdateRequest


class TestSongCreateRequest:
    def test_valid_request(self):
        req = SongCreateRequest(title="My Song", artist="Artist Name")
        assert req.title == "My Song"
        assert req.artist == "Artist Name"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            SongCreateRequest(title="", artist="Artist")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            SongCreateRequest(title="   ", artist="Artist")

    def test_empty_artist_raises(self):
        with pytest.raises(ValidationError):
            SongCreateRequest(title="Song", artist="")


class TestSongUpdateRequest:
    def test_all_fields_none(self):
        req = SongUpdateRequest()
        assert req.title is None

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            SongUpdateRequest(title="   ")

    def test_empty_artist_raises(self):
        with pytest.raises(ValidationError):
            SongUpdateRequest(artist="")

    def test_valid_partial_update(self):
        req = SongUpdateRequest(title="New Title")
        assert req.title == "New Title"


class TestSongReprocessRequest:
    def test_valid_engine(self):
        req = SongReprocessRequest(engine_type="demucs")
        assert req.engine_type == "demucs"

    def test_invalid_engine_raises(self):
        with pytest.raises(ValidationError):
            SongReprocessRequest(engine_type="invalid_engine")

    def test_default_engine(self):
        req = SongReprocessRequest()
        assert req.engine_type == "three_track"


class TestSongReplaceYouTubeRequest:
    def test_minimal_valid_request(self):
        req = SongReplaceYouTubeRequest(video_id="abc123")
        assert req.video_id == "abc123"
        assert req.engine_type == "three_track"
        assert req.title is None
        assert req.artist is None

    def test_full_valid_request(self):
        req = SongReplaceYouTubeRequest(
            video_id="abc123", title="My Song", artist="Artist", engine_type="demucs"
        )
        assert req.engine_type == "demucs"
        assert req.title == "My Song"

    def test_invalid_engine_type_raises(self):
        with pytest.raises(ValidationError):
            SongReplaceYouTubeRequest(video_id="abc", engine_type="invalid")

    def test_video_id_too_long_raises(self):
        with pytest.raises(ValidationError):
            SongReplaceYouTubeRequest(video_id="x" * 101)

    def test_empty_video_id_raises(self):
        with pytest.raises(ValidationError):
            SongReplaceYouTubeRequest(video_id="")

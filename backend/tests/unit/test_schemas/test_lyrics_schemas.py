"""Unit tests for app/schemas/lyrics.py."""
import pytest
from pydantic import ValidationError

from app.schemas.lyrics import LyricsSearchRequest, SaveLyricsRequest


class TestLyricsSearchRequest:
    def test_valid_request(self):
        req = LyricsSearchRequest(title="Bohemian Rhapsody", artist="Queen")
        assert req.title == "Bohemian Rhapsody"
        assert req.artist == "Queen"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            LyricsSearchRequest(title="", artist="Queen")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            LyricsSearchRequest(title="   ", artist="Queen")

    def test_empty_artist_raises(self):
        with pytest.raises(ValidationError):
            LyricsSearchRequest(title="Song", artist="")

    def test_strips_whitespace(self):
        req = LyricsSearchRequest(title="  My Song  ", artist="  Artist  ")
        assert req.title == "My Song"
        assert req.artist == "Artist"


class TestSaveLyricsRequest:
    def test_valid_lyrics(self):
        req = SaveLyricsRequest(lyrics="Hello world\nLine 2")
        assert "Hello" in req.lyrics

    def test_empty_lyrics_raises(self):
        with pytest.raises(ValidationError):
            SaveLyricsRequest(lyrics="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            SaveLyricsRequest(lyrics="   ")

    def test_strips_outer_whitespace(self):
        req = SaveLyricsRequest(lyrics="  Hello  ")
        assert req.lyrics == "Hello"

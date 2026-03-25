import pytest
from pydantic import ValidationError

from app.schemas.youtube import YouTubeDownloadRequest, YouTubeProcessRequest


class TestYouTubeProcessRequest:
    def test_valid_youtube_com_url(self):
        req = YouTubeProcessRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert "youtube.com" in req.url

    def test_valid_youtu_be_url(self):
        req = YouTubeProcessRequest(url="https://youtu.be/dQw4w9WgXcQ")
        assert req.url == "https://youtu.be/dQw4w9WgXcQ"

    def test_valid_m_youtube_url(self):
        req = YouTubeProcessRequest(url="https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert "m.youtube.com" in req.url

    def test_non_youtube_url_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            YouTubeProcessRequest(url="https://vimeo.com/123456")
        assert "valid YouTube URL" in str(exc_info.value)

    def test_empty_url_raises(self):
        with pytest.raises(ValidationError):
            YouTubeProcessRequest(url="")

    def test_optional_title_and_artist(self):
        req = YouTubeProcessRequest(
            url="https://youtube.com/watch?v=abc",
            title="Custom Title",
            artist="Custom Artist",
        )
        assert req.title == "Custom Title"
        assert req.artist == "Custom Artist"

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            YouTubeProcessRequest(url="https://youtube.com/watch?v=abc", title="x" * 201)

    def test_artist_too_long_raises(self):
        with pytest.raises(ValidationError):
            YouTubeProcessRequest(url="https://youtube.com/watch?v=abc", artist="x" * 201)


class TestYouTubeDownloadRequest:
    def test_valid_request(self):
        req = YouTubeDownloadRequest(video_id="dQw4w9WgXcQ", song_id="song-123")
        assert req.video_id == "dQw4w9WgXcQ"
        assert req.song_id == "song-123"

    def test_video_id_too_long_raises(self):
        with pytest.raises(ValidationError):
            YouTubeDownloadRequest(video_id="x" * 101, song_id="song-123")

    def test_song_id_too_long_raises(self):
        with pytest.raises(ValidationError):
            YouTubeDownloadRequest(video_id="vid123", song_id="x" * 101)

    def test_whitespace_video_id_raises(self):
        with pytest.raises(ValidationError):
            YouTubeDownloadRequest(video_id="   ", song_id="song-123")

    def test_empty_optional_string_becomes_none(self):
        req = YouTubeDownloadRequest(video_id="vid123", song_id="song-123", title="", artist="")
        assert req.title is None
        assert req.artist is None

    def test_whitespace_optional_string_becomes_none(self):
        req = YouTubeDownloadRequest(video_id="vid123", song_id="song-123", title="   ")
        assert req.title is None

    def test_optional_fields_with_values(self):
        req = YouTubeDownloadRequest(
            video_id="vid123",
            song_id="song-123",
            title="My Song",
            artist="My Artist",
            album="My Album",
            searchThumbnailUrl="https://example.com/thumb.jpg",
        )
        assert req.title == "My Song"
        assert req.album == "My Album"

    def test_thumbnail_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            YouTubeDownloadRequest(
                video_id="vid123",
                song_id="song-123",
                searchThumbnailUrl="https://example.com/" + "x" * 490,
            )

    def test_ids_stripped_of_whitespace(self):
        req = YouTubeDownloadRequest(video_id="  vid123  ", song_id="  song-123  ")
        assert req.video_id == "vid123"
        assert req.song_id == "song-123"

    def test_none_optional_field_remains_none(self):
        """Validator returns v (line 63) when v is None."""
        req = YouTubeDownloadRequest(video_id="vid123", song_id="song-123", title=None)
        assert req.title is None

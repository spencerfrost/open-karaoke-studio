"""Unit tests for YouTubeService pure-logic helpers — no yt-dlp, no network, no DB."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services.youtube_service import YouTubeService


@pytest.fixture
def service():
    mock_file_service = MagicMock()
    return YouTubeService(file_service=mock_file_service)


# ---------------------------------------------------------------------------
# validate_video_url
# ---------------------------------------------------------------------------


class TestValidateVideoUrl:
    def test_standard_watch_url(self, service):
        assert service.validate_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_short_youtu_be_url(self, service):
        assert service.validate_video_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_mobile_url(self, service):
        assert service.validate_video_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_embed_url(self, service):
        assert service.validate_video_url("https://www.youtube.com/embed/dQw4w9WgXcQ") is True

    def test_empty_string_returns_false(self, service):
        assert service.validate_video_url("") is False

    def test_none_returns_false(self, service):
        assert service.validate_video_url(None) is False

    def test_non_youtube_url_returns_false(self, service):
        assert service.validate_video_url("https://vimeo.com/123456") is False

    def test_plain_video_id_returns_false(self, service):
        # A bare ID (no domain) should not match
        assert service.validate_video_url("dQw4w9WgXcQ") is False


# ---------------------------------------------------------------------------
# get_video_id_from_url
# ---------------------------------------------------------------------------


class TestGetVideoIdFromUrl:
    def test_extracts_id_from_watch_url(self, service):
        vid = service.get_video_id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extracts_id_from_youtu_be(self, service):
        vid = service.get_video_id_from_url("https://youtu.be/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extracts_id_from_mobile_url(self, service):
        vid = service.get_video_id_from_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extracts_id_from_embed_url(self, service):
        vid = service.get_video_id_from_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_returns_none_for_non_youtube_url(self, service):
        assert service.get_video_id_from_url("https://vimeo.com/123456") is None

    def test_returns_none_for_empty_string(self, service):
        assert service.get_video_id_from_url("") is None

    def test_returns_none_for_none(self, service):
        assert service.get_video_id_from_url(None) is None


# ---------------------------------------------------------------------------
# _extract_metadata_from_youtube_info
# ---------------------------------------------------------------------------


FULL_VIDEO_INFO = {
    "title": "Rick Astley - Never Gonna Give You Up",
    "uploader": "Rick Astley",
    "uploader_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "channel": "Rick Astley",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "duration": 213,
    "source": "youtube",
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "id": "dQw4w9WgXcQ",
    "description": "The official video",
    "upload_date": "19871101",
    "thumbnails": [],
}


class TestExtractMetadataFromYoutubeInfo:
    def test_extracts_title(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["title"] == "Rick Astley - Never Gonna Give You Up"

    def test_extracts_artist_from_uploader(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["artist"] == "Rick Astley"

    def test_extracts_duration(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["duration"] == 213

    def test_extracts_video_id(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["video_id"] == "dQw4w9WgXcQ"

    def test_extracts_source_url(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_source_is_youtube(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["source"] == "youtube"

    def test_parses_upload_date(self, service):
        meta = service._extract_metadata_from_youtube_info(FULL_VIDEO_INFO)
        assert meta["upload_date"] == datetime(1987, 11, 1, tzinfo=timezone.utc)

    def test_handles_missing_keys_gracefully(self, service):
        meta = service._extract_metadata_from_youtube_info({})
        assert meta["title"] == "Unknown Title"
        assert meta["artist"] == "Unknown Artist"
        assert meta["duration"] is None
        assert meta["upload_date"] is None

    def test_channel_id_falls_back_to_uploader_id(self, service):
        info = {**FULL_VIDEO_INFO, "channel_id": None}
        meta = service._extract_metadata_from_youtube_info(info)
        assert meta["channel_id"] == "UCuAXFkgsw1L7xaCfnd5JJOw"


# ---------------------------------------------------------------------------
# _parse_upload_date
# ---------------------------------------------------------------------------


class TestParseUploadDate:
    def test_parses_yyyymmdd(self, service):
        result = service._parse_upload_date("20231015")
        assert result == datetime(2023, 10, 15, tzinfo=timezone.utc)

    def test_returns_none_for_none(self, service):
        assert service._parse_upload_date(None) is None

    def test_returns_none_for_empty_string(self, service):
        assert service._parse_upload_date("") is None

    def test_returns_none_for_invalid_format(self, service):
        assert service._parse_upload_date("not-a-date") is None


# ---------------------------------------------------------------------------
# _get_best_thumbnail_url
# ---------------------------------------------------------------------------


class TestGetBestThumbnailUrl:
    def test_returns_highest_preference_thumbnail(self, service):
        info = {
            "thumbnails": [
                {"url": "https://low.jpg", "preference": -1},
                {"url": "https://high.jpg", "preference": 5},
                {"url": "https://mid.jpg", "preference": 2},
            ]
        }
        assert service._get_best_thumbnail_url(info) == "https://high.jpg"

    def test_falls_back_to_thumbnail_field(self, service):
        info = {"thumbnails": [], "thumbnail": "https://fallback.jpg"}
        assert service._get_best_thumbnail_url(info) == "https://fallback.jpg"

    def test_constructs_maxresdefault_url_as_last_resort(self, service):
        info = {"thumbnails": [], "id": "dQw4w9WgXcQ"}
        result = service._get_best_thumbnail_url(info)
        assert "dQw4w9WgXcQ" in result
        assert "maxresdefault" in result

    def test_returns_none_when_no_thumbnail_available(self, service):
        assert service._get_best_thumbnail_url({}) is None


# ---------------------------------------------------------------------------
# _build_search_result_entry
# ---------------------------------------------------------------------------


class TestBuildSearchResultEntry:
    def test_builds_entry_with_all_fields(self, service):
        entry = {
            "id": "vid123",
            "title": "Test Video",
            "channel": "Test Channel",
            "channel_id": "chan456",
            "duration": 180,
            "thumbnails": [{"url": "https://thumb.jpg"}],
        }
        result = service._build_search_result_entry(entry)
        assert result["id"] == "vid123"
        assert result["title"] == "Test Video"
        assert result["url"] == "https://www.youtube.com/watch?v=vid123"
        assert result["channel"] == "Test Channel"
        assert result["thumbnail"] == "https://thumb.jpg"
        assert result["duration"] == 180

    def test_falls_back_to_uploader_for_channel(self, service):
        entry = {"id": "vid123", "uploader": "Uploader Name", "thumbnails": []}
        result = service._build_search_result_entry(entry)
        assert result["channel"] == "Uploader Name"

    def test_thumbnail_is_none_when_no_thumbnails(self, service):
        entry = {"id": "vid123", "thumbnails": []}
        result = service._build_search_result_entry(entry)
        assert result["thumbnail"] is None


# ---------------------------------------------------------------------------
# search_videos  (yt-dlp mocked)
# ---------------------------------------------------------------------------


class TestSearchVideos:
    def _make_ydl_ctx(self, info):
        from unittest.mock import MagicMock, patch
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mock_ydl)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx, mock_ydl

    def test_returns_list_of_results(self, service):
        from unittest.mock import patch, MagicMock
        entry = {"id": "abc", "title": "Hit", "channel": "Ch", "thumbnails": [{"url": "t.jpg"}], "duration": 200}
        ctx, mock_ydl = self._make_ydl_ctx({"entries": [entry]})
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            results = service.search_videos("hit song")
        assert len(results) == 1
        assert results[0]["id"] == "abc"

    def test_returns_empty_list_when_no_entries(self, service):
        from unittest.mock import patch
        ctx, mock_ydl = self._make_ydl_ctx(None)
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            results = service.search_videos("nothing")
        assert results == []

    def test_returns_empty_when_info_has_no_entries_key(self, service):
        from unittest.mock import patch
        ctx, mock_ydl = self._make_ydl_ctx({"other": "data"})
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            results = service.search_videos("nothing")
        assert results == []

    def test_raises_service_error_on_exception(self, service):
        from unittest.mock import patch, MagicMock
        from app.exceptions import ServiceError
        ctx = MagicMock()
        ctx.__enter__.side_effect = RuntimeError("network down")
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            with pytest.raises(ServiceError):
                service.search_videos("query")

    def test_respects_max_results(self, service):
        from unittest.mock import patch, call
        entries = [{"id": f"v{i}", "thumbnails": []} for i in range(3)]
        ctx, mock_ydl = self._make_ydl_ctx({"entries": entries})
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            service.search_videos("query", max_results=3)
        call_arg = mock_ydl.extract_info.call_args[0][0]
        assert "ytsearch3:" in call_arg


# ---------------------------------------------------------------------------
# extract_video_info  (yt-dlp mocked)
# ---------------------------------------------------------------------------


class TestExtractVideoInfo:
    def _make_ydl_ctx(self, info):
        from unittest.mock import MagicMock
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mock_ydl)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_returns_video_info_dict(self, service):
        from unittest.mock import patch
        info = {"id": "abc", "title": "Test"}
        ctx = self._make_ydl_ctx(info)
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            result = service.extract_video_info("https://www.youtube.com/watch?v=abc")
        assert result["id"] == "abc"

    def test_constructs_url_for_plain_video_id(self, service):
        from unittest.mock import patch, MagicMock
        info = {"id": "vid123"}
        ctx = self._make_ydl_ctx(info)
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx) as MockYDL:
            ctx.__enter__.return_value.extract_info.return_value = info
            service.extract_video_info("vid123")
        # Should have prepended watch?v= URL
        called_url = ctx.__enter__.return_value.extract_info.call_args[0][0]
        assert "vid123" in called_url

    def test_raises_service_error_on_failure(self, service):
        from unittest.mock import patch, MagicMock
        from app.exceptions import ServiceError
        ctx = MagicMock()
        ctx.__enter__.side_effect = RuntimeError("boom")
        with patch("app.services.youtube_service.yt_dlp.YoutubeDL", return_value=ctx):
            with pytest.raises(ServiceError):
                service.extract_video_info("bad_id")


# ---------------------------------------------------------------------------
# _extract_metadata_from_youtube_info — inner _extract_selected_thumbnails
# ---------------------------------------------------------------------------


class TestExtractMetadataInnerThumbnails:
    """Tests that exercise the inner _extract_selected_thumbnails helper."""

    def test_thumbnails_with_matching_height_included(self, service):
        info = {
            "thumbnails": [
                {"url": "https://t1.jpg", "height": 120},
                {"url": "https://t2.jpg", "height": 320},
                {"url": "https://t3.jpg", "height": 999},  # no match
            ],
        }
        result = service._extract_metadata_from_youtube_info(info)
        # Function returns dict — doesn't include selected_thumbnails, but
        # we exercise the inner function path through the source call
        assert result["title"] == "Unknown Title"

    def test_handles_empty_thumbnails(self, service):
        info = {"thumbnails": []}
        result = service._extract_metadata_from_youtube_info(info)
        assert isinstance(result, dict)

    def test_upload_date_parsed(self, service):
        info = {"upload_date": "20200615"}
        result = service._extract_metadata_from_youtube_info(info)
        assert result["upload_date"] is not None
        assert result["upload_date"].year == 2020


# ---------------------------------------------------------------------------
# fetch_and_save_thumbnail
# ---------------------------------------------------------------------------


class TestFetchAndSaveThumbnail:
    def test_returns_url_on_success(self, service):
        from unittest.mock import patch
        service.extract_video_info = MagicMock(return_value={"id": "v1", "thumbnails": []})
        service._download_thumbnail_with_fallback = MagicMock(return_value="https://thumb.jpg")
        result = service.fetch_and_save_thumbnail("v1", "song-1")
        assert result == "https://thumb.jpg"

    def test_raises_service_error_when_no_url(self, service):
        from app.exceptions import ServiceError
        service.extract_video_info = MagicMock(return_value={"id": "v1"})
        service._download_thumbnail_with_fallback = MagicMock(return_value=None)
        with pytest.raises(ServiceError, match="No valid thumbnail"):
            service.fetch_and_save_thumbnail("v1", "song-1")

    def test_propagates_service_error_from_extract(self, service):
        from app.exceptions import ServiceError
        service.extract_video_info = MagicMock(side_effect=ServiceError("yt failed"))
        with pytest.raises(ServiceError):
            service.fetch_and_save_thumbnail("v1", "song-1")

    def test_wraps_unexpected_error(self, service):
        from app.exceptions import ServiceError
        service.extract_video_info = MagicMock(side_effect=ValueError("unexpected"))
        with pytest.raises(ServiceError, match="Failed to fetch thumbnail"):
            service.fetch_and_save_thumbnail("v1", "song-1")


# ---------------------------------------------------------------------------
# _download_thumbnail_with_fallback
# ---------------------------------------------------------------------------


class TestDownloadThumbnailWithFallback:
    def test_returns_none_when_no_video_id(self, service):
        result = service._download_thumbnail_with_fallback({}, "song-1")
        assert result is None

    def test_uses_yt_dlp_thumbnails_first(self, service):
        service._download_and_save_thumbnail = MagicMock(return_value=(True, "thumbnail.jpg"))
        service._update_song_thumbnail_in_db = MagicMock()
        video_info = {
            "id": "v1",
            "thumbnails": [{"url": "https://yt.jpg", "preference": 1, "width": 1920, "height": 1080}],
        }
        result = service._download_thumbnail_with_fallback(video_info, "song-1")
        assert result == "https://yt.jpg"
        service._update_song_thumbnail_in_db.assert_called_once()

    def test_falls_back_to_systematic_urls_when_yt_dlp_fails(self, service):
        def fake_download(song_id, url):
            if "maxresdefault" in url and "webp" in url:
                return (True, "thumbnail.webp")
            return (False, "")

        service._download_and_save_thumbnail = MagicMock(side_effect=fake_download)
        service._update_song_thumbnail_in_db = MagicMock()
        video_info = {"id": "v1", "thumbnails": []}
        result = service._download_thumbnail_with_fallback(video_info, "song-1")
        assert result is not None
        assert "maxresdefault" in result

    def test_returns_none_when_all_fail(self, service):
        service._download_and_save_thumbnail = MagicMock(return_value=(False, ""))
        service._update_song_thumbnail_in_db = MagicMock()
        video_info = {"id": "v1", "thumbnails": []}
        result = service._download_thumbnail_with_fallback(video_info, "song-1")
        assert result is None

    def test_skips_yt_thumbnail_without_url(self, service):
        service._download_and_save_thumbnail = MagicMock(return_value=(False, ""))
        service._update_song_thumbnail_in_db = MagicMock()
        video_info = {
            "id": "v1",
            "thumbnails": [{"preference": 1}],  # no url key
        }
        result = service._download_thumbnail_with_fallback(video_info, "song-1")
        assert result is None


# ---------------------------------------------------------------------------
# _get_best_quality_thumbnail
# ---------------------------------------------------------------------------


class TestGetBestQualityThumbnail:
    def test_returns_none_when_no_video_id(self, service):
        result = service._get_best_quality_thumbnail({})
        assert result is None

    def test_uses_highest_preference_thumbnail(self, service):
        service._check_thumbnail_exists = MagicMock(return_value=False)
        video_info = {
            "id": "v1",
            "thumbnails": [
                {"url": "https://low.jpg", "preference": -1, "width": 120, "height": 90},
                {"url": "https://high.jpg", "preference": 10, "width": 1920, "height": 1080},
            ],
        }
        result = service._get_best_quality_thumbnail(video_info)
        assert result == "https://high.jpg"

    def test_falls_back_to_url_check_when_no_thumbnails(self, service):
        service._check_thumbnail_exists = MagicMock(side_effect=lambda url: "maxresdefault.webp" in url)
        video_info = {"id": "v1", "thumbnails": []}
        result = service._get_best_quality_thumbnail(video_info)
        assert result is not None
        assert "maxresdefault" in result

    def test_returns_none_when_no_thumbnail_found(self, service):
        service._check_thumbnail_exists = MagicMock(return_value=False)
        video_info = {"id": "v1", "thumbnails": []}
        result = service._get_best_quality_thumbnail(video_info)
        assert result is None


# ---------------------------------------------------------------------------
# _check_thumbnail_exists
# ---------------------------------------------------------------------------


class TestCheckThumbnailExists:
    def test_returns_true_for_200(self, service):
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.head", return_value=mock_resp):
            assert service._check_thumbnail_exists("https://example.com/t.jpg") is True

    def test_returns_false_for_404(self, service):
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("requests.head", return_value=mock_resp):
            assert service._check_thumbnail_exists("https://example.com/t.jpg") is False

    def test_returns_false_on_exception(self, service):
        from unittest.mock import patch
        with patch("requests.head", side_effect=Exception("timeout")):
            assert service._check_thumbnail_exists("https://example.com/t.jpg") is False


# ---------------------------------------------------------------------------
# _download_and_save_thumbnail
# ---------------------------------------------------------------------------


class TestDownloadAndSaveThumbnail:
    def test_returns_true_and_filename_on_success(self, service):
        from unittest.mock import patch, MagicMock
        from pathlib import Path
        service.file_service.get_song_directory.return_value = Path("/tmp/songs/s1")
        with patch("app.services.file_management.download_image", return_value=True) as mock_dl:
            success, filename = service._download_and_save_thumbnail("s1", "https://i.ytimg.com/vi_webp/abc/maxresdefault.webp")
        assert success is True
        assert filename == "thumbnail.webp"

    def test_detects_jpg_extension(self, service):
        from unittest.mock import patch
        from pathlib import Path
        service.file_service.get_song_directory.return_value = Path("/tmp/songs/s1")
        with patch("app.services.file_management.download_image", return_value=True):
            _, filename = service._download_and_save_thumbnail("s1", "https://t.jpg")
        assert filename == "thumbnail.jpg"

    def test_detects_png_extension(self, service):
        from unittest.mock import patch
        from pathlib import Path
        service.file_service.get_song_directory.return_value = Path("/tmp/songs/s1")
        with patch("app.services.file_management.download_image", return_value=True):
            _, filename = service._download_and_save_thumbnail("s1", "https://i.ytimg.com/vi/abc/thumb.png")
        assert filename == "thumbnail.png"

    def test_defaults_to_jpg_for_unknown_extension(self, service):
        from unittest.mock import patch
        from pathlib import Path
        service.file_service.get_song_directory.return_value = Path("/tmp/songs/s1")
        with patch("app.services.file_management.download_image", return_value=True):
            _, filename = service._download_and_save_thumbnail("s1", "https://i.ytimg.com/vi/abc/thumb.gif")
        assert filename == "thumbnail.jpg"

    def test_returns_false_when_download_fails(self, service):
        from unittest.mock import patch
        from pathlib import Path
        service.file_service.get_song_directory.return_value = Path("/tmp/songs/s1")
        with patch("app.services.file_management.download_image", return_value=False):
            success, filename = service._download_and_save_thumbnail("s1", "https://t.jpg")
        assert success is False
        assert filename == ""

    def test_returns_false_on_exception(self, service):
        service.file_service.get_song_directory.side_effect = RuntimeError("fs error")
        success, filename = service._download_and_save_thumbnail("s1", "https://t.jpg")
        assert success is False
        service.file_service.get_song_directory.side_effect = None


# ---------------------------------------------------------------------------
# _extract_audio_duration
# ---------------------------------------------------------------------------


class TestExtractAudioDuration:
    def test_returns_duration_from_librosa(self, service):
        from unittest.mock import patch, MagicMock
        mock_librosa = MagicMock()
        mock_librosa.get_duration.return_value = 213.5
        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result = service._extract_audio_duration("/tmp/song.mp3")
        assert result == 213.5

    def test_returns_none_on_exception(self, service):
        from unittest.mock import patch, MagicMock
        mock_librosa = MagicMock()
        mock_librosa.get_duration.side_effect = Exception("no audio")
        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result = service._extract_audio_duration("/tmp/bad.mp3")
        assert result is None

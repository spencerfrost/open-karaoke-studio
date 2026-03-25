"""Unit tests for SyncedLyricsService."""
from unittest.mock import patch

import pytest

from app.exceptions import ServiceError
from app.services.syncedlyrics_service import SyncedLyricsService


@pytest.fixture
def service():
    return SyncedLyricsService()


class TestSearchLyrics:
    def test_returns_synced_lyrics_when_found(self, service):
        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.return_value = "[00:01.00] Some lyric line"
            results = service.search_lyrics("Rick Astley Never Gonna Give You Up")
        assert len(results) == 1
        assert results[0]["syncedLyrics"] == "[00:01.00] Some lyric line"

    def test_falls_back_to_plain_lyrics_when_synced_none(self, service):
        def side_effect(query, **kwargs):
            if kwargs.get("synced_only"):
                return None
            if kwargs.get("plain_only"):
                return "Some lyric line"
            return None

        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.side_effect = side_effect
            results = service.search_lyrics("Artist Song")
        assert len(results) == 1
        assert results[0]["plainLyrics"] == "Some lyric line"
        assert results[0]["syncedLyrics"] is None

    def test_returns_empty_list_when_both_fail(self, service):
        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.return_value = None
            results = service.search_lyrics("Unknown Song")
        assert results == []

    def test_handles_synced_search_exception(self, service):
        call_count = [0]

        def side_effect(query, **kwargs):
            call_count[0] += 1
            if kwargs.get("synced_only"):
                raise Exception("API error")
            return "plain lyrics fallback"

        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.side_effect = side_effect
            results = service.search_lyrics("Artist Song")
        # Should fall back to plain lyrics
        assert len(results) == 1
        assert results[0]["plainLyrics"] == "plain lyrics fallback"

    def test_raises_service_error_on_unexpected_exception(self, service):
        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            # Outer exception (not inner try block) — patch the logger.debug to raise
            mock_sl.search.side_effect = [None, None]
            # This should return empty list, not raise
            results = service.search_lyrics("query")
        assert results == []

    def test_result_contains_expected_fields(self, service):
        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.return_value = "[00:00.00] Line"
            results = service.search_lyrics("test query")
        result = results[0]
        assert "id" in result
        assert "name" in result
        assert "syncedLyrics" in result
        assert "plainLyrics" in result
        assert result["name"] == "test query"

    def test_synced_result_sets_synced_lyrics(self, service):
        synced = "[00:01.00] Rick rolled"
        with patch("app.services.syncedlyrics_service.syncedlyrics") as mock_sl:
            mock_sl.search.return_value = synced
            results = service.search_lyrics("query")
        assert results[0]["syncedLyrics"] == synced


class TestSearchLyricsStructured:
    def test_builds_query_from_track_and_artist(self, service):
        with patch.object(service, "search_lyrics", return_value=[]) as mock_search:
            service.search_lyrics_structured(
                {"track_name": "Never Gonna", "artist_name": "Rick Astley"}
            )
        mock_search.assert_called_once_with("Never Gonna Rick Astley")

    def test_returns_empty_list_for_empty_params(self, service):
        result = service.search_lyrics_structured({})
        assert result == []

    def test_returns_empty_list_when_only_album_provided(self, service):
        result = service.search_lyrics_structured({"album_name": "Album Only"})
        assert result == []

    def test_enhances_result_with_structured_metadata(self, service):
        fake_result = {
            "id": None, "name": "query", "trackName": None, "artistName": None,
            "albumName": None, "duration": None, "instrumental": False,
            "plainLyrics": "some", "syncedLyrics": "[00:00.00] line"
        }
        with patch.object(service, "search_lyrics", return_value=[fake_result]):
            results = service.search_lyrics_structured(
                {"track_name": "Never Gonna", "artist_name": "Rick Astley", "album_name": "Whenever"}
            )
        assert results[0]["trackName"] == "Never Gonna"
        assert results[0]["artistName"] == "Rick Astley"
        assert results[0]["albumName"] == "Whenever"

    def test_handles_missing_params_keys(self, service):
        with patch.object(service, "search_lyrics", return_value=[]) as mock_search:
            service.search_lyrics_structured({"track_name": "Song"})
        mock_search.assert_called_once_with("Song")

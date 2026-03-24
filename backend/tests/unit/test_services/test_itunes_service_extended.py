"""Extended tests for itunes_service covering lookup_itunes and uncovered error paths."""
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from app.services.itunes_service import lookup_itunes, search_itunes


SAMPLE_TRACK = {
    "trackId": 123456789,
    "trackName": "Never Gonna Give You Up",
    "artistName": "Rick Astley",
    "artistId": 987654321,
    "collectionName": "Whenever You Need Somebody",
    "collectionId": 111222333,
    "releaseDate": "1987-11-01T00:00:00Z",

    "trackNumber": 1,
    "trackCount": 10,
    "discNumber": 1,
    "discCount": 1,
    "trackTimeMillis": 213000,
    "artworkUrl30": "https://example.com/art30.jpg",
    "artworkUrl60": "https://example.com/art60.jpg",
    "artworkUrl100": "https://example.com/100x100/art.jpg",
    "previewUrl": "https://example.com/preview.mp3",
    "trackExplicitness": "notExplicit",
    "collectionExplicitness": "notExplicit",
    "isStreamable": True,
    "currency": "USD",
    "country": "USA",
    "trackPrice": 1.29,
    "collectionPrice": 9.99,
    "trackRentalPrice": 0.0,
    "collectionHdPrice": 0.0,
    "copyright": "© 1987 RCA",
    "artistViewUrl": "https://music.apple.com/artist/123",
    "collectionViewUrl": "https://music.apple.com/album/123",
    "trackViewUrl": "https://music.apple.com/track/123",
}


def _mock_response(data, status_code=200):
    resp = Mock()
    resp.json.return_value = data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    resp.headers = {}
    resp.url = "https://itunes.apple.com/lookup"
    resp.reason = "OK"
    resp.text = ""
    return resp


class TestLookupItunes:
    @patch("app.services.itunes_service.requests.get")
    def test_returns_track_data(self, mock_get):
        mock_get.return_value = _mock_response({"results": [SAMPLE_TRACK]})
        result = lookup_itunes(123456789)
        assert result is not None
        assert result["title"] == "Never Gonna Give You Up"
        assert result["artist"] == "Rick Astley"
        assert result["id"] == 123456789

    @patch("app.services.itunes_service.requests.get")
    def test_returns_none_for_empty_results(self, mock_get):
        mock_get.return_value = _mock_response({"results": []})
        assert lookup_itunes(999) is None

    @patch("app.services.itunes_service.requests.get")
    def test_parses_release_date(self, mock_get):
        mock_get.return_value = _mock_response({"results": [SAMPLE_TRACK]})
        result = lookup_itunes(123456789)
        assert result["releaseYear"] == 1987
        assert result["releaseDateFormatted"] == "1987-11-01"

    @patch("app.services.itunes_service.requests.get")
    def test_generates_600px_artwork_url(self, mock_get):
        mock_get.return_value = _mock_response({"results": [SAMPLE_TRACK]})
        result = lookup_itunes(123456789)
        assert "artworkUrl600" in result
        assert "600x600" in result["artworkUrl600"]

    @patch("app.services.itunes_service.requests.get")
    def test_handles_missing_artwork_url(self, mock_get):
        track = {**SAMPLE_TRACK, "artworkUrl100": None}
        mock_get.return_value = _mock_response({"results": [track]})
        result = lookup_itunes(123456789)
        assert "artworkUrl600" not in result

    @patch("app.services.itunes_service.requests.get")
    def test_handles_invalid_release_date(self, mock_get):
        track = {**SAMPLE_TRACK, "releaseDate": "bad-date"}
        mock_get.return_value = _mock_response({"results": [track]})
        result = lookup_itunes(123456789)
        assert result["releaseYear"] is None
        assert result["releaseDateFormatted"] is None

    @patch("app.services.itunes_service.requests.get")
    def test_returns_none_on_request_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException("network error")
        assert lookup_itunes(123456789) is None

    @patch("app.services.itunes_service.requests.get")
    def test_returns_none_on_request_exception_with_response(self, mock_get):
        err = requests.RequestException("HTTP error")
        err.response = Mock()
        err.response.status_code = 503
        err.response.reason = "Service Unavailable"
        err.response.url = "https://itunes.apple.com/lookup"
        err.response.headers = {}
        err.response.text = "Service Unavailable"
        mock_get.side_effect = err
        assert lookup_itunes(123456789) is None

    @patch("app.services.itunes_service.requests.get")
    def test_returns_none_on_unexpected_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        assert lookup_itunes(123456789) is None

    @patch("app.services.itunes_service.requests.get")
    def test_includes_raw_data(self, mock_get):
        mock_get.return_value = _mock_response({"results": [SAMPLE_TRACK]})
        result = lookup_itunes(123456789)
        assert "rawData" in result
        assert result["rawData"]["trackName"] == "Never Gonna Give You Up"


class TestSearchItunesErrorPaths:
    @patch("app.services.itunes_service.requests.get")
    def test_request_exception_with_403_response(self, mock_get):
        err = requests.RequestException("403 Forbidden")
        err.response = Mock()
        err.response.status_code = 403
        err.response.reason = "Forbidden"
        err.response.url = "https://itunes.apple.com/search"
        err.response.headers = {}
        err.response.text = "Forbidden"
        mock_get.side_effect = err
        result = search_itunes("Artist", "Song")
        assert result == []

    @patch("app.services.itunes_service.requests.get")
    def test_request_exception_with_429_response(self, mock_get):
        err = requests.RequestException("429 Too Many Requests")
        err.response = Mock()
        err.response.status_code = 429
        err.response.reason = "Too Many Requests"
        err.response.url = "https://itunes.apple.com/search"
        err.response.headers = {"Retry-After": "60"}
        err.response.text = ""
        mock_get.side_effect = err
        result = search_itunes("Artist", "Song")
        assert result == []

    @patch("app.services.itunes_service.requests.get")
    def test_request_exception_with_500_response(self, mock_get):
        err = requests.RequestException("500 Server Error")
        err.response = Mock()
        err.response.status_code = 500
        err.response.reason = "Internal Server Error"
        err.response.url = "https://itunes.apple.com/search"
        err.response.headers = {}
        err.response.text = "error"
        mock_get.side_effect = err
        result = search_itunes("Artist", "Song")
        assert result == []

    @patch("app.services.itunes_service.requests.get")
    def test_request_exception_without_response(self, mock_get):
        err = requests.RequestException("Network error")
        err.response = None
        mock_get.side_effect = err
        result = search_itunes("Artist", "Song")
        assert result == []

    @patch("app.services.itunes_service.requests.get")
    def test_general_exception_returns_empty_list(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected crash")
        result = search_itunes("Artist", "Song")
        assert result == []

    @patch("app.services.itunes_service.requests.get")
    def test_search_with_only_artist(self, mock_get):
        mock_get.return_value = _mock_response({"results": []})
        search_itunes("Artist", "")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["term"] == "Artist"

    @patch("app.services.itunes_service.requests.get")
    def test_result_limit_respected(self, mock_get):
        tracks = [
            {
                "trackId": i, "trackName": f"Song {i}", "artistName": "Artist",
                "collectionName": "Album", "releaseDate": "2023-01-01T00:00:00Z",
            }
            for i in range(10)
        ]
        mock_get.return_value = _mock_response({"results": tracks})
        results = search_itunes("Artist", "Song", limit=3)
        assert len(results) <= 3

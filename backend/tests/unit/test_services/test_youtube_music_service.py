"""Unit tests for YoutubeMusicService — all external calls mocked."""
from unittest.mock import MagicMock, patch

import pytest

import app.services.youtube_music_service as _module


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level TTLCaches before each test to prevent cross-test pollution."""
    _module._search_cache.clear()
    _module._artist_cache.clear()
    _module._album_cache.clear()
    yield
    _module._search_cache.clear()
    _module._artist_cache.clear()
    _module._album_cache.clear()


@pytest.fixture
def mock_ytmusic():
    """Patch YTMusic at module level and return the mock instance."""
    with patch("app.services.youtube_music_service.YTMusic") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def service(mock_ytmusic):
    from app.services.youtube_music_service import YoutubeMusicService
    return YoutubeMusicService()


# ---------------------------------------------------------------------------
# _normalize_song_results
# ---------------------------------------------------------------------------

SAMPLE_SONG_RESULT = {
    "resultType": "song",
    "videoId": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
    "duration": "3:33",
    "album": {"name": "Whenever You Need Somebody"},
    "thumbnails": [{"url": "https://example.com/thumb.jpg"}],
}


class TestNormalizeSongResults:
    def test_returns_mapped_fields(self, service):
        results = service._normalize_song_results([SAMPLE_SONG_RESULT])
        assert len(results) == 1
        song = results[0]
        assert song["videoId"] == "dQw4w9WgXcQ"
        assert song["title"] == "Never Gonna Give You Up"
        assert song["artist"] == "Rick Astley"
        assert song["duration"] == "3:33"
        assert song["album"] == "Whenever You Need Somebody"

    def test_skips_non_song_result_types(self, service):
        raw = [{"resultType": "video", "videoId": "abc", "title": "Video"}]
        results = service._normalize_song_results(raw)
        assert results == []

    def test_skips_items_without_video_id(self, service):
        raw = [{"resultType": "song", "title": "No ID Song"}]
        results = service._normalize_song_results(raw)
        assert results == []

    def test_handles_missing_artist(self, service):
        raw = [{**SAMPLE_SONG_RESULT, "artists": []}]
        results = service._normalize_song_results(raw)
        assert results[0]["artist"] is None

    def test_handles_missing_album(self, service):
        # When "album" key is absent (not None), album name should be None
        raw = [{k: v for k, v in SAMPLE_SONG_RESULT.items() if k != "album"}]
        results = service._normalize_song_results(raw)
        assert results[0]["album"] is None

    def test_handles_missing_thumbnails(self, service):
        raw = [{**SAMPLE_SONG_RESULT, "thumbnails": []}]
        results = service._normalize_song_results(raw)
        assert results[0]["thumbnails"] == []

    def test_empty_input(self, service):
        assert service._normalize_song_results([]) == []


# ---------------------------------------------------------------------------
# _normalize_artist_results
# ---------------------------------------------------------------------------

SAMPLE_ARTIST_RESULT = {
    "resultType": "artist",
    "browseId": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "artist": "Rick Astley",
    "subscribers": "1M",
    "thumbnails": [{"url": "https://example.com/artist.jpg"}],
}


class TestNormalizeArtistResults:
    def test_returns_mapped_fields(self, service):
        results = service._normalize_artist_results([SAMPLE_ARTIST_RESULT])
        assert len(results) == 1
        artist = results[0]
        assert artist["browseId"] == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert artist["name"] == "Rick Astley"
        assert artist["subscribers"] == "1M"

    def test_skips_non_artist_result_types(self, service):
        raw = [{"resultType": "song", "browseId": "abc"}]
        assert service._normalize_artist_results(raw) == []

    def test_skips_items_without_browse_id(self, service):
        raw = [{"resultType": "artist", "artist": "No ID"}]
        assert service._normalize_artist_results(raw) == []

    def test_respects_max_results(self, service):
        raw = [SAMPLE_ARTIST_RESULT] * 10
        results = service._normalize_artist_results(raw, max_results=2)
        assert len(results) == 2

    def test_falls_back_to_name_field(self, service):
        raw = [{**SAMPLE_ARTIST_RESULT, "artist": None, "name": "Fallback Name"}]
        results = service._normalize_artist_results(raw)
        assert results[0]["name"] == "Fallback Name"

    def test_uses_unknown_artist_when_no_name(self, service):
        raw = [{**SAMPLE_ARTIST_RESULT, "artist": None, "name": None}]
        results = service._normalize_artist_results(raw)
        assert results[0]["name"] == "Unknown Artist"


# ---------------------------------------------------------------------------
# search_combined
# ---------------------------------------------------------------------------


class TestSearchCombined:
    def test_calls_ytmusic_search_twice(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search_combined("Rick Astley")
        assert mock_ytmusic.search.call_count == 2

    def test_returns_artists_and_songs_keys(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        result = service.search_combined("query")
        assert "artists" in result
        assert "songs" in result

    def test_second_call_uses_cache(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search_combined("cached query")
        service.search_combined("cached query")
        # First call makes 2 searches (artists + songs); second call hits cache
        assert mock_ytmusic.search.call_count == 2

    def test_different_queries_not_cached_together(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search_combined("query A")
        service.search_combined("query B")
        # Two separate searches × 2 calls each = 4 total
        assert mock_ytmusic.search.call_count == 4

    def test_normalizes_song_results(self, service, mock_ytmusic):
        def search_side_effect(query, filter, limit):
            if filter == "songs":
                return [SAMPLE_SONG_RESULT]
            return []
        mock_ytmusic.search.side_effect = search_side_effect
        result = service.search_combined("Rick Astley")
        assert len(result["songs"]) == 1
        assert result["songs"][0]["videoId"] == "dQw4w9WgXcQ"


# ---------------------------------------------------------------------------
# _get_song_duration
# ---------------------------------------------------------------------------


class TestGetSongDuration:
    def test_returns_mmss_format(self, service, mock_ytmusic):
        mock_ytmusic.get_song.return_value = {
            "videoDetails": {"lengthSeconds": "225"}
        }
        result = service._get_song_duration("vid123")
        assert result == "3:45"

    def test_handles_zero_seconds(self, service, mock_ytmusic):
        mock_ytmusic.get_song.return_value = {"videoDetails": {"lengthSeconds": "0"}}
        result = service._get_song_duration("vid123")
        assert result == "0:00"

    def test_returns_none_when_length_missing(self, service, mock_ytmusic):
        mock_ytmusic.get_song.return_value = {"videoDetails": {}}
        result = service._get_song_duration("vid123")
        assert result is None

    def test_returns_none_on_exception(self, service, mock_ytmusic):
        mock_ytmusic.get_song.side_effect = Exception("API error")
        result = service._get_song_duration("vid123")
        assert result is None


# ---------------------------------------------------------------------------
# get_artist
# ---------------------------------------------------------------------------

SAMPLE_ARTIST_RAW = {
    "name": "Rick Astley",
    "thumbnails": [{"url": "https://example.com/artist.jpg"}],
    "description": "A legendary artist",
    "subscribers": "1M",
    "songs": {
        "results": [
            {
                "videoId": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "duration": "3:33",
                "album": {"name": "Whenever You Need Somebody"},
                "thumbnails": [],
            }
        ]
    },
    "albums": {
        "results": [
            {"browseId": "album-1", "title": "Whenever You Need Somebody", "year": "1987", "thumbnails": []}
        ]
    },
    "singles": {"results": []},
}


class TestGetArtist:
    def test_returns_artist_info(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.return_value = SAMPLE_ARTIST_RAW
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert result["artist"]["name"] == "Rick Astley"
        assert result["artist"]["id"] == "UCuAXFkgsw1L7xaCfnd5JJOw"

    def test_returns_top_songs(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.return_value = SAMPLE_ARTIST_RAW
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert len(result["topSongs"]) == 1
        assert result["topSongs"][0]["videoId"] == "dQw4w9WgXcQ"

    def test_returns_albums(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.return_value = SAMPLE_ARTIST_RAW
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert len(result["albums"]) == 1
        assert result["albums"][0]["type"] == "album"

    def test_caches_result(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.return_value = SAMPLE_ARTIST_RAW
        service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert mock_ytmusic.get_artist.call_count == 1

    def test_fetches_duration_when_missing(self, service, mock_ytmusic):
        raw = {
            **SAMPLE_ARTIST_RAW,
            "songs": {
                "results": [{"videoId": "vid123", "title": "Song", "duration": None, "album": None, "thumbnails": []}]
            },
        }
        mock_ytmusic.get_artist.return_value = raw
        mock_ytmusic.get_song.return_value = {"videoDetails": {"lengthSeconds": "200"}}
        result = service.get_artist("artist-id")
        assert result["topSongs"][0]["duration"] == "3:20"

    def test_propagates_exception(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            service.get_artist("bad-id")


# ---------------------------------------------------------------------------
# get_album_tracks
# ---------------------------------------------------------------------------

SAMPLE_ALBUM_RAW = {
    "title": "Whenever You Need Somebody",
    "year": "1987",
    "thumbnails": [{"url": "https://example.com/album.jpg"}],
    "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
    "tracks": [
        {
            "videoId": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
            "duration": "3:33",
            "trackNumber": 1,
            "isExplicit": False,
        }
    ],
}


class TestGetAlbumTracks:
    def test_returns_album_metadata(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        result = service.get_album_tracks("album-id-1")
        assert result["album"]["title"] == "Whenever You Need Somebody"
        assert result["album"]["browseId"] == "album-id-1"
        assert result["album"]["trackCount"] == 1

    def test_returns_tracks(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        result = service.get_album_tracks("album-id-1")
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["videoId"] == "dQw4w9WgXcQ"
        assert result["tracks"][0]["title"] == "Never Gonna Give You Up"

    def test_caches_result(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        service.get_album_tracks("album-id-1")
        service.get_album_tracks("album-id-1")
        assert mock_ytmusic.get_album.call_count == 1

    def test_handles_empty_tracks(self, service, mock_ytmusic):
        raw = {**SAMPLE_ALBUM_RAW, "tracks": []}
        mock_ytmusic.get_album.return_value = raw
        result = service.get_album_tracks("album-id-1")
        assert result["tracks"] == []
        assert result["album"]["trackCount"] == 0

    def test_handles_missing_artists_in_album(self, service, mock_ytmusic):
        raw = {**SAMPLE_ALBUM_RAW, "artists": []}
        mock_ytmusic.get_album.return_value = raw
        result = service.get_album_tracks("album-id-1")
        assert result["album"]["artist"] is None

    def test_propagates_exception(self, service, mock_ytmusic):
        mock_ytmusic.get_album.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            service.get_album_tracks("bad-album")

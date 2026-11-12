"""Unit tests for YoutubeMusicService — all external calls mocked."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.services.youtube_music_service as _module
from app.exceptions import NotFoundError
from app.services.youtube_music_service import group_search_songs

# ytmusicapi responses recorded from the live API on 2026-10-25, trimmed to
# the fields the service reads.
RECORDED = json.loads(
    (Path(__file__).parents[2] / "fixtures/youtube_music/search.json").read_text()
)


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


def _recorded_search(query):
    def search(q, filter=None, limit=20):
        # The unfiltered top-result lookup isn't recorded
        return RECORDED[query][filter][:limit] if filter else []

    return search


# ---------------------------------------------------------------------------
# _normalize_song_results
# ---------------------------------------------------------------------------

SAMPLE_SONG_RESULT = {
    "resultType": "song",
    "videoId": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
    "duration": "3:33",
    "duration_seconds": 213,
    "isExplicit": False,
    "album": {"name": "Whenever You Need Somebody", "id": "MPREb_1"},
    "thumbnails": [{"url": "https://example.com/thumb.jpg"}],
}


class TestNormalizeSongResults:
    def test_returns_mapped_fields(self, service):
        song = service._normalize_song_results([SAMPLE_SONG_RESULT])[0]
        assert song == {
            "videoId": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
            "artist": "Rick Astley",
            "album": "Whenever You Need Somebody",
            "albumId": "MPREb_1",
            "durationSeconds": 213,
            "isExplicit": False,
            "thumbnails": [{"url": "https://example.com/thumb.jpg"}],
        }

    def test_keeps_every_artist(self, service):
        raw = {
            **SAMPLE_SONG_RESULT,
            "artists": [
                {"name": "JAY-Z", "id": "UC1"},
                {"name": "Alicia Keys", "id": "UC2"},
            ],
        }
        song = service._normalize_song_results([raw])[0]
        assert [a["name"] for a in song["artists"]] == ["JAY-Z", "Alicia Keys"]
        assert song["artist"] == "JAY-Z feat. Alicia Keys"

    def test_parses_duration_text_when_seconds_missing(self, service):
        raw = {**SAMPLE_SONG_RESULT, "duration_seconds": None, "duration": "1:02:03"}
        assert service._normalize_song_results([raw])[0]["durationSeconds"] == 3723

    def test_skips_non_song_result_types(self, service):
        raw = [{"resultType": "video", "videoId": "abc", "title": "Video"}]
        assert service._normalize_song_results(raw) == []

    def test_skips_items_without_video_id(self, service):
        raw = [{"resultType": "song", "title": "No ID Song"}]
        assert service._normalize_song_results(raw) == []

    def test_handles_missing_artist(self, service):
        song = service._normalize_song_results([{**SAMPLE_SONG_RESULT, "artists": []}])[
            0
        ]
        assert song["artists"] == []
        assert song["artist"] is None

    def test_handles_missing_album(self, service):
        raw = {k: v for k, v in SAMPLE_SONG_RESULT.items() if k != "album"}
        song = service._normalize_song_results([raw])[0]
        assert song["album"] is None
        assert song["albumId"] is None

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
        assert results[0]["browseId"] == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert results[0]["name"] == "Rick Astley"
        assert results[0]["subscribers"] == "1M"

    def test_skips_non_artist_result_types(self, service):
        raw = [{"resultType": "song", "browseId": "abc"}]
        assert service._normalize_artist_results(raw) == []

    def test_skips_items_without_browse_id(self, service):
        raw = [{"resultType": "artist", "artist": "No ID"}]
        assert service._normalize_artist_results(raw) == []

    def test_respects_max_results(self, service):
        raw = [SAMPLE_ARTIST_RESULT] * 10
        assert len(service._normalize_artist_results(raw, max_results=3)) == 3

    def test_falls_back_to_name_field(self, service):
        raw = [{**SAMPLE_ARTIST_RESULT, "artist": None, "name": "Fallback Name"}]
        assert service._normalize_artist_results(raw)[0]["name"] == "Fallback Name"

    def test_uses_unknown_artist_when_no_name(self, service):
        raw = [{**SAMPLE_ARTIST_RESULT, "artist": None, "name": None}]
        assert service._normalize_artist_results(raw)[0]["name"] == "Unknown Artist"


# ---------------------------------------------------------------------------
# search and suggestions
# ---------------------------------------------------------------------------


class TestSearch:
    def test_searches_artists_songs_and_the_top_result(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search("test", limit=20)
        filters = {c.kwargs.get("filter") for c in mock_ytmusic.search.call_args_list}
        assert filters == {"artists", "songs", None}

    def test_second_call_uses_cache(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search("cached query")
        service.search("cached query")
        assert mock_ytmusic.search.call_count == 3  # artists, songs, top result

    def test_different_queries_not_cached_together(self, service, mock_ytmusic):
        mock_ytmusic.search.return_value = []
        service.search("query one")
        service.search("query two")
        assert mock_ytmusic.search.call_count == 6

    def test_recorded_search(self, service, mock_ytmusic):
        mock_ytmusic.search.side_effect = _recorded_search("dont stop me now")
        result = service.search("dont stop me now")
        assert result["songs"][0]["artist"] == "Queen"
        assert len(result["artists"]) <= 3

    def test_propagates_exception(self, service, mock_ytmusic):
        mock_ytmusic.search.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            service.search("q")


def _top_result_search(top):
    """Artist and song searches come back empty; the unfiltered one, `top`."""

    def search(q, filter=None, limit=20):
        return [] if filter else top

    return search


class TestTopArtist:
    def test_artist_top_result_gives_its_id(self, service, mock_ytmusic):
        # As recorded for "jamiroquai": the id is on the artist credit
        mock_ytmusic.search.side_effect = _top_result_search(
            [
                {
                    "category": "Top result",
                    "resultType": "artist",
                    "artists": [{"name": "Jamiroquai", "id": "UCjam"}],
                }
            ]
        )
        assert service.search("jamiroquai")["topArtistId"] == "UCjam"

    def test_song_top_result_gives_none(self, service, mock_ytmusic):
        mock_ytmusic.search.side_effect = _top_result_search(
            [
                {
                    "category": "Top result",
                    "resultType": "song",
                    "title": "Hello",
                    "artists": [{"name": "Adele", "id": "UCadele"}],
                }
            ]
        )
        assert service.search("hello")["topArtistId"] is None

    def test_artist_further_down_gives_none(self, service, mock_ytmusic):
        mock_ytmusic.search.side_effect = _top_result_search(
            [{"category": "Artists", "resultType": "artist", "browseId": "UCx"}]
        )
        assert service.search("x")["topArtistId"] is None

    def test_failed_lookup_leaves_the_search_alone(self, service, mock_ytmusic):
        def search(q, filter=None, limit=20):
            if filter is None:
                raise Exception("top result down")
            return []

        mock_ytmusic.search.side_effect = search
        result = service.search("x")
        assert result["topArtistId"] is None
        assert result["songs"] == []


class TestSuggestions:
    def test_returns_and_caches_suggestions(self, service, mock_ytmusic):
        mock_ytmusic.get_search_suggestions.return_value = ["don't stop me now", ""]
        assert service.get_suggestions("dont st") == ["don't stop me now"]
        service.get_suggestions("dont st")
        assert mock_ytmusic.get_search_suggestions.call_count == 1


# ---------------------------------------------------------------------------
# group_search_songs
# ---------------------------------------------------------------------------


class TestGroupSearchSongs:
    @pytest.fixture
    def grouped(self, service, mock_ytmusic):
        def _grouped(query):
            mock_ytmusic.search.side_effect = _recorded_search(query)
            return group_search_songs(service.search(query)["songs"])

        return _grouped

    def test_original_is_the_best_match(self, grouped):
        best = grouped("dont stop me now")["bestMatch"]
        assert best["title"] == "Don't Stop Me Now"
        assert best["artist"] == "Queen"

    def test_covers_are_other_versions(self, grouped):
        versions = grouped("dont stop me now")["otherVersions"]
        titles = {s["title"] for s in versions}
        artists = {s["artist"] for s in versions}
        # Straight covers, a curly apostrophe, bracketed and dash-suffixed takes
        assert "University of South Carolina Marching Band" in artists
        assert "Jonathan Young" in artists
        assert "Don't Stop Me Now (Talkbox Version)" in titles
        assert "Don't Stop Me Now - Acoustic" in titles
        assert "Queen" not in artists

    def test_different_songs_are_other_songs(self, grouped):
        groups = grouped("dont stop me now")
        other_titles = {s["title"] for s in groups["otherSongs"]}
        assert "Don't Stop The Music" in other_titles
        assert "Can't Stop Me Now" in other_titles
        assert not other_titles & {s["title"] for s in groups["otherVersions"]}

    def test_feat_credit_in_the_title_still_groups(self, grouped):
        groups = grouped("empire state of mind")
        assert groups["bestMatch"]["title"].startswith("Empire State Of Mind")
        assert "EMPIRE STATE OF MIND" in {s["title"] for s in groups["otherVersions"]}

    def test_every_result_lands_somewhere_once(self, grouped):
        groups = grouped("dont stop me now")
        count = 1 + len(groups["otherVersions"]) + len(groups["otherSongs"])
        assert count == len(RECORDED["dont stop me now"]["songs"])

    def test_no_results(self):
        assert group_search_songs([]) == {
            "bestMatch": None,
            "otherVersions": [],
            "otherSongs": [],
        }


# ---------------------------------------------------------------------------
# get_artist and get_artist_songs
# ---------------------------------------------------------------------------


def _track(n):
    return {
        "videoId": f"vid{n}",
        "title": f"Song {n}",
        "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
        "album": {"name": "Album", "id": "MPREb_1"},
        "duration": "3:33",
        "duration_seconds": 213,
        "thumbnails": [],
    }


SAMPLE_ARTIST_RAW = {
    "name": "Rick Astley",
    "thumbnails": [{"url": "https://example.com/artist.jpg"}],
    "description": "A legendary artist",
    "subscribers": "1M",
    "songs": {
        "browseId": "VLOLAK5uy_songs",
        # The artist page's inline five carry no duration
        "results": [{**_track(n), "duration": None} for n in range(5)],
    },
    "albums": {
        "results": [
            {
                "browseId": "album-1",
                "title": "Whenever You Need Somebody",
                "year": "1987",
                "thumbnails": [],
            }
        ],
        "browseId": "UCchannel",
        "params": "more-albums",
    },
    "singles": {"results": []},
}


class TestGetArtist:
    @pytest.fixture(autouse=True)
    def artist_page(self, mock_ytmusic):
        mock_ytmusic.get_artist.return_value = SAMPLE_ARTIST_RAW
        mock_ytmusic.get_playlist.return_value = {
            "tracks": [_track(n) for n in range(12)]
        }

    def test_returns_artist_info(self, service):
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert result["artist"]["name"] == "Rick Astley"
        assert result["artist"]["id"] == "UCuAXFkgsw1L7xaCfnd5JJOw"

    def test_returns_five_popular_songs_and_says_there_are_more(self, service):
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert [s["videoId"] for s in result["topSongs"]] == [
            f"vid{n}" for n in range(5)
        ]
        assert result["topSongs"][0]["durationSeconds"] == 213
        assert result["hasMoreSongs"] is True

    def test_no_more_songs_when_the_playlist_is_short(self, service, mock_ytmusic):
        mock_ytmusic.get_playlist.return_value = {
            "tracks": [_track(n) for n in range(5)]
        }
        assert service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")["hasMoreSongs"] is False

    def test_all_songs_come_from_the_playlist(self, service, mock_ytmusic):
        service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        songs = service.get_artist_songs("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert len(songs) == 12
        # The artist page and playlist were each read once
        assert mock_ytmusic.get_artist.call_count == 1
        assert mock_ytmusic.get_playlist.call_count == 1

    def test_falls_back_to_the_inline_songs(self, service, mock_ytmusic):
        mock_ytmusic.get_playlist.side_effect = Exception("playlist gone")
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert len(result["topSongs"]) == 5
        assert result["hasMoreSongs"] is False

    def test_fetches_every_album_oldest_first_once_each(self, service, mock_ytmusic):
        mock_ytmusic.get_artist_albums.return_value = [
            {"browseId": "a-2017", "title": "Automaton", "year": "2017"},
            {"browseId": "a-tales", "title": "Late Night Tales", "year": None},
            {"browseId": "a-tales-2", "title": "Late Night Tales", "year": None},
            {
                "browseId": "a-1993",
                "title": "Emergency On Planet Earth",
                "year": "1993",
            },
            {
                "browseId": "a-1996",
                "title": "Travelling Without Moving",
                "year": "1996",
            },
        ]

        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")

        mock_ytmusic.get_artist_albums.assert_called_once_with(
            "UCchannel", "more-albums"
        )
        assert [a["browseId"] for a in result["albums"]] == [
            "a-1993",
            "a-1996",
            "a-2017",
            "a-tales",
        ]
        assert "albumsMore" not in result
        assert "singlesMore" not in result

    def test_remix_collections_are_set_apart(self, service, mock_ytmusic):
        mock_ytmusic.get_artist_albums.return_value = [
            {"browseId": "a-2001", "title": "A Funk Odyssey", "year": "2001"},
            {"browseId": "r-1999", "title": "Supersonic (Remixes)", "year": "1999"},
            {"browseId": "r-1994", "title": "Space Cowboy (Remixes)", "year": "1994"},
            {"browseId": "r-2010", "title": "Remixed", "year": "2010"},
            {
                "browseId": "r-2022",
                "title": "Little L (Remastered - Sped Up Version)",
                "year": "2022",
            },
        ]

        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")

        assert [a["browseId"] for a in result["albums"]] == ["a-2001"]
        assert [a["browseId"] for a in result["remixes"]] == [
            "r-1994",
            "r-1999",
            "r-2010",
            "r-2022",
        ]

    def test_every_single_loads_and_remix_singles_join_the_remixes(
        self, service, mock_ytmusic
    ):
        mock_ytmusic.get_artist.return_value = {
            **SAMPLE_ARTIST_RAW,
            "singles": {
                "results": [],
                "browseId": "UCchannel",
                "params": "more-singles",
            },
        }
        releases = {
            "more-albums": [
                {
                    "browseId": "r-1994",
                    "title": "Space Cowboy (Remixes)",
                    "year": "1994",
                },
            ],
            "more-singles": [
                {
                    "browseId": "s-2017",
                    "title": "Cloud 9",
                    "year": "2017",
                    "type": "Single",
                },
                {
                    "browseId": "r-2006",
                    "title": "Runaway (Remixes)",
                    "year": "2006",
                    "type": "EP",
                },
                {
                    "browseId": "s-1993",
                    "title": "Too Young to Die",
                    "year": "1993",
                    "type": "Single",
                },
            ],
        }
        mock_ytmusic.get_artist_albums.side_effect = lambda _channel, params: releases[
            params
        ]

        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")

        assert [s["browseId"] for s in result["singles"]] == ["s-1993", "s-2017"]
        assert [r["browseId"] for r in result["remixes"]] == ["r-1994", "r-2006"]

    def test_falls_back_to_the_pages_albums(self, service, mock_ytmusic):
        mock_ytmusic.get_artist_albums.side_effect = Exception("albums down")
        result = service.get_artist("UCuAXFkgsw1L7xaCfnd5JJOw")
        assert [a["browseId"] for a in result["albums"]] == ["album-1"]
        assert result["albums"][0]["type"] == "album"

    def test_unknown_artist(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.side_effect = KeyError("contents")
        with pytest.raises(NotFoundError):
            service.get_artist("bad-id")

    def test_propagates_other_errors(self, service, mock_ytmusic):
        mock_ytmusic.get_artist.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            service.get_artist("bad-id")


# ---------------------------------------------------------------------------
# get_album_tracks
# ---------------------------------------------------------------------------

SAMPLE_ALBUM_RAW = {
    "title": "Whenever You Need Somebody",
    "type": "Album",
    "year": "1987",
    "thumbnails": [{"url": "https://example.com/album.jpg"}],
    "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
    "tracks": [
        {
            "videoId": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
            "duration": "3:33",
            "trackNumber": None,
            "isExplicit": False,
        },
        {
            "videoId": "vid2",
            "title": "Whenever You Need Somebody",
            "artists": [{"name": "Rick Astley", "id": "UCuAXFkgsw1L7xaCfnd5JJOw"}],
            "duration": "3:54",
            "trackNumber": None,
            "isExplicit": False,
        },
    ],
}


class TestGetAlbumTracks:
    def test_returns_album_metadata(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        album = service.get_album_tracks("album-id-1")["album"]
        assert album["title"] == "Whenever You Need Somebody"
        assert album["browseId"] == "album-id-1"
        assert album["type"] == "Album"
        assert album["artists"][0]["name"] == "Rick Astley"
        assert album["trackCount"] == 2

    def test_tracks_carry_the_album_and_its_cover(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        track = service.get_album_tracks("album-id-1")["tracks"][0]
        assert track["album"] == "Whenever You Need Somebody"
        assert track["albumId"] == "album-id-1"
        assert track["thumbnails"] == [{"url": "https://example.com/album.jpg"}]
        assert track["durationSeconds"] == 213

    def test_numbers_tracks_when_ytmusic_leaves_it_out(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        tracks = service.get_album_tracks("album-id-1")["tracks"]
        assert [t["trackNumber"] for t in tracks] == [1, 2]

    def test_caches_result(self, service, mock_ytmusic):
        mock_ytmusic.get_album.return_value = SAMPLE_ALBUM_RAW
        service.get_album_tracks("album-id-1")
        service.get_album_tracks("album-id-1")
        assert mock_ytmusic.get_album.call_count == 1

    def test_unknown_album(self, service, mock_ytmusic):
        mock_ytmusic.get_album.side_effect = KeyError("contents")
        with pytest.raises(NotFoundError):
            service.get_album_tracks("bad-id")

    def test_propagates_other_errors(self, service, mock_ytmusic):
        mock_ytmusic.get_album.side_effect = Exception("Album not found")
        with pytest.raises(Exception, match="Album not found"):
            service.get_album_tracks("bad-id")

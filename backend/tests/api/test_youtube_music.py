"""
Tests for FastAPI YouTube Music endpoints.

The library checks run against real rows in the test database, since what
matters is how the statuses of matching songs combine.
"""

import uuid

import pytest

from app.db.database import get_db_session
from app.db.models import DbSong
from app.exceptions import NotFoundError


def _add_library_song(*, video_id, status, title="Bohemian Rhapsody", artist="Queen"):
    song_id = str(uuid.uuid4())
    with get_db_session() as session:
        session.add(
            DbSong(
                id=song_id, title=title, artist=artist, video_id=video_id, status=status
            )
        )
        session.commit()
    return song_id


def _song(video_id="utwMHfDZ6SA", title="Bohemian Rhapsody", artists=("Queen",)):
    return {
        "videoId": video_id,
        "title": title,
        "artists": [{"name": name, "id": None} for name in artists],
        "artist": " feat. ".join(artists),
        "album": "A Night At The Opera",
        "albumId": "MPREb_1",
        "durationSeconds": 355,
        "isExplicit": False,
        "thumbnails": [],
    }


def _best_match(client):
    response = client.get("/api/youtube-music/search?q=bohemian+rhapsody")
    assert response.status_code == 200
    return response.json()["bestMatch"]


class TestYouTubeMusicSearch:
    def test_search_returns_grouped_results(self, client, mock_youtube_music_service):
        mock_youtube_music_service.search.return_value = {
            "songs": [
                _song(),
                _song("cover1", "Bohemian Rhapsody (Live)", ("Someone Else",)),
                _song("other1", "Killer Queen"),
            ],
            "artists": [{"browseId": "UCq", "name": "Queen", "thumbnails": []}],
        }

        data = client.get("/api/youtube-music/search?q=bohemian+rhapsody").json()

        assert data["bestMatch"]["videoId"] == "utwMHfDZ6SA"
        assert [s["videoId"] for s in data["otherVersions"]] == ["cover1"]
        assert [s["videoId"] for s in data["otherSongs"]] == ["other1"]
        assert data["artists"][0]["name"] == "Queen"
        assert data["topArtistId"] is None
        assert "error" not in data

    def test_search_passes_the_top_artist_on(self, client, mock_youtube_music_service):
        mock_youtube_music_service.search.return_value = {
            "songs": [],
            "artists": [{"browseId": "UCq", "name": "Queen", "thumbnails": []}],
            "topArtistId": "UCq",
        }

        data = client.get("/api/youtube-music/search?q=queen").json()

        assert data["topArtistId"] == "UCq"

    def test_search_requires_query(self, client):
        assert client.get("/api/youtube-music/search").status_code == 422

    def test_search_default_limit(self, client, mock_youtube_music_service):
        client.get("/api/youtube-music/search?q=test")
        mock_youtube_music_service.search.assert_called_once_with("test", limit=20)

    def test_search_validates_limit(self, client):
        assert (
            client.get("/api/youtube-music/search?q=test&limit=100").status_code == 422
        )
        assert client.get("/api/youtube-music/search?q=test&limit=0").status_code == 422

    def test_no_results(self, client, mock_youtube_music_service):
        mock_youtube_music_service.search.return_value = {"songs": [], "artists": []}

        data = client.get("/api/youtube-music/search?q=zzzz").json()

        assert data == {
            "bestMatch": None,
            "otherVersions": [],
            "otherSongs": [],
            "artists": [],
            "topArtistId": None,
        }

    def test_service_failure_is_a_502(self, client, mock_youtube_music_service):
        mock_youtube_music_service.search.side_effect = Exception("API Error")

        response = client.get("/api/youtube-music/search?q=test")

        assert response.status_code == 502
        assert "YouTube Music" in response.json()["detail"]


class TestLibraryField:
    def test_not_in_the_library(self, client, mock_youtube_music_service):
        assert _best_match(client)["library"] is None

    def test_ready_copy(self, client, mock_youtube_music_service):
        song_id = _add_library_song(video_id="utwMHfDZ6SA", status="processed")
        assert _best_match(client)["library"] == {"status": "ready", "songId": song_id}

    def test_processing_copy(self, client, mock_youtube_music_service):
        song_id = _add_library_song(video_id="utwMHfDZ6SA", status="processing")
        assert _best_match(client)["library"] == {
            "status": "processing",
            "songId": song_id,
        }

    def test_matches_by_artist_and_title(self, client, mock_youtube_music_service):
        song_id = _add_library_song(
            video_id="someOtherVid",
            status="processed",
            title="BOHEMIAN RHAPSODY",
            artist="queen",
        )
        assert _best_match(client)["library"]["songId"] == song_id

    def test_matches_a_song_stored_with_its_first_artist_only(
        self, client, mock_youtube_music_service
    ):
        mock_youtube_music_service.search.return_value = {
            "songs": [_song(title="Empire State of Mind", artists=("JAY-Z", "Alicia"))],
            "artists": [],
        }
        song_id = _add_library_song(
            video_id="old",
            status="processed",
            title="Empire State of Mind",
            artist="JAY-Z",
        )
        assert _best_match(client)["library"]["songId"] == song_id

    def test_only_copy_failed(self, client, mock_youtube_music_service):
        failed_id = _add_library_song(video_id="utwMHfDZ6SA", status="error")
        assert _best_match(client)["library"] == {
            "status": "failed",
            "songId": failed_id,
        }

    def test_failed_prefers_the_exact_video_match(
        self, client, mock_youtube_music_service
    ):
        _add_library_song(video_id="someOtherVid", status="error")
        exact_id = _add_library_song(video_id="utwMHfDZ6SA", status="error")
        assert _best_match(client)["library"]["songId"] == exact_id

    def test_working_copy_wins_over_a_failed_one(
        self, client, mock_youtube_music_service
    ):
        _add_library_song(video_id="utwMHfDZ6SA", status="error")
        working_id = _add_library_song(video_id="someOtherVid", status="processed")
        assert _best_match(client)["library"] == {
            "status": "ready",
            "songId": working_id,
        }

    def test_two_queries_for_the_whole_list(self, client, mock_youtube_music_service):
        mock_youtube_music_service.search.return_value = {
            "songs": [_song(f"vid{n}", f"Song {n}") for n in range(20)],
            "artists": [],
        }
        from sqlalchemy import event

        from app.db.database import engine

        statements = []

        def count(conn, cursor, statement, *args):
            if "FROM songs" in statement:
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", count)
        try:
            client.get("/api/youtube-music/search?q=songs")
        finally:
            event.remove(engine, "before_cursor_execute", count)

        assert len(statements) == 2


class TestSuggestions:
    def test_returns_suggestions(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_suggestions.return_value = ["don't stop me now"]

        response = client.get("/api/youtube-music/suggestions?q=dont+st")

        assert response.status_code == 200
        assert response.json() == ["don't stop me now"]

    def test_service_failure_is_a_502(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_suggestions.side_effect = Exception("down")
        assert client.get("/api/youtube-music/suggestions?q=x").status_code == 502


ARTIST = {
    "artist": {"id": "UCq", "name": "Queen", "thumbnails": []},
    "topSongs": [_song()],
    "hasMoreSongs": True,
    "albums": [],
    "singles": [],
    "remixes": [],
}


class TestYouTubeMusicArtist:
    def test_returns_artist_with_library_state(
        self, client, mock_youtube_music_service
    ):
        mock_youtube_music_service.get_artist.return_value = ARTIST
        song_id = _add_library_song(video_id="utwMHfDZ6SA", status="processed")

        response = client.get("/api/youtube-music/artist/UCq")

        assert response.status_code == 200
        data = response.json()
        assert data["artist"]["name"] == "Queen"
        assert data["hasMoreSongs"] is True
        assert data["topSongs"][0]["library"]["songId"] == song_id
        # The cached service result never carries a request's library state
        assert "library" not in ARTIST["topSongs"][0]

    def test_all_popular_songs(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_artist_songs.return_value = [
            _song(f"vid{n}", f"Song {n}") for n in range(12)
        ]

        response = client.get("/api/youtube-music/artist/UCq/songs")

        assert response.status_code == 200
        assert len(response.json()) == 12
        assert response.json()[0]["library"] is None

    @pytest.mark.parametrize("path", ["", "/songs"])
    def test_unknown_artist_is_a_404(self, client, mock_youtube_music_service, path):
        mock_youtube_music_service.get_artist.side_effect = NotFoundError("no artist")
        mock_youtube_music_service.get_artist_songs.side_effect = NotFoundError(
            "no artist"
        )
        assert client.get(f"/api/youtube-music/artist/nope{path}").status_code == 404

    def test_service_failure_is_a_502(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_artist.side_effect = Exception("down")
        assert client.get("/api/youtube-music/artist/UCq").status_code == 502


class TestYouTubeMusicAlbum:
    def test_returns_album_with_library_state(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_album_tracks.return_value = {
            "album": {"browseId": "MPREb_1", "title": "A Night At The Opera"},
            "tracks": [{**_song(), "trackNumber": 11}],
        }
        failed_id = _add_library_song(video_id="utwMHfDZ6SA", status="error")

        response = client.get("/api/youtube-music/album/MPREb_1/tracks")

        assert response.status_code == 200
        track = response.json()["tracks"][0]
        assert track["trackNumber"] == 11
        assert track["library"] == {"status": "failed", "songId": failed_id}

    def test_unknown_album_is_a_404(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_album_tracks.side_effect = NotFoundError("no")
        assert client.get("/api/youtube-music/album/nope/tracks").status_code == 404

    def test_service_failure_is_a_502(self, client, mock_youtube_music_service):
        mock_youtube_music_service.get_album_tracks.side_effect = Exception("down")
        assert client.get("/api/youtube-music/album/x/tracks").status_code == 502

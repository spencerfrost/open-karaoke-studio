"""Guards that a song's failure reason survives the SongResponse schema.

DbSong.to_dict() and SongResponse are two independent places that must both
declare errorMessage — response_model=SongResponse silently drops any key
to_dict() emits that the schema doesn't also declare.
"""

from app.db.models import DbSong
from tests.integration.conftest import _TestingSessionLocal


def _create_song(client, title="Test Song", artist="Test Artist", **kwargs):
    resp = client.post("/api/songs", json={"title": title, "artist": artist, **kwargs})
    assert resp.status_code in (200, 201)
    return resp.json()


def test_get_song_returns_error_message_when_present(client):
    song = _create_song(client, title="Broken Song", artist="Broken Artist")
    with _TestingSessionLocal() as session:
        db_song = session.get(DbSong, song["id"])
        db_song.status = "error"
        db_song.error_message = "Sign in to confirm your age"
        session.commit()

    resp = client.get(f"/api/songs/{song['id']}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["errorMessage"] == "Sign in to confirm your age"


def test_get_song_error_message_defaults_to_none(client):
    song = _create_song(client, title="Fine Song", artist="Fine Artist")

    resp = client.get(f"/api/songs/{song['id']}")

    assert resp.status_code == 200
    assert resp.json()["errorMessage"] is None

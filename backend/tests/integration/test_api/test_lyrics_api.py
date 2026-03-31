"""Integration tests for DB-backed /api/lyrics endpoints."""
import uuid


def _create_song(client, title="Lyric Song", artist="Lyrical Artist"):
    resp = client.post("/api/songs", json={"title": title, "artist": artist})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/lyrics/songs/{song_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_get_song_lyrics_song_not_found(client):
    resp = client.get(f"/api/lyrics/songs/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_song_lyrics_empty(client):
    song_id = _create_song(client)
    resp = client.get(f"/api/lyrics/songs/{song_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plainLyrics"] is None
    assert data["syncedLyrics"] is None
    assert data["hasAlignment"] is False


def test_get_song_lyrics_after_update(client):
    song_id = _create_song(client)
    client.post(
        f"/api/lyrics/songs/{song_id}?type=plain",
        json={"content": "Hello world"},
    )
    resp = client.get(f"/api/lyrics/songs/{song_id}")
    assert resp.status_code == 200
    assert resp.json()["plainLyrics"] == "Hello world"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/lyrics/songs/{song_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_update_lyrics_song_not_found(client):
    resp = client.post(
        f"/api/lyrics/songs/{uuid.uuid4()}?type=plain",
        json={"content": "Test"},
    )
    assert resp.status_code == 404


def test_update_lyrics_invalid_type(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=word_synced",
        json={"content": "Test"},
    )
    assert resp.status_code == 400


def test_update_plain_lyrics_success(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=plain",
        json={"content": "Plain lyrics here"},
    )
    assert resp.status_code == 200
    assert resp.json()["plainLyrics"] == "Plain lyrics here"


def test_update_synced_lyrics_success(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}?type=synced",
        json={"content": "[00:00.00] Line 1"},
    )
    assert resp.status_code == 200
    assert resp.json()["syncedLyrics"] == "[00:00.00] Line 1"


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/lyrics/songs/{song_id}/{type}
# ─────────────────────────────────────────────────────────────────────────────


def test_clear_lyrics_song_not_found(client):
    resp = client.delete(f"/api/lyrics/songs/{uuid.uuid4()}/plain")
    assert resp.status_code == 404


def test_clear_lyrics_invalid_type(client):
    song_id = _create_song(client)
    resp = client.delete(f"/api/lyrics/songs/{song_id}/invalid")
    assert resp.status_code == 400


def test_clear_plain_lyrics_success(client):
    song_id = _create_song(client)
    client.post(f"/api/lyrics/songs/{song_id}?type=plain", json={"content": "Delete me"})
    resp = client.delete(f"/api/lyrics/songs/{song_id}/plain")
    assert resp.status_code == 204
    data = client.get(f"/api/lyrics/songs/{song_id}").json()
    assert data["plainLyrics"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Removed endpoints — verify they no longer exist
# ─────────────────────────────────────────────────────────────────────────────


def test_activate_endpoint_gone(client):
    resp = client.patch("/api/lyrics/999999/activate")
    assert resp.status_code == 404


def test_delete_by_id_endpoint_gone(client):
    resp = client.delete("/api/lyrics/999999")
    assert resp.status_code == 404

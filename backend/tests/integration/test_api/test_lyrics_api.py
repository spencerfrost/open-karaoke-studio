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
    assert resp.json() == []


def test_get_song_lyrics_after_create(client):
    song_id = _create_song(client)
    # Create a lyrics version
    client.post(
        f"/api/lyrics/songs/{song_id}",
        json={"type": "plain", "content": "Hello world", "source": "manual"},
    )
    resp = client.get(f"/api/lyrics/songs/{song_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/lyrics/songs/{song_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_create_lyrics_song_not_found(client):
    resp = client.post(
        f"/api/lyrics/songs/{uuid.uuid4()}",
        json={"type": "plain", "content": "Test", "source": "manual"},
    )
    assert resp.status_code == 404


def test_create_lyrics_success(client):
    song_id = _create_song(client)
    resp = client.post(
        f"/api/lyrics/songs/{song_id}",
        json={"type": "synced", "content": "[00:00] Verse 1", "source": "manual"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "synced"
    assert "id" in data


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/lyrics/{lyrics_id}/activate
# ─────────────────────────────────────────────────────────────────────────────


def test_activate_lyrics_not_found(client):
    resp = client.patch("/api/lyrics/999999/activate")
    assert resp.status_code == 404


def test_activate_lyrics_success(client):
    song_id = _create_song(client)
    create_resp = client.post(
        f"/api/lyrics/songs/{song_id}",
        json={"type": "plain", "content": "Lyrics", "source": "manual", "isActive": False},
    )
    lyrics_id = create_resp.json()["id"]
    resp = client.patch(f"/api/lyrics/{lyrics_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["isActive"] is True


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/lyrics/{lyrics_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_delete_lyrics_not_found(client):
    resp = client.delete("/api/lyrics/999999")
    assert resp.status_code == 404


def test_delete_lyrics_success(client):
    song_id = _create_song(client)
    create_resp = client.post(
        f"/api/lyrics/songs/{song_id}",
        json={"type": "plain", "content": "Delete me", "source": "manual"},
    )
    lyrics_id = create_resp.json()["id"]
    resp = client.delete(f"/api/lyrics/{lyrics_id}")
    assert resp.status_code == 204

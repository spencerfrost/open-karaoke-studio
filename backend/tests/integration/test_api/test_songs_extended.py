"""Extended integration tests for songs API — covers routes not in test_songs_api.py."""
import uuid


def _create_song(client, title="Test Song", artist="Test Artist", **kwargs):
    resp = client.post("/api/songs", json={"title": title, "artist": artist, **kwargs})
    assert resp.status_code in (200, 201)
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/artists
# ─────────────────────────────────────────────────────────────────────────────


def test_get_artists_empty(client):
    response = client.get("/api/songs/artists")
    assert response.status_code == 200
    data = response.json()
    assert "artists" in data
    assert "pagination" in data


def test_get_artists_returns_unique_artists(client):
    _create_song(client, title="Song A1", artist="ArtistA")
    _create_song(client, title="Song A2", artist="ArtistA")
    _create_song(client, title="Song B1", artist="ArtistB")

    response = client.get("/api/songs/artists")
    assert response.status_code == 200
    names = [a["name"] for a in response.json()["artists"]]
    assert names.count("ArtistA") == 1
    assert "ArtistB" in names


def test_get_artists_with_search_filter(client):
    _create_song(client, title="Track", artist="UniqueArtistXYZ")
    _create_song(client, title="Other", artist="OtherArtist")

    response = client.get("/api/songs/artists?search=UniqueArtistXYZ")
    assert response.status_code == 200
    names = [a["name"] for a in response.json()["artists"]]
    assert "UniqueArtistXYZ" in names
    assert "OtherArtist" not in names


def test_get_artists_with_limit_and_offset(client):
    for i in range(5):
        _create_song(client, title=f"Track {i}", artist=f"Artist{i:02d}")

    resp_limited = client.get("/api/songs/artists?limit=2&offset=0")
    assert resp_limited.status_code == 200
    assert len(resp_limited.json()["artists"]) <= 2
    assert resp_limited.json()["pagination"]["hasMore"] is True


def test_get_artists_first_letter(client):
    _create_song(client, title="Track", artist="Zeppelin")
    response = client.get("/api/songs/artists?search=Zeppelin")
    assert response.status_code == 200
    artists = response.json()["artists"]
    zeppelin = next((a for a in artists if a["name"] == "Zeppelin"), None)
    assert zeppelin is not None
    assert zeppelin["firstLetter"] == "Z"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/by-artist/{artist_name}
# ─────────────────────────────────────────────────────────────────────────────


def test_get_songs_by_artist(client):
    artist = f"SoloArtist-{uuid.uuid4().hex[:6]}"
    _create_song(client, title="Hit 1", artist=artist)
    _create_song(client, title="Hit 2", artist=artist)

    response = client.get(f"/api/songs/by-artist/{artist}")
    assert response.status_code == 200
    data = response.json()
    assert "songs" in data
    assert all(s["artist"] == artist for s in data["songs"])
    assert len(data["songs"]) == 2


def test_get_songs_by_artist_not_found_returns_empty(client):
    response = client.get("/api/songs/by-artist/CompletelyUnknownArtist999")
    assert response.status_code == 200
    assert response.json()["songs"] == []


def test_get_songs_by_artist_pagination(client):
    artist = f"PaginatedArtist-{uuid.uuid4().hex[:6]}"
    for i in range(5):
        _create_song(client, title=f"Song {i}", artist=artist)

    resp = client.get(f"/api/songs/by-artist/{artist}?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["songs"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/search (group_by_artist path)
# ─────────────────────────────────────────────────────────────────────────────


def test_search_songs_group_by_artist(client):
    artist = f"GroupArtist-{uuid.uuid4().hex[:6]}"
    _create_song(client, title="Grouped Track 1", artist=artist)
    _create_song(client, title="Grouped Track 2", artist=artist)

    response = client.get(f"/api/songs/search?q={artist}&group_by_artist=true")
    assert response.status_code == 200
    data = response.json()
    assert "artists" in data
    assert any(a["artist"] == artist for a in data["artists"])


def test_search_songs_with_limit(client):
    response = client.get("/api/songs/search?q=Song&limit=2")
    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/{song_id}/chords
# ─────────────────────────────────────────────────────────────────────────────


def test_get_chords_song_not_found(client):
    response = client.get(f"/api/songs/{uuid.uuid4()}/chords")
    assert response.status_code == 404


def test_get_chords_no_chord_data(client):
    song = _create_song(client, title="No Chords Song", artist="Chordless")
    response = client.get(f"/api/songs/{song['id']}/chords")
    # Song exists but has no chord data
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/songs/{song_id} — with lyrics update
# ─────────────────────────────────────────────────────────────────────────────


def test_update_song_with_plain_lyrics(client):
    song = _create_song(client, title="Lyrics Song", artist="Lyrical")
    resp = client.patch(
        f"/api/songs/{song['id']}",
        json={"plainLyrics": "Is this the real life?"},
    )
    assert resp.status_code == 200


def test_update_song_with_synced_lyrics(client):
    song = _create_song(client, title="Synced Song", artist="SyncedArtist")
    resp = client.patch(
        f"/api/songs/{song['id']}",
        json={"syncedLyrics": "[00:00.06] Is this the real life?"},
    )
    assert resp.status_code == 200


def test_update_song_clear_lyrics(client):
    song = _create_song(client, title="Clear Lyrics Song", artist="ClearArtist")
    # Set then clear lyrics
    client.patch(f"/api/songs/{song['id']}", json={"plainLyrics": "Some lyrics"})
    resp = client.patch(f"/api/songs/{song['id']}", json={"plainLyrics": None})
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/{song_id}/thumbnail
# ─────────────────────────────────────────────────────────────────────────────


def test_get_thumbnail_song_not_found(client):
    response = client.get(f"/api/songs/{uuid.uuid4()}/thumbnail")
    assert response.status_code == 404


def test_get_thumbnail_no_file(client):
    song = _create_song(client, title="No Thumbnail", artist="Thumbnailless")
    response = client.get(f"/api/songs/{song['id']}/thumbnail")
    # Song exists but has no thumbnail file
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/songs/{song_id}/download/{track_type}
# ─────────────────────────────────────────────────────────────────────────────


def test_download_invalid_track_type(client):
    song = _create_song(client, title="Download Song", artist="Downloader")
    response = client.get(f"/api/songs/{song['id']}/download/kazoo")
    assert response.status_code == 400


def test_download_song_not_found(client):
    response = client.get(f"/api/songs/{uuid.uuid4()}/download/vocals")
    assert response.status_code == 404


def test_download_track_missing_file(client):
    song = _create_song(client, title="Track Missing", artist="NoFiles")
    response = client.get(f"/api/songs/{song['id']}/download/vocals")
    # Song dir exists (created by POST) but vocals file doesn't
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/songs/{song_id}/reprocess
# ─────────────────────────────────────────────────────────────────────────────


def test_reprocess_song_not_found(client):
    response = client.post(
        f"/api/songs/{uuid.uuid4()}/reprocess",
        json={"engine_type": "demucs"},
    )
    assert response.status_code == 404


def test_reprocess_song_no_original_file(client):
    song = _create_song(client, title="Reprocess Test", artist="Reprocessor")
    response = client.post(
        f"/api/songs/{song['id']}/reprocess",
        json={"engine_type": "demucs"},
    )
    # Song exists but no original.mp3 → 400
    assert response.status_code == 400

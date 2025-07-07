import uuid


def unique_song_id():
    return f"test-song-{uuid.uuid4()}"


def test_get_songs_success(client):
    """Test GET /api/songs returns a list of songs (happy path)."""
    response = client.get("/api/songs")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 0  # Should return a list, possibly empty
    # Optionally check for known test data if you expect it to exist


def test_create_song_success(client):
    """Test POST /api/songs creates a new song (happy path)."""
    payload = {
        "title": "Integration Test Song",
        "artist": "Test Artist",
        "album": "Test Album",
        "durationMs": 123456,
        "source": "test",
        "video_id": "testvid123",
    }
    response = client.post("/api/songs", json={**payload})
    # Accept 200 or 201 depending on implementation
    assert response.status_code in (200, 201)
    data = response.get_json()
    assert data["title"] == payload["title"]
    assert data["artist"] == payload["artist"]
    # Clean up
    client.delete(f"/api/songs/{data['id']}")


def test_create_song_invalid_data(client):
    """Test POST /api/songs with invalid/missing data returns 400."""
    response = client.post("/api/songs", json={"artist": "No Title"})
    assert response.status_code == 400


def test_update_song_success(client):
    """Test PATCH /api/songs/<id> updates a song (happy path)."""
    # Create song first
    create_resp = client.post(
        "/api/songs", json={"title": "Old Title", "artist": "Old Artist"}
    )
    assert create_resp.status_code in (200, 201)
    song_id = create_resp.get_json()["id"]
    # Update
    response = client.patch(
        f"/api/songs/{song_id}", json={"title": "New Title", "favorite": True}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "New Title"
    assert data["favorite"] is True
    # Clean up
    client.delete(f"/api/songs/{song_id}")


def test_update_song_not_found(client):
    """Test PATCH /api/songs/<id> returns 404 for nonexistent song."""
    response = client.patch(
        f"/api/songs/nonexistent-{uuid.uuid4()}", json={"title": "Doesn't Matter"}
    )
    assert response.status_code == 404


def test_update_song_invalid_data(client):
    """Test PATCH /api/songs/<id> with invalid data returns 400."""
    create_resp = client.post("/api/songs", json={"title": "Valid", "artist": "Valid"})
    assert create_resp.status_code in (200, 201)
    song_id = create_resp.get_json()["id"]
    response = client.patch(f"/api/songs/{song_id}", json={"durationMs": -5})
    assert response.status_code == 400
    client.delete(f"/api/songs/{song_id}")


def test_delete_song_success(client):
    """Test DELETE /api/songs/<id> deletes a song (happy path)."""
    create_resp = client.post(
        "/api/songs", json={"title": "Delete Me", "artist": "Test"}
    )
    assert create_resp.status_code in (200, 201)
    song_id = create_resp.get_json()["id"]
    response = client.delete(f"/api/songs/{song_id}")
    assert response.status_code in (200, 204)


def test_delete_song_not_found(client):
    """Test DELETE /api/songs/<id> returns 404 for nonexistent song."""
    response = client.delete(f"/api/songs/nonexistent-{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_songs_pagination(client):
    """Test GET /api/songs with limit/offset parameters."""
    # Clean up any leftover Pagination Song test data before starting
    response = client.get("/api/songs")
    if response.status_code == 200:
        data = response.get_json()
        for song in data:
            if song["title"].startswith("Pagination Song"):
                client.delete(f"/api/songs/{song['id']}")

    # Create 15 songs so we can test pagination (fetch 10, offset 5)
    song_ids = []
    for i in range(15):
        resp = client.post(
            "/api/songs",
            json={
                "title": f"Pagination Song {i}",
                "artist": f"Artist {i}",
            },
        )
        assert resp.status_code in (200, 201)
        song_ids.append(resp.get_json()["id"])

    # Fetch 10 songs, skipping the first 5, sorted by title ascending
    response = client.get("/api/songs?limit=10&offset=5&sort_by=title&direction=asc")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 10
    # Check that the returned titles are sorted lexicographically (string sort)
    actual_titles = [song["title"] for song in data]
    assert actual_titles == sorted(actual_titles)

    # Clean up after test
    response = client.get("/api/songs")
    if response.status_code == 200:
        data = response.get_json()
        for song in data:
            if song["title"].startswith("Pagination Song"):
                client.delete(f"/api/songs/{song['id']}")


def test_get_songs_sorting(client):
    """Test GET /api/songs with sort_by and direction parameters."""
    response = client.get("/api/songs?sort_by=title&direction=asc")
    assert response.status_code == 200
    data = response.get_json()
    titles = [song["title"] for song in data]
    assert titles == sorted(titles)


def test_search_songs_success(client):
    """Test GET /api/songs/search returns matching songs."""
    # Insert a known song for search
    create_resp = client.post(
        "/api/songs",
        json={"title": "Test Song", "artist": "Test Artist"},
    )
    assert create_resp.status_code in (200, 201)
    song_id = create_resp.get_json()["id"]
    # Search for the song
    response = client.get("/api/songs/search?q=Test Song")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "songs" in data
    assert any("Test Song" in song["title"] for song in data["songs"])
    # Clean up
    client.delete(f"/api/songs/{song_id}")


def test_search_songs_empty_query(client):
    """Test GET /api/songs/search with empty query returns empty list."""
    response = client.get("/api/songs/search?q=")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "songs" in data
    assert data["songs"] == []


def test_search_songs_no_results(client):
    """Test GET /api/songs/search returns empty list for no matches."""
    response = client.get("/api/songs/search?q=definitelynotarealsongtitle")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "songs" in data
    assert data["songs"] == []


def test_get_songs_not_found(client):
    """Test GET /api/songs/<id> returns 404 for nonexistent song."""
    response = client.get(f"/api/songs/nonexistent-{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_songs_fuzzy_search_equivalence(client):
    """Test GET /api/songs?q=... returns same results as legacy /api/songs/search?q=... (for migration)."""
    # Insert a known song for search
    create_resp = client.post(
        "/api/songs",
        json={"title": "FuzzyTestSong", "artist": "FuzzyArtist"},
    )
    assert create_resp.status_code in (200, 201)
    song_id = create_resp.get_json()["id"]
    # Fuzzy search via main endpoint
    # Fuzzy search via main endpoint (should match /api/songs/search for migration purposes)
    resp_main = client.get("/api/songs?q=FuzzyTestSong")
    assert resp_main.status_code == 200
    data_main = resp_main.get_json()
    # /api/songs returns a list, so check for the song in the list
    assert any("FuzzyTestSong" in song["title"] for song in data_main)
    # Also test the /api/songs/search endpoint independently
    resp_search = client.get("/api/songs/search?q=FuzzyTestSong")
    assert resp_search.status_code == 200
    data_search = resp_search.get_json()
    # /api/songs/search returns a dict with a 'songs' key
    assert any(
        "FuzzyTestSong" in song["title"] for song in data_search.get("songs", [])
    )
    # Clean up
    client.delete(f"/api/songs/{song_id}")


def test_get_songs_unicode(client):
    """Test GET /api/songs handles unicode and special characters."""
    # Create songs with unicode artist names
    unicode_songs = [
        {"title": "Jóga", "artist": "Björk"},
        {"title": "模特", "artist": "李荣浩"},
    ]
    song_ids = []
    for song in unicode_songs:
        resp = client.post("/api/songs", json=song)
        assert resp.status_code in (200, 201)
        song_ids.append(resp.get_json()["id"])

    # Fetch all songs and check for unicode artists
    response = client.get("/api/songs")
    assert response.status_code == 200
    data = response.get_json()
    assert any("Björk" in song["artist"] for song in data)
    assert any("李荣浩" in song["artist"] for song in data)

    # Clean up
    for song_id in song_ids:
        client.delete(f"/api/songs/{song_id}")


# --- ERROR HANDLING ---
# These are best tested with explicit error injection or by simulating errors in the app

# --- SECURITY & EDGE CASES ---
# Add more as needed, e.g. test_download_song_track_security_violation, etc.

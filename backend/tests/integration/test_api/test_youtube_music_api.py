import pytest
from flask import Flask

from backend.app.api.youtube_music import youtube_music_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(youtube_music_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_search_youtube_music_success(monkeypatch, client):
    class DummyService:
        def search_songs(self, query, limit=10):
            return [
                {
                    "videoId": "abc123",
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "duration": "3:00",
                    "album": "Test Album",
                    "thumbnails": [],
                }
            ]

    monkeypatch.setattr(
        "backend.app.api.youtube_music.YouTubeMusicService", DummyService
    )
    resp = client.get("/api/youtube-music/search?q=test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["results"]
    assert data["results"][0]["title"] == "Test Song"
    assert data["error"] is None


def test_search_youtube_music_missing_query(client):
    resp = client.get("/api/youtube-music/search")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert data["error"].startswith("Missing query parameter")


def test_search_youtube_music_service_error(monkeypatch, client):
    class FailingService:
        def search_songs(self, query, limit=10):
            raise Exception("ytmusicapi error")

    monkeypatch.setattr(
        "backend.app.api.youtube_music.YouTubeMusicService", FailingService
    )
    resp = client.get("/api/youtube-music/search?q=test")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["results"] == []
    assert "ytmusicapi error" in data["error"]

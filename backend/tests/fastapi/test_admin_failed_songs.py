"""Tests for the admin failed songs list and when songs are marked failed."""

from datetime import datetime

import pytest
from tests.fastapi.conftest import _TestingSessionLocal

from app.db.models import DbSong
from app.repositories.song_repository import SongRepository


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    yield session
    session.close()


def _add(db, song_id, status="processed", failed_at=None, error=None):
    db.add(
        DbSong(
            id=song_id,
            title=song_id,
            artist="Queen",
            status=status,
            failed_at=failed_at,
            error_message=error,
        )
    )
    db.commit()


class TestListFailedSongs:
    def test_only_failed_songs_most_recent_first(self, client, db):
        _add(db, "fine")
        _add(db, "old", "error", datetime(2026, 10, 1), "HTTP Error 403")
        _add(db, "new", "error", datetime(2026, 10, 8), "CUDA out of memory")
        _add(db, "untimed", "error", None, "Processing was interrupted")

        resp = client.get("/api/admin/songs/failed")

        assert resp.status_code == 200
        songs = resp.json()
        assert [s["id"] for s in songs] == ["new", "old", "untimed"]
        assert songs[0]["errorMessage"] == "CUDA out of memory"
        assert songs[0]["failedAt"] == "2026-10-08T00:00:00"
        assert songs[2]["failedAt"] is None

    def test_empty(self, client):
        resp = client.get("/api/admin/songs/failed")
        assert resp.status_code == 200
        assert resp.json() == []


class TestFailedAtFollowsStatus:
    def test_failing_stamps_it(self, db):
        _add(db, "song")
        song = SongRepository(db).update("song", status="error", error_message="x")
        assert song.failed_at is not None

    def test_restarting_clears_it(self, db):
        _add(db, "song", "error", datetime(2026, 10, 1))
        song = SongRepository(db).update("song", status="processing")
        assert song.failed_at is None

    def test_other_updates_leave_it(self, db):
        _add(db, "song", "error", datetime(2026, 10, 1))
        song = SongRepository(db).update("song", title="Renamed")
        assert song.failed_at == datetime(2026, 10, 1)

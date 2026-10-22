"""
Fixtures for Celery job tests.

Jobs open their own sessions with get_db_session(), which writes to the shared throwaway
database set up in tests/conftest.py. Tests seed rows with `add_song` and read back what
the job saved with `fetch_song`.
"""

from unittest.mock import Mock, patch

import pytest

from app.db.database import SessionLocal
from app.db.models import DbSong


@pytest.fixture
def db():
    """Session on the shared test database, for seeding and inspecting rows."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def add_song(db):
    """Insert a song row; fields default to a minimal processed song."""

    def _add(song_id, **fields):
        fields.setdefault("title", "Blackbird")
        fields.setdefault("artist", "The Beatles")
        fields.setdefault("status", "processed")
        db.add(DbSong(id=song_id, **fields))
        db.commit()
        return song_id

    return _add


@pytest.fixture
def fetch_song():
    """Read a song as the job left it, from a fresh session."""

    def _fetch(song_id):
        with SessionLocal() as session:
            return session.get(DbSong, song_id)

    return _fetch


@pytest.fixture
def library(tmp_path):
    """Point the jobs' song library at a temp folder."""
    with patch("app.config.get_config", return_value=Mock(BASE_LIBRARY_DIR=tmp_path)):
        yield tmp_path

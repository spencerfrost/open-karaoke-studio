"""
Pytest configuration and shared fixtures for Open Karaoke Studio backend tests.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI

# Point the app's global engine at a throwaway SQLite file BEFORE any app
# module is imported: app/db/database.py builds its engine from
# config.DATABASE_URL at import time, and code that uses SessionLocal or
# get_db_session() directly (jobs, repositories, several API modules) bypasses
# FastAPI dependency overrides entirely. Without this, those paths write to
# the real development database.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="okstudio-tests-", suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

# Same for the song library: BaseConfig reads LIBRARY_DIR at import time, and
# endpoints like POST /api/songs create a song folder through FileService. Left
# unset, every test run leaves empty folders in the real library.
_TEST_LIBRARY_DIR = tempfile.mkdtemp(prefix="okstudio-tests-library-")
os.environ["LIBRARY_DIR"] = _TEST_LIBRARY_DIR

# Add the backend path for imports
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.database import SessionLocal as _SessionLocal
from app.db.database import engine as _global_engine
from app.db.models import Base

# Alembic manages the real schema, but the throwaway test database needs its
# tables created directly.
Base.metadata.create_all(_global_engine)


@pytest.fixture(autouse=True)
def _clean_global_db():
    """Truncate the global engine's tables after each test.

    Covers any code path that wrote through SessionLocal/get_db_session
    instead of an overridden get_db dependency.
    """
    yield
    with _global_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


def pytest_sessionfinish(session, exitstatus):
    """Remove the throwaway test database file (and SQLite sidecars) and library."""
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(_TEST_DB_PATH + suffix)
        except FileNotFoundError:
            pass
    shutil.rmtree(_TEST_LIBRARY_DIR, ignore_errors=True)


@pytest.fixture(scope="function")
def test_db_session():
    """Session on the shared test database; _clean_global_db empties it afterwards."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_test_app():
    """
    Create a minimal FastAPI app for testing that includes all routers.
    This is a factory function to allow fresh app instances for tests.
    """
    from fastapi import WebSocket
    from fastapi.middleware.cors import CORSMiddleware

    from app.api import (
        admin_router,
        albums_router,
        artists_router,
        demo_router,
        health_router,
        host_settings_router,
        jobs_router,
        lyrics_router,
        musicbrainz_router,
        performance_history_router,
        queue_router,
        session_playlist_router,
        sessions_router,
        songs_router,
        users_router,
        youtube_music_router,
        youtube_router,
    )
    from app.ws import (
        SessionConnectionManager,
        websocket_jobs_endpoint,
        websocket_unified_session_endpoint,
    )

    test_app = FastAPI(
        title="Open Karaoke Studio API (Test)",
        version="2.0.0-test",
    )
    manager = SessionConnectionManager()
    test_app.state.session_manager = manager

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routers
    test_app.include_router(admin_router)
    test_app.include_router(albums_router)
    test_app.include_router(artists_router)
    test_app.include_router(demo_router)
    test_app.include_router(health_router)
    test_app.include_router(songs_router)
    test_app.include_router(jobs_router)
    test_app.include_router(sessions_router)
    test_app.include_router(queue_router)
    test_app.include_router(youtube_router)
    test_app.include_router(youtube_music_router)
    test_app.include_router(lyrics_router)
    test_app.include_router(users_router)
    test_app.include_router(performance_history_router)
    test_app.include_router(host_settings_router)
    test_app.include_router(musicbrainz_router)
    test_app.include_router(session_playlist_router)

    # WebSocket routes
    @test_app.websocket("/ws/jobs")
    async def jobs_ws(websocket: WebSocket):
        await websocket_jobs_endpoint(websocket, manager)

    # Must mirror the production registration in app/main.py exactly - this route
    # previously declared a device_id query param that main.py did not, which hid a
    # production bug from every test.
    @test_app.websocket("/ws/session/{session_id}")
    async def unified_session_ws(websocket: WebSocket, session_id: str):
        await websocket_unified_session_endpoint(websocket, session_id, manager)

    # Root endpoint for testing
    @test_app.get("/")
    async def root():
        return {
            "message": "Open Karaoke Studio FastAPI Backend",
            "version": "2.0.0",
            "api_endpoints": {
                "songs": "/api/songs",
                "jobs": "/api/jobs",
                "sessions": "/api/sessions",
                "queue": "/api/karaoke-queue",
                "youtube": "/api/youtube",
                "youtube_music": "/api/youtube-music",
                "lyrics": "/api/lyrics",
                "users": "/api/users",
            },
            "websockets": {
                "jobs": "/ws/jobs",
                "session": "/ws/session/{session_id}",
            },
        }

    return test_app


@pytest.fixture(scope="function")
def temp_library_dir():
    """Create temporary directory for file operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

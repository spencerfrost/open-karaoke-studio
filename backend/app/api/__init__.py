"""
FastAPI Routers for Open Karaoke Studio

This package contains all API endpoint routers organized by domain.
"""

from .health import router as health_router
from .jobs import router as jobs_router
from .karaoke_queue import router as queue_router
from .lyrics import router as lyrics_router
from .metadata import router as metadata_router
from .sessions import router as sessions_router
from .songs import router as songs_router
from .users import router as users_router
from .youtube import router as youtube_router
from .youtube_music import router as youtube_music_router

__all__ = [
    "health_router",
    "songs_router",
    "jobs_router",
    "sessions_router",
    "queue_router",
    "youtube_router",
    "youtube_music_router",
    "metadata_router",
    "lyrics_router",
    "users_router",
]

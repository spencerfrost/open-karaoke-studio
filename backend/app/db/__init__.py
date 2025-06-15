"""
Database models and connection management for Open Karaoke Studio.
"""
# Database infrastructure
from .database import engine, init_db, DBSessionMiddleware, SessionLocal, get_db_session, ensure_db_schema, force_db_sync

# Song operations and business logic
from .song_operations import (
    get_all_songs,
    get_song,
    create_or_update_song,
    delete_song,
    update_song_audio_paths,
    update_song_with_metadata,
    update_song_thumbnail,
    get_artists_with_counts,
    get_artists_total_count,
    get_songs_by_artist,
    search_songs_paginated,
    sync_songs_with_filesystem
)

# Models
from .models import *

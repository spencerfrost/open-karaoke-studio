# backend/app/database.py
"""
Database utility functions
"""

from contextlib import contextmanager
from typing import Iterator, List, Optional
import traceback
from pathlib import Path
import sqlite3

from sqlalchemy.orm import Session
from . import models
from .models import DbSong, SongMetadata
from . import file_management
from . import config


def ensure_db_schema():
    """Ensure the database schema is up to date with the latest model definitions"""
    # Connect directly to SQLite to check and add columns
    db_path = Path(models.DATABASE_URL.replace('sqlite:///', ''))
    if not db_path.exists():
        # If DB doesn't exist yet, SQLAlchemy will create it with the latest schema
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the songs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
        if cursor.fetchone() is None:
            # Table doesn't exist yet, SQLAlchemy will create it
            conn.close()
            return
            
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(songs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add lyrics column if it doesn't exist
        if "lyrics" not in columns:
            print("Adding lyrics column to songs table...")
            cursor.execute("ALTER TABLE songs ADD COLUMN lyrics TEXT")
        
        # Add synced_lyrics column if it doesn't exist
        if "synced_lyrics" not in columns:
            print("Adding synced_lyrics column to songs table...")
            cursor.execute("ALTER TABLE songs ADD COLUMN synced_lyrics TEXT")
        
        # Commit changes
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"SQLite error during schema check: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


@contextmanager
def get_db() -> Iterator[Session]:
    """Get a database session with automatic closing"""
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_or_update_song(song_id: str, metadata: SongMetadata, db: Optional[Session] = None) -> DbSong:
    """
    Create or update a song in the database from a SongMetadata object
    
    Args:
        song_id: The song directory name / ID
        metadata: The SongMetadata object
        db: Optional database session (will create one if not provided)
        
    Returns:
        The created or updated DbSong object
    """
    # Get paths for files
    song_dir = file_management.get_song_dir(song_id)
    vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(file_management.VOCALS_SUFFIX)
    instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(file_management.INSTRUMENTAL_SUFFIX)
    
    # Find original file using glob pattern
    original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
    original_pattern = f"{song_id}{original_suffix}.*"
    original_file = next(song_dir.glob(original_pattern), None)
    
    # Convert absolute paths to relative paths from library root
    vocals_path_rel = str(vocals_path.relative_to(config.BASE_LIBRARY_DIR)) if vocals_path.exists() else None
    instrumental_path_rel = str(instrumental_path.relative_to(config.BASE_LIBRARY_DIR)) if instrumental_path.exists() else None
    original_path_rel = str(original_file.relative_to(config.BASE_LIBRARY_DIR)) if original_file and original_file.exists() else None
    
    # Create DbSong from metadata and paths
    song = models.DbSong.from_metadata(
        song_id=song_id,
        metadata=metadata,
        vocals_path=vocals_path_rel,
        instrumental_path=instrumental_path_rel,
        original_path=original_path_rel
    )
    
    close_session = False
    if db is None:
        close_session = True
        db = models.SessionLocal()
    
    try:
        # Check if song already exists
        existing_song = db.query(models.DbSong).filter(models.DbSong.id == song_id).first()
        
        if existing_song:
            # Update existing song
            for key, value in song.__dict__.items():
                if key != '_sa_instance_state' and hasattr(existing_song, key):
                    setattr(existing_song, key, value)
            db.commit()
            return existing_song
        else:
            # Create new song
            db.add(song)
            db.commit()
            return song
    except Exception as e:
        db.rollback()
        print(f"Error creating/updating song in database: {e}")
        traceback.print_exc()
        return None
    finally:
        if close_session:
            db.close()


def get_song(song_id: str, db: Optional[Session] = None) -> Optional[DbSong]:
    """Get a song from the database by ID"""
    close_session = False
    if db is None:
        close_session = True
        db = models.SessionLocal()
    
    try:
        return db.query(models.DbSong).filter(models.DbSong.id == song_id).first()
    finally:
        if close_session:
            db.close()


def get_all_songs(db: Optional[Session] = None) -> List[DbSong]:
    """Get all songs from the database"""
    close_session = False
    if db is None:
        close_session = True
        db = models.SessionLocal()
    
    try:
        return db.query(models.DbSong).all()
    finally:
        if close_session:
            db.close()


def sync_songs_with_filesystem() -> int:
    """
    Synchronize the database with the filesystem
    
    Reads all song metadata from the karaoke_library and ensures it's in the database.
    Returns the number of songs added or updated.
    """
    song_ids = file_management.get_processed_songs()
    count = 0
    
    with get_db() as db:
        for song_id in song_ids:
            metadata = file_management.read_song_metadata(song_id)
            if metadata:
                if create_or_update_song(song_id, metadata, db):
                    count += 1
    
    return count


# Call this function at import time to ensure schema is up-to-date
ensure_db_schema()
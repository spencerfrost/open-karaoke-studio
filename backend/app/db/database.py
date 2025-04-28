# backend/app/db/database.py
"""
Database utility functions
"""

from contextlib import contextmanager
from typing import Iterator, List, Optional
import traceback
from pathlib import Path
import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from .models import Base, DbSong, SongMetadata
from ..services import file_management
from ..config import Config as config

# Create the database engine
import os
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'karaoke.db')}"
print(f"Database URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize the database
def init_db():
    """Initialize the database with tables from models"""
    Base.metadata.create_all(bind=engine)

# SQLAlchemy session middleware for route handlers (placeholder, can be implemented if needed)
class DBSessionMiddleware:
    """Middleware to manage database sessions in web requests"""
    pass


def ensure_db_schema():
    """Ensure the database schema is up to date with the latest model definitions"""
    # Connect directly to SQLite to check and add columns
    db_path = Path(os.path.join(BASE_DIR, "karaoke.db"))
    if not db_path.exists():
        logging.info("Creating database schema from scratch")
        Base.metadata.create_all(bind=engine)
        return

    # If DB exists, check for missing columns
    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        table_name = table.name
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        missing_columns = set()
        
        for column in table.columns:
            if column.name not in existing_columns:
                missing_columns.add(column.name)
                
        if missing_columns:
            logging.info(f"Missing columns in {table_name}: {missing_columns}")
            # Add columns using direct SQL
            with engine.connect() as connection:
                for col_name in missing_columns:
                    col = table.columns[col_name]
                    col_type = col.type.compile(dialect=engine.dialect)
                    nullable = "" if col.nullable else "NOT NULL"
                    default = f"DEFAULT {col.default.arg}" if col.default is not None and col.default.arg is not None else ""
                    
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}".strip()
                    try:
                        connection.execute(sql)
                        logging.info(f"Added column: {sql}")
                    except Exception as e:
                        logging.error(f"Error adding column {col_name}: {e}")


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Get a database session with automatic closing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_all_songs() -> List[DbSong]:
    """Get all songs from the database"""
    try:
        with get_db_session() as session:
            songs = session.query(DbSong).all()
            return songs
    except Exception as e:
        logging.error(f"Error getting songs from database: {e}")
        return []


def get_song(song_id: str) -> Optional[DbSong]:
    """Get a song by ID from the database"""
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()
            return song
    except Exception as e:
        logging.error(f"Error getting song {song_id} from database: {e}")
        return None


def create_or_update_song(song_id: str, metadata: SongMetadata) -> Optional[DbSong]:
    """Create or update a song in the database from metadata"""

    song_dir = file_management.get_song_dir(song_id)
    vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(file_management.VOCALS_SUFFIX)
    instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(file_management.INSTRUMENTAL_SUFFIX)
    original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
    original_pattern = f"{song_id}{original_suffix}.*"
    original_file = next(song_dir.glob(original_pattern), None)

    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not db_song:
                # Create new song
                db_song = DbSong(id=song_id)
                session.add(db_song)

            # Convert metadata to a dictionary and filter out None values
            metadata_dict = {
                "title": metadata.title,
                "artist": metadata.artist,
                "duration": metadata.duration,
                "favorite": metadata.favorite if hasattr(metadata, 'favorite') else None,
                "date_added": metadata.dateAdded,
                "cover_art_path": metadata.coverArt if hasattr(metadata, 'coverArt') else None,
                "thumbnail_path": metadata.thumbnail if hasattr(metadata, 'thumbnail') else None,
                "vocals_path": str(vocals_path.relative_to(config.BASE_LIBRARY_DIR)) if vocals_path.exists() else None,
                "instrumental_path": str(instrumental_path.relative_to(config.BASE_LIBRARY_DIR)) if instrumental_path.exists() else None,
                "original_path": str(original_file.relative_to(config.BASE_LIBRARY_DIR)) if original_file and original_file.exists() else None,
                "source": metadata.source if hasattr(metadata, 'source') else None,
                "source_url": metadata.sourceUrl if hasattr(metadata, 'sourceUrl') else None,
                "video_id": metadata.videoId if hasattr(metadata, 'videoId') else None,
                "uploader": metadata.uploader if hasattr(metadata, 'uploader') else None,
                "uploader_id": metadata.uploaderId if hasattr(metadata, 'uploaderId') else None,
                "channel": metadata.channel if hasattr(metadata, 'channel') else None,
                "channel_id": metadata.channelId if hasattr(metadata, 'channelId') else None,
                "description": metadata.description if hasattr(metadata, 'description') else None,
                "upload_date": metadata.uploadDate if hasattr(metadata, 'uploadDate') else None,
                "mbid": metadata.mbid if hasattr(metadata, 'mbid') else None,
                "release_title": metadata.releaseTitle if hasattr(metadata, 'releaseTitle') else None,
                "release_id": metadata.releaseId if hasattr(metadata, 'releaseId') else None,
                "release_date": metadata.releaseDate if hasattr(metadata, 'releaseDate') else None,
                "genre": metadata.genre if hasattr(metadata, 'genre') else None,
                "language": metadata.language if hasattr(metadata, 'language') else None,
                "lyrics": metadata.lyrics if hasattr(metadata, 'lyrics') else None,
                "synced_lyrics": metadata.syncedLyrics if hasattr(metadata, 'syncedLyrics') else None
            }

            # Update db_song attributes dynamically
            for key, value in metadata_dict.items():
                if value is not None:
                    setattr(db_song, key, value)

            session.commit()
            return db_song

    except Exception as e:
        logging.error(f"Error creating or updating song {song_id}: {e}")
        traceback.print_exc()
        return None


def sync_songs_with_filesystem() -> int:
    """
    Sync database with the filesystem library.
    Returns the number of songs added.
    """
    count = 0
    try:
        # Get all song directories
        config.BASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        song_dirs = [d for d in config.BASE_LIBRARY_DIR.iterdir() if d.is_dir()]
        
        for song_dir in song_dirs:
            song_id = song_dir.name
            
            # Check if it's already in the database
            db_song = get_song(song_id)
            
            if not db_song:
                # Read metadata from file
                metadata = file_management.read_song_metadata(song_id)
                
                # If metadata exists, add to database
                if metadata:
                    create_or_update_song(song_id, metadata)
                    count += 1
                    logging.info(f"Added song from filesystem: {song_id}")
                
        return count
    except Exception as e:
        logging.error(f"Error syncing songs with filesystem: {e}")
        traceback.print_exc()
        return count
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
from ..config import get_config

# Get configuration and create database engine
config = get_config()
DATABASE_URL = config.DATABASE_URL
logging.info(f"Database URL: {DATABASE_URL}")
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
    # Check if we're using SQLite and get the database path
    if config.DATABASE_URL.startswith('sqlite:'):
        # Extract path from sqlite:///path/to/db
        db_path_str = config.DATABASE_URL.replace('sqlite:///', '')
        db_path = Path(db_path_str)
        
        if not db_path.exists():
            logging.info("Creating database schema from scratch")
            Base.metadata.create_all(bind=engine)
            return
    else:
        # For non-SQLite databases, just ensure schema exists
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
                    
                    # Handle nullability
                    nullable = "" if col.nullable else "NOT NULL"
                    
                    # Handle defaults carefully
                    default = ""
                    if col.default is not None:
                        if hasattr(col.default, 'arg') and col.default.arg is not None:
                            if isinstance(col.default.arg, str):
                                default = f"DEFAULT '{col.default.arg}'"
                            elif isinstance(col.default.arg, bool):
                                default = f"DEFAULT {1 if col.default.arg else 0}"
                            else:
                                default = f"DEFAULT {col.default.arg}"
                    
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}".strip()
                    try:
                        from sqlalchemy import text
                        connection.execute(text(sql))
                        connection.commit()
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
    """Get all songs from the database, sorted by date_added in descending order (newest first)"""
    try:
        with get_db_session() as session:
            songs = session.query(DbSong).order_by(DbSong.date_added.desc()).all()
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
        # Get configuration and all song directories
        config = get_config()
        config.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        song_dirs = [d for d in config.LIBRARY_DIR.iterdir() if d.is_dir()]
        
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


def delete_song(song_id: str) -> bool:
    """Delete a song from the database by its ID."""
    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()
            if db_song:
                session.delete(db_song)
                session.commit()
                logging.info(f"Successfully deleted song {song_id} from the database.")
                return True
            else:
                logging.warning(f"Song {song_id} not found in the database.")
                return False
    except Exception as e:
        logging.error(f"Error deleting song {song_id} from the database: {e}")
        return False
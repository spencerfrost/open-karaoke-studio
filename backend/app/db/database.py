# backend/app/db/database.py
"""
Database utility functions
"""

from contextlib import contextmanager
from typing import Iterator, List, Optional
import traceback
import json
from pathlib import Path
import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from .models import Base, DbSong, SongMetadata, Song
from ..services import file_management
from ..config import get_config

# Get configuration and create database engine
config = get_config()
DATABASE_URL = config.DATABASE_URL
logging.info(f"Database URL: {DATABASE_URL}")

# Log the actual database file path for SQLite debugging
if DATABASE_URL.startswith('sqlite:'):
    db_file_path = DATABASE_URL.replace('sqlite:///', '')
    logging.info(f"SQLite database file path: {db_file_path}")
    logging.info(f"Database file exists: {Path(db_file_path).exists()}")
    
    # Log current working directory for debugging path resolution
    import os
    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"Absolute database path: {Path(db_file_path).resolve()}")

# Configure SQLite engine for better concurrency and cross-process reliability
if DATABASE_URL.startswith('sqlite:'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "timeout": 30,  # 30 second timeout for database locks
            "check_same_thread": False,  # Allow cross-thread access
        },
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections every hour
        echo=False,  # Set to True for SQL debugging if needed
    )
else:
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize the database
def init_db():
    """Initialize the database with tables from models"""
    Base.metadata.create_all(bind=engine)
    
    # Configure SQLite for better concurrency if using SQLite
    if config.DATABASE_URL.startswith('sqlite:'):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text
                # Enable WAL mode for better concurrency
                connection.execute(text("PRAGMA journal_mode=WAL;"))
                # Set reasonable timeout
                connection.execute(text("PRAGMA busy_timeout=30000;"))
                # Enable foreign keys
                connection.execute(text("PRAGMA foreign_keys=ON;"))
                # Set synchronous mode for better reliability
                connection.execute(text("PRAGMA synchronous=FULL;"))
                connection.commit()
                logging.info("SQLite configured with WAL mode for better concurrency")
        except Exception as e:
            logging.warning(f"Failed to configure SQLite pragmas: {e}")


def force_db_sync():
    """Force SQLite WAL checkpoint to ensure data is written to main database file"""
    if config.DATABASE_URL.startswith('sqlite:'):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text
                # Force WAL checkpoint to flush all pending transactions
                result = connection.execute(text("PRAGMA wal_checkpoint(FULL);"))
                logging.info(f"WAL checkpoint result: {result.fetchone()}")
                connection.commit()
        except Exception as e:
            logging.warning(f"Failed to execute WAL checkpoint: {e}")

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
    """Create or update a song in the database from metadata
    
    Returns:
        The refreshed DbSong model with all data loaded
    """

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
                "date_added": getattr(metadata, 'dateAdded', None) or getattr(metadata, 'date_added', None),
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
                "album": metadata.releaseTitle if hasattr(metadata, 'releaseTitle') else None,
                "release_id": metadata.releaseId if hasattr(metadata, 'releaseId') else None,
                "release_date": metadata.releaseDate if hasattr(metadata, 'releaseDate') else None,
                "genre": metadata.genre if hasattr(metadata, 'genre') else None,
                "language": metadata.language if hasattr(metadata, 'language') else None,
                "lyrics": metadata.lyrics if hasattr(metadata, 'lyrics') else None,
                "synced_lyrics": metadata.syncedLyrics if hasattr(metadata, 'syncedLyrics') else None,
                
                # Phase 1B: iTunes fields
                "itunes_track_id": metadata.itunesTrackId if hasattr(metadata, 'itunesTrackId') else None,
                "itunes_artist_id": metadata.itunesArtistId if hasattr(metadata, 'itunesArtistId') else None,
                "itunes_collection_id": metadata.itunesCollectionId if hasattr(metadata, 'itunesCollectionId') else None,
                "track_time_millis": metadata.trackTimeMillis if hasattr(metadata, 'trackTimeMillis') else None,
                "itunes_explicit": metadata.itunesExplicit if hasattr(metadata, 'itunesExplicit') else None,
                "itunes_preview_url": metadata.itunesPreviewUrl if hasattr(metadata, 'itunesPreviewUrl') else None,
                "itunes_artwork_urls": json.dumps(metadata.itunesArtworkUrls) if hasattr(metadata, 'itunesArtworkUrls') and metadata.itunesArtworkUrls else None,
                
                # Phase 1B: Enhanced YouTube fields
                "youtube_duration": metadata.youtubeDuration if hasattr(metadata, 'youtubeDuration') else None,
                "youtube_thumbnail_urls": json.dumps(metadata.youtubeThumbnailUrls) if hasattr(metadata, 'youtubeThumbnailUrls') and metadata.youtubeThumbnailUrls else None,
                "youtube_tags": json.dumps(metadata.youtubeTags) if hasattr(metadata, 'youtubeTags') and metadata.youtubeTags else None,
                "youtube_categories": json.dumps(metadata.youtubeCategories) if hasattr(metadata, 'youtubeCategories') and metadata.youtubeCategories else None,
                "youtube_channel_id": metadata.youtubeChannelId if hasattr(metadata, 'youtubeChannelId') else None,
                "youtube_channel_name": metadata.youtubeChannelName if hasattr(metadata, 'youtubeChannelName') else None,
                
                # Phase 1B: Raw metadata storage
                "itunes_raw_metadata": metadata.itunesRawMetadata if hasattr(metadata, 'itunesRawMetadata') else None,
                "youtube_raw_metadata": metadata.youtubeRawMetadata if hasattr(metadata, 'youtubeRawMetadata') else None,
            }

            # Update db_song attributes dynamically
            for key, value in metadata_dict.items():
                if value is not None:
                    setattr(db_song, key, value)

            session.commit()
            # Refresh the instance to ensure all attributes are loaded before session closes
            session.refresh(db_song)
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


def update_song_audio_paths(song_id: str, vocals_path: str, instrumental_path: str) -> bool:
    """Update song with audio file paths after processing completes
    
    Args:
        song_id: Song identifier
        vocals_path: Relative path to vocals file from library directory
        instrumental_path: Relative path to instrumental file from library directory
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()
            
            if not db_song:
                logging.error(f"Song {song_id} not found for audio path update")
                return False
            
            # Update the audio file paths
            db_song.vocal_path = vocals_path
            db_song.instrumental_path = instrumental_path
            
            session.commit()
            logging.info(f"Successfully updated audio paths for song {song_id}")
            return True
            
    except Exception as e:
        logging.error(f"Error updating audio paths for song {song_id}: {e}")
        traceback.print_exc()
        return False


def update_song_with_metadata(song_id: str, updated_song: DbSong) -> bool:
    """Update song with enhanced metadata from processing
    
    Args:
        song_id: Song identifier
        updated_song: DbSong object with updated metadata fields
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()
            
            if not db_song:
                logging.error(f"Song {song_id} not found for metadata update")
                return False
            
            # Update metadata fields, but preserve existing audio paths if not set in updated_song
            db_song.title = updated_song.title or db_song.title
            db_song.artist = updated_song.artist or db_song.artist
            db_song.duration = updated_song.duration or db_song.duration
            db_song.cover_art_path = updated_song.cover_art_path or db_song.cover_art_path
            db_song.thumbnail_path = updated_song.thumbnail_path or db_song.thumbnail_path
            db_song.genre = updated_song.genre or db_song.genre
            db_song.year = updated_song.year or db_song.year
            db_song.album = updated_song.album or db_song.album
            db_song.release_date = updated_song.release_date or db_song.release_date
            db_song.language = updated_song.language or db_song.language
            db_song.source = updated_song.source or db_song.source
            db_song.source_url = updated_song.source_url or db_song.source_url
            db_song.video_id = updated_song.video_id or db_song.video_id
            db_song.uploader = updated_song.uploader or db_song.uploader
            db_song.uploader_id = updated_song.uploader_id or db_song.uploader_id
            db_song.channel = updated_song.channel or db_song.channel
            db_song.channel_id = updated_song.channel_id or db_song.channel_id
            db_song.description = updated_song.description or db_song.description
            db_song.upload_date = updated_song.upload_date or db_song.upload_date
            db_song.mbid = updated_song.mbid or db_song.mbid
            
            # Phase 1B: iTunes integration fields
            db_song.itunes_track_id = updated_song.itunes_track_id or db_song.itunes_track_id
            db_song.itunes_artist_id = updated_song.itunes_artist_id or db_song.itunes_artist_id
            db_song.itunes_collection_id = updated_song.itunes_collection_id or db_song.itunes_collection_id
            db_song.track_time_millis = updated_song.track_time_millis or db_song.track_time_millis
            db_song.itunes_explicit = updated_song.itunes_explicit if updated_song.itunes_explicit is not None else db_song.itunes_explicit
            db_song.itunes_preview_url = updated_song.itunes_preview_url or db_song.itunes_preview_url
            db_song.itunes_artwork_urls = updated_song.itunes_artwork_urls or db_song.itunes_artwork_urls
            
            # Phase 1B: Enhanced YouTube fields
            db_song.youtube_duration = updated_song.youtube_duration or db_song.youtube_duration
            db_song.youtube_thumbnail_urls = updated_song.youtube_thumbnail_urls or db_song.youtube_thumbnail_urls
            db_song.youtube_tags = updated_song.youtube_tags or db_song.youtube_tags
            db_song.youtube_categories = updated_song.youtube_categories or db_song.youtube_categories
            db_song.youtube_channel_id = updated_song.youtube_channel_id or db_song.youtube_channel_id
            db_song.youtube_channel_name = updated_song.youtube_channel_name or db_song.youtube_channel_name
            
            # Phase 1B: Raw metadata storage
            db_song.itunes_raw_metadata = updated_song.itunes_raw_metadata or db_song.itunes_raw_metadata
            db_song.youtube_raw_metadata = updated_song.youtube_raw_metadata or db_song.youtube_raw_metadata
            
            # Preserve existing file paths if not provided in updated_song
            if updated_song.vocals_path:
                db_song.vocals_path = updated_song.vocals_path
            if updated_song.instrumental_path:
                db_song.instrumental_path = updated_song.instrumental_path
            if updated_song.original_path:
                db_song.original_path = updated_song.original_path
            
            session.commit()
            logging.info(f"Successfully updated metadata for song {song_id}")
            return True
            
    except Exception as e:
        logging.error(f"Error updating metadata for song {song_id}: {e}")
        traceback.print_exc()
        return False
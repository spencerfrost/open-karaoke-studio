# backend/app/services/file_management.py
import shutil
import json
import requests
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from ..config import Config as config
from ..db.models import SongMetadata 

def ensure_library_exists():
    """Creates the base library directory if it doesn't exist."""
    config.BASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def get_song_dir(input_path_or_id: Path | str) -> Path:
    """Creates and returns the specific directory for a song within the library."""
    ensure_library_exists()

    if isinstance(input_path_or_id, Path):
        if input_path_or_id.is_file():
            song_id = input_path_or_id.stem
        else:
            song_id = input_path_or_id.name
    else:
        song_id = input_path_or_id

    song_dir = config.BASE_LIBRARY_DIR / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir


def get_song_dir_from_id(song_id: str) -> Path:
    """Returns the directory for a song given its ID."""
    song_dir = config.BASE_LIBRARY_DIR / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir


def get_song_dir_from_path(input_path: Path) -> Path:
    """Returns the directory for a song given its input path."""
    song_id = input_path.stem
    song_dir = config.BASE_LIBRARY_DIR / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir


def get_vocals_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the vocals file."""
    return song_dir / "vocals"


def get_instrumental_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the instrumental file."""
    return song_dir / "instrumental"


def get_original_path(song_dir: Path, original_input_path: Path) -> Path:
    """Returns the path for storing the original file, keeping original suffix."""
    song_id = song_dir.name
    original_suffix = original_input_path.suffix
    return song_dir / f"{song_id}{config.ORIGINAL_FILENAME_SUFFIX}{original_suffix}"


def save_original_file(input_path: Path, song_dir: Path) -> Optional[Path]:
    """Copies the original input file to the song directory."""
    if not input_path.exists():
        return None

    destination = get_original_path(song_dir, input_path)
    try:
        shutil.copy2(input_path, destination)
        return destination
    except (IOError, OSError) as e:
        print(f"Error copying original file: {e}")
        return None


def get_processed_songs(library_path: Optional[Path] = None) -> List[str]:
    """Scans the library and returns a list of potential song IDs (directories)."""
    library_path = library_path or config.BASE_LIBRARY_DIR

    if not library_path.is_dir():
        return []

    return [d.name for d in library_path.iterdir() if d.is_dir()]


def read_song_metadata(
    song_id: str, library_path: Optional[Path] = None
) -> Optional[SongMetadata]:
    """
    Reads song metadata from the database.
    Falls back to legacy metadata.json if database entry not found.
    """
    try:
        from ..db import database
        db_song = database.get_song(song_id)
        
        if db_song:
            # Convert DbSong to SongMetadata
            metadata = SongMetadata(
                title=db_song.title,
                artist=db_song.artist,
                duration=db_song.duration,
                favorite=db_song.favorite,
                dateAdded=db_song.date_added,
                coverArt=db_song.cover_art_path,
                thumbnail=db_song.thumbnail_path,
                source=db_song.source,
                sourceUrl=db_song.source_url,
                videoId=db_song.video_id,
                uploader=db_song.uploader,
                uploaderId=db_song.uploader_id,
                channel=db_song.channel,
                channelId=db_song.channel_id,
                description=db_song.description,
                uploadDate=db_song.upload_date,
                mbid=db_song.mbid,
                releaseTitle=db_song.release_title,
                releaseId=db_song.release_id,
                releaseDate=db_song.release_date,
                genre=db_song.genre,
                language=db_song.language,
                lyrics=db_song.lyrics,
                syncedLyrics=db_song.synced_lyrics
            )
            return metadata
            
    except ImportError:
        logging.error("Cannot read metadata: Database module not available")
        raise Exception("Database module not available, cannot read metadata")
    
    
    
    except Exception as e:
        print(f"Error accessing database: {e}")
        return None


def write_song_metadata(song_id: str, metadata: SongMetadata):
    """
    Writes song metadata to the database.
    No longer writes to metadata.json file.
    """
    try:
        from ..db import database
        database.create_or_update_song(song_id, metadata)
        logging.info(f"Updated database record for song: {song_id}")
    except ImportError:
        # Database module not available, log error
        logging.error("Cannot save metadata: Database module not available")
        raise Exception("Database module not available, cannot save metadata")
    except Exception as e:
        logging.error(f"Error updating database for {song_id}: {e}")
        raise Exception(f"Could not write metadata for {song_id}: {e}") from e


def download_image(url: str, save_path: Path) -> bool:
    """Downloads an image from a URL and saves it to the specified path."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Check if response contains image data
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            print(f"Downloaded content is not an image: {content_type}")
            return False

        # Save the image
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return False


def get_thumbnail_path(song_dir: Path) -> Path:
    """Returns the standard path for the YouTube thumbnail."""
    return song_dir / "thumbnail.jpg"


def get_cover_art_path(song_dir: Path) -> Path:
    """Returns the standard path for the album cover art."""
    return song_dir / "cover.jpg"


def parse_title_artist(title: str) -> Tuple[str, str]:
    """Attempts to parse artist and song title from a YouTube video title."""
    # Common patterns: "Artist - Title", "Artist: Title", "Artist | Title"
    separators = [" - ", ": ", " | ", " – ", "- ", ": ", "| ", "– "]

    for separator in separators:
        if separator in title:
            parts = title.split(separator, 1)
            artist = parts[0].strip()
            song_title = parts[1].strip()

            # Clean up common YouTube title artifacts
            song_title = song_title.split("(Official")[0].strip()
            song_title = song_title.split("[Official")[0].strip()
            song_title = song_title.split("(feat.")[0].strip()
            song_title = song_title.split("ft.")[0].strip()

            return artist, song_title

    # If no separator found, return title and Unknown Artist
    return "Unknown Artist", title


def delete_song_files(song_id: str):
    """Deletes the directory and all files associated with a song."""
    song_dir = get_song_dir(song_id)
    if song_dir.exists() and song_dir.is_dir():
        try:
            shutil.rmtree(song_dir)
            logging.info(f"Successfully deleted song directory: {song_dir}")
        except Exception as e:
            logging.error(f"Error deleting song directory {song_dir}: {e}")
            raise Exception(f"Could not delete song directory {song_dir}: {e}")
    else:
        logging.warning(f"Song directory does not exist: {song_dir}")

# backend/app/services/file_management.py
import shutil
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from ..config import Config as config
from ..db.models import SongMetadata  # Import the Pydantic model for metadata
from urllib.parse import urlparse

# --- Constants ---
METADATA_FILENAME = "metadata.json"
VOCALS_SUFFIX = ".mp3"
INSTRUMENTAL_SUFFIX = ".mp3"


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


# --- Metadata Functions ---


def read_song_metadata(
    song_id: str, library_path: Optional[Path] = None
) -> Optional[SongMetadata]:
    """Reads metadata.json for a given song ID."""
    song_dir = get_song_dir(song_id)
    metadata_file = song_dir / METADATA_FILENAME
    if metadata_file.exists():
        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
                # Use Pydantic to parse and validate
                return SongMetadata(**data)
        except (json.JSONDecodeError, TypeError, ValueError, FileNotFoundError) as e:
            print(f"Error reading or parsing metadata for {song_id}: {e}")
            return None  # Return None on error
        except Exception as e:  # Catch potential Pydantic validation errors too
            print(f"Validation error reading metadata for {song_id}: {e}")
            return None
    else:
        # print(f"Metadata file not found for song ID: {song_id}") # Optional: Log this
        return None  # Metadata file doesn't exist


def write_song_metadata(
    song_id: str, metadata: SongMetadata, library_path: Optional[Path] = None
):
    """
    Writes metadata.json for a given song ID.
    Also updates the database entry if database module is available.
    """
    song_dir = get_song_dir(song_id)
    metadata_file = song_dir / METADATA_FILENAME
    try:
        song_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists
        # Use Pydantic's .model_dump_json() (V2) or .json() (V1) for serialization
        if hasattr(metadata, "model_dump_json"):
            json_data = metadata.model_dump_json(indent=2)
        else:
            json_data = metadata.json(indent=2)  # Pydantic V1 fallback

        with open(metadata_file, "w") as f:
            f.write(json_data)

        # Update database entry if database module is available
        try:
            from . import database

            database.create_or_update_song(song_id, metadata)
        except ImportError:
            # Database module not available, skip database update
            pass
        except Exception as e:
            print(f"Error updating database for {song_id}: {e}")
            # Continue since we've already saved the file

    except Exception as e:
        print(f"Error writing metadata for {song_id}: {e}")
        # Decide if error should be raised or just logged
        raise Exception(f"Could not write metadata for {song_id}: {e}") from e


# --- Media and Asset Management ---


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


# --- Function to create initial metadata ---
def create_initial_metadata(
    song_dir: Path,
    title: str,
    artist: str,
    duration: float,
    youtube_info: Dict[str, Any],
):
    """
    Creates the initial metadata file after processing.
    Also creates a database entry if database module is available.
    """
    metadata = SongMetadata(
        title=title,
        artist=artist,
        duration=duration,
        dateAdded=datetime.now(timezone.utc),
        source="youtube",
        videoId=youtube_info.get("id"),
        videoTitle=youtube_info.get("title", title),
        sourceUrl=youtube_info.get("webpage_url"),
        uploader=youtube_info.get("uploader"),
        channel=youtube_info.get("channel"),
        # description=youtube_info.get("description", "")[:500]
    )

        
    thumbnails = youtube_info.get('thumbnails', [])
    thumbnail_url = thumbnails[0]['url'] if thumbnails else None
    if thumbnail_url:
        thumbnail_path = get_thumbnail_path(song_dir)
        logging.info(f"Downloading thumbnail from {thumbnail_url}")
        download_image(thumbnail_url, thumbnail_path)

    thumbnail_url = youtube_info.get("thumbnail")
    if thumbnail_url:
        thumbnail_path = get_thumbnail_path(song_dir)
        if download_image(thumbnail_url, thumbnail_path):
            metadata.thumbnail = f"{song_dir.name}/thumbnail.jpg"

    # Save metadata
    write_song_metadata(song_dir.name, metadata)

    # Also update database if available
    try:
        from . import database

        database.create_or_update_song(song_dir.name, metadata)
    except ImportError:
        # Database module not available
        pass
    except Exception as e:
        print(f"Error updating database with initial metadata: {e}")

    return metadata

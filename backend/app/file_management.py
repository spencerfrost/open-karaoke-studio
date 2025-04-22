# backend/app/file_management.py
import shutil
import json # Add json import
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple # Add Dict, Any, Tuple
from . import config
from .models import SongMetadata # Import the new Pydantic model for metadata
from urllib.parse import urlparse

# --- Constants ---
METADATA_FILENAME = "metadata.json"
# Assuming standard output names from Demucs (adjust if different)
VOCALS_SUFFIX = ".mp3" # Or .wav, .flac etc. depending on your output format
INSTRUMENTAL_SUFFIX = ".mp3" # Or .wav, .flac etc.

# --- Existing Functions ---
def ensure_library_exists():
    """Creates the base library directory if it doesn't exist."""
    try:
        config.BASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating base library directory {config.BASE_LIBRARY_DIR}: {e}")
        raise

def get_song_dir(input_path_or_id: Path | str) -> Path:
    """Creates and returns the specific directory for a song within the library."""
    if isinstance(input_path_or_id, Path):
        song_name = input_path_or_id.stem
    else: # Assume it's an ID (string)
        song_name = str(input_path_or_id)
    song_dir = config.BASE_LIBRARY_DIR / song_name
    # Don't auto-create here anymore, creation should happen during processing
    # song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir

def get_vocals_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the vocals file."""
    # Use actual filename from config/constants if available
    return song_dir / (config.VOCALS_FILENAME_STEM if hasattr(config, 'VOCALS_FILENAME_STEM') else "vocals")

def get_instrumental_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the instrumental file."""
    # Use actual filename from config/constants if available
    return song_dir / (config.INSTRUMENTAL_FILENAME_STEM if hasattr(config, 'INSTRUMENTAL_FILENAME_STEM') else "instrumental")

def get_original_path(song_dir: Path, original_input_path: Path) -> Path:
    """Returns the path for storing the original file, keeping original suffix."""
    # Standardize original filename slightly for easier retrieval
    suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
    filename = f"{song_dir.name}{suffix}{original_input_path.suffix}"
    return song_dir / filename

def save_original_file(input_path: Path, song_dir: Path) -> Optional[Path]:
    """Copies the original input file to the song directory."""
    destination_path = get_original_path(song_dir, input_path)
    try:
        # Ensure directory exists before copying
        song_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_path, destination_path)
        print(f"Copied original file to: {destination_path}")
        return destination_path
    except Exception as e:
        print(f"Error copying original file {input_path} to {destination_path}: {e}")
        # Don't raise here, let the caller handle based on context
        return None # Indicate failure


def get_processed_songs(library_path: Optional[Path] = None) -> List[str]:
    """Scans the library and returns a list of potential song IDs (directories)."""
    library_dir = library_path if library_path else config.BASE_LIBRARY_DIR
    try:
        library_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error accessing or creating library directory {library_dir}: {e}")
        return []

    song_ids = []
    try:
        for item in library_dir.iterdir():
            # Basic check: is it a directory and does it contain expected files?
            if item.is_dir():
                 # Optional: Add check for vocals/instrumental files existence if needed
                 # vocals_file = get_vocals_path_stem(item).with_suffix(VOCALS_SUFFIX)
                 # instrumental_file = get_instrumental_path_stem(item).with_suffix(INSTRUMENTAL_SUFFIX)
                 # if vocals_file.exists() and instrumental_file.exists():
                 song_ids.append(item.name)
    except OSError as e:
        print(f"Error reading library directory {library_dir}: {e}")
        return []
    return song_ids

# --- New Metadata Functions ---

def read_song_metadata(song_id: str, library_path: Optional[Path] = None) -> Optional[SongMetadata]:
    """Reads metadata.json for a given song ID."""
    song_dir = get_song_dir(song_id)
    metadata_file = song_dir / METADATA_FILENAME
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                # Use Pydantic to parse and validate
                return SongMetadata(**data)
        except (json.JSONDecodeError, TypeError, ValueError, FileNotFoundError) as e:
            print(f"Error reading or parsing metadata for {song_id}: {e}")
            return None # Return None on error
        except Exception as e: # Catch potential Pydantic validation errors too
             print(f"Validation error reading metadata for {song_id}: {e}")
             return None
    else:
        # print(f"Metadata file not found for song ID: {song_id}") # Optional: Log this
        return None # Metadata file doesn't exist

def write_song_metadata(song_id: str, metadata: SongMetadata, library_path: Optional[Path] = None):
    """Writes metadata.json for a given song ID."""
    song_dir = get_song_dir(song_id)
    metadata_file = song_dir / METADATA_FILENAME
    try:
        song_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists
        # Use Pydantic's .model_dump_json() (V2) or .json() (V1) for serialization
        if hasattr(metadata, 'model_dump_json'):
             json_data = metadata.model_dump_json(indent=2)
        else:
             json_data = metadata.json(indent=2) # Pydantic V1 fallback

        with open(metadata_file, 'w') as f:
            f.write(json_data)
    except Exception as e:
        print(f"Error writing metadata for {song_id}: {e}")
        # Decide if error should be raised or just logged
        raise ProcessingError(f"Could not write metadata for {song_id}", 500) from e


# --- Media and Asset Management ---

def download_image(url: str, save_path: Path) -> bool:
    """Downloads an image from a URL and saves it to the specified path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Ensure the directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the image to file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully downloaded image to: {save_path}")
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
    # Common patterns: "Artist - Title", "Artist | Title", "Title by Artist"
    # Also remove common suffixes like "(Official Video)", "(Lyrics)", etc.
    
    # Default values
    artist = "Unknown Artist"
    cleaned_title = title
    
    # Remove common suffixes
    common_suffixes = [
        "(Official Video)", "(Official Music Video)", "(Official Audio)",
        "(Lyrics)", "(Lyric Video)", "(Audio)", "(HQ)", "(HD)",
        "[Official Video]", "[Official Music Video]", "[Official Audio]",
        "[Lyrics]", "[Lyric Video]", "[Audio]", "[HQ]", "[HD]",
        "- Official Video", "- Lyrics", "(Official)", "[Official]"
    ]
    
    for suffix in common_suffixes:
        if suffix.lower() in title.lower():
            cleaned_title = title.replace(suffix, "").strip()
    
    # Try common separators
    separators = [" - ", " – ", " | ", " _ ", ": "]
    for separator in separators:
        if separator in cleaned_title:
            parts = cleaned_title.split(separator, 1)
            artist = parts[0].strip()
            cleaned_title = parts[1].strip()
            return cleaned_title, artist
    
    # Try "by" pattern (e.g., "Title by Artist")
    if " by " in cleaned_title.lower():
        parts = cleaned_title.lower().split(" by ", 1)
        cleaned_title = parts[0].strip().title()  # Title case for title
        artist = parts[1].strip().title()  # Title case for artist
        return cleaned_title, artist
    
    # Return best guess
    return cleaned_title, artist

# --- Function to create initial metadata ---

def create_initial_metadata(input_path: Path, song_dir: Path, duration: Optional[float] = None, 
                            youtube_info: Optional[Dict[str, Any]] = None):
    """Creates the initial metadata file after processing."""
    song_id = song_dir.name
    
    if youtube_info:  # If we have YouTube info
        # Parse title and artist from YouTube title
        youtube_title = youtube_info.get('title', '')
        title, artist = parse_title_artist(youtube_title)
        
        # Create metadata with YouTube info
        initial_data = SongMetadata(
            title=title,
            artist=artist,
            duration=youtube_info.get('duration', duration),
            dateAdded=datetime.now(timezone.utc),
            favorite=False,
            source="youtube",
            sourceUrl=youtube_info.get('url', ''),
            videoId=youtube_info.get('id', ''),
            channelName=youtube_info.get('uploader', ''),
            channelId=youtube_info.get('channel_id', ''),
            description=youtube_info.get('description', '')[:500] if youtube_info.get('description') else None,  # Truncate long descriptions
            uploadDate=youtube_info.get('upload_date'),
            # Set thumbnail if we downloaded it
            thumbnail=str(get_thumbnail_path(song_dir).relative_to(config.BASE_LIBRARY_DIR)) if get_thumbnail_path(song_dir).exists() else None,
            # coverArt will be set later if MusicBrainz lookup succeeds
        )
    else:  # Regular file upload
        # Basic metadata extraction from filename
        title_guess = song_id.replace('_', ' ').replace('-', ' ').title()
        
        initial_data = SongMetadata(
            title=title_guess,
            artist="Unknown Artist",  # Or try to parse from filename
            duration=duration,
            dateAdded=datetime.now(timezone.utc),
            favorite=False,
            source="upload"
        )
    
    print(f"Creating initial metadata for song: {song_id}")
    write_song_metadata(song_id, initial_data)
    return initial_data


def generate_directory_name(artist: str, title: str) -> str:
    """Generate a clean directory name from artist and title."""
    # Replace spaces and problematic characters
    artist_clean = (
        artist.replace(' ', '-')
        .replace('/', '_')
        .replace('\\', '_')
        .replace(':', '')
        .replace('*', '')
        .replace('?', '')
        .replace('"', '')
        .replace('<', '')
        .replace('>', '')
        .replace('|', '')
    )

    title_clean = (
        title.replace(' ', '-')
        .replace('/', '_')
        .replace('\\', '_')
        .replace(':', '')
        .replace('*', '')
        .replace('?', '')
        .replace('"', '')
        .replace('<', '')
        .replace('>', '')
        .replace('|', '')
    )

    # Create name and ensure it's not too long for filesystems
    dir_name = f"{artist_clean}-{title_clean}"
    if len(dir_name) > 80:  # Set a reasonable maximum length
        dir_name = dir_name[:80]

    return dir_name
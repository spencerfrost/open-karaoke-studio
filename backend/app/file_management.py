# backend/app/file_management.py
import shutil
import json # Add json import
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any # Add Dict, Any
from . import config
from .models import SongMetadata # Import the new Pydantic model for metadata

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


# --- Function to create initial metadata (Example) ---
# Call this function after successful audio separation in your processing task

def create_initial_metadata(input_path: Path, song_dir: Path, duration: Optional[float] = None):
    """Creates the initial metadata file after processing."""
    song_id = song_dir.name
    # Basic metadata extraction (improve as needed)
    title_guess = song_id.replace('_', ' ').replace('-', ' ').title()

    initial_data = SongMetadata(
        title=title_guess,
        artist="Unknown Artist", # Or try to parse from filename
        duration=duration,
        dateAdded=datetime.now(timezone.utc),
        favorite=False
    )
    print(f"Creating initial metadata for song: {song_id}")
    write_song_metadata(song_id, initial_data)
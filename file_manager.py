# file_manager.py
"""Manages file and directory operations for the song library - Reverted State."""

import shutil
from pathlib import Path
import config  # Import settings from config.py


def ensure_library_exists():
    """Creates the base library directory if it doesn't exist."""
    config.BASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def get_song_dir(input_path: Path) -> Path:
    """Creates and returns the specific directory for a song within the library."""
    song_name = input_path.stem  # Use filename without extension as song identifier
    song_dir = config.BASE_LIBRARY_DIR / song_name
    song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir


def get_vocals_path(song_dir: Path) -> Path:
    """Returns the standard path for the vocals file."""
    return song_dir / config.VOCALS_FILENAME  # Uses hardcoded name from config


def get_instrumental_path(song_dir: Path) -> Path:
    """Returns the standard path for the instrumental file."""
    return song_dir / config.INSTRUMENTAL_FILENAME  # Uses hardcoded name from config


def get_original_path(song_dir: Path, original_input_path: Path) -> Path:
    """Returns the path for storing the original file, keeping original suffix."""
    # Using suffix defined in config and original extension
    return (
        song_dir
        / f"{original_input_path.stem}{config.ORIGINAL_FILENAME_SUFFIX}{original_input_path.suffix}"
    )


def save_original_file(input_path: Path, song_dir: Path) -> Path:
    """Copies the original input file to the song directory."""
    destination_path = get_original_path(song_dir, input_path)
    try:
        shutil.copyfile(input_path, destination_path)
        print(f"Copied original file to: {destination_path}")
        return destination_path
    except Exception as e:
        print(f"Error copying original file {input_path} to {destination_path}: {e}")
        return None


def get_processed_songs(library_path=None):
    """Scans the library and returns a list of processed song names."""
    # Use default library dir from config if none provided
    library_dir = library_path if library_path else config.BASE_LIBRARY_DIR
    try:
        library_dir.mkdir(parents=True, exist_ok=True)  # Ensure it exists
    except Exception as e:
        print(f"Error accessing or creating library directory {library_dir}: {e}")
        return []

    songs = []
    for item in library_dir.iterdir():
        if item.is_dir():
            # Check if essential files exist (using fixed names from config)
            if (item / config.INSTRUMENTAL_FILENAME).exists() and (
                item / config.VOCALS_FILENAME
            ).exists():
                songs.append(item.name)  # Add song name (directory name)
    return songs

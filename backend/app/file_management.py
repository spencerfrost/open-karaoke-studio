import shutil
from pathlib import Path
from typing import List, Optional
import config

def ensure_library_exists():
    """Creates the base library directory if it doesn't exist."""
    try:
        config.BASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating base library directory {config.BASE_LIBRARY_DIR}: {e}")
        raise  # Re-raise to be handled by the API layer

def get_song_dir(input_path: Path) -> Path:
    """Creates and returns the specific directory for a song within the library."""
    song_name = input_path.stem
    song_dir = config.BASE_LIBRARY_DIR / song_name
    song_dir.mkdir(parents=True, exist_ok=True)
    return song_dir

def get_vocals_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the vocals file."""
    return song_dir / config.VOCALS_FILENAME_STEM

def get_instrumental_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the instrumental file."""
    return song_dir / config.INSTRUMENTAL_FILENAME_STEM

def get_original_path(song_dir: Path, original_input_path: Path) -> Path:
    """Returns the path for storing the original file, keeping original suffix."""
    filename = f"{original_input_path.stem}{config.ORIGINAL_FILENAME_SUFFIX}{original_input_path.suffix}"
    return song_dir / filename

def save_original_file(input_path: Path, song_dir: Path) -> Path:
    """Copies the original input file to the song directory."""
    destination_path = get_original_path(song_dir, input_path)
    try:
        shutil.copyfile(input_path, destination_path)
        print(f"Copied original file to: {destination_path}")
        return destination_path
    except Exception as e:
        print(f"Error copying original file {input_path} to {destination_path}: {e}")
        raise  # Re-raise to be handled by the API layer

def get_processed_songs(library_path: Optional[Path] = None) -> List[str]:
    """Scans the library and returns a list of processed song names (directories)."""
    library_dir = library_path if library_path else config.BASE_LIBRARY_DIR
    try:
        library_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error accessing or creating library directory {library_dir}: {e}")
        return []  # Or raise an exception if this is critical

    songs = []
    try:
        for item in library_dir.iterdir():
            if item.is_dir():
                songs.append(item.name)
    except OSError as e:
        print(f"Error reading library directory {library_dir}: {e}")
        return []  # Or raise
    return songs
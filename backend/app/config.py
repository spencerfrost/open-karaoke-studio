from pathlib import Path

# --- File Management ---
# Determine project root three levels up (open-karaoke directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_LIBRARY_DIR = PROJECT_ROOT / "karaoke_library"  # Root directory for processed songs
# Define base filenames (extension added dynamically)
VOCALS_FILENAME_STEM = "vocals"
INSTRUMENTAL_FILENAME_STEM = "instrumental"
ORIGINAL_FILENAME_SUFFIX = "_original" # Suffix for the copied original

# --- Audio Processing ---
DEFAULT_MODEL = "htdemucs_ft" # Default Demucs model
DEFAULT_MP3_BITRATE = "320" # Default bitrate if saving as MP3

# --- Downloads ---
TEMP_DOWNLOADS_DIR = Path("./temp_downloads") # Directory for temporary downloads
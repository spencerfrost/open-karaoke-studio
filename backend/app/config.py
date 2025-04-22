from pathlib import Path

# --- File Management ---
BASE_LIBRARY_DIR = Path("./karaoke_library") # Root directory for processed songs
# Define base filenames (extension added dynamically)
VOCALS_FILENAME_STEM = "vocals"
INSTRUMENTAL_FILENAME_STEM = "instrumental"
ORIGINAL_FILENAME_SUFFIX = "_original" # Suffix for the copied original

# --- Audio Processing ---
DEFAULT_MODEL = "htdemucs_ft" # Default Demucs model
DEFAULT_MP3_BITRATE = "320" # Default bitrate if saving as MP3

# --- Uploads ---
YT_DOWNLOAD_DIR = Path("./downloads") # Directory to store uploaded files
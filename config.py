# config.py
"""Configuration settings for the Karaoke App."""

from pathlib import Path

# --- Audio Processing ---
DEFAULT_MODEL = "htdemucs_ft" # Default Demucs model
DEFAULT_STEMS = ['vocals', 'drums', 'bass', 'other'] # Stems expected from the default model
OUTPUT_FORMAT = ".wav" # Output format ('.wav' or '.mp3')
MP3_BITRATE = "320" # Bitrate if output format is MP3 (e.g., "192", "320")

# --- File Management ---
BASE_LIBRARY_DIR = Path("./karaoke_library") # Root directory for processed songs
SEPARATED_FOLDER_NAME = "separated" # Subfolder within the library for raw stems (optional now)
VOCALS_FILENAME = f"vocals{OUTPUT_FORMAT}"
INSTRUMENTAL_FILENAME = f"instrumental{OUTPUT_FORMAT}"
ORIGINAL_FILENAME_SUFFIX = f"_original{OUTPUT_FORMAT}" # Suffix if copying/converting original

# --- GUI ---
WINDOW_TITLE = "Open Karaoke Studio"
DEFAULT_STATUS_READY = "Status: Ready"
DEFAULT_STATUS_SELECT_FILE = "Status: Select an audio file"

# --- Future Use ---
YT_DOWNLOAD_DIR = Path("./downloads") # Temporary directory for YouTube downloads
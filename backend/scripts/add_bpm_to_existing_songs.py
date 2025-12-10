#!/usr/bin/env python3
"""
Script to detect and add BPM for all existing songs in the database.

This script goes through all songs that don't have BPM values yet,
detects their tempo using Librosa, and updates the database.
"""

import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_config
from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.audio import detect_bpm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to process all songs for BPM detection."""
    logger.info("Starting BPM detection for all songs...")

    config = get_config()
    processed_count = 0
    error_count = 0

    try:
        with get_db_session() as session:
            repo = SongRepository(session)

            # Get all songs that don't have BPM yet
            songs_without_bpm = repo.fetch_all(filters={"bpm": None})

            logger.info(f"Found {len(songs_without_bpm)} songs without BPM values")

            for song in songs_without_bpm:
                try:
                    song_id = song.id
                    song_title = song.title
                    song_artist = song.artist

                    logger.info(f"Processing song: {song_title} by {song_artist}")

                    # Find the original audio file
                    song_dir = Path(config.LIBRARY_DIR) / song_id
                    original_file = song_dir / "original.mp3"

                    if not original_file.exists():
                        logger.warning(f"Original file not found for song {song_id}: {original_file}")
                        error_count += 1
                        continue

                    # Detect BPM
                    detected_bpm = detect_bpm(original_file, lambda msg: logger.info(f"[{song_title}] {msg}"))

                    if detected_bpm is not None:
                        # Update the song with BPM
                        repo.update(song_id, bpm=detected_bpm)
                        logger.info(f"Updated {song_title} with BPM: {detected_bpm}")
                        processed_count += 1
                    else:
                        logger.warning(f"Failed to detect BPM for {song_title}")
                        error_count += 1

                except Exception as e:
                    logger.error(f"Error processing song {song_id} ({song_title}): {e}")
                    error_count += 1
                    continue

        logger.info("BPM detection completed!")
        logger.info(f"Successfully processed: {processed_count} songs")
        logger.info(f"Errors: {error_count} songs")

    except Exception as e:
        logger.error(f"Fatal error during BPM detection: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
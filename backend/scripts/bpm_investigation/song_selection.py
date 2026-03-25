"""
Song selection logic for BPM investigation.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to sys.path to allow imports from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_config
from app.db.database import get_db_session
from app.db.models import DbSong
from app.repositories.song_repository import SongRepository

from .config import PRIMARY_TEST_SONG_ID

logger = logging.getLogger(__name__)


def find_audio_file(song_id: str) -> Optional[Path]:
    """
    Locate the audio file for a given song ID.

    Searches in order of preference:
    1. instrumental.mp3 (preferred - cleaner beat detection)
    2. original.mp3 (fallback)

    Args:
        song_id: Database ID of the song

    Returns:
        Path to the audio file, or None if not found
    """
    config = get_config()
    song_dir = config.LIBRARY_DIR / song_id

    # Prefer instrumental for cleaner beat detection
    instrumental_path = song_dir / "instrumental.mp3"
    if instrumental_path.exists():
        return instrumental_path

    # Fallback to original
    original_path = song_dir / "original.mp3"
    if original_path.exists():
        return original_path

    logger.warning(f"No audio file found for song {song_id} in {song_dir}")
    return None


def select_test_songs() -> List[DbSong]:
    """
    Select diverse test songs from the database for BPM accuracy testing.

    Selection criteria:
    - Always includes primary test song: 328a2091-db5e-4dfe-b516-6cbcadde8678
    - Auto-selects 3 additional songs with diverse BPM ranges:
      * Slow: 60-90 BPM
      * Medium: 90-140 BPM
      * Fast: 140-180+ BPM
    - Verifies audio files exist before including

    Returns:
        List of DbSong objects ready for testing
    """
    logger.info("Selecting test songs from database...")

    with get_db_session() as db:
        repo = SongRepository(db)

        # Always include primary test song (Drum & Bass track)
        primary_song = repo.fetch(PRIMARY_TEST_SONG_ID)

        selected_songs = []
        if primary_song and find_audio_file(primary_song.id):
            selected_songs.append(primary_song)
            logger.info(
                f"Added primary test song: {primary_song.title} by {primary_song.artist}"
            )
        else:
            logger.warning(
                f"Primary test song {PRIMARY_TEST_SONG_ID} not found or missing audio file"
            )

        # Select diverse additional songs
        all_songs = repo.fetch_all()

        # Define BPM ranges
        bpm_ranges = [
            ("Slow", 60, 90),
            ("Medium", 90, 140),
            ("Fast", 140, 200),
        ]

        for range_name, min_bpm, max_bpm in bpm_ranges:
            # Find songs in this BPM range with valid audio files
            candidates = [
                song
                for song in all_songs
                if song.bpm is not None
                and min_bpm <= song.bpm < max_bpm
                and song.id not in [s.id for s in selected_songs]
                and find_audio_file(song.id) is not None
            ]

            if candidates:
                # Select the first candidate (could be randomized if desired)
                selected = candidates[0]
                selected_songs.append(selected)
                logger.info(
                    f"Added {range_name} BPM song ({selected.bpm} BPM): "
                    f"{selected.title} by {selected.artist}"
                )
            else:
                logger.warning(f"No {range_name} BPM songs found with valid audio files")

    logger.info(f"Selected {len(selected_songs)} total test songs")
    return selected_songs

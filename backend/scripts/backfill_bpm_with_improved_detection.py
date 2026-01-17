"""
Backfill BPM for existing songs using improved detection algorithm.
Can optionally re-detect for songs with potentially incorrect BPM.
"""

import logging
import argparse
from pathlib import Path
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_config
from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.audio import detect_bpm
from app.services import file_management

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_bpm(redetect_all: bool = False, min_bpm: float = 30, max_bpm: float = 300):
    """
    Backfill BPM for songs.

    Args:
        redetect_all: If True, re-detect BPM for all songs. If False, only detect for songs without BPM.
        min_bpm: Songs with BPM below this will be re-detected
        max_bpm: Songs with BPM above this will be re-detected
    """
    config = get_config()
    updated_count = 0
    failed_count = 0
    skipped_count = 0

    with get_db_session() as session:
        repo = SongRepository(session)
        songs = repo.fetch_all()

        logger.info(f"Found {len(songs)} total songs")

        for idx, song in enumerate(songs, 1):
            try:
                # Determine if we should process this song
                should_process = (
                    redetect_all or
                    song.bpm is None or
                    song.bpm < min_bpm or
                    song.bpm > max_bpm
                )

                if not should_process:
                    skipped_count += 1
                    continue

                logger.info(f"[{idx}/{len(songs)}] Processing: {song.title} by {song.artist} (current BPM: {song.bpm})")

                # Get file paths
                song_dir = Path(config.BASE_LIBRARY_DIR) / song.id
                original_path = song_dir / "original.mp3"
                instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

                if not original_path.exists():
                    logger.warning(f"  Original file not found for song {song.id}")
                    failed_count += 1
                    continue

                # Detect BPM
                def status_callback(msg):
                    logger.info(f"  {msg}")

                detected_bpm = detect_bpm(
                    original_path,
                    status_callback,
                    instrumental_path if instrumental_path.exists() else None
                )

                if detected_bpm:
                    repo.update(song.id, bpm=detected_bpm)
                    logger.info(f"  ✓ Updated: {song.bpm} -> {detected_bpm} BPM")
                    updated_count += 1
                else:
                    logger.warning(f"  ✗ BPM detection failed for song {song.id}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  ✗ Error processing song {song.id}: {e}", exc_info=True)
                failed_count += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Backfill complete!")
    logger.info(f"  Updated: {updated_count}")
    logger.info(f"  Failed:  {failed_count}")
    logger.info(f"  Skipped: {skipped_count}")
    logger.info("=" * 60)

    return updated_count, failed_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill BPM for existing songs using improved detection algorithm"
    )
    parser.add_argument(
        "--redetect-all",
        action="store_true",
        help="Re-detect BPM for all songs (default: only songs without BPM)"
    )
    parser.add_argument(
        "--min-bpm",
        type=float,
        default=30,
        help="Re-detect songs below this BPM (default: 30)"
    )
    parser.add_argument(
        "--max-bpm",
        type=float,
        default=300,
        help="Re-detect songs above this BPM (default: 300)"
    )

    args = parser.parse_args()

    logger.info("Starting BPM backfill...")
    logger.info(f"  Redetect all: {args.redetect_all}")
    logger.info(f"  BPM range: {args.min_bpm}-{args.max_bpm}")
    logger.info("")

    backfill_bpm(args.redetect_all, args.min_bpm, args.max_bpm)

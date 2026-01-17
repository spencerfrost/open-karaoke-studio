"""
Backfill BPM for existing songs.
Processes all songs where bpm IS NULL and instrumental.mp3 exists.
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.audio import detect_bpm
from app.config import get_config

logger = logging.getLogger(__name__)


def backfill_bpm():
    """Detect and save BPM for all existing songs that don't have it."""
    config = get_config()

    with get_db_session() as db:
        repo = SongRepository(db)

        # Find all songs without BPM
        songs = repo.fetch_all()
        songs_without_bpm = [s for s in songs if s.bpm is None]

        logger.info(f"Found {len(songs_without_bpm)} songs without BPM")
        print(f"Found {len(songs_without_bpm)} songs without BPM\n")

        success_count = 0
        error_count = 0
        skip_count = 0

        for i, song in enumerate(songs_without_bpm, 1):
            try:
                # Check if instrumental file exists
                song_dir = Path(config.LIBRARY_DIR) / song.id
                instrumental_path = song_dir / "instrumental.mp3"

                if not instrumental_path.exists():
                    logger.warning(f"[{i}/{len(songs_without_bpm)}] Skipping {song.title}: no instrumental file")
                    print(f"[{i}/{len(songs_without_bpm)}] ⊗ Skipping {song.title}: no instrumental file")
                    skip_count += 1
                    continue

                # Detect BPM
                def status_callback(msg):
                    logger.info(f"{song.title}: {msg}")
                    # Don't print status messages to avoid clutter

                print(f"[{i}/{len(songs_without_bpm)}] Detecting BPM for: {song.title}")
                bpm = detect_bpm(instrumental_path, status_callback)

                if bpm:
                    # Update song
                    repo.update(song.id, bpm=bpm)
                    logger.info(f"✓ {song.title}: BPM = {bpm}")
                    print(f"[{i}/{len(songs_without_bpm)}] ✓ {song.title}: BPM = {bpm}")
                    success_count += 1
                else:
                    logger.warning(f"✗ {song.title}: BPM detection failed")
                    print(f"[{i}/{len(songs_without_bpm)}] ✗ {song.title}: BPM detection failed")
                    error_count += 1

            except Exception as e:
                logger.error(f"✗ {song.title}: Error - {str(e)}", exc_info=True)
                print(f"[{i}/{len(songs_without_bpm)}] ✗ {song.title}: Error - {str(e)}")
                error_count += 1

        print(f"\n{'='*60}")
        print(f"Backfill complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors:  {error_count}")
        print(f"  Skipped: {skip_count} (missing instrumental.mp3)")
        print(f"  Total:   {len(songs_without_bpm)}")
        print(f"{'='*60}\n")

        logger.info(
            f"Backfill complete: {success_count} success, {error_count} errors, {skip_count} skipped"
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    backfill_bpm()

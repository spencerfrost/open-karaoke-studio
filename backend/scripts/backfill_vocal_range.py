"""
Backfill vocal range and duration for existing songs.

- Duration: read from original.mp3 file metadata (fast, no audio loading)
- Vocal range: run librosa.pyin on vocals.mp3 (slow, ~10-30s per song)

By default skips songs that already have both values. Use --force to re-run all.

Usage:
    cd backend && source venv/bin/activate
    python scripts/backfill_vocal_range.py [--dry-run] [--force] [--duration-only] [--range-only]
"""
import argparse
import logging
import sys
from pathlib import Path

import librosa

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_config
from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.audio import detect_vocal_range

logger = logging.getLogger(__name__)


def backfill(
    dry_run: bool = False,
    force: bool = False,
    duration_only: bool = False,
    range_only: bool = False,
):
    config = get_config()

    with get_db_session() as db:
        repo = SongRepository(db)
        all_songs = repo.fetch_all()

        if force:
            songs = all_songs
        else:
            songs = [
                s
                for s in all_songs
                if (not duration_only and not range_only and (s.vocal_range_low is None or not s.duration))
                or (duration_only and not s.duration)
                or (range_only and s.vocal_range_low is None)
            ]

        do_duration = not range_only
        do_range = not duration_only

        print(f"Processing {len(songs)} / {len(all_songs)} songs")
        print(f"  Duration:    {'yes' if do_duration else 'no'}")
        print(f"  Vocal range: {'yes' if do_range else 'no'}")
        print()

        duration_ok = duration_skip = duration_err = 0
        range_ok = range_skip = range_err = 0

        for i, song in enumerate(songs, 1):
            song_dir = Path(config.LIBRARY_DIR) / song.id
            prefix = f"[{i}/{len(songs)}] '{song.title}'"

            if dry_run:
                original = song_dir / "original.mp3"
                vocals = song_dir / "vocals.mp3"
                print(
                    f"{prefix}: would process"
                    f" (original={'✓' if original.exists() else '✗'},"
                    f" vocals={'✓' if vocals.exists() else '✗'})"
                )
                duration_ok += do_duration
                range_ok += do_range
                continue

            updates = {}

            # --- Duration ---
            if do_duration and (force or not song.duration):
                original_path = song_dir / "original.mp3"
                if original_path.exists():
                    try:
                        duration = librosa.get_duration(path=str(original_path))
                        updates["duration"] = duration
                        duration_ok += 1
                    except Exception as e:
                        logger.warning("Duration detection failed for %s: %s", song.id, e)
                        duration_err += 1
                else:
                    duration_skip += 1

            # --- Vocal range ---
            if do_range and (force or song.vocal_range_low is None):
                vocals_path = song_dir / "vocals.mp3"
                if vocals_path.exists():
                    result = detect_vocal_range(
                        vocals_path, lambda msg: logger.debug("%s: %s", song.title, msg)
                    )
                    if result is not None:
                        updates["vocal_range_low"] = result[0]
                        updates["vocal_range_high"] = result[1]
                        range_ok += 1
                    else:
                        range_err += 1
                else:
                    range_skip += 1

            if updates:
                repo.update(song.id, **updates)
                parts = []
                if "duration" in updates:
                    parts.append(f"duration={updates['duration']:.1f}s")
                if "vocal_range_low" in updates:
                    parts.append(f"range={updates['vocal_range_low']}–{updates['vocal_range_high']}")
                print(f"{prefix}: ✓ {', '.join(parts)}")
            else:
                print(f"{prefix}: – nothing to update")

        print(f"\n{'='*60}")
        if dry_run:
            print("Dry run complete (no changes made)")
        else:
            print("Backfill complete!")
        if do_duration:
            print(f"  Duration:    {duration_ok} ok, {duration_err} errors, {duration_skip} skipped (no original.mp3)")
        if do_range:
            print(f"  Vocal range: {range_ok} ok, {range_err} errors, {range_skip} skipped (no vocals.mp3)")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Backfill duration and vocal range for existing songs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making any changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even for songs that already have data",
    )
    parser.add_argument(
        "--duration-only",
        action="store_true",
        help="Only backfill duration (skip vocal range detection)",
    )
    parser.add_argument(
        "--range-only",
        action="store_true",
        help="Only backfill vocal range (skip duration)",
    )
    args = parser.parse_args()

    if args.duration_only and args.range_only:
        print("Error: --duration-only and --range-only are mutually exclusive")
        sys.exit(1)

    backfill(
        dry_run=args.dry_run,
        force=args.force,
        duration_only=args.duration_only,
        range_only=args.range_only,
    )

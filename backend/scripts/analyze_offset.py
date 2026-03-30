"""
Analyze the global LRC timestamp offset for a song.

Compares synced LRC timestamps against detected vocal onsets in the vocals audio
to estimate how far out of sync the lyrics are, and optionally saves a corrected
version.

Usage:
    python scripts/analyze_offset.py --song-id <id>        # Analyze only
    python scripts/analyze_offset.py --song-id <id> --apply # Analyze + save corrected version
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_session
from app.repositories.lyrics_repository import LyricsRepository
from app.repositories.song_repository import SongRepository
from app.services.file_service import FileService
from app.services.lyrics_offset import analyze_global_offset, shift_lrc_timestamps

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run(song_id: str, apply: bool = False) -> None:
    file_service = FileService()

    with get_db_session() as db:
        song_repo = SongRepository(db)
        song = song_repo.fetch(song_id)
        if not song:
            print(f"Song not found: {song_id}")
            sys.exit(1)

        lyrics_repo = LyricsRepository(db)
        lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
        if not lyrics or not lyrics.content:
            print(f'No active synced lyrics for "{song.title}"')
            sys.exit(1)

        vocals_path = file_service.get_vocals_path(song_id, ".mp3")
        if not vocals_path.exists():
            print(
                f'No vocals.mp3 found for "{song.title}". '
                "Run audio separation (Demucs) before analyzing offset."
            )
            sys.exit(1)

        print(f'Song: "{song.title}" — {song.artist}')
        print(f"Vocals: {vocals_path}")
        print()
        print("Analyzing offset...")

        result = analyze_global_offset(lyrics.content, vocals_path)

        # --- Per-anchor table -------------------------------------------------
        anchors = result["anchors"]
        print(f"\n{'Anchor':<6}  {'Type':<18}  {'LRC ts':>8}  {'Onset':>8}  {'Offset':>8}  {'':>8}  Text")
        print("-" * 90)
        for i, a in enumerate(anchors, 1):
            onset_str = f"{a['detected_onset']:.3f}s" if a["detected_onset"] is not None else "   N/A"
            offset_str = f"{a['offset']:+.3f}s" if a["offset"] is not None else "   N/A"
            flag = "[EXCLUDED]" if a.get("excluded") else ""
            print(
                f"{i:<6}  {a['anchor_type']:<18}  {a['lrc_timestamp']:>7.3f}s"
                f"  {onset_str:>8}  {offset_str:>8}  {flag:<10}  \"{a['line_text'][:40]}\""
            )

        # --- Summary ----------------------------------------------------------
        print()
        if result["estimated_offset"] is None:
            print("Result: INSUFFICIENT DATA — could not estimate offset.")
            print(
                f"  {result['successful_anchors']}/{result['anchor_count']} anchors yielded a measurement."
            )
            return

        print(f"Estimated offset : {result['estimated_offset']:+.3f}s")
        print(f"Confidence       : {result['confidence'].upper()}")
        print(f"Anchors          : {result['successful_anchors']}/{result['anchor_count']} successful")
        if result["max_deviation"] is not None:
            print(f"Max deviation    : {result['max_deviation']:.3f}s")

        if result["confidence"] in ("low", "insufficient"):
            print(
                "\nWarning: low confidence — verify results before applying."
            )

        # --- Apply ------------------------------------------------------------
        if apply:
            if result["estimated_offset"] is None:
                print("\n--apply skipped: no offset estimate available.")
                return

            corrected = shift_lrc_timestamps(lyrics.content, -result["estimated_offset"])
            new_lyrics = lyrics_repo.save_lyrics(
                song_id=song_id,
                lyrics_type="synced",
                content=corrected,
                source="offset_correction",
                metadata={
                    "estimated_offset": result["estimated_offset"],
                    "confidence": result["confidence"],
                    "anchor_count": result["anchor_count"],
                    "successful_anchors": result["successful_anchors"],
                    "max_deviation": result["max_deviation"],
                },
                is_active=False,
            )
            print(
                f"\nSaved corrected lyrics as inactive version (id={new_lyrics.id})."
            )
            print(
                f"To activate: PATCH /api/lyrics/{new_lyrics.id}/activate"
            )
        else:
            print(
                "\nRun with --apply to save a corrected lyrics version."
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze global LRC timestamp offset for a song."
    )
    parser.add_argument(
        "--song-id",
        required=True,
        metavar="ID",
        help="Song ID to analyze.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Save the corrected lyrics as an inactive version in the database.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("app").setLevel(logging.DEBUG)

    run(args.song_id, apply=args.apply)


if __name__ == "__main__":
    main()

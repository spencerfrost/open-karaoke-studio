"""
Backfill correct `line_index` values and instrumental_intervals into songs
that already have stored word-synced alignment data.

Fixes the root cause documented in docs/plans/archive/2026-08-30-lyrics-alignment-indexing.md:
WhisperX's sentence-splitting shifted line_index for every word after the
first split, and the old intro/mid-song instrumental threshold split was
inconsistent. The stored `words` array's timings are already correct and in
WhisperX's original positional order, so this recomputes labels offline by
walking that order against the original lyrics text — no audio, no GPU,
no re-running WhisperX.

Usage:
    python scripts/backfill_lyrics_line_index.py            # dry run, report only
    python scripts/backfill_lyrics_line_index.py --apply     # write changes
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.lyrics_alignment import (
    AlignedWord,
    _build_instrumental_intervals,
    recompute_alignment_line_indices,
)

logger = logging.getLogger(__name__)


def _source_content(song, source_type: str) -> str | None:
    return song.synced_lyrics if source_type == "synced" else song.plain_lyrics


def backfill_lyrics_line_index(apply: bool) -> None:
    mode = "APPLY" if apply else "DRY RUN"
    print(f"Backfilling lyrics line_index ({mode})\n")

    with get_db_session() as db:
        repo = SongRepository(db)
        songs = [s for s in repo.fetch_all() if s.word_synced_lyrics]

        print(f"Found {len(songs)} songs with stored word-synced alignment\n")

        songs_changed = 0
        songs_unchanged = 0
        songs_skipped_no_content = 0
        songs_skipped_divergence = 0
        total_lines_changed = 0

        for i, song in enumerate(songs, 1):
            try:
                stored = json.loads(song.word_synced_lyrics)
            except (TypeError, ValueError):
                logger.warning(
                    "Skipping %s: unparseable word_synced_lyrics JSON", song.id
                )
                songs_skipped_no_content += 1
                continue

            source_type = stored.get("lyrics_source_type")
            words: list[AlignedWord] = stored.get("words", [])
            content = _source_content(song, source_type) if source_type else None

            if not content or not words:
                print(
                    f"[{i}/{len(songs)}] ⊘ Skipping {song.title}: no source content or words"
                )
                songs_skipped_no_content += 1
                continue

            recomputed = recompute_alignment_line_indices(
                words, source_type=source_type, content=content
            )
            if recomputed is None:
                print(
                    f"[{i}/{len(songs)}] ⊘ Skipping {song.title}: token walk diverged"
                )
                songs_skipped_divergence += 1
                continue

            words_relabelled = sum(
                1
                for old, new in zip(words, recomputed)
                if old["line_index"] != new["line_index"]
            )
            new_intervals = _build_instrumental_intervals(recomputed)

            if words_relabelled == 0 and new_intervals == stored.get(
                "instrumental_intervals", []
            ):
                songs_unchanged += 1
                continue

            songs_changed += 1
            total_lines_changed += words_relabelled
            print(
                f"[{i}/{len(songs)}] {'✓' if apply else '→'} {song.title}: "
                f"{words_relabelled} word(s) relabelled, "
                f"{len(new_intervals)} instrumental interval(s) "
                f"(was {len(stored.get('instrumental_intervals', []))})"
            )

            if apply:
                stored["words"] = recomputed
                stored["instrumental_intervals"] = new_intervals
                repo.update(song.id, word_synced_lyrics=json.dumps(stored))

        print(f"\n{'=' * 60}")
        print(
            "Backfill complete!" if apply else "Dry run complete — no changes written."
        )
        print(f"  Changed:            {songs_changed}")
        print(f"  Words relabelled:   {total_lines_changed}")
        print(f"  Unchanged:          {songs_unchanged}")
        print(f"  Skipped (content):  {songs_skipped_no_content}")
        print(f"  Skipped (diverged): {songs_skipped_divergence}")
        print(f"  Total:              {len(songs)}")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write recomputed line_index/instrumental_intervals to the database. "
        "Without this flag the script only reports what would change.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    backfill_lyrics_line_index(apply=args.apply)

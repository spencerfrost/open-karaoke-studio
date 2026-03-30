"""
Analyze synced lyrics for section break detection.

Runs timing gap and text repetition analysis on songs with synced lyrics,
producing a report of where section breaks should be inserted.

Usage:
    python scripts/analyze_section_breaks.py                      # Analyze all songs
    python scripts/analyze_section_breaks.py --song-id <id>       # Single song (detailed)
    python scripts/analyze_section_breaks.py --save                # Save as inactive lyrics versions
    python scripts/analyze_section_breaks.py --output report.json  # JSON report
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_session
from app.repositories.lyrics_repository import LyricsRepository
from app.repositories.song_repository import SongRepository
from app.services.lyrics_analysis import analyze_lyrics

logger = logging.getLogger(__name__)


def analyze_song(song, lyrics_repo, save=False):
    """Analyze a single song's synced lyrics. Returns analysis result or None."""
    lyrics = lyrics_repo.get_active_lyrics(song.id, "synced")
    if not lyrics or not lyrics.content:
        return None

    result = analyze_lyrics(lyrics.content)

    if save and result["candidates"]:
        lyrics_repo.save_lyrics(
            song_id=song.id,
            lyrics_type="synced",
            content=result["modified_lrc"],
            source="analysis",
            metadata={
                "candidates": result["candidates"],
                "stats": result["stats"],
            },
            is_active=False,
        )

    return result


def print_song_result(index, total, song, result):
    """Print analysis result for a single song."""
    if result is None:
        print(f"[{index}/{total}] Skipping \"{song.title}\" - {song.artist}: no synced lyrics")
        return

    candidates = result["candidates"]
    stats = result["stats"]
    median_gap = stats["median_gap"]

    header = f"[{index}/{total}] \"{song.title}\" - {song.artist}"
    detail = f"  Lines: {result['total_lines']} | Median gap: {median_gap:.1f}s | Existing breaks: {result['existing_breaks']}"

    if not candidates:
        print(f"{header}")
        print(f"{detail}")
        print(f"  No candidates found")
        return

    print(f"{header}")
    print(f"{detail}")
    print(f"  {len(candidates)} candidate(s):")

    for c in candidates:
        methods_str = "+".join(c["methods"])
        reasons_str = "; ".join(c["reasons"])
        print(
            f"    Line {c['after_line_index']}  [{c['confidence']:.2f}] {methods_str}  \"{reasons_str}\""
        )
        print(
            f"      \"{c['before_text']}\"  -->  \"{c['after_text']}\""
        )


def run_analysis(song_id=None, save=False, output_path=None):
    """Run section break analysis on songs."""
    with get_db_session() as db:
        song_repo = SongRepository(db)
        lyrics_repo = LyricsRepository(db)

        if song_id:
            song = song_repo.fetch(song_id)
            if not song:
                print(f"Song not found: {song_id}")
                return
            songs = [song]
        else:
            songs = song_repo.fetch_all()

        total = len(songs)
        results = []
        songs_with_candidates = 0
        songs_without_lyrics = 0
        total_candidates = 0

        print(f"Analyzing {total} song(s)...\n")

        for i, song in enumerate(songs, 1):
            try:
                result = analyze_song(song, lyrics_repo, save=save)

                if result is None:
                    songs_without_lyrics += 1
                    if song_id:
                        # Only print skip message for single-song mode
                        print_song_result(i, total, song, result)
                    continue

                if result["candidates"]:
                    songs_with_candidates += 1
                    total_candidates += len(result["candidates"])

                # Print detailed output for single song, or songs with candidates in batch
                if song_id or result["candidates"]:
                    print_song_result(i, total, song, result)

                if output_path:
                    results.append(
                        {
                            "song_id": song.id,
                            "title": song.title,
                            "artist": song.artist,
                            **result,
                        }
                    )

            except Exception as e:
                logger.error(f"Error analyzing {song.title}: {e}", exc_info=True)
                print(f"[{i}/{total}] Error analyzing \"{song.title}\": {e}")

        # Summary
        if not song_id:
            print(f"\n{'=' * 60}")
            print(f"Analysis complete!")
            print(f"  Songs analyzed: {total - songs_without_lyrics}")
            print(f"  Songs without synced lyrics: {songs_without_lyrics}")
            print(f"  Songs with candidates: {songs_with_candidates}")
            print(f"  Total candidates: {total_candidates}")
            if save:
                print(f"  Saved: {songs_with_candidates} inactive lyrics versions")
            print(f"{'=' * 60}\n")

        if output_path:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Report written to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Analyze lyrics for section breaks")
    parser.add_argument("--song-id", help="Analyze a single song by ID")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save analyzed lyrics as inactive versions",
    )
    parser.add_argument("--output", help="Write JSON report to file")
    args = parser.parse_args()

    run_analysis(song_id=args.song_id, save=args.save, output_path=args.output)
